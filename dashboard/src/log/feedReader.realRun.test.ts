import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { mapTraceRecordToFeedRow } from "./feedReader";
import type { FrameRecord } from "./types";

/**
 * Verifies outcome mapping against the real demo run (packet's "Read
 * first" §4, the pre-dispatch review's independently-checked counts): 520
 * `encounter_rolled` (330 `encountered:false`, 190 `true`), 186
 * `nothing_salient`, 4 `transmitted`.
 *
 * `runs/` is gitignored (ui-spec §1.2) — this run may not exist in every
 * checkout/CI environment, so the suite degrades to skipped rather than
 * failing when it's absent, per the same "acceleration, not a required
 * input" spirit the rest of this reader follows.
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/whiterun-jarl-01");
const TRACE_FILE = path.join(RUN_DIR, "trace.jsonl");
const runExists = existsSync(TRACE_FILE);

function loadTraceRecords(): FrameRecord[] {
  const text = readFileSync(TRACE_FILE, "utf8");
  return text
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

describe.skipIf(!runExists)("mapTraceRecordToFeedRow against runs/whiterun-jarl-01 (real demo run)", () => {
  const records = runExists ? loadTraceRecords() : [];
  const rows = records.map(mapTraceRecordToFeedRow).filter((r) => r !== null);

  it("has the expected raw record counts (sanity check on the fixture itself)", () => {
    const encounterRolled = records.filter((r) => r.payload.record_type === "encounter_rolled");
    expect(encounterRolled).toHaveLength(520);
    expect(encounterRolled.filter((r) => r.payload.encountered === false)).toHaveLength(330);
    expect(records.filter((r) => r.payload.record_type === "nothing_salient")).toHaveLength(186);
    expect(records.filter((r) => r.payload.record_type === "transmitted")).toHaveLength(4);
  });

  it("maps exactly the encountered:false rolls to rolled_against rows", () => {
    expect(rows.filter((r) => r.outcome === "rolled_against")).toHaveLength(330);
  });

  it("maps every nothing_salient record to a nothing_salient row", () => {
    expect(rows.filter((r) => r.outcome === "nothing_salient")).toHaveLength(186);
  });

  it("maps every transmitted record to a transmitted row", () => {
    expect(rows.filter((r) => r.outcome === "transmitted")).toHaveLength(4);
  });

  it("elides every encountered:true roll (not its own outcome row)", () => {
    const positiveRolls = records.filter(
      (r) => r.payload.record_type === "encounter_rolled" && r.payload.encountered === true,
    );
    expect(positiveRolls).toHaveLength(190);
    for (const r of positiveRolls) {
      expect(mapTraceRecordToFeedRow(r)).toBeNull();
    }
  });

  it("contains the packet's own worked deep-link row: tick 7, nothing_salient, irileth/proventus", () => {
    const row = rows.find((r) => r.tick === 7 && r.outcome === "nothing_salient");
    expect(row).toBeDefined();
    expect(row?.participants).toEqual(["irileth", "proventus"]);
  });
});
