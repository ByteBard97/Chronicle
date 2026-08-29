# adapters/skyrim

The SKSE/Papyrus seam: everything that translates between Skyrim's game
state and Chronicle's event log. This is the only place in the repo allowed
to know Skyrim exists.

Two directions of traffic:
- **In**: game events (deaths, crimes, cell attach/load, dialogue, quest
  stages, item transfers) arrive here and get turned into `chronicle.events`
  appends. This direction is built and landed (see slices below).
- **Out**: derived Chronicle state (beliefs, rumors, reputation) renders
  back into the game — as AI-package overrides on cell hydration, and as
  prompt context injected into Mantella/CHIM-style dialogue mods. **Every
  write path below is now confirmed writing correctly against a real,
  running game** (14/16 checks in `adapters/skyrim/livetest/`, see the
  live-test harness) — what's not yet confirmed is whether the resulting
  state change is something a player would actually notice on screen;
  see `docs/design/next-phases-2026-08.md` for the current plan to close
  that gap.

Isolating this seam is what keeps the substrate choice (see
`docs/decisions/0003-substrate-choice.md`) reversible: if we ever prototype
against a different engine, only this directory changes.

## What's here

- **`ChronicleBridge/`** — the SKSE plugin (C++, CommonLibSSE-NG).
  Status as of 2026-08-29: **7 slices landed**, whole tree builds clean,
  and the compiled DLL + a real patched ESP deploy into a live game
  install. **All 7 have now been exercised against a real, running
  game** via an automated pytest harness over DevBench
  (`adapters/skyrim/livetest/`) — 14 of 16 checks pass; the 2 that don't
  are both the same save/load-persistence bug, not a per-slice failure
  (see `docs/design/simple-modlist-milestone.md`).
  1. Live NPC position streaming (`docs/design/
     chronicle-bridge-spatial-streamer.md`) — the original "In" slice.
  2. Cell-hydration AI-package overrides.
  3. Avoidance (real FormID pairs patched into `AvoidanceGlobals.cpp`,
     171/171 verified via a real patcher run).
  4. Vendor-markup price hook (`VendorPriceHook.{h,cpp}`, first
     vtable/UI hook — live-game caveats noted in
     `docs/design/next-phases-2026-08.md`).
  5. Crime-witness cascade (Python side only; C++ event sink is a
     separately-scoped open research question, see `docs/research/
     29-crime-witness-event-extraction.md` and `30-crime-witness-
     prior-art-spike.md`).
  6. Diegetic evidence (`docs/design/chronicle-bridge-diegetic-
     evidence-out.md`) — belief/evidence state spawns as a real
     authored `MiscItem` in the world, gated on `BeliefInstance.
     confidence`.
  7. `EvidencePoller.{h,cpp}` — the C++ consumer for diegetic evidence,
     resolving NPCs via `IdentityMap` and calling `PlaceObjectAtMe`.

  One gap this slice list doesn't close: the named-cast map
  (`IdentityMap.cpp`'s `kNamedCast`) covers 19 of Whiterun's 28
  live-captured NPCs (grown from 1, `2f27cc8`) — real coverage, not
  the full cast, so some landed rules still can't apply to every NPC
  the player might meet. Separately: state-level verification against
  a live game is done (14/16 checks, see `adapters/skyrim/livetest/`),
  but that doesn't yet mean the effect is *player-visible* on screen —
  that's the next thing to confirm.
- **`contracts/`** — the OpenAPI wire contract(s) shared between the
  plugin and Chronicle-side listeners. Single source of truth for payload
  shapes; both sides are written/generated to match it, never
  independently hand-synced.
- **`listener/`** — the Python-side counterpart to `ChronicleBridge/`'s
  outbound traffic. Deliberately not part of `chronicle/` — this is
  Skyrim-adapter plumbing (receiving/validating the wire payload), not
  simulation logic.
