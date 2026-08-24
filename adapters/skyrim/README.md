# adapters/skyrim

The SKSE/Papyrus seam: everything that translates between Skyrim's game
state and Chronicle's event log. This is the only place in the repo allowed
to know Skyrim exists.

Two directions of traffic:
- **In**: game events (deaths, crimes, cell attach/load, dialogue, quest
  stages, item transfers) arrive here and get turned into `chronicle.events`
  appends.
- **Out**: derived Chronicle state (beliefs, rumors, reputation) gets
  rendered back into the game — as AI-package overrides on cell hydration,
  and as prompt context injected into Mantella/CHIM-style dialogue mods.

Isolating this seam is what keeps the substrate choice (see
`docs/decisions/0003-substrate-choice.md`) reversible: if we ever prototype
against a different engine, only this directory changes.

## What's here

- **`ChronicleBridge/`** — the SKSE plugin (C++, CommonLibSSE-NG). First
  slice only so far: live NPC position streaming (see
  `docs/design/chronicle-bridge-spatial-streamer.md`), not the full "In"/
  "Out" traffic described above yet.
- **`contracts/`** — the OpenAPI wire contract(s) shared between the
  plugin and Chronicle-side listeners. Single source of truth for payload
  shapes; both sides are written/generated to match it, never
  independently hand-synced.
- **`listener/`** — the Python-side counterpart to `ChronicleBridge/`'s
  outbound traffic. Deliberately not part of `chronicle/` — this is
  Skyrim-adapter plumbing (receiving/validating the wire payload), not
  simulation logic.
