---
date: 2026-08-20
sources:
  - "research/External World-State Sync for Skyrim - Research Report.md"
topic: "Save/reload timeline consistency — fourth independent pass, primary-sourced"
status: filed
---

# External world-state sync — fourth independent pass

A fourth, independently-arrived report on the same save/reload question as
reports 05/06/07. Distinguishes itself by primary-sourcing almost every
claim to a specific GitHub issue, PR, or discussion thread rather than
project docs/FAQs — this makes it the strongest evidentiary basis of the
four for anything it disagrees with the others on.

## Findings

- **[RESOLVES a tracked disagreement] SkyrimNet's reload behavior is "ask," confirmed via primary source.** Reports 05 and 06 disagreed on this (05: "effectively ignore, no cross-process fork"; 06: "explicit but weakly-sourced cleanup protocol"). This report cites SkyrimNet-GamePlugin issue #251 directly: on loading an older save, the DLL calls `ClearTimelineMessage()` to ask the player whether to discard future events (`msgClearHistory`), and the same issue requests a public "erase and forget from time X forward" API. This is a primary-sourced, specific behavior — stronger evidence than either prior characterization. **Closes the sub-disagreement** left open in `open-questions.md`.
- **[RISK, concrete cautionary tale] SkyrimNet issue #487: "Created memories get erased."** A 100%-reproducible bug where memories created via the dashboard/MCP API were silently hard-deleted within 1-2 days, while auto-generated memories survived. Root cause, confirmed by the maintainer: a background cleanup routine's liveness criterion was an **internal, non-inspectable timestamp**, and externally-created rows were stamped differently by a second write path, so the cleanup treated them as orphans and deleted 237 rows with no recovery path. This is exactly the failure ADR-0004's tombstone-then-reap design is meant to prevent — now with a concrete precedent, not just a hypothetical.
- **[BUILD-ON] Reachability-based liveness, not timestamp-based, is the correct GC rule — reinforced by git's actual model.** Git's objects are collectable only when unreachable from any ref; the reflog keeps abandoned branch tips reachable for a grace period (90 days for reachable entries, 30 for unreachable), and `git gc` prunes loose objects only past a further two-week window by default. Applied to Chronicle: a branch is live if any surviving save/co-save references it — never a bare timestamp comparison, which is precisely what broke in SkyrimNet #487 and in CHIM's own PR #572 (NULL-timestamped manual edits treated as "never anchored" and wiped on reconnect).
- **[DESIGN-INPUT] Bitemporal framing sharpens the existing (gamets, wall_ts) fields already implicit in reports 05-07**: `gamets` (in-game clock) is **valid time** — when the fact is true in the modeled reality; server wall-clock is **transaction time** — when it was stored. Every query needs both coordinates ("Lydia's beliefs as of branch B, game-time T" vs. "what did the service know when the player saved S17"). HerikaServer's schema is cited as an accidental, incomplete version of this (has both columns, but validity is a bare nullable field rather than a first-class interval) — which is diagnosed as the direct cause of its NULL-timestamp bugs (PR #572).
- **[BUILD-ON] A concrete six-pattern race-condition catalog**, more specific than reports 05-07's race discussion: (1) co-save-read vs. service-notification ordering; (2) save-during-in-flight-mutation (manifest's head-sequence should be "last ACKed," not "last attempted," with gaps repaired by replay); (3) file-based IPC vs. mod-manager virtual filesystem hiding files (MO2 can virtualize IPC files into `overwrite/root` so an external process never sees them — an argument for loopback HTTP/named pipes over file polling); (4) editor-vs-game lost updates (CHIM PR #560: concurrent writers clobbering a relationship blob — fix is per-key CAS or a single serialized writer, never whole-blob overwrites); (5) unanchored rows meeting a rollback sweep (the #572/#487 bug class); (6) load-time load spike (SkyrimNet's own documented "cannot keep up with game load," issue #172). General mitigation shape: **the game side is optimistic and never blocks; the service side is pessimistic and validates every event against the currently-acknowledged branch head.**
- **[DESIGN-INPUT, new] A "DEGRADED" mode for service-unreachable-at-load**, absent from reports 05-07's protocols: if the service can't be reached at load time, the game buffers events locally in a bounded queue (spilling to disk if needed) and reconciles on reconnect — the loading screen must never stall waiting for the service.
- **[BUILD-ON] Concrete manifest schema**, structurally identical to ADR-0004/0005's design but with two additions worth adopting: `parent_branch_id` (explicit fork ancestry, not just implied by the fork table) and `char_name_hash` (explicitly labeled display/debug-only, never a key — with a citation showing *why*: Mantella's community resources page maintains a manual list of vanilla NPCs who change name/refID mid-game, which is what happens when name-keyed identity is trusted).
- **[DESIGN-INPUT] Death-reload must resolve automatically, not via a prompt.** SkyrimNet's `msgClearHistory` prompt is reserved for large divergences; the report's explicit recommendation is that dying and retrying from a save seconds-to-minutes old on the same branch should be a **silent continue or small fork** — a confirmation prompt on every death "is the fast path to users disabling the system."
- **[BUILD-ON] Fowler's "Retroactive Event... Updating External Systems" pattern reframes which side reconciles.** Chronicle's Python service is the "external system" relative to Skyrim's save file (the authoritative log) — this argues against trying to hand-write compensating actions per subsystem when a branch is abandoned (the approach whose brittleness CHIM's PR history documents) and for the branch-switching model where "correction" is just "serve a different branch."
- **[RISK] Same-process reloads are a distinct, under-addressed hazard.** The engine doesn't cleanly tear down script activity on an in-session reload (community-documented: "the engine does not close/end scripts properly... you end up stacking scripts"), which is why process-restarting loaders exist. Design consequence: no cached "current timeline" state may survive at the process level, only per-load; idempotent re-registration must be safe to run N times per process; a first-load-in-new-process must be indistinguishable from a tenth-load-in-same-process, which the UUID handshake provides for free but which is worth stating as an explicit requirement.

## Comparison table (as given in the source report)

| Dimension | Mantella | CHIM/HerikaServer | SkyrimNet |
|---|---|---|---|
| Reload strategy | **Ignore** — memory drift | **Roll back** ("Dragon Break" — delete future events, archive to Playthrough Manager) | **Ask** — prompt via `ClearTimelineMessage`/`msgClearHistory` |
| Characteristic failure | Temporal incoherence | Data loss for anything not perfectly time-anchored (NULL-stamped rows wiped, PR #572) | Prompt fatigue; GC still broke on internal timestamps (#487) |

The report's framing: the ecosystem has explored three corners of the
design space (ignore/rollback/ask) and each has a characteristic failure
mode; the fourth corner — **fork**, keep both timelines, let the save
decide which is live — is what none of them ship, and is what
ADR-0004 already adopts.

## Flagged uncertainties

- This report's own protocol section proposes concrete numbers (a ≥7-day
  GC grace period, "hundred bytes" manifest budget) as recommendations
  informed by git's precedent, not as verified Skyrim-specific constants
  — same caveat as reports 05-07's equivalent figures.
- SkyrimNet issue/PR numbers (#251, #487, #119, #391, #465, #172) are
  cited directly and should be treated as accurate as of this survey, but
  issue trackers can be closed/renumbered/reorganized — worth a spot
  check before quoting a specific issue number in user-facing documentation.
