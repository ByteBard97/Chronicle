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
- **Every event carries both time coordinates — bitemporal, mandatory,
  never `NULL`**: `gamets` (Skyrim's in-game clock at the moment of the
  event — **valid time**, when the fact is true in the modeled reality)
  and `wall_ts` (real-world time the event was durably stored — **transaction
  time**). Queries need both: "Lydia's beliefs as of branch B, game-time T"
  is a valid-time query; "what did the service know when the player saved
  S17" is a transaction-time query. This is not optional metadata —
  CHIM's HerikaServer had both columns and still broke (PR #572,
  `docs/research/09-save-sync-forensics.md`) because validity was a bare
  nullable field rather than a mandatory, always-populated one: manually-
  edited rows left `gamets` unstamped were indistinguishable from "never
  anchored" and got wiped by the next rollback sweep. **Every write path —
  including future admin/dashboard/debug tools — must stamp both fields or
  be rejected**, not silently defaulted.

  **Footnote (2026-09-01):** `Dwemer-Dynamics/HerikaServer` PR/issue #572
  (and #560, cited elsewhere in report 09 for the concurrent-writer race)
  both 404 today, per a live GitHub check during the sync-handshake spec's
  review (`docs/design/chronicle-bridge-sync-handshake-review-kimi-2026-09-01.md`).
  Report 09 flagged generally that issue numbers "can be
  closed/renumbered/reorganized," but this specific pair is now
  unverifiable rather than merely unspotchecked. The underlying design
  rule (mandatory, non-nullable bitemporal fields; reachability-based GC)
  doesn't depend on this one citation — SkyrimNet's #487 and the general
  git-reflog precedent independently support it — but this citation itself
  should be treated as anecdotal, not primary-sourced, until re-verified.
- **Garbage collection is reachability-based, never timestamp-based, with
  a grace period and soft-delete first.** A branch is live if and only if
  some surviving `.ess`/co-save on disk references its
  `(save_uuid, generation)` — mirroring both the "orphaned co-save" test
  community tools (SSE Engine Fixes) already use, and git's own model
  (objects collectable only when unreachable from any ref; the reflog
  keeps abandoned tips reachable for a grace period before `git gc` prunes
  them). Abandoned branches are **tombstoned** (`abandoned_at`) first, kept
  through a retention window so an accidental reload stays recoverable,
  and only hard-purged after that window, never inline at reload time.
  **This rule exists because of a documented failure, not by analogy**:
  SkyrimNet issue #487 (`docs/research/09-...`) is a 100%-reproducible bug
  where a GC routine hard-deleted 237 externally-created memories — no
  recovery path — because its liveness criterion was an internal,
  non-inspectable timestamp that a second write path (the dashboard/MCP
  API) stamped differently. Reachability-from-a-live-reference cannot fail
  this way; a timestamp comparison can and did.
- **User-curated content is a protected stream class, exempt by
  construction, not by heuristic.** Hand-authored bios, pinned rumors, or
  any record a person (not the simulation) created directly must live in
  a stream class the fork/rollback/GC machinery never touches — mirroring
  SkyrimNet's own Beta20 fix ("user-curated world knowledge entries are no
  longer deleted when loading older saves") and CHIM's Playthrough Manager
  archive, both retrofits of a rule Chronicle should have from the start.
  "Exempt by class" means the exemption is a property of *which stream the
  record lives in*, not a special-cased conditional buried in the GC pass
  — the retrofit history in report 09 is evidence that heuristic exemptions
  get missed.

## Rationale

- Four independent research reports converged on this design without
  prompting each other (`docs/research/05-...`, `06-...`,
  `07-skyrimnet-substrate.md`, the last of which re-derived the same DAG
  model — down to a concrete `ChronicleSync::OnGameSave`/`OnGameLoad` C++
  sketch — while researching an unrelated question, SkyrimNet's platform
  risk; and `09-save-sync-forensics.md`, which grounds the same model in
  actual repository history — CHIM/SkyrimNet PRs and issues — rather than
  architecture alone). This is the same model the broader event-sourcing
  community uses for branching (commit≈event, branch≈stream, reload≈
  checkout-then-new-commits — see report 05 §3), and report 09 adds git's
  own reachability/reflog/grace-period GC model as a second, independent
  precedent for the same discipline.
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
`.skse`/`.ess` pairing is atomic by convention only. Report 09's specific
GC grace-period recommendation (≥7 days, informed by git's 2-week/30-day/
90-day precedents) is a reasonable starting default, not a verified
Skyrim-specific constant — same caveat as every other numeric threshold
in this ADR's source reports.
