---
date: 2026-08-26
sources:
  - "compass_artifact_wf-4a18014d-0c21-5ccd-b55d-6679232e8da8_text_markdown.md"
topic: "off-screen entity simulation and live/abstract handoff protocol (RimWorld WorldPawns vs Dwarf Fortress historical_figure) — first pass"
status: filed
---

# Off-Screen Entity Simulation and Handoff in Dwarf Fortress and RimWorld — An Architectural Blueprint for the "Chronicle" Skyrim Bridge

## TL;DR
- **Adopt RimWorld's `WorldPawns` model, not Dwarf Fortress's re-instantiation model.** Chronicle should keep the *same authoritative Python object* alive across the abstract↔live boundary (RimWorld preserves the identical `Pawn` object when a caravan enters a map), rather than serializing an abstract record and regenerating a fresh actor at spawn (DF's approach, which is the direct cause of its "necks ripped off in world-gen, instantly die on arrival" class of bugs).
- **Python is authoritative for social/relationship state; the engine is authoritative for physical/combat state; reconcile at 3D-load via a versioned, idempotent handoff protocol** that begins on `TESCellAttachDetachEvent` (cell attach, roughly one cell — 4096 game units ≈ 58.5 m — ahead of 3D load), writes state into the actor in native C++ off-camera before `Load3D`, and treats the reverse direction (actor→abstract) as a "catch-up" fast-forward exactly like RimWorld's mothball tick.
- **The dominant failure mode is state divergence** (the player kills/robs/marries the NPC while loaded, then Python has stale state, or Python is unavailable at load). Solve it the way RimWorld's `WorldPawnGC` and mothball systems do: define a strict ownership split, make every message idempotent and versioned, let the engine win on physical facts and Python win on social facts, and have a "plausible story" backfill (alibi generation) for any gap you cannot reconcile.

## Key Findings

### The two games sit at opposite ends of the "preserve vs regenerate" spectrum
- **RimWorld preserves object identity.** An off-map pawn is the *same* `Verse.Pawn` C# object it was on the map, parked in the `WorldPawns` collection. When it returns, `CaravanEnterMapUtility.Enter` calls `GenSpawn.Spawn` on that very object and `WorldPawns.RemovePawn` removes it from the world registry. Needs, health, relationships, and memories are never serialized/regenerated across the boundary — they simply keep existing at a reduced tick rate.
- **Dwarf Fortress regenerates.** Off-site entities exist only as compact `historical_figure` records. When a unit leaves the map it is "offloaded" and re-initialized from histfig data; when it arrives it is instantiated fresh — inventory, wounds, and transient state are generated at instantiation time. This is why, per the DF wiki, "every time the local map is offloaded, all units… are re-initialized from historical figure data," healing non-permanent wounds and resetting stomach fullness and intoxication.
- **For Chronicle, RimWorld's model is the correct target** because social simulation state (grudges, obligations, beliefs) is exactly the kind of rich, path-dependent state that DF's regenerate-from-summary approach *destroys*. You want the RimWorld invariant: the authoritative object is continuous; only its *tick fidelity* and its *engine embodiment* change.

### Both games use tiered tick rates as the core cost-reduction mechanism
- **RimWorld** has three tick buckets in `Verse.TickManager`: `tickListNormal` (`TickerType.Normal`, every tick — 60/s at 1×), `tickListRare` (`TickerType.Rare`, every 250 ticks), and `tickListLong` (`TickerType.Long`, every 2000 ticks). Off-map world pawns are ticked by `WorldPawns.WorldPawnsTick`, and *mothballed* pawns are processed only every 15000 ticks (`MothballUpdateInterval`, once per in-game day) via `DoMothballProcessing`/`TickMothballed(15000)`. Auto-tending of injuries for world pawns runs on a 7500-tick interval (`TendIntervalTicks`).
- **Dwarf Fortress** staggers world simulation off the local fort loop. Tarn Adams (Toady One), in Game Developer's "Q&A: Dissecting the development of Dwarf Fortress," describes the main loop: "Every hundred ticks, for instance, it'll check job assignments and 'strange moods.' Armies are moved on the world map… Every ten ticks it advances the seasons… and it also does a check for certain plot element advances (diplomats, sieges, etc.)," while local per-tile/per-unit work happens every tick with flags allowing whole sections to be skipped. The world-map army simulation is thus ~100× coarser than local fort simulation.
- **Chronicle takeaway:** run three fidelity tiers in Python — a "loaded" tier (event-driven, per engine callback), a "near" tier (seconds), and a "cold/mothballed" tier (once per in-game hour/day) — and demote/promote NPCs between them exactly as RimWorld moves pawns between `pawnsAlive` and `pawnsMothballed`.

### Data structures: what is actually stored off-screen
- **RimWorld `WorldPawns`** holds four `HashSet<Pawn>`: `pawnsAlive`, `pawnsMothballed`, `pawnsDead`, and `pawnsForcefullyKeptAsWorldPawns`. A `WorldPawnSituation` enum classifies each (`Free`, `Dead`, `FactionLeader`, `Kidnapped`, `CaravanMember`, `InTravelingTransportPod`, `ForSaleBySettlement`, `None`). Mothballing is gated by `ShouldMothball`/`DefPreventingMothball`: a pawn is mothballed only if it has no non-permanent `Hediff` (i.e., nothing actively changing like a bleeding wound or disease), is not a caravan member, and is not in a transport pod. This is *lazy evaluation of health*: a pawn with a healing wound must tick; a fully-healed pawn need not.
- **RimWorld caravans** are `WorldObject`s carrying the real pawn objects. Needs are simulated abstractly via `CaravanPawnsNeedsUtility` — food/rest are decremented per world-tick rather than per pawn-AI-tick. Travel cost is governed by `CaravanTicksPerMove`. Injuries are tended abstractly via the same auto-tend path. Food consumption is real bookkeeping: per the RimWorld wiki and in-game info panel, an adult humanlike pawn's hunger rate is a fixed 1.6 nutrition/day (route-independent), and a caravanning colonist forages roughly 0.09 nutrition/day per point of Plants skill — abstract per-day accounting rather than per-meal simulation.
- **DF `historical_figure`** records store identity, history, relationships, skills, and links — but *not* live physical state (position within a map, current wounds, stomach contents). "If a creature's `hist_figure_id` is not equal to -1, then by definition it is a historical figure." Only a small fraction of the population is tracked explicitly; the rest are handled as abstract population counts. `army` structures are, in the DF wiki's framing of Toady's design, "the abstract data structures used… to keep track of moving people" — position and members on the world map, ticked ~every 100 local ticks.
- **DF statistical abstraction:** "In world generation, due to computation and memory constraints, most population numbers have to be treated abstractly," with only histfigs explicitly tracked. Caravans/invasions "can instantiate non-historical populations" on demand — pure just-in-time generation.

### The Storyteller / army system: probability tables instead of simulation
- **RimWorld's Storyteller** samples incidents from probability tables rather than simulating causes. Incidents fire on a mean-time-between (MTB) basis: `IncidentDef.baseChance`, category MTBs, and a population-intent factor. Per Cassandra's `Storytellers.xml` constants documented by the community: `classic_ThreatBigMTBDays = 3.75` (big threats such as raids average ~3.75 days apart), `classic_ThreatSmallMTBDays ≈ 1.25`, and `minDaysBetweenThreatBigs = 1.9`. Randy Random uses `mtbDays ≈ 1.13` with `maxThreatBigIntervalDays = 13`. The `IncidentQueue` ticks each `StorytellerTick`. This is statistical abstraction: the world doesn't simulate a raider band forming and marching; it rolls dice and *then* generates the band with a plausible composition.
- **This is the game-industry "alibi generation" pattern** (Ben Sunshine-Hill, "Alibi Generation: Fooling All the Players All the Time," *Game AI Pro* ch. 37; AAAI 2010): generate only the *visible* information up front, and when the player interacts, retroactively generate the *invisible* backstory as a consistent effect using the visible facts as cause. Sunshine-Hill's stated goal is that "it is impossible for the player to determine whether an NPC has always been around or whether they were just given an alibi a couple of seconds ago." Chronicle should use this for any state it *chose not to simulate* off-screen.

### Handoff protocol specifics
- **RimWorld abstract→live:** `Caravan.Enter` → `CaravanEnterMapUtility.Enter(caravan, map, spawnCellGetter, dropInventoryMode, draftColonists)` → `GetOrGenerateMapUtility.GetOrGenerateMap` (map made lazily if it doesn't exist) → `CellFinder.TryFindRandomEdgeCellWith` picks a map-edge entry cell → `GenSpawn.Spawn(pawn, loc, map, Rot4.Random, WipeMode.Vanish, false)` for each pawn → optional inventory drop (`CaravanDropInventoryMode`). Crucially, `WorldPawns.RemovePawn` is called so the pawn is no longer double-tracked, and if the pawn was mothballed it gets a final catch-up tick (`TickMothballed(TicksGame % 15000)`) *just before removal* to bring transient state current. Nothing is regenerated: the same object with the same needs/health/relations is placed on the map.
- **RimWorld live→abstract (reverse):** `Pawn.ExitMap` → `CaravanExitMapUtility.ExitMapAndCreateCaravan` despawns the pawns and hands them to a caravan `WorldObject`; internally `WorldPawns.PassToWorld(pawn, PawnDiscardDecideMode)` registers them and `PawnComponentsUtility.RemoveComponentsOnDespawned` strips map-only components. The object survives; its map embodiment is discarded.
- **DF abstract→live:** off-site armies/caravans/sieges are converted to active units at the fort map edge; histfigs are instantiated as units with inventory/equipment/wounds generated at instantiation. Caravan pack animals and traders become histfigs during their stay; guards do not. Caravans arrive at a wagon-navigable map edge and depart 30000–40000 ticks (25–33 days) later.

### Coherence guarantees and their instructive failure modes
- **RimWorld's `WorldPawnGC`** (garbage collector) is the coherence keeper for the *population*, not the individual. It walks a reachability graph: `AccumulatePawnGCData` marks "critical" pawns (faction leaders, kidnapped, caravan members, quest targets, pawns with relations to on-map pawns, pawns referenced in active `Tale`s) and preserves them; unreferenced world pawns are discarded via `RemoveAndDiscardPawnViaGC`. `GetSituation` drives keep/discard.
  - **Instructive bug #1:** In long games this graph *over-keeps* — every raider you ever killed who has any relation lingers, bloating saves and slowing ticks, which is why community mods (Zhentar's WorldPawnGC, RuntimeGC, "Better GC: Mothballed and World Pawns") exist to aggressively prune, in one case cutting ticking pawns "from 200+ to 80+." Lesson: relation-graph reachability is correct but must have a *time-decay* escape valve.
  - **Instructive bug #2:** EdBPrepareCarefully's dead "placeholder parent" pawns were left out of `pawnsForcefullyKeptAsWorldPawns`, so GC destroyed them ~48h later, silently deleting sibling relationships. Lesson: anything you want to survive must be *explicitly pinned*, not merely reachable.
- **DF's regenerate-on-arrival** produces its own class of incoherence: per TV Tropes' "GoodBadBugs / Dwarf Fortress," "Historical figures can survive having their necks ripped off in world-gen, only to instantly die once they show up during actual play" (world-gen abstract combat resolved differently from local instantiation); traded animals that can't die because their unit is never offloaded; and invisible/ghost caravans (bug tracker #9593). Lesson: a summary→full regeneration boundary is where invariants silently break; minimize what you regenerate.
- **Both use deterministic seeding / lazy generation with a plausible story** to make just-in-time generation reproducible and consistent (DF world seeds; RimWorld map/pawn generation from seeded `PawnGenerationRequest`s).

### The Skyrim side: how the engine already does simulation LOD
- **Creation Engine AI process LOD** has four tiers in `RE::AIProcess`/`RE::ProcessLists` (singleton): **High, MiddleHigh, MiddleLow, Low**. `HighProcessData` holds full combat/detection/head-tracking/pathing for actors in the attached cell grid with 3D loaded; lower tiers progressively drop combat/detection/animation; **Low** actors have no 3D and no per-frame AI — only periodic package/schedule evaluation. `ProcessLists` sorts actors into these tiers "based on distance and importance." This is Skyrim's native equivalent of RimWorld's tick tiers — Chronicle layers *on top of* it.
- **Engine limit directly relevant to handoff:** Skyrim only updates an unloaded NPC's AI-process position for at most **1 in-game hour**, which is why the "NPC AI Process Position Fix - NG" plugin exists (it detects wait/sleep/fast-travel, computes the time delta, and forces schedule-position updates). Any Python-driven off-screen movement must be re-asserted into the engine at load, not assumed.
- **Cell/actor load sequence:** player crosses a boundary → `CellLoaderTask` (background thread) → `TESObjectREFR::CreateReference` → per-ref 3D load / actor init → cell attach (`TESCellAttachDetachEvent`, Papyrus `OnCellAttach`) → 3D loads (`OnLoad`) → `TESCellFullyLoadedEvent`. Actors promote Low→High as their cell enters the grid. Default `uGridsToLoad=5` → a 5×5 = 25-cell active area; each exterior cell is 4096 game units ≈ 58.5 m, so ~292×292 m loaded.
- **Persistence & reconciliation:** `.ess` saves store per-reference deltas as ChangeForms (ACHR for actors); the reference-handle cap is ~2²⁰ ≈ 1,048,576 (SSE Engine Fixes defaults `RefrLoadGameLimit`=1,000,000 / `RefrMainMenuLimit`=800,000). SKSE co-saves (`SKSESerializationInterface`) provide `SetSave/Load/RevertCallback`, `WriteRecord`/`ReadRecordData`, and critically `ResolveFormId`/`ResolveHandle` to remap IDs across load-order changes. SKSE messages `kMessage_DataLoaded`, `kMessage_NewGame`, `kMessage_PreLoadGame`, `kMessage_PostLoadGame` bracket the load lifecycle.
- **Papyrus vs native C++:** Papyrus is a single-threaded, frame-synced VM; `RegisterForSingleUpdate` is practically limited to ~0.1 s intervals and delayed native calls cost a frame each. The bridge *must* be native C++ (CommonLibSSE-NG), using `SKSETaskInterface::AddTask` to marshal engine mutations onto the main thread, and named pipes / shared memory for IPC to the Python process.

## Details

### Comparative table (all three axes)

| Axis | Dwarf Fortress | RimWorld | Recommended for Chronicle |
|---|---|---|---|
| **Off-screen representation** | Compact `historical_figure` record; live state discarded on offload; `army` structs for movement | Same live `Pawn` object parked in `WorldPawns` (alive/mothballed/dead) | Same live Python object; tier flag (loaded/near/cold) |
| **Tick reduction** | World armies every ~100 ticks; seasonal checks every 10; local every tick with skip-flags | `Normal`/`Rare`(250)/`Long`(2000); world pawns tended every 7500; mothball every 15000 | 3 tiers: event-driven / seconds / hourly |
| **Statistical abstraction** | Population counts abstract; histfigs explicit; caravans/invasions instantiated JIT | Storyteller MTB tables; incidents rolled then generated | MTB for off-screen social events; alibi backfill |
| **Handoff direction (in)** | Regenerate unit from histfig at map edge | `CaravanEnterMapUtility.Enter` → `GenSpawn.Spawn` same object | Reconcile Python state into pre-existing/spawned actor in C++ |
| **Handoff direction (out)** | Offload unit → histfig; transient state lost | `ExitMap`/`PassToWorld`; object survives, map components stripped | On cell detach, snapshot engine physical facts → Python; demote tier |
| **Coherence mechanism** | Deterministic world seed; JIT generation | `WorldPawnGC` reachability graph; mothball catch-up tick; forced-keep pins | Ownership split + idempotent versioned messages + alibi backfill |
| **Known failure mode** | Regeneration breaks invariants (necks, ghost caravans) | GC over-keeps (save bloat) or under-pins (lost relations) | Divergence when player mutates actor; Python unavailability |

### What state lives where (authoritative ownership split)

**Python (authoritative, survives everything):**
- Identity: stable NPC ID ↔ Skyrim base FormID mapping (run through `ResolveFormId` on load).
- Social graph: relationships, grudges, obligations, beliefs, faction standings, memory/knowledge of events ("who did what to whom").
- Long-horizon plans/goals and off-screen "narrative position" (which settlement, what they're nominally doing).
- Reputation and disposition toward the player.

**Engine (authoritative for physical facts while loaded):**
- 3D position, cell, current package/animation.
- Combat state, health/limb damage (Skyrim actor values, ACHR ChangeForm).
- Inventory *as physically manipulated by the player* (robbed, gifted, pickpocketed).
- Life/death and marriage state (player-driven), which are engine facts Python must accept.

**Regenerated / discarded at spawn (never trusted across the boundary):**
- Transient AI micro-state (exact idle, head-tracking target).
- Off-screen "alibi" details not previously simulated (what they were carrying, exactly where they slept) — generated on demand, plausibly, from Python's coarse state.

### The handoff protocol (concrete)

**Promotion (abstract → live), triggered on `TESCellAttachDetachEvent` for the NPC's cell (one cell ahead of 3D load):**
1. C++ bridge fires `HANDOFF_REQUEST{npc_id, form_id, engine_state_version}` to Python over the named pipe.
2. Python returns `HANDOFF_STATE{npc_id, state_version, social_blob, disposition, plans, plausible_inventory_hints, last_known_pos}` — a single batched message, not per-field.
3. Bridge, on the main thread via `SKSETaskInterface::AddTask`, and *before* `Load3D` completes (actor still Low/unloaded, off-camera): reposition with `MoveTo` (safe for unloaded actors, no pop-in), set disposition/faction/relationship-derived values, apply any Python-authoritative overrides. Never `SetPosition`/`TranslateTo` before `Is3DLoaded()` is true.
4. Let 3D load naturally; the actor promotes Low→High. From here the engine owns physical simulation; Python drops the NPC to "loaded/mirror" tier and stops authoritative physical simulation.

**Demotion (live → abstract), on `OnCellDetach`/`TESCellAttachDetachEvent` (detach):**
1. Bridge snapshots engine physical facts (position, health, inventory delta, alive/dead, marriage) into `ENGINE_SNAPSHOT{npc_id, state_version+1, ...}`.
2. Python reconciles: physical facts overwrite Python's mirror; social facts are Python-authoritative and unchanged; a "catch-up" is scheduled.
3. Python resumes off-screen simulation at reduced tier — exactly RimWorld's mothball model: a single `TickMothballed(delta)`-style fast-forward when the NPC is next promoted, rather than continuous fine ticking.

**Message schema (suggested, versioned + idempotent):**
```
Envelope     { protocol_ver, msg_type, npc_id, state_version, monotonic_seq, timestamp }
HandoffState { social_blob(cbor), disposition:int8, plans[], inv_hints[], last_pos:{cell,x,y,z} }
EngineSnapshot { pos, av_health, limb_dmg[], inv_delta[], flags{dead,married,hostile} }
Ack          { npc_id, applied_state_version }
```
Every message carries `state_version` and `monotonic_seq`; the receiver ignores any message with `seq <= last_applied_seq` (idempotency), and on conflict the ownership split decides the winner (engine wins physical, Python wins social).

### Timing and pop-in avoidance
- **Begin handoff at cell attach, not 3D load.** `TESCellAttachDetachEvent` fires when the cell enters the grid — roughly one cell (~58.5 m) before the actor's mesh instantiates, giving the round-trip to Python (target < 16 ms one way over a named pipe; shared memory if you need per-frame streaming) ample slack.
- **Reposition while unloaded via `MoveTo`.** Because an unloaded actor has no 3D, moving it produces no visible pop-in; 3D then loads at the correct position.
- **Player observing during transition:** if the player is already looking at the cell edge, keep the actor Low/disabled until state is applied, then enable off-frame; if state can't arrive in time, spawn with last-known engine state (stale but coherent) and silently reconcile on the next tick — never block the render thread waiting on Python.

### Failure modes and how to survive them
- **Python slow/unavailable:** the bridge must never block. On timeout, spawn the actor from the *last cached* `HandoffState` in the SKSE co-save. The game remains playable with slightly stale social state; Python reconciles when it returns. This mirrors RimWorld's invariant that world simulation degrades gracefully, not catastrophically.
- **Idempotency:** because `TESCellAttachDetachEvent` can fire repeatedly (border-straddling, fast-travel), every apply is keyed by `state_version` and `monotonic_seq`; re-applying the same handoff is a no-op.
- **Divergence (player killed/robbed/married the NPC while loaded):** these are *engine-authoritative* facts. On demotion, `EngineSnapshot.flags{dead,married}` and `inv_delta` overwrite Python's mirror unconditionally. Python then runs its social consequences (a grudge from the victim's kin, a spouse relationship) from those facts — this is alibi generation in reverse: the visible engine fact becomes the cause, Python generates the social effect.
- **Save/load with external state:** Skyrim saves engine state in `.ess`; Python state lives outside. Bridge writes a **compact mirror of each NPC's `state_version` + a hash of the social blob into the SKSE co-save** via `SKSESerializationInterface` (`SetSaveCallback`/`WriteRecord`). On `kMessage_PostLoadGame`, the `LoadCallback` runs `ResolveFormId` on every stored FormID (load-order may have shifted), then hands Python the set of `{npc_id, state_version}` the save expects. Python rolls its own store forward/back to match that version (keep a per-NPC append-only log keyed by `state_version` so you can seek to the version the save embeds). If the player reloads an older save, Python must roll back to the save's `state_version` — treat the co-save's versions as ground truth for "where the timeline is."
- **Handle budget:** never materialize all 150 NPCs as persistent 0xFF references — that burns the ~1M handle budget and defeats the purpose. Only the ~10 in loaded cells are live actors; the rest are pure Python objects with no engine footprint, exactly as RimWorld keeps world pawns out of any map.

## Recommendations

**Stage 1 — Build the ownership split and tick tiers first (before any handoff code).**
- Implement the three Python fidelity tiers (loaded / near / cold) and the RimWorld-style mothball rule: an NPC is "cold" (hourly tick) unless it has an *active, changing* state (an unfolding grudge event, travel in progress) — the direct analogue of `DefPreventingMothball`.
- Define the authoritative ownership table above as a hard contract in code. This is the single most important decision; get it wrong and every later bug is a divergence bug.
- **Benchmark to proceed:** cold-tier NPCs cost < 0.1 ms each per hourly tick; ~140 cold NPCs update in one batch without a frame hitch.

**Stage 2 — Native C++ bridge with idempotent, versioned messaging.**
- Write the bridge as a CommonLibSSE-NG SKSE plugin, not Papyrus. Hook `TESCellAttachDetachEvent`, `TESCellFullyLoadedEvent`, `TESLoadGameEvent`; marshal all engine writes through `SKSETaskInterface::AddTask`.
- Use a named pipe for request/response and, only if you find you need per-frame position streaming for a visible NPC, add a shared-memory channel with an event for sync.
- Make every message carry `{state_version, monotonic_seq}`; implement the "ignore stale seq / ownership-split conflict resolution" logic from day one.
- **Benchmark to proceed:** handoff round-trip p99 < 16 ms; zero observable pop-in in a test where the player walks a patrolling NPC's cell boundary 100 times.

**Stage 3 — Coherence, save/load, and alibi backfill.**
- Implement the SKSE co-save mirror (`state_version` + social-blob hash + FormID list) and the `ResolveFormId` reconciliation on `kMessage_PostLoadGame`.
- Implement engine-wins-physical / Python-wins-social reconciliation on demotion, including the "reload an older save → Python rolls back to the save's `state_version`" path. Keep a per-NPC append-only versioned log so rollback is a seek.
- Add alibi generation for any state you deliberately did not simulate: when a cold NPC is promoted and the player inspects details Python never tracked (exact inventory, where they were), generate it on demand from Python's coarse facts, consistent with what the player could already have observed.
- **Benchmark to proceed:** kill/rob/marry an NPC while loaded, unload, reload from three different saves; social consequences are always consistent with engine facts and never resurrect a dead NPC or lose a marriage.

**Thresholds that would change the recommendation:**
- If you ever need > ~50 simultaneously *loaded* actors, revisit whether Python should own physical simulation at all (you'd be fighting the engine's own High-process cap, which mods raise only to ~2000 total AI instances).
- If IPC round-trip p99 exceeds ~30 ms under load, move from named pipes to shared memory + a lock-free ring buffer.
- If save-file divergence bugs dominate testing, make the SKSE co-save the *sole* source of timeline truth and have Python treat itself as a pure cache (stronger than the recommended split, but simpler to reason about).

## Caveats
- **Source provenance (RimWorld):** internals here are from a community decompilation (`josh-m/RW-Decompile`, `WorldPawns.cs`/`WorldPawnGC.cs`/`CaravanEnterMapUtility.cs`/`TickManager.cs`) and the RimWorld wiki. Exact constants (`MothballUpdateInterval=15000`, `TendIntervalTicks=7500`, tick-list intervals) are from that decompiled source and match the wiki's tick documentation, but the decompilation reflects a specific version (Alpha/1.0-era `WorldPawns.cs`); 1.5/1.6 refactors (e.g., 1.6's camera-distance "variable tick rate") have since changed some paths.
- **Source provenance (DF):** internals come from the DF wiki, DFHack `df-structures`, and Tarn Adams' Game Developer Q&A. Field layouts and exact tick cadences ("armies every ~100 ticks") are from dev commentary and reverse-engineered documentation, not published source, and change between versions.
- **Skyrim CommonLibSSE tier names** (`kHigh`/`kMiddleHigh`/`kMiddleLow`/`kLow`) and per-tier contents are from DeepWiki's AI-generated summary of the powerof3 headers; verify the exact enum values against the actual `AIProcess.h`/`ProcessLists.h` before coding. The ~2²⁰ reference-handle cap is the widely-cited community figure; the Engine Fixes INI defaults (1,000,000 / 800,000) are confirmed from the mod page. The "off-screen AI position update capped at 1 in-game hour" behavior is inferred from the NPC AI Process Position Fix mod's description.
- **The alibi-generation and simulation-LOD literature** (Sunshine-Hill; the Springer/ACM simulation-LOD work) is academic/industry theory; it validates the *approach* but is not a description of how DF or RimWorld are implemented.
- This report assumes single-player Skyrim SE/AE; the handle-budget and co-save reconciliation advice does not account for any multiplayer/Skyrim Together layer.