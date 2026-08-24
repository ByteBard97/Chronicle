# Lane 37 delivery report — T4a.2 counterfactual (roll-identity + narrative)

**Delivered:** `a674b0e` — `scenarios/test_tier4a_counterfactual.py`.
Pure scenario-test lane, no production code touched (`git diff
chronicle/` is empty).

## Acceptance, per criterion

- **`uv run pytest -q` green (lane-36 count + new test), ruff clean.**
  ✓ — 215 passed, 0 failed, 0 xfailed (213 from lane 36 + 2 new).
  `uv run ruff check .`: clean.
- **Both assertions pass as written; the identity scan is a reusable
  helper.** ✓ — `rolls_outside()` is a standalone module-level function
  (not inlined in the test body), with a docstring naming it as the
  exact predicate the dashboard's future §3.9 merge-scan tool should
  reuse (design doc F4) rather than reimplementing "outside the
  mourner's changed sites" independently. `_roll_key_tuple()` is the
  shared join key (tick, location_id, participants) both the scenario
  test and, eventually, that tool would scan by.
- **No production-code changes.** ✓ — only the one new file; verified
  via `git status --short` before committing.

## What was built

Two-driver harness per design doc T7: `_run()` builds a driver, forms
the kinship edge, injects the death, has sven witness it, runs the tick
loop, and closes — called twice with identical construction except one
extra kwarg (`disabled_rules=(SCHEDULE_WRITE_BACK,)` for Run B). Same
`seed_id`, same schedule fixture, same `mourning_triggers`/
`mourning_location`/`mourning_duration_ticks` — literally the same
function, one flag different, per the packet's "one fixture, one config
flag" discipline.

- **Primary (roll-identity) assertion**: `rolls_outside(rolls,
  mourner_id)` filters `encounter_rolled` records to those whose
  `{npc_a, npc_b}` excludes the mourner, keyed by `(tick, location_id,
  frozenset(participants))`. The test asserts the key sets are IDENTICAL
  between A and B (every non-mourner pair rolled at exactly the same
  ticks/sites in both runs) and, for every shared key,
  `value`/`threshold`/`encountered`/`roll_key` are all equal. Verified
  non-vacuous: the control pair (camilla, delphine) at an unrelated
  tavern produces 15 identical rolls (one per tick) in both runs —
  confirmed by direct inspection before finalizing the test, not just
  by the test passing.
- **Companion (narrative) assertion**: `driver.belief_of(_PRIEST,
  _CLAIM_ID)` and `driver.belief_of(_MARKET_NPC, _CLAIM_ID)` after each
  run — Run A: priest informed, market regular not (sven is overlaid to
  the temple from tick 0 and the run window, 15 ticks, sits entirely
  inside the 30-tick mourning duration, so he never returns to the
  market); Run B: the reverse.

## Findings

1. **No production-code changes were needed** — the packet flagged this
   as the expected outcome and it held. The two-driver harness, the
   roll-identity scan, and the narrative check are all expressible
   entirely from the existing `Driver`/`FrameLogReader` surface lane 36
   landed.
2. **The run window was sized deliberately short (15 ticks) against a
   30-tick mourning duration** so the narrative assertion doesn't need
   to reason about restoration at all — sven simply never returns to
   the market within the test's observed span in Run A. This keeps the
   companion assertion simple and unambiguous (priest informed / market
   never informed, rather than "informed earlier"), at the cost of not
   also exercising restoration-then-later-market-arrival in this same
   test — lane 36's rung already covers restoration mechanics directly,
   so this isn't a coverage gap, just a deliberate scope split between
   the two lanes.
3. **`rolls_outside`/`_roll_key_tuple` are written as free functions,
   not private to a single test**, specifically so a later M5 tooling
   lane building the §3.9 merge-scan can import or port them directly
   rather than re-deriving the same predicate independently (F4's
   concern: the scenario-test definition and the dashboard tool's
   definition of "outside the mourner's changed sites" must not drift
   apart).

## Milestone note

This closes Tier 4a's executable surface: T4a.1 (lane 36) and T4a.2
(this lane) are both green. Rule 17 is live; rules 1–17 of 19 are now
implemented in the registry (12/13/18/19 remain stubs). The tier's
forced tooling (schedule diff §3.8, run comparison §3.9) is not part of
either lane — both are dashboard-side M5 work, queued behind this.
