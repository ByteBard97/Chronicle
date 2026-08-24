import { describe, expect, it } from "vitest";
import { buildProvenance, collapseHops, type ProvenanceHop } from "./provenance";
import { emptySocialState, type SocialState } from "../log/reconstruct";
import type { FrameRecord, KeyframeBelief, KeyframeEvidence } from "../log/types";

function belief(overrides: Partial<KeyframeBelief> = {}): KeyframeBelief {
  return {
    id: "belief-x",
    holder_id: "npc-x",
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

function evidence(overrides: Partial<KeyframeEvidence> = {}): KeyframeEvidence {
  return {
    id: "ev-x",
    belief_id: "belief-x",
    evidence_type: "reported",
    source_id: "npc-y",
    predecessor_belief_id: null,
    gamets: 0,
    strength: 0.9,
    ...overrides,
  };
}

function trace(tick: number, payload: Record<string, unknown>, seq = 0): FrameRecord {
  return {
    schema_version: 1,
    seed_id: "seed",
    save_uuid: "save",
    generation: 0,
    tick,
    stream: "trace",
    seq,
    payload,
  };
}

function baseState(): SocialState {
  return emptySocialState(0);
}

describe("buildProvenance", () => {
  it("returns null for a belief that doesn't exist in state", () => {
    const state = baseState();
    expect(buildProvenance(state, [], "nope", 10)).toBeNull();
  });

  it("linear chain: belief -> retelling -> witness, in order, terminating at the witness", () => {
    const state = baseState();
    state.beliefs.set("belief-witness", belief({ id: "belief-witness", holder_id: "npc-a", confidence: 1.0, last_rehearsed: 0 }));
    state.beliefs.set("belief-hearer", belief({ id: "belief-hearer", holder_id: "npc-b", confidence: 0.8, last_rehearsed: 5 }));
    state.evidence.set("ev-witness", evidence({ id: "ev-witness", belief_id: "belief-witness", evidence_type: "witnessed", source_id: "npc-a", predecessor_belief_id: null, gamets: 0 }));
    state.evidence.set("ev-hearer", evidence({ id: "ev-hearer", belief_id: "belief-hearer", evidence_type: "reported", source_id: "npc-a", predecessor_belief_id: "belief-witness", gamets: 5 }));

    const result = buildProvenance(state, [], "belief-hearer", 10);
    expect(result).not.toBeNull();
    expect(result!.columns).toHaveLength(1);
    const column = result!.columns[0]!;
    expect(column.branch).toBeNull();
    expect(column.entries).toHaveLength(2);
    expect(column.entries[0]).toMatchObject({ kind: "hop", hop: { edgeId: "ev-hearer", isWitness: false } });
    expect(column.entries[1]).toMatchObject({ kind: "hop", hop: { edgeId: "ev-witness", isWitness: true } });
  });

  it("corroborated belief: two grounding evidence records render as two parallel columns, not a spanning-tree pick", () => {
    const state = baseState();
    state.beliefs.set("belief-target", belief({ id: "belief-target", holder_id: "npc-target" }));
    state.beliefs.set("belief-parent-a", belief({ id: "belief-parent-a", holder_id: "npc-a" }));
    state.beliefs.set("belief-parent-b", belief({ id: "belief-parent-b", holder_id: "npc-b" }));
    // Both parents are themselves witness termini.
    state.evidence.set("ev-a-witness", evidence({ id: "ev-a-witness", belief_id: "belief-parent-a", evidence_type: "witnessed", source_id: "npc-a", predecessor_belief_id: null, gamets: 0 }));
    state.evidence.set("ev-b-witness", evidence({ id: "ev-b-witness", belief_id: "belief-parent-b", evidence_type: "witnessed", source_id: "npc-b", predecessor_belief_id: null, gamets: 0 }));
    state.evidence.set("ev-1", evidence({ id: "ev-1", belief_id: "belief-target", source_id: "npc-a", predecessor_belief_id: "belief-parent-a", gamets: 3 }));
    state.evidence.set("ev-2", evidence({ id: "ev-2", belief_id: "belief-target", source_id: "npc-b", predecessor_belief_id: "belief-parent-b", gamets: 4 }));

    const result = buildProvenance(state, [], "belief-target", 10)!;
    expect(result.columns).toHaveLength(2);
    const edgeIds = result.columns.map((c) => c.id).sort();
    expect(edgeIds).toEqual(["ev-1", "ev-2"]);
    // Both parent witnesses actually render -- not a picked single chain.
    const witnessSourceIds = result.columns
      .flatMap((c) => c.entries)
      .filter((e): e is { kind: "hop"; hop: ProvenanceHop } => e.kind === "hop" && e.hop.isWitness)
      .map((e) => e.hop.sourceId)
      .sort();
    expect(witnessSourceIds).toEqual(["npc-a", "npc-b"]);
  });

  it("a belief with 2+ evidence reached mid-chain becomes a branch, not a flattened single column", () => {
    const state = baseState();
    state.beliefs.set("belief-target", belief({ id: "belief-target", holder_id: "npc-target" }));
    state.beliefs.set("belief-corroborated", belief({ id: "belief-corroborated", holder_id: "npc-mid" }));
    state.beliefs.set("belief-parent-a", belief({ id: "belief-parent-a", holder_id: "npc-a" }));
    state.beliefs.set("belief-parent-b", belief({ id: "belief-parent-b", holder_id: "npc-b" }));
    state.evidence.set("ev-a-witness", evidence({ id: "ev-a-witness", belief_id: "belief-parent-a", evidence_type: "witnessed", source_id: "npc-a", predecessor_belief_id: null, gamets: 0 }));
    state.evidence.set("ev-b-witness", evidence({ id: "ev-b-witness", belief_id: "belief-parent-b", evidence_type: "witnessed", source_id: "npc-b", predecessor_belief_id: null, gamets: 0 }));
    state.evidence.set("ev-mid-1", evidence({ id: "ev-mid-1", belief_id: "belief-corroborated", source_id: "npc-a", predecessor_belief_id: "belief-parent-a", gamets: 2 }));
    state.evidence.set("ev-mid-2", evidence({ id: "ev-mid-2", belief_id: "belief-corroborated", source_id: "npc-b", predecessor_belief_id: "belief-parent-b", gamets: 3 }));
    state.evidence.set("ev-target", evidence({ id: "ev-target", belief_id: "belief-target", source_id: "npc-mid", predecessor_belief_id: "belief-corroborated", gamets: 5 }));

    const result = buildProvenance(state, [], "belief-target", 10)!;
    expect(result.columns).toHaveLength(1);
    const column = result.columns[0]!;
    expect(column.branch).not.toBeNull();
    expect(column.branch!.beliefId).toBe("belief-corroborated");
    expect(column.branch!.columns).toHaveLength(2);
  });

  it("mutated hop: a belief whose variant_id matches a mutation_applied record renders an always-expanded mutation hop", () => {
    const state = baseState();
    state.beliefs.set("belief-witness", belief({ id: "belief-witness", holder_id: "npc-a" }));
    state.beliefs.set("belief-mutated", belief({ id: "belief-mutated", holder_id: "npc-b", variant_id: "variant-1" }));
    state.evidence.set("ev-witness", evidence({ id: "ev-witness", belief_id: "belief-witness", evidence_type: "witnessed", predecessor_belief_id: null, gamets: 0 }));
    state.evidence.set("ev-mutated", evidence({ id: "ev-mutated", belief_id: "belief-mutated", predecessor_belief_id: "belief-witness", gamets: 5 }));
    const traceRecords = [
      trace(5, {
        record_type: "transmitted",
        claim_id: "claim-1",
        evidence_id: "ev-mutated",
        teller_belief_id: "belief-witness",
        hearer_belief_id: "belief-mutated",
        variant: { variant_id: "variant-1", parent_variant_id: null, slots: {}, mutated_slot: "perpetrator" },
      }),
      trace(5, { record_type: "mutation_applied", claim_id: "claim-1", variant_id: "variant-1", mutation_id: "mut-1", slot: "perpetrator", old_value: "unknown", new_value: "a bandit chief" }),
    ];

    const result = buildProvenance(state, traceRecords, "belief-mutated", 10)!;
    const column = result.columns[0]!;
    const mutatedEntry = column.entries.find((e) => e.kind === "hop" && e.hop.edgeId === "ev-mutated");
    expect(mutatedEntry).toMatchObject({
      kind: "hop",
      hop: { mutation: { mutationId: "mut-1", slot: "perpetrator", oldValue: "unknown", newValue: "a bandit chief" } },
    });
  });

  it("mutation attribution is keyed to the specific transmitted evidence that introduced the variant, not the belief's (T-dependent) current variant_id -- a corroborating evidence record on the same belief must NOT also be flagged", () => {
    const state = baseState();
    state.beliefs.set("belief-witness-a", belief({ id: "belief-witness-a", holder_id: "npc-a" }));
    state.beliefs.set("belief-witness-b", belief({ id: "belief-witness-b", holder_id: "npc-b" }));
    // belief-target's variant_id happens to equal the mutated variant (as it
    // would after a transmission) -- a belief.variant_id-keyed lookup would
    // wrongly flag BOTH evidence records below as mutation hops.
    state.beliefs.set("belief-target", belief({ id: "belief-target", holder_id: "npc-target", variant_id: "variant-1" }));
    state.evidence.set("ev-witness-a", evidence({ id: "ev-witness-a", belief_id: "belief-witness-a", evidence_type: "witnessed", predecessor_belief_id: null, gamets: 0 }));
    state.evidence.set("ev-witness-b", evidence({ id: "ev-witness-b", belief_id: "belief-witness-b", evidence_type: "witnessed", predecessor_belief_id: null, gamets: 0 }));
    state.evidence.set("ev-transmitted", evidence({ id: "ev-transmitted", belief_id: "belief-target", predecessor_belief_id: "belief-witness-a", gamets: 5 }));
    state.evidence.set("ev-corroboration", evidence({ id: "ev-corroboration", belief_id: "belief-target", predecessor_belief_id: "belief-witness-b", gamets: 6 }));
    const traceRecords = [
      trace(5, {
        record_type: "transmitted",
        claim_id: "claim-1",
        evidence_id: "ev-transmitted",
        variant: { variant_id: "variant-1", parent_variant_id: null, slots: {}, mutated_slot: "perpetrator" },
      }),
      trace(5, { record_type: "mutation_applied", claim_id: "claim-1", variant_id: "variant-1", mutation_id: "mut-1", slot: "perpetrator", old_value: "unknown", new_value: "a bandit chief" }),
      trace(6, {
        record_type: "supersession",
        evidence_id: "ev-corroboration",
        winner_belief_id: "belief-target",
        resolution_rule: "r",
        confidence_dent: 0.1,
      }),
    ];

    const result = buildProvenance(state, traceRecords, "belief-target", 10)!;
    const byEdgeId = new Map(result.columns.map((c) => [c.id, (c.entries[0] as { kind: "hop"; hop: ProvenanceHop }).hop]));
    expect(byEdgeId.get("ev-transmitted")!.mutation).toEqual({ mutationId: "mut-1", slot: "perpetrator", oldValue: "unknown", newValue: "a bandit chief" });
    expect(byEdgeId.get("ev-corroboration")!.mutation).toBeNull();
  });

  it("superseded chain: an evidence id matching a supersession record renders grayed (supersession set) with the resolution as an interstitial fact", () => {
    const state = baseState();
    state.beliefs.set("belief-witness", belief({ id: "belief-witness", holder_id: "npc-teller" }));
    state.beliefs.set("belief-winner", belief({ id: "belief-winner", holder_id: "npc-holder" }));
    state.evidence.set("ev-witness", evidence({ id: "ev-witness", belief_id: "belief-witness", evidence_type: "witnessed", predecessor_belief_id: null, gamets: 0 }));
    state.evidence.set("ev-supersede", evidence({ id: "ev-supersede", belief_id: "belief-winner", source_id: "npc-teller", predecessor_belief_id: "belief-witness", gamets: 27 }));
    const traceRecords = [
      trace(27, {
        record_type: "supersession",
        holder_id: "npc-holder",
        teller_id: "npc-teller",
        teller_belief_id: "belief-witness",
        evidence_id: "ev-supersede",
        winner_belief_id: "belief-winner",
        resolution_rule: "evidence-type-ordering+v1",
        confidence_dent: 0.1,
      }),
    ];

    const result = buildProvenance(state, traceRecords, "belief-winner", 30)!;
    const column = result.columns[0]!;
    const supersededEntry = column.entries.find((e) => e.kind === "hop" && e.hop.edgeId === "ev-supersede");
    expect(supersededEntry).toMatchObject({
      kind: "hop",
      hop: { supersession: { resolutionRule: "evidence-type-ordering+v1", confidenceDent: 0.1 } },
    });
  });

  it("canonical-root termination: a belief with variant_id null and predecessor null renders as a one-hop witness column", () => {
    const state = baseState();
    state.beliefs.set("belief-root", belief({ id: "belief-root", holder_id: "npc-eyewitness", variant_id: null }));
    state.evidence.set("ev-root", evidence({ id: "ev-root", belief_id: "belief-root", evidence_type: "witnessed", source_id: "npc-eyewitness", predecessor_belief_id: null, gamets: 0 }));

    const result = buildProvenance(state, [], "belief-root", 10)!;
    expect(result.columns).toHaveLength(1);
    expect(result.columns[0]!.entries).toEqual([{ kind: "hop", hop: expect.objectContaining({ isWitness: true, edgeId: "ev-root" }) }]);
    expect(result.columns[0]!.branch).toBeNull();
  });
});

describe("collapseHops", () => {
  function hop(overrides: Partial<ProvenanceHop> = {}): ProvenanceHop {
    return {
      edgeId: "ev-x",
      beliefId: "belief-x",
      holderId: "npc-x",
      claimId: "claim-1",
      variantId: null,
      evidenceType: "reported",
      sourceId: "npc-y",
      tick: 0,
      location: null,
      confidence: 0.5,
      confidenceDelta: null,
      predecessorBeliefId: "belief-prev",
      isWitness: false,
      mutation: null,
      supersession: null,
      ...overrides,
    };
  }

  it("collapse counting: a run of 3 consecutive unchanged retellings collapses behind a count", () => {
    const hops = [hop({ edgeId: "ev-1" }), hop({ edgeId: "ev-2" }), hop({ edgeId: "ev-3" })];
    const entries = collapseHops(hops);
    expect(entries).toEqual([{ kind: "collapsed", count: 3, hops }]);
  });

  it("a single plain hop is not collapsed (nothing to collapse)", () => {
    const hops = [hop({ edgeId: "ev-1" })];
    expect(collapseHops(hops)).toEqual([{ kind: "hop", hop: hops[0] }]);
  });

  it("mutations, supersessions, and the witness terminus are always individually expanded, breaking a collapsible run", () => {
    const plain1 = hop({ edgeId: "ev-1" });
    const mutated = hop({ edgeId: "ev-2", mutation: { mutationId: "m1", slot: "s", oldValue: "a", newValue: "b" } });
    const plain2 = hop({ edgeId: "ev-3" });
    const superseded = hop({ edgeId: "ev-4", supersession: { resolutionRule: "r", confidenceDent: 0.1 } });
    const plain3 = hop({ edgeId: "ev-5" });
    const witness = hop({ edgeId: "ev-6", isWitness: true, predecessorBeliefId: null });

    const entries = collapseHops([plain1, mutated, plain2, superseded, plain3, witness]);
    expect(entries).toEqual([
      { kind: "hop", hop: plain1 },
      { kind: "hop", hop: mutated },
      { kind: "hop", hop: plain2 },
      { kind: "hop", hop: superseded },
      { kind: "hop", hop: plain3 },
      { kind: "hop", hop: witness },
    ]);
  });
});
