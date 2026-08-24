# Lane 51 — role roster in the log (`role_installed`) (Track A, micro-lane)

**Status:** Ready to start immediately. The M6 role inspector (lane 52)
needs the role roster reconstructable from a run's log; today roles
live only in fixture-side construction (lane 47's design: vacancy
derives from `npc_died`, lapse/succession from `status_changed` — but
the *roster itself* isn't in the log).

**Effort:** small (one emission point + replay + tests).

## Context

Lane 47's design (S3) made vacancy replayable from `NPCDied` events
and lapse/succession from `status_changed` — deliberately no keyframe
entries. The missing piece: **role definitions**. A `role_installed`
event (schema §3:98, fields already filled by the coordinator) emitted
once per role at installation closes the loop — readers reconstruct
roster + vacancy + succession from the log alone.

## Read first

- `docs/frame-log-schema.md` §3:98 — the `role_installed` fields
  (`role_id`, `title`, `institution_id`, `duties`, `holder_id`).
- `chronicle/roles.py` — the `Role`/`Duty` shapes (lane 47).
- `chronicle/driver.py` — where roles are installed (construction /
  fixture install path).
- `chronicle/framelog.py` — the event-serialization branch idiom +
  `state_at`'s replay branches (lane 36's `schedule_rewrite` branch is
  the model).
- `docs/work-packets/reviews/README.md` — governance.

## Task

1. `chronicle/events.py`: the `RoleInstalled` dataclass (§3:98 fields)
   + the framelog serialization branch.
2. `chronicle/driver.py`: emit `role_installed` on install (run start;
   any later installs too).
3. `chronicle/framelog.py`: `state_at` rebuilds the role roster from
   `role_installed` events (roster at T = installs ≤ T), so
   reconstruction shows roles alongside the existing vacancy/succession
   replay.
4. Tests: round-trip; roster reconstructed from the log alone at
   arbitrary T (install, then vacancy via `NPCDied`, then succession
   via `role_appointed` — the full lifecycle visible in one
   reconstruction); older runs (no `role_installed`) tolerate cleanly.
5. Suite green; the T5 rungs stay green unedited (their fixtures emit
   the new event — verify the existing tests tolerate it; if one
   counts events exactly, report it, don't edit silently).

## Acceptance

- `uv run pytest -q` green (240 + your new tests), ruff clean.
- `role_installed` records match §3:98 field-for-field.
- Full role lifecycle reconstructs from the log alone — covered by test.
- No new RNG purposes; no other schema edits (§3:98 is filled).

## File boundaries

**Create:** nothing new beyond the event class's tests

**Edit:** `chronicle/events.py`, `chronicle/driver.py`,
`chronicle/framelog.py` + the pre-authorized mechanical edits class

**Do not touch:** frozen/coordinator docs (§3:98 is filled),
`chronicle/roles.py` (read-only — gaps are findings), `scenarios/`
(except if a test's exact event count needs the pre-authorized class),
`dashboard/`, `runs/`

## Conventions

- Match the engine idiom.
- **Local commits OK** (path-scoped, atomic `add && commit`); never push.
- File a delivery report on disk.
