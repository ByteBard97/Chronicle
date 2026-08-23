import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { buildVariantTree, CANONICAL_NODE_ID, firstClaimId } from "./variantTree";
import { emptySocialState, fromKeyframeState, replayTo, type SocialState } from "../log/reconstruct";
import type { FrameRecord } from "../log/types";

/**
 * Verifies the tree model against the real demo run built for this lane
 * (lane 17's `runs/carrier-mutation-01`: 1 `mutation_applied`, 7
 * `supersession` records, 8 variants across 3 generations of one claim).
 * `runs/` is gitignored -- degrades to skipped rather than failing when
 * absent, matching `feedReader.realRun.test.ts`/`mapMarkers.realRun.test.ts`'s
 * precedent.
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

describe.skipIf(!runExists)("variant tree against runs/carrier-mutation-01 (real demo run)", () => {
  const allEvents = runExists ? loadRecords(EVENTS_FILE) : [];
  const allTrace = runExists ? loadRecords(TRACE_FILE) : [];

  it("the active claim is claim-market-murder (the run's first claim)", () => {
    const state = stateAt(allEvents, allTrace, 0);
    expect(firstClaimId(state)).toBe("claim-market-murder");
  });

  it("at t=200 (end of run), all 8 variants + canonical are visible with correct depths", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const tree = buildVariantTree(state, allTrace, "claim-market-murder", 200);
    const byId = Object.fromEntries(tree.nodes.map((n) => [n.id, n]));

    expect(Object.keys(byId).sort()).toEqual(
      [
        CANONICAL_NODE_ID,
        "variant-auto-1",
        "variant-auto-2",
        "variant-auto-3",
        "variant-auto-4",
        "variant-auto-12",
        "variant-auto-13",
        "variant-auto-14",
      ].sort(),
    );

    // variant-auto-1/-2/-4 are direct children of canonical (depth 1).
    expect(byId["variant-auto-1"]).toMatchObject({ depth: 1, parentId: CANONICAL_NODE_ID });
    expect(byId["variant-auto-2"]).toMatchObject({ depth: 1, parentId: CANONICAL_NODE_ID });
    expect(byId["variant-auto-4"]).toMatchObject({ depth: 1, parentId: CANONICAL_NODE_ID });
    // variant-auto-3 is a child of variant-auto-1 (depth 2); -12/-13 children of -3 (depth 3); -14 child of -13 (depth 4).
    expect(byId["variant-auto-3"]).toMatchObject({ depth: 2, parentId: "variant-auto-1" });
    expect(byId["variant-auto-12"]).toMatchObject({ depth: 3, parentId: "variant-auto-3" });
    expect(byId["variant-auto-13"]).toMatchObject({ depth: 3, parentId: "variant-auto-3" });
    expect(byId["variant-auto-14"]).toMatchObject({ depth: 4, parentId: "variant-auto-13" });
  });

  it("exactly the run's one mutation_applied labels its edge; every other edge is plain", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const tree = buildVariantTree(state, allTrace, "claim-market-murder", 200);
    const labeled = tree.edges.filter((e) => e.mutationId !== null);
    expect(labeled).toHaveLength(1);
    expect(labeled[0]).toMatchObject({
      toId: "variant-auto-4",
      fromId: CANONICAL_NODE_ID,
      mutationId: "mut-6f926caa6484",
      slot: "perpetrator",
      oldValue: "unknown",
      newValue: "a bandit chief",
    });
    expect(tree.edges.filter((e) => e.mutationId === null)).toHaveLength(tree.edges.length - 1);
  });

  it("all 7 supersessions render as cross-links, including the 2 with a null (canonical) winner", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const tree = buildVariantTree(state, allTrace, "claim-market-murder", 200);
    expect(tree.crossLinks).toHaveLength(7);
    const toCanonical = tree.crossLinks.filter((c) => c.toId === CANONICAL_NODE_ID);
    expect(toCanonical).toHaveLength(2);
    expect(toCanonical.every((c) => c.fromId === "variant-auto-4")).toBe(true);
    // No cross-link has a null loser in this dataset (packet's finding: one-sided toward the winner side here).
    expect(tree.crossLinks.some((c) => c.fromId === CANONICAL_NODE_ID)).toBe(false);
  });

  it("duplicate loser->winner pairs (variant-auto-1 -> variant-auto-4, twice) are grouped for fan-out", () => {
    const state = stateAt(allEvents, allTrace, 200);
    const tree = buildVariantTree(state, allTrace, "claim-market-murder", 200);
    const pair = tree.crossLinks.filter((c) => c.fromId === "variant-auto-1" && c.toId === "variant-auto-4");
    expect(pair).toHaveLength(2);
    expect(pair.map((c) => c.pairIndex).sort()).toEqual([0, 1]);
  });

  it("holder count at T=200 (well past the resolving keyframe) matches the log's real, fully-resolved semantics", () => {
    // At T=200 the nearest keyframe (tick 191) already bakes in every
    // supersession's resolved variant_id (the Python sim writes it, this
    // reader just reads it back) -- ysolda and relief_caravaneer both
    // eventually resolve onto the canonical (null) variant, so their
    // originating variants (-2 and -4) end up with 0 holders and canonical
    // ends up with 3 (belethor + ysolda + relief_caravaneer).
    const state = stateAt(allEvents, allTrace, 200);
    expect(state.beliefs.size).toBe(8);
    const tree = buildVariantTree(state, allTrace, "claim-market-murder", 200);
    const holderCounts = Object.fromEntries(tree.nodes.map((n) => [n.id, n.holderCount]));
    expect(holderCounts).toEqual({
      [CANONICAL_NODE_ID]: 3,
      "variant-auto-1": 1,
      "variant-auto-2": 0,
      "variant-auto-3": 1,
      "variant-auto-4": 0,
      "variant-auto-12": 1,
      "variant-auto-13": 1,
      "variant-auto-14": 1,
    });
  });

  it("holder count at T=30 (the intra-keyframe window before the resolving keyframe) shows the live reconstruct.ts gap", () => {
    // Keyframes are every 24 ticks (23, 47, ...); the supersession chain
    // fires at ticks 26-28, strictly between keyframe 23 and keyframe 47.
    // At T=30, state is keyframe-23 (pre-supersession) + a delta replay
    // that silently skips `supersession` (reconstruct.ts's do-not-touch
    // gap, see variantTree.ts's module header) -- so relief_caravaneer and
    // ysolda still show up on their pre-resolution variants (-4 and -2)
    // rather than the canonical root the log actually resolved them to by
    // tick 28. This module correctly reflects that stale state, per the
    // packet's literal "count state.beliefs" recipe.
    const state = stateAt(allEvents, allTrace, 30);
    expect(state.beliefs.size).toBe(5);
    const tree = buildVariantTree(state, allTrace, "claim-market-murder", 30);
    const holderCounts = Object.fromEntries(tree.nodes.map((n) => [n.id, n.holderCount]));
    expect(holderCounts).toEqual({
      [CANONICAL_NODE_ID]: 1, // belethor only -- ysolda/relief_caravaneer not yet folded onto canonical
      "variant-auto-1": 1, // carlotta
      "variant-auto-2": 1, // ysolda -- stale: the log resolves her off this variant by tick 28
      "variant-auto-3": 1, // caravaneer
      "variant-auto-4": 1, // relief_caravaneer -- stale: the log resolves him off this variant by tick 28
    });
  });

  it("layout is scrub-stable: shared nodes keep identical (depth, order) at t=96 and t=200", () => {
    const earlyState = stateAt(allEvents, allTrace, 96);
    const lateState = stateAt(allEvents, allTrace, 200);
    const early = buildVariantTree(earlyState, allTrace, "claim-market-murder", 96);
    const late = buildVariantTree(lateState, allTrace, "claim-market-murder", 200);
    const earlyById = Object.fromEntries(early.nodes.map((n) => [n.id, { depth: n.depth, order: n.order }]));
    const lateById = Object.fromEntries(late.nodes.map((n) => [n.id, { depth: n.depth, order: n.order }]));
    for (const id of Object.keys(earlyById)) {
      expect(lateById[id]).toEqual(earlyById[id]);
    }
  });

  it("as-of-T: at t=1, only canonical + variant-auto-1/-2 are visible (variant-auto-3 also appears at t=1)", () => {
    const state = stateAt(allEvents, allTrace, 1);
    const tree = buildVariantTree(state, allTrace, "claim-market-murder", 1);
    expect(new Set(tree.nodes.map((n) => n.id))).toEqual(
      new Set([CANONICAL_NODE_ID, "variant-auto-1", "variant-auto-2", "variant-auto-3"]),
    );
    expect(tree.crossLinks).toHaveLength(0); // first supersession fires at tick 26
  });
});
