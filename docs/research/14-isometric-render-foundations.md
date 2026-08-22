---
date: 2026-08-22
sources:
  - "session web research, 2026-08-22 (single-agent pass over open-source Skyrim/NIF rendering foundations; licenses verified against repos, not READMEs)"
topic: "2.5D / isometric render foundations for the Whiterun dashboard — can we render real Skyrim geometry without building a renderer from scratch?"
status: filed — fo76utils smoke test PASSED 2026-08-22 (TES5 statics confirmed; see Verification section)
---

# Isometric render foundations (option 3 feasibility)

Answers the user's question: a Sims-like 2.5D view of Whiterun from REAL
Skyrim geometry, without building a renderer from scratch, distributable
without shipping Bethesda assets ("ship the generator, not the image" —
all candidates read the user's own installed game files). Report 12's 2D
backdrop plan is unchanged; whichever 3D path wins simply becomes the
tile generator feeding the same dashboard.

## Findings

- **[BUILD-ON, pending verification] fo76utils is the lowest-effort candidate.** MIT (LICENSE file verified), Linux CI binaries, mature (last push 2025-03-12). CLI suite: `render` renders a world/cell/object straight from ESM+BSA with full camera transform control (`-view SCALE RX RY RZ …` — any isometric angle) and debug render modes (form-ID-color, depth, normals); `terrain` has an explicit `-iso` mode; **`markers` plots icons at REFR coordinates onto a rendered map — the NPC-token-overlay precedent, already built**. Open question: TES5 *statics* (buildings/walls) support is unstated in its docs (FO4/76 full; TES4/FO3/FNV terrain-only). One command answers it — smoke test in progress against the downloaded 1.6.1170 depot files (see below).
- **[BUILD-ON] ByroRedux is the verified-capable foundation** (matiaszanolli/ByroRedux). Rust+Vulkan clean-room Creation Engine rebuild; Linux is the primary target. Demonstrated, benched, CI-gated: 100% clean parse of all 18,862 Skyrim SE NIFs, interior cells render end-to-end, exterior smoke test walks out the Bannered Mare door into WhiterunWorld cell (6,−2) with terrain splatting + placed REFRs. Gaps: SpeedTree trees, water (tracked upstream). Headless `--list-cells` catalog mode + TCP debug CLI (`byro-dbg`) with screenshot capture — natural injection point for tile baking and later sim-driven NPC tokens. License: MIT declared in Cargo.toml/README, **no LICENSE file** (file an upstream issue before depending). Single-author, extremely active (pushed 2026-08-22); MIT makes forking safe. Cost: heavier dependency, needs a Vulkan GPU at bake time. Estimate 1–3 weeks.
- **[BUILD-ON] Custom web pipeline** (bsa-rs `ba2` crate [0BSD] + byroredux-nif/nifly → glTF → three.js ortho camera) if the dashboard must be pure browser. Most control, most work (4–8 weeks). **Scene assembly (REFR→mesh placement) is always custom code — no library does it** (ByroRedux's cell_loader and fo76utils' render contain it; nifly/PyNifly/Mutagen deliberately stop at single meshes / raw records).
- **[RISK] Dead ends confirmed:** PyNifly (GPL-3.0, **Windows-only** — ships a Windows NiflyDLL); blender_niftools_addon (BSD but **cannot import SSE NIFs at all**, dormant since 2024); xLODGen (terrain LOD textures only, no buildings; closed freeware, Wine-only); OpenSkyrim (Bevy-based, MIT/Apache, but created 2026-08-06 and unproven against real game data — watch, don't build on); no working web-based NIF loader exists (closest: fo76utils' Nifskope fork, BSD, has glTF export for SSE NIFs → NIF→glTF→three.js is a viable bridge).
- **[BUILD-ON] Supporting pieces are solved on Linux:** BSA reading — `ba2` crate (0BSD, BSA v103/104/105 + BA2); DDS decode — fo76utils' `bcdecode` (MIT) or `image-dds` crate (MIT/Apache).
- **[DESIGN-INPUT] The 1.6.1170 depot downloads double as the render corpus.** `Skyrim.esm` + Textures BSAs live in `depot_489832/Data/`, Meshes BSAs in `depot_489831/Data/` — a symlinked staging dir gives any of these tools a complete, pin-correct game-data view **without touching the live 1.7.99 install** (the pending backup decision from HANDOFF-2026-08-21-1836 is not on this path's critical chain).

## License table (verified against repos, not READMEs)

| Project | License (verified via) | Last push | Linux |
|---|---|---|---|
| fo76utils | MIT — LICENSE file | 2025-03-12 | yes (CI binaries) |
| ByroRedux | MIT — Cargo.toml only, no LICENSE file ⚠ | 2026-08-22 | primary target |
| nifly | GPL-3.0 — LICENSE file | 2026-07-29 | yes |
| PyNifly | GPL-3.0 — LICENSE file | 2026-08-21 | **no (Windows only)** |
| blender_niftools_addon | BSD-3-Clause — LICENSE.rst | 2024-06-16 (stale) | yes, but no SSE support |
| bsa-rs (`ba2` crate) | 0BSD — Cargo.toml | 2024-12-22 | yes |
| image-dds | MIT OR Apache-2.0 — Cargo.toml | 2025-11-11 | yes |
| OpenSkyrim | MIT/Apache-2.0 | 2026-08-20 (created 2026-08-06) | claimed |

## Decision rule

1. If fo76utils renders WhiterunWorld statics → it becomes the bake tool (~1–2 weeks to productionize: camera pose, tile stitching, `markers` overlay).
2. If terrain-only → ByroRedux (~1–3 weeks; file the LICENSE issue upstream in parallel).
3. Web-native-only requirement → custom glTF pipeline (4–8 weeks), last resort.

## Verification (2026-08-22, this machine) — fo76utils WINS

Built from source (scons in a throwaway venv, g++ 11, no system installs)
and run against the symlinked 1.6.1170 depot staging dir:

- **Full Tamriel** (its own documented tes5 example): 18,876 terrain tiles
  + 243,298 objects + 17,688 water/transparent in **11 seconds** —
  terrain, statics, and textures all confirmed working for TES5.
- **WhiterunWorld top-down** (`-w 0x0001A26F`): the whole walled city —
  walls, Dragonsreach, Jorrvaskr, Gildergreen, market, gate — 1,184
  objects, in seconds. Working invocation:
  ```
  ./render <stage>/Skyrim.esm out.dds 2048 2048 <stage> \
    -w 0x0001A26F -deftxt 0x00000C16 -env textures/cubemaps/chrome_e.dds \
    -light 2.6 70.5288 135 -ltxtres 256 -rq 10 -view 0.1 180 0 0 -2458 -614 8192
  ```
- **Isometric angle** (`-view 0.15 145 0 0 …`): works — buildings show
  depth/wall faces. Framing needs calibration, not new code.

Gotchas learned (all bake-pipeline concerns, not feasibility):

- **No automatic framing**: `-view` is fully manual. Transform convention
  (from rndrmain.cpp): `px = s·x + offsX + W/2`, `py = −s·y + offsY + H/2`
  for the top-down RX=180 case. WhiterunWorld city cells span grid
  X 4..7, Y −4..0 (WhiterunOrigin = 0x0001A27F at (4,−2), per esmdump),
  so city center ≈ world units (24576, −6144) → `offsX = −2458`,
  `offsY = −614` at scale 0.1.
- The worldspace has essentially **no LAND terrain of its own** (ground
  is mesh pavement) — the surrounding void renders as flat default green.
  For the dashboard backdrop that's fine (city content is what matters).
- One building rendered black (a texture/effect-mesh miss) and default
  mip levels are soft — tune `-mip`/`-lmip`/`-hqm` during
  productionizing. `markers` overlay not yet exercised.
- Renders are Bethesda-derived: internal tooling only, never committed or
  redistributed (report 12's rule). The distributable artifact is the
  bake script + the user's own game files.
