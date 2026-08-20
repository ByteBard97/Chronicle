# Ideas

Unsorted. Promote to `docs/vision.md` or a new ADR once an idea earns it.

## Action items

- **Ask MinLL (SkyrimNet's maintainer) directly, in the SkyrimNet
  Discord, for (a) an explicit license for the closed C++ core and (b) an
  open-source-on-abandonment / succession commitment.** A targeted,
  exhaustive-as-possible search (GitHub, docs, FAQ, Patreon, Ko-fi,
  Reddit) found no public statement on either — see
  `docs/research/10-skyrimnet-health.md`. The Discord and Ko-fi couldn't
  be exhaustively searched, so a statement could already exist there;
  asking directly is the fastest way to close that gap either way.
  Getting either commitment in writing would materially lower the risk
  rating in `docs/decisions/0003-substrate-choice.md` and is one of the
  two explicit conditions (alongside API stabilization) for promoting the
  SkyrimNet adapter back to primary. Not blocking — Chronicle's reference
  implementation doesn't depend on the answer — but worth doing early
  since the answer changes a real architectural decision.

- **Decide the target Skyrim game version (SE 1.5.97 vs AE/1.6.x) before
  `adapters/skyrim/` work starts.** None of the research addresses this
  at all — it's a real gap, not an oversight the research resolved. The
  Anniversary Edition's forced 1.6.x runtime update has a documented
  history of breaking existing SKSE plugins overnight (the same
  engine-update-fragility risk `docs/research/01-skyrim-modding-substrate.md`
  already flags), which is why a lot of the modding community
  deliberately stays on the older 1.5.97 branch via Steam's Betas tab.
  User flagged (2026-08-20) that Skyrim versioning is "a thorny problem"
  and plans to research it themselves before this becomes a blocker.
  Also decide exact pinned versions of SKSE64, Address Library,
  powerofthree's Extender, and (if used) the SkyrimNet beta at the same
  time — the research names the tools but not specific version numbers.

- **When `adapters/skyrim/` work actually starts (v0.2), install and
  smoke-test the SKSE bridge dependencies**: SKSE64, Address Library for
  SKSE Plugins, powerofthree's Papyrus Extender (Nexus SE 22854, MIT —
  the reference-implementation dependency), and either Leidtier's
  `SKSE_HTTP` (license unconfirmed — verify first) or a custom
  CommonLibSSE-NG WebSocket plugin (`SkyrimScripting/SKSE_Template_WebSockets`
  as a starting template). Not needed for any current headless work.

- **Check whether Mutagen / xEdit's Info NPC Extractor (already the
  recommended NPC data ingestion path, `docs/research/01-skyrim-modding-substrate.md`)
  also cleanly surfaces AI-package/schedule data and cell/worldspace
  coordinates, not just names/bios.** The dashboard's map view and the
  math tier's encounter sampling (`docs/architecture.md`) both need NPC
  location-over-time data, and nobody's verified the ingestion toolchain
  covers that case. A v0.2+/`adapters/skyrim/`-side concern — doesn't
  block current headless work, but worth a quick targeted check before
  the map view or encounter sampling gets built for real.
