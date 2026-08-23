# Assets, Data & Prior Art for a Whiterun Social-Simulation Debug Dashboard

## TL;DR
- **Best clean map backdrop:** No perfectly-licensed, production-ready *vector* top-down of Whiterun city exists. The two strongest options are (a) the UESP Skyrim gamemap tiles, which use a raw game-unit coordinate system and whose marker data is CC-BY-SA 2.5, and (b) Mirhayasu's hand-drawn Whiterun map on DeviantArt — attractive but **CC BY-NC-ND (non-commercial, no-derivatives), so internal-use only**. For a real-spatial-layout backdrop you fully control, self-capture Whiterun's local map in the Creation Kit.
- **Best coordinate data path:** Don't re-extract from scratch. Use `thallada/skyrim-cell-dump` (**MIT**) to dump CELL X/Y by worldspace, or Mutagen / an xEdit script for full REFR X/Y/Z. Critically, Whiterun city is its **own worldspace** (`WhiterunWorld`, form ID `0x0001A26F`, parent = Tamriel), so render NPCs against WhiterunWorld's local origin — not Tamriel's exterior cell (4, −4).
- **Strongest prior art:** SkyrimNet already ships a React web dashboard (~30 pages) showing live NPC state/location/memory; Stanford's Generative Agents ("Smallville," **MIT**) is the canonical top-down agent-society replay (Django server + Phaser + Tiled). These two are the projects to study and potentially consume directly.

## Key Findings
1. **No permissively-licensed SVG/vector top-down of Whiterun city is known to exist.** The cleanest reusable art is either UESP's tile system (Bethesda-derived imagery, CC-BY-SA data) or fan cartography under restrictive NC-ND licenses. Genuine Skyrim vector art on Nexus exists only for hold *crests/symbols*, not city layouts.
2. **The worldspace-to-map transform you need is simple and well-documented:** Skyrim uses raw game units, 4096 units per cell, and the UESP web map maps game units linearly to map coordinates (no scaling correction is needed for Skyrim, unlike Oblivion). You can calibrate your own affine transform from two known reference points.
3. **Whiterun city is a separate worldspace,** so a city dashboard must render against WhiterunWorld's local frame. Its exact local cell bounds are not published — but you can extract them yourself by filtering `Skyrim.esm` cells by the WhiterunWorld form ID.
4. **Extracted-coordinate tooling is mature and permissively licensed:** skyrim-cell-dump (MIT), Mutagen (C#), esplugin (GPL), plus xEdit scripting. Live-position access is available via SKSE/Papyrus `GetPos` or SkyrimNet's modder API.
5. **Prior art for external NPC visualization is rich:** SkyrimNet, Mantella, CHIM/Herika, and IntelEngine all provide live in-game/web dashboards; academic agent-society visualizers (Generative Agents, Project Sid) provide the exact "god-view" rendering patterns the user describes.

## Details

### Section 1 — Existing top-down / interactive maps of Whiterun

**UESP Skyrim Gamemap (maps.uesp.net / gamemap.uesp.net)**
- Link: https://gamemap.uesp.net/sr/ · source: https://github.com/uesp/uesp-gamemap
- Format: Raster map tiles (Leaflet/Google-Maps-style, 256×256 tiles), rendered from Creation Kit top-down orthographic captures; interactive web app (Svelte + a modified Leaflet). **Not vector.**
- Coordinates: **YES** — the key advantage. Markers use raw Skyrim game-unit coordinates directly; per UESP's own developer notes, "all of their coordinates are directly taken from the game data" (example marker coords are full game units such as −70507 / 119408).
- License: Wiki content (marker data, text) is **Creative Commons Attribution-ShareAlike 2.5** — confirmed on UESP's own licensing page (en.uesp.net/wiki/MediaWiki:Licenses: "All content is available under the terms of the Attribution-ShareAlike 2.5 License"). The older map engine code is GPL v2. The tile *imagery* is derived from Bethesda game assets (CK render screenshots), so it carries Bethesda IP — fine for personal/internal use, risky for public redistribution.
- Maintenance: **Actively maintained** (gamemap repo has 1,500+ commits; the wiki maps page was last edited 22 July 2025).
- Note: UESP's Whiterun view is the Tamriel-worldspace exterior; interior city detail is provided via separate local maps.

**UESP / Elder Scrolls Fandom local city maps of Whiterun**
- Link: https://en.uesp.net/wiki/Skyrim:Whiterun (and the Fandom wiki equivalent)
- Format: Raster (JPG, from CK-exported DDS) top-down local maps generated via **World → Create Local Maps** in the Creation Kit. Clean top-down, but screenshot-style with perspective/lighting baked in.
- Coordinates: Partial — UESP documents the capture method and coordinate system, but the images themselves are not coordinate-registered overlays.
- License: UESP content CC-BY-SA 2.5; Fandom content CC-BY-SA 3.0. Underlying imagery is Bethesda-derived.
- Maintenance: Stable.

**Mirhayasu — hand-drawn Whiterun maps (DeviantArt)**
- Links: https://www.deviantart.com/mirhayasu/art/Skyrim-Whiterun-Map-872921889 · https://www.deviantart.com/mirhayasu/art/Sykrim-Whiterun-art-Map-906688357
- Format: High-res raster digital paintings (e.g., 4000×5000 px, ~1.5 MB). Attractive, stylized, artistic top-down-ish layout — arguably the best-looking Whiterun "map" art available.
- Coordinates: NO.
- License: **RESTRICTIVE — Creative Commons Attribution-NonCommercial-NoDerivatives 3.0 (CC BY-NC-ND).** Usable as an internal/personal backdrop with attribution, but you may **not** modify it, may **not** distribute derivatives, and may **not** use it commercially. Flag clearly.
- Maintenance: Static art (2021–2022). (Note: a fan, jlasercreations, made a laser-cut derivative — done with the artist's involvement, not a license grant to others.)

**A Quality World Map (Nexus, IcePenguin)**
- Link: https://www.nexusmods.com/skyrimspecialedition/mods/5804 · original: https://www.nexusmods.com/skyrim/mods/4929
- Format: Raster paper-style *world* map textures (all of Skyrim, not a Whiterun city map), including a flat "paper" variant with hand-drawn roads.
- Coordinates: NO (province scale, not city).
- License: Nexus mod; "upload permission: not allowed to upload to other sites." Restrictive for redistribution. Province-scale, so not directly a Whiterun city backdrop anyway.
- Maintenance: Long-standing, stable.

**Hold Capital Symbol Vectors — SVG (Nexus)**
- Link: https://www.nexusmods.com/skyrim/mods/68479
- Format: **Genuine SVG + high-res PNG** vector artwork of the nine hold-capital heraldic symbols (Whiterun included). This is the closest thing to permissively-licensed Skyrim vector art found.
- Coordinates: NO — heraldic emblems, not city layouts. Useful as **UI iconography** (a Whiterun crest in your dashboard chrome), not as a map.
- License: **Permissive** — author states "Feel free to use these graphics in your work. You don't have to credit me, but it would be nice." Re-uploading elsewhere requires credit + link back.
- Maintenance: Static.

**MapGenie: Skyrim · gamemapscout · skyrimmap.ru · IGN interactive maps**
- Link: https://mapgenie.io/skyrim (and others)
- Format: Interactive raster web maps with location markers.
- Coordinates: Internal to their systems; not exposed as reusable data.
- License: **Proprietary / all-rights-reserved** (MapGenie is a commercial product). Not reusable — flag as restrictive.
- Maintenance: MapGenie actively maintained.

**DeviantArt / Pinterest fan & D&D battlemaps** (e.g., LostTrailsMaps top-down city packs, various Whiterun battlemaps)
- Format: Raster.
- Coordinates: NO.
- License: Varies; generally all-rights-reserved or Patreon-gated. Treat as restrictive unless the artist states otherwise.

### Section 2 — Datasets / tools that already extracted real in-game coordinates

**thallada/skyrim-cell-dump (RECOMMENDED starting point)**
- Link: https://github.com/thallada/skyrim-cell-dump · Python bindings: https://github.com/thallada/skyrim-cell-dump-py · https://crates.io/crates/skyrim-cell-dump
- Format: Rust library + CLI; outputs **JSON or text** of every CELL's form ID, X/Y cell coordinates, worldspace form ID, and persistent flag.
- Coordinates: **YES** — cell X/Y plus worldspace association. Its README example explicitly emits per-cell `world_form_id` (60 = Tamriel), so **filtering `Skyrim.esm` cells by `world_form_id = 0x1A26F` yields the WhiterunWorld grid directly** — the fastest way to get Whiterun's city cell bounds. (Cell-level, not per-REFR sub-cell position.)
- License: **MIT** — verified in the repo's `Cargo.toml` (`license = "MIT"`) and on crates.io.
- Maintenance: Stable; also feeds thallada's `modmapper`.

**thallada/modmapper + modmapper-web (reference implementation)**
- Link: https://github.com/thallada/modmapper · https://github.com/thallada/modmapper-web · live: modmapper.com
- Format: Rust backend scraping Nexus plugins → DB of CELL edits; Next.js + Mapbox frontend rendering cells on a Skyrim map (with WebAssembly build of skyrim-cell-dump).
- Coordinates: YES (cell grid over a Skyrim map).
- License: MIT-family (verify in repo).
- Value: A **working, open example of exactly the "render Skyrim game coordinates on a web map" problem** — study its game-unit→web-map projection.
- Maintenance: Active.

**Mutagen (Noggog)**
- Format: .NET/C# framework for reading/writing Bethesda plugins with a high-level, xEdit-like API; can enumerate PLACED_OBJECT (REFR) records with full Position (X/Y/Z) and Rotation.
- Coordinates: **YES — full REFR X/Y/Z**, the best route to actual NPC/object placement rather than just cells.
- License: Permissive open source (GPL/MIT-family — verify LICENSE).
- Maintenance: Very active, widely used in modern tooling.

**xEdit / SSEEdit scripting**
- Link: https://github.com/TES5Edit/TES5Edit
- Format: Pascal scripts run inside xEdit; iterate REFR/ACHR records and export the X/Y/Z DATA fields to CSV.
- Coordinates: YES.
- License: Open source (xEdit/MPL-style).
- Maintenance: Active.

**Other parsers (context):** esplugin (Ortham, GPL) and its predecessor libespm; esper and esplib (matortheeternal / BadDog, Python); SkyrimLib (tstavrianos); ESMSharp (MIT). Most target load-order/record inspection rather than position export — **skyrim-cell-dump and Mutagen are the two most directly useful** for coordinates.

**Live position access (runtime)**
- Papyrus `GetPositionX/Y/Z` and the console `GetPos` return game-unit coordinates for any actor.
- SKSE plugins expose live actor positions; SkyrimNet's IntelEngine specifically does "native position polling at engine speed" and JSON state serialization. If your dashboard is a companion to a running game, this is a **live feed** rather than a static dump.

**The coordinate transform (practical core — from primary CK/UESP sources):**
- **1 exterior cell = 4096 × 4096 game units** (= 192 ft = 64 yards ≈ 58.52 m per side). Source: ck.uesp.net/wiki/Exterior_Cells and ck.uesp.net/wiki/Unit.
- **`cellX = floor(gameX / 4096)`, `cellY = floor(gameY / 4096)`** (rounds toward −∞ for negatives).
- **Cell center in game units:** `gameX = cellX*4096 + 2048`, `gameY = cellY*4096 + 2048` — confirmed by UESP's own console map-capture procedure (`player.setpos x [CellX]*4096+2048`).
- **Unit conversions** (ck.uesp.net/wiki/Unit): 1 unit = 0.5625 in = 1.42875 cm; 128 units = 6 ft; 64 units = 1 yard; ~70 units ≈ 1 m (exactly ~69.99 units/m).
- **UESP's web map uses raw game units mapped linearly to map coordinates** — Skyrim does **not** need Oblivion's "241/256" tile-crop correction. So for your own map you can fit a simple affine transform (uniform scale + offset) from two known reference markers. UESP's gamemap DB stores this as `posLeft/posTop/posRight/posBottom` game-unit bounds, but the specific numeric constants for the Skyrim ('sr') world are held server-side (served via `getworlds.php`) and are **not published** in the GitHub repo or wiki — so calibrate empirically.
- **Whiterun exterior in Tamriel ≈ cell (4, −4)** (from UESP's `cow tamriel` list); derived cell-center ≈ game units **(18432, −14336)**. A published nearby anchor useful for calibration: the **Riverwood map marker at game units (21941, −44792)**.

**Whiterun worldspace (critical architectural fact):**
- The city of Whiterun is its **own worldspace**: editor ID **`WhiterunWorld`**, form ID **`0x0001A26F`**, with **Tamriel as its parent worldspace**, and its own local coordinate origin. This is corroborated by the Unofficial Skyrim Special Edition Patch changelog, which lists `WRLD:0001A26F:WhiterunWorld` alongside the other city worldspaces (WindhelmWorld `0001691D`, RiftenWorld `00016BB4`, MarkarthWorld `00016D71`, SolitudeWorld `00037EDF`).
- Consequence: NPCs *inside* the city report positions in WhiterunWorld's frame, so a Whiterun-city dashboard must render against WhiterunWorld coordinates — **not** the Tamriel 4,−4 exterior cell. WhiterunWorld's exact local cell bounds aren't tabulated on UESP/CK wikis, so **extract them yourself** by filtering skyrim-cell-dump output on `world_form_id = 0x1A26F` to get the min/max X/Y and thus your map extent.

### Section 3 — Prior art for external / companion NPC visualization tools

**SkyrimNet (MOST RELEVANT — a working Skyrim NPC "god-view" debug dashboard)**
- Link: https://github.com/MinLL/SkyrimNet-GamePlugin · docs: https://goncalo22.github.io/SkyrimNet-GamePlugin/
- What it is: An LLM-driven NPC AI framework running in-process as a native DLL, with a built-in **web dashboard at localhost:8080** described in its own docs as "a clean, real-time command center for monitoring the entire AI simulation." It shows server status, GameMaster state, **nearby NPCs, a live event stream, recent LLM requests** (with timing/tokens/outputs), thread-pool stats, and **pinned characters with quick-teleport**; the Characters page shows live actor data next to editable bios. It is a **React-based control panel with roughly thirty pages**.
- Relevance: The closest existing "debug dashboard for Skyrim NPC AI." It exposes live NPC state/location/memory via a documented modder API — study its architecture and consider consuming its API directly.
- License: Free/open passion project by developer "Min" (verify the code LICENSE on the repo).
- Maintenance: **Very active** (frequent beta releases; recent work on dashboards, filters, event rendering).
- Ecosystem: **IntelEngine** (galanx — NPC autonomy, natural-language scheduling, native position polling, cell/door analysis, JSON state serialization; https://github.com/galanx/IntelEngine-GamePlugin); **SeverActions** (native follower framework with rapport/trust/loyalty/mood); **zevck/SkyrimNet-Prisma-Dashboard** (brings the web dashboard in-game as an overlay — now being deprecated in favor of the native dashboard).

**Mantella**
- Link: https://github.com/art-from-the-machine/Mantella · https://art-from-the-machine.github.io/Mantella/
- What it is: A Python external app (Whisper STT + LLM + xVASynth/XTTS TTS) giving every NPC voice conversation, memory, world awareness, vision, and 20+ actions including travel-to-location. Runs as a background server; NPCs can start conversations with each other and join group conversations.
- Relevance: Mature external companion architecture with per-NPC state; a candidate data feed. No 2D map view of its own.
- License: Code open source (uses Elder Scrolls Fandom wiki character content under CC BY-SA; verify code LICENSE).
- Maintenance: Very active (Skyrim SE/AE and Fallout 4).

**CHIM / Herika (The Herika Project)**
- Link: https://www.nexusmods.com/skyrimspecialedition/mods/126330 (CHIM)
- What it is: An AI-NPC framework with a **web-server UI**, "Soulgaze" vision, an **MCP server for debugging**, memory/mood systems, and PrismaUI in-game panels. Herika (originally a ChatGPT-driven Breton follower in Whiterun) grew into this server stack.
- Relevance: Another web-dashboard-bearing AI-NPC framework; the MCP debug server is notable for programmatic introspection.
- License: Nexus/mixed. Maintenance: active.

**Academic / agent-society visualizers (the rendering patterns to borrow)**
- **Stanford Generative Agents ("Smallville") — the best template for a top-down god-view dashboard.** Link: https://github.com/joonspk-research/generative_agents · paper: arXiv:2304.03442. It renders 25 agents on a top-down 2D pixel-art town using an environment map + collision map; a server maintains a **JSON data structure holding each agent's current location and action**, and there is a browser **replay** you navigate with arrow keys. Per the repo README, the environment is implemented as a **Django project** (served at http://localhost:8000/, frontend under `environment/frontend_server`), the sandbox game is built with the **Phaser** web framework, and maps are edited in the **Tiled** map editor. This is exactly the "watch the Sims from a top-down god-view" model the user describes. The successor repo `joonspk-research/genagents` ("Generative Agent Simulations of 1,000 People") is explicitly **MIT-licensed**.
- **Project Sid (Altera).** Link: https://github.com/altera-al/project-sid · paper: arXiv:2411.00114. 1000+ autonomous agents in Minecraft using the PIANO architecture, with emergent economy, culture, **religion/meme spread**, and government. The repo is the technical report (not full code), but it is the best reference for **large-scale belief/rumor-propagation visualization** — directly analogous to the user's NPC belief/rumor engine.

**Skyrim NPC-tracking mods (coordinate-access patterns, not full dashboards)**
- **Skyrim Radar Mod (SE)** — https://www.nexusmods.com/skyrimspecialedition/mods/23533 — HUD radar of nearby enemies/followers/neutral NPCs relative to the player; demonstrates live relative-position access via SKSE/SkyUI.
- **Where Are You** (SKSE, SE/AE) — https://www.nexusmods.com/skyrimspecialedition/mods/76063 — lookup NPCs by name, view stats/inventory, teleport, add tracking markers.
- **Flute Finder** — GPS-style tracking of 150+ NPCs via quest markers.
- **Follower Map Markers · CS Tag & Track NPCs** — quest-marker-based NPC tracking.
- **epinter/WikiMap** (https://github.com/epinter/WikiMap) — C++ SKSE plugin linking in-game map markers to the online map/wiki (Steam-overlay integration pattern).
- These confirm the *access patterns* (SKSE actor-position polling; quest-marker APIs) but **none provide a clean external 2D top-down social dashboard** — that gap is what your project fills.

## Recommendations

**Stage 1 — Get a usable Whiterun backdrop now (internal use):**
1. **Self-capture Whiterun's local map in the Creation Kit** (World → Create Local Maps; render window in top view "T", non-perspective "0", cell borders on "B"), following UESP's documented procedure. This gives you a coordinate-registered, correctly-scaled, top-down image you fully control (still Bethesda-derived IP, so keep it internal).
2. Alternatively, use UESP gamemap tiles for the exterior and treat Mirhayasu's art as an *optional* stylized skin — but keep Mirhayasu's CC BY-NC-ND art strictly internal (no redistribution, no modification, attribution required).
3. Use the Hold Capital Symbol SVGs (permissive) for the Whiterun crest and other UI chrome.
- **Threshold to change approach:** if you ever plan to publicly ship or redistribute the dashboard, drop all Bethesda-derived and NC-ND art and commission or generate **original** top-down Whiterun art traced from your own extracted coordinates.

**Stage 2 — Build the coordinate layer:**
1. Run `skyrim-cell-dump` (MIT) on `Skyrim.esm`; filter cells by `world_form_id = 0x1A26F` (WhiterunWorld) to get Whiterun's local cell grid and compute your map's min/max extent.
2. For per-NPC/per-object placement, use **Mutagen** (C#) or an **xEdit Pascal script** to export REFR/ACHR Position X/Y/Z within WhiterunWorld to CSV/JSON.
3. Establish your affine transform: pick two reference REFRs whose game-unit coords and desired pixel positions you know, then solve scale + offset. Because Skyrim maps game units linearly, a two-point fit is exact for translation + uniform scale.
4. If the dashboard is live/companion to a running game, poll positions at runtime via SKSE/Papyrus `GetPos`, or — better — consume **SkyrimNet's API** for richer NPC state (location + memory + relationships).

**Stage 3 — Borrow proven visualization architecture:**
1. Use **Stanford Generative Agents'** Django-server + JSON-agent-state + Phaser-replay model as your rendering template (MIT successor repo; purpose-built for exactly this god-view).
2. Study/consume **SkyrimNet's** dashboard + modder API for live NPC belief/relationship/location state.
- **Threshold:** if you specifically need belief/rumor-propagation views, model on **Project Sid's** meme/religion-spread tracking and Generative Agents' memory-stream inspector.

## Caveats
- **Licensing tiers:** Anything derived from Bethesda game assets (UESP tiles, CK-captured local maps, all Nexus map textures) is safe for personal/internal use but carries Bethesda IP for redistribution. **Mirhayasu's maps are CC BY-NC-ND** (no commercial use, no derivatives). **MapGenie is proprietary.** Only `skyrim-cell-dump` (MIT), the Hold Capital SVGs (permissive with credit), and UESP wiki *marker data* (CC-BY-SA 2.5) are cleanly reusable, each with its own attribution terms.
- **No perfect off-the-shelf asset exists:** there is no known permissively-licensed vector top-down of Whiterun *city*. The realistic path is self-capture + your own coordinate overlay.
- **Verify code licenses at time of use:** Mutagen, Mantella, SkyrimNet, and the original `generative_agents` repo are flagged here as "MIT/GPL-family — verify"; confirm the LICENSE file before redistributing. (skyrim-cell-dump = MIT and the `genagents` successor = MIT are confirmed.)
- **WhiterunWorld local bounds are not published** — extract them yourself; do not assume Tamriel 4,−4 coordinates apply inside the city.
- **Watch for aggregator/AI-generated repos:** some SkyrimNet-adjacent GitHub bundles (e.g., "Skyrim-AI-Revolution-Ultimate-NPC-Mod") appear to be marketing/aggregator packages; prefer the canonical upstreams (`MinLL/SkyrimNet-GamePlugin`, `art-from-the-machine/Mantella`).
- **The specific numeric UESP map constants** (`posLeft/posTop/posRight/posBottom` for Skyrim) are server-side and unpublished; this is why the recommendation is to calibrate your own transform from known reference points rather than reuse UESP's exact values.