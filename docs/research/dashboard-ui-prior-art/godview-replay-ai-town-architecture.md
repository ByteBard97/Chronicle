> Filed 2026-08-22 in `docs/research/dashboard-ui-prior-art/` — external
> research, not code-verified. Covers similar ground to the two broad
> surveys in this folder, but its standout, distinguishing contribution is
> a detailed architecture writeup of **a16z's AI Town**
> (`HistoricalObject`/`useHistoricalTime`: quantize → delta-encode →
> optional RLE → varint, replayed client-side at ~1 Hz persistence with
> smooth playback) as the closest existing template for Chronicle's
> "every view renders as of tick T" requirement, plus concrete
> SVG-vs-Canvas-vs-WebGL rendering benchmarks. Feeds the dashboard design
> work, not any accepted ADR.

# Prior Art for a Headless Social-Simulation Debugging Dashboard

## TL;DR
- The interaction grammar you need is already proven and largely convergent: adopt (1) a WebGL/canvas god-view (not SVG) with click-to-inspect markers, (2) a global timeline scrubber where every panel renders "as of tick T," (3) play/pause/speed transport controls, (4) a persistent per-entity inspector, and (5) event markers on the timeline. The single best architectural template for your exact "render as of tick T" requirement is **a16z's AI Town** (github.com/a16z-infra/ai-town), whose `HistoricalObject`/`useHistoricalTime` system stores per-tick numeric deltas in a compressed buffer and replays them client-side.
- The most important performance decision is renderer choice: per Scott Logic's "Rendering One Million Datapoints with D3 and WebGL," SVG "can typically handle around 1,000 datapoints" and Canvas "around 10,000 datapoints whilst maintaining smooth 60fps interactions"; WebGL (PixiJS/Phaser) is the proven path for hundreds-to-thousands of animated sprites — which is why AI Town, Smallville, and virtually every shipping god-view use sprite-batched WebGL, not DOM.
- The most-cited pain points to avoid: research tools (Mesa/SolaraViz, NetLogo, Smallville's replay) couple visualization to a live simulation process and have no true time-scrubber (Smallville's own README calls its replay "primarily intended for debugging purposes" with unoptimized storage); provenance/"why" is the #1 missing affordance (the RimWorld "Modern Social Tab" mod exists because the vanilla Social tab "gives you a list of names and a number beside each one. It never tells you why"); and dense per-agent overlays don't automate well ("the level of details to show… are completely dependent on the level of details a user wants," per GAMA's maintainers).

## Key Findings

### The convergent interaction grammar (adopt these)
Across ABM tools, generative-agent replays, shipped god-games, and RTS/MOBA replay systems, the same patterns recur:

1. **Click-agent → state panel/inspector.** Universal: NetLogo agent monitors, Mesa/GAMA/AnyLogic inspectors, The Sims selection, RimWorld inspect pane, SC2 "click icon → center camera on unit," AI Town "click on any character to read their inner monologue."
2. **Global timeline scrubber with draggable playhead.** Universal in RTS/MOBA/sports/video tools; notably *absent* from most ABM tools and from Smallville (which only supports "start replay at step N").
3. **Event markers on the timeline.** Per Dota2Gamers.gg's replay guide, Dota 2 lets you "navigate to kills, objectives, or team fights without scrubbing blindly"; SC2/CS2 similar.
4. **Play/pause + discrete speed multipliers.** The Sims' 1×/2×/3× + pause is the canonical "god-game" transport; Dota/SC2 replays add speed up/slow down; Smallville's demo mode takes a `<simulation-speed>` from 1 (slowest) to 5 (fastest).
5. **At-a-glance state encoding (color/bars/badges).** The Sims plumbob color = mood; need bars; RimWorld mood color-coding and third-party need bars / Pawn Badge skill icons; Dwarf Therapist name color = stress.
6. **Overview roster synchronized with the map.** The Sims/RimWorld colonist bar; Dwarf Therapist spreadsheet; SC2 production tab; clicking a roster row centers/selects on the map.
7. **Layered/toggleable overlays.** GAMA "multi-layer 2D/3D displays," SC2 observer toggles (vision, production), AnyLogic multiple displays per model.

### The single best "render as of tick T" template: AI Town
AI Town (a16z-infra, MIT-licensed, built on Convex + PixiJS) solves precisely your "every view renders as of tick T with smooth playback" problem, and its architecture is documented in `ARCHITECTURE.md` (github.com/a16z-infra/ai-town/blob/main/ARCHITECTURE.md):
- The simulation runs ~60 ticks/second (`TICK = 16`ms) but only persists once per second (`STEP_INTERVAL = 1000`ms), writing a **diff** of game state at the end of each step. The doc explains the motivation: "continuous quantities like position will only update every second. This, then, defeats the whole purpose of having high-frequency ticks: Player positions will jump around and look choppy."
- Each player's *location* ("position, orientation, and speed") is fed at the end of every tick into a **`HistoricalObject`**, which "efficiently tracks its changes over time and serializes them into a buffer that clients can use for replaying its history."
- History fields are **numeric floats only**, at most **16 fields** (`MAX_FIELDS = 16`), must be declared up-front, and are compressed through a four-stage pipeline documented in `historicalObject.ts`: **quantization → delta encoding → optional run-length encoding → varint encoding**. Internally each field is a `History` of line-segment `Sample`s (`{time, value}`), so any field can be queried at an arbitrary time T.
- The client uses a **`useHistoricalValue`** hook to decode the buffer and a **`useHistoricalTime`** hook to keep "replayed time synchronized across multiple historical buffers." The client deliberately renders server time **up to ~1.5s in the past** (`MAX_SERVER_BUFFER_AGE = 1500`ms), keeping ~250–1250ms of buffer and nudging playback rate between **0.8× and 1.2×** to keep the buffer healthy — this is what makes motion smooth despite 1 Hz persistence.
- Documented limits: game state should stay "less than a few dozen kilobytes"; "Games that require tens of thousands of objects interacting together may not be a good fit"; total input latency ≈ 1.5s (configurable down to a 250ms step "at the cost of adding more Convex function calls and database bandwidth").

**Why this matters for you:** the piecewise-linear "sample = line segment over time" model is exactly how you get any panel to answer "what was true at tick T." For discrete state (beliefs, rumors, grudges) rather than continuous position, you'd store event/interval records rather than HistoricalObject floats, but the *pattern* — persist deltas, reconstruct state at an arbitrary T on the client, keep a small in-memory working set — is the one to copy.

## Details by area

### (1) Agent-based-modeling observation UIs

**NetLogo / NetLogo Web.** The classic ABM environment: "hundreds or thousands of independent agents." Inspection is via **agent monitors** (right-click → inspect turtle/patch) and the Command Center. Documented pain points (CCL docs/wiki, NetLogo Users Group): it's JVM/heap-bound ("the lower heap size limit may affect your ability to run models with very large numbers of agents"); "There is no fixed limit… performance will become exceedingly slow if you have too many agents"; monitors with large agentsets are slow. NetLogo Web is partially compiled and slower still; the CCL team lists ongoing "Speed optimizations… around breed checks… large agentsets." There is **no time-scrubber** — you can only run forward (or use BehaviorSpace for batch runs).

**Mesa + SolaraViz (the newer Solara-based visualization).** Mesa 3 replaced its old custom JS viz with **SolaraViz**, "a pure Python, React-style web framework." It offers step/play/pause with `play_interval` (speed) and `render_interval` (how often plots redraw). Documented complaints (GitHub) are numerous and directly relevant:
  - **Performance:** the docs themselves warn "Running the model can be performance-intensive. It is strongly recommended to pause the model in the dashboard before switching pages." Mesa 3.2 added **asynchronous updates** (#2656) — "Visualization now runs in a separate thread, dramatically improving performance for complex models" — an implicit admission the prior version blocked. Users report dashboards are "very slow if you run everything above it" (Discussion #2338).
  - **Fragility/usability:** "SolaraViz Cannot Be Run Locally" (#2814); won't start unless model `__init__` uses keyword args (#2722); static histograms; repeated breaking API changes ("SolaraViz is in active development… there might be API breaking changes in minor releases").
  - **No true scrubber:** you step forward/back a step, but there is no global "as of tick T" timeline; open feature requests exist for streaming plot updates (#2255) and integrated analysis (#3265).
  - Rendering backends are **matplotlib (default) or Altair** — neither is built for thousands of live-updating agents.

**GAMA.** The most feature-rich for your use case. It provides **agent inspectors** ("follow the state of a given agent"), **agent browsers** (a sortable table of all agents of a species, savable to CSV), and **monitors** (track a GAML expression). Inspectors can be declared in-model as experiment outputs, can *highlight* an agent across all displays, edit variables live, or kill it. It offers **multi-layer 2D/3D displays** and two rendering backends: Java2D ("classical") and **OpenGL**, where "the OpenGL display… provides better performance for large scale simulation" (GAMA markets "up to millions of agents" via GIS data — a vendor claim; benchmark it). Documented limitation directly on point: a GitHub issue ("Display idea for helping agent behavior debug," #2240) requesting per-agent "at time t" overlays was effectively declined because "it cannot be easily automated: the level of details to show… are completely dependent on the level of details a user wants." GAMA is a heavyweight desktop Java/Eclipse app, not a web dashboard.

**AnyLogic.** Commercial. Inspection is via **inspection windows** (drag from palette, bind to an agent, customize a `toString`-style readout) and a runtime **developer panel** ("select agent to dive"). Animation binds shape properties (size/position/color/visibility) to model variables. It's strong on 2D/3D animation and "spying agents"/dashboards for KPIs, but it's a proprietary IDE, not a scrubber-based replay tool.

**Cross-cutting ABM critique:** none of NetLogo, Mesa, GAMA, or AnyLogic ships a **global timeline scrubber** with "every view as of tick T." They are live-stepping tools. That gap is your opportunity.

### (2) Stanford generative agents (Smallville) and successors

**Smallville / `joonspk-research/generative_agents`.** The sandbox "is built using the Phaser web game development framework, with imported visual sprites, environment and collision maps." The architecture: a Python **`reverie.py`** backend maintains a JSON world state and, at each step, writes a per-tick **`movement/{step}.json`** file; a Django **`frontend_server`** serves a Phaser town view. Replay works by pointing the browser at `http://localhost:8000/replay/<simulation-name>/<starting-time-step>/`. Documented **design and limitations** (verbatim from the repo README):
  - Replay is **debug-grade, storage-unoptimized:** "the replay function is primarily intended for debugging purposes and does not prioritize optimizing the size of the simulation folder or the visuals."
  - To demo properly you must first run **`compress_sim_storage.py`** (it consolidates the per-step movement files) and then use the `/demo/<name>/<step>/<speed>/` route, where `<simulation-speed>` runs 1 (slowest) to 5 (fastest).
  - The replay is **forward-only with a start-step parameter** — you pick a starting time-step; there is no draggable timeline scrubber or "jump anywhere" affordance.
  - All character sprites look identical in raw replay (a known cosmetic limitation).
  - The evaluation relied on humans "watching a replay of a randomly chosen agent's life" with "access to all information stored in the agent's memory stream" — i.e., a per-agent memory-stream inspector is central to the design.

**Storage/architecture takeaway:** the **JSON-snapshot-per-tick** approach is simple and debuggable but bloats storage (hence the separate compress step) — the opposite tradeoff from AI Town's delta buffers. For 1,000 NPCs over long runs, naive per-tick JSON will not scale; adopt deltas + periodic keyframes.

**AI Town (a16z-infra / Convex).** Covered above as the best template. Rewrote Smallville's Python stack into TypeScript on Convex + **PixiJS** ("All interactions, background music and rendering… are powered by PixiJS"; originally prototyped on Phaser via `phaser3-simple-rpg`). Runs "1–5 simulated minutes every real-world second," "click on any character to read their inner monologue," fits in <1 GB RAM. Its `HistoricalObject`/`useHistoricalTime` delta-replay system is the standout reusable idea.

**Other reimplementations/forks:** `semantic-systems/generative_agents_` (adds an "Inner Voice" call to inject thoughts and Phaser tweaks to show the whole map); `AlexHarn/claudeville` (Claude port) whose README candidly logs UI debt — "Persona panel needs improvements for large groups (25+ personas) - scrolling works but needs smart ordering by proximity/activity"; `mkturkcan/generative-agents` (low-cost local models); `nmatter1/smallville` (game-integration client library). These forks confirm the **"persona panel doesn't scale past ~25 agents without smart ordering"** problem you'll hit at 25–1,000 NPCs.

### (3) Game-shipped god views

**The Sims.** The gold standard for legible at-a-glance social/need state (details from The Sims Wiki):
  - **Plumbob:** floats over the selected Sim; identifies the active Sim *and* encodes mood by color — per the wiki, "If the Sim is in a very good mood, the plumbob will be a bright, deep green… A Sim in a bad mood will have a red plumbob, and the red will get brighter and deeper as the Sim's mood gets worse," shifting through paler/neutral tones between. It's also translucent so it doesn't occlude. This is a compact "selection + status" glyph worth copying for NPC markers.
  - **Need/motive bars:** color-coded green→yellow→red bars communicate each need's level at a glance; mood is an aggregate.
  - **Action queue:** the row of queued interaction icons shows what a Sim will do next, with the active item visually distinguished from queued ones — directly analogous to showing an NPC's current plan/schedule.
  - **Thought bubbles** surface transient wants/reactions above the Sim.
  - **Relationship panel** (hotkey R) shows friend/romance bars per known Sim.
  - Design lesson: state is layered by proximity of need — glanceable glyph on the world (plumbob), summary bars in the selection HUD, full detail in panels.

**Dwarf Fortress — Legends mode & third-party viewers.** Legends mode is a **historical browser**: "players can view maps, histories of each civilization and any figure who has lived or died." It's browsing accumulated *history*, not a live scrubber. Third-party viewers improve on the clunky built-in UI:
  - **Legends Viewer** (Parker147/Kromtec) and **LegendsViewer-Next** (Kromtec; .NET 10 + Vue 3/TypeScript + **Leaflet.js** interactive maps): "Browser-like navigation, including tabs… view other people/places/entities by just clicking names in the event logs or search lists, CTRL+Click opens a new tab." Every tab has an **Events sub-tab** with filtering. This **hyperlinked entity-graph navigation** (click any name to jump to that entity, everything cross-linked) is a strong model for beliefs-with-provenance and rumor-spread chains.
  - **Legends Browser / Legends Browser 2** (robertjanetzko; Java then Go): runs a local web server at `localhost:58881`, "Recreates Legends mode… with objects being accessible as pages with links to related objects," adds statistics/overviews. Requires exporting `legends.xml` (+ `legends_plus.xml` via DFHack).
  - **Dwarf Therapist:** a spreadsheet/table over all dwarves — "view all dwarf skills in one place," sort by "profession, migration wave, happiness"; in the DFHack GUI reimplementation, name color reflects stress ("cyan = ecstatic → red = miserable"). Community verdict: "the best part of DT is the available info and the sorting" — i.e., a **sortable, filterable, color-coded roster table** is invaluable at scale. (The DF community had to *build* these because the in-game UI was inadequate for browsing a large population — a cautionary tale about shipping only a map view.)

**RimWorld.** Rich inspection conventions plus a mature analyzer-mod ecosystem:
  - **Colonist bar** (top): portraits with mood color + needs; clicking centers on the pawn.
  - **Inspect pane** (bottom-left) with tabs: **Needs**, **Thoughts** (moodlets with numeric offsets and expiry), **Social** (relationships), **Health**, **Gear**, plus a **History/graph tab** charting mood/wealth over time.
  - Vanilla pain point that motivated mods: per the "Modern Social Tab" Steam Workshop page, the vanilla Social tab "gives you a list of names and a number beside each one. It never tells you why. Modern Social Tab replaces it with a relationship ledger… with every reason behind it laid out and labelled by where it came from" — i.e., **provenance for every relationship value**, exactly your "beliefs with provenance" requirement.
  - **RimHUD:** integrates a dense, resizable readout into the inspect pane with visual warnings for life-threatening conditions/mental breaks.
  - **Numbers** mod: "a customizable general overview tab… see any stats on all your colonists… in a single window," sortable columns, click header to sort, click cell to jump to colonist — the RimWorld analog of Dwarf Therapist.
  - **Pawn Badge:** small skill/role icons next to portraits so you can identify roles at a glance; **Colony Manager** (fluffy) automates bulk tasks; **Modern Needs Tab** keeps a 15-day recorded history so "graphs, rates and forecasts are real recorded history rather than a guess."
  - Design lessons: (a) tabs for orthogonal facets of one entity; (b) always show *why* (provenance/moodlet source); (c) provide a sortable colony-wide table in addition to per-pawn panels; (d) recorded history + graphs beat instantaneous snapshots.

### (4) Sports / RTS / MOBA replay conventions (the grammar players already know)

**Dota 2.** Per the Dota2Gamers.gg replay guide, the replay bar shows **event markers** so you "navigate to kills, objectives, or team fights without scrubbing blindly," with "Stat Overlays: View live graphs, hero net worth, and item builds," plus speed up/slow down/pause/jump. Steam's cross-game recorder "shows a timeline of everything that has happened in a match. Players can also add their own markers and times of interest to the timeline" — i.e., **user-placed bookmarks**. Documented bug worth noting (Valve issue #20025): "Using fast-forward/rewind buttons while replay is paused causes it to bug out" — pause/scrub state interaction is a real edge case to test.

**StarCraft II.** The **observer/replay UI** is a rich template (Liquipedia/patch notes):
  - **Production tab** ("Displays all research, construction and production taking place") and Units/Structures tabs; "Clicking on an icon in the Units/Structures/Production tabs will now center the camera on that unit. Continued clicks will cycle through all units of that type" — a great pattern for "cycle through all NPCs who believe X."
  - **Jump back to any already-seen point**; toggle timeline/duration panel; **Watch with Others** where "each viewer can adjust his or her own UI… Whoever hosted the replay lobby also gets the ability to control the timeline."
  - Damaged units flash / change selection-circle color for observers — legibility affordances.
  - Fully **custom observer UIs** via SC2Interface mod support — evidence that broadcast professionals need *configurable* overlays.

**CS2 / general.** `demo_gototick` and timeline scrubbing to "jump to exact moments… using tick numbers" — the **tick is the addressable unit of time**, exactly your "as of tick T." Video-editor/graphics-debugger scrubbers (e.g., NVIDIA Frame Scrubber) reinforce the grammar: drag playhead, shift-drag to select a range and zoom, hotkeys to step frame-by-frame.

**Grammar to inherit:** draggable playhead + tick-addressable jumps; event markers + user bookmarks on the bar; speed multipliers; camera bookmarks / "cycle through entities of type"; per-viewer UI toggles; production/summary side panel that stays in sync with the timeline.

### (5) Rendering performance: hundreds-to-thousands of entities

The evidence is consistent and decisive:
- **SVG/D3 (retained-mode DOM):** per Scott Logic's "Rendering One Million Datapoints with D3 and WebGL" (Colin Eberhardt, 2020), "SVG charts can typically handle around 1,000 datapoints"; graph-viz libraries (GraphAware) warn of "a performance drop… when you try drawing graphs larger than ~1000 nodes"; every SVG node is a DOM node kept in memory, so "performance degrades quickly" past a few thousand. **Do not build the map in SVG.**
- **Canvas (immediate-mode):** per the same Scott Logic source, "With Canvas you can expect to render around 10,000 datapoints whilst maintaining smooth 60fps interactions"; degradation sets in "as you exceed 5,000 points and approach 10,000." Canvas is a single DOM node — but you lose free hit-testing (you must math out clicks) and accessibility.
- **WebGL (PixiJS/Phaser):** the proven path for "thousands of moving sprites efficiently even on mobile" (PixiJS docs). PixiJS does **automatic sprite batching** — per the official pixijs Wiki "v4 Performance Tips," "Sprites can be batched with up to 16 different textures (dependent on hardware). This is the fastest way to render content." Per the PixiJS Spritesheets guide, "WebGL rendering speed scales roughly with the number of draw calls made. Batching multiple Sprites… into a single draw call is the main secret to how PixiJS can run so blazingly fast." Critical caveat, same Wiki: "Culling, PIXI does not cull anything, we have left this to you and your application" — you must implement viewport culling for large worlds.
- **Mesa/SolaraViz:** matplotlib/Altair backends + Python round-trips make it unsuitable for thousands of live agents (hence the "pause before switching pages" warning and the threading fix).
- **NetLogo Web:** JVM-to-JS, partially compiled, slow with large agentsets.

**Recommendation for 25–1,000 NPCs:** WebGL via **PixiJS** (AI Town's choice) or Phaser (Smallville's choice), with a spritesheet, sprite batching, and viewport culling. Canvas 2D is an acceptable fallback up to a few thousand markers if you want simpler hit-testing. Reserve SVG only for small overlays (selection rings, a handful of rumor-arc lines), never for the full agent layer. Rumor-state overlays that connect many NPCs (edges) are the most expensive layer — draw them on the WebGL/canvas layer, aggregate/cluster at low zoom, and only render edges for the selected rumor.

## Recommendations

**Stage 1 — Core skeleton (build first).**
1. **Renderer:** PixiJS WebGL canvas for the map + NPC markers, one spritesheet, sprite batching, viewport culling. Budget for 1,000 markers at 60fps.
2. **Time model:** make the **tick the addressable unit**. Store simulation output as **per-tick deltas over periodic keyframes** (AI Town's model), not full JSON snapshots per tick (Smallville's model, which its authors admit is storage-unoptimized). A "state as of tick T" resolver = nearest keyframe + replay deltas forward.
3. **Transport controls:** play/pause + discrete speed multipliers (adopt The Sims' 1×/2×/3× and Smallville's 1–5), plus a **draggable timeline scrubber** with tick-addressable jumps (the affordance every ABM tool lacks).
4. **Global "as of tick T" contract:** every panel subscribes to a single current-tick value (AI Town's `useHistoricalTime` pattern) so map, inspector, and timeline never desync.

**Stage 2 — Inspection.**
5. **Click-agent → persistent inspector** with tabbed facets (RimWorld model): Beliefs (with **provenance/source labels** — the RimWorld "Modern Social Tab" lesson), Rumors heard, Grudges (with why), Schedule/current plan (Sims action-queue style), and a per-NPC **history graph** (RimWorld history tab / Modern Needs Tab).
6. **At-a-glance encoding on markers:** a Sims-plumbob-style mood/state glyph and/or color; Pawn-Badge-style role icons; keep it translucent/non-occluding.
7. **Sortable, filterable roster table** alongside the map (Dwarf Therapist / RimWorld Numbers): sort by belief, grudge count, last-rumor-received tick; click row → select + center on map; "cycle through all NPCs matching filter" (SC2 production-tab pattern).

**Stage 3 — Timeline richness & rumor analysis.**
8. **Event markers on the scrub bar** (Dota 2 model): rumor mutations, belief flips, new grudges, conversations; plus **user bookmarks**.
9. **Rumor-state overlay** as a selectable layer drawn on the WebGL/canvas layer; show spread edges only for the selected rumor; cluster at low zoom. Consider **Legends-Viewer-style hyperlinked navigation**: click a belief's provenance → jump to the NPC/event that originated it.
10. **Layer toggles** (GAMA/SC2 observer model) for rumor overlays, grudge edges, schedule paths.

**Benchmarks / thresholds that change the plan.**
- If sustained NPC count ≤ ~300 *and* you want trivial hit-testing/accessibility, **Canvas 2D** is acceptable and simpler than WebGL.
- If marker count routinely exceeds ~2,000 or you draw many rumor edges, WebGL is mandatory and you must add culling + LOD/clustering.
- If per-tick delta payloads exceed a few dozen KB (AI Town's stated in-memory ceiling), move to server-side tick indexing and stream only the viewport's entities.
- If replay desync/scrub bugs appear, test the **paused-while-scrubbing** path explicitly (the documented Dota 2 failure mode, Valve issue #20025).

## Caveats
- **Live-stepping vs. replay are different problems.** Almost all ABM tools (NetLogo, Mesa, GAMA, AnyLogic) only step forward live; Smallville only replays forward from a chosen start step. A true bidirectional **scrubber over recorded history** is comparatively rare outside RTS/MOBA replays — you are combining two lineages, so borrow the *time model* from RTS/AI Town and the *inspection affordances* from god-games/ABM.
- **Source quality notes.** AI Town's exact code-level constants (`TICK=16`, `STEP_INTERVAL=1000`, `MAX_SERVER_BUFFER_AGE=1500`, 16-field limit, quantize→delta→RLE→varint pipeline) come from the repo's `ARCHITECTURE.md` (primary) plus code mirrors of `historicalObject.ts`/`useHistoricalTime.ts`; the doc's "60 ticks per second / 1 step per second" is consistent with `TICK=16`/`STEP_INTERVAL=1000`. Verify against the current `main` branch before implementing. Several RimWorld/Sims details come from wikis, community mods, and Steam Workshop pages rather than official docs; treat mod-specific behavior as version-dependent.
- **Forward-looking/marketing claims flagged:** GAMA's "up to millions of agents" and PixiJS's "thousands of sprites… even on mobile" are vendor/community claims that depend heavily on per-agent complexity, texture count, and culling; benchmark with your actual marker/overlay complexity rather than trusting the headline number.
- **Provenance is the recurring blind spot.** The single most-requested improvement across RimWorld (Social tab), GAMA (per-agent debug overlays, issue #2240), and Smallville forks (persona-panel ordering) is *explaining why* and *scaling the per-entity view*. Since "beliefs with provenance" and "rumors mutating as they spread" are your core differentiators, invest disproportionately in the provenance/why UI and in per-entity views that stay legible at 1,000 NPCs.

## Key links
- AI Town architecture: https://github.com/a16z-infra/ai-town/blob/main/ARCHITECTURE.md · demo: https://www.convex.dev/ai-town
- Generative Agents (Smallville): https://github.com/joonspk-research/generative_agents · paper: https://arxiv.org/abs/2304.03442
- Mesa SolaraViz docs: https://mesa.readthedocs.io/stable/tutorials/6_visualization_basic.html · issues: https://github.com/mesa/mesa/issues/2814
- GAMA inspectors/displays: https://gama-platform.org/wiki/InspectorsAndMonitors · https://gama-platform.org/wiki/Displays
- AnyLogic inspecting agents: https://anylogic.help/anylogic/agentbased/inspecting-agents.html
- The Sims plumbob: https://sims.fandom.com/wiki/Plumbob
- DF Legends Viewer: https://github.com/Kromtec/LegendsViewer-Next · Legends Browser: https://github.com/robertjanetzko/LegendsBrowser2 · Dwarf Therapist: https://dwarffortresswiki.org/index.php/Utility:Dwarf_therapist
- RimHUD: https://github.com/Jaxe-Dev/RimHUD · Numbers: https://steamcommunity.com/sharedfiles/filedetails/?id=1414302321 · Modern Social Tab: https://steamcommunity.com/sharedfiles/filedetails/?id=3740700588
- Dota 2 replays: https://dota2gamers.gg/how-to-watch-dota-2-replay/ · SC2 replay features: https://liquipedia.net/starcraft2/Replay_Features · CS2 replay: https://tradeit.gg/blog/cs2-replay-controls/
- Rendering perf: https://blog.scottlogic.com/2020/05/01/rendering-one-million-points-with-d3.html · PixiJS perf: https://github.com/pixijs/pixijs/wiki/v4-Performance-Tips · https://pixijs.com/7.x/guides/components/sprite-sheets