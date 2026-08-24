# Lane 43 — Tier 4b: pairwise encounter weighting (rule 18) + T4b.1 (Track A)

**Status:** Ready to start immediately. The design is accepted and ruled
(`docs/design/tier-4b-avoidance.md` — decisions W1–W5 are your spec;
overseer review in `docs/work-packets/reviews/2026-08-23-lane-40/`).
Tier 4a's machinery is landed (lanes 36/37).

**Effort:** medium (override mechanics + rule + rung test).

## Context

T4b.1 (frozen, `docs/scenario-ladder.md:86-89`): a strong grudge
between a pair; the pair's weight drops per the named avoidance rule;
encounters between them cease at the shared tavern block; the weight
delta is visible in the trace, not a hidden multiplier. Tier 4a's
distinction holds: 4a changed who's at the table; 4b changes whether
tablemates talk.

## Read first (in order)

1. `docs/design/tier-4b-avoidance.md` — the ruled design. Deviations
   come back as findings.
2. `docs/scenario-ladder.md:86-89` — the frozen rung text.
3. `chronicle/schedule.py` — `sample_encounters` (:119-179; the
   `encounter_probability` seam), the per-pair roll loop (the T4
   precondition comment — your override must not perturb other pairs'
   rolls).
4. `chronicle/driver.py` — `_run_tick`'s per-tick consultation shape
   (lane 36's overlay lookup precedent), the tunables block.
5. `chronicle/social.py` — `grudge_at`/`grudge_cooled` (:280-307),
   `grudges_of`/`grudge` accessors (:485-491), the `_grudges` store.
6. `chronicle/rules.py` — the rule-18 stub + `ScheduleWriteBackRule`'s
   real-rule shape.
7. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions (ruled — see the design doc + review)

- **Per-pair threshold replacement (W1):** `sample_encounters` gains
  `pair_thresholds: Mapping[frozenset[str], float] | None = None`;
  listed pairs compare against the override, everyone else against the
  caller's `encounter_probability`, byte-identical to today.
- **`AVOIDANCE_PROBABILITY = 0.0`** (ruled O1) — `encountered` is
  never true for an avoiding pair; the rung asserts exactly.
- **`AVOIDANCE_GRUDGE_THRESHOLD = 0.5`** (ruled O2) — placeholder
  tunable, strictly above `forgiveness_threshold`'s 0.2.
- **Driver computes per tick (W1):** `_active_avoidance_pairs(tick)`
  scans the grudge store (`grudge_at(...).severity >= threshold` and
  not `grudge_cooled`), keyed `frozenset((holder, target))` — mutual
  grudges collapse to one key (ruled O4).
- **Public accessor (ruled O3):** `SocialStateStore` grows a public
  `grudges()` iterator — do not read `_grudges` from the driver.
- **No new record type, no new RNG purpose (W2/W4):** the
  `encounter_rolled` row's lowered `threshold` is the visible delta;
  the paired `rule_evaluated` row (one per avoiding pair per rolled
  tick, `fired: true`, the grudge named in `inputs`, base vs. effective
  probability in `result`) carries the reason. Grudge-free pairs
  produce no rule-18 row at all.
- **Rule 18 registers replacing the stub** with a real (driver-owned)
  toggle: disabling suppresses the override itself.
- **Cooling is read-time (W3):** nothing stored; avoidance stops when
  decayed severity drops below the threshold — the rule rows simply
  stop appearing.

## Task

1. `chronicle/schedule.py`: the `pair_thresholds` parameter.
2. `chronicle/social.py`: the public `grudges()` iterator (+ unit test).
3. `chronicle/driver.py`: `_active_avoidance_pairs`, the tunables, the
   per-tick wiring into `sample_encounters`, rule-18 evaluation +
   emission.
4. `chronicle/rules.py`: `PairwiseEncounterWeightingRule` replaces the
   stub.
5. `scenarios/test_tier4b_avoidance.py` — the T4b.1 rung per W2:
   grudged pair sharing a tavern block (every row `encountered: false`,
   `threshold == 0.0`, a same-tick rule-18 row naming the grudge) +
   **control pair** at the same block with no grudge (base threshold,
   encounters vary) — proving per-pair, not location-wide. Plus a
   cooling case if cheap (decay past the threshold → avoidance stops).
6. Suite green; no behavior change with no qualifying grudges (the
   regression proof: the full suite unedited).

## Acceptance

- `uv run pytest -q` green (218 + your new tests), ruff clean.
- The rung + control pair pass as written; cooling behavior per W3.
- No new record types; no new RNG purposes; no schema edits.
- T4a.2's roll-identity guarantee unaffected (lane 37's test still
  passes unedited — the suite is the proof).

## File boundaries

**Create:** `scenarios/test_tier4b_avoidance.py`

**Edit:** `chronicle/schedule.py`, `chronicle/social.py`,
`chronicle/driver.py`, `chronicle/rules.py` + the pre-authorized
mechanical edits class (registry count migration; idiom-correct test
homes)

**Do not touch:** frozen/coordinator docs, `rng.py`, other
`scenarios/` files, `dashboard/`, `runs/`

## Conventions

- Match the engine idiom; named constants with rule citations.
- **Local commits OK** (path-scoped); never push.
- File a delivery report on disk: delivered, acceptance per criterion
  with command tails, findings list.
