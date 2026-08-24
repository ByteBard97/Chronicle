# Lane 39 — StatusChanged event class (Track A, micro-lane)

**Status:** Ready to start immediately; small filler. Backlog item from
lane 26 (the T3.5 Thane event anchors on `RumorHeard` for want of a
status event type) and lane 33's fixture conventions.

**Effort:** small (one event class + serialization branch + tests).

## Context

Status changes (Thane-hood, role appointments, faction rank) currently
anchor claims on `RumorHeard` — the lane-23/26 precedent — which works
but conflates "someone said something" with "the world's roster
changed." A `status_changed` event class gives Tier 5 (roles/vacancy)
and future reputation fixtures an honest anchor. Schema §3's event
table gets a new row (coordinator-owned — the packet authorizes it via
the coordinator, who amends at dispatch).

## Read first

- `chronicle/events.py` — the event dataclass idiom (NPCDied etc.),
  `origin` handling.
- `chronicle/framelog.py` — the event-serialization branch idiom (the
  lane-24 `escalation_warning` precedent).
- `docs/frame-log-schema.md` §3 — the event table (the coordinator
  fills the row at dispatch; fields below).
- `chronicle/tests/` — event/serialization test idiom.

## Pinned fields (coordinator-set; the schema row mirrors this)

`npc_id` (string), `status_kind` (string — e.g. `"thane"`,
`"role_appointed"`), `detail` (string — e.g. hold/role name),
`location_id` (string | null).

## Task

1. `chronicle/events.py`: the `StatusChanged` dataclass per the pinned
   fields.
2. `chronicle/framelog.py`: the serialization branch (in-bounds per
   the lane-24 precedent).
3. Tests: round-trip write/read; reader tolerance (older runs
   unaffected); a scripted `driver.inject_event(StatusChanged(...))`
   flowing through `driver.witness` off its canonical key (the
   T3.5-pattern anchor, now honest).
4. No changes to existing scenario tests (the `RumorHeard` anchors
   stay — migration is a later call).

## Acceptance

- `uv run pytest -q` green (206+), ruff clean.
- The event round-trips; the schema §3 row (filled by the coordinator
  at dispatch) matches the emitted shape field-for-field.

## File boundaries

**Edit:** `chronicle/events.py`, `chronicle/framelog.py`, the
idiom-correct test files

**Do not touch:** frozen docs (the coordinator fills the schema row),
scenario tests, `dashboard/`, `runs/`

## Conventions

- **Local commits OK** (path-scoped); never push.
- File a delivery report on disk.
