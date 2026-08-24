/**
 * State reconstruction: nearest keyframe <= T + replay deltas to T
 * (docs/frame-log-schema.md §5 / §1: "any tick renders as keyframe +
 * replayed deltas — random access to any T is the acceptance test").
 *
 * Each trace/event record's effect on derived state mirrors the
 * corresponding `chronicle/claims.py` constructor (`witness()`, `retell()`,
 * `corroborate()`) — same fields, same formulas (via ../derived/decay.ts's
 * mirrored constants; see that module's header for the schema-drift
 * finding about where those constants actually come from).
 *
 * Reader rule (schema §7): an unrecognized `record_type` — including any
 * `schema_version: 2`-era addition this reader predates — is skipped, not
 * an error. `applyTraceRecord`'s `default` branch is that skip; nothing
 * throws, and the state is simply unaffected by a record type this reader
 * doesn't yet know how to fold in.
 *
 * `supersession` (lane 27): applies the record's own recorded outcome
 * rather than re-deriving the win/loss decision, per
 * `docs/work-packets/lane-27-supersession-replay.md`'s pinned instruction
 * — `chronicle/framelog.py`'s reader re-executes `claims.resolve()` fully,
 * but the amended §4:120 payload already carries everything a
 * trust-the-record reader needs. NOTE (out of scope for this lane, filed
 * as a finding): the `transmitted` case below decays `tellerBelief` via
 * `decayBelief()` before deriving the hearer's confidence, but
 * `chronicle/claims.py`'s `retell()` (and `resolve()`'s adoption branch)
 * both use the teller's *raw, undecayed* `confidence` — confirmed against
 * `driver.py`'s call sites, which never decay a belief before passing it
 * to `retell()`/`resolve()`. That's a pre-existing divergence unrelated to
 * this lane's task; fixing it would shift confidence values several
 * already-landed lanes' tests assert against, so it's left as-is here.
 *
 * `schedule_rewrite` (lane 41, Tier 4a): a genuinely new pattern for this
 * module. Every case in `applyTraceRecord`'s switch matches an
 * events/trace TRACE-stream record (`payload.record_type`);
 * `schedule_rewrite` is instead an EVENTS-stream record (schema §3:96)
 * identified by `payload.event_type` -- there is no `record_type` on it
 * at all. `applyTraceRecord` therefore checks `event_type` FIRST, before
 * the `record_type`-or-bail early return every other branch sits behind;
 * a `case "schedule_rewrite":` added to the existing switch would never
 * match. `SocialState.baseSchedule` is hydrated once from the keyframe
 * (the run's immutable base schedule, `chronicle/driver.py`'s
 * `self.schedule` -- see `types.ts`'s `KeyframeScheduleBlock` doc);
 * `scheduleOverlays` only grows via this new branch and is never pruned
 * -- `effectiveScheduleAt` (below) decides at query time whether a given
 * overlay is still active for tick T, mirroring
 * `chronicle/schedule.py::effective_schedule_at` exactly (total override
 * per overlaid NPC, automatic restoration once
 * `tick >= overlay.end_tick`).
 *
 * FIXED (was filed as a lane-41 finding, closed the same night):
 * `RunReader.deltasBetween` (log/runReader.ts) windows the events stream
 * from the nearest keyframe's tick onward (via the sidecar's
 * `tick_offsets`), while `chronicle/framelog.py::state_at` scans the
 * events stream from tick 0 for `schedule_rewrite` unconditionally
 * (framelog.py:691, `self.records(EVENTS_STREAM, upto_tick=tick)` with no
 * keyframe-relative floor). Concretely: `runs/mourning-demo-01` has
 * `schedule_rewrite` records at tick 0 (end_tick 72) and its first
 * keyframe at tick 23 -- querying `stateAt(t)` for any `t` in `[23, 72)`
 * would replay deltas starting at the keyframe's byte offset and never
 * see the tick-0 overlay, under-populating `SocialState.scheduleOverlays`
 * for that range even though this module's own replay logic was correct
 * given the records it was handed. `RunReader.stateAt`/`stateAtLatestKnown`
 * now separately scan the full events stream from byte 0 for
 * `schedule_rewrite` specifically (mirroring Python's own unconditional
 * full scan), overwriting `scheduleOverlays` with the authoritative
 * result -- see `runReader.ts`'s `scheduleOverlaysUpTo`. `derived/
 * scheduleDiff.ts`/`SchedDiffScreen.vue` still read `mapData.eventRecords`
 * directly rather than `socialState.scheduleOverlays` -- harmless now
 * that both are correct, left as-is rather than churned for its own sake.
 */
import type {
  EventKeyRef,
  FrameRecord,
  KeyframeClaim,
  KeyframeBelief,
  KeyframeEvidence,
  KeyframeGrudge,
  KeyframeObligation,
  KeyframeRelationship,
  KeyframeReputation,
  KeyframeRumorState,
  KeyframeScheduleBlock,
  KeyframeScheduleOverlay,
  KeyframeState,
  KeyframeVariant,
} from "./types";
import { decayBelief } from "../derived/decay";
import {
  RETELL_CONFIDENCE_DECAY,
  RETELL_GIST_DECAY,
  RETELL_VERBATIM_DECAY,
  WITNESS_CONFIDENCE,
} from "../derived/constants";

export interface SocialState {
  tick: number;
  claims: Map<string, KeyframeClaim>;
  variants: Map<string, KeyframeVariant>;
  beliefs: Map<string, KeyframeBelief>;
  evidence: Map<string, KeyframeEvidence>;
  /** Keyed `${npc_id} ${claim_id} ${variant_id ?? ""}`. */
  rumors: Map<string, KeyframeRumorState>;
  /** Keyed by the relationship's own `id` (chronicle/social.py's `SocialStateStore._relationships`). */
  relationships: Map<string, KeyframeRelationship>;
  /**
   * Keyed by the composite `grudgeKey(holder_id, target_id)` -- Python's
   * `SocialStateStore` enforces one grudge per (holder_id, target_id) pair
   * (`_grudge_key`), not by the grudge's own `id`. Hydration and replay
   * MUST use the same key function, or they'd silently diverge.
   */
  grudges: Map<string, KeyframeGrudge>;
  /** Keyed by the obligation's own `id` (chronicle/social.py's `SocialStateStore._obligations`). */
  obligations: Map<string, KeyframeObligation>;
  /**
   * Keyed by the composite `reputationKey(observer_id, subject_id, context)`
   * -- Python's `SocialStateStore._reputations` is keyed by that same triple.
   */
  reputations: Map<string, KeyframeReputation>;
  /**
   * The run's immutable base schedule (chronicle/driver.py's `self.schedule`,
   * set once at construction, never mutated). Hydrated once from a
   * keyframe's `state.schedules[]` (`fromKeyframeState`) -- the same base
   * schedule reappears, unchanged, in every keyframe of a run, so this is
   * NOT re-hydrated on each replay step, only carried forward.
   */
  baseSchedule: KeyframeScheduleBlock[];
  /**
   * Every `schedule_rewrite` seen so far (events-stream, schema §3:96),
   * appended to by `applyTraceRecord`'s `event_type` branch -- never
   * pruned. Whether a given overlay is still "active" for some tick T is
   * a pure function of T vs. the overlay's own `end_tick`
   * (`effectiveScheduleAt`, below), computed at query time -- there is no
   * separate "restore" record to react to (chronicle/schedule.py's
   * `effective_schedule_at` docstring confirms the same).
   */
  scheduleOverlays: KeyframeScheduleOverlay[];
}

export function rumorKey(npcId: string, claimId: string, variantId: string | null): string {
  return `${npcId} ${claimId} ${variantId ?? ""}`;
}

/** Composite key mirroring chronicle/social.py's `SocialStateStore._grudge_key` (holder_id, target_id). */
export function grudgeKey(holderId: string, targetId: string): string {
  return `${holderId} ${targetId}`;
}

/** Composite key mirroring chronicle/social.py's `SocialStateStore._reputations` (observer_id, subject_id, context). */
export function reputationKey(observerId: string, subjectId: string, context: string): string {
  return `${observerId} ${subjectId} ${context}`;
}

export function emptySocialState(tick: number): SocialState {
  return {
    tick,
    claims: new Map(),
    variants: new Map(),
    beliefs: new Map(),
    evidence: new Map(),
    rumors: new Map(),
    relationships: new Map(),
    grudges: new Map(),
    obligations: new Map(),
    reputations: new Map(),
    baseSchedule: [],
    scheduleOverlays: [],
  };
}

/** Runtime-tolerant read of one keyframe `state.schedules[]` entry (schema §7: skip malformed, never throw). */
function toScheduleBlock(raw: Record<string, unknown>): KeyframeScheduleBlock | null {
  const npcId = raw.npc_id;
  const locationId = raw.location_id;
  const startTick = raw.start_tick;
  const endTick = raw.end_tick;
  if (
    !isString(npcId) ||
    !isString(locationId) ||
    typeof startTick !== "number" ||
    typeof endTick !== "number" ||
    endTick <= startTick // chronicle/schedule.py's ScheduleBlock raises here; a reader skips instead.
  ) {
    return null;
  }
  return { npc_id: npcId, location_id: locationId, start_tick: startTick, end_tick: endTick };
}

/** Build the working state from a keyframe's `state` object — unknown keyframe keys are simply not read. */
export function fromKeyframeState(state: KeyframeState, tick: number): SocialState {
  const out = emptySocialState(tick);
  for (const c of state.claims ?? []) out.claims.set(c.id, c);
  for (const v of state.variants ?? []) out.variants.set(v.id, v);
  for (const b of state.beliefs ?? []) out.beliefs.set(b.id, b);
  for (const e of state.evidence ?? []) out.evidence.set(e.id, e);
  for (const r of state.rumor_states ?? []) out.rumors.set(rumorKey(r.npc_id, r.claim_id, r.variant_id), r);
  for (const rel of state.relationships ?? []) out.relationships.set(rel.id, rel);
  for (const g of state.grudges ?? []) out.grudges.set(grudgeKey(g.holder_id, g.target_id), g);
  for (const o of state.obligations ?? []) out.obligations.set(o.id, o);
  for (const rep of state.reputations ?? [])
    out.reputations.set(reputationKey(rep.observer_id, rep.subject_id, rep.context), rep);
  // `schedules` is an older-run-tolerant, optional key (schema §5's
  // additive-per-tier extension) -- a keyframe with no `schedules` field
  // (pre-Tier-4a run) leaves `baseSchedule` empty rather than throwing.
  out.baseSchedule = (state.schedules ?? []).map(toScheduleBlock).filter((b): b is KeyframeScheduleBlock => b !== null);
  return out;
}

function isString(v: unknown): v is string {
  return typeof v === "string";
}

function isStringOrNull(v: unknown): v is string | null {
  return v === null || typeof v === "string";
}

/**
 * Runtime-tolerant parse of a `schedule_rewrite` event payload (schema
 * §3:96) into a `KeyframeScheduleOverlay`, or `null` if malformed --
 * shared by `applyTraceRecord` (below) and `derived/scheduleDiff.ts`
 * (which reads `mapData.eventRecords` directly rather than
 * `SocialState.scheduleOverlays` alone -- see this module's header
 * FINDING on `runReader.ts`'s keyframe-windowed events read). Exported so
 * both call sites share one parser rather than two independently
 * maintained field lists.
 */
export function parseScheduleRewrite(payload: Record<string, unknown>): KeyframeScheduleOverlay | null {
  if (payload.event_type !== "schedule_rewrite") return null;
  const npcId = payload.npc_id;
  const locationId = payload.location_id;
  const startTick = payload.start_tick;
  const endTick = payload.end_tick;
  const cause = payload.cause;
  const rule = payload.rule;
  const triggerEventKey = payload.trigger_event_key as EventKeyRef | undefined;
  if (
    !isString(npcId) ||
    !isString(locationId) ||
    typeof startTick !== "number" ||
    typeof endTick !== "number" ||
    endTick <= startTick ||
    !isString(cause) ||
    !isString(rule) ||
    triggerEventKey === undefined ||
    !isString(triggerEventKey.save_uuid) ||
    typeof triggerEventKey.generation !== "number" ||
    typeof triggerEventKey.seq !== "number"
  ) {
    return null;
  }
  return {
    npc_id: npcId,
    location_id: locationId,
    start_tick: startTick,
    end_tick: endTick,
    cause,
    rule,
    trigger_event_key: {
      save_uuid: triggerEventKey.save_uuid,
      generation: triggerEventKey.generation,
      seq: triggerEventKey.seq,
    },
  };
}

/**
 * Mutates `state` in place applying one trace record's effect, mirroring
 * the matching `chronicle/claims.py` function. `tick` is the record's
 * envelope tick, used as the record's `gamets`/`last_rehearsed` (schema §2:
 * tick *is* gamets at the ADR-0010 quantum).
 */
export function applyTraceRecord(state: SocialState, payload: Record<string, unknown>, tick: number): void {
  // schedule_rewrite (lane 41, Tier 4a): an EVENTS-stream record, matched
  // on `event_type`, not `record_type` -- checked FIRST, before the
  // record_type-or-bail return below, or it would never match (see this
  // module's header note). Every other events-stream payload (npc_died,
  // crime_witnessed, ...) has no derived-state effect here and falls
  // through to that same early return, same as before this lane.
  if (payload.event_type === "schedule_rewrite") {
    const overlay = parseScheduleRewrite(payload);
    if (overlay !== null) state.scheduleOverlays.push(overlay);
    return;
  }

  const recordType = payload.record_type;
  if (!isString(recordType)) return; // an events-stream payload (event_type, no record_type) — nothing to fold in here.

  switch (recordType) {
    case "belief_formed": {
      const claimId = payload.claim_id;
      const holderId = payload.holder_id;
      const beliefId = payload.belief_id;
      const evidenceId = payload.evidence_id;
      if (!isString(claimId) || !isString(holderId) || !isString(beliefId) || !isString(evidenceId)) return;

      if (!state.claims.has(claimId)) {
        state.claims.set(claimId, {
          id: claimId,
          kind: isString(payload.claim_kind) ? payload.claim_kind : "unknown",
          slots: (payload.claim_slots as Record<string, string | null>) ?? {},
          canonical_event_key: (payload.canonical_event_key as KeyframeClaim["canonical_event_key"]) ?? {
            save_uuid: "",
            generation: 0,
            seq: -1,
          },
          truth_status: "unconfirmed",
        });
      }

      state.beliefs.set(beliefId, {
        id: beliefId,
        holder_id: holderId,
        claim_id: claimId,
        variant_id: null,
        confidence: WITNESS_CONFIDENCE,
        verbatim_strength: 1.0,
        gist_strength: 1.0,
        first_learned: tick,
        last_rehearsed: tick,
      });
      state.evidence.set(evidenceId, {
        id: evidenceId,
        belief_id: beliefId,
        evidence_type: "witnessed",
        source_id: holderId,
        predecessor_belief_id: null,
        gamets: tick,
        strength: 1.0,
      });

      const key = rumorKey(holderId, claimId, null);
      const existing = state.rumors.get(key);
      state.rumors.set(key, {
        npc_id: holderId,
        claim_id: claimId,
        variant_id: null,
        stage: "heard",
        first_heard: existing?.first_heard ?? tick,
        last_heard: tick,
        last_told: existing?.last_told ?? null,
        exposure_count: (existing?.exposure_count ?? 0) + 1,
        distinct_source_count: (existing?.distinct_source_count ?? 0) + 1,
      });
      return;
    }

    case "belief_corroborated": {
      const beliefId = payload.belief_id;
      const confidenceAfter = payload.confidence_after;
      if (!isString(beliefId) || typeof confidenceAfter !== "number") return;
      const existing = state.beliefs.get(beliefId);
      if (existing === undefined) return; // corroborating a belief this reader never saw formed — skip, don't crash.
      state.beliefs.set(beliefId, { ...existing, confidence: confidenceAfter, last_rehearsed: tick });
      return;
    }

    case "transmitted": {
      const claimId = payload.claim_id;
      const tellerId = payload.teller_id;
      const tellerBeliefId = payload.teller_belief_id;
      const hearerId = payload.hearer_id;
      const hearerBeliefId = payload.hearer_belief_id;
      const evidenceId = payload.evidence_id;
      const variant = payload.variant as
        | { variant_id: string; parent_variant_id: string | null; slots: Record<string, string | null>; mutated_slot: string | null }
        | undefined;
      if (
        !isString(claimId) ||
        !isString(tellerId) ||
        !isString(tellerBeliefId) ||
        !isString(hearerId) ||
        !isString(hearerBeliefId) ||
        !isString(evidenceId) ||
        variant === undefined ||
        !isString(variant.variant_id)
      ) {
        return;
      }

      const tellerBelief = state.beliefs.get(tellerBeliefId);
      if (tellerBelief === undefined) return;
      const decayedTeller = decayBelief(tellerBelief, tick);

      state.variants.set(variant.variant_id, {
        id: variant.variant_id,
        claim_id: claimId,
        parent_variant_id: variant.parent_variant_id,
        slots: variant.slots ?? {},
        mutated_slot: variant.mutated_slot,
        gamets: tick,
      });

      state.beliefs.set(hearerBeliefId, {
        id: hearerBeliefId,
        holder_id: hearerId,
        claim_id: claimId,
        variant_id: variant.variant_id,
        confidence: decayedTeller.confidence * RETELL_CONFIDENCE_DECAY,
        verbatim_strength: decayedTeller.verbatim_strength * RETELL_VERBATIM_DECAY,
        gist_strength: decayedTeller.gist_strength * RETELL_GIST_DECAY,
        first_learned: tick,
        last_rehearsed: tick,
      });
      state.evidence.set(evidenceId, {
        id: evidenceId,
        belief_id: hearerBeliefId,
        evidence_type: "reported",
        source_id: tellerId,
        predecessor_belief_id: tellerBeliefId,
        gamets: tick,
        strength: decayedTeller.confidence,
      });

      const hearerKey = rumorKey(hearerId, claimId, variant.variant_id);
      const existingHearer = state.rumors.get(hearerKey);
      state.rumors.set(hearerKey, {
        npc_id: hearerId,
        claim_id: claimId,
        variant_id: variant.variant_id,
        stage: "heard",
        first_heard: existingHearer?.first_heard ?? tick,
        last_heard: tick,
        last_told: existingHearer?.last_told ?? null,
        exposure_count: (existingHearer?.exposure_count ?? 0) + 1,
        distinct_source_count: (existingHearer?.distinct_source_count ?? 0) + 1,
      });

      const tellerKey = rumorKey(tellerId, claimId, tellerBelief.variant_id);
      const existingTeller = state.rumors.get(tellerKey);
      if (existingTeller !== undefined) {
        state.rumors.set(tellerKey, { ...existingTeller, stage: "repeated", last_told: tick });
      }
      return;
    }

    // Supersession (schema §4:120, lane-12 amendment): apply the RECORDED
    // outcome, don't re-derive the win/loss decision (chronicle/claims.py's
    // resolve() already made that call before writing the record). Every
    // supersession -- whichever side wins -- leaves the winner's belief
    // holding `winner_variant_id` (null -> canonical): claims.py's adoption
    // branch sets variant_id to the teller's (winning) variant, and its
    // repel branch simply leaves the incumbent's variant untouched, and the
    // incumbent's variant *is* winner_variant_id in that branch by
    // construction. So the branch only changes which confidence formula
    // applies, never the resulting variant_id.
    case "supersession": {
      const holderId = payload.holder_id;
      const winnerBeliefId = payload.winner_belief_id;
      const winnerVariantId = payload.winner_variant_id;
      const tellerBeliefId = payload.teller_belief_id;
      const tellerId = payload.teller_id;
      const evidenceId = payload.evidence_id;
      const confidenceDent = payload.confidence_dent;
      if (
        !isString(holderId) ||
        !isString(winnerBeliefId) ||
        !isStringOrNull(winnerVariantId) ||
        !isString(tellerBeliefId) ||
        !isString(tellerId) ||
        !isString(evidenceId) ||
        typeof confidenceDent !== "number"
      ) {
        return;
      }

      const incumbent = state.beliefs.get(winnerBeliefId);
      const tellerBelief = state.beliefs.get(tellerBeliefId);
      // Both branches need the teller's belief (its confidence is the
      // Evidence's `strength`, per claims.py's "reported testimony from the
      // teller, strength as given" regardless of who wins) -- reader
      // tolerance means an unseen belief on either end skips, not crashes.
      if (incumbent === undefined || tellerBelief === undefined) return;

      const challengeRepelled = incumbent.variant_id === winnerVariantId;
      const updatedBelief: KeyframeBelief = challengeRepelled
        ? (() => {
            const decayed = decayBelief(incumbent, tick);
            return {
              ...decayed,
              confidence: decayed.confidence * (1 - confidenceDent),
              last_rehearsed: tick,
            };
          })()
        : {
            ...incumbent,
            variant_id: winnerVariantId,
            confidence: tellerBelief.confidence * RETELL_CONFIDENCE_DECAY * (1 - confidenceDent),
            verbatim_strength: tellerBelief.verbatim_strength * RETELL_VERBATIM_DECAY,
            gist_strength: tellerBelief.gist_strength * RETELL_GIST_DECAY,
            last_rehearsed: tick,
          };
      state.beliefs.set(winnerBeliefId, updatedBelief);

      state.evidence.set(evidenceId, {
        id: evidenceId,
        belief_id: winnerBeliefId,
        evidence_type: "reported",
        source_id: tellerId,
        predecessor_belief_id: tellerBeliefId,
        gamets: tick,
        strength: tellerBelief.confidence,
      });
      return;
    }

    // relationship_formed (schema §4, chronicle/social.py's Relationship):
    // insert-or-overwrite by the relationship's own `id`. `last_updated` is
    // omitted from the trace record at formation time (it equals
    // `formed_at` then) -- default to `formed_at` when absent, matching the
    // keyframe's own serialized form once the sim later updates it.
    case "relationship_formed": {
      const id = payload.id;
      const fromId = payload.from_id;
      const toId = payload.to_id;
      const basis = payload.basis;
      const basisId = payload.basis_id;
      const strength = payload.strength;
      const formedAt = payload.formed_at;
      if (
        !isString(id) ||
        !isString(fromId) ||
        !isString(toId) ||
        !isString(basis) ||
        !isStringOrNull(basisId) ||
        typeof strength !== "number" ||
        typeof formedAt !== "number"
      ) {
        return;
      }
      const lastUpdated = typeof payload.last_updated === "number" ? payload.last_updated : formedAt;
      state.relationships.set(id, {
        id,
        from_id: fromId,
        to_id: toId,
        basis,
        basis_id: basisId,
        strength,
        formed_at: formedAt,
        last_updated: lastUpdated,
      });
      return;
    }

    // grudge_formed (schema §4, chronicle/social.py's Grudge): insert-or-
    // overwrite keyed by the COMPOSITE (holder_id, target_id) pair, not by
    // `id` -- mirrors SocialStateStore.add_grudge()'s one-grudge-per-pair
    // upsert semantics exactly (grudgeKey() must match fromKeyframeState()'s
    // hydration key or the two would silently diverge on identical data).
    // `last_rehearsed` is read from the record itself (present in real
    // data) -- unlike Relationship.last_updated, this field is NOT omitted
    // at formation time, so the record's own value wins per the lane-27
    // "apply the recorded outcome" idiom; the envelope tick is only a
    // fallback for a hypothetically malformed/older record.
    case "grudge_formed": {
      const id = payload.id;
      const holderId = payload.holder_id;
      const targetId = payload.target_id;
      const sourceBeliefId = payload.source_belief_id;
      const grievanceType = payload.grievance_type;
      const severity = payload.severity;
      const emotionalStrength = payload.emotional_strength;
      const evidentiaryStrength = payload.evidentiary_strength;
      const forgivenessThreshold = payload.forgiveness_threshold;
      if (
        !isString(id) ||
        !isString(holderId) ||
        !isString(targetId) ||
        !isString(sourceBeliefId) ||
        !isString(grievanceType) ||
        typeof severity !== "number" ||
        typeof emotionalStrength !== "number" ||
        typeof evidentiaryStrength !== "number" ||
        typeof forgivenessThreshold !== "number"
      ) {
        return;
      }
      const lastRehearsed = typeof payload.last_rehearsed === "number" ? payload.last_rehearsed : tick;
      state.grudges.set(grudgeKey(holderId, targetId), {
        id,
        holder_id: holderId,
        target_id: targetId,
        source_belief_id: sourceBeliefId,
        grievance_type: grievanceType,
        severity,
        emotional_strength: emotionalStrength,
        evidentiary_strength: evidentiaryStrength,
        last_rehearsed: lastRehearsed,
        forgiveness_threshold: forgivenessThreshold,
      });
      return;
    }

    // obligation_issued (schema §4, chronicle/social.py's Obligation):
    // insert keyed by the obligation's own `id`. `excuse` is always null at
    // issuance; a later obligation_resolved is what sets it.
    case "obligation_issued": {
      const id = payload.id;
      const issuerId = payload.issuer_id;
      const debtorId = payload.debtor_id;
      const beneficiaryId = payload.beneficiary_id;
      const action = payload.action;
      const condition = payload.condition;
      const deadline = payload.deadline;
      const status = payload.status;
      const witnesses = payload.witnesses;
      const sanctions = payload.sanctions;
      const createdAt = payload.created_at;
      if (
        !isString(id) ||
        !isString(issuerId) ||
        !isString(debtorId) ||
        !isStringOrNull(beneficiaryId) ||
        !isString(action) ||
        !isStringOrNull(condition) ||
        !(deadline === null || typeof deadline === "number") ||
        !isString(status) ||
        !Array.isArray(witnesses) ||
        !witnesses.every(isString) ||
        !isStringOrNull(sanctions) ||
        typeof createdAt !== "number"
      ) {
        return;
      }
      state.obligations.set(id, {
        id,
        issuer_id: issuerId,
        debtor_id: debtorId,
        beneficiary_id: beneficiaryId,
        action,
        condition,
        deadline,
        status,
        witnesses,
        sanctions,
        excuse: null,
        created_at: createdAt,
        fulfilled_at: null,
        violated_at: null,
      });
      return;
    }

    // obligation_resolved (schema §4): a DIFFERENT, smaller shape than
    // Obligation -- transitions an existing obligation's status in place.
    // Reader tolerance: resolving an obligation this reader never saw
    // issued skips cleanly, matching belief_corroborated's precedent.
    case "obligation_resolved": {
      const obligationId = payload.obligation_id;
      const status = payload.status;
      if (!isString(obligationId) || !isString(status)) return;
      const existing = state.obligations.get(obligationId);
      if (existing === undefined) return;
      // `excuse` is optional/tolerant (schema §7): a record that omits it
      // shouldn't skip the whole status transition -- fall back to the
      // obligation's current excuse rather than rejecting the record.
      const excuse = isStringOrNull(payload.excuse) ? payload.excuse : existing.excuse;
      const fulfilledAt = status === "fulfilled" ? tick : existing.fulfilled_at;
      const violatedAt = status === "violated" ? tick : existing.violated_at;
      state.obligations.set(obligationId, {
        ...existing,
        status,
        excuse,
        fulfilled_at: fulfilledAt,
        violated_at: violatedAt,
      });
      return;
    }

    // reputation_updated (schema §4, chronicle/social.py's Reputation):
    // "inputs-plus-result" shaped, same pattern as belief_corroborated --
    // apply the RESULT fields directly, replacing (not merging) the keyed
    // accumulator. Keyed by the COMPOSITE (observer_id, subject_id,
    // context) triple, matching SocialStateStore._reputations exactly.
    // The record also carries input-only `kind`/`positive` fields that
    // describe what caused the update -- not part of the stored shape.
    case "reputation_updated": {
      const observerId = payload.observer_id;
      const subjectId = payload.subject_id;
      const context = payload.context;
      const alpha = payload.alpha;
      const beta = payload.beta;
      const directCount = payload.direct_count;
      const witnessCount = payload.witness_count;
      const certifiedCount = payload.certified_count;
      const uncertainty = payload.uncertainty;
      const lastUpdated = payload.last_updated;
      if (
        !isString(observerId) ||
        !isString(subjectId) ||
        !isString(context) ||
        typeof alpha !== "number" ||
        typeof beta !== "number" ||
        typeof directCount !== "number" ||
        typeof witnessCount !== "number" ||
        typeof certifiedCount !== "number" ||
        typeof uncertainty !== "number" ||
        typeof lastUpdated !== "number"
      ) {
        return;
      }
      state.reputations.set(reputationKey(observerId, subjectId, context), {
        observer_id: observerId,
        subject_id: subjectId,
        context,
        alpha,
        beta,
        direct_count: directCount,
        witness_count: witnessCount,
        certified_count: certifiedCount,
        uncertainty,
        last_updated: lastUpdated,
      });
      return;
    }

    // threshold_crossed (schema §4): verified stateless -- driver.py's
    // _evaluate_accumulation writes this purely as an audit trail; the
    // EscalationWarning event + witness() call (already handled by the
    // belief_formed case) are the only actual state effects. No accumulator
    // object exists anywhere for a reader to reconstruct: the count is
    // always recomputed live from beliefs in the Python engine, never
    // persisted as an object of its own. Explicit documented no-op.
    case "threshold_crossed":
      return;

    // encounter_rolled / nothing_salient: schema §4 — trace-only records
    // with no derived-state effect (a roll result and a "found nothing to
    // propagate" negative row respectively). Correctly a no-op here, not
    // an omission.
    case "encounter_rolled":
    case "nothing_salient":
      return;

    // "keyframe" itself is never replayed as a delta by this function —
    // the caller (runReader.ts) uses a keyframe record as the *starting*
    // state via fromKeyframeState(), never folds it in as a delta on top
    // of another state.
    default:
      // Unknown record_type (Tier 2/3 producers this reader doesn't model
      // yet, or a genuinely future schema_version's addition) — schema §7
      // skip-and-continue.
      return;
  }
}

/**
 * Reconstruct state at `targetTick` from a starting `SocialState` (from a
 * keyframe, or `emptySocialState` if none exists yet) plus every
 * intervening record, applied in the order given (callers pass records
 * ordered by `seq` within each stream — schema §2's ordering discipline).
 * Records at or before the starting state's tick, or after `targetTick`,
 * must already be excluded by the caller (this function trusts its input
 * range, matching how the sidecar index is used to select it).
 */
export function replayTo(start: SocialState, records: FrameRecord[], targetTick: number): SocialState {
  const state: SocialState = {
    tick: targetTick,
    claims: new Map(start.claims),
    variants: new Map(start.variants),
    beliefs: new Map(start.beliefs),
    evidence: new Map(start.evidence),
    rumors: new Map(start.rumors),
    relationships: new Map(start.relationships),
    grudges: new Map(start.grudges),
    obligations: new Map(start.obligations),
    reputations: new Map(start.reputations),
    baseSchedule: [...start.baseSchedule],
    scheduleOverlays: [...start.scheduleOverlays],
  };
  for (const record of records) {
    if (record.tick > targetTick) continue;
    applyTraceRecord(state, record.payload, record.tick);
  }
  return state;
}

/**
 * The schedule blocks in effect at `tick` (Tier 4a, lane 41 — dashboard
 * mirror of `chronicle/schedule.py::effective_schedule_at`, the ONE place
 * presence-with-overlays is computed on the Python side; this is that
 * function's TypeScript twin, same semantics, so the two can't drift
 * apart): base blocks covering `tick`, except any NPC with an overlay
 * covering `tick` has ALL of their base presence at `tick` replaced by
 * that overlay -- total override, not merge. `overlays` need not already
 * be filtered to "seen by tick" -- callers may pass every overlay ever
 * recorded; only `covers(tick)` matters here (an overlay recorded after
 * `tick` cannot cover `tick` anyway, since half-open `[start_tick,
 * end_tick)` ranges are always non-negative and `start_tick` is recorded
 * at or after the record's own tick in every real producer, but this
 * function does not depend on that — it only ever checks the range).
 */
export function effectiveScheduleAt(
  base: readonly KeyframeScheduleBlock[],
  overlays: readonly KeyframeScheduleOverlay[],
  tick: number,
): (KeyframeScheduleBlock | KeyframeScheduleOverlay)[] {
  const covers = (b: KeyframeScheduleBlock): boolean => b.start_tick <= tick && tick < b.end_tick;
  const activeOverlays = overlays.filter(covers);
  const overridden = new Set(activeOverlays.map((o) => o.npc_id));
  return [...base.filter((b) => covers(b) && !overridden.has(b.npc_id)), ...activeOverlays];
}
