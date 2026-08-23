/**
 * Rumor stage at T (`chronicle/claims.py` rules 16/19, `stage_at()`,
 * ported). Stored stage is only ever "heard" | "repeated" (rumor_states
 * §5's keyframe field, or a hearing/telling event replayed from the trace);
 * "dormant" and "forgotten" are always derived at read time from decay, per
 * rule 19's lazy-derivation discipline — mirrored here, not reinvented:
 * thresholds come from ../derived/constants.ts (itself mirroring
 * claims.py's module constants — see that module's header for the
 * schema-drift finding).
 */
import type { KeyframeBelief, KeyframeRumorState } from "../log/types";
import { decayBelief } from "./decay";
import { RUMOR_DORMANT_AFTER, RUMOR_FORGOTTEN_GIST_THRESHOLD } from "./constants";

export type RumorStage = "unheard" | "heard" | "repeated" | "dormant" | "forgotten";

/**
 * Mirrors `claims.py`'s `stage_at()`. `rumor` and `belief` must be null when
 * the NPC has never heard the claim/variant at all — the "unheard" stage,
 * which (per claims.py's RumorState docstring) is the *absence* of a
 * RumorState, never a stored value.
 */
export function rumorStageAt(
  rumor: KeyframeRumorState | null,
  belief: KeyframeBelief | null,
  atTick: number,
): RumorStage {
  if (rumor === null || belief === null) return "unheard";

  const decayed = decayBelief(belief, atTick);
  if (decayed.gist_strength < RUMOR_FORGOTTEN_GIST_THRESHOLD) return "forgotten";

  const lastActivity = rumor.last_told ?? rumor.last_heard;
  if (atTick - lastActivity > RUMOR_DORMANT_AFTER) return "dormant";

  return (rumor.stage === "repeated" ? "repeated" : "heard");
}
