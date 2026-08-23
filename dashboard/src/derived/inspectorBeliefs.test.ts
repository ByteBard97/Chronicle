import { describe, expect, it } from "vitest";
import { beliefsForNpc } from "./inspectorBeliefs";
import { emptySocialState, type SocialState } from "../log/reconstruct";
import type { KeyframeBelief, KeyframeClaim, KeyframeRumorState, KeyframeVariant, KeyframeEvidence } from "../log/types";

const CLAIM: KeyframeClaim = {
  id: "claim-1",
  kind: "npc_death",
  slots: { perpetrator: "unknown", cause: "assassination", location: "whiterun_market" },
  canonical_event_key: { save_uuid: "s", generation: 0, seq: 0 },
  truth_status: "unconfirmed",
};

function belief(overrides: Partial<KeyframeBelief> = {}): KeyframeBelief {
  return {
    id: "belief-1",
    holder_id: "npc-a",
    claim_id: "claim-1",
    variant_id: null,
    confidence: 0.9,
    verbatim_strength: 0.9,
    gist_strength: 1.0,
    first_learned: 0,
    last_rehearsed: 0,
    ...overrides,
  };
}

function rumor(overrides: Partial<KeyframeRumorState> = {}): KeyframeRumorState {
  return {
    npc_id: "npc-a",
    claim_id: "claim-1",
    variant_id: null,
    stage: "heard",
    first_heard: 0,
    last_heard: 0,
    last_told: null,
    exposure_count: 1,
    distinct_source_count: 1,
    ...overrides,
  };
}

function baseState(): SocialState {
  const state = emptySocialState(0);
  state.claims.set(CLAIM.id, CLAIM);
  return state;
}

describe("beliefsForNpc", () => {
  it("returns an empty array for an NPC holding no beliefs", () => {
    const state = baseState();
    expect(beliefsForNpc(state, "npc-a", 10)).toEqual([]);
  });

  it("filters to only the requested holder_id", () => {
    const state = baseState();
    state.beliefs.set("belief-1", belief({ id: "belief-1", holder_id: "npc-a" }));
    state.beliefs.set("belief-2", belief({ id: "belief-2", holder_id: "npc-b" }));
    state.rumors.set("npc-a claim-1 ", rumor());
    state.rumors.set("npc-b claim-1 ", rumor({ npc_id: "npc-b" }));

    const result = beliefsForNpc(state, "npc-a", 10);
    expect(result).toHaveLength(1);
    expect(result[0].beliefId).toBe("belief-1");
  });

  it("synthesizes claim text from the claim's slots for an unvarianted belief", () => {
    const state = baseState();
    state.beliefs.set("belief-1", belief());
    state.rumors.set("npc-a claim-1 ", rumor());

    const [item] = beliefsForNpc(state, "npc-a", 0);
    expect(item.text).toBe("perpetrator: unknown, cause: assassination, location: whiterun_market");
    expect(item.variantLabel).toBeNull();
  });

  it("synthesizes claim text from the variant's (merged) slots, and a variant label from the mutated slot", () => {
    const state = baseState();
    const variant: KeyframeVariant = {
      id: "variant-1",
      claim_id: "claim-1",
      parent_variant_id: null,
      slots: { perpetrator: "a bandit chief", cause: "assassination", location: "whiterun_market" },
      mutated_slot: "perpetrator",
      gamets: 5,
    };
    state.variants.set(variant.id, variant);
    state.beliefs.set("belief-1", belief({ variant_id: "variant-1" }));
    state.rumors.set("npc-a claim-1 variant-1", rumor({ variant_id: "variant-1" }));

    const [item] = beliefsForNpc(state, "npc-a", 5);
    expect(item.text).toBe("perpetrator: a bandit chief, cause: assassination, location: whiterun_market");
    expect(item.variantLabel).toBe("perpetrator: a bandit chief");
  });

  it("falls back to a same-(npc,claim) rumor when the exact (npc,claim,variant) key misses -- the reconstruct.ts supersession-rekeying gap", () => {
    // Mirrors runs/carrier-mutation-01: a belief's variant_id resolved onto
    // canonical (null) by a supersession, but its only rumors entry is
    // still keyed under the pre-supersession variant it was transmitted on.
    const state = baseState();
    state.beliefs.set("belief-1", belief({ variant_id: null, last_rehearsed: 28 }));
    state.rumors.set(
      "npc-a claim-1 variant-old",
      rumor({ variant_id: "variant-old", stage: "repeated", last_heard: 28, last_told: 28 }),
    );

    const [item] = beliefsForNpc(state, "npc-a", 30);
    expect(item.stage).toBe("repeated");
  });

  it("is 'unheard' when no rumor exists at all for the (npc, claim) pair, exact or fallback", () => {
    const state = baseState();
    state.beliefs.set("belief-1", belief());
    // No rumors entry set at all.
    const [item] = beliefsForNpc(state, "npc-a", 10);
    expect(item.stage).toBe("unheard");
  });

  it("reports 'dormant' via decay once the rumor has gone quiet long enough (mirrors rumorStage.test.ts's thresholds)", () => {
    const state = baseState();
    state.beliefs.set("belief-1", belief({ last_rehearsed: 0 }));
    state.rumors.set("npc-a claim-1 ", rumor({ last_heard: 0 }));

    const [item] = beliefsForNpc(state, "npc-a", 2000); // past RUMOR_DORMANT_AFTER (1080)
    expect(item.stage).toBe("dormant");
  });

  it("reports decayed strengths at T, not the belief's raw stored values", () => {
    const state = baseState();
    state.beliefs.set("belief-1", belief({ confidence: 0.9, last_rehearsed: 0 }));
    state.rumors.set("npc-a claim-1 ", rumor());

    const atZero = beliefsForNpc(state, "npc-a", 0)[0];
    const atLater = beliefsForNpc(state, "npc-a", 500)[0];
    expect(atZero.confidence).toBe(0.9);
    expect(atLater.confidence).toBeLessThan(atZero.confidence);
  });

  it("wires provenance from the belief's most recent grounding evidence (top-level facts only)", () => {
    const state = baseState();
    state.beliefs.set("belief-1", belief());
    state.rumors.set("npc-a claim-1 ", rumor());
    const older: KeyframeEvidence = {
      id: "ev-1",
      belief_id: "belief-1",
      evidence_type: "witnessed",
      source_id: "npc-a",
      predecessor_belief_id: null,
      gamets: 0,
      strength: 1,
    };
    const newer: KeyframeEvidence = {
      id: "ev-2",
      belief_id: "belief-1",
      evidence_type: "reported",
      source_id: "npc-c",
      predecessor_belief_id: "belief-0",
      gamets: 5,
      strength: 0.8,
    };
    state.evidence.set(older.id, older);
    state.evidence.set(newer.id, newer);

    const [item] = beliefsForNpc(state, "npc-a", 10);
    expect(item.provenance).toEqual({ evidenceType: "reported", sourceId: "npc-c", tick: 5 });
  });

  it("has null provenance when no evidence was folded in for this belief", () => {
    const state = baseState();
    state.beliefs.set("belief-1", belief());
    state.rumors.set("npc-a claim-1 ", rumor());

    const [item] = beliefsForNpc(state, "npc-a", 10);
    expect(item.provenance).toBeNull();
  });
});
