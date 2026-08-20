---
date: 2026-08-20
sources:
  - "research/save-reload-architecture.md (originally: Architecture of External State Persistence and Timeline Synchronization in Skyrim SE/AE Plugins)"
topic: "Save/reload timeline consistency — DAG model and wire protocol"
status: filed
---

# Save/reload timeline consistency — DAG model and wire protocol (architecture report)

Independent answer to the same `open-questions.md` prompt as report 05.
Converges on the same core recommendation (event-sourced, fork-on-reload,
co-save-embedded UUID) but contributes a concrete DAG formalization, a
FormID-stability warning neither the compass report nor any prior filed
report raised, and a fully specified wire protocol.

## Findings

- **[DESIGN-INPUT] Skyrim's save topology is fundamentally a DAG, not a line.** Because a player can load any historical save at any time, state should be modeled as save-nodes (identified by save-embedded `SaveUUID`) connected by edges representing the events that transitioned parent → child state. Deriving "current world state" is a path-traversal query from the root node along the active branch's lineage to the head — this is a direct, more formal restatement of report 05's "event-sourcing branching" finding, useful because it gives Chronicle's engine a concrete traversal algorithm rather than just a metaphor.
- **[RISK] FormID instability is a persistence hazard this report is the only one to flag.** A FormID's upper 8 (or 12, for `.esl` light plugins) bits encode the mod's position in the active load order. Adding/removing/reordering mods invalidates any raw FormID stored externally. **Chronicle must store composite keys (plugin name + local FormID offset), never raw 32-bit FormIDs** — SKSE's `ResolveFormId` exists specifically to re-resolve these against the current load order via the save header's embedded plugin list.
- **[BUILD-ON] A concrete binary co-save record layout is proposed**: a `TMNL` (Timeline) record with `SaveUUID` (16 bytes), `ParentSaveUUID` (16 bytes), `SaveSequence` (uint64), `EngineGameTime`/`gamets` (double), `RealTimestamp` (uint64 ms). This is a directly implementable schema for the co-save shim, one level more concrete than report 05's prose description of the same watermark concept.
- **[BUILD-ON] A 4-message WebSocket protocol is proposed**: `CLIENT_INIT` (handshake, plugin/load-order versions) → `SYNC_TIMELINE` (shim → service, sent from `kPostLoadGame` once the `TMNL` co-save chunk is parsed, carrying `save_uuid`/`parent_save_uuid`/`save_sequence`/`gamets`) → `TIMELINE_READY` (service → shim, returns an **epoch fencing token**) → `MUTATION_EVENT` (shim → service, must carry the active `epoch_id`).
- **[DESIGN-INPUT] Epoch fencing solves the stale-async-write race concretely.** If the player triggers a long-running LLM call and then quickloads before it returns, the response would otherwise land in the wrong timeline. Rule: every load/new-game increments an `epoch_id`; every mutation must carry the epoch it was issued under; the service discards any mutation whose `epoch_id` is older than its current active epoch. This is a more precise mechanism than report 05's "gate writes on watermark receipt" — the two are compatible (epoch fencing is one way to implement that gate).
- **[DESIGN-INPUT] Input buffering during the load window is specified as an explicit rule**: on `kMessage_PreLoadGame`, set an atomic `g_isLoading = true` flag; suppress all event-generation hooks until `kMessage_PostLoadGame` completes, the `TMNL` chunk is transmitted, and the service returns `TIMELINE_READY`.
- **[RISK] Documented crash-level evidence of the Papyrus-not-ready race**: SkyrimNet issue #465, "Save-load crash in `WarmupPapyrusPropertyCache` → `dynamic_character_bio`" — querying Papyrus form properties immediately on `kMessage_PostLoadGame`, before the engine finishes populating property caches, causes null-pointer dereferences. Mitigation proposed: delay Papyrus-derived event triggers by a minimum threshold (e.g. 200ms) after `kPostLoadGame`, or wait for an explicit Papyrus-side initialization heartbeat.
- **[RISK] SkyrimNet PR #476** reportedly fixed a bug where event histories dropped "originator-less" events during quicksave/quickload timeline rebuilds — background/environmental events with no clear originating actor were silently omitted. Relevant if Chronicle's event schema ever allows an event without an actor field.
- **[BUILD-ON] Three-tier GC policy, more concrete than report 05's**: (1) disk-alignment mark-and-sweep — the SKSE plugin scans `Saves/` or listens for `kMessage_DeleteGame`, transmits an active-manifest of extant `SaveUUID`s, service does reachability traversal from all active heads and flags unreachable DAG nodes; (2) tombstone/soft-delete first, to protect against transient file-lock or Mod-Organizer-2 virtual-filesystem visibility gaps during startup scans; (3) hard purge only after a grace period (e.g. 7 days) or a storage threshold, cascading into vector-DB embedding deletion and re-indexing.
- **[RISK] Volatile/uncommitted state needs explicit handling**: events between save points are an "uncommitted transient edge" — held in a volatile buffer keyed to the active `SaveUUID`. On `SAVE_CREATED`, commit the buffer. On reload/death without saving (`SYNC_TIMELINE` for an earlier save), discard the buffer rather than committing it as if it happened.

## Comparative table (as given in the source report)

| Dimension | Mantella/Pantella | CHIM/HerikaServer | SkyrimNet |
|---|---|---|---|
| Backend | External Python; SQLite/JSON | External web server (PHP/Prisma/SQL + vector DB) | Integrated C++ SKSE plugin, async worker threads |
| Temporal IDs | Sequential transcript indices, unindexed | `gamets`, `localts`, `ts` | Save-scoped UUIDs, entity UUIDs, event-history indices |
| Reload handling | Ignore | Append/filter (monotonic log, RAG-relevance filtering) | Reconcile/clean (timeline purge, protected global-knowledge packs survive) |
| Timeline branching | Unhandled | Partial (vector retrieval surfaces anomalies) | Isolated via explicit cleanup protocol |
| Known failure mode | Cross-timeline memory pollution | Personality drift / timestamp desync | Warmup property-cache race crash (#465) |

Note: this report characterizes SkyrimNet as having an explicit "timeline cleanup protocol" (assigns entity/virtual-speaker UUIDs, purges on load, protects curated `.sknpack` world-knowledge from pruning) — a more optimistic read of SkyrimNet's reload handling than report 05, which called SkyrimNet's reload behavior "effectively ignore/implicit." Neither report's characterization is drawn from a primary SkyrimNet design doc; treat as an open disagreement between the two save/reload sources, not just an uncertainty (see open-questions.md).

## Flagged uncertainties (carried into open-questions.md)

- SkyrimNet's "explicit timeline cleanup protocol" claim is sourced to a GitHub Discussion (#387) and repo activity, not a design document — weaker sourcing than the co-save/SKSE mechanics sections of this same report.
- The `TMNL` binary layout and the 4-message WebSocket protocol are this report's own proposal, not something any existing mod implements today — treat as a design starting point, not prior art.
