"""On-disk fork support (docs/design/fork-on-disk-support.md).

``ui-spec.md`` §3.1 already specifies fork semantics: "Appending at any
historical tick T (< end of log) creates a fork -- (save_uuid,
generation+1), re-simulated from T." This module is the implementation --
nothing here amends that spec.

Copy-forward, not cross-run reference (the design doc's §1 ruling): a fork
creates a brand-new run directory (``runs/<new_run_id>/``) whose
``events.jsonl``/``trace.jsonl`` open with a **verbatim copy** of the
parent's records up to the fork tick, then continue with fresh
generation-stamped records from there. The new run is fully self-contained
and readable "from the log alone" (ui-spec's reader discipline), with zero
reader changes needed.

A fork's new ``Driver`` is not a new kind of object (design doc §0) -- it's
an ordinary ``Driver`` constructed with ``generation = parent_generation +
1`` and its stores (``claims``/``social``/``roles``/``event_log``) seeded
from the parent's state at the fork tick, exactly the "start-from-keyframe
shaping" shape ``Driver.__init__`` already documents.
"""

from __future__ import annotations

from pathlib import Path

from chronicle.driver import Driver
from chronicle.framelog import (
    EVENTS_STREAM,
    TRACE_STREAM,
    FrameLogReader,
    default_runs_dir,
)


def fork_run(
    parent_run_id: str,
    *,
    at_tick: int,
    new_run_id: str,
    runs_dir: Path | None = None,
) -> Driver:
    """Fork ``parent_run_id`` at ``at_tick`` into a new run ``new_run_id``; returns a ready-to-use ``Driver``.

    Steps (docs/design/fork-on-disk-support.md §2):

      1. Resolve the parent run's directory and read its state at
         ``at_tick`` (``FrameLogReader.state_at()``, extended to also carry
         replayed canonical events, ``framelog.ReconstructedState.event_log``).
      2. Register the branch link in that reconstructed, in-memory
         ``EventLog`` via ``EventLog.fork()`` -- the same lineage logic the
         in-memory precedent already implements, so the new ``Driver``'s
         ``event_log.lineage(save_uuid, new_generation)`` call sees the
         inherited prefix (deaths, schedule overlays, ...) without
         re-deriving it a second way.
      3. Construct a ``Driver`` for the new run: ``generation =
         parent_generation + 1``, ``save_uuid`` unchanged, stores
         pre-populated from step 1. Constructing the ``Driver`` is what
         creates the new run's directory, opens its stream files, writes
         the initial sidecar index, and registers it in ``runs/index.json``
         (``FrameLogWriter.__init__`` -- reused verbatim, not reinvented).
      4. Copy the parent's ``events.jsonl``/``trace.jsonl`` records up to
         and including ``at_tick`` into the new run's (still-empty) stream
         files, through the new ``Driver``'s own writer
         (``write_event``/``write_trace``/``write_keyframe`` -- the writer's
         own append machinery, not hand-rolled JSONL), temporarily stamped
         at the *parent's* generation (they really happened under that
         branch), then flip the writer back to the new generation for
         everything from here on.
      5. Flush -- ``FrameLogWriter.flush()`` rewrites the sidecar index from
         its own accumulated offset/keyframe bookkeeping, so the copied
         prefix is indexed correctly with no separate rebuild step needed.

    The returned ``Driver`` is NOT closed here -- it is ready for the caller
    (a scenario, the fork CLI command, or eventually the dashboard's
    injection console per ui-spec §3.1) to inject the diverging event and
    continue. A caller with nothing further to do should call
    ``driver.close()`` itself (matching the normal run lifecycle: a run's
    registry entry is marked complete on close).

    Raises ``FileNotFoundError`` if the parent run doesn't exist,
    ``ValueError`` if ``at_tick`` is negative, beyond the parent's recorded
    max tick, or the parent has no records at all, and ``FileExistsError``
    if ``new_run_id`` already exists on disk (surfaced early here with a
    clear message, though ``FrameLogWriter``'s own create-only guard would
    catch it too).
    """
    base = runs_dir if runs_dir is not None else default_runs_dir()
    parent_dir = base / parent_run_id
    if not parent_dir.exists():
        raise FileNotFoundError(f"no such run {parent_run_id!r} under {base} (looked for {parent_dir})")
    new_dir = base / new_run_id
    if new_dir.exists():
        raise FileExistsError(f"run directory {new_dir} already exists -- pick a different --new-run-id")

    parent_reader = FrameLogReader(parent_dir)
    index = parent_reader.read_index()
    ticks = [int(t) for stream in index["streams"].values() for t in stream["tick_offsets"]]
    max_tick = max(ticks) if ticks else None
    if max_tick is None:
        raise ValueError(f"run {parent_run_id!r} has no records yet -- nothing to fork from")
    if at_tick < 0:
        raise ValueError(f"--at-tick {at_tick} must be >= 0")
    if at_tick > max_tick:
        raise ValueError(f"--at-tick {at_tick} is beyond run {parent_run_id!r}'s max tick ({max_tick})")

    # The parent's baked-in (seed_id, save_uuid, generation) -- any record's
    # envelope carries it (the on-disk format bakes in exactly one such
    # triple per run, cli.py's _branch_identity's same assumption).
    first = next(parent_reader.records(EVENTS_STREAM), None) or next(parent_reader.records(TRACE_STREAM), None)
    if first is None:
        raise ValueError(f"run {parent_run_id!r} has no records to fork from")
    seed_id = first["seed_id"]
    save_uuid = first["save_uuid"]
    parent_generation = first["generation"]

    state = parent_reader.state_at(at_tick)

    # The in-memory EventLog.fork() precedent, applied to the replayed
    # event_log: at_event_count is the full inherited prefix (everything
    # replayed up to at_tick), so lineage(save_uuid, new_generation) below
    # returns exactly that prefix.
    inherited_count = len(state.event_log.lineage(save_uuid, parent_generation))
    new_generation = state.event_log.fork(save_uuid, parent_generation, inherited_count)

    driver = Driver(
        run_id=new_run_id,
        seed_id=seed_id,
        save_uuid=save_uuid,
        generation=new_generation,
        schedule=state.schedule,
        runs_dir=base,
        event_log=state.event_log,
        claims=state.claims,
        social=state.social,
        roles=state.roles,
    )

    # Copy-forward the parent's own records, verbatim, stamped at the
    # PARENT's generation while copying (they really happened under that
    # branch) -- then flip the writer to the new generation for everything
    # written from here on. Driver's own construction above is the only
    # thing that has touched the new run's stream files so far (they were
    # just opened, empty), so this copy starts at offset 0 in each.
    driver.writer.generation = parent_generation
    try:
        for record in parent_reader.records(EVENTS_STREAM, upto_tick=at_tick):
            payload = record["payload"]
            if payload.get("record_type") == "keyframe":
                driver.writer.write_keyframe(tick=record["tick"], state=payload["state"])
            else:
                driver.writer.write_event(tick=record["tick"], seq=record["seq"], payload=payload)
        for record in parent_reader.records(TRACE_STREAM, upto_tick=at_tick):
            driver.writer.write_trace(tick=record["tick"], payload=record["payload"])
    finally:
        driver.writer.generation = new_generation
    driver.writer.flush()

    return driver
