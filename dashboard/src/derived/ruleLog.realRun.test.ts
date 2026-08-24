import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { computeRuleHistogram, mapTraceRecordsToRuleLogRows } from "./ruleLog";
import type { FrameRecord } from "../log/types";

/**
 * `mapTraceRecordsToRuleLogRows`/`computeRuleHistogram` against the real
 * `runs/tier3-demo-01` demo run -- same "runs/ is gitignored, skip rather
 * than fail when absent" precedent as `socialDiff.realRun.test.ts`.
 *
 * FINDING (corrects the lane packet's own "Read first" claim, and a
 * dispatch-note miscount): `trace.jsonl`'s `rule_evaluated` records were
 * counted directly (`python3`, grouping by `payload.rule`/`payload.fired`)
 * rather than trusted from either secondhand description. The packet's
 * "Read first" item 2 says the run's `rule_evaluated` rows cover "all 16
 * live rules" -- false for this run's actual data: exactly 9 distinct
 * rule names appear, totalling 165 records. Separately, the dispatch
 * note's per-rule numbers for `tell-decision-policy` (102) and
 * `accumulation-threshold` (13) do not match this run's file either (they
 * sum to 210, not the dataset's real 165) -- the real counts below are
 * `tell-decision-policy`: 58 (44 fired / 14 not), `accumulation-threshold`:
 * 12 (1 fired / 11 not). Every other rule's count in the dispatch note
 * checked out exactly and is asserted below too. This test asserts the
 * counts actually present in the checked-out fixture, not either
 * secondhand figure.
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/tier3-demo-01");
const TRACE_FILE = path.join(RUN_DIR, "trace.jsonl");
const runExists = existsSync(TRACE_FILE);

function loadRecords(file: string): FrameRecord[] {
  return readFileSync(file, "utf8")
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

describe.skipIf(!runExists)("ruleLog against runs/tier3-demo-01 (real demo run)", () => {
  const allTrace = runExists ? loadRecords(TRACE_FILE) : [];
  const rows = mapTraceRecordsToRuleLogRows(allTrace);
  const histogram = computeRuleHistogram(rows);

  it("finds exactly 165 rule_evaluated records across 9 distinct rules", () => {
    expect(rows).toHaveLength(165);
    expect(histogram).toHaveLength(9);
  });

  it("matches the real per-rule fired/not-fired breakdown exactly", () => {
    const byRule = Object.fromEntries(histogram.map((b) => [b.rule, b]));
    expect(byRule).toEqual({
      "tell-decision-policy": { rule: "tell-decision-policy", fired: 44, notFired: 14, total: 58 },
      "encounter-sampling": { rule: "encounter-sampling", fired: 44, notFired: 0, total: 44 },
      "mutation-policy": { rule: "mutation-policy", fired: 0, notFired: 14, total: 14 },
      "testimony-transfer": { rule: "testimony-transfer", fired: 14, notFired: 0, total: 14 },
      "accumulation-threshold": { rule: "accumulation-threshold", fired: 1, notFired: 11, total: 12 },
      "witness-creates-belief": { rule: "witness-creates-belief", fired: 9, notFired: 0, total: 9 },
      "shared-claim-invariant": { rule: "shared-claim-invariant", fired: 9, notFired: 0, total: 9 },
      "reputation-evidence-accumulation": { rule: "reputation-evidence-accumulation", fired: 4, notFired: 0, total: 4 },
      "obligation-issue-fulfill-violate": { rule: "obligation-issue-fulfill-violate", fired: 1, notFired: 0, total: 1 },
    });
  });

  it("has at least one not-fired accumulation-threshold row with a visible, non-blank accumulator ratio", () => {
    const stuckRows = rows.filter((r) => r.rule === "accumulation-threshold" && !r.fired);
    expect(stuckRows.length).toBe(11);
    for (const row of stuckRows) {
      expect(row.resultSummary).toBe("not fired");
      expect(row.inputsSummary).not.toBe("—");
      expect(row.inputsSummary).toMatch(/^\d+\/\d+/); // count/threshold ratio leads the summary
    }
  });

  it("mutation-policy never fires in this run (all 14 evaluations are negative rows)", () => {
    const mutationRows = rows.filter((r) => r.rule === "mutation-policy");
    expect(mutationRows).toHaveLength(14);
    expect(mutationRows.every((r) => !r.fired)).toBe(true);
  });

  it("sorts the histogram by total evaluations descending, tell-decision-policy busiest", () => {
    expect(histogram[0]!.rule).toBe("tell-decision-policy");
    expect(histogram[0]!.total).toBe(58);
  });
});
