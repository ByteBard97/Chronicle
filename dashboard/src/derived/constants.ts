/**
 * Mirrored derivation constants.
 *
 * FINDING (see this lane's final report): docs/frame-log-schema.md's
 * keyframe payload (§5) does not carry these constants anywhere — a
 * keyframe is a snapshot of *stored* state (claims, variants, beliefs, ...)
 * and the schema explicitly lists decayed strength values as "deliberately
 * absent ... derived at read time, never stored." That is correct for the
 * *values*, but the *parameters* driving that derivation (the half-lives,
 * the retell decay factors, the rumor-stage thresholds) are equally absent
 * from every record type in the catalog. The work packet asks the reader
 * to "read the constants from the keyframe record, not hardcoding" — that
 * is not possible against the schema as written today, so this module
 * mirrors `chronicle/claims.py`'s module-level constants instead (values
 * copied 1:1, with the same names and source citations) and reconstruction
 * (`../log/reconstruct.ts`) imports from here. This is a real reader/schema
 * drift risk: if the math tier ever recalibrates these on the Python side
 * without a corresponding change here (or without the schema growing a
 * "sim_config"/constants record the dashboard could read instead), the
 * dashboard's decay curves silently diverge from the sim's own. Flagged for
 * the coordinator; not fixed here since it would mean amending the frozen
 * schema, which is out of this lane's file boundary.
 */

// chronicle/claims.py:46-48
export const RETELL_CONFIDENCE_DECAY = 0.8;
export const RETELL_VERBATIM_DECAY = 0.7;
export const RETELL_GIST_DECAY = 0.95;
export const WITNESS_CONFIDENCE = 0.95;

// chronicle/claims.py:59-61 (ticks; 1 tick = 1 gamets = 1 game-hour, ADR-0010)
export const CONFIDENCE_DECAY_HALF_LIFE = 168.0;
export const VERBATIM_DECAY_HALF_LIFE = 72.0;
export const GIST_DECAY_HALF_LIFE = 1440.0;

// chronicle/claims.py:73-74 (rumor stage machine, rule 16)
export const RUMOR_DORMANT_AFTER = 1080.0;
export const RUMOR_FORGOTTEN_GIST_THRESHOLD = 0.05;
