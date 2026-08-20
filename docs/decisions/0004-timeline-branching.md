---
status: accepted
date: 2026-08-20
---

# 0004: Timeline branching for save/reload consistency

## Context

Skyrim players save, die, reload, and roll back constantly. Chronicle's
event-sourced log (`0002-event-sourcing.md`) is append-only, but a naive
single linear log breaks the moment a player reloads a save from before
some event was recorded: the log would contain events (an assassination,
its succession contest, every derived rumor) that never happened in the
timeline the player is now actually in.

Research (`docs/research/05-save-reload-sync-protocol.md`,
`docs/research/06-save-reload-timeline-sync.md`) surveyed how Mantella,
CHIM/HerikaServer, and SkyrimNet handle this today and found none of them
solve it cleanly: Mantella ignores it (memory drift across reloads and
same-named characters), CHIM prunes globally by comparing Skyrim's internal
clock (`gamets`) — which is reseeded identically on every new save and
can't disambiguate two forks sharing a clock value — and SkyrimNet's
in-process design has no cross-process fork mechanism at all (or, per a
less-confirmed source, an unpublished internal cleanup protocol; see
`open-questions.md`).

## Decision

Skyrim's save topology is a **directed acyclic graph**, not a line. Model
it as one:

- Every event carries a **branch key**: `(save_uuid, generation)`.
- `save_uuid` is generated once per playthrough (new game) and persists
  across saves within that character's timeline; `generation` increments
  each time the player reloads a save that is behind the branch's current
  head — i.e., each fork.
- **Never roll back.** Loading an earlier save never deletes or rewrites
  events. It forks: a new `generation` is opened with the loaded save's
  state as its starting point, and the old suffix becomes an abandoned
  branch rather than being erased.
- **State derivation is a path traversal**: to compute current world state,
  fold over events from the root along the lineage to the active
  `(save_uuid, generation)` head — not "all events ever recorded."
- **Garbage collection**: abandoned branches are tombstoned
  (`abandoned_at`), never hard-deleted inline. A branch is only reaped once
  no live `.ess`/co-save on disk references its `(save_uuid, generation)`
  — mirroring the "orphaned co-save" test community tools (SSE Engine
  Fixes) already use — and only after a retention window, so an accidental
  reload stays recoverable.

## Rationale

- Both independent research reports converged on this design without
  prompting each other, and it's the same model the broader event-sourcing
  community uses for branching (commit≈event, branch≈stream, reload≈
  checkout-then-new-commits — see report 05 §3).
- It's strictly more capable than every existing mod's approach: it
  disambiguates multiple characters/save slots (unlike Mantella's
  name-keyed files), doesn't require a global clock comparison that can
  collide (unlike CHIM's `gamets`-only reconciliation), and doesn't require
  staying in-process to work (unlike SkyrimNet's architecture).
- Fork-don't-rollback preserves data: nothing about a player's play session
  is destroyed by a reload, which matters both for debuggability (the
  dashboard's causality timeline, `docs/architecture.md`) and for
  eventual features like "what would have happened" comparisons across
  branches.

## Consequences

- `chronicle/events.py`'s `Event` base type now carries `save_uuid: str`
  and `generation: int` fields; `EventLog` (or its successor) must support
  querying/folding along a specific branch's lineage, not just "all
  events." See the accompanying code change and
  `chronicle/tests/test_events.py::test_forking_a_branch_excludes_the_abandoned_suffix`.
- Snapshotting per branch at each save becomes necessary once logs get
  long enough that replaying from the root is expensive — out of scope for
  the current skeleton, but the branch key is designed to make that
  addition non-breaking later.
- The SKSE-side half of this (generating `save_uuid`, writing the co-save
  record, detecting forks at load time, notifying the service) is
  specified in `0005-sync-handshake.md` and lives entirely in
  `adapters/skyrim/` — `chronicle/` only needs to know branch keys exist,
  never how they're produced.
- FormIDs must never be persisted raw inside event payloads (see
  `docs/architecture.md`'s FormID rule) — a load-order change would
  silently corrupt every event referencing an actor/item by raw FormID,
  which would be indistinguishable from a genuine timeline fork bug.

## Implementation-risk notes

See `docs/decisions/open-questions.md` — CHIM's fork-trigger threshold is
reconstructed, not confirmed; the save-embedded-UUID pattern has no
confirmed Skyrim precedent (nearest prior art is a different engine); the
`.skse`/`.ess` pairing is atomic by convention only.
