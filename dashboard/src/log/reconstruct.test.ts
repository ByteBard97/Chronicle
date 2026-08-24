import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  applyTraceRecord,
  emptySocialState,
  fromKeyframeState,
  grudgeKey,
  replayTo,
  reputationKey,
  rumorKey,
  type SocialState,
} from "./reconstruct";
import type { FrameRecord, KeyframeBelief } from "./types";
import {
  RETELL_CONFIDENCE_DECAY,
  RETELL_GIST_DECAY,
  RETELL_VERBATIM_DECAY,
  WITNESS_CONFIDENCE,
} from "../derived/constants";

// process.cwd() is the vitest root (dashboard/, per vitest.config.ts) --
// more robust across environments than import.meta.url, which vitest's
// module transform does not always resolve to a real file:// URL.
const FIXTURE_DIR = path.resolve(process.cwd(), "public/runs/mock-t0");

function loadJsonl(filename: string): FrameRecord[] {
  const text = readFileSync(path.join(FIXTURE_DIR, filename), "utf8");
  return text
    .split("\n")
    .filter((line) => line.length > 0)
    .map((line) => JSON.parse(line) as FrameRecord);
}

const events = loadJsonl("events.jsonl");
const trace = loadJsonl("trace.jsonl");
const allRecords = [...events, ...trace];

describe("reconstruct: mock-t0 fixture", () => {
  it("replays from empty state (no keyframe before tick 3) through every Tier-0/1 record type", () => {
    const before = allRecords.filter((r) => r.tick <= 3 && r.payload.record_type !== "keyframe");
    const state = replayTo(emptySocialState(0), before, 3);

    // T0: belief_formed -- npc-guard witnesses the claim directly. (By
    // T=3 T6's belief_corroborated has already raised bel-1's confidence
    // to 0.97 -- checked separately below; WITNESS_CONFIDENCE is its
    // value only immediately after T0, before that later record applies.)
    expect(state.claims.get("claim-jarl-death")).toBeDefined();
    expect(state.beliefs.get("bel-1")).toMatchObject({ holder_id: "npc-guard" });

    // T2: transmitted at tick 1 -- hand-computed expectation. The teller's
    // belief (bel-1) contributes its RAW, undecayed confidence/verbatim/gist
    // here -- confirmed against `chronicle/claims.py`'s `retell()` (and
    // `resolve()`'s adoption branch), and against every `driver.py` call
    // site, none of which decay a belief before passing it to retell()/
    // resolve(). `reconstruct.ts` used to decay the teller belief first
    // (a divergence filed as a finding at lane 27, fixed at the source once
    // the blast radius was confirmed to be exactly these two tests).
    const expectedBel2Confidence = WITNESS_CONFIDENCE * RETELL_CONFIDENCE_DECAY;
    const expectedBel2Verbatim = 1.0 * RETELL_VERBATIM_DECAY;
    const expectedBel2Gist = 1.0 * RETELL_GIST_DECAY;

    const bel2 = state.beliefs.get("bel-2");
    expect(bel2).toBeDefined();
    expect(bel2!.confidence).toBeCloseTo(expectedBel2Confidence, 12);
    expect(bel2!.verbatim_strength).toBeCloseTo(expectedBel2Verbatim, 12);
    expect(bel2!.gist_strength).toBeCloseTo(expectedBel2Gist, 12);
    expect(bel2!.variant_id).toBe("var-1");

    // T3/T4: negative rows (encountered:false, nothing_salient) parse without
    // throwing and have no state effect -- both trace record types exist in
    // the fixture precisely to exercise this.
    expect(state.beliefs.size).toBe(3); // bel-1, bel-2, bel-4 (npc-smith's independent witness at T5... wait T5 is tick 3)

    // T6: belief_corroborated applied directly from the record's own fields.
    expect(state.beliefs.get("bel-1")?.confidence).toBe(0.97);
    expect(state.beliefs.get("bel-1")?.last_rehearsed).toBe(3);

    // Rumor stage: npc-guard has told the story (T2) -- "repeated".
    expect(state.rumors.get(rumorKey("npc-guard", "claim-jarl-death", null))?.stage).toBe("repeated");
    // npc-baker has only heard it so far -- "heard".
    expect(state.rumors.get(rumorKey("npc-baker", "claim-jarl-death", "var-1"))?.stage).toBe("heard");
  });

  it("reconstructs at T=96 from the tick-24 keyframe plus the one post-keyframe delta, matching a hand-computed expectation", () => {
    const keyframeRecord = events.find((r) => r.payload.record_type === "keyframe");
    expect(keyframeRecord).toBeDefined();
    const keyframeState = fromKeyframeState(keyframeRecord!.payload.state as never, keyframeRecord!.tick);

    // Sanity: the keyframe's own authored bel-2, before any post-keyframe replay.
    expect(keyframeState.beliefs.get("bel-2")).toMatchObject({ confidence: 0.6, last_rehearsed: 24 });

    const deltas = allRecords.filter((r) => r.tick > 24 && r.tick <= 96 && r.payload.record_type !== "keyframe");
    expect(deltas).toHaveLength(1); // the tick-96 transmitted record (T7)

    const state = replayTo(keyframeState, deltas, 96);

    // Hand-computed expectation for bel-3 (npc-farmer): teller (bel-2,
    // confidence 0.6 / verbatim 0.6 / gist 0.9 per the keyframe) contributes
    // its RAW, undecayed strengths -- see the T2 test above for why (lane-27
    // finding, fixed at the source). Elapsed time since bel-2's last
    // rehearsal (72 ticks) is irrelevant to this formula; it would only
    // matter for a since-abandoned pre-decay step.
    const expectedConfidence = 0.6 * RETELL_CONFIDENCE_DECAY;
    const expectedVerbatim = 0.6 * RETELL_VERBATIM_DECAY;
    const expectedGist = 0.9 * RETELL_GIST_DECAY;

    const bel3 = state.beliefs.get("bel-3");
    expect(bel3).toBeDefined();
    expect(bel3!.holder_id).toBe("npc-farmer");
    expect(bel3!.confidence).toBeCloseTo(expectedConfidence, 12);
    expect(bel3!.verbatim_strength).toBeCloseTo(expectedVerbatim, 12);
    expect(bel3!.gist_strength).toBeCloseTo(expectedGist, 12);

    // The mutation: var-2 carries the mutated "cause" slot, linked to var-1.
    const var2 = state.variants.get("var-2");
    expect(var2).toMatchObject({ parent_variant_id: "var-1", mutated_slot: "cause" });
    expect(var2!.slots.cause).toBe("illness");

    // The keyframe's own bel-1/npc-guard state is carried through untouched
    // (no post-keyframe record mentions it).
    expect(state.beliefs.get("bel-1")).toEqual(keyframeState.beliefs.get("bel-1"));
  });

  it("tolerates the fixture's own unknown keyframe key ('roles', a Tier-5-shaped addition) without erroring", () => {
    const keyframeRecord = events.find((r) => r.payload.record_type === "keyframe");
    expect((keyframeRecord!.payload as { roles?: unknown[] }).roles).toEqual([]);
    // fromKeyframeState only reads the keys its type declares; 'roles' at
    // the payload level (sibling to 'state') is simply never looked at --
    // proving skip-and-continue doesn't require an explicit exclusion list.
    expect(() => fromKeyframeState(keyframeRecord!.payload.state as never, keyframeRecord!.tick)).not.toThrow();
  });
});

describe("reconstruct: supersession (lane 27)", () => {
  function seedBelief(state: SocialState, id: string, overrides: Partial<KeyframeBelief>) {
    state.beliefs.set(id, {
      id,
      holder_id: "holder",
      claim_id: "claim-x",
      variant_id: null,
      confidence: 1,
      verbatim_strength: 1,
      gist_strength: 1,
      first_learned: 0,
      last_rehearsed: 0,
      ...overrides,
    });
  }

  it("adoption branch: the incumbent was on the loser's variant -- re-points to the winner's variant using the TELLER's raw confidence (claims.py's retell()/resolve() convention: no pre-decay)", () => {
    const state = emptySocialState(0);
    seedBelief(state, "incumbent-belief", { holder_id: "holder", variant_id: "var-loser", confidence: 0.5, last_rehearsed: 0 });
    seedBelief(state, "teller-belief", { holder_id: "teller", variant_id: "var-winner", confidence: 0.8, verbatim_strength: 0.9, gist_strength: 0.95, last_rehearsed: 10 });

    applyTraceRecord(
      state,
      {
        record_type: "supersession",
        holder_id: "holder",
        claim_id: "claim-x",
        loser_variant_id: "var-loser",
        winner_variant_id: "var-winner",
        resolution_rule: "evidence-type-ordering+v1",
        confidence_dent: 0.1,
        teller_id: "teller",
        teller_belief_id: "teller-belief",
        evidence_id: "ev-supersession-1",
        winner_belief_id: "incumbent-belief",
      },
      15,
    );

    const updated = state.beliefs.get("incumbent-belief");
    expect(updated).toBeDefined();
    expect(updated!.variant_id).toBe("var-winner");
    expect(updated!.confidence).toBeCloseTo(0.8 * RETELL_CONFIDENCE_DECAY * (1 - 0.1), 12);
    expect(updated!.verbatim_strength).toBeCloseTo(0.9 * RETELL_VERBATIM_DECAY, 12);
    expect(updated!.gist_strength).toBeCloseTo(0.95 * RETELL_GIST_DECAY, 12);
    expect(updated!.last_rehearsed).toBe(15);

    const evidence = state.evidence.get("ev-supersession-1");
    expect(evidence).toMatchObject({
      belief_id: "incumbent-belief",
      evidence_type: "reported",
      source_id: "teller",
      predecessor_belief_id: "teller-belief",
      gamets: 15,
      strength: 0.8, // teller's raw confidence, not the decayed/dented result
    });
  });

  it("repel branch: the incumbent already held the winning variant -- decays in place, then dents, variant unchanged", () => {
    const state = emptySocialState(0);
    seedBelief(state, "incumbent-belief", { holder_id: "holder", variant_id: "var-winner", confidence: 0.6, last_rehearsed: 0 });
    seedBelief(state, "teller-belief", { holder_id: "teller", variant_id: "var-loser", confidence: 0.4, last_rehearsed: 5 });

    applyTraceRecord(
      state,
      {
        record_type: "supersession",
        holder_id: "holder",
        claim_id: "claim-x",
        loser_variant_id: "var-loser",
        winner_variant_id: "var-winner",
        resolution_rule: "evidence-type-ordering+v1",
        confidence_dent: 0.1,
        teller_id: "teller",
        teller_belief_id: "teller-belief",
        evidence_id: "ev-supersession-2",
        winner_belief_id: "incumbent-belief",
      },
      20,
    );

    const updated = state.beliefs.get("incumbent-belief");
    const decayedConfidence = 0.6 * Math.pow(0.5, 20 / 168.0);
    expect(updated!.variant_id).toBe("var-winner"); // unchanged -- the challenge was repelled
    expect(updated!.confidence).toBeCloseTo(decayedConfidence * (1 - 0.1), 12);
    expect(updated!.last_rehearsed).toBe(20);

    // Evidence strength is still the teller's raw confidence, win or lose.
    expect(state.evidence.get("ev-supersession-2")).toMatchObject({ strength: 0.4 });
  });

  it("null winner_variant_id re-points the belief onto the canonical (un-varianted) root", () => {
    const state = emptySocialState(0);
    seedBelief(state, "incumbent-belief", { holder_id: "holder", variant_id: "var-loser", confidence: 0.5, last_rehearsed: 0 });
    seedBelief(state, "teller-belief", { holder_id: "teller", variant_id: null, confidence: 0.9, last_rehearsed: 0 });

    applyTraceRecord(
      state,
      {
        record_type: "supersession",
        holder_id: "holder",
        claim_id: "claim-x",
        loser_variant_id: "var-loser",
        winner_variant_id: null,
        resolution_rule: "evidence-type-ordering+v1",
        confidence_dent: 0.1,
        teller_id: "teller",
        teller_belief_id: "teller-belief",
        evidence_id: "ev-supersession-3",
        winner_belief_id: "incumbent-belief",
      },
      3,
    );

    expect(state.beliefs.get("incumbent-belief")?.variant_id).toBeNull();
  });

  it("reader tolerance: an unresolvable belief_id (winner or teller) skips without throwing or mutating state", () => {
    const state = emptySocialState(0);
    seedBelief(state, "teller-belief", { holder_id: "teller", variant_id: "var-winner", confidence: 0.7, last_rehearsed: 0 });
    const before = JSON.stringify([...state.beliefs.entries()]);

    expect(() =>
      applyTraceRecord(
        state,
        {
          record_type: "supersession",
          holder_id: "holder",
          claim_id: "claim-x",
          loser_variant_id: "var-loser",
          winner_variant_id: "var-winner",
          resolution_rule: "evidence-type-ordering+v1",
          confidence_dent: 0.1,
          teller_id: "teller",
          teller_belief_id: "teller-belief",
          evidence_id: "ev-supersession-4",
          winner_belief_id: "missing-belief", // never formed in this reader's view
        },
        3,
      ),
    ).not.toThrow();
    expect(JSON.stringify([...state.beliefs.entries()])).toBe(before);
    expect(state.evidence.has("ev-supersession-4")).toBe(false);
  });
});

describe("reconstruct: schema §7 tolerance against a fictional schema_version: 2", () => {
  it("skips an unrecognized record_type from a future schema version entirely (no throw, no state change)", () => {
    const state = emptySocialState(0);
    const before = JSON.stringify(state.beliefs);
    // A hypothetical Tier-6 "role_succeeded" record this reader has never
    // heard of, carrying a schema_version this document doesn't define yet.
    applyTraceRecord(
      state,
      { record_type: "role_succeeded", schema_version: 2, role_id: "jarl", old_holder: "npc-jarl", new_holder: "npc-heir" },
      0,
    );
    expect(JSON.stringify(state.beliefs)).toBe(before);
    expect(state.claims.size).toBe(0);
  });

  it("tolerates unknown payload fields on a known record type (additive-per-tier extension, schema §7)", () => {
    const state = emptySocialState(0);
    applyTraceRecord(
      state,
      {
        record_type: "belief_formed",
        belief_id: "bel-x",
        claim_id: "claim-x",
        holder_id: "npc-x",
        evidence_id: "ev-x",
        claim_kind: "npc_died",
        claim_slots: { npc_id: "npc-y" },
        canonical_event_key: { save_uuid: "s0", generation: 0, seq: 0 },
        // A hypothetical future field a schema_version: 2 reader would use;
        // this reader must still apply the record correctly, ignoring it.
        confidence_source_reliability: 0.42,
      },
      5,
    );
    expect(state.beliefs.get("bel-x")).toMatchObject({ holder_id: "npc-x", claim_id: "claim-x" });
  });

  it("ignores an events-stream payload with no record_type (an ordinary canonical event) without error", () => {
    const state = emptySocialState(0);
    expect(() =>
      applyTraceRecord(state, { event_type: "npc_died", gamets: 0, wall_ts: 0, origin: null }, 0),
    ).not.toThrow();
    expect(state.beliefs.size).toBe(0);
  });
});

describe("reconstruct: layer-4 social state (lane 34)", () => {
  it("relationship_formed inserts a relationship keyed by its own id, defaulting last_updated to formed_at when omitted", () => {
    const state = emptySocialState(0);
    applyTraceRecord(
      state,
      {
        record_type: "relationship_formed",
        id: "rel-keeper-player",
        from_id: "hulda",
        to_id: "player",
        basis: "kinship",
        basis_id: null,
        strength: 0.9,
        formed_at: 0,
        // last_updated deliberately omitted -- the trace record's real shape.
      },
      0,
    );
    expect(state.relationships.get("rel-keeper-player")).toMatchObject({
      from_id: "hulda",
      to_id: "player",
      basis: "kinship",
      strength: 0.9,
      formed_at: 0,
      last_updated: 0,
    });
  });

  it("grudge_formed inserts keyed by the composite (holder_id, target_id) pair, not by id", () => {
    const state = emptySocialState(0);
    applyTraceRecord(
      state,
      {
        record_type: "grudge_formed",
        id: "grudge-1",
        holder_id: "adrianne",
        target_id: "ulfberth",
        source_belief_id: "obl-favor-2",
        grievance_type: "obligation_violated",
        severity: 0.8,
        emotional_strength: 1,
        evidentiary_strength: 0.6,
        last_rehearsed: 2,
        forgiveness_threshold: 0.2,
      },
      2,
    );
    const key = grudgeKey("adrianne", "ulfberth");
    expect(state.grudges.get(key)).toMatchObject({ id: "grudge-1", holder_id: "adrianne", target_id: "ulfberth" });
    expect(state.grudges.size).toBe(1);
  });

  it("grudge_formed applies the record's OWN last_rehearsed field rather than substituting the envelope tick (lane-27 'apply the recorded outcome' idiom)", () => {
    const state = emptySocialState(0);
    applyTraceRecord(
      state,
      {
        record_type: "grudge_formed",
        id: "grudge-1",
        holder_id: "a",
        target_id: "b",
        source_belief_id: "bel-x",
        grievance_type: "insult",
        severity: 0.5,
        emotional_strength: 0.5,
        evidentiary_strength: 0.5,
        last_rehearsed: 7, // deliberately different from the envelope tick (12) below
        forgiveness_threshold: 0.2,
      },
      12,
    );
    const key = grudgeKey("a", "b");
    expect(state.grudges.get(key)?.last_rehearsed).toBe(7);
  });

  it("a second grudge_formed for the same holder/target pair (different id) overwrites by composite key -- proves upsert-by-pair semantics", () => {
    const state = emptySocialState(0);
    applyTraceRecord(
      state,
      {
        record_type: "grudge_formed",
        id: "grudge-1",
        holder_id: "adrianne",
        target_id: "ulfberth",
        source_belief_id: "obl-favor-2",
        grievance_type: "obligation_violated",
        severity: 0.8,
        emotional_strength: 1,
        evidentiary_strength: 0.6,
        last_rehearsed: 2,
        forgiveness_threshold: 0.2,
      },
      2,
    );
    applyTraceRecord(
      state,
      {
        record_type: "grudge_formed",
        id: "grudge-2", // different id, same pair
        holder_id: "adrianne",
        target_id: "ulfberth",
        source_belief_id: "obl-favor-3",
        grievance_type: "insult",
        severity: 0.5,
        emotional_strength: 0.7,
        evidentiary_strength: 0.9,
        last_rehearsed: 5,
        forgiveness_threshold: 0.1,
      },
      5,
    );
    expect(state.grudges.size).toBe(1);
    const key = grudgeKey("adrianne", "ulfberth");
    expect(state.grudges.get(key)).toMatchObject({ id: "grudge-2", grievance_type: "insult", severity: 0.5 });
  });

  it("obligation_issued inserts with excuse null and no fulfilled_at/violated_at; obligation_resolved then transitions status (fulfilled path)", () => {
    const state = emptySocialState(0);
    applyTraceRecord(
      state,
      {
        record_type: "obligation_issued",
        id: "obl-favor-1",
        issuer_id: "adrianne",
        debtor_id: "ulfberth",
        beneficiary_id: null,
        action: "return the borrowed steel",
        condition: null,
        deadline: null,
        status: "active",
        witnesses: [],
        sanctions: null,
        created_at: 0,
      },
      0,
    );
    expect(state.obligations.get("obl-favor-1")).toMatchObject({
      status: "active",
      excuse: null,
      fulfilled_at: null,
      violated_at: null,
      witnesses: [],
    });

    applyTraceRecord(
      state,
      { record_type: "obligation_resolved", obligation_id: "obl-favor-1", status: "fulfilled", gamets: 1, excuse: null },
      1,
    );
    expect(state.obligations.get("obl-favor-1")).toMatchObject({
      status: "fulfilled",
      excuse: null,
      fulfilled_at: 1,
      violated_at: null,
    });
  });

  it("obligation_resolved (violated path) sets violated_at and leaves fulfilled_at null, carrying witnesses through", () => {
    const state = emptySocialState(0);
    applyTraceRecord(
      state,
      {
        record_type: "obligation_issued",
        id: "obl-favor-2",
        issuer_id: "adrianne",
        debtor_id: "ulfberth",
        beneficiary_id: null,
        action: "forge a replacement blade",
        condition: null,
        deadline: null,
        status: "active",
        witnesses: ["proventus"],
        sanctions: null,
        created_at: 0,
      },
      0,
    );
    applyTraceRecord(
      state,
      { record_type: "obligation_resolved", obligation_id: "obl-favor-2", status: "violated", gamets: 2, excuse: null },
      2,
    );
    expect(state.obligations.get("obl-favor-2")).toMatchObject({
      status: "violated",
      excuse: null,
      fulfilled_at: null,
      violated_at: 2,
      witnesses: ["proventus"],
    });
  });

  it("obligation_resolved omitting excuse still applies the status transition (excuse falls back to the existing value, schema §7 tolerance)", () => {
    const state = emptySocialState(0);
    applyTraceRecord(
      state,
      {
        record_type: "obligation_issued",
        id: "obl-x",
        issuer_id: "a",
        debtor_id: "b",
        beneficiary_id: null,
        action: "do a thing",
        condition: null,
        deadline: null,
        status: "active",
        witnesses: [],
        sanctions: null,
        created_at: 0,
      },
      0,
    );
    applyTraceRecord(state, { record_type: "obligation_resolved", obligation_id: "obl-x", status: "fulfilled", gamets: 3 }, 3);
    expect(state.obligations.get("obl-x")).toMatchObject({ status: "fulfilled", fulfilled_at: 3, excuse: null });
  });

  it("obligation_resolved referencing an obligation_id never seen via obligation_issued skips cleanly, no throw", () => {
    const state = emptySocialState(0);
    expect(() =>
      applyTraceRecord(
        state,
        { record_type: "obligation_resolved", obligation_id: "obl-unknown", status: "fulfilled", gamets: 1, excuse: null },
        1,
      ),
    ).not.toThrow();
    expect(state.obligations.has("obl-unknown")).toBe(false);
  });

  it("reputation_updated inserts keyed by the composite (observer_id, subject_id, context) triple, ignoring the input-only kind/positive fields", () => {
    const state = emptySocialState(0);
    applyTraceRecord(
      state,
      {
        record_type: "reputation_updated",
        observer_id: "proventus",
        subject_id: "player",
        context: "civic",
        kind: "witnessed",
        positive: true,
        alpha: 2.0,
        beta: 1.0,
        direct_count: 1,
        witness_count: 0,
        certified_count: 0,
        uncertainty: 0.5,
        last_updated: 0,
      },
      0,
    );
    const key = reputationKey("proventus", "player", "civic");
    expect(state.reputations.get(key)).toMatchObject({
      observer_id: "proventus",
      subject_id: "player",
      context: "civic",
      alpha: 2.0,
      beta: 1.0,
      direct_count: 1,
    });
    // kind/positive are input-only -- not required on the stored shape (harmless if present as extras).
  });

  it("a second reputation_updated for the same observer/subject/context REPLACES the accumulator rather than duplicating it", () => {
    const state = emptySocialState(0);
    applyTraceRecord(
      state,
      {
        record_type: "reputation_updated",
        observer_id: "proventus",
        subject_id: "player",
        context: "civic",
        alpha: 2.0,
        beta: 1.0,
        direct_count: 1,
        witness_count: 0,
        certified_count: 0,
        uncertainty: 0.5,
        last_updated: 0,
      },
      0,
    );
    applyTraceRecord(
      state,
      {
        record_type: "reputation_updated",
        observer_id: "proventus",
        subject_id: "player",
        context: "civic",
        alpha: 2.5,
        beta: 1.0,
        direct_count: 2,
        witness_count: 0,
        certified_count: 0,
        uncertainty: 0.4,
        last_updated: 4,
      },
      4,
    );
    expect(state.reputations.size).toBe(1);
    const key = reputationKey("proventus", "player", "civic");
    expect(state.reputations.get(key)).toMatchObject({ alpha: 2.5, direct_count: 2, uncertainty: 0.4, last_updated: 4 });
  });

  it("threshold_crossed is an explicit no-op: state is byte-identical before and after", () => {
    const state = emptySocialState(0);
    state.grudges.set(grudgeKey("a", "b"), {
      id: "g1",
      holder_id: "a",
      target_id: "b",
      source_belief_id: "bel-x",
      grievance_type: "theft",
      severity: 0.5,
      emotional_strength: 0.5,
      evidentiary_strength: 0.5,
      last_rehearsed: 0,
      forgiveness_threshold: 0.2,
    });
    const before = JSON.stringify([...state.grudges.entries()]);
    applyTraceRecord(
      state,
      {
        record_type: "threshold_crossed",
        rule: "accumulation-threshold",
        accumulator: { holder_id: "belethor", grievance_kind: "theft", count: 4, belief_ids: [] },
        threshold: 4,
        produced: { event_key: { save_uuid: "s", generation: 0, seq: 0 }, claim_id: "claim-x" },
      },
      3,
    );
    expect(JSON.stringify([...state.grudges.entries()])).toBe(before);
    expect(state.beliefs.size).toBe(0);
  });

  it("older-run tolerance: a keyframe with no relationships/grudges/obligations/reputations fields hydrates to four empty maps without throwing", () => {
    const bareState = { claims: [], variants: [], beliefs: [], evidence: [], rumor_states: [] };
    let hydrated: SocialState | undefined;
    expect(() => {
      hydrated = fromKeyframeState(bareState as never, 0);
    }).not.toThrow();
    expect(hydrated!.relationships.size).toBe(0);
    expect(hydrated!.grudges.size).toBe(0);
    expect(hydrated!.obligations.size).toBe(0);
    expect(hydrated!.reputations.size).toBe(0);
  });

  it("fromKeyframeState and replayTo agree on grudge/reputation keying for identical real-shaped data", () => {
    const keyframeState = {
      grudges: [
        {
          id: "grudge-violation-auto-1",
          holder_id: "adrianne",
          target_id: "ulfberth",
          source_belief_id: "obl-favor-2",
          grievance_type: "obligation_violated",
          severity: 0.8,
          emotional_strength: 1,
          evidentiary_strength: 0.6,
          last_rehearsed: 2,
          forgiveness_threshold: 0.2,
        },
      ],
      reputations: [
        {
          observer_id: "proventus",
          subject_id: "player",
          context: "civic",
          alpha: 2.0,
          beta: 1.0,
          direct_count: 1,
          witness_count: 0,
          certified_count: 0,
          uncertainty: 0.5,
          last_updated: 0,
        },
      ],
    };
    const hydrated = fromKeyframeState(keyframeState as never, 0);

    const replayed = emptySocialState(0);
    applyTraceRecord(
      replayed,
      {
        record_type: "grudge_formed",
        id: "grudge-violation-auto-1",
        holder_id: "adrianne",
        target_id: "ulfberth",
        source_belief_id: "obl-favor-2",
        grievance_type: "obligation_violated",
        severity: 0.8,
        emotional_strength: 1,
        evidentiary_strength: 0.6,
        forgiveness_threshold: 0.2,
      },
      2,
    );
    applyTraceRecord(
      replayed,
      {
        record_type: "reputation_updated",
        observer_id: "proventus",
        subject_id: "player",
        context: "civic",
        alpha: 2.0,
        beta: 1.0,
        direct_count: 1,
        witness_count: 0,
        certified_count: 0,
        uncertainty: 0.5,
        last_updated: 0,
      },
      0,
    );

    expect([...hydrated.grudges.keys()]).toEqual([...replayed.grudges.keys()]);
    expect([...hydrated.reputations.keys()]).toEqual([...replayed.reputations.keys()]);
  });
});

// ---------------------------------------------------------------------------
// Role roster (lane 52, Tier 5): role_installed / npc_died /
// status_changed(role_appointed) -- see this file's `SocialState.roles` doc
// for why fromKeyframeState never hydrates it (a keyframe never carries a
// `roles` key at all) and why `applyTraceRecord`'s fold here is only
// correct for a full, unwindowed replay (RunReader's keyframe-window fix
// is covered separately in runReader.test.ts).

describe("reconstruct: role roster replay (lane 52)", () => {
  it("role_installed upserts the full role, keyed by role_id, with holder_id and duties", () => {
    const state = emptySocialState(-1);
    applyTraceRecord(
      state,
      {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "steward_of_whiterun",
        title: "Steward of Whiterun",
        institution_id: "whiterun_court",
        duties: [{ name: "collect_taxes", lapse_status_kind: "duty_lapsed" }],
        holder_id: "proventus",
      },
      0,
    );
    expect(state.roles.get("steward_of_whiterun")).toEqual({
      role_id: "steward_of_whiterun",
      title: "Steward of Whiterun",
      institution_id: "whiterun_court",
      duties: [{ name: "collect_taxes", lapse_status_kind: "duty_lapsed" }],
      holder_id: "proventus",
      vacated_at: null,
    });
  });

  it("npc_died vacates every role currently held by the dying NPC, using the event's own gamets", () => {
    const state = emptySocialState(-1);
    applyTraceRecord(
      state,
      {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "jarl_of_whiterun",
        title: "Jarl of Whiterun",
        institution_id: "whiterun_court",
        duties: [{ name: "hold_court", lapse_status_kind: "duty_lapsed" }],
        holder_id: "jarl_balgruuf",
      },
      0,
    );
    applyTraceRecord(
      state,
      {
        event_type: "npc_died",
        gamets: 12.5,
        wall_ts: 0,
        origin: null,
        npc_id: "jarl_balgruuf",
        cause: "assassination",
        killer_id: "the_player",
        location_id: "dragonsreach",
      },
      12, // envelope tick deliberately differs from gamets -- vacated_at must use gamets (framelog.py:735), not this.
    );
    const role = state.roles.get("jarl_of_whiterun")!;
    expect(role.holder_id).toBeNull();
    expect(role.vacated_at).toBe(12.5);
  });

  it("npc_died is a no-op for roles the dying NPC does not currently hold", () => {
    const state = emptySocialState(-1);
    applyTraceRecord(
      state,
      {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "steward_of_whiterun",
        title: "Steward of Whiterun",
        institution_id: "whiterun_court",
        duties: [],
        holder_id: "proventus",
      },
      0,
    );
    applyTraceRecord(
      state,
      { event_type: "npc_died", gamets: 5, wall_ts: 0, origin: null, npc_id: "irileth", cause: "combat", killer_id: null, location_id: null },
      5,
    );
    expect(state.roles.get("steward_of_whiterun")!.holder_id).toBe("proventus");
  });

  it("status_changed(role_appointed): detail is the role_id, npc_id the new holder, vacancy cleared", () => {
    const state = emptySocialState(-1);
    applyTraceRecord(
      state,
      {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "jarl_of_whiterun",
        title: "Jarl of Whiterun",
        institution_id: "whiterun_court",
        duties: [],
        holder_id: "jarl_balgruuf",
      },
      0,
    );
    applyTraceRecord(state, { event_type: "npc_died", gamets: 0, wall_ts: 0, origin: null, npc_id: "jarl_balgruuf", cause: "assassination", killer_id: null, location_id: null }, 0);
    applyTraceRecord(
      state,
      { event_type: "status_changed", gamets: 0, wall_ts: 0, origin: null, npc_id: "irileth", status_kind: "role_appointed", detail: "jarl_of_whiterun", location_id: null },
      0,
    );
    const role = state.roles.get("jarl_of_whiterun")!;
    expect(role.holder_id).toBe("irileth");
    expect(role.vacated_at).toBeNull();
  });

  it("status_changed(duty_lapsed) does NOT touch the roster -- no lapse field is ever stored here (derived/roles.ts's job)", () => {
    const state = emptySocialState(-1);
    applyTraceRecord(
      state,
      {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "jarl_of_whiterun",
        title: "Jarl of Whiterun",
        institution_id: "whiterun_court",
        duties: [{ name: "hold_court", lapse_status_kind: "duty_lapsed" }],
        holder_id: "jarl_balgruuf",
      },
      0,
    );
    const before = new Map(state.roles);
    applyTraceRecord(
      state,
      { event_type: "status_changed", gamets: 0, wall_ts: 0, origin: null, npc_id: "jarl_balgruuf", status_kind: "duty_lapsed", detail: "hold_court", location_id: null },
      0,
    );
    expect(state.roles).toEqual(before);
  });

  it("status_changed(role_appointed) for an unknown role_id is a tolerant no-op (reader tolerance, schema §7)", () => {
    const state = emptySocialState(-1);
    applyTraceRecord(
      state,
      { event_type: "status_changed", gamets: 0, wall_ts: 0, origin: null, npc_id: "irileth", status_kind: "role_appointed", detail: "no_such_role", location_id: null },
      0,
    );
    expect(state.roles.size).toBe(0);
  });

  it("replayTo carries the roster forward (a fresh Map, not the same reference, per its field-by-field copy contract)", () => {
    const start = emptySocialState(-1);
    applyTraceRecord(
      start,
      {
        event_type: "role_installed",
        gamets: 0,
        wall_ts: 0,
        origin: null,
        role_id: "steward_of_whiterun",
        title: "Steward of Whiterun",
        institution_id: "whiterun_court",
        duties: [],
        holder_id: "proventus",
      },
      0,
    );
    const replayed = replayTo(start, [], 10);
    expect(replayed.roles.get("steward_of_whiterun")).toEqual(start.roles.get("steward_of_whiterun"));
    expect(replayed.roles).not.toBe(start.roles);
  });

  it("fromKeyframeState never hydrates roles -- a keyframe's state object carries no roles key at all (this module's own header finding)", () => {
    const state = fromKeyframeState({ schedules: [] }, 47);
    expect(state.roles.size).toBe(0);
  });
});
