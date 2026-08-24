import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import CompareScreen from "./CompareScreen.vue";

/**
 * CompareScreen.test.ts -- DiffScreen.test.ts's pattern (memory-history
 * router, fetch stubbed to serve two synthetic same-seed_id runs,
 * flushPromises), extended to TWO run ids (`run`/`runB`).
 *
 * Fixture: run "cmp-a" and run "cmp-b" share `seed_id: "s"`.
 *  - Both roll the SAME (tick, location, participants) pair at tick 2
 *    with the SAME `value` (0.3) but a DIFFERENT `threshold` (0.9 vs
 *    0.1) -- `encountered` flips (true vs false). This is
 *    `findFirstDivergentRoll`'s target: a real, byte-comparable
 *    divergence at a known tick.
 *  - Both form the same belief (`belief-x`, npc "npc-x") at tick 5; only
 *    run A corroborates it (tick 6, confidence 0.95) -- run B's belief
 *    stays at its witnessed baseline, so npc-x is a divergent entity in
 *    the ranked list once T >= 6.
 */
function eventLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "events", seq, payload }) + "\n";
}
function traceLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "trace", seq, payload }) + "\n";
}

const keyframeLine = eventLine(0, 0, {
  record_type: "keyframe",
  state: { claims: [], variants: [], beliefs: [], evidence: [], rumor_states: [], relationships: [], grudges: [], obligations: [], reputations: [] },
});
const EVENTS_CONTENT = keyframeLine;
const EVENT_TICK_OFFSETS = { "0": 0 };

function rollLine(threshold: number, encountered: boolean): string {
  return traceLine(2, 0, {
    record_type: "encounter_rolled",
    roll_key: { seed_id: "s", purpose: "encounter", tick: 2, site: "market", participants: ["p", "q"], draw: 0 },
    value: 0.3,
    threshold,
    outcome: encountered ? "encountered" : "missed",
    location_id: "market",
    npc_a: "p",
    npc_b: "q",
    encountered,
  });
}

const beliefFormed = traceLine(5, 0, {
  record_type: "belief_formed",
  belief_id: "belief-x",
  claim_id: "claim-1",
  holder_id: "npc-x",
  evidence_id: "ev-1",
  claim_kind: "theft",
  claim_slots: {},
  canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
});
const beliefCorroborated = traceLine(6, 0, { record_type: "belief_corroborated", belief_id: "belief-x", confidence_after: 0.95 });

const TRACE_A_ROLL = rollLine(0.9, true); // 0.3 < 0.9 -> encountered
const TRACE_B_ROLL = rollLine(0.1, false); // 0.3 < 0.1 is false -> not encountered

const TRACE_A_CONTENT = TRACE_A_ROLL + beliefFormed + beliefCorroborated;
const TRACE_B_CONTENT = TRACE_B_ROLL + beliefFormed;

const byteLen = (s: string) => new TextEncoder().encode(s).length;

const SIDECAR_A = {
  schema_version: 1,
  streams: {
    events: { tick_offsets: EVENT_TICK_OFFSETS, keyframe_offsets: [{ tick: 0, offset: 0 }] },
    trace: { tick_offsets: { "2": 0, "5": byteLen(TRACE_A_ROLL), "6": byteLen(TRACE_A_ROLL + beliefFormed) } },
  },
};
const SIDECAR_B = {
  schema_version: 1,
  streams: {
    events: { tick_offsets: EVENT_TICK_OFFSETS, keyframe_offsets: [{ tick: 0, offset: 0 }] },
    trace: { tick_offsets: { "2": 0, "5": byteLen(TRACE_B_ROLL) } },
  },
};

function registryEntry(runId: string) {
  return {
    run_id: runId,
    seed_id: "s",
    created_wall_ts: 0,
    branches: [{ save_uuid: "s", generation: 0 }],
    tick_range: { start: 0, end: 6 },
    streams: { events: "events.jsonl", trace: "trace.jsonl" },
    status: "complete",
  };
}
const REGISTRY = { schema_version: 1, runs: [registryEntry("cmp-a"), registryEntry("cmp-b")] };

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
      if (url.endsWith("/runs/cmp-a/index.json")) return new Response(JSON.stringify(SIDECAR_A), { status: 200 });
      if (url.endsWith("/runs/cmp-b/index.json")) return new Response(JSON.stringify(SIDECAR_B), { status: 200 });
      if (url.endsWith("/runs/cmp-a/events.jsonl")) return rangeResponse(EVENTS_CONTENT, init);
      if (url.endsWith("/runs/cmp-a/trace.jsonl")) return rangeResponse(TRACE_A_CONTENT, init);
      if (url.endsWith("/runs/cmp-b/events.jsonl")) return rangeResponse(EVENTS_CONTENT, init);
      if (url.endsWith("/runs/cmp-b/trace.jsonl")) return rangeResponse(TRACE_B_CONTENT, init);
      return new Response(null, { status: 404 });
    }),
  );
}

async function mountAt(query: string) {
  stubFetch();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: CompareScreen },
      { path: "/compare", component: CompareScreen },
    ],
  });
  await router.push(query);
  const pinia = createPinia();
  const wrapper = mount(CompareScreen, { global: { plugins: [router, pinia] } });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  await flushPromises();
  return { wrapper, router };
}

describe("CompareScreen.vue", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("deep link ?run=...&runB=...&t=... resolves both runs and shows the ranked divergence list as the primary rendering", async () => {
    const { wrapper } = await mountAt("/compare?run=cmp-a&runB=cmp-b&t=6");
    expect(wrapper.text()).toContain("npc-x");
    // The divergence list table must appear before (structurally, above)
    // the map panes -- primary, not buried below two maps.
    const html = wrapper.html();
    const listIdx = html.indexOf("divergence-list");
    const panesIdx = html.indexOf("compare-pane");
    expect(listIdx).toBeGreaterThan(-1);
    expect(panesIdx).toBeGreaterThan(-1);
    expect(listIdx).toBeLessThan(panesIdx);
  });

  it('"find first divergence" jumps both playheads to the same tick (the shared t)', async () => {
    const { wrapper, router } = await mountAt("/compare?run=cmp-a&runB=cmp-b&t=6");
    const btn = wrapper.find(".compare-screen__find-btn");
    expect(btn.exists()).toBe(true);
    expect(btn.attributes("disabled")).toBeUndefined();

    await btn.trigger("click");
    await flushPromises();
    await flushPromises();

    expect(router.currentRoute.value.query.t).toBe("2"); // the roll's tick
    const tickLabels = wrapper.findAll(".compare-pane__tick").map((n) => n.text());
    expect(tickLabels).toEqual(["t 2", "t 2"]); // both panes aligned on the same tick
  });

  it("a deep link with t pre-set lands both panes aligned on that tick without any interaction", async () => {
    const { wrapper } = await mountAt("/compare?run=cmp-a&runB=cmp-b&t=5");
    const tickLabels = wrapper.findAll(".compare-pane__tick").map((n) => n.text());
    expect(tickLabels).toEqual(["t 5", "t 5"]);
  });

  it("shows a placeholder until both run A and run B are selected", async () => {
    const { wrapper } = await mountAt("/compare?run=cmp-a");
    expect(wrapper.text()).toContain("pick two runs sharing a seed_id");
  });
});
