import { describe, expect, it } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";
import {
  computeDivergenceList,
  extractRolls,
  findFirstDivergentRoll,
  rollIdentityKey,
} from "./runCompare";
import type { FrameRecord } from "../log/types";

function record(tick: number, seq: number, stream: "events" | "trace", payload: Record<string, unknown>): FrameRecord {
  return { schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream, seq, payload };
}

function roll(tick: number, seq: number, locationId: string, npcA: string, npcB: string, value: number, threshold: number): FrameRecord {
  return record(tick, seq, "trace", {
    record_type: "encounter_rolled",
    roll_key: { seed_id: "s", purpose: "encounter", tick, site: locationId, participants: [npcA, npcB], draw: 0 },
    value,
    threshold,
    outcome: value < threshold ? "encountered" : "missed",
    location_id: locationId,
    npc_a: npcA,
    npc_b: npcB,
    encountered: value < threshold,
  });
}

describe("extractRolls / rollIdentityKey", () => {
  it("extracts only encounter_rolled records and tolerates malformed ones", () => {
    const records: FrameRecord[] = [
      roll(1, 0, "market", "a", "b", 0.2, 0.5),
      record(2, 0, "trace", { record_type: "nothing_salient" }),
      record(3, 0, "trace", { record_type: "encounter_rolled", location_id: "market" }), // missing fields
    ];
    const rolls = extractRolls(records);
    expect(rolls).toHaveLength(1);
    expect(rolls[0]!.tick).toBe(1);
  });

  it("keys participants order-independently (frozenset semantics)", () => {
    const r1 = roll(5, 0, "market", "a", "b", 0.1, 0.5);
    const r2 = roll(5, 0, "market", "b", "a", 0.1, 0.5);
    expect(rollIdentityKey(extractRolls([r1])[0]!)).toBe(rollIdentityKey(extractRolls([r2])[0]!));
  });
});

describe("findFirstDivergentRoll", () => {
  it("identical runs -> no divergence found", () => {
    const recordsA: FrameRecord[] = [
      roll(0, 0, "market", "a", "b", 0.2, 0.5),
      roll(1, 0, "market", "a", "c", 0.6, 0.5),
    ];
    const recordsB: FrameRecord[] = [
      roll(0, 0, "market", "a", "b", 0.2, 0.5),
      roll(1, 0, "market", "a", "c", 0.6, 0.5),
    ];
    expect(findFirstDivergentRoll(recordsA, recordsB)).toBeNull();
  });

  it("one flipped roll -> found at exactly the right tick/key, earlier agreeing rolls don't false-positive", () => {
    const recordsA: FrameRecord[] = [
      roll(0, 0, "market", "a", "b", 0.2, 0.5), // agrees
      roll(1, 0, "tavern", "c", "d", 0.3, 0.5), // agrees
      roll(2, 0, "market", "a", "c", 0.4, 0.5), // will differ: threshold flips encountered
    ];
    const recordsB: FrameRecord[] = [
      roll(0, 0, "market", "a", "b", 0.2, 0.5),
      roll(1, 0, "tavern", "c", "d", 0.3, 0.5),
      roll(2, 0, "market", "a", "c", 0.4, 0.35), // same value, different threshold -> encountered flips
    ];
    const result = findFirstDivergentRoll(recordsA, recordsB);
    expect(result).not.toBeNull();
    expect(result!.tick).toBe(2);
    expect(result!.locationId).toBe("market");
    expect(result!.participants).toEqual(["a", "c"]);
    expect(result!.a.encountered).toBe(true); // 0.4 < 0.5
    expect(result!.b.encountered).toBe(false); // 0.4 < 0.35 is false
  });

  it("a key present on only one side is not treated as a divergence", () => {
    const recordsA: FrameRecord[] = [roll(0, 0, "market", "a", "b", 0.2, 0.5)];
    const recordsB: FrameRecord[] = [roll(0, 0, "market", "c", "d", 0.2, 0.5)]; // different pair, same tick/site
    expect(findFirstDivergentRoll(recordsA, recordsB)).toBeNull();
  });

  it("scans in tick order and returns the EARLIEST divergence, not just any", () => {
    const recordsA: FrameRecord[] = [
      roll(0, 0, "market", "a", "b", 0.1, 0.9), // will differ
      roll(1, 0, "market", "a", "c", 0.1, 0.9), // will also differ, later tick
    ];
    const recordsB: FrameRecord[] = [
      roll(0, 0, "market", "a", "b", 0.1, 0.05),
      roll(1, 0, "market", "a", "c", 0.1, 0.05),
    ];
    const result = findFirstDivergentRoll(recordsA, recordsB);
    expect(result?.tick).toBe(0);
  });
});

describe("computeDivergenceList", () => {
  function beliefFormed(tick: number, seq: number, holderId: string, beliefId: string, claimId: string): FrameRecord {
    return record(tick, seq, "trace", {
      record_type: "belief_formed",
      belief_id: beliefId,
      claim_id: claimId,
      holder_id: holderId,
      evidence_id: `ev-${beliefId}`,
      claim_kind: "theft",
      claim_slots: {},
      canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
    });
  }
  function corroborated(tick: number, seq: number, beliefId: string, confidenceAfter: number): FrameRecord {
    return record(tick, seq, "trace", { record_type: "belief_corroborated", belief_id: beliefId, confidence_after: confidenceAfter });
  }

  it("no divergence when both runs' beliefs match exactly", () => {
    const recordsA = [beliefFormed(0, 0, "npc-a", "belief-1", "claim-1")];
    const recordsB = [beliefFormed(0, 0, "npc-a", "belief-1", "claim-1")];
    expect(computeDivergenceList(recordsA, recordsB, 5)).toEqual([]);
  });

  it("ranks by first-divergence tick then blast radius", () => {
    // npc-a diverges at tick 5 (one belief differs); npc-b diverges
    // earlier, at tick 2, with two differing beliefs -- should rank first
    // despite npc-a's record coming first in the array.
    const recordsA = [
      beliefFormed(0, 0, "npc-a", "belief-a", "claim-a"),
      beliefFormed(0, 1, "npc-b", "belief-b1", "claim-b1"),
      beliefFormed(0, 2, "npc-b", "belief-b2", "claim-b2"),
      corroborated(5, 0, "belief-a", 0.9),
      corroborated(2, 0, "belief-b1", 0.9),
      corroborated(2, 1, "belief-b2", 0.9),
    ];
    const recordsB = [
      beliefFormed(0, 0, "npc-a", "belief-a", "claim-a"),
      beliefFormed(0, 1, "npc-b", "belief-b1", "claim-b1"),
      beliefFormed(0, 2, "npc-b", "belief-b2", "claim-b2"),
      // npc-a's corroboration is missing in run B -> confidence differs from tick 5 on.
      // npc-b's two corroborations are also missing in run B -> differs from tick 2 on.
    ];
    const list = computeDivergenceList(recordsA, recordsB, 10);
    expect(list.map((e) => e.npcId)).toEqual(["npc-b", "npc-a"]);
    expect(list[0]!.firstDivergenceTick).toBe(2);
    expect(list[0]!.blastRadius).toBe(2);
    expect(list[1]!.firstDivergenceTick).toBe(5);
    expect(list[1]!.blastRadius).toBe(1);
  });

  it("Δ signs: delta is b - a (positive means run B is higher)", () => {
    const recordsA = [beliefFormed(0, 0, "npc-a", "belief-1", "claim-1"), corroborated(1, 0, "belief-1", 0.3)];
    const recordsB = [beliefFormed(0, 0, "npc-a", "belief-1", "claim-1"), corroborated(1, 0, "belief-1", 0.9)];
    const list = computeDivergenceList(recordsA, recordsB, 5);
    expect(list).toHaveLength(1);
    // Values are decayed-at-T (elapsed since last_rehearsed=1, T=5), so
    // compare loosely -- what matters is the sign and rough magnitude.
    const row = list[0]!.deltas[0]!;
    expect(row.a).toBeCloseTo(0.3, 1);
    expect(row.b).toBeCloseTo(0.9, 1);
    expect(row.delta).toBeGreaterThan(0.5);
  });
});

// ---------------------------------------------------------------------------
// Real-fixture proof (scenarios/run_compare_fixture.py): two actual runs
// sharing seed_id "compare-fixture-demo", differing only in
// encounter_probability. Skips gracefully if the fixture hasn't been
// generated yet (`uv run python scenarios/run_compare_fixture.py`) rather
// than failing CI on a missing-file setup step.
const RUNS_DIR = resolve(__dirname, "../../../runs");
const FIXTURE_A = resolve(RUNS_DIR, "compare-fixture-a/trace.jsonl");
const FIXTURE_B = resolve(RUNS_DIR, "compare-fixture-b/trace.jsonl");
const hasFixture = existsSync(FIXTURE_A) && existsSync(FIXTURE_B);

function readJsonl(path: string): FrameRecord[] {
  return readFileSync(path, "utf-8")
    .split("\n")
    .filter((line) => line.trim().length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

describe.skipIf(!hasFixture)("findFirstDivergentRoll against the real compare-fixture-a/b runs", () => {
  it("finds a real divergence: same value, differing threshold/encountered, at a real tick", () => {
    const recordsA = readJsonl(FIXTURE_A);
    const recordsB = readJsonl(FIXTURE_B);
    const result = findFirstDivergentRoll(recordsA, recordsB);
    expect(result).not.toBeNull();
    expect(result!.a.value).toBeCloseTo(result!.b.value, 9); // roll_key-keyed RNG draw is identical
    expect(result!.a.threshold).not.toBeCloseTo(result!.b.threshold, 9); // encounter_probability differs
    expect(typeof result!.tick).toBe("number");
    expect(result!.tick).toBeGreaterThanOrEqual(0);
  });
});
