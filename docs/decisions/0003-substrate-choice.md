---
status: accepted
date: 2026-08-20
---

# 0003: Build against Skyrim directly, via a Substrate Abstraction Layer

## Status

**Accepted, amended 2026-08-20.** Was DRAFT pending research; resolved by
`docs/research/07-skyrimnet-substrate.md` (SAL architecture, adopted and
unchanged). **Amended** by `docs/research/10-skyrimnet-health.md`, which
inverts which SAL provider is primary — see "Amendment," below. The SAL
architecture itself (a generic provider interface, no SkyrimNet-specific
types leaking into `chronicle/`) is unchanged by this amendment; only the
provider priority and the specifics of how the SkyrimNet provider is
built change.

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

- **Reference implementation — standalone bridge.** powerofthree's
  Papyrus Extender (MIT-licensed, open-source, and — notably — already a
  required dependency of SkyrimNet itself, so it's more battle-tested
  than SkyrimNet's own core) plus an open-source SKSE HTTP/WebSocket
  bridge. Built first; Chronicle's own integration tests and scenarios
  target this provider by default.
- **Optional adapter — SkyrimNet.** Targets SkyrimNet's Papyrus/C++ event
  pipeline for low-latency, direct-memory state access when SkyrimNet is
  installed. Pinned hard to one specific SkyrimNet beta and its declared
  Public API version, with a startup version handshake that refuses to
  run against a mismatched version rather than degrading silently.

This resolves the original tension without picking a side: Chronicle
still targets Skyrim directly (no RimWorld/2D prototype detour), but
doesn't build its foundation on SkyrimNet's churn. The combined SAL
approach is rated **LOW-MEDIUM RISK** with the standalone path as
reference implementation (report 10) — stronger than the MEDIUM RISK
rating report 07 gave the SAL when SkyrimNet was primary.

## Amendment (2026-08-20): provider priority inverts

Report 07 rated direct SkyrimNet coupling HIGH RISK but still recommended
it as the SAL's *primary* provider, with the standalone bridge as
secondary/fallback. Report 10's deeper pass — working from actual release
history and integrator bug trails rather than a point-in-time risk rating
— found evidence specific enough to invert that priority:

- **The public C++ API churns fast, with real integrator breakage**: v6 →
  v9 in about a month (Beta18 → Beta20); Beta21 shipped an explicit
  "Breaking Changes" section. IntelEngine v3.5.0 hard-requires SkyrimNet
  v9 for a specific exported symbol; IntelEngine v3.2.1 shipped a feature
  blocked on an *unreleased* SkyrimNet build; SeverActions v3.0.1 hit an
  init-ordering deadlock against SkyrimNet's own startup sequence;
  SeverActions v2.9.9 had to rebase off a changed `npc.UUID` schema.
- **No LICENSE, no continuity statement — confirmed via a targeted,
  exhaustive-as-possible search** (GitHub repo, docs, FAQ, Patreon, Ko-fi,
  Reddit), not just "not found in passing." Default copyright applies: no
  legal fork path if the maintainer (MinLL) stops.
- **The "fallback" is the stronger foundation, not a weaker one**:
  powerofthree's Extender is a required dependency of SkyrimNet itself.
  Chronicle depending on it directly is not a downgrade from depending on
  SkyrimNet — it's depending on the same foundation SkyrimNet already
  depends on, without SkyrimNet's additional churn and licensing risk on
  top.
- **The project is healthy right now** — weekly-to-biweekly releases,
  1,209 Patreon members, ~5,000 Discord members, growing star count. The
  risk case is churn and no-continuity-path, not abandonment; this is why
  the decision is "not primary," not "don't integrate at all."

**Concrete thresholds for revisiting this amendment** (from report 10,
adopted verbatim):

- **Promote SkyrimNet to primary** if Min publishes a real license *and* a
  credible succession/open-source-on-abandonment commitment *and* the
  Public API stabilizes (a v1.0 with semver + no breaking bumps across
  2-3 release cycles).
- **Drop the SkyrimNet adapter entirely** if release cadence stalls
  2-3+ months with unanswered issues, or breaking API bumps continue
  every release with no compatibility shims.
- **Re-evaluate Mantella as primary target instead** if a fully
  open-source foundation is wanted today and the external-server setup
  cost (no in-process latency advantage) is judged acceptable — noted as
  a fallback-of-the-fallback, not acted on now.

## Rationale

- The scaffold already isolates Skyrim-specific code in `adapters/skyrim/`
  (`0001-external-service-architecture.md`) — the SAL formalizes that
  existing boundary as an explicit provider interface with implementations,
  rather than requiring new architecture.
- SkyrimNet's maintenance signal (active development, ecosystem
  consolidation via MinAI's redirect) is real, but report 10's evidence is
  that this signal describes *current health*, not *foundation stability*
  — a fast-churning API is a bad thing to build the reference
  implementation against, even when the churn comes from active
  development rather than neglect.
- A no-LICENSE closed DLL is not a risk that due diligence, monitoring, or
  a support contract can mitigate — the only mitigation available is
  architectural: never make it the foundation, keep it strictly optional
  and pinned.
- Building the reference implementation on powerofthree's Extender isn't
  a compromise — it's building on the same dependency SkyrimNet itself
  requires, which makes it a stronger foundation choice, not a weaker one.

## Consequences

- The provider interface itself is Chronicle's contract, and it must be
  designed before either provider is implemented — this becomes the first
  piece of `adapters/skyrim/` code. The standalone (po3 + SKSE-HTTP)
  provider is built and tested first; the SkyrimNet adapter is optional
  and can land later without blocking anything.
- `chronicle/` stays engine-agnostic either way; neither provider choice
  changes anything about `chronicle/events.py` or the belief-facet store.
- If a SkyrimNet adapter is built, it must track the specific Public API
  version it was pinned against and fail loudly at startup (refuse to
  run, with a clear message) on a version mismatch — never silently
  misbehave. All `Register*`/`RegisterEventByUUID`-style calls are
  isolated behind one adapter module with contract tests, so an upstream
  API break is a one-file fix, not a Chronicle-wide refactor. Init
  ordering is guarded explicitly — register only after SkyrimNet finishes
  its own initialization (SeverActions' startup deadlock, report 10 §3,
  is the cautionary tale). The DLL itself is never redistributed with
  Chronicle.
- If SkyrimNet's licensing/continuity situation is ever clarified (a
  LICENSE file added, or an explicit statement from MinLL) *and* its API
  stabilizes per the thresholds above, this ADR's provider priority
  should be revisited — but the SAL architecture itself doesn't need to
  change either way.
- A direct outreach to SkyrimNet's maintainer (Discord) requesting a
  license and continuity statement is tracked as an action item in
  `notes/ideas.md` — getting either in writing is the fastest path to
  reconsidering this amendment.

## Related

`docs/research/07-skyrimnet-substrate.md` also independently re-derived
the co-save timeline synchronization design from ADR-0004/0005 — see
those ADRs' updated rationale sections for the third (and, via report 09,
fourth) convergence.

`docs/architecture.md`'s Substrate Abstraction Layer section reflects this
amendment's inverted priority and the adapter-isolation tactics (contract
tests, init-ordering guard, no DLL redistribution).
