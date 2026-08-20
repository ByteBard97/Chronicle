---
date: 2026-08-20
sources:
  - "research/Skyrim Substrate Integration Research.md (originally: System Architecture Report: SkyrimNet Platform Risk Sizing and Save-State Timeline Reconciliation for External AI Services)"
topic: "SkyrimNet ecosystem due-diligence — resolves ADR-0003"
status: filed
---

# SkyrimNet ecosystem due-diligence

Answers the due-diligence prompt drafted in `open-questions.md`. Resolves
ADR-0003 (substrate choice) — see that ADR for the decision itself; this
file is the evidence behind it. Also independently re-derives the
save/reload sync design from reports 05/06 (a third convergence — see
ADR-0004/0005).

## Findings

- **[RISK, decisive] Direct SkyrimNet coupling rated HIGH RISK.** Closed C++ core, DLL-only distribution, no LICENSE file — no legal fork path if the project stalls or a game update breaks it unpatched. Single maintainer (MinLL), funded via Ko-fi rather than institutional backing — a real bus-factor risk despite high commit velocity. In-process design means a core exception is a **crash-to-desktop**, not a degraded external service.
- **[BUILD-ON, decisive] Substrate Abstraction Layer (SAL) rated MEDIUM RISK, adopted.** Define Chronicle's domain events against a generic Python provider interface from day one. Primary provider targets SkyrimNet's Papyrus/C++ event pipeline for low-latency state access; secondary provider implements the same interface using powerofthree's Papyrus Extender + an open-source SKSE HTTP/WebSocket bridge. This hedges binary deprecation while preserving performance when SkyrimNet is available. See ADR-0003.
- **[RISK] Documented API-version drift breaks compiled integrations.** SkyrimNet's Public API bumped to v9 at Beta 20; version bumps break binary compatibility across major beta shifts, requiring downstream native plugins to recompile. Also documented: action-cache stalls (expiration timers refreshed on cache hits, locking NPCs into stale action loops), event-history loss (events lacking an explicit originator ID dropped from the queue — same failure class report 06 also flagged), hardcoded port-8080 assumptions breaking custom configs.
- **[DESIGN-INPUT] Ecosystem consolidation is real and double-edged.** MinAI's deprecation and redirect to SkyrimNet (confirmed independently via GitHub in report 01's follow-up) represents genuine consolidation of community effort onto one high-performance runtime — but that consolidation is exactly what concentrates platform risk onto one closed binary. The SAL is the correct response to this specific dynamic, not a generic hedge.
- **[BUILD-ON] Third independent confirmation of the co-save timeline design.** This report re-derives, without prompting from reports 05/06, the same core mechanism: a `SaveHeader` co-save record (`timeline_uuid`, `save_epoch`, `last_event_id`) written via `SKSE::SerializationInterface`, fork-on-reload via DAG branching, and a load handshake that mutes the event pipeline until the external service acknowledges the active timeline. It includes a concrete C++ sketch (`ChronicleSync::OnGameSave`/`OnGameLoad`) and its own wire protocol (`SAVE_NOTIFY`/`LOAD_REQUEST`/`SYNC_READY`) — differs in field names from reports 05/06 but is architecturally identical. See ADR-0004/0005's updated rationale sections.
- **[RISK] Orphan-branch retention window given as a concrete default**: 48 hours with no new events and no associated save file on disk marks a branch orphaned, pending pruning that preserves shared ancestor nodes. Consistent with (not contradicting) reports 05/06's "configurable retention window" — this is a reasonable starting default, not a verified constant.
- **[DEFER] Comparative fragmented-vs-consolidated ecosystem table** (Mantella/CHIM/Herika as "fragmented, open, higher-latency" vs. SkyrimNet as "consolidated, closed, low-latency") is useful framing but doesn't change the SAL decision — Chronicle hedges regardless of which side of that tradeoff turns out to matter more in practice.

## Risk rating table (as given in the source report)

| Metric | SkyrimNet direct coupling | Standalone fallback (PO3 Extender + SKSE_HTTP) |
|---|---|---|
| Latency | Direct C++ memory reads, zero-serialization | IPC payload serialization (JSON over HTTP/WebSocket) |
| Maintenance risk | High — single maintainer, closed binary | Low — PO3 Extender and HTTP bridges are open source |
| API drift resilience | Low — C++ API v9-style bumps break compiled integrations | High — standard Papyrus interfaces stable across game builds |
| Licensing/forkability | None — no LICENSE file, DLL binary only | Fully open-source ecosystem standard |
| **Combined rating** | **HIGH RISK** as sole dependency | **MEDIUM RISK** as part of a SAL hedge |

## Recommended architecture (as proposed by the report)

1. **Substrate Abstraction Layer**: isolate all runtime mod interfaces (`RegisterEvent`, `RegisterPackage`, `RegisterDecorator`) behind an internal API provider interface. Primary deployment targets SkyrimNet; open-source fallback insulates against closed-binary deprecation.
2. **Event-sourced co-save synchronization engine**: SKSE bridge wrapper tags `.skse` co-saves with atomic Timeline UUIDs; external event DAG forks branches on save rollback; strict message-freeze during load windows.

## Flagged uncertainties

- The specific "48 hour" orphan-branch retention default and the "200ms"-class timing figures throughout this report's protocol section are the report's own proposal, consistent with but not more authoritative than reports 05/06's equivalent (also-proposed, also-untested) figures. Treat all such constants as tunables pending real implementation.
- `PublicGetWorldKnowledgeForActor` and other named SkyrimNet C++ entry points are cited to the project's own public header/discussion threads — accurate as of this survey, but SkyrimNet's own findings above establish that this API surface can change between betas.
