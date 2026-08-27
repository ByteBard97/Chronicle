---
date: 2026-08-26
sources:
  - "Abstract Entity Modding Patterns.md"
topic: "off-screen entity simulation and live/abstract handoff protocol — second independent pass, Creation-Engine-specific framing"
status: filed
---

# Off-Screen Entity Handoff, v2

Second independent pass on the same ground as
[offscreen-entity-handoff-rimworld-dwarf-fortress.md](offscreen-entity-handoff-rimworld-dwarf-fortress.md),
framed specifically around the Creation Engine / SKSE handoff mechanics.

# **Architecture and State Synchronization for Headless NPC Simulation in the Creation Engine**

## **Introduction**

The integration of an external, headless social-simulation service with a live instance of the Creation Engine presents an intricate systems engineering challenge. Within the architecture of standard Bethesda titles, the simulation of non-player characters (NPCs) is strictly bound to the active state of the engine's 3D spatial grid, colloquially known as loaded cells. When an NPC resides in an unloaded cell, their existence is functionally suspended. The engine halts their physical simulation, pathfinding, and decision-making processes. Their state remains immutable unless a specific, manually crafted quest script or background background procedure forcibly mutates their stored properties.  
A project such as "Chronicle," which is designed to maintain a persistent, continuously evolving social state for a population of roughly 150 named NPCs—while only rendering approximately 10 at any given time—requires a fundamental decoupling of the NPC's cognitive, social, and chronological state from their physical representation in the 3D environment. This architectural paradigm is highly analogous to the systems utilized by complex simulation titles such as *Dwarf Fortress* and *RimWorld*, both of which manage sprawling populations of off-screen entities while maintaining the seamless illusion of continuous, parallel existence.  
This report provides an exhaustive investigation into the data structures, update frequencies, and handoff protocols employed by these simulation-heavy titles to manage off-screen entities. It then translates these established mechanics into a robust, thread-safe architectural recommendation for handling the transition from a headless Python simulation state to a live Skyrim Actor via a Skyrim Script Extender (SKSE) plugin. The ultimate objective is to provide a methodology that ensures absolute state coherence without visual pop-in, jarring teleportation artifacts, or engine instability, resolving the precise transition of an abstract entity becoming an active participant in the loaded world.

## **Abstract Entity Data Structures and Memory Partitioning**

To comprehend how a headless Python process should maintain the state of off-screen Skyrim actors, it is necessary to examine how established simulations partition active, physical data from inactive, abstract data. Memory and processing constraints dictate that the data structures representing a visible entity must be vastly different from the data structures representing an off-screen entity.

### **Dwarf Fortress: The Dichotomy of Historical Figures and Units**

*Dwarf Fortress* operates under extreme computational constraints due to the sheer volume of entities tracked across its procedurally generated worlds. To solve the problem of processing thousands of entities simultaneously, the engine strictly separates physical manifestations from abstract chronological records1. The architecture relies on two primary data structures: the unit and the historical\_figure.  
The unit data structure represents a fully instantiated physical entity within the local, loaded map. It possesses an immensely complex memory layout containing discrete body parts, active wounds, current inventory contents, complex pathfinding algorithms, and immediate artificial intelligence goals2. Units only exist in memory when they are physically present on a loaded map tile. The computational cost of maintaining a unit is high. Therefore, once a unit leaves the map—such as a merchant caravan departing the fortress—the physical unit data is culled from active memory and offloaded4.  
Conversely, the historical\_figure (often abbreviated as histfig) is a lightweight, abstract data structure that persists universally in the global state1. It tracks the entity's long-term state parameters: family relationships, accumulated grudges, kill lists, noble titles, and civilization affiliations1. If a creature's internal hist\_figure\_id is not equal to \-1, it is explicitly tracked by the game's history simulator, regardless of whether it physically exists in the loaded world at that moment1.  
When a caravan or migrant wave is generated entirely off-screen, the engine may create "void dwarves"—entities generated out of nothing to fulfill a population requirement1. These void entities are instantly assigned a historical\_figure record. Their relationships are maintained as direct pointers in memory to other historical figures, stored in the worldgen\_relationships property4. The abstract historical\_figure data structure requires vastly less memory and CPU overhead than a physical unit, allowing the game to simulate the socio-political movements of tens of thousands of off-screen entities effortlessly.

### **RimWorld: The WorldPawns Architecture and Storage Hierarchy**

*RimWorld*, engineered in C\#, employs a similar partitioning philosophy but handles it through a unified object model with a distinct storage hierarchy based on the entity's current location. Every humanoid or significant creature is instantiated as an instance of the Verse.Pawn class8.  
However, the game radically differentiates the computational treatment of active pawns versus abstract pawns based on their containing data structure. Pawns that are currently in the player's colony or on a loaded encounter map are stored within the Map object's ThingGrid and PawnTracker. These pawns receive continuous, high-frequency tick updates to process pathfinding, rendering frames, and immediate AI thought nodes9.  
Pawns that have left the map—such as traveling caravans, escaped prisoners, or off-site faction leaders—are transferred out of the active map structures and serialized into the RimWorld.Planet.WorldPawns container10. The WorldPawns manager acts as the ultimate, abstracted repository for off-screen entities11. To prevent unbounded save file bloat over long playthroughs, RimWorld utilizes an aggressive garbage collection process known as WorldPawnGCTick11. If a world pawn is deemed computationally unimportant—meaning it has no remaining relationships to active colony pawns, holds no political office, and is not flagged as a historical necessity—the garbage collector permanently deletes the pawn. For persistent NPCs that must never be deleted, the engine sets specific boolean flags, such as DefPreventingMothball, to ensure the pawn is preserved in the world state indefinitely12.

### **Application to the External Python Simulation**

For the Chronicle architecture under consideration, the external Python process must fulfill the exact role of the WorldPawns manager or the historical\_figure database. The Skyrim engine itself must never be considered the canonical source of truth for an off-screen NPC.

| Simulation Engine | Abstract Structure | Instantiated Structure | Primary Location |
| :---- | :---- | :---- | :---- |
| **Dwarf Fortress** | historical\_figure | unit | Global Memory / Local Map |
| **RimWorld** | Verse.Pawn (in WorldPawns) | Verse.Pawn (in Map) | Planet Scope / Local Map |
| **Chronicle (Python)** | Headless Object Model | Actor (Papyrus/C++) | External Process / Loaded Cell |

In the Python process, each of the 150 named NPCs must be represented by a lightweight, headless object. This object should exclusively contain their long-term state: current abstract location nodes, relationship matrices mapping their disposition toward other entities, psychological beliefs, ongoing obligations, and serialized abstractions of their inventory. The Python process does not need to know where an NPC is standing within a room; it only needs to know that the NPC is currently residing within the abstract node of that specific room.

## **Simulation Frequencies and Computational Scaling**

Continuous simulation of 150 NPCs at an engine-level tick rate—typically 60 frames per second in the Creation Engine—is computationally disastrous and logically unnecessary. When an entity cannot be seen, their actions do not need to be calculated with microsecond precision. Both *Dwarf Fortress* and *RimWorld* achieve their scale by utilizing specialized execution schedules and vastly reduced tick rates for abstract entities.

### **Event Batching and Annual Scheduling in Dwarf Fortress**

Because iterating through the status of tens of thousands of historical figures on every single engine tick would immediately halt the CPU, *Dwarf Fortress* relies on long-term event scheduling and daily batched resolution6.  
At the commencement of a simulation year, the engine generates an annual schedule13. It deterministically calculates future events—such as the exact date a specific historical figure will succumb to old age—and places these events in a time-sorted array1. The history simulation engine then performs a daily routine check, rather than a frame-by-frame check, to process these pre-calculated events6.  
Furthermore, abstract activities such as site succession, regional wars, and marriages are processed probabilistically rather than deterministically14. When a non-player army moves across the world map to attack a site, they do not pathfind tile-by-tile. Instead, they teleport across regional nodes based on probability tables that determine their time of arrival and their chance of interception14. The engine simply checks the probability table at the scheduled macro-tick, resolves the outcome, and updates the historical record accordingly.

### **Mothballing and Scaled Tick Rates in RimWorld**

*RimWorld* manages the processing overhead of off-screen pawns using a highly effective optimization concept known as "mothballing"12.  
The active game runs at a standard rate of 120 ticks per second9. If an off-screen pawn were forced to process its Pawn\_HealthTracker (which manages bleeding, diseases, and wound healing) and its Pawn\_RelationsTracker at this high frequency, late-game performance would degrade entirely17. Therefore, the WorldPawns system aggressively mothballs inactive entities, suspending their tick rate almost entirely.  
For biological processes that must logically continue off-screen—such as a disease progressing toward a fatal outcome or a pregnancy advancing—the game utilizes delta-time batching rather than continuous ticking18. Instead of adding a microscopic 0.001 severity to a disease every single tick, the engine waits for an off-screen macro-tick cycle, which may occur only once every 10,000 ticks. When the macro-tick fires, the engine applies a batched delta of severity all at once, retroactively updating the pawn's state to match the elapsed time19.  
The engine uses abstract methods like ShouldAutoTendTo to deterministically calculate if an off-screen caravan member would have successfully healed their wounds, bypassing the need to simulate the actual medical AI job, pathfinding to medicine, and tending animations15. If a pawn is severely wounded, the Pawn\_HealthTracker continues to progress off-map in batched increments. If the disease severity reaches a lethal threshold during an off-screen update, the Notify\_PawnKilled event is triggered entirely within the abstract WorldPawns state, killing the pawn without them ever rendering on the player's screen20.

### **Implementation for the External Python Simulation**

The external Python process governing Chronicle must adopt a similarly decoupled tick architecture. Attempting to simulate the 140 off-screen NPCs at 60 Hz would consume unnecessary socket bandwidth and processor cycles.  
The Python simulation should operate on a macro-tick schedule, executing state updates perhaps once per second, or corresponding to one in-game hour. Travel across the Skyrim map should be calculated via a node-based graph. If an NPC requires three days to travel from Solitude to Riften, the Python simulation simply transitions their state object to "Traveling" and sets a future timestamp for their arrival. If an NPC is traveling, Python can roll against probability tables on a macro-tick to determine if they encounter bandits, suffer a delay, or acquire loot. The results of these probability rolls seamlessly adjust the abstract inventory and health pools, banking the data until the entity is required to physically manifest in the game world.

## **Coherence Guarantees: History, Position, and Inventory**

The most profound difficulty in a headless simulation architecture is ensuring that the state remains completely coherent between what the player physically experiences in the engine and what the external process mathematically calculates. If a caravan has been abstractly simulated as traveling for three days, it must spawn with a plausible inventory, a logical position, and a coherent history. This requires a strict delineation of what data is preserved, what is dynamically recomputed, and what is safely discarded.

### **The Master-Slave State Paradigm**

To guarantee absolute coherence, a rigid Master-Slave data architecture must be enforced. **The Python headless process is the Master. The Skyrim Actor is the Slave.** The Skyrim engine's saved variables, default outfits, and base statistics must be completely subjugated to the state provided by the Python payload.

| State Vector | Preservation Strategy | Computational Handling |
| :---- | :---- | :---- |
| **Historical Identity** | Fully Preserved | Python maintains all grudges, relationships, and memories. Applied via Faction Ranks upon cell load. |
| **Macro-Health** | Fully Preserved | Python tracks overall health percentage and permanent afflictions. Applied as a delta upon cell load. |
| **Inventory & Wealth** | Recomputed | Python tracks abstract wealth or categories. Translated into exact FormIDs upon cell load. |
| **Micro-Positioning** | Recomputed | Python tracks the macro-node (e.g., "Tavern"). Engine computes the exact X/Y/Z coordinate upon entry. |
| **Travel Pathing** | Discarded | Exact step-by-step coordinates between cities are irrelevant and discarded. Only arrival time matters. |

### **Preserving History and Health**

If an NPC was wounded in an off-screen bandit attack calculated probabilistically by Python, their abstract health pool is reduced. When the cell loads, the SKSE plugin must intercept this value and physically set the actor's health to the corresponding percentage.  
Similarly, if the NPC died off-screen, Python simply marks their abstract object as deceased. When the player eventually enters the cell where the corpse should reside, the SKSE plugin must instantly trigger the OnDeath event state or spawn the corpse directly, rather than spawning a living actor and subsequently killing them in front of the player, which would break immersion22.

### **Recomputing Inventory and Position**

A caravan that has traveled for three days will have consumed supplies and potentially acquired new trade goods. The Python process does not need to track the exact FormID of every apple or iron sword. Instead, it tracks abstract values such as "Food Level: Low" or "Trade Wealth: High." When the caravan arrives in a loaded cell, the handoff protocol reads these abstract values and dynamically generates an inventory utilizing Skyrim's leveled lists, ensuring the inventory is coherent with the journey's outcome.  
Positioning must also be dynamically recomputed. The Python process knows the NPC is in the "Bannered Mare" node, but it cannot know if a chair is currently occupied by the player. The engine must be trusted to recompute the exact micro-positioning using its internal NavMesh and AI Sandbox packages.

## **The Handoff Protocol: Transitioning Abstract to Active**

The critical point of failure in any headless simulation is the moment of materialization—the exact microsecond an abstract entity is summoned into the player's loaded 3D environment. If handled without strict architectural controls, this transition results in severe visual pop-in, coordinate clipping, AI pathing failures, and engine crashes.

### **Realization Mechanics in Dwarf Fortress and RimWorld**

In *Dwarf Fortress*, when an abstract historical figure—such as a forgotten beast or a traveling diplomat—is scheduled to enter the loaded fortress map, they must transition from a historical\_figure to a physical unit1. This transition involves generating the complex physical data structures required for the map. The engine reads the historical\_figure's abstract inventory and instantiates actual physical items and body parts25. If an entity becomes trapped in the transition queue, debugging tools like DFHack's fix/retrieve-units script are utilized to force the pending unit into the active map24. This reveals that the engine utilizes a highly controlled buffer queue to prevent simultaneous mass-spawning from crashing the application24.  
When *RimWorld* brings a pawn from the WorldPawns list to the active map, it utilizes a heavily structured spawning sequence26. The engine avoids using PawnGenerator.GenerateNewPawnInternal, as this method is strictly reserved for generating entirely new entities from procedural generation tables26. Instead, it takes the pre-existing serialized pawn from the WorldPawns container, removes it from that container, and invokes GenSpawn.Spawn26. This critical method registers the pawn with the local Map's ThingGrid, inserts it into the active PawnTracker, and initializes its MindState to begin processing active AI jobs through its ThinkNodes26.

### **The Skyrim Handoff: SKSE and the Creation Engine**

In the Creation Engine, transitioning a headless Python entity into a live Actor requires bypassing the severe limitations of Papyrus scripting. Papyrus is inherently slow, asynchronous, and strictly tied to framerate. Attempting to use Papyrus to synchronize a complex array of inventories, health values, and social flags at the exact moment a cell loads will invariably result in a noticeable delay—often manifesting as the "naked NPC" or "statue NPC" effect—before the scripts finish execution.  
The handoff protocol must be executed via an SKSE C++ plugin, preferably utilizing the CommonLibSSE-NG framework to ensure multi-version compatibility29.

#### **Step 1: Pre-Emptive Instantiation and The Invisible XMarker**

To avoid visual pop-in, the physical Actor must be placed in the world *before* they are rendered to the player's camera. The Creation Engine struggles immensely with MoveTo commands issued to unloaded cells, frequently resulting in corrupted coordinates, infinite loading screens, or hard crashes because the NavMesh is not loaded to accept the actor's placement31.  
The SKSE plugin should monitor the player's location. When the player enters a cell, the plugin intercepts the TESCellAttachEvent and identifies which of the simulated NPCs are scheduled to be in that cell according to the Python process33.  
The physical Actor reference in Skyrim is then moved to a pre-placed, invisible XMarker that is guaranteed to be on a valid NavMesh35. Alternatively, if the actor must spawn dynamically near the player without a fixed marker, they must spawn in a disabled state, utilizing DisableNoWait or initializing with abInitiallyDisabled \= True31.

#### **Step 2: Thread-Safe State Mutation via SKSETaskInterface**

The SKSE plugin requests the NPC's current state from the Python process. Once the payload is received, the C++ plugin must apply this state to the Actor.  
Crucially, **modifying an Actor's values from an asynchronous background thread will cause a hard Crash to Desktop (CTD)**. The Creation Engine is notoriously volatile regarding thread safety, and cross-thread mutations routinely trigger an EXCEPTION\_ACCESS\_VIOLATION at memory addresses such as 0198090 or 05E1F2237.  
To apply the Python state safely, the SKSE plugin must employ the SKSETaskInterface39. By invoking task-\>AddTask(), the C++ code queues a lambda function containing the state mutations. The engine will safely execute this lambda closure exclusively on the main thread during its next internal tick39. Within this safe, main-thread lambda, the plugin synchronizes the actor:

* Adding or removing inventory items to match the abstract Python state.  
* Applying damage or setting health percentages.  
* Modifying Papyrus variables or Faction ranks to reflect abstract social grudges.

#### **Step 3: AI Evaluation and Visual Realization**

Once the physical state is mutated on the main thread, the NPC's artificial intelligence must be forced to recognize its new reality. Calling the C++ equivalent of EvaluatePackage() forces the engine's BGSProcedureTree to discard old behaviors and immediately select a new AI package based on the newly injected state40. For instance, this forces an NPC to switch from a casual sandbox package to a hostile combat package if the Python state dictates they hold a severe grudge against a nearby entity.  
Finally, to mask the materialization process, the actor is brought into the visual field. If they were disabled, they are enabled via EnableNoWait. If they were enabled but placed out of sight, SetAlpha(0.0) can be used to make them entirely invisible, followed by a transition to SetAlpha(1.0) once their armor is fully loaded and their AI package has initialized36. This specific sequence prevents the visual jarring of a T-pose or an instantaneous teleportation artifact.

## **State Synchronization and Memory Management**

Coherence across play sessions requires exceptionally careful management of save files. The SKSE framework utilizes a serialization interface to create a .skse co-save file alongside the standard .ess save file, storing persistent data for C++ plugins42.

### **Avoiding Co-Save Bloat**

If the SKSE plugin attempts to serialize the entire relational and chronological state of 150 simulated NPCs into the .skse file every time the player initiates a quicksave, it will cause severe save bloat. This bloat results in elongated save times, engine freezing, and eventual save corruption44.  
The Python process must maintain its own localized database, such as SQLite or structured JSON, entirely independent of the Skyrim save file. The .skse co-save should only store a single string identifier: a Session ID or a Save Timestamp.  
When the player saves the game, SKSE broadcasts an Inter-Process Communication (IPC) message, triggered by the SKSEMessagingInterface::kSaveGame event, to the Python process. This message contains the save file name and the timestamp34. The Python process then commits its current memory state to its own database under that specific save name. When the player loads a save, SKSE sends the kPreLoadGame message with the corresponding save name, prompting the Python process to load the matching historical state into active memory34. This guarantees absolute coherence between the player's localized timeline and the external Python simulation timeline without introducing engine-breaking bloat.

## **Recommended Handoff Pattern for "Chronicle"**

Synthesizing the mechanics of *Dwarf Fortress* and *RimWorld* with the volatile constraints of the Creation Engine, the following architectural pipeline is recommended for the "Chronicle" transition from headless Python NPC to live Skyrim actor.

### **Phase 1: IPC via Named Pipes**

Because the Skyrim engine must rapidly synchronize data during a cell load without stalling the main thread, the IPC between the SKSE C++ plugin and the headless Python process must possess extremely low latency. Standard HTTP requests or socket connections introduce unacceptable network stack overhead.  
The recommended IPC protocol is Named Pipes47. Named pipes allow for direct, duplex memory-to-memory communication between a C++ client and a Python server hosted on the same local machine. This ensures that when the SKSE plugin requests an NPC's state during a loading screen, the response is resolved in microseconds, preventing Infinite Loading Screens (ILS)48.

### **Phase 2: Interception and Payload Retrieval**

> 1. The player approaches a cell boundary or triggers a fast travel event.  
> 2. The SKSE plugin intercepts the TESCellAttachEvent33.  
> 3. The plugin queries the Python process via the Named Pipe, requesting the state of all abstract entities currently residing in the target node.  
> 4. Python responds with a serialized payload containing the FormIDs of the NPCs, alongside their respective state payloads (Macro-Health, Abstract Inventory, Relationship Dispositions).

### **Phase 3: Pre-Instantiation Masking**

> 1. For each NPC returned in the payload, the SKSE plugin locates their base Actor reference.  
> 2. Before the rendering pipeline completes, the plugin utilizes SetAlpha(0.0) or DisableNoWait on the actor to ensure they are visually imperceptible to the player31.  
> 3. The actor is moved via MoveTo to a secure, invisible XMarker positioned on a validated NavMesh, circumventing the coordinate corruption associated with unloading cells35.

### **Phase 4: Thread-Safe State Injection**

> 1. The SKSE plugin bundles the Python state payload into a lambda function.  
> 2. The lambda is dispatched to the main thread via SKSETaskInterface::AddTask()32.  
> 3. On the main thread, the lambda executes, overwriting the engine's stored data with the Python master data. It clears the actor's inventory, injects the exact items specified by Python, applies health modifications, and sets the actor's rank in dynamically generated Papyrus Factions to govern combat and dialogue conditions.  
> 4. The lambda invokes EvaluatePackage() to force the BGSProcedureTree to recognize the newly injected reality40.

### **Phase 5: Visual Realization**

> 1. With the inventory populated, health set, and AI package running, the actor is completely coherent.  
> 2. A secondary task triggers SetAlpha(1.0) or EnableNoWait, rendering the actor into the world31.  
> 3. Because the actor was moved to a valid XMarker on the NavMesh and their AI is already evaluating, they will appear to seamlessly engage with their environment rather than spawning jarringly.

### **Phase 6: The Departure Protocol (Cell Detach)**

Coherence must operate bidirectionally. When the player leaves a cell, the live engine actor must be handed back to the abstract Python simulation.

> 1. The SKSE plugin detects a TESCellDetachEvent.  
> 2. A reverse-sync lambda is queued via the SKSETaskInterface.  
> 3. The main thread reads the actor's final physical state, noting exact health percentages, surviving inventory, and newly acquired grudges from combat events.  
> 4. This delta is sent back over the Named Pipe to the Python process.  
> 5. Python consumes the payload, updates its headless objects, and resumes probabilistic macro-tick simulation for that entity.  
> 6. The physical Actor object in the Skyrim engine is disabled and suspended in vanilla stasis, entirely ignored until the next cell attach event.

## **Conclusion**

The successful implementation of the "Chronicle" mod relies on recognizing and navigating the Creation Engine's architectural limitations. Treating the Skyrim engine as a mere visual client—rather than a canonical database—is the only viable methodology for large-scale social simulation. By adopting *Dwarf Fortress*'s strict separation of instantiated units and abstract historical figures, and emulating *RimWorld*'s mothballing and garbage collection mechanics for off-screen pawns, Chronicle can achieve a massive scale of simulation without CPU degradation.  
Absolute state coherence requires a Master-Slave hierarchy where the Python headless process dictates reality. Utilizing Named Pipes for microsecond IPC, bypassing the .skse co-save to prevent save bloat, and exclusively employing the SKSETaskInterface to execute thread-safe state mutations will guarantee a seamless, invisible handoff from an abstract data point to a living, breathing entity within the game world.

#### **Works cited**

> 1. Historical figure \- Dwarf Fortress Wiki, [https://dwarffortresswiki.org/index.php/Historical\_figure](https://dwarffortresswiki.org/index.php/Historical_figure)  
> 2. DFHack Lua API Reference, [https://docs.dfhack.org/en/stable/docs/dev/Lua%20API.html](https://docs.dfhack.org/en/stable/docs/dev/Lua%20API.html)  
> 3. DFHack Documentation, [https://media.readthedocs.org/pdf/dfhack/latest/dfhack.pdf](https://media.readthedocs.org/pdf/dfhack/latest/dfhack.pdf)  
> 4. Development changelog — DFHack 53.16-r1 documentation, [https://docs.dfhack.org/en/stable/docs/NEWS-dev.html](https://docs.dfhack.org/en/stable/docs/NEWS-dev.html)  
> 5. DFHack/dfhack 53.10-r2 on GitHub \- NewReleases.io, [https://newreleases.io/project/github/DFHack/dfhack/release/53.10-r2](https://newreleases.io/project/github/DFHack/dfhack/release/53.10-r2)  
> 6. How the simulation of history in DF actually works? : r/dwarffortress, [https://www.reddit.com/r/dwarffortress/comments/11sgmrm/how\_the\_simulation\_of\_history\_in\_df\_actually\_works/](https://www.reddit.com/r/dwarffortress/comments/11sgmrm/how_the_simulation_of_history_in_df_actually_works/)  
> 7. DFHack \- Dwarf Fortress Modding Engine \- Steam Community, [https://steamcommunity.com/app/2346660/allnews/](https://steamcommunity.com/app/2346660/allnews/)  
> 8. please help me with this bug report :: RimWorld General Discussions, [https://steamcommunity.com/app/294100/discussions/0/1744483505473309718/](https://steamcommunity.com/app/294100/discussions/0/1744483505473309718/)  
> 9. Performance issues in longterm low colonist colony : r/RimWorld, [https://www.reddit.com/r/RimWorld/comments/1peh78p/performance\_issues\_in\_longterm\_low\_colonist\_colony/](https://www.reddit.com/r/RimWorld/comments/1peh78p/performance_issues_in_longterm_low_colonist_colony/)  
> 10. Infinite spawns on caravan map? Use dev mode to delete it. \- Reddit, [https://www.reddit.com/r/RimWorld/comments/1lkc4dg/infinite\_spawns\_on\_caravan\_map\_use\_dev\_mode\_to/](https://www.reddit.com/r/RimWorld/comments/1lkc4dg/infinite_spawns_on_caravan_map_use_dev_mode_to/)  
> 11. New to the game and modding. What does this bug message mean?, [https://www.reddit.com/r/RimWorld/comments/8cnynq/new\_to\_the\_game\_and\_modding\_what\_does\_this\_bug/](https://www.reddit.com/r/RimWorld/comments/8cnynq/new_to_the_game_and_modding_what_does_this_bug/)  
> 12. Rimworld output log published using HugsLib · GitHub, [https://gist.github.com/HugsLibRecordKeeper/4e21393de21a6911e1a8d9a4fb63066e](https://gist.github.com/HugsLibRecordKeeper/4e21393de21a6911e1a8d9a4fb63066e)  
> 13. 2012 Log \- Bay 12 Games: Dwarf Fortress, [http://www.bay12games.com/dwarves/dev\_2012.html](http://www.bay12games.com/dwarves/dev_2012.html)  
> 14. World activities \- Dwarf Fortress Wiki, [https://dwarffortresswiki.org/index.php/World\_activities](https://dwarffortresswiki.org/index.php/World_activities)  
> 15. Rimworld output log published using HugsLib · GitHub, [https://gist.github.com/HugsLibRecordKeeper/1eaed21316484af6caa7e009e89677bd](https://gist.github.com/HugsLibRecordKeeper/1eaed21316484af6caa7e009e89677bd)  
> 16. Rimworld output log published using HugsLib · GitHub, [https://gist.github.com/HugsLibRecordKeeper/64a9cb05a0b95a625dca4b97752eeb33](https://gist.github.com/HugsLibRecordKeeper/64a9cb05a0b95a625dca4b97752eeb33)  
> 17. Rimworld Late Game Lag from WorldTick Pawns \- Reddit, [https://www.reddit.com/r/RimWorld/comments/17xw3ur/rimworld\_late\_game\_lag\_from\_worldtick\_pawns/](https://www.reddit.com/r/RimWorld/comments/17xw3ur/rimworld_late_game_lag_from_worldtick_pawns/)  
> 18. RW-Decompile/Verse/Pawn\_HealthTracker.cs at master \- GitHub, [https://github.com/josh-m/RW-Decompile/blob/master/Verse/Pawn\_HealthTracker.cs](https://github.com/josh-m/RW-Decompile/blob/master/Verse/Pawn_HealthTracker.cs)  
> 19. Steam-værksted::Performance \- Slower Pawn Tick Rate, [https://steamcommunity.com/sharedfiles/filedetails/?l=danish\&id=3524116050](https://steamcommunity.com/sharedfiles/filedetails/?l=danish&id=3524116050)  
> 20. Something is preventing my colonists from dying, need some help., [https://steamcommunity.com/app/294100/discussions/0/4034727620344784530/](https://steamcommunity.com/app/294100/discussions/0/4034727620344784530/)  
> 21. Can someone help me with this error please? :: RimWorld 일반 토론, [https://steamcommunity.com/app/294100/discussions/0/2145343824304236854/?l=koreana](https://steamcommunity.com/app/294100/discussions/0/2145343824304236854/?l=koreana)  
> 22. \[Creation Kit\] How to make miscellaneous quest fail/disappear if an, [https://www.reddit.com/r/skyrimmods/comments/zpqwzn/creation\_kit\_how\_to\_make\_miscellaneous\_quest/](https://www.reddit.com/r/skyrimmods/comments/zpqwzn/creation_kit_how_to_make_miscellaneous_quest/)  
> 23. Timer for a Death Script, plus other things. : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/xrne7u/timer\_for\_a\_death\_script\_plus\_other\_things/](https://www.reddit.com/r/skyrimmods/comments/xrne7u/timer_for_a_death_script_plus_other_things/)  
> 24. fix/retrieve-units \- DFHack's documentation\!, [https://docs.dfhack.org/en/latest/docs/tools/fix/retrieve-units.html](https://docs.dfhack.org/en/latest/docs/tools/fix/retrieve-units.html)  
> 25. modtools/create-unit — DFHack 52.03-r1 documentation, [https://docs.dfhack.org/en/52.03-r1/docs/tools/modtools/create-unit.html](https://docs.dfhack.org/en/52.03-r1/docs/tools/modtools/create-unit.html)  
> 26. RimWorld pawn generation code? \- Reddit, [https://www.reddit.com/r/RimWorld/comments/g2ofbg/rimworld\_pawn\_generation\_code/](https://www.reddit.com/r/RimWorld/comments/g2ofbg/rimworld_pawn_generation_code/)  
> 27. How to spawn a pawn? : r/RimWorld \- Reddit, [https://www.reddit.com/r/RimWorld/comments/qijamb/how\_to\_spawn\_a\_pawn/](https://www.reddit.com/r/RimWorld/comments/qijamb/how_to_spawn_a_pawn/)  
> 28. Help Identifying Error Issue : r/RimWorld \- Reddit, [https://www.reddit.com/r/RimWorld/comments/1c2nwm6/help\_identifying\_error\_issue/](https://www.reddit.com/r/RimWorld/comments/1c2nwm6/help_identifying_error_issue/)  
> 29. alandtse/CommonLibSSE-NG \- GitHub, [https://github.com/alandtse/CommonLibSSE-NG](https://github.com/alandtse/CommonLibSSE-NG)  
> 30. CommonLibSSE NG: CommonLibSSE NG ("Next Generation"), [https://ng.commonlib.dev/](https://ng.commonlib.dev/)  
> 31. Cant make Actor to run package and PlaceActorAtMe behavior, [https://www.afkmods.com/index.php?/topic/5560-skyrim-modding-help-cant-make-actor-to-run-package-and-placeactoratme-behavior/](https://www.afkmods.com/index.php?/topic/5560-skyrim-modding-help-cant-make-actor-to-run-package-and-placeactoratme-behavior/)  
> 32. Make LoadInteriorRefList async without crash using SKSE Task, [https://git.hallada.net/thallada/BazaarRealmPlugin/commit/b3dd9e240d8b2f5a9947bf603078a9635573c9c8](https://git.hallada.net/thallada/BazaarRealmPlugin/commit/b3dd9e240d8b2f5a9947bf603078a9635573c9c8)  
> 33. What does Skyrim Script Extender actually do? Why didn't SE, [https://www.reddit.com/r/skyrimmods/comments/1chqz2k/what\_does\_skyrim\_script\_extender\_actually\_do\_why/](https://www.reddit.com/r/skyrimmods/comments/1chqz2k/what_does_skyrim_script_extender_actually_do_why/)  
> 34. SKSE System Messages \- Skyrim.dev, [https://skyrim.dev/skse/system-messages](https://skyrim.dev/skse/system-messages)  
> 35. \[Question\] Console Commands for a Noob? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/32iz6x/question\_console\_commands\_for\_a\_noob/](https://www.reddit.com/r/skyrimmods/comments/32iz6x/question_console_commands_for_a_noob/)  
> 36. \[Programming Question\] How to get Actors to properly reset. \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/48w9ay/programming\_question\_how\_to\_get\_actors\_to/](https://www.reddit.com/r/skyrimmods/comments/48w9ay/programming_question_how_to_get_actors_to/)  
> 37. SKSE Related CTD at Main Menu : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/197leo5/skse\_related\_ctd\_at\_main\_menu/](https://www.reddit.com/r/skyrimmods/comments/197leo5/skse_related_ctd_at_main_menu/)  
> 38. How do I solve this crash log (SkyrimSE.exe+5E1F22) on ... \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/18drn73/how\_do\_i\_solve\_this\_crash\_log\_skyrimseexe5e1f22/](https://www.reddit.com/r/skyrimmods/comments/18drn73/how_do_i_solve_this_crash_log_skyrimseexe5e1f22/)  
> 39. CommonLibSSE Task Interface Implementation \- GitHub Gist, [https://gist.github.com/Ryan-rsm-McKenzie/90e9e3bde1584fcdac0c9feb1e352586](https://gist.github.com/Ryan-rsm-McKenzie/90e9e3bde1584fcdac0c9feb1e352586)  
> 40. EvaluatePackage function \- Actor script | Skyrim SE \- Papyrus Index, [https://papyrus.bellcube.dev/skyrimse/script/actor/function/evaluatepackage/](https://papyrus.bellcube.dev/skyrimse/script/actor/function/evaluatepackage/)  
> 41. SetAlpha function \- Actor script | Skyrim SE \- The Papyrus Index, [https://papyrus.bellcube.dev/skyrimse/script/actor/function/setalpha/](https://papyrus.bellcube.dev/skyrimse/script/actor/function/setalpha/)  
> 42. Guide :: SKSE Installation \- Steam Community, [https://steamcommunity.com/sharedfiles/filedetails/?id=839312113](https://steamcommunity.com/sharedfiles/filedetails/?id=839312113)  
> 43. What are the .skse files created alongside my saves for? \- Arqade, [https://gaming.stackexchange.com/questions/181335/what-are-the-skse-files-created-alongside-my-saves-for](https://gaming.stackexchange.com/questions/181335/what-are-the-skse-files-created-alongside-my-saves-for)  
> 44. SKSE Co-Save Cleaning? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/a2fr6m/skse\_cosave\_cleaning/](https://www.reddit.com/r/skyrimmods/comments/a2fr6m/skse_cosave_cleaning/)  
> 45. My SKSE Co-save is bloating in unusual increments due to ... \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1k1j6am/my\_skse\_cosave\_is\_bloating\_in\_unusual\_increments/](https://www.reddit.com/r/skyrimmods/comments/1k1j6am/my_skse_cosave_is_bloating_in_unusual_increments/)  
> 46. I made a mod which make SKSE cosaves save up-to 150 times faster, [https://www.reddit.com/r/skyrimmods/comments/1os2hsd/i\_made\_a\_mod\_which\_make\_skse\_cosaves\_save\_upto/](https://www.reddit.com/r/skyrimmods/comments/1os2hsd/i_made_a_mod_which_make_skse_cosaves_save_upto/)  
> 47. Implementation Of InterProcessCommunication \- NamedPipes, [https://www.c-sharpcorner.com/article/implementation-of-interprocesscommunication-namedpipes-using-cpp-and-c-sharp/](https://www.c-sharpcorner.com/article/implementation-of-interprocesscommunication-namedpipes-using-cpp-and-c-sharp/)  
> 48. High-Performance Local IPC: C\# to Python via Windows Named Pipes, [https://www.youtube.com/watch?v=0qFyiLS1BZA](https://www.youtube.com/watch?v=0qFyiLS1BZA)  
> 49. IPC between Python and C \- YouTube, [https://www.youtube.com/watch?v=6CI55c2cwRU](https://www.youtube.com/watch?v=6CI55c2cwRU)  
> 50. r/skyrimmods on Reddit: \[Help\] ILS on Fast Travelling, Freezes on Wait, [https://www.reddit.com/r/skyrimmods/comments/urp8y2/help\_ils\_on\_fast\_travelling\_freezes\_on\_wait/](https://www.reddit.com/r/skyrimmods/comments/urp8y2/help_ils_on_fast_travelling_freezes_on_wait/)