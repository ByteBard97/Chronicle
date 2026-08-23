import { describe, expect, it } from "vitest";
import { buildVariantTree, claimIds, firstClaimId, CANONICAL_NODE_ID } from "./variantTree";
import { emptySocialState, type SocialState } from "../log/reconstruct";
import type { FrameRecord, KeyframeBelief, KeyframeClaim, KeyframeVariant } from "../log/types";

function trace(tick: number, payload: Record<string, unknown>, seq = 0): FrameRecord {
  return { schema_version: 1, seed_id: "s", save_uuid: "s", generation: 0, tick, stream: "trace", seq, payload };
}

function claim(over: Partial<KeyframeClaim> & Pick<KeyframeClaim, "id">): KeyframeClaim {
  return {
    kind: "npc_death",
    slots: {},
    canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
    truth_status: "unconfirmed",
    ...over,
  };
}

function variant(over: Partial<KeyframeVariant> & Pick<KeyframeVariant, "id" | "claim_id" | "gamets">): KeyframeVariant {
  return {
    parent_variant_id: null,
    slots: {},
    mutated_slot: null,
    ...over,
  };
}

function belief(over: Partial<KeyframeBelief> & Pick<KeyframeBelief, "id" | "holder_id" | "claim_id">): KeyframeBelief {
  return {
    variant_id: null,
    confidence: 0.9,
    verbatim_strength: 1,
    gist_strength: 1,
    first_learned: 0,
    last_rehearsed: 0,
    ...over,
  };
}

/**
 * Synthetic lineage: a 3-generation tree under one claim.
 *   canonical -> v1 (plain transmission)
 *   v1 -> v2 (mutated: "perpetrator" unknown -> "a bandit", mut-1)
 *   v2 -> v3 (plain transmission, generation 2)
 * Plus a supersession pointing loser=v1, winner=canonical (winner end
 * null), and a second pointing loser=null (canonical), winner=v2 (loser
 * end null) -- both ends of "either end can be null" exercised.
 */
function buildState(): SocialState {
  const state = emptySocialState(300);
  state.claims.set("claim-1", claim({ id: "claim-1" }));
  state.variants.set("v1", variant({ id: "v1", claim_id: "claim-1", parent_variant_id: null, gamets: 5 }));
  state.variants.set(
    "v2",
    variant({ id: "v2", claim_id: "claim-1", parent_variant_id: "v1", mutated_slot: "perpetrator", gamets: 10 }),
  );
  state.variants.set("v3", variant({ id: "v3", claim_id: "claim-1", parent_variant_id: "v2", gamets: 20 }));
  state.beliefs.set("b-canon", belief({ id: "b-canon", holder_id: "witness", claim_id: "claim-1", variant_id: null }));
  state.beliefs.set("b-v1", belief({ id: "b-v1", holder_id: "holder-a", claim_id: "claim-1", variant_id: "v1" }));
  state.beliefs.set("b-v2-1", belief({ id: "b-v2-1", holder_id: "holder-b", claim_id: "claim-1", variant_id: "v2" }));
  state.beliefs.set("b-v2-2", belief({ id: "b-v2-2", holder_id: "holder-c", claim_id: "claim-1", variant_id: "v2" }));
  return state;
}

const TRACE_RECORDS: FrameRecord[] = [
  trace(
    10,
    {
      record_type: "mutation_applied",
      claim_id: "claim-1",
      parent_variant_id: "v1",
      variant_id: "v2",
      slot: "perpetrator",
      old_value: "unknown",
      new_value: "a bandit",
      mutation_id: "mut-1",
      roll_key: {},
    },
    100,
  ),
  trace(
    15,
    {
      record_type: "supersession",
      holder_id: "holder-a",
      claim_id: "claim-1",
      loser_variant_id: "v1",
      winner_variant_id: null,
      resolution_rule: "rule-a",
      confidence_dent: 0.2,
      teller_id: "t1",
      teller_belief_id: "b1",
      evidence_id: "e1",
      winner_belief_id: "b-canon",
    },
    200,
  ),
  trace(
    16,
    {
      record_type: "supersession",
      holder_id: "witness",
      claim_id: "claim-1",
      loser_variant_id: null,
      winner_variant_id: "v2",
      resolution_rule: "rule-b",
      confidence_dent: 0.1,
      teller_id: "t2",
      teller_belief_id: "b2",
      evidence_id: "e2",
      winner_belief_id: "b-v2-1",
    },
    201,
  ),
];

describe("buildVariantTree (synthetic, multi-generation)", () => {
  it("builds a canonical root + one node per visible variant, with correct depths", () => {
    const tree = buildVariantTree(buildState(), TRACE_RECORDS, "claim-1", 300);
    const byId = Object.fromEntries(tree.nodes.map((n) => [n.id, n]));
    expect(byId[CANONICAL_NODE_ID]).toMatchObject({ isCanonical: true, depth: 0, variantId: null });
    expect(byId.v1).toMatchObject({ depth: 1, parentId: CANONICAL_NODE_ID });
    expect(byId.v2).toMatchObject({ depth: 2, parentId: "v1", mutatedSlot: "perpetrator" });
    expect(byId.v3).toMatchObject({ depth: 3, parentId: "v2" });
  });

  it("orders nodes deterministically by first-appearance gamets, canonical first", () => {
    const tree = buildVariantTree(buildState(), TRACE_RECORDS, "claim-1", 300);
    const byId = Object.fromEntries(tree.nodes.map((n) => [n.id, n]));
    expect(byId[CANONICAL_NODE_ID]!.order).toBe(0);
    expect(byId.v1!.order).toBeLessThan(byId.v2!.order);
    expect(byId.v2!.order).toBeLessThan(byId.v3!.order);
  });

  it("ties in gamets break by variant id lexicographically", () => {
    const state = buildState();
    state.variants.set("v-b", variant({ id: "v-b", claim_id: "claim-1", parent_variant_id: null, gamets: 5 }));
    state.variants.set("v-a", variant({ id: "v-a", claim_id: "claim-1", parent_variant_id: null, gamets: 5 }));
    const tree = buildVariantTree(state, TRACE_RECORDS, "claim-1", 300);
    const byId = Object.fromEntries(tree.nodes.map((n) => [n.id, n]));
    // v1 also has gamets 5; v-a < v-b < v1 lexicographically.
    expect(byId["v-a"]!.order).toBeLessThan(byId["v-b"]!.order);
    expect(byId["v-b"]!.order).toBeLessThan(byId.v1!.order);
  });

  it("labels the mutated edge from mutation_applied; unmutated edges are plain", () => {
    const tree = buildVariantTree(buildState(), TRACE_RECORDS, "claim-1", 300);
    const edgeById = Object.fromEntries(tree.edges.map((e) => [e.toId, e]));
    expect(edgeById.v2).toMatchObject({
      fromId: "v1",
      mutationId: "mut-1",
      slot: "perpetrator",
      oldValue: "unknown",
      newValue: "a bandit",
    });
    expect(edgeById.v1).toMatchObject({ fromId: CANONICAL_NODE_ID, mutationId: null, slot: null });
    expect(edgeById.v3).toMatchObject({ fromId: "v2", mutationId: null });
  });

  it("cross-links: either end can be the canonical root, not just the loser", () => {
    const tree = buildVariantTree(buildState(), TRACE_RECORDS, "claim-1", 300);
    expect(tree.crossLinks).toHaveLength(2);
    const winnerIsCanonical = tree.crossLinks.find((c) => c.fromId === "v1" && c.toId === CANONICAL_NODE_ID);
    const loserIsCanonical = tree.crossLinks.find((c) => c.fromId === CANONICAL_NODE_ID && c.toId === "v2");
    expect(winnerIsCanonical).toMatchObject({ resolutionRule: "rule-a", confidenceDent: 0.2 });
    expect(loserIsCanonical).toMatchObject({ resolutionRule: "rule-b", confidenceDent: 0.1 });
  });

  it("contested-claim dent lands on the winner node named by the supersession record", () => {
    const tree = buildVariantTree(buildState(), TRACE_RECORDS, "claim-1", 300);
    const byId = Object.fromEntries(tree.nodes.map((n) => [n.id, n]));
    expect(byId[CANONICAL_NODE_ID]!.dents).toEqual([
      { tick: 15, resolutionRule: "rule-a", confidenceDent: 0.2, holderId: "holder-a" },
    ]);
    expect(byId.v2!.dents).toEqual([{ tick: 16, resolutionRule: "rule-b", confidenceDent: 0.1, holderId: "witness" }]);
  });

  it("holder count at T: state.beliefs grouped by variant_id, null -> canonical", () => {
    const tree = buildVariantTree(buildState(), TRACE_RECORDS, "claim-1", 300);
    const byId = Object.fromEntries(tree.nodes.map((n) => [n.id, n]));
    expect(byId[CANONICAL_NODE_ID]!.holderCount).toBe(1); // b-canon
    expect(byId.v1!.holderCount).toBe(1); // b-v1
    expect(byId.v2!.holderCount).toBe(2); // b-v2-1, b-v2-2
    expect(byId.v3!.holderCount).toBe(0);
  });

  it("as-of-T filtering: a variant/edge/cross-link is invisible before its originating record's tick/gamets", () => {
    // atTick=9: v2 (gamets 10) and v3 (gamets 20) not yet visible; neither supersession (ticks 15/16) fired yet.
    const tree = buildVariantTree(buildState(), TRACE_RECORDS, "claim-1", 9);
    const ids = tree.nodes.map((n) => n.id);
    expect(ids).toEqual([CANONICAL_NODE_ID, "v1"]);
    expect(tree.edges.map((e) => e.toId)).toEqual(["v1"]);
    expect(tree.crossLinks).toHaveLength(0);
  });

  it("layout is scrub-stable: shared nodes keep identical (depth, order) across different T", () => {
    const state = buildState();
    const early = buildVariantTree(state, TRACE_RECORDS, "claim-1", 10); // v1, v2 visible; v3 not yet
    const late = buildVariantTree(state, TRACE_RECORDS, "claim-1", 300); // everything visible
    const earlyById = Object.fromEntries(early.nodes.map((n) => [n.id, { depth: n.depth, order: n.order }]));
    const lateById = Object.fromEntries(late.nodes.map((n) => [n.id, { depth: n.depth, order: n.order }]));
    for (const id of Object.keys(earlyById)) {
      expect(lateById[id]).toEqual(earlyById[id]);
    }
  });

  it("duplicate (fromId, toId) cross-link pairs are grouped for fan-out rendering", () => {
    const state = buildState();
    const dupTrace: FrameRecord[] = [
      ...TRACE_RECORDS,
      trace(
        17,
        {
          record_type: "supersession",
          holder_id: "holder-x",
          claim_id: "claim-1",
          loser_variant_id: "v1",
          winner_variant_id: null,
          resolution_rule: "rule-a",
          confidence_dent: 0.2,
          teller_id: "t3",
          teller_belief_id: "b3",
          evidence_id: "e3",
          winner_belief_id: "b-canon",
        },
        202,
      ),
    ];
    const tree = buildVariantTree(state, dupTrace, "claim-1", 300);
    const pair = tree.crossLinks.filter((c) => c.fromId === "v1" && c.toId === CANONICAL_NODE_ID);
    expect(pair).toHaveLength(2);
    expect(pair.map((c) => c.pairIndex).sort()).toEqual([0, 1]);
    expect(pair.every((c) => c.pairCount === 2)).toBe(true);
  });

  it("claimIds / firstClaimId reflect SocialState.claims' insertion order", () => {
    const state = buildState();
    state.claims.set("claim-2", claim({ id: "claim-2" }));
    expect(claimIds(state)).toEqual(["claim-1", "claim-2"]);
    expect(firstClaimId(state)).toBe("claim-1");
  });

  it("firstClaimId is null for an empty state", () => {
    expect(firstClaimId(emptySocialState(0))).toBeNull();
  });
});
