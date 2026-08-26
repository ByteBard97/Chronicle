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

- ~~Decide the target Skyrim game version before `adapters/skyrim/` work
  starts.~~ **Resolved 2026-08-21 — see
  [ADR-0008](../docs/decisions/0008-game-version-pin.md).** Pin to
  **1.6.1170 + SKSE64 2.2.6** (not 1.7.99, the patch that shipped
  2026-08-20 and broke the plugin ecosystem exactly as
  `docs/research/01-skyrim-modding-substrate.md` had flagged as a live
  risk). Full dependency pin table and revisit trigger (late Sept-Oct
  2026) in the ADR; evidence in
  `docs/research/11-version-pin-and-transport.md`.

- ~~When `adapters/skyrim/` work actually starts (v0.2), install and
  smoke-test the SKSE bridge dependencies~~ **Resolved by research
  2026-08-23 — see
  [docs/research/22-native-skse-plugin-prior-art.md](../docs/research/22-native-skse-plugin-prior-art.md).**
  Build a first-party CommonLibSSE-NG plugin ("ChronicleBridge") over
  **IXWebSocket** (BSD-3-Clause, confirmed license), not `SKSE_HTTP` —
  dependencies confirmed clean: SKSE64, Address Library for SKSE
  Plugins, powerofthree's Papyrus Extender (MIT). ~~New action item this
  research surfaced, not yet resolved: before any other
  `adapters/skyrim/` work, run a Stage-0 spike confirming an in-process
  WebSocket server bound to `127.0.0.1` inside the Proton prefix is
  reachable from a native-Linux Python process~~ **Resolved
  2026-08-25, empirically, in production.** ChronicleBridge (the actual
  shipped plugin, `adapters/skyrim/ChronicleBridge/`) has been sending
  live outbound HTTP POSTs from inside the Proton prefix to a listener
  bound on `127.0.0.1:8765` on the native Linux host at ~1Hz during a
  real Whiterun play session — confirmed via the listener's own access
  log (`204` responses) and real named-NPC data landing in
  `adapters/skyrim/listener/whiterun-positions.json` (Idolaf
  Battle-Born, Saffir, Carlotta Valentia, Amren, Adrianne Avenicci, and
  more). **Correction to this note's original prediction:** the shipped
  transport is plain fire-and-forget HTTP POST (see
  `adapters/skyrim/contracts/chronicle-bridge.openapi.yaml`), not
  IXWebSocket — simpler than what this note anticipated, and it's what
  actually got built for the v0.2 first slice
  (`docs/design/chronicle-bridge-spatial-streamer.md`). The Stage-0
  unknown this note flagged as highest-risk is closed.

- **Check whether Mutagen / xEdit's Info NPC Extractor (already the
  recommended NPC data ingestion path, `docs/research/01-skyrim-modding-substrate.md`)
  also cleanly surfaces AI-package/schedule data and cell/worldspace
  coordinates, not just names/bios.** The dashboard's map view and the
  math tier's encounter sampling (`docs/architecture.md`) both need NPC
  location-over-time data, and nobody's verified the ingestion toolchain
  covers that case. A v0.2+/`adapters/skyrim/`-side concern — doesn't
  block current headless work, but worth a quick targeted check before
  the map view or encounter sampling gets built for real.
