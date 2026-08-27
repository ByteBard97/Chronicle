# adapters/skyrim

The SKSE/Papyrus seam: everything that translates between Skyrim's game
state and Chronicle's event log. This is the only place in the repo allowed
to know Skyrim exists.

Two directions of traffic:
- **In**: game events (deaths, crimes, cell attach/load, dialogue, quest
  stages, item transfers) arrive here and get turned into `chronicle.events`
  appends. This direction is built and landed (see slices below).
- **Out**: derived Chronicle state (beliefs, rumors, reputation) is meant
  to render back into the game — as AI-package overrides on cell
  hydration, and as prompt context injected into Mantella/CHIM-style
  dialogue mods. **This direction does not exist yet.** Every write path
  below is compiled and Python-tested but has no confirmed visible effect
  in a running game — see `docs/design/next-phases-2026-08.md` for the
  current plan to close this gap.

Isolating this seam is what keeps the substrate choice (see
`docs/decisions/0003-substrate-choice.md`) reversible: if we ever prototype
against a different engine, only this directory changes.

## What's here

- **`ChronicleBridge/`** — the SKSE plugin (C++, CommonLibSSE-NG).
  Status as of 2026-08-27: **7 slices landed**, whole tree builds clean,
  and the compiled DLL + a real patched ESP are deployed into a live dev
  install (`~/Games/ChronicleDev`). None of these have been verified
  against a running game yet — that's the open next step, not a
  hypothetical future one.
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

  Two gaps this slice list doesn't close: the named-cast map
  (`IdentityMap.cpp`'s `kNamedCast`) covers 19 of Whiterun's 28
  live-captured NPCs (grown from 1, `2f27cc8`) — real coverage, not
  the full cast, so some landed rules still can't apply to every NPC
  the player might meet; and none of this is visible
  in-game until someone launches Skyrim against the ChronicleDev
  deployment and works through `docs/design/
  chronicle-bridge-verification-runbook.md`.
- **`contracts/`** — the OpenAPI wire contract(s) shared between the
  plugin and Chronicle-side listeners. Single source of truth for payload
  shapes; both sides are written/generated to match it, never
  independently hand-synced.
- **`listener/`** — the Python-side counterpart to `ChronicleBridge/`'s
  outbound traffic. Deliberately not part of `chronicle/` — this is
  Skyrim-adapter plumbing (receiving/validating the wire payload), not
  simulation logic.
