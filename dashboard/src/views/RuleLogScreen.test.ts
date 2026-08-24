import { afterEach, describe, expect, it, vi } from "vitest";
import { createRouter, createMemoryHistory } from "vue-router";
import { createPinia } from "pinia";
import { mount, flushPromises } from "@vue/test-utils";
import RuleLogScreen from "./RuleLogScreen.vue";

/**
 * RuleLogScreen.test.ts -- DiffScreen.test.ts's pattern (memory-history
 * router, fetch stubbed to serve a synthetic run, flushPromises).
 *
 * Fixture: a tick-0 empty keyframe (sidecar-index realism only, excluded
 * from `mapData.traceRecords`'s contract since it's on the events
 * stream) plus five `rule_evaluated` trace records covering both the
 * fired and evaluated-but-not-fired cases across two distinct rules --
 * enough to exercise the histogram's per-rule fired/not-fired split, the
 * rule filter/deep-link contract, and the not-fired accumulator display.
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

const r1 = traceLine(1, 0, {
  record_type: "rule_evaluated",
  rule: "accumulation-threshold",
  inputs: { holder_id: "belethor", grievance_kind: "theft", count: 3, threshold: 4, latched: false },
  fired: false,
  result: null,
});
const r2 = traceLine(2, 0, {
  record_type: "rule_evaluated",
  rule: "accumulation-threshold",
  inputs: { holder_id: "belethor", grievance_kind: "theft", count: 4, threshold: 4, latched: true },
  fired: true,
  result: { grudge_id: "grudge-1" },
});
const r3 = traceLine(3, 0, {
  record_type: "rule_evaluated",
  rule: "tell-decision-policy",
  inputs: { teller_id: "npc-a", hearer_id: "npc-b" },
  fired: true,
  result: { claim_id: "claim-1" },
});
const r4 = traceLine(4, 0, {
  record_type: "rule_evaluated",
  rule: "tell-decision-policy",
  inputs: { teller_id: "npc-c", hearer_id: "npc-d" },
  fired: false,
  result: null,
});
const r5 = traceLine(5, 0, {
  record_type: "rule_evaluated",
  rule: "tell-decision-policy",
  inputs: { teller_id: "npc-e", hearer_id: "npc-f" },
  fired: true,
  result: { claim_id: "claim-2" },
});

const TRACE_CONTENT = r1 + r2 + r3 + r4 + r5;
const byteLen = (s: string) => new TextEncoder().encode(s).length;
const TRACE_TICK_OFFSETS = {
  "1": 0,
  "2": byteLen(r1),
  "3": byteLen(r1 + r2),
  "4": byteLen(r1 + r2 + r3),
  "5": byteLen(r1 + r2 + r3 + r4),
};

const REGISTRY = {
  schema_version: 1,
  runs: [
    {
      run_id: "rulelog-test-run",
      seed_id: "s",
      created_wall_ts: 0,
      branches: [{ save_uuid: "s", generation: 0 }],
      tick_range: { start: 0, end: 5 },
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
      { path: "/", component: RuleLogScreen },
      { path: "/rules", component: RuleLogScreen },
    ],
  });
  await router.push(query);
  const pinia = createPinia();
  const wrapper = mount(RuleLogScreen, { global: { plugins: [router, pinia] } });
  await router.isReady();
  await flushPromises();
  await flushPromises();
  return { wrapper, router };
}

describe("RuleLogScreen.vue", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("deep link ?run=... shows every rule_evaluated row, fired and not, with equal visual weight", async () => {
    const { wrapper } = await mountAt("/rules?run=rulelog-test-run");
    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(5);
    expect(wrapper.text()).toContain("5 of 5 evaluations");
  });

  it("a not-fired row shows its accumulator values (count/threshold ratio) visibly, not blank", async () => {
    const { wrapper } = await mountAt("/rules?run=rulelog-test-run");
    const notFiredRow = wrapper.find('tr[data-fired="false"]');
    expect(notFiredRow.exists()).toBe(true);
    expect(notFiredRow.text()).toContain("3/4");
    expect(notFiredRow.text()).toContain("not fired");
  });

  it("the histogram shows fired vs. not-fired counts per rule", async () => {
    const { wrapper } = await mountAt("/rules?run=rulelog-test-run");
    expect(wrapper.text()).toContain("1 fired · 1 not · 2 total"); // accumulation-threshold
    expect(wrapper.text()).toContain("2 fired · 1 not · 3 total"); // tell-decision-policy
  });

  it("deep link ?filters={\"rule\":\"tell-decision-policy\"} lands pre-filtered to that rule's rows only", async () => {
    const { wrapper } = await mountAt('/rules?run=rulelog-test-run&filters={"rule":"tell-decision-policy"}');
    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(3);
    for (const row of rows) {
      expect(row.text()).toContain("tell-decision-policy");
    }
    expect(wrapper.text()).toContain("3 of 5 evaluations");
  });

  it("clicking a histogram bar sets the rule filter", async () => {
    const { wrapper } = await mountAt("/rules?run=rulelog-test-run");
    const bars = wrapper.findAll(".rule-histogram__row");
    const accumulationBar = bars.find((b) => b.text().includes("accumulation-threshold"));
    expect(accumulationBar).toBeDefined();
    await accumulationBar!.trigger("click");
    await flushPromises();
    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(2);
  });

  it("the rule filter dropdown narrows the table", async () => {
    const { wrapper } = await mountAt("/rules?run=rulelog-test-run");
    const select = wrapper.find(".rule-filter-bar__field select");
    await select.setValue("accumulation-threshold");
    await flushPromises();
    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(2);
  });

  it("shows a placeholder when no run is selected", async () => {
    const { wrapper } = await mountAt("/rules?");
    expect(wrapper.text()).toContain("no run loaded");
  });

  it("a rule-chip-shaped deep link (filters only, no run) still lands pre-filtered once a run is selected -- mirrors the real cross-lane flow (a full-page navigation drops run context; picking the run afterward keeps the filter)", async () => {
    const { wrapper } = await mountAt('/rules?filters={"rule":"tell-decision-policy"}');
    expect(wrapper.text()).toContain("no run loaded");
    const select = wrapper.find("#run-picker");
    await select.setValue("rulelog-test-run");
    await flushPromises();
    await flushPromises();
    const rows = wrapper.findAll("tbody tr");
    expect(rows).toHaveLength(3);
    for (const row of rows) {
      expect(row.text()).toContain("tell-decision-policy");
    }
  });
});
