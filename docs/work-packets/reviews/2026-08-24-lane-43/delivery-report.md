# Lane 43 delivery report — Tier 4b pairwise encounter weighting (rule 18, T4b.1)

**Delivered:** `79d8d73` — rule 18 live (avoidance), the T4b.1 rung, per
the ruled design (`docs/design/tier-4b-avoidance.md` decisions W1–W5,
overseer review `docs/work-packets/reviews/2026-08-23-lane-40/`).

## Acceptance, per criterion

- **`uv run pytest -q` green (218 + new tests), ruff clean.** ✓ — 223
  passed, 0 failed, 0 xfailed (219 prior + 1 `SocialStateStore.grudges()`
  unit test + 1 `sample_encounters` pair_thresholds unit test + 3 rung
  tests). `uv run ruff check .`: clean.
- **The rung + control pair pass as written; cooling behavior per W3.**
  ✓ — `scenarios/test_tier4b_avoidance.py`, three tests:
  1. The grudged pair (adrianne/ulfberth, severity 0.8) never encounters
     across 10 ticks (`threshold == 0.0`, `encountered is False` every
     row) while the control pair (camilla/delphine, no grudge) at the
     same tavern block encounters at the base threshold every tick and
     produces **zero** rule-18 rows — proving avoidance is per-pair, not
     location-wide. Each avoiding roll's paired `rule_evaluated` row
     fires, names the grudge id, and carries
     `result == {"base_probability": 1.0, "effective_probability": 0.0}`.
  2. Cooling: the same grudge, run at ticks [390, 410) — cheap despite
     the large tick numbers, since `grudge_at` is a pure function of
     elapsed gamets, not of ticks actually simulated. By the half-life
     math (`GRUDGE_EMOTIONAL_HALF_LIFE=672`,
     `GRUDGE_EVIDENTIARY_HALF_LIFE=336`, `social.py:80-81`) severity
     has decayed from 0.8 to ~0.46–0.47 there, below
     `AVOIDANCE_GRUDGE_THRESHOLD=0.5` but above
     `forgiveness_threshold`'s 0.2 — the "cooling, not yet forgiven"
     middle stage the design doc named. Asserted: `threshold` reverts
     to the base `encounter_probability`, encounters resume, and the
     rule-18 rows **continue appearing** with `fired: false` and the
     current decayed severity in `inputs` — doctrine 3's "visible, not
     silent" holds through a cooling transition with no special-cased
     record.
  3. The regression case: no grudge at all → zero rule-18 rows, every
     `encounter_rolled.threshold` at the base probability.
- **No new record types; no new RNG purposes; no schema edits.** ✓ —
  `git diff docs/frame-log-schema.md chronicle/rng.py` for this lane is
  empty. Avoidance reuses `encounter_rolled` (lowered `threshold`) and
  `rule_evaluated` (rule 18's own row) exactly as designed.
- **T4a.2's roll-identity guarantee unaffected.** ✓ —
  `scenarios/test_tier4a_counterfactual.py` passed unedited as part of
  the full battery (its fixture forms no grudges, confirmed again by
  this run: `git diff` shows that file untouched).

## What was built

- **`schedule.py`** — `sample_encounters` gains `pair_thresholds:
  Mapping[frozenset[str], float] | None = None`. A pair present in the
  mapping compares its (unchanged) roll `value` against the override
  instead of `encounter_probability`; every other pair, byte-identical
  to before. New unit test
  (`test_sample_encounters_pair_thresholds_overrides_only_the_named_pair`)
  proves exactly this: the named pair's roll value is untouched, its
  threshold/encountered flip; every other pair in the same call is
  byte-for-byte identical to a no-override call.
- **`social.py`** — `SocialStateStore.grudges()`, a public bulk
  accessor (design doc O3, ruled in the packet: "do not read `_grudges`
  from the driver"). New unit test
  (`test_grudges_lists_every_grudge_regardless_of_holder`) covers the
  empty case and multiple holders.
- **`rules.py`** — `PairwiseEncounterWeightingRule` replaces the
  rule-18 stub: `fired = severity >= threshold`, both caller-assembled;
  `result` carries `{base_probability, effective_probability}` only
  when fired (mirroring `AccumulationThresholdRule`'s
  fired-only-carries-a-result-when-relevant shape).
- **`driver.py`** — two new tunables
  (`AVOIDANCE_PROBABILITY = 0.0`, `AVOIDANCE_GRUDGE_THRESHOLD = 0.5`,
  both construction-overridable); `_grudge_severities(tick)` (every
  grudge, either direction, decayed severity — no threshold gate, so
  doctrine 3's visibility survives cooling); `_avoidance_thresholds`
  (the W1 override mapping — severity above the floor AND not
  `grudge_cooled`); `_evaluate_avoidance` (the per-roll rule-18
  evaluation, no-op for grudge-free pairs); wired into `_run_tick`
  alongside rule 17's overlay lookup, gated by the rule's own
  `enabled()` check (a real, driver-owned toggle — disabling rule 18
  means `_grudge_severities` is never even computed, so a disabled rule
  cannot silently still avoid).

## Findings

1. **No deviations from the ruled design.** W1–W5 implemented as
   specified in the packet's pinned decisions; `grudges()` was added as
   directed rather than reaching into `_grudges`.
2. **Severity in the primary rung's assertions is checked as `> 0.5`,
   not pinned to the exact tick-0 value (0.8).** Over 10 ticks against
   672/336-tick half-lives the decay is negligible (~0.0011 by tick 9),
   but asserting the literal float would make the test brittle against
   any future half-life retuning that isn't otherwise a behavior
   change worth failing this rung over. The exact-value check exists
   instead in the cooling test, where the range (0.2, 0.5) is the
   entire point.
3. **The cooling test's tick range (390–410) is derived from the actual
   half-life constants**, not guessed — computed by hand from
   `_decay`'s formula (`claims.py:94-95`,
   `value * 0.5 ** (elapsed / half_life)`) to land comfortably inside
   the cooling band (below 0.5, above 0.2) for the whole 20-tick window,
   so the test has margin against floating-point noise rather than
   sitting on a boundary.
