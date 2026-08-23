import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia, setActivePinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import TimelineBar from "./TimelineBar.vue";
import { useMapDataStore } from "../../stores/mapData";
import { useLiveDockStore } from "../../stores/liveDock";

/**
 * TimelineBar.test.ts — lane 16 rewrite (authorized rewrite class: the
 * `whiterunMock.ts`-fixture premise this file asserted is exactly what
 * this lane replaces). `TimelineBar` reads `useMapDataStore()` itself
 * (mirroring MapScreen.vue's idiom, since this lane found MapScreen needs
 * no prop-passing edit -- see the lane report), so these tests populate
 * that store directly (`load`/`setTick`/`dockToLatest`, same idiom
 * `stores/mapData.test.ts` uses) rather than mounting the full MapScreen.
 *
 * Fixture: tick 0 keyframe (empty state); tick 10 `belief_formed` (claim
 * c1) -> one claim_born marker; tick 20 `npc_died` -> one events marker;
 * tick 30 `mutation_applied` (claim c1) -> one mutation marker. maxTick=30.
 */
function eventLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "events", seq, payload }) + "\n";
}

function traceLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "trace", seq, payload }) + "\n";
}

const keyframeLine = eventLine(0, 0, { record_type: "keyframe", state: { claims: [], variants: [], beliefs: [], evidence: [], rumor_states: [] } });
const diedLine = eventLine(20, 1, { event_type: "npc_died", npc_id: "npc-9", location_id: "dragonsreach" });
const EVENTS_CONTENT = keyframeLine + diedLine;
const EVENT_TICK_OFFSETS = { "0": 0, "20": new TextEncoder().encode(keyframeLine).length };

const beliefLine = traceLine(10, 0, { record_type: "belief_formed", claim_id: "c1", holder_id: "irileth" });
const mutationLine = traceLine(30, 1, { record_type: "mutation_applied", claim_id: "c1", slot: "cause" });
const TRACE_CONTENT = beliefLine + mutationLine;
const TRACE_TICK_OFFSETS = { "10": 0, "30": new TextEncoder().encode(beliefLine).length };

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "test-run",
      seed_id: "s",
      created_wall_ts: 0,
      branches: [{ save_uuid: "s", generation: 0 }],
      tick_range: { start: 0, end: 30 },
      streams: { events: "events.jsonl", trace: "trace.jsonl" },
      status: "complete",
    },
  ],
};

const SIDECAR = {
  schema_version: 1,
  streams: {
    events: { tick_offsets: EVENT_TICK_OFFSETS, keyframe_offsets: [{ tick: 0, offset: 0 }] },
    trace: { tick_offsets: TRACE_TICK_OFFSETS },
  },
};

function rangeResponse(content: string, init?: RequestInit): Response {
  const rangeHeader = (init?.headers as Record<string, string> | undefined)?.Range ?? "";
  const bytes = new TextEncoder().encode(content);
  const match = /^bytes=(\d+)-(\d*)$/.exec(rangeHeader);
  let start = 0;
  let end = bytes.length;
  if (match) {
    start = Number(match[1]);
    end = match[2] === "" ? bytes.length : Number(match[2]) + 1;
  }
  end = Math.min(end, bytes.length);
  const text = new TextDecoder().decode(bytes.slice(start, end));
  return new Response(text, { status: 206, headers: { "Content-Range": `bytes ${start}-${end - 1}/${bytes.length}` } });
}

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/runs/index.json")) return new Response(JSON.stringify(REGISTRY), { status: 200 });
      if (url.endsWith("/index.json")) return new Response(JSON.stringify(SIDECAR), { status: 200 });
      if (url.endsWith("events.jsonl")) return rangeResponse(EVENTS_CONTENT, init);
      if (url.endsWith("trace.jsonl")) return rangeResponse(TRACE_CONTENT, init);
      return new Response(null, { status: 404 });
    }),
  );
}

async function setup() {
  stubFetch();
  const pinia = createPinia();
  setActivePinia(pinia);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/", component: { template: "<div />" } }],
  });
  await router.push("/");
  await router.isReady();

  const mapData = useMapDataStore(pinia);
  await mapData.load("test-run");

  return { pinia, router, mapData };
}

function mountBar(pinia: ReturnType<typeof createPinia>, router: ReturnType<typeof createRouter>) {
  return mount(TimelineBar, { global: { plugins: [pinia, router] } });
}

describe("TimelineBar", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the real run's typed markers (claim born + mutation + events) and day ticks derived from the log", async () => {
    const { pinia, router, mapData } = await setup();
    await mapData.setTick(30);
    const wrapper = mountBar(pinia, router);
    await flushPromises();

    expect(wrapper.findAll(".track__event")).toHaveLength(3);
    expect(wrapper.text()).toContain("3 typed markers");
  });

  it("playhead follows urlState.t exactly, even at a tick with no record of its own (not the last-replayed record's tick)", async () => {
    const { pinia, router, mapData } = await setup();
    await router.push("/?t=25");
    await mapData.setTick(25); // between the tick-20 and tick-30 records -- nothing lands exactly here
    const wrapper = mountBar(pinia, router);
    await flushPromises();

    expect(wrapper.find('[data-testid="playhead-chip"]').text()).toContain("t 25");
  });

  it("clicking a marker sets urlState.t to that marker's tick ('replace' mode -- no new history entry)", async () => {
    const { pinia, router, mapData } = await setup();
    await mapData.setTick(30);
    const wrapper = mountBar(pinia, router);
    await flushPromises();

    const historyLengthBefore = window.history.length;
    const markers = wrapper.findAll(".track__event");
    const deathMarker = markers.find((m) => (m.attributes("title") ?? "").includes("death"))!;
    await deathMarker.trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.query.t).toBe("20");
    expect(window.history.length).toBe(historyLengthBefore);
  });

  it("toggling a legend type off hides that type's markers; toggling it back on shows them again", async () => {
    const { pinia, router, mapData } = await setup();
    await mapData.setTick(30);
    const wrapper = mountBar(pinia, router);
    await flushPromises();
    expect(wrapper.findAll(".track__event")).toHaveLength(3);

    const mutationLegendItem = wrapper.findAll(".timeline-legend__item").find((i) => i.text() === "▮ mutation")!;
    await mutationLegendItem.trigger("click");
    await flushPromises();
    expect(wrapper.findAll(".track__event")).toHaveLength(2);
    expect(wrapper.text()).toContain("2 typed markers");

    await mutationLegendItem.trigger("click");
    await flushPromises();
    expect(wrapper.findAll(".track__event")).toHaveLength(3);
  });

  it("mirrors mapData's historical (non-docked) state into the liveDock store: pill shows the detached form, not the frozen docked string", async () => {
    const { pinia, router, mapData } = await setup();
    await mapData.setTick(30);
    const wrapper = mountBar(pinia, router);
    await flushPromises();

    const liveDock = useLiveDockStore(pinia);
    expect(liveDock.docked).toBe(false);
    expect(wrapper.find('[data-testid="live-dock-pill"]').attributes("data-docked")).toBe("false");
  });

  it("mirrors mapData's docked (LIVE) state into the liveDock store: pill shows the frozen docked status string", async () => {
    const { pinia, router, mapData } = await setup();
    await mapData.dockToLatest();
    const wrapper = mountBar(pinia, router);
    await flushPromises();

    const liveDock = useLiveDockStore(pinia);
    expect(liveDock.docked).toBe(true);
    const pill = wrapper.find('[data-testid="live-dock-pill"]');
    expect(pill.attributes("data-docked")).toBe("true");
    expect(pill.text()).toBe(`LIVE — docked · following newest frame · +${liveDock.newEventCount} events · scrub to detach`);
  });
});
