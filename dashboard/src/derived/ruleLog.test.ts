import { describe, expect, it } from "vitest";
import {
  computeRuleHistogram,
  filterRuleLogRows,
  mapTraceRecordToRuleLogRow,
  mapTraceRecordsToRuleLogRows,
  summarizeFields,
} from "./ruleLog";
import type { FrameRecord } from "../log/types";

function traceRecord(tick: number, seq: number, payload: Record<string, unknown>): FrameRecord {
  return { schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "trace", seq, payload };
}

describe("summarizeFields", () => {
  it("collapses a count/threshold pair into a leading N/M ratio", () => {
    expect(summarizeFields({ count: 1, threshold: 4 })).toBe("1/4");
  });

  it("keeps other fields alongside the ratio, comma-joined", () => {
    expect(summarizeFields({ holder_id: "belethor", count: 1, threshold: 4, latched: false })).toBe(
      "1/4, holder_id: belethor, latched: false",
    );
  });

  it("falls back to plain key: value pairs when there is no ratio pair", () => {
    expect(summarizeFields({ holder_id: "npc-a", target_id: "npc-b" })).toBe("holder_id: npc-a, target_id: npc-b");
  });

  it("returns an em-dash for an empty or missing object", () => {
    expect(summarizeFields({})).toBe("—");
    expect(summarizeFields(null)).toBe("—");
    expect(summarizeFields(undefined)).toBe("—");
  });

  it("summarizes arrays by length and nested objects opaquely", () => {
    expect(summarizeFields({ belief_ids: ["a", "b", "c"], nested: { x: 1 } })).toBe("belief_ids: [3], nested: {…}");
  });
});

describe("mapTraceRecordToRuleLogRow", () => {
  it("returns null for a non-rule_evaluated record", () => {
    expect(mapTraceRecordToRuleLogRow(traceRecord(1, 0, { record_type: "belief_formed" }))).toBeNull();
  });

  it("maps a fired row with its result summary", () => {
    const record = traceRecord(5, 2, {
      record_type: "rule_evaluated",
      rule: "witness-creates-belief",
      inputs: { witness_id: "npc-a" },
      fired: true,
      result: { belief_id: "belief-1" },
    });
    const row = mapTraceRecordToRuleLogRow(record);
    expect(row).not.toBeNull();
    expect(row).toMatchObject({
      key: "5:2",
      tick: 5,
      seq: 2,
      rule: "witness-creates-belief",
      fired: true,
      inputs: { witness_id: "npc-a" },
      result: { belief_id: "belief-1" },
      inputsSummary: "witness_id: npc-a",
      resultSummary: "belief_id: belief-1",
    });
  });

  it("maps a not-fired row: result stays null and the accumulator values from inputs are visible in the summary, not blank", () => {
    const record = traceRecord(0, 27, {
      record_type: "rule_evaluated",
      rule: "accumulation-threshold",
      inputs: {
        holder_id: "belethor",
        grievance_kind: "theft",
        count: 1,
        threshold: 4,
        latched: false,
        belief_ids: ["belief-merchant-theft-1"],
      },
      fired: false,
      result: null,
    });
    const row = mapTraceRecordToRuleLogRow(record);
    expect(row).not.toBeNull();
    expect(row!.fired).toBe(false);
    expect(row!.result).toBeNull();
    expect(row!.resultSummary).toBe("not fired");
    // The stuck-counter case (ui-spec §3.7's "3/4 thefts" pinned example):
    // the accumulator ratio must be visible in the inputs summary.
    expect(row!.inputsSummary).toBe("1/4, holder_id: belethor, grievance_kind: theft, latched: false, belief_ids: [1]");
    expect(row!.inputsSummary).not.toBe("—");
  });

  it("tolerates a non-string rule and a non-object inputs/result", () => {
    const record = traceRecord(1, 0, { record_type: "rule_evaluated", rule: 42, inputs: "oops", fired: true, result: "also-oops" });
    const row = mapTraceRecordToRuleLogRow(record);
    expect(row!.rule).toBe("(unknown rule)");
    expect(row!.inputs).toEqual({});
    expect(row!.result).toBeNull();
  });
});

describe("mapTraceRecordsToRuleLogRows", () => {
  it("skips non-rule_evaluated records and preserves stream order", () => {
    const records = [
      traceRecord(1, 0, { record_type: "belief_formed" }),
      traceRecord(1, 1, { record_type: "rule_evaluated", rule: "r1", inputs: {}, fired: true, result: {} }),
      traceRecord(2, 0, { record_type: "rule_evaluated", rule: "r2", inputs: {}, fired: false, result: null }),
    ];
    const rows = mapTraceRecordsToRuleLogRows(records);
    expect(rows.map((r) => r.rule)).toEqual(["r1", "r2"]);
  });
});

describe("filterRuleLogRows", () => {
  const rows = mapTraceRecordsToRuleLogRows([
    traceRecord(1, 0, { record_type: "rule_evaluated", rule: "r1", inputs: {}, fired: true, result: {} }),
    traceRecord(2, 0, { record_type: "rule_evaluated", rule: "r2", inputs: {}, fired: false, result: null }),
  ]);

  it("passes every row through when no rule filter is set", () => {
    expect(filterRuleLogRows(rows, {})).toHaveLength(2);
  });

  it("narrows to rows for exactly the filtered rule", () => {
    const filtered = filterRuleLogRows(rows, { rule: "r2" });
    expect(filtered).toHaveLength(1);
    expect(filtered[0]!.rule).toBe("r2");
  });
});

describe("computeRuleHistogram", () => {
  it("buckets fired vs. not-fired counts per rule (synthetic)", () => {
    const rows = mapTraceRecordsToRuleLogRows([
      traceRecord(0, 0, { record_type: "rule_evaluated", rule: "busy-rule", inputs: {}, fired: true, result: {} }),
      traceRecord(1, 0, { record_type: "rule_evaluated", rule: "busy-rule", inputs: {}, fired: true, result: {} }),
      traceRecord(2, 0, { record_type: "rule_evaluated", rule: "busy-rule", inputs: {}, fired: false, result: null }),
      traceRecord(3, 0, { record_type: "rule_evaluated", rule: "quiet-rule", inputs: {}, fired: false, result: null }),
    ]);
    const histogram = computeRuleHistogram(rows);
    expect(histogram).toEqual([
      { rule: "busy-rule", fired: 2, notFired: 1, total: 3 },
      { rule: "quiet-rule", fired: 0, notFired: 1, total: 1 },
    ]);
  });

  it("sorts by total evaluations descending, alphabetically on ties", () => {
    const rows = mapTraceRecordsToRuleLogRows([
      traceRecord(0, 0, { record_type: "rule_evaluated", rule: "b-rule", inputs: {}, fired: true, result: {} }),
      traceRecord(1, 0, { record_type: "rule_evaluated", rule: "a-rule", inputs: {}, fired: true, result: {} }),
    ]);
    const histogram = computeRuleHistogram(rows);
    expect(histogram.map((b) => b.rule)).toEqual(["a-rule", "b-rule"]);
  });

  it("returns an empty array for no rows", () => {
    expect(computeRuleHistogram([])).toEqual([]);
  });
});
