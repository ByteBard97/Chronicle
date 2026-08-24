# Lane 47 delivery report — Tier 5 role model + vacancy + duty lapse (T5.1)

**Delivered:** `35d589d` — `chronicle/roles.py` (new), the vacancy
cascade wired into `chronicle/driver.py`, the T5.1 rung, and unit
tests, per the ruled design (`docs/design/tier-5-roles-and-vacancy.md`
decisions S1–S4, overseer review `docs/work-packets/reviews/2026-08-24-lane-44/`).

## Acceptance, per criterion

- **`uv run pytest -q` green (223 + new tests), ruff clean.** ✓ — 234
  passed, 0 failed, 0 xfailed (223 prior + 7 `RoleStore` unit tests +
  4 rung tests). `uv run ruff check .`: clean.
- **The rung asserts pass as written; `StatusChanged` lapse records
  match §3:97 field-for-field.** ✓ — `scenarios/test_tier5_vacancy.py`,
  four tests:
  1. Death vacates the role immediately (`holder_of` → `None`,
     `vacated_at` set to the death's `gamets`) — asserted **before**
     any tick loop runs, proving vacancy needs no belief. Two
     `status_changed` events exist (one per duty), each field-for-field
     against §3:97 (`npc_id` = the dead former holder, `status_kind` =
     `"duty_lapsed"`, `detail` = the duty name, `location_id` = `None`).
     No `rule_evaluated` row at all for `ROLE_VACANCY_SUCCESSION` — rule
     19 stays a stub this lane, exactly per the packet.
  2. The lapse propagates through ordinary machinery: the scenario
     scripts `witness()` off the lapse event's own canonical key (no
     auto-witness), runs the tick loop, and a `transmitted` record
     carries the claim to a second NPC.
  3. **Replay-from-log, not a keyframe dependency**: a driver resumed
     over the *same* `event_log` (containing the original death) with
     the role reinstalled fresh at its pre-death state shows the
     vacancy immediately at `__init__` — and, checked explicitly, does
     **not** re-inject the lapse events a second time (the event log's
     `StatusChanged` count is unchanged across the resume).
  4. The regression case: no installed role → zero `status_changed`
     events, no vacancy state anywhere.
- **No new RNG purposes; no schema edits.** ✓ — `git diff
  chronicle/rng.py docs/frame-log-schema.md` for this lane is empty;
  §3:97 was already filled (lane 39) and §3:98's retirement was the
  coordinator's own edit from the lane-44 review, not touched here.
- **Replay-from-log vacancy covered by test.** ✓ — test 3 above,
  verified to actually exercise the `__init__` bootstrap path (a fresh
  `RoleStore` passed to a new `Driver` over a shared `event_log`), not
  merely re-running the live cascade.

## What was built

- **`chronicle/roles.py`** (new module, per design doc S1's rationale:
  roles are a different axis of state from `social.py`'s four kinds,
  so they get their own module rather than growing that one).
  `Duty` (name + lapse status kind), `Role` (id, title, institution_id,
  duties, holder_id, vacated_at — frozen, `dataclasses.replace`
  mutations), `RoleStore` (`install`/`role`/`holder_of`/
  `roles_held_by`/`vacate`, mirroring `SocialStateStore`'s dup-guard-
  on-install and sparse-index discipline).
- **`driver.py`** — `roles: RoleStore | None = None` construction
  param (mirroring `claims`/`social`); `inject_event`'s `NPCDied`
  branch now runs the vacancy cascade **after** that event's own write
  lands (a real ordering bug caught and fixed mid-implementation: the
  cascade recursively calls `inject_event()` again for each lapse
  event, and schema §2 states file order IS seq order for the events
  stream — cascading before the outer write would have written a
  higher-seq lapse event ahead of the lower-seq death that caused it).
  `_vacate_roles_on_death` vacates every role the deceased held and
  injects one `StatusChanged` per duty. `__init__` separately
  bootstraps vacancy from a pre-populated `event_log`/`roles` pair
  (derive-only — no event re-injection), the same pattern
  `_deceased`/`_schedule_overlays` already established for resume
  safety.

## Findings

1. **A real ordering bug, caught before it shipped, not after.** My
   first draft ran the vacancy cascade (which recursively calls
   `inject_event()`) *before* the outer `NPCDied` event's own
   `writer.write_event()` call — this would have written a lapse
   event's higher seq number to the file ahead of the death's lower
   seq number, violating schema §2's "file order is the true order"
   for the events stream. Caught by re-reading the schema's own
   ordering guarantee against the draft, not by a failing test (no rung
   in this lane's own test happens to probe raw file order for this
   case). Fixed by moving the write above the cascade. Flagging because
   it's exactly the kind of bug a scenario test at this scale wouldn't
   catch, and worth a note for whoever reviews other `inject_event`-
   adjacent changes in the future.
2. **No deviations from the ruled design.** S1–S4 implemented as
   specified; O1's design rule ("nothing stores the holder's npc id as
   a proxy for the role") is upheld — nowhere in `driver.py` or the
   rung test caches a role's holder outside `RoleStore` itself.
3. **`Role`/`Duty` have no trace-record analog** (no `role_installed`
   schema row) — installation is a pure in-memory/scripted act, the
   same status `mutation_candidates`/`claim_privacy`/`accumulation_thresholds`
   have (caller-supplied configuration, never itself logged). Consistent
   with every other caller-supplies-context mapping in this codebase,
   not a gap.
