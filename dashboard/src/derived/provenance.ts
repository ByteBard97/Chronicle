/**
 * Provenance drill-down (lane 22, ui-spec §3.6): `SocialState` (beliefs +
 * evidence) + raw trace records (`transmitted`, `mutation_applied`,
 * `supersession`) -> a DAG-honest span-list model for one target belief at
 * T. Mirrors the lane-14/16/21/28 idiom: pure, no Vue/store deps,
 * unit-testable against synthetic states.
 *
 * DAG honesty (the acceptance core, ui-spec §3.6): `chronicle/claims.py`'s
 * `chain_for` walks a SINGLE parent (each belief's grounding evidence at
 * index 0 only) — a deliberate spanning-tree pick. This module instead
 * takes `evidence_for`'s full recipe dashboard-side: ALL Evidence records
 * grounding a belief (`Array.from(state.evidence.values()).filter(e =>
 * e.belief_id === beliefId)` — `state.evidence` is keyed by evidence id,
 * not belief id, so a scan is required every time, same pattern
 * `inspectorBeliefs.ts`'s `latestProvenance` already uses). Every one of
 * those evidence records becomes its own column; where a corroborated
 * belief's evidence records share the same `predecessor_belief_id`, both
 * columns independently recurse into (and display) that same predecessor
 * — never picking one and hiding the other.
 *
 * Field provenance, evidence-first (no cross-referencing trace records
 * needed for these): `KeyframeEvidence.source_id`/`evidence_type`/
 * `gamets`/`predecessor_belief_id` already carry the teller, kind, tick,
 * and backward link directly — `reconstruct.ts`'s `transmitted` and
 * `supersession` cases both set `evidence.source_id` to the teller/reporter
 * id (see that module's header comment). Only three facts genuinely need
 * the raw trace stream, since `KeyframeEvidence`/`KeyframeBelief` don't
 * carry them: (1) location — only a `transmitted` record's `location_id`
 * carries it (a `supersession` record has no location field at all, so a
 * superseded hop's `location` is honestly `null`, a finding, not a bug);
 * (2) whether a hop's evidence came from a `supersession` record (the
 * grayed/interstitial case) vs. an ordinary `transmitted` one, keyed by
 * matching `evidence_id`; (3) whether a hop's evidence is the specific
 * `transmitted` record that *introduced* a mutated variant, keyed by that
 * record's own `variant.variant_id` matching a `mutation_applied` record
 * (mirrors `variantTree.ts`'s `mutationByVariant` map) — deliberately
 * matched against the transmitting evidence's own introduced variant, NOT
 * against the belief's current `variant_id` (T-dependent: a later
 * `supersession` can re-point the belief onto a different variant
 * entirely, which would otherwise flag every one of that belief's
 * evidence records as the same mutation hop and flip hops between
 * mutation/plain as T scrubs past the supersession). See `TraceIndexes`'
 * `variantByEvidence` below for the full argument.
 *
 * Collapse rule (pinned): consecutive "plain" hops (no mutation, no
 * supersession, not the witness terminus) collapse behind a count;
 * mutation hops, superseded hops, and the witness terminus are always
 * individually expanded. Collapsing only ever happens along one column's
 * own linear stretch — it never reaches across a branch (a corroborated
 * predecessor immediately stops the column and hands off to a
 * `ProvenanceBranch` of its own parallel columns).
 */
import type { FrameRecord, KeyframeEvidence } from "../log/types";
import type { SocialState } from "../log/reconstruct";
import { decayBelief } from "./decay";

export interface ProvenanceMutation {
  mutationId: string;
  slot: string | null;
  oldValue: string | null;
  newValue: string | null;
}

export interface ProvenanceSupersession {
  resolutionRule: string;
  confidenceDent: number;
}

export interface ProvenanceHop {
  /** The Evidence record id this hop renders — unique across the whole panel. */
  edgeId: string;
  /** The belief this evidence grounds (the "child" side of the edge). */
  beliefId: string;
  holderId: string;
  claimId: string | null;
  variantId: string | null;
  evidenceType: string;
  /** Teller/reporter/witness — `KeyframeEvidence.source_id`. */
  sourceId: string;
  /** `KeyframeEvidence.gamets`. */
  tick: number;
  /** Only ever non-null for a `transmitted`-sourced hop (see module header). */
  location: string | null;
  /** `beliefId`'s belief, decayed to `atTick` (read, not re-derived from any other formula). */
  confidence: number;
  /** `confidence` minus the predecessor belief's own decayed-at-`atTick` confidence; `null` when there's no predecessor belief to compare against. */
  confidenceDelta: number | null;
  predecessorBeliefId: string | null;
  /** `predecessorBeliefId === null` — the chain terminus (an eyewitness's `belief_formed` origin). */
  isWitness: boolean;
  /** Set when `beliefId`'s belief's `variant_id` was produced by a `mutation_applied` record — always-expanded per the collapse rule. */
  mutation: ProvenanceMutation | null;
  /** Set when a `supersession` record names this exact evidence id — the grayed/interstitial case. */
  supersession: ProvenanceSupersession | null;
}

export type ProvenanceDisplayEntry =
  | { kind: "hop"; hop: ProvenanceHop }
  | { kind: "collapsed"; count: number; hops: ProvenanceHop[] };

export interface ProvenanceColumn {
  /** The column's first (nearest-to-target) hop's evidence id. */
  id: string;
  /** Target-to-witness order, collapsed per the pinned rule. */
  entries: ProvenanceDisplayEntry[];
  /** Set when the column's last hop's predecessor belief is itself corroborated (2+ evidence) — the column hands off to its own parallel columns rather than picking one. `null` when the column ended at a witness terminus. */
  branch: ProvenanceBranch | null;
}

export interface ProvenanceBranch {
  beliefId: string;
  holderId: string;
  /** One column per Evidence record grounding `beliefId` — DAG-honest: every one renders, never a spanning-tree pick. */
  columns: ProvenanceColumn[];
}

function isString(v: unknown): v is string {
  return typeof v === "string";
}

/** Every Evidence record grounding `beliefId` — `evidence_for()`'s dashboard-side recipe (module header); `state.evidence` has no belief-id index, so this scans. */
function evidenceForBelief(state: SocialState, beliefId: string): KeyframeEvidence[] {
  const result: KeyframeEvidence[] = [];
  for (const e of state.evidence.values()) {
    if (e.belief_id === beliefId) result.push(e);
  }
  return result.sort((a, b) => a.gamets - b.gamets || a.id.localeCompare(b.id));
}

interface TraceIndexes {
  mutationByVariant: Map<string, Record<string, unknown>>;
  supersessionByEvidence: Map<string, Record<string, unknown>>;
  locationByEvidence: Map<string, string>;
  /**
   * evidence id -> the variant id that `transmitted` record's own
   * `variant.variant_id` introduced. Deliberately NOT `belief.variant_id`
   * (T-dependent — a later `supersession` can re-point the belief onto a
   * different variant entirely, e.g. `belief-auto-relief_caravaneer-4`
   * resolves onto canonical by tick 28): keying mutation attribution off
   * the belief's *current* variant would flag every one of that belief's
   * evidence records as the same mutation hop (wrong) and would flip
   * hops between mutation/plain as T scrubs past a supersession (also
   * wrong — a mutation hop's identity is fixed history, immutable once
   * the `transmitted` record that introduced the variant is written). A
   * `supersession`-sourced evidence record never introduces a variant
   * itself (`reconstruct.ts`'s `supersession` case only ever re-points an
   * *existing* variant), so this map is only ever populated from
   * `transmitted` records — a superseded hop's `mutation` is correctly
   * always `null`.
   */
  variantByEvidence: Map<string, string>;
}

/** Builds the trace-record lookups this module needs (module header) — mirrors `variantTree.ts`'s `mutationByVariant` idiom. */
function buildTraceIndexes(traceRecords: FrameRecord[], atTick: number): TraceIndexes {
  const mutationByVariant = new Map<string, Record<string, unknown>>();
  const supersessionByEvidence = new Map<string, Record<string, unknown>>();
  const locationByEvidence = new Map<string, string>();
  const variantByEvidence = new Map<string, string>();

  for (const r of traceRecords) {
    if (r.tick > atTick) continue;
    const p = r.payload;
    if (p.record_type === "mutation_applied" && isString(p.variant_id)) {
      mutationByVariant.set(p.variant_id, p);
    } else if (p.record_type === "supersession" && isString(p.evidence_id)) {
      supersessionByEvidence.set(p.evidence_id, p);
    } else if (p.record_type === "transmitted" && isString(p.evidence_id)) {
      if (isString(p.location_id)) locationByEvidence.set(p.evidence_id, p.location_id);
      const variant = p.variant as { variant_id?: unknown } | undefined;
      if (variant !== undefined && isString(variant.variant_id)) {
        variantByEvidence.set(p.evidence_id, variant.variant_id);
      }
    }
  }

  return { mutationByVariant, supersessionByEvidence, locationByEvidence, variantByEvidence };
}

function buildHop(evidence: KeyframeEvidence, state: SocialState, atTick: number, idx: TraceIndexes): ProvenanceHop {
  const belief = state.beliefs.get(evidence.belief_id);
  const holderId = belief?.holder_id ?? "";
  const claimId = belief?.claim_id ?? null;
  const variantId = belief?.variant_id ?? null;
  const confidence = belief !== undefined ? decayBelief(belief, atTick).confidence : evidence.strength;

  const predecessorBeliefId = evidence.predecessor_belief_id;
  let confidenceDelta: number | null = null;
  if (predecessorBeliefId !== null) {
    const predBelief = state.beliefs.get(predecessorBeliefId);
    if (predBelief !== undefined) {
      confidenceDelta = confidence - decayBelief(predBelief, atTick).confidence;
    }
  }

  let mutation: ProvenanceMutation | null = null;
  const introducedVariantId = idx.variantByEvidence.get(evidence.id);
  if (introducedVariantId !== undefined) {
    const m = idx.mutationByVariant.get(introducedVariantId);
    if (m !== undefined) {
      mutation = {
        mutationId: isString(m.mutation_id) ? m.mutation_id : "",
        slot: isString(m.slot) ? m.slot : null,
        oldValue: (m.old_value as string | null) ?? null,
        newValue: (m.new_value as string | null) ?? null,
      };
    }
  }

  let supersession: ProvenanceSupersession | null = null;
  const s = idx.supersessionByEvidence.get(evidence.id);
  if (s !== undefined) {
    supersession = {
      resolutionRule: isString(s.resolution_rule) ? s.resolution_rule : "",
      confidenceDent: typeof s.confidence_dent === "number" ? s.confidence_dent : 0,
    };
  }

  return {
    edgeId: evidence.id,
    beliefId: evidence.belief_id,
    holderId,
    claimId,
    variantId,
    evidenceType: evidence.evidence_type,
    sourceId: evidence.source_id,
    tick: evidence.gamets,
    location: idx.locationByEvidence.get(evidence.id) ?? null,
    confidence,
    confidenceDelta,
    predecessorBeliefId,
    isWitness: predecessorBeliefId === null,
    mutation,
    supersession,
  };
}

/** A hop collapses only when it's a plain retelling: no mutation, no supersession, and not the witness terminus (always shown, per the pinned rule). */
function isCollapsible(hop: ProvenanceHop): boolean {
  return hop.mutation === null && hop.supersession === null && !hop.isWitness;
}

/** Groups a linear (target-to-witness ordered) hop sequence, collapsing consecutive collapsible runs of 2+ behind a count; a run of exactly 1 stays an ordinary expanded hop (nothing to collapse). */
export function collapseHops(hops: ProvenanceHop[]): ProvenanceDisplayEntry[] {
  const entries: ProvenanceDisplayEntry[] = [];
  let run: ProvenanceHop[] = [];

  const flush = () => {
    if (run.length === 0) return;
    if (run.length === 1) {
      entries.push({ kind: "hop", hop: run[0]! });
    } else {
      entries.push({ kind: "collapsed", count: run.length, hops: run });
    }
    run = [];
  };

  for (const hop of hops) {
    if (isCollapsible(hop)) {
      run.push(hop);
    } else {
      flush();
      entries.push({ kind: "hop", hop });
    }
  }
  flush();
  return entries;
}

/**
 * Walks one column starting at `startEvidence`, extending straight through
 * every predecessor that has exactly one grounding Evidence record (an
 * uncorroborated, ordinary retelling chain), stopping at a witness
 * terminus or at a corroborated predecessor (2+ evidence — a branch,
 * handed off to `buildBranch` rather than picked from). `visiting` guards
 * against a cycle (shouldn't occur in real data; defensive only).
 */
function buildColumn(
  startEvidence: KeyframeEvidence,
  state: SocialState,
  atTick: number,
  idx: TraceIndexes,
  visiting: Set<string>,
): ProvenanceColumn {
  const hops: ProvenanceHop[] = [];
  let current: KeyframeEvidence = startEvidence;

  for (;;) {
    const hop = buildHop(current, state, atTick, idx);
    hops.push(hop);

    if (hop.isWitness) {
      return { id: startEvidence.id, entries: collapseHops(hops), branch: null };
    }

    const predBeliefId = hop.predecessorBeliefId as string;
    if (visiting.has(predBeliefId)) {
      // Defensive cycle guard — real data terminates at a witness; treat an
      // (unexpected) cycle as an early terminus rather than looping forever.
      return { id: startEvidence.id, entries: collapseHops(hops), branch: null };
    }

    const predEvidence = evidenceForBelief(state, predBeliefId);
    if (predEvidence.length === 0) {
      // Predecessor belief has no recorded evidence (shouldn't occur per the
      // pinned facts) — degrade to an early terminus rather than throwing.
      return { id: startEvidence.id, entries: collapseHops(hops), branch: null };
    }

    if (predEvidence.length === 1) {
      current = predEvidence[0]!;
      continue;
    }

    visiting.add(predBeliefId);
    const branch = buildBranch(predBeliefId, predEvidence, state, atTick, idx, visiting);
    visiting.delete(predBeliefId);
    return { id: startEvidence.id, entries: collapseHops(hops), branch };
  }
}

/** DAG-honest fan-out: one column per Evidence record grounding `beliefId` — every parent renders, never a spanning-tree pick. */
function buildBranch(
  beliefId: string,
  evidence: KeyframeEvidence[],
  state: SocialState,
  atTick: number,
  idx: TraceIndexes,
  visiting: Set<string>,
): ProvenanceBranch {
  const belief = state.beliefs.get(beliefId);
  const columns = evidence.map((e) => buildColumn(e, state, atTick, idx, visiting));
  return { beliefId, holderId: belief?.holder_id ?? "", columns };
}

/**
 * The entry point: the DAG-honest provenance for `targetBeliefId`, as of
 * `atTick`. Returns `null` when the target belief doesn't exist in `state`
 * (an honest "nothing to drill into" rather than a synthesized empty
 * branch) — the caller (the panel) renders that as its own empty state.
 */
export function buildProvenance(
  state: SocialState,
  traceRecords: FrameRecord[],
  targetBeliefId: string,
  atTick: number,
): ProvenanceBranch | null {
  const belief = state.beliefs.get(targetBeliefId);
  if (belief === undefined) return null;

  const idx = buildTraceIndexes(traceRecords, atTick);
  const evidence = evidenceForBelief(state, targetBeliefId);
  const columns = evidence.map((e) => buildColumn(e, state, atTick, idx, new Set([targetBeliefId])));
  return { beliefId: targetBeliefId, holderId: belief.holder_id, columns };
}
