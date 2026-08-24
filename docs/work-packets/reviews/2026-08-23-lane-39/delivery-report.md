# Lane 39 delivery report — StatusChanged event class

**Delivered:** `5362cbc` — `chronicle/events.py`'s `StatusChanged`
dataclass, `chronicle/framelog.py`'s serialization branch, and three
tests. Schema §3:97 was already filled (coordinator, pre-dispatch) — no
schema edit in this lane.

## Acceptance, per criterion

- **`uv run pytest -q` green (206+), ruff clean.** ✓ — 218 passed
  (215 prior + 3 new), 0 failed, 0 xfailed. `uv run ruff check .`: clean.
- **The event round-trips; the schema §3 row matches the emitted shape
  field-for-field.** ✓ — `test_event_payload_maps_status_changed` checks
  the mapping directly; `test_status_changed_round_trips_write_and_read`
  writes through `FrameLogWriter` and reads back through
  `FrameLogReader`, confirming all four fields (`npc_id`, `status_kind`,
  `detail`, `location_id`, including the `None` case) survive the
  JSONL round trip unchanged. Fields match §3:97 exactly: `npc_id`
  (string), `status_kind` (string), `detail` (string), `location_id`
  (string | null).

## What was built

- **`StatusChanged(Event)`** — four fields, `location_id` defaulting to
  `None` (matching `NPCDied`'s optional-location convention). Docstring
  states its purpose plainly: an honest anchor for roster/status
  changes, distinct from `RumorHeard`'s "someone said something," and
  explicitly notes existing `RumorHeard`-anchored fixtures (lanes 23/26)
  are not migrated by this class landing — migration is a later call,
  per the packet.
- **`framelog.py`'s `event_payload` branch** — mechanical, field-for-
  field, same shape as the `EscalationWarning`/`ScheduleRewrite`
  branches immediately above it.
- **Three tests**: the payload-mapping unit test and round-trip test in
  `chronicle/tests/test_framelog.py` (alongside the existing
  `RumorHeard` payload test); and
  `test_a_belief_can_be_witnessed_off_a_status_changed_canonical_key`
  in `chronicle/tests/test_driver.py`, which injects a `StatusChanged`
  event and calls `driver.witness()` with its canonical key directly
  (the exact T3.5-pattern anchor, now exercised honestly instead of via
  `RumorHeard`) — confirms the claim's `canonical_event_key` round-
  trips, exactly one event and one `belief_formed` record exist, and
  the `belief_formed` record's `canonical_event_key` matches.

## Findings

1. **No explicit "reader tolerance for older runs" test added.**
   `state_at`'s events-stream scan already only reads specific known
   fields per `event_type` (the `schedule_rewrite` check added in
   lane 36 is the only type-specific branch there); any other
   `event_type`, known or unknown, is silently skipped for overlay
   purposes without affecting reconstruction. This tolerance already
   exists structurally rather than needing a new type-specific test —
   `test_reader_ignores_unknown_trace_record_types` covers the
   equivalent trace-stream case. Flagging the reasoning rather than
   adding a redundant test.
2. **No engine call site emits `StatusChanged` yet** (same status as
   `EscalationWarning` before lane 24 wired it, and `ScheduleRewrite`
   before lane 36) — this lane is the type definition + serialization
   only, per the packet's explicit scope ("no changes to existing
   scenario tests... migration is a later call").
