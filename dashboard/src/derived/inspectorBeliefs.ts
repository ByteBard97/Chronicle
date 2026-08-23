/**
 * NpcInspector's Beliefs tab, real-data assembly (lane 28, ui-spec §3.2):
 * `SocialState` (an NPC's held beliefs) -> render-ready `InspectorBelief[]`
 * — claim/variant text, rumor stage, decayed-at-T strengths, and a
 * summary provenance fact. Mirrors the lane-14/21 idiom (pure, no Vue/
 * store deps, unit-testable against synthetic states).
 *
 * "Beliefs for the NPC" = `state.beliefs` values where `holder_id`
 * matches (the packet's pinned recipe) — one card per held belief, one
 * belief per claim an NPC currently holds an opinion on.
 *
 * Claim text is synthesized from slots (no narrative-text field exists on
 * `KeyframeClaim`/`KeyframeVariant`): the variant's own `slots` (already
 * the *full*, merged slot set per `transmitted`'s payload, not a diff)
 * when the belief points at one, else the claim's base `slots` for an
 * unvarianted (canonical) belief. E.g. "perpetrator: unknown, cause:
 * assassination, location: whiterun_market" — confirmed against
 * `runs/carrier-mutation-01`'s `claim-market-murder`.
 *
 * Rumor-stage lookup finding (reconstruct.ts, not fixed here per this
 * lane's read-only boundary on `src/log/*`): `applyTraceRecord`'s
 * `supersession` case updates a belief's `variant_id` but never rekeys
 * `state.rumors` (keyed `${npc} ${claim} ${variant_id}`) — so a belief
 * that has been re-pointed onto a different (or canonical/null) variant
 * by a supersession has no rumor entry under its *current* key anymore,
 * only under whichever variant it was transmitted onto originally.
 * Confirmed directly against `runs/carrier-mutation-01`:
 * `belief-auto-relief_caravaneer-4` resolves (4 supersessions, ticks
 * 26-28) onto the canonical (null) variant, but its only `rumors` entry
 * is still keyed under `variant-auto-4` (its original `transmitted`
 * variant). An exact-key lookup on the belief's current `variant_id`
 * therefore misses and `rumorStageAt` would report "unheard" for a belief
 * the NPC plainly holds. `findRumorForBelief` below falls back to any
 * rumor for the same `(npc_id, claim_id)` pair, preferring the most
 * recently active one, when the exact key misses.
 */
import type { KeyframeBelief, KeyframeEvidence, KeyframeRumorState } from "../log/types";
import { rumorKey, type SocialState } from "../log/reconstruct";
import { rumorStageAt, type RumorStage } from "./rumorStage";
import { decayBelief } from "./decay";

export interface InspectorBeliefProvenance {
  evidenceType: string;
  sourceId: string;
  tick: number;
}

export interface InspectorBelief {
  beliefId: string;
  claimId: string;
  variantId: string | null;
  /** null for an unvarianted (canonical) belief -- BeliefCard's `variantLabel` chip is omitted for those. */
  variantLabel: string | null;
  stage: RumorStage;
  text: string;
  /** Strengths decayed to `atTick` (lane-14's `decayBelief`, not recomputed here). */
  confidence: number;
  verbatimStrength: number;
  gistStrength: number;
  lastRehearsed: number;
  /** Top-level grounding-evidence facts only -- the full chain render is lane 22's drill-down. */
  provenance: InspectorBeliefProvenance | null;
}

function claimText(state: SocialState, belief: KeyframeBelief): string {
  const variantSlots = belief.variant_id !== null ? state.variants.get(belief.variant_id)?.slots : undefined;
  const slots = variantSlots ?? state.claims.get(belief.claim_id)?.slots ?? {};
  const parts = Object.entries(slots).map(([slot, value]) => `${slot}: ${value ?? "unknown"}`);
  return parts.length > 0 ? parts.join(", ") : belief.claim_id;
}

function variantLabel(state: SocialState, belief: KeyframeBelief): string | null {
  if (belief.variant_id === null) return null;
  const variant = state.variants.get(belief.variant_id);
  if (variant === undefined) return belief.variant_id;
  if (variant.mutated_slot !== null) {
    const value = variant.slots[variant.mutated_slot] ?? "?";
    return `${variant.mutated_slot}: ${value}`;
  }
  return variant.id;
}

/** See this module's header for the reconstruct.ts rumor-rekeying finding this fallback works around. */
function findRumorForBelief(state: SocialState, belief: KeyframeBelief): KeyframeRumorState | null {
  const exact = state.rumors.get(rumorKey(belief.holder_id, belief.claim_id, belief.variant_id));
  if (exact !== undefined) return exact;

  let best: KeyframeRumorState | null = null;
  for (const rumor of state.rumors.values()) {
    if (rumor.npc_id !== belief.holder_id || rumor.claim_id !== belief.claim_id) continue;
    if (best === null || rumor.last_heard > best.last_heard) best = rumor;
  }
  return best;
}

/** Most recent (by `gamets`) evidence grounding this belief, if any was folded in. */
function latestProvenance(state: SocialState, belief: KeyframeBelief): InspectorBeliefProvenance | null {
  let best: KeyframeEvidence | null = null;
  for (const evidence of state.evidence.values()) {
    if (evidence.belief_id !== belief.id) continue;
    if (best === null || evidence.gamets > best.gamets) best = evidence;
  }
  if (best === null) return null;
  return { evidenceType: best.evidence_type, sourceId: best.source_id, tick: best.gamets };
}

/**
 * The pinned recipe: `state.beliefs` values held by `npcId`, each resolved
 * to a render-ready card. Empty array for an NPC with no beliefs (or one
 * this state has never heard from at all) -- the caller renders that as an
 * honest empty Beliefs tab, not the removed fixture.
 */
export function beliefsForNpc(state: SocialState, npcId: string, atTick: number): InspectorBelief[] {
  const result: InspectorBelief[] = [];
  for (const belief of state.beliefs.values()) {
    if (belief.holder_id !== npcId) continue;
    const decayed = decayBelief(belief, atTick);
    const rumor = findRumorForBelief(state, belief);
    result.push({
      beliefId: belief.id,
      claimId: belief.claim_id,
      variantId: belief.variant_id,
      variantLabel: variantLabel(state, belief),
      stage: rumorStageAt(rumor, belief, atTick),
      text: claimText(state, belief),
      confidence: decayed.confidence,
      verbatimStrength: decayed.verbatim_strength,
      gistStrength: decayed.gist_strength,
      lastRehearsed: belief.last_rehearsed,
      provenance: latestProvenance(state, belief),
    });
  }
  result.sort((a, b) => a.claimId.localeCompare(b.claimId) || a.beliefId.localeCompare(b.beliefId));
  return result;
}
