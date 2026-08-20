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
