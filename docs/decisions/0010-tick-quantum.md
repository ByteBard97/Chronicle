---
status: accepted
date: 2026-08-22
---

# 0010: Tick quantum and constant rebaseline

## Context

`docs/dashboard-build-plan.md` §1 prerequisite 4 flags this as blocking and
non-cosmetic: the codebase has two clocks with no stated relationship.
`chronicle/fixtures/whiterun_schedule.py`'s `ScheduleBlock.start_tick`/
`end_tick` (int, `chronicle/schedule.py`) and `chronicle/claims.py`'s /
`chronicle/social.py`'s `gamets` (float, used throughout for
`last_rehearsed`, `first_learned`, decay elapsed-time math, and the rumor
stage machine) have never been pinned to the same unit. Landing a quantum
means deciding what a tick *is*, in real terms, and then re-deriving every
time constant that was previously a dimensionless placeholder.

`chronicle/claims.py:57-67` carries four such placeholders, explicitly
marked as such:

```
CONFIDENCE_DECAY_HALF_LIFE = 500.0
VERBATIM_DECAY_HALF_LIFE = 200.0
GIST_DECAY_HALF_LIFE = 2000.0
RUMOR_DORMANT_AFTER = 5000.0
```

Their docstrings (and `docs/decisions/open-questions.md`'s CHIM
fork-threshold note) already say these are "tunable to be set empirically,"
not derived from any source report. That status doesn't change here — this
ADR re-expresses the same placeholders in real units, it doesn't newly
derive them from evidence. What changes is that "500" stops being an
opaque number and becomes "~3 game-days," which is a number a human (or a
scenario author) can sanity-check against intent.

**The fixture is explicitly not evidence for the quantum and is out of
scope for this change.** `chronicle/fixtures/whiterun_schedule.py`'s
docstring already disclaims schedule realism — its blocks (0-200,
0-1000, etc.) are scaffolding sized to the tick ranges the existing
`scenarios/` suite exercises, not a daily routine. At the quantum this ADR
adopts, those blocks read as an 8-day court gathering and a 41-day tavern
shift — semantically odd, functionally harmless, since the scenarios that
use them run fixed tick ranges the fixture already covers. No lane owns
rewriting that fixture into a realistic daily routine; it stays as-is.

`docs/v0.1-spec.md` rules 5/6/16 set the *qualitative* intent this
rebaseline must preserve, not numbers to hit:

- Rule 5: verbatim strength decays faster than gist strength (fuzzy-trace
  theory) — the source of `VERBATIM_DECAY_HALF_LIFE < GIST_DECAY_HALF_LIFE`.
- Rule 6: confidence decays with time since last rehearsal — the source of
  `CONFIDENCE_DECAY_HALF_LIFE` existing at all.
- Rule 16: the rumor stage machine `unheard -> heard -> repeated ->
  dormant -> forgotten` — the source of `RUMOR_DORMANT_AFTER` and
  `RUMOR_FORGOTTEN_GIST_THRESHOLD`.

`docs/scenario-ladder.md` (not yet implemented as pytest tests, but the
forcing tiers this build works toward) supplies concrete anchors the new
values should not contradict:

- **T0.2 Decay** — 30 quiet game-days, asserts stage is still `heard`,
  "not dormant yet."
- **T2.1 Spread** — 10 game-days, cast ≈ 25 (this is the run
  `docs/ui-spec.md` sizes its 10⁵-10⁶ trace-row estimate against).
- **T2.5 Dormancy and reactivation** — 90 quiet game-days after spread;
  the rumor must have migrated to `dormant` well before this window ends,
  so a retelling has something to reactivate.

## Decision

**One tick = one game-hour.** Equivalently: **`tick` (int, `schedule.py`)
and `gamets` (float, `claims.py`/`social.py`) are the same clock, same
unit** — 1 tick = 1 gamets = 1 game-hour. This is the load-bearing part of
this ADR: Lane 2's frame-log timestamps and Lane 4's driver tick loop
advance one clock, not two that happen to correlate. A `gamets` value of
`1050.0` and a `tick` value of `1050` refer to the same instant.

Derived cadence: **24 ticks = 1 game-day** (matches the keyframe cadence
`docs/ui-spec.md` already assumes: "K default one game-day"). **240 ticks
= 10 game-days.**

### Rebaselined constants (`chronicle/claims.py`)

All four are still placeholders in the same "tunable, not derived" sense
the original comments stated — this rebaseline changes their *units*, not
their epistemic status. Each is chosen to preserve rule 5/6/16's
qualitative shape and to sit sensibly against the T0.2/T2.5 anchors above,
not to hit a specific research-derived number (none exists).

| Constant | Old (unitless) | New (ticks) | Derivation |
|---|---|---|---|
| `VERBATIM_DECAY_HALF_LIFE` | 200.0 | **72.0** | ~3 game-days (24×3). Exact wording should fade within a few days — fastest of the three, preserving rule 5's ordering. |
| `CONFIDENCE_DECAY_HALF_LIFE` | 500.0 | **168.0** | ~7 game-days (24×7, one week). A belief nobody has rehearsed in a week has lost roughly half its confidence — rule 6, positioned between verbatim and gist per fuzzy-trace theory. |
| `GIST_DECAY_HALF_LIFE` | 2000.0 | **1440.0** | ~60 game-days (24×60). Gist ("something bad happened to the Jarl") should outlive both verbatim and confidence by a wide margin — rule 5's central claim — while still eventually crossing `RUMOR_FORGOTTEN_GIST_THRESHOLD` over a multi-month horizon rather than never. |
| `RUMOR_DORMANT_AFTER` | 5000.0 | **1080.0** | ~45 quiet game-days (24×45). Chosen to sit strictly between the T0.2 anchor (30 quiet days = 720 ticks, must still read as "not dormant yet") and the T2.5 anchor (90 quiet days = 2160 ticks, must have reached "dormant" well before the window closes so a later retelling has something to reactivate). The old value, 5000 ticks ≈ 208 days at this quantum, was answering the build plan's flagged question ("is that the intended dormancy horizon?") with "no" — 208 quiet days is far outside any scenario-ladder window this system is meant to exercise. |

`RUMOR_FORGOTTEN_GIST_THRESHOLD = 0.05` is a dimensionless strength floor,
not a time constant — unchanged. `RETELL_CONFIDENCE_DECAY`,
`RETELL_VERBATIM_DECAY`, `RETELL_GIST_DECAY`, and `WITNESS_CONFIDENCE` are
per-event multiplicative factors (applied once per retelling, not against
elapsed time) — also unchanged; they carry no tick unit to rebaseline.

**Sanity check against the new values:** at the T2.5 anchor (90 quiet
days = 2160 ticks after spread), a belief with `GIST_DECAY_HALF_LIFE =
1440` has decayed to `0.5^(2160/1440) ≈ 0.35` of its starting gist
strength — comfortably above `RUMOR_FORGOTTEN_GIST_THRESHOLD = 0.05` for
any reasonable starting strength, so the scenario can exercise "dormant"
and "forgotten" as genuinely distinct outcomes rather than always
co-occurring.

**Rule 16 ordering check:** `stage_at()` checks "forgotten" before
"dormant" (a belief that never got rehearsed can skip straight to
forgotten even without a long quiet gap), so rule 16's stated sequence
`... -> dormant -> forgotten` is a *typical* path, not a hard invariant —
but the constants should make the typical path typical. Solving for the
starting `gist_strength` at which a belief crosses
`RUMOR_FORGOTTEN_GIST_THRESHOLD` at the same elapsed time
`RUMOR_DORMANT_AFTER` triggers: the old constants (2000/5000) cross over
at starting gist ≈ 0.28 — over a quarter of beliefs by starting strength
would skip "dormant" entirely. The new constants (1440/1080) cross over
at starting gist ≈ 0.084 — only unusually weak beliefs skip "dormant," so
the rebaseline incidentally makes the documented rule-16 sequence the
common case rather than close to a coin-flip, on top of fitting the
T0.2/T2.5 anchors.

No other `chronicle/` module has time-denominated constants. Verified with
`grep -rn '^[A-Z][A-Z0-9_]* *[:=]' chronicle/`, which catches every
module-level constant assignment in the package (not just the narrower
`^[A-Z_]* = ` pattern, which would miss a name containing a digit):
`schedule.py` (`ENCOUNTER_PROBABILITY = 0.5`, dimensionless), `social.py`
(`GRUDGE_EMOTIONAL_WEIGHT`, `GRUDGE_EVIDENTIARY_WEIGHT`,
`REPUTATION_PRIOR_ALPHA/BETA`, `REPUTATION_WEIGHT_BY_KIND`, all
dimensionless weights/priors — no grudge-cooling clock exists yet; that's
Tier 3, out of scope here), `claims.py`'s own `RETELL_*`/
`WITNESS_CONFIDENCE` (dimensionless, covered above), and no constants at
all in `propagate.py`, `events.py`, or `fixtures/`.

## Consequences

- **Ticks-per-10-game-days = 240.** This is the figure `docs/ui-spec.md`'s
  10⁵-10⁶ trace-row estimate for a 25-NPC, 10-game-day Tier-2 run should be
  checked against (Lane 2/M0's concern, not resolved here — just supplied).
- Any code or docs that referenced the old constants' magnitudes directly
  (none found outside `chronicle/tests/test_claims.py`, which imports the
  named constants symbolically rather than hardcoding their values) is
  unaffected.
- `chronicle/fixtures/whiterun_schedule.py` is unchanged and stays
  semantically odd (8-day court scene, 41-day tavern shift) under this
  quantum — a known, accepted consequence, not a defect this ADR should
  fix. A realistic daily-routine fixture is future work, unowned by any
  current lane.
- Future scenario-ladder tests (T0.2, T2.1, T2.5) should use game-day-based
  tick counts (`24 * N`) rather than bare tick literals, so their intent
  reads directly off the assertion.

## Related

`docs/dashboard-build-plan.md` §1 prerequisite 4 (the forcing requirement).
`docs/v0.1-spec.md` rules 5, 6, 16. `docs/scenario-ladder.md` T0.2/T2.1/T2.5.
`docs/decisions/open-questions.md`'s "tunable to be set empirically" note,
which this ADR's constants inherit rather than override.
