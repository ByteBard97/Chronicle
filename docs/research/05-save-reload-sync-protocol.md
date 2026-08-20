---
date: 2026-08-20
sources:
  - "research/save-reload-compass.md (originally: External-State Sync for Skyrim SE/AE...)"
topic: "Save/reload timeline consistency — protocol design"
status: filed
---

# Save/reload timeline consistency — protocol design (compass report)

Answers the `open-questions.md` prompt on how existing external-state mods
handle save/load/reload consistency, and proposes a sync protocol.

## Findings

- **[RISK] None of the three existing AI-NPC mods solve reload consistency cleanly.** Mantella ignores it entirely (per-NPC summary files keyed by player name, no reload hook — "timeline bleeding" across reloads and same-named characters). CHIM/HerikaServer is the only one with an explicit story: it detects backward jumps in Skyrim's internal clock (`gamets`) and prunes "future" events into a "Playthrough Manager" backup — global, not per-save-slot. SkyrimNet is in-process and has no cross-process fork mechanism at all.
- **[BUILD-ON] SKSE's `SerializationInterface` co-save is the right atomic anchor.** The `.skse` co-save is written/deleted/renamed in lockstep with the `.ess` (`kMessage_DeleteGame` fires right before both are deleted). Callback order on load: `kPreLoadGame` → **Revert** (wipes stale in-memory state) → **Load** (repopulates from new co-save) → `kPostLoadGame`. This is the standard place to embed a per-save timeline identity.
- **[DESIGN-INPUT] A save-embedded UUID + monotonic generation counter is strictly stronger than CHIM's clock-only (`gamets`) approach**, since `gamets` is reseeded identically (10,000,000) on every new save and cannot disambiguate two forks sharing a clock value. This pattern (GUID-on-start + heartbeat, reload detected by comparing stored timestamps against the save's clock) has precedent in other engines — the clearest documented example is the "realms" Neverwinter Nights module — but is under-documented specifically for Skyrim; expect to implement and test the co-save read path from scratch rather than reuse an existing library.
- **[RISK] `kPostLoadGame` and Papyrus's `OnPlayerLoadGame` are two non-synchronized "load done" signals.** `kPostLoadGame` (native, earlier) can fire before Papyrus forms are resolved; `OnPlayerLoadGame` (Papyrus, later) never fires on a brand-new game at all — the standard idiom is to run the same init routine from both `OnInit()` and `OnPlayerLoadGame()`. A service must not treat either signal alone as "game ready."
- **[BUILD-ON] Event-sourcing's branching model maps directly onto save reloads.** The Git analogy is exact: commit≈event, branch≈stream, reload≈checkout-then-new-commits≈fork. The community consensus (per EventStore/KurrentDB discussions) on branch identity is either a new stream per branch or branch identity carried inside events — this project should carry `(save_uuid, generation)` inside events (see the events.py change, item 5 of this batch).
- **[DESIGN-INPUT] Branch garbage collection should never hard-delete inline.** Tombstone abandoned branches (`abandoned_at`), keep them for a retention window so an accidental reload is recoverable, reap out-of-band once no live `.ess`/co-save references them — mirrors both the Atuin (shell-history sync) project's sync-deletion lesson and SSE Engine Fixes' existing practice of deleting orphaned `.skse` files with no matching `.ess`.
- **[RISK] Throughput and back-pressure**: SkyrimNet's own bug tracker documents it "cannot keep up with game load" during bursts — the service must be idempotent (dedupe on `(save_uuid, generation, event_seq)`) and back-pressure-tolerant, not just correctness-tolerant.
- **[DEFER] Only fork above a configured backward-jump threshold** (echoing CHIM's "DragonBreak" trigger for old saves) so trivial same-point quicksave/quickload doesn't spawn a new branch every time.

## Recommended protocol (as proposed by the report)

1. **Establish timeline identity.** Ship a thin SKSE/Papyrus shim. On new game (`OnInit()`, since `OnPlayerLoadGame` won't fire), generate `save_uuid = UUIDv4`, `generation = 0`. On every save, also write a monotonic `event_seq` and current `gamets` into the co-save — this triple is the **watermark**. Mirror it to a sidecar file as an out-of-process fallback.
2. **Service is an append-only event store**, keyed by `(save_uuid, generation)` = a branch. Never UPDATE/DELETE; snapshot per branch at each save.
3. **Reconcile on load, fork don't roll back.** Shim pushes the loaded watermark to the service *before* any new event may commit (closes the `kPostLoadGame`/Papyrus race). Compare to branch head: equal → continue; in the past → fork (increment `generation`, copy the snapshot forward, tombstone the abandoned suffix); unknown `save_uuid` → switch/create that character's branch set (fixes Mantella's same-name collision).
4. **Branch GC**: retention window, then reap when no `.ess`/co-save references the `(save_uuid, generation)` — same test SSE Engine Fixes uses for orphaned co-saves.
5. **Hardening**: treat load as "ready" only after an explicit `game_ready` ping (not just `kPostLoadGame`); idempotent + back-pressure-tolerant service; version co-save records so schema upgrades don't corrupt old branches.

**Scaling notes from the report**: single-character/never-reload play can skip forking entirely (linear log). Moving in-process (a DLL, SkyrimNet-style) lets you read the watermark from memory and drop the sidecar file. Low write volume (a few events/min) needs nothing heavier than SQLite per branch; only reach for a dedicated event store/vector DB above roughly tens of events/second.

## Flagged uncertainties (carried into open-questions.md)

- CHIM's exact fork/prune trigger (the specific numeric threshold, in in-game days) is reconstructed from its FAQ/changelog/HerikaServer field names, not confirmed in any primary Dwemer Dynamics source.
- Mantella's and SkyrimNet's "ignore" behavior is inferred from their documented architecture and the absence of reload-reconciliation features, not from an explicit "we do nothing" statement from either project.
- The save-embedded-UUID pattern has no confirmed Skyrim precedent; the strongest published prior art is from a different engine (NWN "realms").
- SKSE `.skse`/`.ess` pairing is atomic **by convention**, not a transactional guarantee — the SKSE headers never use the word "atomic," and `kPostLoadGame`'s success bool exists precisely because a load can fail after `kPreLoadGame`.
