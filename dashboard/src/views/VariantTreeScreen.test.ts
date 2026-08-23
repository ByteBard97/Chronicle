import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import VariantTreeScreen from "./VariantTreeScreen.vue";

/**
 * VariantTreeScreen.test.ts -- Shell.test.ts/MapScreen.test.ts's pattern
 * (memory-history router, fetch stubbed to serve a synthetic run,
 * flushPromises). The fixture deliberately carries TWO claims (unlike the
 * real `runs/carrier-mutation-01`, which has exactly one -- see the lane
 * report) so "claim selector switches trees" is actually exercisable:
 *
 *  - `claim-a`: witness `npc-w` (t0) -> transmitted to `npc-x` on `va-1`
 *    (t1, plain) -> transmitted to `npc-y` on `va-2` (t2, mutated:
 *    `loc: market -> alley`, `mut-a`) -> a supersession at t3 naming
 *    canonical (`null`) as the winner -- exercising "either end of a
 *    supersession can be the canonical root" end-to-end through the
 *    screen, not just the derived module.
 *  - `claim-b`: witness `npc-p` only (t0), no variants -- a visibly
 *    smaller/different tree once selected.
 */

function eventLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "events", seq, payload }) + "\n";
}

function traceLine(tick: number, seq: number, payload: Record<string, unknown>): string {
  return JSON.stringify({ schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "trace", seq, payload }) + "\n";
}

const KEYFRAME_STATE = {
  claims: [
    { id: "claim-a", kind: "npc_death", slots: { loc: "market" }, canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 }, truth_status: "unconfirmed" },
    { id: "claim-b", kind: "npc_death", slots: {}, canonical_event_key: { save_uuid: "s", generation: 0, seq: 1 }, truth_status: "unconfirmed" },
  ],
  variants: [],
  beliefs: [
    { id: "belief-w", holder_id: "npc-w", claim_id: "claim-a", variant_id: null, confidence: 0.95, verbatim_strength: 1, gist_strength: 1, first_learned: 0, last_rehearsed: 0 },
    { id: "belief-p", holder_id: "npc-p", claim_id: "claim-b", variant_id: null, confidence: 0.9, verbatim_strength: 1, gist_strength: 1, first_learned: 0, last_rehearsed: 0 },
  ],
  evidence: [],
  rumor_states: [],
};

const keyframeLine = eventLine(0, 0, { record_type: "keyframe", state: KEYFRAME_STATE });
const EVENTS_CONTENT = keyframeLine;
const EVENT_TICK_OFFSETS = { "0": 0 };

const transmit1 = traceLine(1, 0, {
  record_type: "transmitted",
  claim_id: "claim-a",
  teller_id: "npc-w",
  teller_belief_id: "belief-w",
  hearer_id: "npc-x",
  hearer_belief_id: "belief-x",
  evidence_id: "ev-1",
  variant: { variant_id: "va-1", parent_variant_id: null, slots: { loc: "market" }, mutated_slot: null },
  location_id: "market",
});
const transmit2 = traceLine(2, 1, {
  record_type: "transmitted",
  claim_id: "claim-a",
  teller_id: "npc-x",
  teller_belief_id: "belief-x",
  hearer_id: "npc-y",
  hearer_belief_id: "belief-y",
  evidence_id: "ev-2",
  variant: { variant_id: "va-2", parent_variant_id: "va-1", slots: { loc: "alley" }, mutated_slot: "loc" },
  location_id: "alley",
});
const mutationApplied = traceLine(2, 2, {
  record_type: "mutation_applied",
  claim_id: "claim-a",
  parent_variant_id: "va-1",
  variant_id: "va-2",
  slot: "loc",
  old_value: "market",
  new_value: "alley",
  mutation_id: "mut-a",
  roll_key: {},
});
const supersession = traceLine(3, 3, {
  record_type: "supersession",
  holder_id: "npc-y",
  claim_id: "claim-a",
  loser_variant_id: "va-2",
  winner_variant_id: null,
  resolution_rule: "rule-x",
  confidence_dent: 0.15,
  teller_id: "npc-x",
  teller_belief_id: "belief-x",
  evidence_id: "ev-s",
  winner_belief_id: "belief-w",
});
const TRACE_CONTENT = transmit1 + transmit2 + mutationApplied + supersession;
const TRACE_TICK_OFFSETS = {
  "1": 0,
  "2": new TextEncoder().encode(transmit1).length,
  "3": new TextEncoder().encode(transmit1 + transmit2 + mutationApplied).length,
};

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "tree-test-run",
      seed_id: "s",
      created_wall_ts: 0,
      branches: [{ save_uuid: "s", generation: 0 }],
      tick_range: { start: 0, end: 3 },
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

async function mountAt(query: string) {
  stubFetch();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: VariantTreeScreen },
      { path: "/tree", component: VariantTreeScreen },
    ],
  });
  await router.push(query);
  const pinia = createPinia();
  const wrapper = mount(VariantTreeScreen, { global: { plugins: [router, pinia] } });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  return { wrapper, router, pinia };
}

describe("VariantTreeScreen.vue", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mounts and renders the tree SVG for the default (first) claim, claim-a, at t=3", async () => {
    const { wrapper } = await mountAt("/?run=tree-test-run&t=3");
    expect(wrapper.find("svg.tree-svg").exists()).toBe(true);
    // canonical + va-1 + va-2 = 3 nodes visible by t=3.
    expect(wrapper.findAll(".tree-svg__node")).toHaveLength(3);
  });

  it("the canonical root renders as a real node, never a phantom 'null' node, even though a supersession names it as winner", async () => {
    const { wrapper } = await mountAt("/?run=tree-test-run&t=3");
    const labels = wrapper.findAll(".tree-svg__node").map((n) => n.attributes("aria-label"));
    expect(labels.some((l) => l?.startsWith("canonical |"))).toBe(true);
    expect(labels.some((l) => l?.startsWith("null |"))).toBe(false);
    expect(wrapper.html()).not.toContain(">null<");
  });

  it("scrubbing t filters nodes/edges: va-2 is invisible before t=2, visible at t=2", async () => {
    const { wrapper, router } = await mountAt("/?run=tree-test-run&t=1");
    expect(wrapper.findAll(".tree-svg__node")).toHaveLength(2); // canonical + va-1 only

    await router.push("/?run=tree-test-run&t=2");
    await flushPromises();
    await flushPromises();
    expect(wrapper.findAll(".tree-svg__node")).toHaveLength(3); // + va-2
  });

  it("claim selector switches trees: claim-b has only the canonical node (no variants)", async () => {
    const { wrapper } = await mountAt("/?run=tree-test-run&t=3");
    expect(wrapper.findAll(".tree-svg__node")).toHaveLength(3);

    const select = wrapper.find(".tree-screen__claim select");
    await select.setValue("claim-b");
    await flushPromises();
    expect(wrapper.findAll(".tree-svg__node")).toHaveLength(1);
  });

  it("node click shows the right holder table", async () => {
    const { wrapper } = await mountAt("/?run=tree-test-run&t=2");
    const findNode = (label: string) => wrapper.findAll(".tree-svg__node").find((n) => n.attributes("aria-label")?.startsWith(`${label} |`));

    await findNode("va-1")!.trigger("click");
    await flushPromises();
    let panel = wrapper.find('[aria-label="holder table"]');
    expect(panel.text()).toContain("va-1");
    expect(panel.text()).toContain("npc-x");
    expect(panel.text()).not.toContain("npc-y");

    // Same filter, other direction: clicking va-2 must show npc-y and NOT npc-x.
    await findNode("va-2")!.trigger("click");
    await flushPromises();
    panel = wrapper.find('[aria-label="holder table"]');
    expect(panel.text()).toContain("va-2");
    expect(panel.text()).toContain("npc-y");
    expect(panel.text()).not.toContain("npc-x");
  });

  it("deep link ?view=tree&run=...&t=... lands on the tree screen with the right tick", async () => {
    const { wrapper } = await mountAt("/tree?run=tree-test-run&t=2");
    expect(wrapper.find("svg.tree-svg").exists()).toBe(true);
    expect(wrapper.findAll(".tree-svg__node")).toHaveLength(3);
  });

  it("shows a placeholder when no run is selected", async () => {
    const { wrapper } = await mountAt("/?");
    expect(wrapper.text()).toContain("no run loaded");
  });
});
