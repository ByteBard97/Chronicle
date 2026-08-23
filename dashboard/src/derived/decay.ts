/**
 * Analytic decay at read time (docs/ui-spec.md §1.1: "belief strength /
 * confidence curves are closed-form functions of elapsed time ... computed
 * at read time"; docs/frame-log-schema.md's implementer note cites the
 * exact formula at `chronicle/claims.py:71` — `value * 0.5 ** (elapsed /
 * half_life)`). Ported verbatim; nothing here is sampled or cached.
 */
import type { KeyframeBelief } from "../log/types";
import {
  CONFIDENCE_DECAY_HALF_LIFE,
  GIST_DECAY_HALF_LIFE,
  VERBATIM_DECAY_HALF_LIFE,
} from "./constants";

export function decayValue(value: number, elapsed: number, halfLife: number): number {
  if (elapsed <= 0) return value;
  return value * Math.pow(0.5, elapsed / halfLife);
}

/**
 * `claims.py`'s `decay()`, ported: erode confidence/verbatim/gist by time
 * elapsed since `last_rehearsed`. A pure read-time computation — never
 * mutates the belief record itself, matching the store's "derivation is
 * lazy" discipline (rule 19).
 */
export function decayBelief(belief: KeyframeBelief, atTick: number): KeyframeBelief {
  const elapsed = atTick - belief.last_rehearsed;
  if (elapsed <= 0) return belief;
  return {
    ...belief,
    confidence: decayValue(belief.confidence, elapsed, CONFIDENCE_DECAY_HALF_LIFE),
    verbatim_strength: decayValue(belief.verbatim_strength, elapsed, VERBATIM_DECAY_HALF_LIFE),
    gist_strength: decayValue(belief.gist_strength, elapsed, GIST_DECAY_HALF_LIFE),
  };
}
