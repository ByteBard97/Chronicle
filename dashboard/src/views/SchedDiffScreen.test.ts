import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import SchedDiffScreen from "./SchedDiffScreen.vue";

/**
 * SchedDiffScreen.test.ts -- RuleLogScreen.test.ts's pattern (memory-history
 * router, fetch stubbed to serve a synthetic run, flushPromises).
 *
 * Fixture: a tick-0 keyframe carrying a two-NPC base schedule, plus a
 * tick-0 `schedule_rewrite` overlaying one NPC (sven) to the temple for
 * `[0, 20)` -- enough to exercise total override, the causal link render,
 * the NPC filter, and (at a later tick) automatic restoration.
 */
function eventLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "save-1", generation: 0, tick, stream: "events", seq, payload }) + "\n";
}

const keyframeLine = eventLine(0, 0, {
  record_type: "keyframe",
  state: {
    claims: [],
    variants: [],
    beliefs: [],
    evidence: [],
    rumor_states: [],
    relationships: [],
    grudges: [],
    obligations: [],
    reputations: [],
    schedules: [
      { npc_id: "sven", location_id: "sven_house", start_tick: 0, end_tick: 100 },
      { npc_id: "erik", location_id: "market", start_tick: 0, end_tick: 100 },
    ],
  },
});

const rewriteLine = eventLine(0, 1, {
  event_type: "schedule_rewrite",
  gamets: 0,
  wall_ts: 0,
  origin: null,
  npc_id: "sven",
  location_id: "temple_of_kynareth",
  start_tick: 0,
  end_tick: 20,
  cause: "mourning",
  rule: "schedule-write-back",
  trigger_event_key: { save_uuid: "save-1", generation: 0, seq: 0 },
});

const EVENTS_CONTENT = keyframeLine + rewriteLine;
const EVENT_TICK_OFFSETS = { "0": 0 };
const TRACE_CONTENT = "";
const TRACE_TICK_OFFSETS = {};

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "scheddiff-test-run",
      seed_id: "s",
      created_wall_ts: 0,
      branches: [{ save_uuid: "save-1", generation: 0 }],
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

function stubFetch(registry: unknown = REGISTRY) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      if (url.endsWith("/runs/index.json")) return new Response(JSON.stringify(registry), { status: 200 });
      if (url.endsWith("/index.json")) return new Response(JSON.stringify(SIDECAR), { status: 200 });
      if (url.endsWith("events.jsonl")) return rangeResponse(EVENTS_CONTENT, init);
      if (url.endsWith("trace.jsonl")) return rangeResponse(TRACE_CONTENT, init);
      return new Response(null, { status: 404 });
    }),
  );
}

async function mountAt(query: string, registry: unknown = REGISTRY) {
  stubFetch(registry);
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: SchedDiffScreen },
      { path: "/scheddiff", component: SchedDiffScreen },
      { path: "/feed", component: { template: "<div>feed</div>" } },
    ],
  });
  await router.push(query);
  const pinia = createPinia();
  const wrapper = mount(SchedDiffScreen, { global: { plugins: [router, pinia] } });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  return { wrapper, router };
}

describe("SchedDiffScreen.vue", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("deep link ?run=...&t=10 shows both NPCs, sven overridden to the temple", async () => {
    const { wrapper } = await mountAt("/scheddiff?run=scheddiff-test-run&t=10");
    expect(wrapper.text()).toContain("2 NPCs");
    expect(wrapper.text()).toContain("sven");
    expect(wrapper.text()).toContain("erik");
    expect(wrapper.text()).toContain("temple_of_kynareth");
    expect(wrapper.text()).toContain("mourning");
  });

  it("the inserted block links its causing rule and event (feed deep link)", async () => {
    const { wrapper } = await mountAt("/scheddiff?run=scheddiff-test-run&t=10");
    const link = wrapper.find(".schedule-block-bar__event-link");
    expect(link.exists()).toBe(true);
    expect(link.text()).toContain("schedule-write-back");
    expect(link.attributes("href")).toBe("/feed?run=scheddiff-test-run&t=0");
  });

  it("restoration: at t=25 (past end_tick 20), sven is back on his base block, no overlay shown", async () => {
    const { wrapper } = await mountAt("/scheddiff?run=scheddiff-test-run&t=25");
    expect(wrapper.find(".schedule-block-bar__event-link").exists()).toBe(false);
    expect(wrapper.text()).toContain("sven_house");
    expect(wrapper.text()).not.toContain("temple_of_kynareth");
  });

  it("the NPC filter narrows to one NPC's lane row", async () => {
    const { wrapper } = await mountAt("/scheddiff?run=scheddiff-test-run&t=10");
    const select = wrapper.find(".schedule-filter-bar__field select");
    await select.setValue("erik");
    await flushPromises();
    const rows = wrapper.findAll(".schedule-lane-row__npc");
    expect(rows.map((r) => r.text())).toEqual(["erik"]);
  });

  it("deep link filters={\"npc\":\"sven\"} lands pre-filtered", async () => {
    const { wrapper } = await mountAt('/scheddiff?run=scheddiff-test-run&t=10&filters={"npc":"sven"}');
    const rows = wrapper.findAll(".schedule-lane-row__npc");
    expect(rows.map((r) => r.text())).toEqual(["sven"]);
  });

  it("shows a placeholder when no run is selected", async () => {
    const { wrapper } = await mountAt("/scheddiff?");
    expect(wrapper.text()).toContain("no run loaded");
  });
});
