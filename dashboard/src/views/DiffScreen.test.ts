import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import DiffScreen from "./DiffScreen.vue";

/**
 * DiffScreen.test.ts -- VariantTreeScreen.test.ts's pattern (memory-
 * history router, fetch stubbed to serve a synthetic run, flushPromises).
 *
 * Fixture: an empty tick-0 keyframe (excluded from `mapData.eventRecords`
 * per its own contract -- present only for sidecar-index realism) plus
 * five distinct within-window trace records (tick 10 belief_formed, tick
 * 15 grudge_formed, tick 18 obligation_issued, tick 20 obligation_resolved,
 * tick 22 reputation_updated x2), each immediately followed by a matching
 * `rule_evaluated` row -- one instance of every delta type the packet
 * asks for, each carrying a real rule chip and event link, so a deep
 * link `?run=...&t=30` (T2 defaulting to 30-24=6) exercises the whole
 * (6, 30] window in one screen-level test. Every subject is BORN inside
 * the window (before = 0/baseline at T2) rather than pre-seeded via a
 * keyframe, matching the packet's own reconstruction recipe
 * (`replayTo(emptySocialState(-1), records, t)` -- a keyframe's `state`
 * is never read by `computeSocialDiff`) and sidestepping decay-direction
 * ambiguity for the belief row.
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

const beliefFormed = traceLine(10, 0, {
  record_type: "belief_formed",
  belief_id: "belief-x",
  claim_id: "claim-1",
  holder_id: "npc-a",
  evidence_id: "ev-1",
  claim_kind: "theft",
  claim_slots: {},
  canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
});
const beliefRule = traceLine(10, 1, {
  record_type: "rule_evaluated",
  rule: "test-rule-belief",
  inputs: { belief_id: "belief-x" },
  fired: true,
  result: null,
});
const obligationIssued = traceLine(11, 0, {
  record_type: "obligation_issued",
  id: "obligation-1",
  issuer_id: "npc-e",
  debtor_id: "npc-f",
  beneficiary_id: null,
  action: "repay",
  condition: null,
  deadline: null,
  status: "active",
  witnesses: [],
  sanctions: null,
  created_at: 11,
});
const reputationSeed = traceLine(12, 0, {
  record_type: "reputation_updated",
  observer_id: "npc-a",
  subject_id: "npc-b",
  context: "civic",
  kind: "witnessed",
  positive: true,
  alpha: 1.0,
  beta: 1.0,
  direct_count: 0,
  witness_count: 0,
  certified_count: 0,
  uncertainty: 0.5,
  last_updated: 12,
});
const grudgeFormed = traceLine(15, 0, {
  record_type: "grudge_formed",
  id: "grudge-1",
  holder_id: "npc-c",
  target_id: "npc-d",
  source_belief_id: "belief-x",
  grievance_type: "insult",
  severity: 0.7,
  emotional_strength: 1.0,
  evidentiary_strength: 0.6,
  last_rehearsed: 15,
  forgiveness_threshold: 0.3,
});
const grudgeRule = traceLine(15, 1, {
  record_type: "rule_evaluated",
  rule: "test-rule-grudge",
  inputs: { holder_id: "npc-c", target_id: "npc-d" },
  fired: true,
  result: { grudge_id: "grudge-1" },
});
const obligationResolved = traceLine(20, 0, { record_type: "obligation_resolved", obligation_id: "obligation-1", status: "fulfilled", gamets: 20, excuse: null });
const obligationRule = traceLine(20, 1, {
  record_type: "rule_evaluated",
  rule: "test-rule-obligation",
  inputs: { obligation_id: "obligation-1" },
  fired: true,
  result: null,
});
const reputationUpdated = traceLine(22, 0, {
  record_type: "reputation_updated",
  observer_id: "npc-a",
  subject_id: "npc-b",
  context: "civic",
  kind: "witnessed",
  positive: true,
  alpha: 3.0,
  beta: 1.0,
  direct_count: 1,
  witness_count: 0,
  certified_count: 0,
  uncertainty: 0.4,
  last_updated: 22,
});
const reputationRule = traceLine(22, 1, {
  record_type: "rule_evaluated",
  rule: "test-rule-reputation",
  inputs: { observer_id: "npc-a", subject_id: "npc-b", context: "civic" },
  fired: true,
  result: null,
});

const TRACE_CONTENT =
  beliefFormed + beliefRule + obligationIssued + reputationSeed + grudgeFormed + grudgeRule + obligationResolved + obligationRule + reputationUpdated + reputationRule;
const byteLen = (s: string) => new TextEncoder().encode(s).length;
const TRACE_TICK_OFFSETS = {
  "10": 0,
  "11": byteLen(beliefFormed + beliefRule),
  "12": byteLen(beliefFormed + beliefRule + obligationIssued),
  "15": byteLen(beliefFormed + beliefRule + obligationIssued + reputationSeed),
  "20": byteLen(beliefFormed + beliefRule + obligationIssued + reputationSeed + grudgeFormed + grudgeRule),
  "22": byteLen(beliefFormed + beliefRule + obligationIssued + reputationSeed + grudgeFormed + grudgeRule + obligationResolved + obligationRule),
};

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "diff-test-run",
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

async function mountAt(query: string) {
  stubFetch();
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: DiffScreen },
      { path: "/diff", component: DiffScreen },
    ],
  });
  await router.push(query);
  const pinia = createPinia();
  const wrapper = mount(DiffScreen, { global: { plugins: [router, pinia] } });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  return { wrapper, router };
}

describe("DiffScreen.vue", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("deep link ?run=...&t=30 lands with T2 defaulting to T1-24 (=6), and shows one row per delta type", async () => {
    const { wrapper } = await mountAt("/diff?run=diff-test-run&t=30");
    expect(wrapper.text()).toContain("as-of 30 vs 6");

    const rows = wrapper.findAll("tbody tr");
    // 4 real delta rows -- one belief, one grudge, one obligation, one reputation.
    expect(rows).toHaveLength(4);
    expect(wrapper.find('[data-type="belief"]').exists()).toBe(true);
    expect(wrapper.find('[data-type="grudge"]').exists()).toBe(true);
    expect(wrapper.find('[data-type="obligation"]').exists()).toBe(true);
    expect(wrapper.find('[data-type="reputation"]').exists()).toBe(true);
  });

  it("every row shows a signed delta, a rule chip, and a feed event link", async () => {
    const { wrapper } = await mountAt("/diff?run=diff-test-run&t=30");
    expect(wrapper.text()).toContain("test-rule-belief");
    expect(wrapper.text()).toContain("test-rule-grudge");
    expect(wrapper.text()).toContain("test-rule-obligation");
    expect(wrapper.text()).toContain("test-rule-reputation");

    const beliefRow = wrapper.find('[data-type="belief"]');
    expect(beliefRow.find(".diff-row__delta").text()).toMatch(/^\+/); // confidence went up

    const eventLink = beliefRow.find(".diff-row__event-link");
    expect(eventLink.exists()).toBe(true);
    expect(eventLink.attributes("href")).toBe("/feed?run=diff-test-run&t=10");
  });

  it("filters by type narrows to exactly one row", async () => {
    const { wrapper } = await mountAt('/diff?run=diff-test-run&t=30&filters={"type":"grudge"}');
    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(1);
    expect(wrapper.find('[data-type="grudge"]').exists()).toBe(true);
  });

  it("filters by npc narrows to the rows involving that npc", async () => {
    const { wrapper } = await mountAt('/diff?run=diff-test-run&t=30&filters={"npc":"npc-c"}');
    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(1);
    expect(wrapper.find('[data-type="grudge"]').exists()).toBe(true);
  });

  it("filters by rule narrows to the row that rule fired for", async () => {
    const { wrapper } = await mountAt('/diff?run=diff-test-run&t=30&filters={"rule":"test-rule-obligation"}');
    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(1);
    expect(wrapper.find('[data-type="obligation"]').exists()).toBe(true);
  });

  it("a T2 override in filters (deep-linkable) excludes an obligation transition that already happened by T2, while the later reputation move remains", async () => {
    // t2=21 sits strictly between the obligation's resolution (tick 20,
    // already "fulfilled" by t2) and the reputation update (tick 22,
    // still ahead of t2) -- obligations are discrete/undecayed, so the
    // obligation row disappears exactly (no decay-only residue the way a
    // belief/grudge row would show), proving the override really changed
    // the window, not just the display.
    const { wrapper } = await mountAt('/diff?run=diff-test-run&t=30&filters={"t2":"21"}');
    expect(wrapper.text()).toContain("as-of 30 vs 21");
    expect(wrapper.find('[data-type="obligation"]').exists()).toBe(false);
    expect(wrapper.find('[data-type="reputation"]').exists()).toBe(true);
  });

  it("a subject already present before T2 shows a decay-only row (no event/rule) instead of the record that first created it", async () => {
    // t2=15 is after the belief's formation (tick 10) -- the belief
    // already exists at T2, so its row (still present, per real decay)
    // must NOT link back to the tick-10 belief_formed record anymore.
    const { wrapper } = await mountAt('/diff?run=diff-test-run&t=30&filters={"t2":"15"}');
    const beliefRow = wrapper.find('[data-type="belief"]');
    expect(beliefRow.exists()).toBe(true);
    expect(beliefRow.find(".diff-row__event-link").exists()).toBe(false);
    expect(beliefRow.text()).toContain("decay only");
  });

  it("shows a placeholder when no run is selected", async () => {
    const { wrapper } = await mountAt("/diff?");
    expect(wrapper.text()).toContain("no run loaded");
  });
});
