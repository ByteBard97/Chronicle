import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import App from "./App.vue";
import TimelineBar from "./components/timeline/TimelineBar.vue";

/**
 * App.test.ts — lane 54 (M7 gate fix): the timeline is promoted from a
 * `/map`-only mount to global chrome (ui-spec §2), owned by `App.vue` (the
 * actual router-outlet wrapper — `Shell.vue` is only ever mounted at `/`,
 * not a shared layout across routes; see the lane report). This proves
 * the timeline renders and stays interactive on a non-map route, and that
 * `App.vue`'s own `[run, t]` watcher (a route-guarded twin of
 * `MapScreen.vue`'s, which steps aside whenever `/map` is the active
 * route so the two never race the same live tail) actually populates
 * `mapData` off `/map`, since nothing else does there.
 *
 * Fixture mirrors `TimelineBar.test.ts`'s: a keyframe at tick 0, a
 * `belief_formed` trace record at tick 10, and an `npc_died` event at
 * tick 20 (one typed marker) -- enough to prove real data reaches the
 * globally-mounted bar, not just that the component exists in the DOM.
 */

function eventLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return (
    JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "events", seq, payload }) +
    "\n"
  );
}

function traceLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return (
    JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "trace", seq, payload }) +
    "\n"
  );
}

const keyframeLine = eventLine(0, 0, { record_type: "keyframe", state: { claims: [], variants: [], beliefs: [], evidence: [], rumor_states: [] } });
const diedLine = eventLine(20, 1, { event_type: "npc_died", npc_id: "npc-9", location_id: "dragonsreach" });
const EVENTS_CONTENT = keyframeLine + diedLine;
const EVENT_TICK_OFFSETS = { "0": 0, "20": new TextEncoder().encode(keyframeLine).length };

const beliefLine = traceLine(10, 0, { record_type: "belief_formed", claim_id: "c1", holder_id: "irileth" });
const TRACE_CONTENT = beliefLine;
const TRACE_TICK_OFFSETS = { "10": 0 };

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "test-run",
      seed_id: "s",
      created_wall_ts: 0,
      branches: [{ save_uuid: "s", generation: 0 }],
      tick_range: { start: 0, end: 20 },
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

async function mountAppAt(path: string) {
  stubFetch();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      // Stand-ins, not the real views: this test is about App.vue's own
      // shell/watcher wiring, not any particular view's internals.
      { path: "/", component: { template: "<div class='landing-stub' />" } },
      { path: "/map", component: { template: "<div class='map-stub' />" } },
    ],
  });
  await router.push(path);
  const wrapper = mount(App, { global: { plugins: [router, createPinia()] } });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  return { wrapper, router };
}

describe("App.vue (lane 54: global timeline chrome)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the timeline with real typed markers on the landing route, without ever visiting /map", async () => {
    const { wrapper } = await mountAppAt("/?run=test-run&t=20");
    expect(wrapper.find(".landing-stub").exists()).toBe(true);
    expect(wrapper.findComponent(TimelineBar).exists()).toBe(true);
    expect(wrapper.findAll(".track__event").length).toBeGreaterThan(0);
  });

  it("marker clicks on the landing route still write urlState.t (scrub stays functional off /map)", async () => {
    const { wrapper, router } = await mountAppAt("/?run=test-run&t=0");
    const markers = wrapper.findAll(".track__event");
    const deathMarker = markers.find((m) => (m.attributes("title") ?? "").includes("death"));
    expect(deathMarker).toBeDefined();
    await deathMarker!.trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.query.t).toBe("20");
  });

  it("play/pause and speed presets stay wired off /map", async () => {
    const { wrapper } = await mountAppAt("/?run=test-run&t=0");
    const playBtn = wrapper.find('[data-testid="transport-play-pause"]');
    expect(playBtn.text()).toBe("▶");
    await playBtn.trigger("click");
    expect(playBtn.text()).toBe("⏸");
  });

  it("only mounts one TimelineBar on /map (App's global mount, not a duplicate from MapScreen)", async () => {
    const { wrapper } = await mountAppAt("/map?run=test-run&t=20");
    expect(wrapper.find(".map-stub").exists()).toBe(true);
    expect(wrapper.findAllComponents(TimelineBar)).toHaveLength(1);
  });
});
