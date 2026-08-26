# Design prep — fork-on-disk support

**Status:** design proposal, informing a scoped-down implementation lane.
Not a ui-spec/ADR amendment — implements what those documents already
specify, doesn't change them.

Sources: `docs/ui-spec.md` §3.1 (fork semantics, already specified,
frozen), §1.1/§1.2 (physical layout + runs registry, frozen — this lane
must fit inside them, not amend them); `chronicle/framelog.py`'s
`FrameLogReader.state_at()`/`ReconstructedState` (existing read-side
reconstruction); `chronicle/driver.py`'s `Driver.__init__` (already
accepts pre-populated `claims`/`social`/`roles`/`event_log` — the
"start-from-keyframe shaping" path); `chronicle/events.py`'s
`EventLog.fork()` (the in-memory precedent — lineage by reference, not
copy); `chronicle/sync.py`'s `Resolution` (FORK/ADOPT already carry
`fork_parent_generation`/`fork_at_gamets`, currently unactionable —
`docs/design/chronicle-sync-cli-integration.md` §0).

## 0. What's already there (this is smaller than it first looked)

Checked before assuming this needs new state-reconstruction machinery —
it doesn't:

- **ui-spec.md §3.1 already specifies the semantics precisely**:
  "Appending at any historical tick T (< end of log) creates a fork —
  `(save_uuid, generation+1)`, re-simulated from T." Nothing to design
  here beyond implementation; the frozen doc already made this call.
- **State reconstruction at an arbitrary tick already exists**:
  `FrameLogReader.state_at(tick) -> ReconstructedState` (keyframe +
  replayed deltas, the same machinery every read view already uses).
- **`Driver` already accepts pre-populated stores**: `claims`, `social`,
  `roles`, `event_log` are all constructor parameters, documented as
  "start-from-keyframe shaping." A fork's new `Driver` is not a new kind
  of object — it's an ordinary `Driver` constructed with `generation =
  parent_generation + 1` and these stores seeded from the parent's state
  at the fork tick, exactly the shape the constructor already expects.

## 1. What's actually missing

- **`ReconstructedState` doesn't carry an `EventLog`** — only
  `claims`/`social`/`schedule`/`roles`. A fork's new `Driver` needs the
  parent's canonical events up to the fork tick too (so
  `EventLog.lineage()` and rule 11's belief-derived accumulators see the
  same history) — `state_at()` needs a sibling that also replays
  `EVENTS_STREAM` records into a fresh `EventLog` up to that tick, or an
  extension to `ReconstructedState` itself. Prefer extending
  `ReconstructedState` (one more field) over inventing a parallel
  function — check whichever is the smaller diff once you're in the
  code.
- **Cross-run lineage strategy — the one real decision this doc rules
  on.** ui-spec.md's reader discipline says derived state "is
  reconstructed from the log alone" — for a run's own directory, which
  the frozen physical layout (§1.1, "one directory per run") already
  implies means *that run's own files*, not a chain across directories.
  **Ruling: copy-forward, not cross-run reference.** A fork creates a
  brand-new run directory (`runs/<new_run_id>/`) whose `events.jsonl`/
  `trace.jsonl` open with a **verbatim copy** of the parent's records up
  to the fork tick, then continue with fresh generation-stamped records
  from there. This is the smaller, ui-spec-compliant option: the new
  run is fully self-contained and readable "from the log alone" with
  zero reader changes, matches how `EventLog.fork()`'s lineage already
  behaves logically (the child's own view of history includes the
  inherited prefix), and needs no change to the frozen runs registry
  (§1.2) beyond a normal new entry — a cross-run-reference scheme would
  need the registry and every reader to learn about ancestry chains,
  which nothing in ui-spec.md anticipates and which is real, unscoped,
  additional risk to a frozen contract this lane must not touch.
  **This ruling only needs owner sign-off if a future reviewer disagrees
  with "reconstructed from the log alone" reading it this way — flagging
  it here rather than silently deciding is the point of this doc.**
- **A CLI entry point.** `chronicle sync-check` (landed) computes
  FORK/ADOPT correctly but reports them as unsupported. Once fork exists,
  `sync-check`'s FORK/ADOPT branch (`chronicle/cli.py`,
  `sync_check_command`) should be revisited to actually invoke it instead
  of exiting 3 — noted here, not this lane's job to wire (keep the two
  lanes separable; landing fork-on-disk alone is valuable and testable
  without touching `sync-check` at all).

## 2. Scope for the first lane

`chronicle fork <run_id> --at-tick T [--new-run-id ID]`:

1. Read the parent run's state at tick T via `state_at()` (extended per
   §1 to also carry replayed canonical events).
2. Create a new run directory (`--new-run-id`, or an auto-generated id
   if omitted — check `chronicle`'s existing run-id generation
   convention, likely already used somewhere for scenario/demo runs).
3. Copy `events.jsonl`/`trace.jsonl` records up to and including tick T
   from the parent into the new run's files verbatim (same records,
   same `save_uuid`, same `generation` — they really did happen, in both
   branches, up to the fork point).
4. Register the new run in `runs/index.json` (the existing registry
   write path — reuse whatever `Driver`/writer already does on run
   creation, don't hand-roll a second registry writer).
5. Construct a `Driver` for the new run: `generation = parent_generation
   + 1`, stores pre-populated from step 1's extended `ReconstructedState`,
   `event_log` likewise pre-populated. The new `Driver` is ready for the
   caller (a scenario, or eventually the dashboard's injection console
   per ui-spec §3.1) to inject the diverging event and continue.
6. Tests: fork a small fixture run at a mid-log tick, assert the new
   run's copied prefix matches the parent's records exactly up to T,
   assert the new run's `generation` is `parent + 1`, assert injecting a
   new event into the forked `Driver` and running further ticks produces
   a real divergent continuation (the parent's own post-T history is
   untouched — forking must never mutate the parent run's files).

## 3. Non-goals for this lane

- Wiring `chronicle sync-check`'s FORK/ADOPT paths to call this (§1,
  noted as a follow-up, separable).
- Dashboard UI for triggering a fork (ui-spec §3.1's injection-console
  UX — "a 'forking from tick T' confirmation naming the new generation"
  — is a dashboard-side lane, not this one).
- Any change to `docs/ui-spec.md` itself — this lane implements what it
  already specifies.
