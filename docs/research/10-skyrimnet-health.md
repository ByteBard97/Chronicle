---
date: 2026-08-20
sources:
  - "research/compass_artifact_wf-51dabde7-265e-55b7-a83b-6dac798ea2ce_text_markdown.md (originally: Building Chronicle Against SkyrimNet: Health, Risk, and Integration Strategy)"
topic: "SkyrimNet health deep-dive — inverts ADR-0003's provider priority"
status: filed
---

# SkyrimNet health deep-dive

A second, deeper due-diligence pass on SkyrimNet, superseding report 07's
provider-priority conclusion (not its risk analysis, which this report
confirms and sharpens). Where report 07 recommended SkyrimNet as primary
provider with a standalone fallback, this report — working from actual
release history and integrator bug trails rather than a point-in-time
risk rating — inverts that: **the standalone path is the reference
implementation, SkyrimNet is an optional pinned adapter.** See
`docs/decisions/0003-substrate-choice.md`, amended.

## Findings

- **[DESIGN-INPUT, decisive — reverses report 07] Provider priority inverts.** Report 07 rated direct SkyrimNet coupling HIGH RISK and recommended it as *primary* provider behind a SAL anyway, with the standalone bridge as secondary. This report's risk ratings are more granular and land differently: SkyrimNet-as-sole-primary = MEDIUM-HIGH; standalone-path-first-with-SkyrimNet-optional = LOW-MEDIUM. The difference isn't a disagreement about SkyrimNet's risk (both agree it's substantial) — it's that this report has concrete evidence the *API churn*, not just the licensing/bus-factor risk, makes SkyrimNet unsuitable as the foundation Chronicle is built against from day one.
- **[RISK, concrete] The public C++ API is churning fast, with real integrator breakage.** v6 (Beta18, Mar 30) → v9 (Beta20, May 2) — three version bumps in about a month. Beta21 shipped an explicit "Breaking Changes" section. Concrete downstream damage: IntelEngine v3.5.0 hard-requires SkyrimNet v9 for a specific exported symbol (`PublicGetWorldKnowledgeForActor`); IntelEngine v3.2.1 shipped a feature blocked on an *unreleased* SkyrimNet build; SeverActions v3.0.1 had an init-ordering deadlock (its decorators registered before SkyrimNet finished initializing); SeverActions v2.9.9 had to rebase a prompt off a changed `npc.UUID` schema after Beta19.
- **[RISK, confirmed and sharpened] Still no LICENSE, still no continuity statement — now confirmed as a *targeted, exhaustive-as-possible* negative search**, not just "not found in passing." Checked: GitHub repo (README/discussions/issues/wiki), docs site, FAQ, Patreon, Ko-fi, Reddit. None state what happens to the closed DLL if the maintainer (MinLL/"Min") stops. Default copyright applies (no LICENSE = all rights reserved) — no legal fork path, full stop. The report is explicit that the invite-only Discord and Ko-fi couldn't be exhaustively searched, so a statement could exist there — which is exactly why the recommended action (ask directly) matters.
- **[DESIGN-INPUT] The project is healthy right now — the risk is churn and no-continuity-path, not abandonment.** Weekly-to-biweekly releases through Beta23.1 (Aug 10-11, 2026); 1,209 Patreon members ($5 entry); 290 GitHub stars/42 forks (climbing during the research window: 177→242→290); ~5,000 Discord members. This matters: the risk case for de-prioritizing SkyrimNet as primary isn't "it might die," it's "its churn rate makes it a bad foundation, and if it does die, nothing can be legally continued."
- **[BUILD-ON, upgrades the fallback's status] powerofthree's Papyrus Extender isn't a weaker fallback — it's the stronger foundation.** MIT-licensed, open-source, and — the key fact — **already a required dependency of SkyrimNet itself**. This means the "fallback" stack is more battle-tested than the primary candidate, not less: SkyrimNet's own reliability depends on po3's Extender being solid.
- **[BUILD-ON] Concrete integration tactics, adopted into ADR-0003/architecture**: pin any SkyrimNet adapter to one specific beta and its declared Public API version; implement a startup version handshake that refuses to run against a mismatched version (mirroring IntelEngine's own "requires SkyrimNet v9" gating); isolate all `Register*`/`RegisterEventByUUID`-style calls behind one adapter module with contract tests, so an upstream break is a one-file fix; explicitly guard init ordering (SeverActions' deadlock is the cautionary tale — register only after SkyrimNet finishes its own initialization); never redistribute the DLL.
- **[DEFER, with thresholds] Concrete conditions for re-promoting SkyrimNet to primary, or dropping it entirely** — not vague "revisit later" language: promote if Min publishes a real license *and* a credible succession/open-source-on-abandonment commitment *and* the API stabilizes (a v1.0 with semver + no breaking bumps across 2-3 release cycles); drop the adapter entirely if release cadence stalls 2-3+ months with unanswered issues, or breaking bumps continue every release with no compatibility shims.
- **[DESIGN-INPUT] Mantella is a viable open-source primary-target alternative if the SAL's hedge is judged insufficient** — noted as a threshold condition ("re-evaluate Mantella as primary if you want a fully open-source foundation today"), not a recommendation to switch now. Kept as a documented fallback-of-the-fallback, not acted on.
- **[DESIGN-INPUT] The MinAI→SkyrimNet consolidation is rational within Min's own portfolio, and doesn't collapse the wider ecosystem to a single point of failure** — Mantella and CHIM remain architecturally independent. The actual SPOF is narrower than "the ecosystem": it's specifically SkyrimNet's closed C++ core, for anyone who builds *exclusively* on it. Confirms (doesn't newly discover) report 07's ecosystem-consolidation finding.

## Recommended architecture (as given in the source report)

1. Build Chronicle against an internal abstraction (a provider interface) with the po3-Extender + SKSE-HTTP/external-server path as the **reference implementation**, and a SkyrimNet adapter as an **optional plugin** behind the same interface. No SkyrimNet-specific types leak into Chronicle's core.
2. Pin any shipped SkyrimNet adapter hard: one beta, one declared Public API version, a startup handshake that refuses to run on mismatch.
3. Isolate `Register*` calls in one adapter module with contract tests; guard init ordering explicitly.
4. Mitigate the legal/continuity gap: never redistribute the DLL, integrate only against the documented public API at arm's length, and directly ask Min for a license + continuity statement — getting it in writing changes the risk math.

## Flagged uncertainties

- All community-size figures (Patreon/GitHub/Discord counts) are point-in-time snapshots captured at slightly different moments in mid-2026, not audited — treat trend direction (growing) as more reliable than exact counts.
- The "no continuity statement exists" finding is a negative result across publicly searchable sources only; the invite-only Discord and Ko-fi weren't exhaustively searchable. This is precisely the gap the recommended Discord outreach (see `notes/ideas.md`) is meant to close.
