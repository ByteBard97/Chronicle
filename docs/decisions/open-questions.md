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

## Closed: save/reload timeline consistency (2026-08-20)

Reports [05](../research/05-save-reload-sync-protocol.md) and
[06](../research/06-save-reload-timeline-sync.md) answered the prompt that
was drafted here. Both independently converged on the same core design —
event-sourced service, save-embedded `SaveUUID`/generation identity via
SKSE co-save, fork-on-reload rather than rollback, tombstone-then-reap
branch GC — which is now captured in
[ADR-0004](0004-timeline-branching.md) and
[ADR-0005](0005-sync-handshake.md), with a corresponding branch-key change
to `chronicle/events.py`.

**Sub-disagreement, not fully resolved**: the two reports characterize
SkyrimNet's own reload handling differently — report 05 calls it
"effectively ignore/implicit" (in-process, no cross-process fork
mechanism); report 06 describes an "explicit timeline cleanup protocol"
(entity/virtual-speaker UUIDs, purge-on-load, protected knowledge packs),
sourced to a GitHub Discussion rather than a design doc. This doesn't block
Chronicle's own protocol (which doesn't depend on how SkyrimNet handles
*its* reloads), but it's relevant input to the still-open SkyrimNet
due-diligence question below, so it's tracked rather than dropped.

**Implementation-risk notes carried forward** (uncertainties the source
reports flagged as unconfirmed, not settled facts):

- **CHIM's exact fork/prune trigger is reconstructed, not confirmed.** The
  specific numeric threshold (how many in-game days back counts as
  "old enough to fork") is inferred from CHIM's FAQ, Nexus changelog, and
  HerikaServer's timestamp field names — no primary Dwemer Dynamics source
  states the actual number. Don't copy a specific threshold value from
  either report as if it were verified; treat Chronicle's own threshold as
  a tunable to be set empirically.
- **The save-embedded-UUID pattern has no confirmed Skyrim precedent.**
  The strongest published prior art for "GUID-on-start + heartbeat, detect
  reload by comparing stored state against the save's clock" is from a
  different engine (the Neverwinter Nights "realms" module). Skyrim mods
  more commonly reconcile via timestamp comparison (CHIM's `gamets`) than
  via a stored GUID. Chronicle will be implementing and testing this
  co-save read/write path essentially from scratch — budget for that.
- **SKSE's `.skse`/`.ess` pairing is atomic by convention, not guaranteed.**
  Neither SKSE's headers nor either report claim transactional atomicity —
  `kPostLoadGame`'s success boolean exists precisely because a load can
  fail after `kPreLoadGame` fires. ADR-0005's idempotency/versioning rules
  exist to cover this gap, but a crash between co-save and `.ess` writes
  remains a residual risk worth a scenario test once the shim exists.

## Deferred: economic simulation

None of the four research prompts covered economic simulation (prices,
supply, the trade-ripple layer of the Jarl-assassination north-star
scenario in `docs/vision.md`) — it's slated as a later tier (v0.4),
deliberately out of scope while the belief tier is unproven. Noting it here
so it doesn't silently vanish from the plan.
