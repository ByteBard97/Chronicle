---
status: accepted
date: 2026-08-21
---

# 0008: Game version pin

## Context

`notes/ideas.md` flagged this as a real gap on 2026-08-20: no research
report addressed which Skyrim game version to target, and you noted
versioning was "a thorny problem" you'd research yourself. That happened
sooner than expected — Bethesda shipped patch **1.7.99** on 2026-08-20,
the first update in two and a half years, which broke the native SKSE
plugin ecosystem exactly as `docs/research/01-skyrim-modding-substrate.md`
had flagged as a live risk. Three independent research reports
(`docs/research/11-version-pin-and-transport.md`) answered the resulting
question same-week.

## Decision

**Pin to game version 1.6.1170 + SKSE64 2.2.6.** Do not target 1.7.99.

Full dependency pin:

| Layer | Pin |
|---|---|
| Game | Skyrim SE/AE **1.6.1170** (Steam) |
| SKSE | **2.2.6** (2.2.7/2.2.8 also acceptable — same 1.6.1170 target, add plugin-preload support) |
| Address Library for SKSE Plugins | All-in-one package, **v11+** |
| powerofthree's Papyrus Extender | Current release, "AE 1.6.1170 and higher" build |
| PapyrusUtil SE | **4.6** |
| SSE Engine Fixes | Part 1, **v6.1.1/6.2** (1.6.1170 build) |
| HTTP bridge | Leidtier's SKSE_HTTP (Mantella-parity) or a custom CommonLibSSE-NG + Address Library plugin (ADR-0003's reference-implementation path) |
| Proton | GE-Proton (latest) or Proton Experimental |

Lock procedure (Linux): `download_depot 489830 <depot> <manifest>` via
the Steam console for each of the three 1.6.1170 depots (values in
`docs/research/11-version-pin-and-transport.md`), copy over the install,
freeze `appmanifest_489830.acf` (`chmod a-w` / `chattr +i`), set "only
update this game when I launch it," and always launch through
`skse64_loader.exe`, never the Steam Play button.

**Revisit trigger** (adopted from the research, not invented): move the
pin to 1.7.99 when (a) PapyrusUtil ships a 1.7.99 build, (b) SSE Engine
Fixes updates, and (c) any AI-NPC framework Chronicle ends up depending
on posts a 1.7.99 build. Community estimate: late September–October 2026.
Don't revisit preemptively.

## Rationale

- Unanimous across three independently-researched reports, for the same
  reason each time: 1.6.1170 has been the ecosystem standard for 2.5
  years, and — decisively — **all three AI-NPC frameworks (Mantella,
  CHIM, SkyrimNet) are built against it today**, with none documenting
  1.7.99 support. Targeting anything else would mean building against a
  moving, currently-broken target.
- The depot manifest values are cross-corroborated across all three
  independent reports (not copies of one source) — real evidence, not
  just repeated claims.
- Doesn't block anything current: v0.1 is headless (`docs/v0.1-spec.md`),
  so this pin only becomes operationally relevant when `adapters/skyrim/`
  work actually starts (v0.2). Deciding it now removes it from the list
  of things that could stall that work later.

## Consequences

- `docs/architecture.md`'s deployment target section should reference this
  pin.
- ADR-0003's SAL reference implementation (standalone bridge) should be
  built and tested against 1.6.1170 + SKSE 2.2.6 specifically, not
  "whatever's current" — this is a direct consequence of SKSE's own
  policy of supporting only the latest Steam runtime per release, which
  means "latest" and "the version everything else targets" are two
  different things right now.
- If a SkyrimNet adapter is ever built (ADR-0003, optional), it must be
  pinned to a SkyrimNet release built against 1.6.1170, consistent with
  ADR-0003's existing startup-version-handshake requirement — this ADR
  doesn't change that requirement, just supplies the concrete version.
- Address Library alone is not sufficient to survive every future patch —
  the research surfaced (and one report initially got wrong, corrected by
  a same-week follow-up) that Address Library only remaps *function
  addresses*; a patch that changes compiled-in class/struct layouts still
  requires a recompile against updated CommonLib headers regardless of
  Address Library. Not actionable today (we're pinned below 1.7.99
  anyway) but worth remembering for the eventual 1.7.99 migration.
- No action needed on this machine or the Linux dev box until `adapters/skyrim/`
  work starts — this ADR records the decision, not an immediate task.

## Related

`docs/research/11-version-pin-and-transport.md` for the full evidence.
Resolves the version-pin action item in `notes/ideas.md`.
