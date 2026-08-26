# Design prep — wiring `chronicle.sync.resolve()` into a real CLI path

**Status:** design proposal, informing a scoped-down implementation lane.
Not an ADR amendment. Written the same way the two ChronicleBridge
design docs were: name the dependency this doesn't build, then build
the smallest real thing.

Sources: `chronicle/sync.py` (the pure RESOLVE logic, built and tested
this session, never yet fed a real run's state); `docs/decisions/
0005-sync-handshake.md` (the full handshake this is one piece of);
`chronicle/cli.py`'s `_inject_write`/`_max_tick` (the closest existing
precedent — and the discovery that motivated this doc, below);
`chronicle/framelog.py` (the on-disk run format).

## 0. What this finds, before proposing anything

`chronicle/sync.py`'s `resolve()` is a pure function — correct, tested,
and currently unreachable from any real run. Wiring it in looked like a
small task ("read a run's state, build a `BranchState`, call `resolve()`,
return JSON") until checking what a "run" actually is on disk.

**It isn't there.** `chronicle/cli.py`'s `_inject_write` already refuses
injection at a tick behind the run's current max tick, with the comment
"that is fork territory, a deliberately deferred milestone
(docs/dashboard-build-plan.md §3)". `chronicle/framelog.py`'s on-disk
format bakes exactly one `(save_uuid, generation)` pair into a run's
records (`"branches": [{"save_uuid": ..., "generation": ...}]`, singular)
— there is no mechanism today to store a second generation inside one
run directory, or to open a new run directory as a fork of an existing
one. The in-memory `EventLog.fork()` (`chronicle/events.py`) that
`Driver` uses internally has no on-disk counterpart at all.

**This means:** `resolve()` can correctly *decide* FORK or ADOPT for a
real run, but nothing in this repo can *act* on that decision yet — the
same "named, not solved" discipline as the death-extraction slice's
ADR-0005 dependency (`docs/design/chronicle-bridge-death-extraction.md`
§1), just one layer further in. Building real fork-on-disk support is
its own future milestone (a `docs/dashboard-build-plan.md` §3 item
already, by name) — not something to fake or shortcut here.

## 1. What's honestly buildable today

A `chronicle sync-check <run_id> --manifest '<json>'` CLI subcommand
(mirroring `inject`'s shape: positional run_id, a JSON blob, printed
result) that:

- Reads the run's current state via `FrameLogReader`/`_max_tick` (the
  same read path `_inject_write` already uses) and assembles a
  `chronicle.sync.BranchState` from it — `known=True` (the run exists on
  disk by definition once you can point at its `run_id`), single
  `known_generations={the run's baked-in generation}`, `head_seq`/
  `head_gamets` read off the run's actual records.
- Calls `chronicle.sync.resolve(manifest, branch_state)` and prints the
  `Resolution` as JSON.
- **For `CONTINUE`:** this is real and complete — the manifest matches
  the run, nothing to build beyond reporting `replay_from_seq` if any.
- **For `FORK`/`ADOPT`:** report the decision honestly, but the command
  must say plainly (exit code + stderr message, same idiom as
  `_inject_write`'s refusal) that no fork-on-disk mechanism exists to act
  on it yet — this is surfacing the real limitation at the CLI boundary,
  not silently no-op'ing.
- **For `NEW_TIMELINE`/`LEGACY_IMPORT`:** these mean "no existing run
  matches" — arguably this is where a NEW run directory gets created,
  which the CLI already knows how to do (`chronicle`'s existing run-init
  path, whatever creates a run). Check whether wiring this through
  `sync-check` to actually call that path is a small, honest addition or
  its own scope creep; lean toward "report only" for this first lane
  unless it's genuinely trivial once you're in the code.
- **For `DEGRADED`:** doesn't apply to a CLI call at all (it's about the
  *caller* being unable to reach the service) — the CLI subcommand
  itself is proof the service is reachable, so this decision never
  applies here; don't build anything for it.

## 2. Non-goals for this lane

- Fork-on-disk support itself (the real dependency, named above — its
  own future milestone, needs a design decision on how a forked branch's
  directory/records/index actually look, which nobody has specified yet
  even in ADR-0004/0005).
- Wiring this into `adapters/skyrim/listener/` — that's a further
  integration decision (does the manifest arrive over HTTP from the
  shim? via a new endpoint mirroring `/whiterun/events`'s shape?) that
  should wait until there's a real fork-on-disk target to wire *to*.
  Shipping listener wiring for CONTINUE-only, with FORK/ADOPT reported
  as CLI-side errors, would be premature — the shim doesn't exist to
  call it yet either (C++ side, needs the Windows machine).
- Epoch fencing enforcement in the CLI (that's a live-session concept —
  "current epoch for this session" — that doesn't map onto a one-shot
  CLI invocation cleanly; `mutation_admissible()` stays a library
  function other callers use, not something `sync-check` itself needs).
