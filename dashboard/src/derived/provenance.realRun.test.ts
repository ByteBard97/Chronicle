import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { buildProvenance, type ProvenanceHop } from "./provenance";
import { emptySocialState, fromKeyframeState, replayTo, type SocialState } from "../log/reconstruct";
import type { FrameRecord } from "../log/types";

/**
 * Verifies DAG-honesty and the superseded/grayed-chain case against the
 * real demo run (`runs/carrier-mutation-01`, lane 17): `belief-auto-
 * relief_caravaneer-4` has 5 grounding Evidence records (1 `transmitted`
 * original + 4 `supersession`-sourced corroborations, confirmed directly
 * against `trace.jsonl`) -- `chain_for`'s single-parent walk would show
 * only 1; this module must show all 5. `runs/` is gitignored -- degrades
 * to skipped rather than failing when absent, matching
 * `variantTree.realRun.test.ts`'s precedent.
 */
const RUN_DIR = path.resolve(process.cwd(), "../runs/carrier-mutation-01");
const EVENTS_FILE = path.join(RUN_DIR, "events.jsonl");
const TRACE_FILE = path.join(RUN_DIR, "trace.jsonl");
const runExists = existsSync(EVENTS_FILE) && existsSync(TRACE_FILE);

function loadRecords(file: string): FrameRecord[] {
  return readFileSync(file, "utf8")
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

function stateAt(allEvents: FrameRecord[], allTrace: FrameRecord[], atTick: number): SocialState {
  const keyframes = allEvents.filter((r) => r.payload.record_type === "keyframe" && r.tick <= atTick);
  const latestKeyframe = keyframes.length > 0 ? keyframes[keyframes.length - 1]! : null;
  const start = latestKeyframe ? fromKeyframeState(latestKeyframe.payload.state as never, latestKeyframe.tick) : emptySocialState(-1);
  const deltas = [...allEvents, ...allTrace].filter((r) => r.payload.record_type !== "keyframe" && r.tick > start.tick && r.tick <= atTick);
  return replayTo(start, deltas, atTick);
}

function hopsOf(entries: ReturnType<typeof buildProvenance>): ProvenanceHop[] {
  if (entries === null) return [];
  const out: ProvenanceHop[] = [];
  for (const column of entries.columns) {
    for (const entry of column.entries) {
      if (entry.kind === "hop") out.push(entry.hop);
      else out.push(...entry.hops);
    }
    if (column.branch !== null) {
      for (const sub of column.branch.columns) {
        for (const entry of sub.entries) {
          if (entry.kind === "hop") out.push(entry.hop);
          else out.push(...entry.hops);
        }
      }
    }
  }
  return out;
}

describe.skipIf(!runExists)("provenance against runs/carrier-mutation-01 (real demo run)", () => {
  const allEvents = runExists ? loadRecords(EVENTS_FILE) : [];
  const allTrace = runExists ? loadRecords(TRACE_FILE) : [];

  it("belief-auto-relief_caravaneer-4 (5 grounding evidence records) renders 5 parallel top-level columns, not chain_for's 1", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const result = buildProvenance(state, allTrace, "belief-auto-relief_caravaneer-4", 200);
    expect(result).not.toBeNull();
    expect(result!.columns).toHaveLength(5);
  });

  it("4 of those 5 columns start with a supersession-sourced (grayed) hop; exactly 1 starts with a plain transmitted hop", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const result = buildProvenance(state, allTrace, "belief-auto-relief_caravaneer-4", 200)!;
    const firstHops = result.columns.map((c) => c.entries[0]!).map((e) => (e.kind === "hop" ? e.hop : e.hops[0]!));
    const superseded = firstHops.filter((h) => h.supersession !== null);
    const plain = firstHops.filter((h) => h.supersession === null);
    expect(superseded).toHaveLength(4);
    expect(plain).toHaveLength(1);
  });

  it("a superseded hop carries the real resolution rule and confidence dent as its interstitial fact", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const result = buildProvenance(state, allTrace, "belief-auto-relief_caravaneer-4", 200)!;
    const hops = hopsOf(result);
    const superseded = hops.filter((h) => h.supersession !== null);
    expect(superseded.length).toBeGreaterThan(0);
    for (const hop of superseded) {
      expect(hop.supersession!.resolutionRule.length).toBeGreaterThan(0);
      expect(hop.supersession!.confidenceDent).toBeGreaterThan(0);
    }
  });

  it("mutation attribution is T-stable: exactly 1 hop is a mutation hop, at both T=26 (before the resolving supersessions land) and T=200 (long after)", () => {
    const stateEarly = stateAt(allEvents, allTrace, 26);
    const resultEarly = buildProvenance(stateEarly, allTrace, "belief-auto-relief_caravaneer-4", 26);
    const mutationCountEarly = resultEarly === null ? 0 : hopsOf(resultEarly).filter((h) => h.mutation !== null).length;
    expect(mutationCountEarly).toBe(1);

    const stateLate = stateAt(allEvents, allTrace, 200);
    const resultLate = buildProvenance(stateLate, allTrace, "belief-auto-relief_caravaneer-4", 200)!;
    const mutationCountLate = hopsOf(resultLate).filter((h) => h.mutation !== null).length;
    expect(mutationCountLate).toBe(1);
  });

  it("belief-auto-ysolda-2 (4 grounding evidence records) also renders all 4 parents, not a spanning-tree pick", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const result = buildProvenance(state, allTrace, "belief-auto-ysolda-2", 200);
    expect(result).not.toBeNull();
    expect(result!.columns).toHaveLength(4);
  });
});
