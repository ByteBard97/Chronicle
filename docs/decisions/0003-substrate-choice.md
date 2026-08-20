---
status: accepted
date: 2026-08-20
---

# 0003: Build against Skyrim directly, via a Substrate Abstraction Layer

## Status

**Accepted.** Was DRAFT pending research; resolved by
`docs/research/07-skyrimnet-substrate.md`.

## The original tension

**Case for prototyping elsewhere (RimWorld, or from scratch in 2D):** Skyrim's
engine constraints and mod-installation friction make it a poor
*laboratory* — "Skyrim is the destination, not the laboratory." Validate
the belief/rumor/grudge model somewhere cheap to iterate on, then port to
Skyrim once it's an integration problem rather than a design problem.

**Case for targeting Skyrim directly:** the external-service architecture
(`0001-external-service-architecture.md`) means most engine constraints
don't apply to Chronicle's actual simulation logic, only to the thin
adapter seam; Mantella/CHIM/SkyrimNet already provide a maintained
presentation layer a from-scratch prototype would have to fake anyway.

## What research found

`docs/research/01-skyrim-modding-substrate.md` established that real
integration surface exists — SkyrimNet's Papyrus/C++ API
(`RegisterEvent`, `RegisterPackage` for runtime AI-package injection,
`RegisterDecorator`, `DirectNarration`, lifecycle ModEvents) is the closest
thing the ecosystem has to exactly what Chronicle needs, and MinAI's own
deprecation notice redirects users to it — a real, if informal,
consolidation signal.

But `docs/research/07-skyrimnet-substrate.md` sized the platform risk of
depending on it directly and rated that **HIGH RISK**: SkyrimNet's C++
core is closed-source, distributed only as a compiled DLL, has no LICENSE
file (no legal fork path if the project stalls or an unpatched game update
breaks it), is maintained by a single Ko-fi-funded developer, has already
shown documented API-version drift breaking compiled integrations across
beta shifts (Public API bumped to v9 at Beta 20), and — because it's
in-process — a core exception is a crash-to-desktop, not a degraded
external service.

## Decision

**Target Skyrim directly, through a Substrate Abstraction Layer (SAL).**

Chronicle defines its domain events (deaths, crimes, cell attach/detach,
dialogue, package changes, item transfers — see `docs/architecture.md`)
against a **generic Python provider interface** that lives at the boundary
of `chronicle/` and `adapters/`. Two providers implement it, both under
`adapters/skyrim/`:

- **Primary provider — SkyrimNet.** Targets SkyrimNet's Papyrus/C++ event
  pipeline for low-latency, direct-memory state access when SkyrimNet is
  installed and its API is compatible with the version Chronicle was
  built against.
- **Secondary provider — standalone bridge.** powerofthree's Papyrus
  Extender plus an open-source SKSE HTTP/WebSocket bridge, reimplementing
  the same provider interface without depending on SkyrimNet's closed
  binary.

This resolves the original tension without picking a side: Chronicle
still targets Skyrim directly (no RimWorld/2D prototype detour), but
doesn't take on SkyrimNet's platform risk as an unhedged dependency. The
combined SAL approach is rated **MEDIUM RISK** by the same report that
rated direct coupling HIGH RISK.

## Rationale

- The scaffold already isolates Skyrim-specific code in `adapters/skyrim/`
  (`0001-external-service-architecture.md`) — the SAL formalizes that
  existing boundary as an explicit provider interface with two
  implementations, rather than requiring new architecture.
- SkyrimNet's maintenance signal (active development, ecosystem
  consolidation via MinAI's redirect) is real and worth capturing when
  available — the SAL captures it via the primary provider without
  requiring it.
- A no-LICENSE closed DLL is not a risk that due diligence, monitoring, or
  a support contract can mitigate — the only mitigation available is
  architectural: never make it a single point of failure.

## Consequences

- The provider interface itself is Chronicle's contract, and it must be
  designed before either provider is implemented — this becomes the first
  piece of `adapters/skyrim/` code, ahead of either SkyrimNet-specific or
  standalone-bridge-specific code.
- `chronicle/` stays engine-agnostic either way; neither provider choice
  changes anything about `chronicle/events.py` or the belief-facet store.
- Chronicle must track SkyrimNet's Public API version it was built
  against and fail loudly (fall back to the secondary provider, or refuse
  to start with the primary) rather than silently misbehave on a version
  bump — this is a direct consequence of the documented API-drift risk.
- If SkyrimNet's licensing situation is ever clarified (a LICENSE file
  added, or an explicit statement from MinLL), this ADR's risk rating for
  the primary provider should be revisited, but the SAL architecture
  itself doesn't need to change either way.

## Related

`docs/research/07-skyrimnet-substrate.md` also independently re-derived
the co-save timeline synchronization design from ADR-0004/0005 — see
those ADRs' updated rationale sections for the third convergence.
