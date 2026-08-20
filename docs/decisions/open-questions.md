# Open questions

Tensions surfaced by research that contradict an existing decision record or
another report. Resolving one means proposing an ADR update and getting
explicit sign-off before marking it resolved here.

## Resolved by direct repo verification (2026-08-20)

Three factual disagreements between the two `01-skyrim-modding-substrate.md`
source reports were repo-checkable rather than genuinely ambiguous, so they
were resolved directly against GitHub instead of re-researched:

- **MinAI status** — confirmed **deprecated**. `MinLL/MinAI`'s README leads
  with an explicit deprecation banner redirecting users to SkyrimNet; no
  `LICENSE` file in the repo; latest release `2.1.3` published 2025-04-23.
  (The "active, open source" claim in the gemini-sourced report was stale.)
- **Mantella latest release** — confirmed **v0.14, published 2026-04-21**
  (`art-from-the-machine/Mantella`). The compass-sourced report's April 2026
  date was correct; the gemini-sourced report's "December 2025" was stale.
- **CHIM/HerikaServer license** — confirmed **MIT** (`abeiro/HerikaServer`
  ships a top-level `MIT-LICENSE` file; GitHub's detected SPDX license is
  `MIT`). The "GPL-3.0 lineage" claim in the compass-sourced report was
  wrong; the gemini-sourced report's "MIT" was correct.

`docs/research/01-skyrim-modding-substrate.md` has been corrected in place
to reflect these facts.

## Open: SkyrimNet — build-on or study-only?

The two `01-skyrim-modding-substrate.md` source reports gave opposite
recommendations. One treats SkyrimNet as study-only prior art alongside
Mantella/CHIM. The other names it the primary integration target: it's the
only actively maintained framework exposing the exact primitives Chronicle
needs (`RegisterEvent`, `RegisterPackage` for runtime AI-package injection,
`RegisterDecorator`, `DirectNarration`, lifecycle ModEvents), and MinAI's own
README (now verified above) redirects users to it — a strong maintenance
signal.

But the thing that makes SkyrimNet the best integration target is also the
biggest platform risk: its C++ core is closed-source, distributed only as a
compiled DLL via GitHub releases, has no `LICENSE` file (so no legal fork
path if it goes dark), is maintained by one person, and its API can change
between betas.

**This bears directly on ADR-0003** (substrate choice) — SkyrimNet's
maturity was part of the case for targeting Skyrim directly rather than
prototyping elsewhere first, but its closed-binary/single-maintainer risk
argues for hedging rather than committing outright.

**Next step, not yet run:** a short due-diligence research prompt on
SkyrimNet's ecosystem health (Patreon sustainability, community size, the
author's roadmap and stated stance on third-party integrations, whether
other integrators have hit documented API-breakage pain) before ADR-0003 is
finalized. This is risk-sizing, not re-architecture — the fallback
(powerofthree's Papyrus Extender + a standalone SKSE_HTTP/WebSocket bridge)
is already established in both source reports either way.

> I'm evaluating SkyrimNet (`github.com/MinLL/SkyrimNet-GamePlugin`) as the
> primary integration target for an external Python social-simulation
> service, but its C++ core is closed-source (compiled-DLL-only releases,
> no LICENSE file), maintained by one person (MinLL), and its Papyrus/C++
> API can change between betas. Research the health and risk of building
> against it: (1) Patreon/funding sustainability and update cadence —
> is there a pattern of long gaps or abandonment risk; (2) community size
> and the author's stated roadmap and stance on third-party
> integrations/forks, including any public statement on what happens to
> the project if development stops; (3) documented API-breakage pain from
> other integrators or mod authors who built against SkyrimNet's
> `RegisterEvent`/`RegisterPackage`/`RegisterDecorator` API across beta
> versions — check issue trackers, Discord-adjacent forum posts, and
> changelogs, not just the docs; (4) whether MinAI's deprecation and
> redirect to SkyrimNet (confirmed: MinAI's README now explicitly points
> users to SkyrimNet) reflects a healthy consolidation or a
> single-point-of-failure concentration risk for the AI-NPC modding
> ecosystem as a whole. End with a risk rating (low/medium/high) for
> building Chronicle's primary integration against SkyrimNet's API as-is,
> versus building the standalone powerofthree's-Extender + SKSE_HTTP
> fallback from day one and treating SkyrimNet as optional.

## Open: save/reload timeline consistency — a gap none of the 4 prompts covered

Every filed research report implicitly assumes the sim runs alongside a
continuously-progressing game. It doesn't: Skyrim players save, die,
reload, and roll back hours or days constantly. If the player reloads a
save from before the Jarl died, Chronicle's event log now contains events
(the assassination, the succession contest, every rumor derived from it)
that never happened in the timeline the player is now in.

The event-sourced core (`docs/decisions/0002-event-sourcing.md`) is
plausibly the right substrate for this — snapshot per save, fork the
timeline on reload — but this needs its own research pass: nobody has yet
looked at how Mantella, CHIM, or SkyrimNet actually reconcile their
external memory stores against save-scumming, or whether SKSE's co-save
serialization (`SerializationInterface`) is the right anchor for letting an
external process identify which timeline a loaded save belongs to.

**Assessment: this is arguably the single hardest unsolved integration
problem in the project.** Not yet scheduled — flagging here so it doesn't
get lost, and drafting the prompt now so it's ready to fire.

> I'm building an external Python service that maintains persistent world
> state (NPC beliefs, rumors, relationships) alongside Skyrim SE/AE.
> Research how external-state mods handle save/load/reload consistency:
> (1) how Mantella, CHIM/HerikaServer, and SkyrimNet reconcile their
> external memory stores when the player reloads an earlier save, dies, or
> maintains multiple characters/save slots — do they roll back, fork,
> ignore, or corrupt? Find bug reports and design discussions, not just
> docs; (2) SKSE co-save serialization (SKSE's `SerializationInterface`) —
> what it can store, how mods use it to keep plugin state atomic with the
> `.ess` save file, and whether a save-embedded UUID/timestamp is the
> standard pattern for letting an external process identify which timeline
> a loaded save belongs to; (3) how the event-sourcing community handles
> timeline forking and branch garbage-collection in analogous domains;
> (4) any Skyrim mods that detect save-load events at runtime
> (`OnPlayerLoadGame`) and what race conditions exist between game load and
> external-service notification. End with a recommended sync protocol for
> an external service.

## Deferred: economic simulation

None of the four research prompts covered economic simulation (prices,
supply, the trade-ripple layer of the Jarl-assassination north-star
scenario in `docs/vision.md`) — it's slated as a later tier (v0.4),
deliberately out of scope while the belief tier is unproven. Noting it here
so it doesn't silently vanish from the plan.
