# **Architectural Analysis of Skyrim's Radiant Machinery, Autonomous GM Agents, and Surface-Layer Injection Infrastructure**

The evolution of procedural quest generation and reactive world state in *The Elder Scrolls V: Skyrim* represents a continuous attempt to bridge static engine architecture with dynamic narrative intent. While Bethesda’s native engine machinery provided a robust framework for procedural reference binding, its reliance on fixed templates established a structural ceiling for narrative depth1. Subsequent modding efforts have progressively pushed these boundaries, culminating in modern Native Script Extender (SKSE) architectures that bypass native engine bottlenecks to orchestrate fully dynamic actor behavior, macro-faction politics, and runtime UI injection2.  
Evaluating the mechanics of Skyrim's native Radiant Story engine, the historical lineage of quest-generation mods, cutting-edge autonomous agent frameworks, dynamic faction response architectures, and the UI surfacing pipelines required to present generated content provides a clear technical foundation for external Game Master (GM) agents2.

## **1\. Bethesda's Radiant Story Engine: Internals, Execution Mechanics, and Hard Architectural Limits**

### **Story Manager Events, Quest Nodes, and Condition Trees**

Skyrim's native procedural engine, known as Radiant Story, operates through a centralized event-driven dispatcher called the Story Manager (BGSStoryManager)6. The Story Manager listens for specific gameplay triggers—termed Story Manager Events—which range from cell changes (ScriptEventLocation), item acquisitions, and actor deaths to location clearance and generic script-sent signals (LocationDiscovery, ActorKill)6.  
When an event fires, the Story Manager evaluates a hierarchical node structure6. This hierarchy consists primarily of Branch Nodes (BGSStoryManagerBranchNode) and Quest Nodes (BGSStoryManagerQuestNode)6. Nodes can be configured as "Stack" (evaluating children sequentially until one succeeds) or "Random" (selecting among valid children based on weighted probabilities)6. Attached to each node and individual quest form is a tree of engine conditions (TESCondition). These conditions perform real-time checks against game state, evaluating variables such as GetStage, GetInCell, GetFactionRank, and GetVMQuestVariable. If an event matches a node's condition tree, the Story Manager attempts to instantiate the associated quest object (TESQuest)6.

### **Reference Aliases, Alias Fill Conditions, and World Interactions**

The core mechanism of Radiant Story is its Reference Alias (BGSRefAlias) system6. A quest in Skyrim is an abstract container of logic, objectives, and scripts; it does not hardcode specific world entities, but instead defines symbolic slots known as aliases (such as "QuestGiver", "TargetLocation", or "BanditLeader")6. When a quest is selected by the Story Manager, it executes an alias-filling pass6. Aliases are populated through distinct fill conditions defined in the Creation Kit:

* **Specific Reference**: Hardcoded FormID binding to a static world reference6.  
* **Unique Actor**: Resolves to a unique persistent actor in the world database6.  
* **Find Matching Reference**: Searches loaded or unloaded cells based on spatial proximity, cell flags, and keyword matching (such as locating an uncleared dungeon tagged LocTypeDungeon within a specific distance radius from the player)6.  
* **Create In**: Instantiates a new base object form directly into a target container or location reference6.

The World Interactions (WI) system is a specialized subset of Radiant Story managed by a master script (WIMain)6. It handles ambient events—such as courier deliveries, road encounters, and thug attacks—by listening for location transitions and periodically evaluating event nodes against player status parameters, including current hold bounty and completed quest counts6.

### **Runtime Limits and SKSE Event Injection Boundaries**

Despite its flexibility, the vanilla Radiant Story architecture faces severe operational boundaries:

* **Static Template Reliance**: Every radiant quest must exist as a pre-authored TESQuest record compiled into an .esp/.esm plugin prior to runtime1. The engine cannot synthesize new quest structures, script logic, or conditional branches on the fly1.  
* **Form Creation Restrictions**: Game engines enforce strict memory management regarding runtime form creation. Neither Papyrus scripts nor standard SKSE plugins can construct arbitrary, serialized TESQuest forms in memory at runtime without causing save-game corruption or FormID index exhaustion6.  
* **Alias Fill Failures**: If a single mandatory alias fails its fill conditions (such as no dungeon matching the exact keyword criteria existing within spatial constraints), the entire quest fails to start, forcing the Story Manager to roll back the event6.  
* **SKSE Event Limits**: While SKSE allows developers to send custom script events to trigger existing Story Manager nodes, it cannot alter the underlying compiled structure of the quest tree dynamically6. Consequently, dynamic quest generation within native limits is strictly a problem of combinatorial alias matching across pre-existing templates1.

## **2\. The Quest-Generation Modding Lineage and the Frontier of Autonomous AI Orchestration**

### **The Template Era: Notice Board, Missives, and Geographic Scoping**

To mitigate vanilla radiant repetition, early modding efforts focused on restructuring how radiant quests were handed to the player8. *The Notice Board* introduced physical board objects into hold capitals, aggregating quest notices populated via regional cell checks8. However, it frequently assigned cross-province objectives that broke immersion, such as a Solitude blacksmith requesting ore located in Riften8.  
*Missives* refined this model by introducing regional target scoping8. Designed with strict geographical hierarchies, *Missives* evaluates the player's current hold and restricts quest target allocation to three distinct radii: local hold objectives confined entirely to current hold boundaries, neighboring hold objectives spanning adjacent territorial borders, and global province-wide contracts reserved exclusively for high-tier quest types8.  
*Missives* functions by maintaining a pre-authored grid of template quests7. Upon board interaction, a Papyrus script checks local cell keywords, selects an inactive quest instance from the pool, populates its location/actor aliases within the enforced geographic boundary, and attaches generic text notes to the board7. Mod extensions such as *Missives \- Voice and Quest Expansion* spliced vanilla audio lines to mask the generic nature of these interactions, yet the underlying mechanic remained strictly template-bound7.

### **Deep-Dive Architecture Profile: IntelEngine and SkyrimNet**

The current state of the art in dynamic content generation is represented by *IntelEngine*, an autonomous C++ SKSE plugin built specifically as an autonomy and task execution framework for *SkyrimNet*2. *SkyrimNet* provides the core infrastructure: a single native SKSE plugin running asynchronously on background worker threads, executing C++ direct memory reads to feed game state into Large Language Models (LLMs) via OpenAI-compatible API endpoints3. *IntelEngine* operates on top of *SkyrimNet*, converting conversational AI outputs into physical, persistent world state interventions2.

| Architectural Layer | IntelEngine Implementation / Engine Interface | Technical Function & Performance Characteristics |
| :---- | :---- | :---- |
| **Indexing Engine** | Native C++ memory scanner executed on save load2. | Builds a dynamic spatial and entity index of every actor, door, cell, Z-axis level, and furniture item across the load order without hardcoded lists2. |
| **Story Engine (DM)** | Background C++ tick thread executing every 3 in-game hours2. | Evaluates player history, local memory arrays, spatial proximity, and time state to trigger grounded quest interventions2. |
| **Political DM** | Autonomous macro-simulation thread ticking every 6 in-game hours2. | Simulates 9 active political factions; tracks morale, army strength, trade deals, espionage, assassinations, and war declarations off-screen2. |
| **Task State Machine** | Dual-persistence engine using C++ runtime arrays and PapyrusUtil (StorageUtil)2. | Governs slot-based actor state machines; manages 3-tiered speed packages, travel schedules, and arrival/departure windows using native distance calculation2. |
| **Action Registration** | Direct integration into *SkyrimNet* action YAML manifest2. | Registers 10 core AI actions (Fetch, Escort, Travel, Deliver, Ambush, Rescue) with strict eligibility pre-checks evaluated before model generation2. |
| **Audio & Presentation** | Direct C++ routing into Skyrim's native audio engine (X3DAudio)11. | Voices generated dialogue using TTS, applying real-time spatial acoustic reverb, dungeon occlusion, and ducking native to the game cell11. |

*IntelEngine* constructs playable dynamic quests without relying on traditional Creation Kit quest templates2. When the Story Engine determines a narrative intervention is required, it initiates a multi-stage execution pipeline2:

> 1. **Entity Selection and Pre-Placement**: The C++ indexer identifies a target actor or dungeon cell2. In rescue quests, the target NPC is moved off-screen deep into the specified dungeon, physically bound to prisoner furniture forms (AP\_SittingChair or bleedout state) prior to player cell load2.  
> 2. **Actor Dispatch and Physical Travel**: Rather than spawning quests statically on a board, *IntelEngine* dispatches an NPC to seek out the player on foot2. The C++ engine calculates travel distance against game time, initiating the actor's departure early enough to ensure arrival at a calculated meeting point2. If spatial pathing fails in unloaded cells, a recovery pipeline executes: **Soft Recovery** (AI package re-evaluation) ![][image1] **Progressive Teleport** (incremental spatial nudging) ![][image1] **Safety Timeout** (force-completion to prevent soft-locks)2.  
> 3. **Tactical and Political Battle Spawns**: When faction standing reaches thresholds (![][image2]), or when the Political DM resolves an escalating war state, the engine triggers physical battles2. In player-present skirmishes, *IntelEngine* injects 5 sequential combat waves consisting of 22 active soldiers per side (44 total actors simultaneously engaged in combat), directly updating global faction morale and regional territory ownership upon battle resolution2.

### **Dynamic Quest Execution vs. Unstructured LLM Experiments**

While frameworks like *IntelEngine*, *CHIM*, and *Mantella* provide dynamic interactions, community evaluation highlights significant structural differences between conversational "improv" and robust quest design10. Unstructured LLM integrations frequently suffer from a complete disconnect between dialogue and engine mechanics12. If an LLM-driven NPC verbally agrees to resolve a dispute peacefully, the underlying vanilla quest engine remains unaware of the dialogue transaction12. The quest stage does not advance, map markers persist indefinitely, and players are forced to execute debug console commands (SetStage) to force completion12.  
To overcome this structural failure mode, systems must enforce structural symbiosis2. Symbolic simulation state must govern engine logic (quest flags, inventory items, objective markers), while the LLM layer is restricted to narrative framing, dialogue generation, and contextual action dispatch2.

## **3\. Dynamic Faction Systems and Macro-Simulation State Surfacing**

### **Open Civil War and Civil War Overhaul: Board Games, Super-Moves, and Story Manager Bottlenecks**

Attempts to turn Skyrim's static Civil War into a dynamic faction simulation have revealed severe engine constraints6. *Open Civil War* (OCW) restores Bethesda's cut city sieges (Markarth, Riften, Falkreath, etc.) and overlays an autonomous tabletop campaign system onto the war map6.  
OCW implements three operational modes:

* **Standard**: Vanilla-like progression with added city siege instances6.  
* **Fortuna**: The macro-simulation runs automatically in the background using hidden battle odds15.  
* **Wargamer**: A fully exposed turn-based strategy game where the player directly commands military units across hold borders6.

Under the hood, OCW tracks hold garrison strength using a greedy algorithmic model15. Factions execute tactical moves to secure border forts6. When an army accumulates sufficient strength, it triggers a **Super-Move**—a high-stakes campaign targeting an entire hold capital6. If resolved off-screen, a dice-roll algorithm calculates the winner based on resource ratios6. If resolved on-screen, the mod instantiates a pitched city assault quest6.  
The primary failure mode of OCW and its predecessor, *Civil War Overhaul* (CWO), stems directly from **Story Manager Bottlenecks**6. Swapping ownership of a hold requires reallocating city garrisons, changing Jarls, swapping crime factions, and shifting hundreds of linked world references6. The native engine executes these transitions via Story Manager events (ScriptEventLocation)6. When heavily modded save games experience high Papyrus script latency, the Story Manager drops event updates6. This results in broken game states: hostile guards spawning in friendly holds, missing Jarl dialogue options, broken quest aliases, and permanent save lockups6.

### **Organic Factions and Faction Warfare: Resource Pools and Progression Vectors**

In contrast to OCW's quest-driven transitions, *Organic Factions* completely bypasses Skyrim's Story Manager5. It operates as an independent, script-driven macro-simulation built on isolated resource loops5.  
An "Organic Faction" consists of three core components:

> 1. **Faction Resource Pool**: An abstract numerical counter incremented over real-time intervals, representing manpower, wealth, and territory5.  
> 2. **Actor Progression Vectors**: As resource pools grow, the mod executes background Papyrus scripts that dynamically scale member actor levels, apply higher-tier perk forms, and modify actor base stats without altering base ESM records5.  
> 3. **Territorial Expansion Spawns**: Upon reaching specific resource thresholds, the faction claims physical locations by spawning strategic actor groups (patrols, camp guards, raiding parties)5.

If the player raids an Organic Faction's stronghold and slays its commander, the resource pool collapses, forcing the faction to retreat, reduce patrol density, and begin rebuilding manpower over subsequent game days5. Because *Organic Factions* manages its state entirely within standalone arrays and direct actor references, it avoids triggering massive Story Manager cascading updates, proving far more resilient against script fatigue5. *Faction Warfare* implements a similar dynamic by tracking a global player-faction reputation matrix, triggering localized reinforcement calls or delayed hitman spawns that intercept the player in exterior cells whenever negative standing thresholds are crossed2.

### **Surfacing Faction State: World Edits, Spawns, and Script Safety**

To ensure stability when surfacing macro-faction changes to the player, external directors must carefully select their presentation vector based on engine risk profiles:

* **Direct Worldspace Edits (High Risk)**: Modifying persistent location forms, altering cell navmesh dynamically, or forcing hold ownership flips mid-game generates persistent reference corruption and high risk of save bloat6.  
* **Dynamic Actor Spawns (Medium Risk)**: Spawning combatants or patrols dynamically via SKSE or native functions (PlaceAtMe) is functionally safe provided the spawned forms are explicitly tagged as temporary (DeleteWhenDone) to avoid inflating the co-save database2.  
* **Dialogue and Reputation Overlays (Low Risk)**: Surfacing political moves through conversational awareness, vendor price shifts, or guard remark conditions requires zero physical world alterations, presenting narrative consequences cleanly without engine strain10.

## **4\. Dialogue, Journal, and UI Surfacing Systems**

### **Runtime Journal Manipulation via PO3 Papyrus Extender**

For dynamic GM interventions to feel native, generated content must seamlessly populate the player’s quest journal11. Vanilla Skyrim limits quest objective text to pre-compiled strings stored within the TESQuest form. Modifying these descriptions dynamically required breakthroughs in SKSE reverse-engineering4.  
The definitive utility for runtime journal manipulation is **powerofthree's Papyrus Extender** (PO3\_SKSEFunctions)4. It exposes a native C++ function directly to Papyrus: PO3\_SKSEFunctions.SetObjectiveText(Quest akQuest, string asText, int aiIndex)4. This function writes arbitrary text strings directly into the runtime memory address of the specified quest objective index (aiIndex)4. When the journal menu updates, it reads the modified memory space, rendering customized text strings without modifying the underlying plugin file4.

### **Map Marker Binding, Objective Registration, and Quest Reflection**

A complete dynamic quest surfacing pipeline integrates three distinct native hooks:

> 1. **Objective Registration**: A pre-allocated pool of generic framework quests (containing blank, pre-indexed objective slots ![][image3]) is compiled into the mod’s ESP. At runtime, the GM engine claims an unused quest instance, uses SetObjectiveText to write context-specific instructions, and executes SetObjectiveDisplayed() to push the objective to the HUD4.  
> 2. **Map Marker Assignment**: Spatial markers are bound dynamically by pointing reference aliases to target coordinate markers or persistent actors using SetTargetObject() via standard Papyrus or SKSE alias manipulation.  
> 3. **Engine Reflection**: Advanced frameworks read back this state11. *SkyrimNet* executes native C++ reflection against Skyrim's underlying QuestJournalManager memory structure11. This allows NPCs to inspect the exact string text, quest title, and objective state currently displayed in the player’s log, enabling conversational dialogue partners to react organically to active jobs11.

### **UI Presentation Layers: Scaleform, SKSE Menu Framework, and Web-Overlay Bridges**

When presenting complex simulation data that exceeds the capabilities of standard Skyrim message boxes or journal entries, modern modding leverages dedicated SKSE UI frameworks2.

| UI Surfacing Technology | Underlying Tech Stack | Integration Mechanism & Architectural Capabilities |
| :---- | :---- | :---- |
| **Vanilla Scaleform / SkyUI** | Adobe Flash (ActionScript 2.0 / GFx)20. | Invoked via Papyrus UI.InvokeStringA("Journal Menu", ...)20. Highly rigid, limited string bandwidth, prone to memory leaks if over-polled. |
| **SKSE Menu Framework** | Dear ImGui / C++ Native Hooks21. | Renders custom hardware-accelerated overlay menus directly within the game viewport21. Zero Papyrus overhead, ideal for real-time telemetry and debug log analysis21. |
| **PrismaUI / Web Overlays** | Chromium Embedded Framework (CEF) / React2. | Runs an in-game React web UI dashboard (Shift+7 overlay)2. C++ bridge converts Papyrus quest properties into JSON snapshots (nlohmann::json) via mutex-guarded std::unordered\_map channels2. |

## **5\. Player Perception, Community Reception, and Director Trust Hazards**

### **The Blandness Vector: Structural Failure Modes of Template Quests**

Community analysis across modding channels reveals explicit reasons why native radiant content induces acute player fatigue1:

* **Zero Provenance and Absence of Cause**: Vanilla radiant quests select targets based purely on spatial distance and keyword eligibility, such as "Kill bandit leader at \[RANDOM DUNGEON\]"1. The target actor possesses no prior relationship with the player, no historical interaction, and no belief state justifying their hostility1.  
* **Lack of Narrative Consequence**: Completing a vanilla radiant task alters no world state beyond awarding a gold stipend1. Slaying a bandit chief does not reduce regional bandit raid frequencies, nor does becoming Guildmaster unlock functional structural authority over guild operations1.  
* **Template Transparency**: Players instantly recognize the fill-in-the-blank nature of native quest notes1. Once the underlying syntax is exposed, immersion collapses, and the quest is reduced to a mechanical checklist item1.

To solve the blandness vector, generated content must feature **provenance for free**2. A quest asking the player to confront an NPC is engaging only when anchored to established simulation state—such as a local merchant hiring mercenaries because rumors mutated to make them believe the player killed their spouse2.

### **Player Trust Hazards: Stacking, Invisible Variables, and Teleportation Jank**

When introducing a dynamic GM agent or AI director, maintaining player trust requires strict adherence to predictable, transparent world rules2:

* **Invisible Stacking and Staked Odds**: A director that secretly stacks spatial variables—such as spawning an enemy squad directly behind the player's back simply because the pacing curve demands intensity—reads instantly as unfair manipulation2. Director interventions must obey **expected randomness** and maintain physical world continuity; interventions must originate from logical in-world vectors, such as soldiers marching from a nearby fort, rather than materialized ambient spawns2.  
* **Teleportation Jank and Spatial Pops**: In autonomous actor frameworks like *IntelEngine*, relying on aggressive forced teleports to make NPCs keep appointments disrupts suspension of disbelief2. If an NPC vanishes mid-sentence or materializes directly inside a small interior cell without opening a door, the illusion of a living world breaks2. Systems must enforce progressive spatial recovery: natural pathing progressing to off-screen cell nudging, with safety timeouts executed strictly outside the player's frustum2.  
* **Unchecked Cooldowns and Behavioral Overrides**: Spawning player-seeking interactions too frequently creates extreme narrative fatigue22. Community guidance for autonomy mods explicitly mandates enforcing strict global cooldowns, such as minimum 24-hour in-game buffers for player-seeking events, and toggling off conflicting package overrides to prevent uncoordinated AI instability22.

## **6\. Synthesis: Architectural Blueprint for an External GM Agent Pipeline**

### **Input-to-Presentation Execution Pipeline**

To construct an external GM agent that sits atop an underlying social, belief, and faction simulation (such as Chronicle) and interfaces cleanly with Skyrim, the system must implement a strict four-stage execution pipeline:

> 1. **Input Stage (External Simulation State)**: The external engine maintains the absolute source of truth regarding social topology, including actor belief graphs, rumor mutation histories, grudge intensity vectors, and macro-faction resource pools2.  
> 2. **Recognition Stage (Story-Sifting Layer)**: A deterministic sifting module continually parses the social graph, searching for interesting structural configurations—such as an actor with high grudge intensity, sufficient wealth, and an erroneous belief identifying the player as the source of their misfortune2.  
> 3. **Intervention Stage (GM Decision Layer)**: The GM agent accepts the sifted situation and authors a targeted physical intervention2. Rather than inventing arbitrary quests, the intervention maps directly to available engine verbs: dispatching an ambush party, scheduling a secret meeting, or offering a context-anchored contract2.  
> 4. **Presentation Stage (SKSE Surface Injection)**: The intervention is passed down to the native SKSE framework2. Objective strings are written to memory via PO3\_SKSEFunctions.SetObjectiveText, physical actors are placed using off-screen cell packages, and dynamic TTS dialogue lines are rendered through native C++ spatial audio channels2.

### **Structural Integration and Engine Boundaries**

To deploy this architecture without destabilizing the underlying game engine or breaking player trust, the integration layer must observe four mandatory technical constraints:

* **Separation of State and Presentation**: The external simulation must remain the sole arbiter of truth2. The Skyrim engine acts strictly as an execution view and interaction surface2.  
* **Story Manager Bypass for Macro-State**: Macro-faction tracking, reputation matrices, and resource counters must bypass Bethesda's fragile Story Manager event tree entirely, operating instead via standalone C++ backend structures or isolated Papyrus data stores (StorageUtil)2.  
* **Memory-Level Text Injection**: Objective descriptions and journal entries must be written dynamically at runtime using SKSE C++ memory hooks (PO3\_SKSEFunctions), eliminating plugin form duplication and preventing co-save bloat4.  
* **Strict Spatial and Physical Realism**: All dynamic actor interventions must respect physical pathing bounds, utilizing off-screen pre-placement, early travel departure scheduling, and frustum-checked recovery pipelines to preserve spatial integrity and safeguard player trust2.

#### **Works cited**

> 1. Is it just me or do u guys wish that we weren't always forced to be the boss? \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/uixujd/is\_it\_just\_me\_or\_do\_u\_guys\_wish\_that\_we\_werent/](https://www.reddit.com/r/skyrimmods/comments/uixujd/is_it_just_me_or_do_u_guys_wish_that_we_werent/)  
> 2. galanx/IntelEngine-GamePlugin: AI Game Plugin \- GitHub, [https://github.com/galanx/IntelEngine-GamePlugin](https://github.com/galanx/IntelEngine-GamePlugin)  
> 3. Public facing files for SkyrimNet \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin](https://github.com/MinLL/SkyrimNet-GamePlugin)  
> 4. PO3\_SKSEFunctions script | Skyrim SE \- The Papyrus Index \- BellCube, [https://papyrus.bellcube.dev/skyrimse/script/po3\_sksefunctions/](https://papyrus.bellcube.dev/skyrimse/script/po3_sksefunctions/)  
> 5. Full Organic Factions Lite documentation released\! : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/j7y2q2/full\_organic\_factions\_lite\_documentation\_released/](https://www.reddit.com/r/skyrimmods/comments/j7y2q2/full_organic_factions_lite_documentation_released/)  
> 6. Could someone please explain how Open Civil War works? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/99l32s/could\_someone\_please\_explain\_how\_open\_civil\_war/](https://www.reddit.com/r/skyrimmods/comments/99l32s/could_someone_please_explain_how_open_civil_war/)  
> 7. Missives \- Voice and Quest Expansion \- Skyrim Creations, [https://creations.bethesda.net/en/skyrim/details/f957f0da-39ff-40c4-9600-71879cb26a7f/Missives\_\_\_Voice\_and\_Quest\_Expansion](https://creations.bethesda.net/en/skyrim/details/f957f0da-39ff-40c4-9600-71879cb26a7f/Missives___Voice_and_Quest_Expansion)  
> 8. \[SE\]\[PC\] Mods that add more non-combat focused activities and quests? : r/skyrimmods, [https://www.reddit.com/r/skyrimmods/comments/15j357k/sepc\_mods\_that\_add\_more\_noncombat\_focused/](https://www.reddit.com/r/skyrimmods/comments/15j357k/sepc_mods_that_add_more_noncombat_focused/)  
> 9. Unique Radiant Quests In Each Hold : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/6arbqd/unique\_radiant\_quests\_in\_each\_hold/](https://www.reddit.com/r/skyrimmods/comments/6arbqd/unique_radiant_quests_in_each_hold/)  
> 10. CHIM vs SkyrimNet : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1s7wm4q/chim\_vs\_skyrimnet/](https://www.reddit.com/r/skyrimmods/comments/1s7wm4q/chim_vs_skyrimnet/)  
> 11. Releases · MinLL/SkyrimNet-GamePlugin \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin/releases](https://github.com/MinLL/SkyrimNet-GamePlugin/releases)  
> 12. Mantella for first ever playthrough? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1vpmmqj/mantella\_for\_first\_ever\_playthrough/](https://www.reddit.com/r/skyrimmods/comments/1vpmmqj/mantella_for_first_ever_playthrough/)  
> 13. Civil War Overhaul is BACK along with every mod from the Epic Gameplay Overhaul : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/grj4gd/civil\_war\_overhaul\_is\_back\_along\_with\_every\_mod/](https://www.reddit.com/r/skyrimmods/comments/grj4gd/civil_war_overhaul_is_back_along_with_every_mod/)  
> 14. How to mod the Civil War so it doesn't SUCK without blowing up your load order (My Civil War Mod Recipe) : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/kh5jeo/how\_to\_mod\_the\_civil\_war\_so\_it\_doesnt\_suck/](https://www.reddit.com/r/skyrimmods/comments/kh5jeo/how_to_mod_the_civil_war_so_it_doesnt_suck/)  
> 15. Could someone pleeease, Explain-Like-I'm-a-5-Year-Old, the war table mechanic in the Open Civil War mod for SSE? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/cvjblz/could\_someone\_pleeease\_explainlikeima5yearold\_the/](https://www.reddit.com/r/skyrimmods/comments/cvjblz/could_someone_pleeease_explainlikeima5yearold_the/)  
> 16. Factions and allying with them | Page 3 \- Cyberpunk | Forums \- CD Projekt Red, [https://forums.cdprojektred.com/index.php?threads/factions-and-allying-with-them.7506730/page-3](https://forums.cdprojektred.com/index.php?threads/factions-and-allying-with-them.7506730/page-3)  
> 17. Skyrim SE & Skyrim AE Ultimate Modding Guide \- All In One, [https://www.sinitargaming.com/skyrim\_se.html](https://www.sinitargaming.com/skyrim_se.html)  
> 18. True Skyrim Endgame: Roguelike, Mapping and randomly generated Content? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/11vqkq7/true\_skyrim\_endgame\_roguelike\_mapping\_and/](https://www.reddit.com/r/skyrimmods/comments/11vqkq7/true_skyrim_endgame_roguelike_mapping_and/)  
> 19. PapyrusExtenderSSE/Papyrus/Source/scripts/PO3\_SKSEFunctions.psc at master \- GitHub, [https://github.com/powerof3/PapyrusExtenderSSE/blob/master/Papyrus/Source/scripts/PO3\_SKSEFunctions.psc](https://github.com/powerof3/PapyrusExtenderSSE/blob/master/Papyrus/Source/scripts/PO3_SKSEFunctions.psc)  
> 20. Adding a New Stat: Skyrim Modding Tutorial, [http://skyrimmw.weebly.com/skyrim-modding/adding-a-new-stat-skyrim-modding-tutorial](http://skyrimmw.weebly.com/skyrim-modding/adding-a-new-stat-skyrim-modding-tutorial)  
> 21. \[Mod Release\] Log Watcher — Real-time Analysis of SKSE Logs in Game : r/skyrimmods, [https://www.reddit.com/r/skyrimmods/comments/1oyt6cs/mod\_release\_log\_watcher\_realtime\_analysis\_of\_skse/](https://www.reddit.com/r/skyrimmods/comments/1oyt6cs/mod_release_log_watcher_realtime_analysis_of_skse/)  
> 22. vg/ \- /tesg/ \~ The Elder Scrolls General \- Video Game Generals \- 4chan, [https://boards.4chan.org/vg/thread/577768761/tesg-the-elder-scrolls-general](https://boards.4chan.org/vg/thread/577768761/tesg-the-elder-scrolls-general)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAZCAYAAADe1WXtAAAAVklEQVR4XmNgGAWjgFTwCF2AGuA/ugA1AAcQf0QXpAboRhegFtgLxHfQBWEAFEaU4GsMVAQgA0vQBSkBL9EFKAVGQHweXZBSAPI21UEtusAoGAVDDQAAR7MansDMUQEAAAAASUVORK5CYII=>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAZCAYAAABHLbxYAAABd0lEQVR4Xu2VzytEURTHT7KWEtnIxgJJbBQLYyVlRab8WNkosWKDZCFF2VvwR1haTlnZK3+AnbUsJHG+3fPMmW/3zcx7Y4p6n/rWO59z73v33fumESkoaBsjmi6WEaZZpPGlGWfZAu+aG02f5lTC/T9qRgTgK3Y9aHVHtR3nXnPLMidYpAcLQPqdmzHnScY1xZCEwXvcaJJLCfNfnBsw53cV9YGrwbb5TJxIOMJJbjSgJOFhZ+R5t3C94mowb77h8aeByQ8sM3Ak4R7HVi9YjeP34HcCXyafiVnJcSwG7+a61VPOgWHzu+SbYkvCZHw/eViSML/TuTVzvKOj5jM9q1fCpAo3MjAm8VNITqdEfsL8IvlU+KjyElsMwO7GFpS8QDf5GjYkDNrnRk5iL/rkrtG/cDU4NJ8Kmo8sW+BTs6qZc9nRnP+MELnSPLsaYA11F/qbXEv10+H0uHEA7s2uNyX+N/tnWNa8au648a/hI6qXgoKCgjbzDaCCZdRfpdQuAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD4AAAAZCAYAAABpaJ3KAAABmElEQVR4Xu2WOy8FURDHhwQRFEqPqIlOJAoKEYVEoVbdViEqhcIXUAmJTyAheqLVaLQSEgmVhgiiUQkzzuzrv3P2XoV7PM4vmWTnN7N7z+zdF1Ek8m+Z4GhF+QMYR2HQxtGHsh7vHDe63an5lw/yDcg65jnmOF41ny10ELWrH9b8mOMoK/vpIrdjnivDNZtDFOTWhOuSfMxwk+BKSBOeoVH1IfENKdGt+armiLVvCWnYAtehHs9kM7EWf6FuRPM7zRFr3wLJ/byGBXJ+G2VgcCDME3w+ZYBcg1wyiPgDlIHBgTBP8PmUfqr+x/dQBkTWs2s4a0CfT2kh17COBXJ+A2Ug7skexDegzxfwDSh+AWUAejieUCpvZA/Y8OCn4KbUh0YerpfghnLbNbLX2dDgi1Ru2jFcnnOqrgtS30SZY5/qH+OZYzoXcgWeZeVP5Bj4mS0OnwcmL5QtYka35V3uo94ZHSRXl/euj1tyPb1YUJLfsAIRt0zuK/SBY6VYrkYu70eOE/C/AfmT5La45liCWiQSiUQikT/EB0xgfqFGKk9pAAAAAElFTkSuQmCC>