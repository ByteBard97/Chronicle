# Lane 36 delivery report — Tier 4a schedule write-back (rule 17, T4a.1)

**Delivered:** `76751f7` — the write-back core (rule 17) and the T4a.1
mourning rung, per the ruled design (`docs/design/tier-4a-schedule-write-back.md`
decisions T1–T7, overseer review `reviews/2026-08-23-lane-33/`).

## Acceptance, per criterion

- **`uv run pytest -q` green (206 + new tests), ruff clean.** ✓ — 213
  passed, 0 failed, 0 xfailed (206 prior + 4 rung tests +
  3 `effective_schedule_at` unit tests). `uv run ruff check .`: clean.
- **`schedule_rewrite` records match §3:96 field-for-field.** ✓ —
  asserted directly in the rung:
  ```python
  assert rewrite["npc_id"] == _MOURNER
  assert rewrite["location_id"] == _TEMPLE
  assert rewrite["start_tick"] == 0
  assert rewrite["end_tick"] == _MOURNING_DURATION
  assert rewrite["cause"] == "mourning"
  assert rewrite["trigger_event_key"] == {"save_uuid": _SAVE, "generation": 0, "seq": 1}
  assert rewrite["rule"] == SCHEDULE_WRITE_BACK
  ```
- **The rung asserts pass as written, incl. the T4 precondition and the
  reconstruction-in-window check.** ✓ — four scenario tests in
  `scenarios/test_tier4a_mourning.py`:
  1. Overlay inserted at the trigger tick, restored after `end_tick`
     (mechanical ground truth: `encounter_rolled` records, not a
     re-derivation of presence) — **and** the T4 precondition: camilla
     and delphine, co-present with the mourner at his own base site, are
     still grouped and rolled there exactly as if he'd never left.
  2. The log-derived latch: sven corroborating a second, independent
     witness's testimony about the same death re-runs rule 17's hook
     (same call site as rule 16) but declines — exactly one
     `schedule_rewrite` event in the whole run, one fired row and one
     declined row (`already_mourning: true`) both naming sven.
  3. `state_at` reconstruction inside the mourning window (tick 15, past
     the first keyframe at tick 9) shows sven at the temple; after the
     window (tick 30), restored to the house. **Verified this actually
     depends on the fix**: monkeypatched `effective_schedule_at` to the
     pre-T3 base-only behavior and reran — the test fails, confirming it
     isn't passing by accident.
  4. The regression half: no `mourning_triggers` mapping registered ->
     zero `schedule_rewrite` events, zero rule-17 `rule_evaluated` rows.
  Plus 3 focused unit tests for `effective_schedule_at` itself in
  `chronicle/tests/test_schedule.py` (override-only-the-overlay-npc,
  restoration-is-automatic, no-overlays-is-plain-base).
- **No new RNG purposes; no other schema edits (§3:96 is filled).** ✓ —
  `chronicle/rng.py` untouched (`git diff chronicle/rng.py` empty); no
  roll anywhere in the mourning trigger or overlay mechanism, per the
  design doc's own argument (deterministic kinship + belief-acquisition
  trigger, no dice). No `docs/frame-log-schema.md` edit — §3:96 was
  already filled by the coordinator's O3 ruling before this lane started.

## What was built, file by file

- **`chronicle/events.py`** — `ScheduleRewrite(Event)`: the §3:96 fields,
  with `trigger_event_key` represented as three flat fields
  (`trigger_save_uuid`/`generation`/`seq`) rather than importing
  `claims.EventKey` — this module (layer 1) doesn't depend on layer 2
  types, and every other event class here is already flat.
- **`chronicle/schedule.py`** — `effective_schedule_at(base, overlays,
  tick)`: base blocks covering `tick`, with any NPC under an overlay
  covering `tick` having ALL their base presence replaced (total
  override, never a merge). This is the *one* place presence-with-
  overlays is computed — both `driver._run_tick` and
  `framelog.state_at` call it, so they can't drift apart (the design
  doc's explicit requirement). Also added the code comment at
  `sample_encounters`'s roll loop naming the per-pair-independence
  precondition T4a.2 will depend on (lane 37), since a future refactor
  that rolls once per site instead of per pair would silently break it.
- **`chronicle/framelog.py`** — three changes: (1) `event_payload`'s
  `schedule_rewrite` branch; (2) `serialize_state`'s `"schedules"` key
  drops the `covers(tick)` filter — the base schedule is immutable under
  the overlay design, so keyframes now capture it whole, closing the
  latent gap the design doc's F2 finding named (a block not covering the
  keyframe's own tick could previously be missing from every keyframe
  that would ever capture it); (3) `state_at` gains a `schedule_rewrite`
  branch in its existing events-stream scan (collecting overlays as
  ordinary `ScheduleBlock`s) and the final return now computes
  `effective_schedule_at(schedule, overlays, tick)` instead of returning
  the raw keyframe schedule.
- **`chronicle/rules.py`** — `ScheduleWriteBackRule` replaces the
  rule-17 stub: `fired = kin and not already_mourning`, both booleans
  caller-assembled (never a store query inside `evaluate()`). Real
  toggle (lane-19 precedent for driver-owned rules) — disabling it
  suppresses the rewrite itself, which is what lane 37's Run B needs.
- **`chronicle/driver.py`** — `mourning_triggers` (claim_kind -> the
  slot naming the deceased; `npc_death` claims don't carry this by
  default, per the design doc's F3 finding, so the rung's fixture adds
  it explicitly), `mourning_location`, `mourning_duration_ticks`
  (default `MOURNING_DURATION_TICKS = 72`, the coordinator-ruled O2
  placeholder — the rung overrides it to 20 for a faster test, which the
  constructor already supports); `_schedule_overlays` derived at
  `__init__` from the event log (same start-from-keyframe-safe pattern
  as `_deceased`); `_mourning_already_triggered` (the log-derived latch,
  scanning the event log directly rather than an in-memory flag) and
  `_evaluate_mourning` (the hook, wired at the exact three call sites
  rule 16 uses: `witness`, `retell`'s first-hearing branch,
  `corroborate`); `_run_tick` now computes presence through
  `effective_schedule_at`.
- **`scenarios/test_tier4a_mourning.py`** — the T4a.1 rung, described
  above.

## Findings

1. **No deviations from the ruled design.** T1–T7 implemented as
   specified; the `mourning_triggers` authoring note (F3/O1) is used
   exactly as the packet described (the rung's death claim carries an
   explicit `"deceased"` slot).
2. **`serialize_state`'s `tick` parameter is now unused inside the
   function body** (only the docstring references it) — the `covers(tick)`
   filter it fed was the only thing it did there. Left the parameter in
   place: removing it would touch every call site for no behavior gain,
   and it still documents the keyframe's "as of tick" framing for the
   claims/social snapshot fields. Not a boundary concern (only
   `framelog.py` itself), flagging for the record in case a future lane
   wants to clean it up.
3. **The reconstruction test's fix-dependency was verified directly**,
   not just argued: monkeypatching `effective_schedule_at` back to
   base-only behavior makes
   `test_t4a1_state_at_inside_the_mourning_window_shows_the_overlay`
   fail, confirming the assertion isn't passing for an unrelated reason.
4. **`corroborate()`'s mourning hook is latch-blocked in practice for
   this rung** (sven is already mourning by the time he corroborates) --
   exactly as the design doc anticipated ("in practice usually
   latch-blocked... but a kinship edge formed after first learning is a
   real case this catches"). No engine gap; noting it so lane 37 or a
   future rung doesn't expect corroborate-triggered mourning to be the
   common path.
