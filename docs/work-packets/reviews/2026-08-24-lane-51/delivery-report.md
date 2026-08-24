# Lane 51 delivery report — role roster in the log (`role_installed`)

**Delivered:** `b357a46` — `RoleInstalled` (events.py), the
`role_installed` serialization branch and `state_at` roster/vacancy/
succession replay (framelog.py), `Driver.install_role()` (driver.py),
plus tests and a mechanical follow-on fix to the north-star fixture.

## Acceptance, per criterion

- **`uv run pytest -q` green (240 + new tests), ruff clean.** ✓ — 249
  passed, 0 failed, 0 xfailed (246 prior + 3). `uv run ruff check .`:
  clean.
- **`role_installed` records match §3:98 field-for-field.** ✓ — unit
  test asserts the mapping directly (`role_id`, `title`,
  `institution_id`, `duties` as `[{"name", "lapse_status_kind"}, ...]`,
  `holder_id`); a round-trip test writes through `FrameLogWriter` and
  reads back through `FrameLogReader`, confirming every field survives
  the JSONL round trip unchanged, including the empty-duties case.
- **Full role lifecycle reconstructs from the log alone — covered by
  test.** ✓ — `test_role_roster_reconstructs_full_lifecycle_from_the_log_alone`:
  installs a role via `driver.install_role()`, kills the holder
  (triggering lane 47's vacancy cascade and lane 48's succession, both
  already-landed mechanisms, untouched here), then reconstructs via a
  **fresh** `FrameLogReader` at three points — before the death (still
  the original holder), and after (vacated *and* re-appointed to the
  ranked successor) — with no keyframe anywhere in the run. Every
  `Role` field (`title`, `institution_id`, `duties`) round-trips too,
  not just `holder_id`.
- **No new RNG purposes; no other schema edits (§3:98 is filled).** ✓
  — `git diff chronicle/rng.py docs/frame-log-schema.md` for this lane
  is empty (§3:98 was already filled by the coordinator ahead of this
  lane).

## What was built

`RoleInstalled` mirrors every other engine-internal event's shape
(`EscalationWarning`, `ScheduleRewrite`) — `duties` as a flat
`(name, lapse_status_kind)` tuple rather than importing
`chronicle.roles.Duty`, keeping `events.py` (layer 1) independent of
that layer's types. `state_at`'s existing events-stream scan (already
handling `schedule_rewrite` since lane 36) gained three more branches,
all operating on a local `roles_by_id: dict[str, Role]` built up in
file order (schema §2: file order is seq order for the events stream):
`role_installed` seeds an entry; `npc_died` vacates every role whose
*current* `holder_id` in the roster-so-far matches the dead NPC;
`status_changed` with `status_kind == "role_appointed"` re-installs the
named successor. The final roster is loaded into a fresh `RoleStore`
and attached to `ReconstructedState.roles`. `Driver.install_role()` is
the new one-stop wrapper (`self.roles.install(role)` + the event) —
calling `self.roles.install()` directly still works exactly as before,
it just leaves nothing in the log for a reader to reconstruct from.

## Findings

1. **A real seq collision, caught by the test suite, not guessed.**
   Switching `chronicle/fixtures/north_star.py` (lane 49, mine) to use
   the new `install_role()` wrapper means `build_driver()` now consumes
   two branch seqs (1 and 2) for the two roles' `role_installed` events
   before the assassination fires. `scenarios/test_north_star.py` and
   `run_north_star_demo.py` both hardcoded the assassination's
   `NPCDied` at `seq=1` — which now silently collided with the
   steward's `role_installed` event. `EventLog.append()` is idempotent
   on `(save_uuid, generation, seq)`, so the *second* write to seq=1
   (the assassination) was silently dropped as a "duplicate," and the
   Jarl's role never vacated — caught by `test_north_star_composition`
   failing outright (`assert 'jarl_balgruuf' == 'irileth'`), not by a
   silent pass. Fixed by deriving the seq from
   `driver.event_log.lineage(...)` instead of hardcoding it — the exact
   "engine-internal events consume seqs" lesson lane 24 already
   documented, now hit a second time in a different fixture. Both
   files updated (the pre-authorized mechanical-fix class); verified:
   demo run regenerated cleanly (`role_installed: 2` in its counts),
   determinism re-checked byte-identical, CLI-reconstructed at tick 0
   and tick 240.
2. **Tier 5's own dedicated test files were left untouched, on
   purpose.** `scenarios/test_tier5_vacancy.py` and
   `test_tier5_succession.py` still call `driver.roles.install()`
   directly (no `role_installed` event, no log-reconstructable roster
   for those specific runs) — not a regression, just means those two
   test files' runs don't benefit from this lane's new anchor. Updating
   them to use `install_role()` was avoidable scope (the packet didn't
   require it, and doing so would have meant editing two files
   explicitly listed as "do not touch except for count fixes" for a
   reason beyond a count fix). Flagging as a known, deliberate gap
   rather than an oversight — a trivial follow-up if the coordinator
   wants those runs' rosters reconstructable too.
3. **`chronicle/fixtures/north_star.py` isn't in either the Edit or
   Do-not-touch list** (only `chronicle/roles.py` and `scenarios/` are
   named) — I edited it to adopt the new wrapper since it's a fixture
   module I authored in lane 49, not a frozen test, and doing so
   materially improves the capstone run without touching anything the
   packet explicitly protected. Flagging the boundary judgment call for
   the record.
