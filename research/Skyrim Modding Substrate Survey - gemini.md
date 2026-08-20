# **Skyrim Modding Substrate Survey for External Social Simulation Architecture**

Building an external, world-wide social simulation service for *The Elder Scrolls V: Skyrim (Special Edition / Anniversary Edition)* requires bridging Skyrim's native C++ engine infrastructure, Papyrus scripting runtime, and existing modding frameworks. Rather than constructing every communication channel, event listener, and data extraction pipeline from scratch, leveraging existing open-source frameworks significantly accelerates development. This survey evaluates existing AI integration substrates, Skyrim Script Extender (SKSE) event-forwarding mechanisms, runtime package injection workflows, historical reputation and consequence systems, and NPC data extraction pipelines to establish an architectural foundation for a high-concurrency Python social simulation service.

## **1\. Existing AI Integration Frameworks: Architectural Survey and Pipeline Analysis**

The Skyrim artificial intelligence modding landscape has evolved from simple text-file exchange mechanisms to asynchronous HTTP backends, local vector databases, and native in-process C++ plugins. Analyzing these systems provides vital design patterns for event streaming, prompt context construction, and dynamic action execution.

| Framework | Repository / Nexus Link | Last Maintenance | License | Architecture Overview | Strategic Recommendation |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Mantella** | [art-from-the-machine/Mantella](https://github.com/art-from-the-machine/Mantella) \[cite: 1\] [Mantella Nexus Mods](https://www.nexusmods.com/skyrimspecialedition/mods/98631) \[cite: 2\] | December 2025 (v0.14)3 | AGPL-3.0 (Backend)1 / MIT (Mantella-Spell)4 | Decoupled Python service (main.py) communicating via asynchronous HTTP (SKSE\_HTTP) with Papyrus wrappers1. | **Study Architecture / Reuse IPC Substrate**4. Study the client-side event forwarding and HTTP server wrappers, but avoid building the simulation directly inside Mantella's backend. |
| **Pantella** | [Pathos14489/Pantella](https://github.com/Pathos14489/Pantella) \[cite: 7\] | Active Fork (2025)7 | AGPL-3.07 | Architectural fork of Mantella expanding local LLM backends (KoboldCpp, Llama 3, Gemma) and TTS routing options7. | **Study**. Serves as a reference for multi-backend LLM and TTS routing layers. |
| **CHIM (HerikaServer)** | [abeiro/HerikaServer](https://github.com/abeiro/HerikaServer) \[cite: 8\] [CHIM Nexus Mods](https://www.nexusmods.com/skyrimspecialedition/mods/126330) \[cite: 9\] | March 20268 | GPL-3.0 Lineage8 | SKSE Native DLL (aiagent.dll) connected to a PHP web server (HerikaServer) backed by PostgreSQL and vector embeddings8. | **Study Memory/RAG Pipeline**9. Analyze the \~500MB embedding model setup for semantic retrieval, but bypass the PHP/PostgreSQL stack. |
| **MinAI** | [MinLL/MinAI](https://github.com/MinLL/MinAI) \[cite: 11\] | April 2025 (v2.1.3)11 | Open Source12 | Middleware framework extending CHIM via PHP plugins, Papyrus scripts, and SPID integrations11. | **Study Context Builders & Sapience**11. Adapt MinAI's modular context serialization design for Python state rendering. |
| **SkyrimNet** | [MinLL/SkyrimNet-GamePlugin](https://github.com/MinLL/SkyrimNet-GamePlugin) \[cite: 13\] | Late 202514 | Open Source13 | Single in-process SKSE C++ DLL embedding a lightweight HTTP web server (localhost:8080) directly in Skyrim's process space13. | **Study Direct Memory Event Piping**13. Replicate its pattern of reading game memory pointers without inter-process serialization overhead. |

### **Mantella Architecture and Inter-Process Communication**

Mantella operates as a decoupled dual-component system1. Game-side execution is handled by Mantella-Spell (written in Papyrus and versioned via Spriggit) alongside supporting SKSE C++ plugins4. Inter-process communication (IPC) between Skyrim and the external Python process (main.py, requiring Python 3.11) historically relied on disk file polling but has transitioned to asynchronous HTTP via Leidtier's SKSE\_HTTP plugin1.  
Mantella constructs LLM context by aggregating game clock time, actor location, inventory modifications, nearby actors, weather state, and visual screenshots passed to vision-capable models3. It injects pre-written character biographies for over 3,000 NPCs harvested from Unofficial Elder Scrolls Pages (UESP) lore databases1. Action execution relies on parsing structured string commands or function calls returned by the backend, enabling NPCs to initiate combat, follow the player, exchange items, cast spells, or navigate across cell boundaries3. Extension points exist via Mantella Dialogue (by mikastamm) and custom Papyrus event listeners (RegisterForModEvent)4.  
Building the social simulation directly inside Mantella's Python server is unadvisable because Mantella is optimized specifically for real-time 1-on-1 dialogue loops, local speech-to-text (STT), and text-to-speech (TTS) pipelines16. However, its client-side event forwarding and SKSE\_HTTP integrations provide an ideal blueprint for lightweight HTTP event streaming4.

### **CHIM and MinAI Context Construction and Retrieval-Augmented Generation Memory**

CHIM utilizes a native C++ SKSE plugin (aiagent.dll) communicating with a local PHP web service (HerikaServer) backed by a PostgreSQL database8. HerikaServer manages long-term character memory through a \~500MB local vector embedding model, facilitating semantic search across past conversations and lore records9.  
MinAI operates as a middleware extension running on top of CHIM12. It introduces a modular context builder framework that formats character and environmental state into prompt structures11. Context sections conditionally serialized for the LLM include physical equipment layering, survival states (Frostfall exposure, temperature, fatigue, hunger), dirt/blood levels, power dynamics, and local crime/bounty status11. MinAI also introduces "Sapience," which uses Spell Perk Item Distributor (SPID) to dynamically toggle AI perception on all actors in proximity to the player, alongside "Dungeon Master" hotkeys for injecting arbitrary narrative events into the game world12.  
While CHIM's dependency on a full PHP and PostgreSQL web stack (frequently running inside Windows Subsystem for Linux) introduces unnecessary complexity for a pure Python social simulation10, MinAI's context builder design pattern offers a strong template for serializing belief graphs in Python11.

### **SkyrimNet In-Process Memory Architecture**

SkyrimNet departs from multi-process web stacks by operating as a unified, in-process SKSE C++ plugin13. By embedding its HTTP web server (localhost:8080) and worker threads directly inside Skyrim's process space, it reads game state straight from native C++ memory pointers, bypassing inter-process serialization overhead and thread-blocking network latency13.  
SkyrimNet's C++ memory-reading patterns illustrate the latency lower-bound for in-memory event detection13. For an external Python service tracking 1,000+ off-grid NPCs, a separate process remains necessary, but SkyrimNet's event-filtering architecture demonstrates how to minimize game-thread interference13.

## **2\. SKSE Event Substrates and Inter-Process State Forwarding**

To maintain an external belief graph covering rumors, crimes, grudges, and relationship shifts across Skyrim, an external Python service requires a continuous stream of granular game events.

### **Native Hookable Game Events**

Using CommonLibSSE-NG (a modern C++ SDK for SKSE plugin development), developers can hook into Skyrim's internal event dispatchers managed by RE::ScriptEventSourceHolder and RE::BSTEventSource19.

| Event Class | Native Source | Trigger Condition | Social Simulation Utility |
| :---- | :---- | :---- | :---- |
| TESDeathEvent | RE::ScriptEventSourceHolder \[cite: 19\] | Actor death occurs in a loaded cell19. | Triggers grudge resolution, inheritance, family grief, and high-severity rumor generation. |
| TESContainerChangedEvent | RE::ScriptEventSourceHolder \[cite: 19\] | Item transferred between containers or actors19. | Tracks theft, bartering, gift-giving, and item-based obligation shifts. |
| TESActivateEvent | RE::ScriptEventSourceHolder \[cite: 19\] | Player or NPC interacts with an object or actor19. | Detects physical contact, door transitions, and container searching. |
| TESCombatEvent | RE::ScriptEventSourceHolder \[cite: 20\] | Actor enters or exits combat state20. | Ingests violent conflict evidence, hostility spikes, and self-defense context. |
| TESActorLocationChangeEvent | RE::ScriptEventSourceHolder \[cite: 20\] | Actor transitions across cell or location boundaries20. | Updates physical coordinates of NPCs for spatial rumor propagation models. |
| TESCellAttachDetachEvent | RE::ScriptEventSourceHolder \[cite: 20\] | Actor 3D object loaded into or unloaded from active cell grid20. | Signals transition between symbolic background simulation and physical cell hydration. |
| TESEnterBleedoutEvent | RE::ScriptEventSourceHolder \[cite: 19\] | Actor health reaches zero in protected or essential state19. | Generates assault evidence and severe grievance records. |
| TESEquipEvent | RE::ScriptEventSourceHolder \[cite: 20\] | Actor equips or unequips armor, weapons, or clothing20. | Updates visual state context (e.g., faction armor worn, drawn weapons). |

### **Event Forwarding Mechanisms to External Processes**

To bridge Skyrim's C++ event pipeline with an external Python process, three primary integration patterns exist:  
Developing a custom, lightweight SKSE C++ plugin using CommonLibSSE-NG and an asynchronous network library (such as cpp-httplib or Boost.Asio) represents the most performant strategy. The plugin registers sinks for native engine events (TESDeathEvent, TESContainerChangedEvent, TESCombatEvent, TESActorLocationChangeEvent)19. Upon event dispatch, the C++ thread formats the event payload into a lightweight JSON buffer and pushes it via WebSocket stream or HTTP POST directly to the Python service. This approach completely bypasses the Papyrus runtime, avoiding script thread lag.  
Alternatively, developers can leverage existing Papyrus extenders such as powerofthree's Papyrus Extender (PO3), PapyrusUtil, and JContainers alongside Leidtier's SKSE\_HTTP plugin4. While functional for low-frequency interactions, piping high-frequency events (such as location or container changes) through Papyrus SendModEvent scripts creates severe execution bottlenecks inside Skyrim's script virtual machine17.

## **3\. AI Package Overrides, Schedule Manipulation, and Cell Hydration Dynamics**

Injecting social simulation state (e.g., an NPC seeking revenge, traveling to another hold to spread a rumor, or avoiding an enemy) into Skyrim requires manipulating the engine's AI Package evaluation system.

### **Package Evaluation Engine Mechanics**

Skyrim NPCs execute behavior through AI Packages (TESPackage), which define high-level behaviors such as Sandbox, Travel, Patrol, UseItemAt, Eat, or Sleep. The engine evaluates an actor's package stack sequentially based on package priorities and conditional flags. Calling Actor.EvaluatePackage() in Papyrus forces the engine to interrupt an actor's current pathfinding loop and re-evaluate their package stack. Custom AI packages can be dynamically assigned across the NPC roster at runtime using Spell Perk Item Distributor (SPID) based on actor IDs, factions, or dynamic keywords12. To execute a dynamic social goal, an SKSE plugin sets a Global Variable or updates an SKSE-driven quest alias containing a high-priority Travel or UseItem package, then triggers EvaluatePackage().

### **Cell Hydration Dynamics**

Skyrim's world engine enforces a strict boundary based on active cell grids. NPCs within the active cell grid surrounding the player (typically a 3x3 or 5x5 grid of loaded cells) are fully hydrated as 3D physical references (TESObjectREFR)20. They execute full Havok physics, line-of-sight checks, precise pathfinding, and high-frequency AI package updates.  
Conversely, NPCs in distant, unloaded cells do not exist as physical 3D objects. The game engine tracks their general location using abstract schedule timers (interpolating movement speed along standard road paths), but detailed collision, line-of-sight, and script executions are completely suspended.

### **Dual-State Simulation Pattern**

An external social simulation service must implement a dual-representation model to handle cell hydration:  
In the global scope, the Python service maintains a lightweight, graph-based representation of all \~1,000 named NPCs. This service continuously updates spatial coordinates, belief graphs, grudges, and social obligations in fixed tick cycles regardless of whether the actor's cell is loaded in Skyrim.  
When an NPC enters the active cell grid around the player, Skyrim dispatches a TESCellAttachDetachEvent or TESCellFullyLoadedEvent20. The SKSE plugin notifies the Python service, which hydrates the NPC's social state into the active game space by applying temporary relationship overrides, setting dialogue topic flags, or attaching active AI packages. When the NPC detaches from the loaded grid, active state is serialized back to Python, and the actor reverts to symbolic simulation.

## **4\. Historical Analysis of Reputation, Rumor, and Dynamic Consequence Mods**

Attempts to implement systemic reputation, rumor propagation, and dynamic consequences within Skyrim span the modding community's history. Analyzing previous attempts clarifies the technical bottlenecks that led to stalling or abandonment.

| Mod Name | Repository / Nexus Link | Last Maintenance | License | Architectural Approach | Failure / Stalling Mechanism | Strategic Recommendation |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Skyrim Reputation** | [Skyrim Reputation Nexus](https://www.nexusmods.com/skyrimspecialedition/mods/22374) \[cite: 21, 22\] | Mod Released 2018; Patches Active (\~2023)21 | Open / Nexus Standard22 | Pure Papyrus script engine using Quest Topic conditions to modify dialogue based on regional/global alignment metrics22. | **Papyrus Script Lag & Dialogue Override Conflicts**: Global alignment math ran on Papyrus thread queues, causing delayed responses. Heavy dialogue overrides clobber custom NPC greetings22. | **Study**. Do not use Papyrus for math or global dialogue conditions. Keep all belief calculations in Python and inject context dynamically. |
| **Organic Factions** | [SSE Organic Factions Nexus](https://www.nexusmods.com/skyrimspecialedition/mods/10289) \[cite: 23, 24\] [EtherDynamics GitHub/Website](http://www.etherdynamics.com) \[cite: 23\] | \~202224 | Open Framework / Proprietary Extension23 | Custom C++ / Enhanced AI Framework tracking faction resources, territory, and recruitment independent of player level23. | **Authoring Overhead & Vanilla Engine Brittleness**: Creating factions required extensive manual Creation Kit setup26. Attempting to overwrite hardcoded vanilla quest systems (such as the Civil War) caused severe stability issues26. | **Study**. Learn from its resource-flow mechanisms, but construct the social graph externally to avoid hardcoding complex quest aliases in the Creation Kit26. |

### **Skyrim Reputation Architectural Lessons**

*Skyrim Reputation* tracked crime events, quest completions, faction allegiances, and character transformations (vampirism/werewolf) via Papyrus scripts, assigning the player regional and global reputation levels22. NPCs altered their approach dialogue based on these calculated levels22.  
The mod encountered two critical bottlenecks. First, Skyrim's dialogue engine enforces strict priority hierarchies. *Skyrim Reputation* applied broad approach dialogue conditions that frequently broke unique NPC quest greetings22. Second, executing global reputation recalculations in Papyrus caused script queue backups on complex modlists, creating noticeable latency before NPCs reacted to crimes22. Furthermore, tracking was global rather than interpersonal; an NPC in Markarth would instantly react to a crime committed in Riften without a realistic rumor propagation delay22.

### **Organic Factions Architectural Lessons**

EtherDynamics' *Organic Factions* introduced an AI framework where factions accumulated wealth, recruited troops, upgraded gear, and captured territory dynamically23. Faction leaders evaluated strategic decisions based on resource availability and member mortality25.  
Despite its operational success, the project stalled due to extreme authoring friction. Setting up a single faction required configuring dozens of linked references, actor base templates, and script properties in the Creation Kit26. Additionally, attempting to hook into vanilla location ownership and civil war frameworks caused instability because native Skyrim quests rely on hardcoded stage triggers and static actor locations26.

## **5\. Data Sources for Skyrim NPC Rosters, Factions, and Relationships**

Populating a global social simulation graph covering \~1,000 named NPCs requires extracting baseline character rosters, faction allegiances, relationship matrices, and daily schedules directly from Skyrim's master files (Skyrim.esm, Update.esm, DLC plugins) and combining them with community lore databases.

| Data Source / Tool | Repository / Project Link | Last Maintenance | License | Data Extracted | Strategic Recommendation |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Creation Kit Master Records (.esm)** | Native Engine Files | Official Bethesda File | Commercial / Proprietary | NPC\_ (Base actor stats, voice types), FACT (Faction structures), RELA (Directed relationship matrices), PACK (Schedules)16. | **Primary Data Source**. Mine directly via automated extraction scripts. |
| **Mutagen / Synthesis** | [Mutagen-Modding/Synthesis](https://github.com/Mutagen-Modding/Synthesis) \[cite: 28\] [ExperienceMutagenPatcher](https://github.com/tr4wzified/ExperienceMutagenPatcher) \[cite: 29\] | Active (2026)28 | GPL-3.028 | Programmatic C\# / .NET library for reading, parsing, and exporting binary Skyrim record graphs28. | **Build Ingestion Pipeline**. Write a Mutagen extraction script to dump all NPC, relationship, and faction records to JSON. |
| **Spriggit** | Integrated in Mantella-Spell \[cite: 4\] | Active (2025)4 | Open Source | Converts binary .esm/.esp plugins into human-readable YAML file structures4. | **Study / Version Control**. Useful for inspection, but Mutagen is preferred for automated programmatic extraction. |
| **UESP Lore Summaries** | [Mantella Bio Substrate](https://github.com/art-from-the-machine/Mantella) \[cite: 1\] [SkyrimNet Data](https://github.com/MinLL/SkyrimNet-GamePlugin) \[cite: 13\] | Active / Maintained1 | CC BY-SA 3.01 | Narrative background bios, character personality traits, and lore summaries for \~3,000 NPCs13. | **Ingest Data**. Merge UESP text summaries with Mutagen relational graphs to populate LLM character prompts. |

### **Creation Kit Record Structures**

Skyrim's master files structure social structures using four primary record types:

* **NPC\_ Records**: Defines character form IDs, localized names, editor IDs, assigned Voice Types (VOVT), base stats, default AI packages, and initial world space locations.  
* **FACT Records**: Defines organizational memberships (such as WhiterunGuardFaction or CompanionsFaction), rank structures, crime group associations, and inter-faction disposition matrices (Neutral, Enemy, Ally, Friend).  
* **RELA Records**: Directed relationship records linking Actor A to Actor B with explicit integer relationship ranks:  
  * \+4: Lover  
  * \+3: Ally  
  * \+2: Confidant  
  * \+1: Friend  
  * 0: Neutral  
  * \-1: Acquaintance / Disliked  
  * \-2: Rival  
  * \-3: Enemy  
  * \-4: Archenemy  
* **PACK Records**: AI package schedule definitions specifying where an actor sleeps, eats, works, and sandboxes across the game's 24-hour time loop.

### **Ingestion Pipeline Strategy**

Extracting record structures manually via Creation Kit export scripts is slow and error-prone. Mutagen provides a modern, high-performance C\# framework for parsing binary mod files28. A custom Mutagen script can iterate across all NPC\_, FACT, and RELA records in Skyrim.esm and its expansion DLCs, extracting actor editor IDs, localized names, faction trees, relationship ranks, and voice types into a normalized JSON file. Combining this structural graph with pre-parsed UESP character biographies (used by Mantella and SkyrimNet) provides both the quantitative graph edges and qualitative background prompts required for an LLM social simulation1.

## **6\. Architectural Recommendations and Integration Blueprint**

To construct a performant social simulation service capable of tracking real-time beliefs, rumors, grudges, and obligations across \~1,000 NPCs, the optimal structural choices across all surveyed substrates are synthesized below:

> 1. **Inter-Process Event Substrate**: Develop a dedicated, lightweight C++ SKSE plugin using **CommonLibSSE-NG**19. Avoid routing real-time event checks through Papyrus scripts. The plugin registers sinks directly with RE::ScriptEventSourceHolder for TESDeathEvent, TESContainerChangedEvent, TESCombatEvent, and TESActorLocationChangeEvent19. The plugin forwards event payloads asynchronously via a C++ WebSocket thread directly to the external Python service.  
> 2. **Context Serialization Strategy**: Adopt **MinAI's** modular context builder design11. When an NPC enters a dialogue interaction, the Python service serializes the actor's current social state (top active grudges, recent rumors heard, target obligations) into structured prompt contexts11.  
> 3. **Off-Grid Engine and Cell Hydration**: Implement a **Dual-State Engine Pattern**. The Python service continuously simulates symbolic belief graphs, rumor diffusion, and spatial positioning across the entire 1,000-NPC roster off-grid. When TESCellAttachDetachEvent fires20, the SKSE C++ plugin hydrates loaded actors in the player's active grid by applying temporary relationship overrides and injecting dynamic high-priority AI packages via **SPID**.  
> 4. **Data Ingestion Pipeline**: Write a custom **Mutagen** script to mine base relationship matrices (RELA), faction hierarchies (FACT), and schedule routines (PACK) directly from Skyrim's master plugins28. Merge this quantitative graph with pre-parsed **UESP character bios**13 to initialize the Python social graph automatically upon first run.

#### **Works cited**

> 1. art-from-the-machine/Mantella: Mantella is a Skyrim and Fallout 4 mod which allows you to naturally speak to NPCs using a Speech-to-Text → LLMs → Text-to-Speech pipeline \- GitHub, [https://github.com/art-from-the-machine/Mantella](https://github.com/art-from-the-machine/Mantella)  
> 2. Milestones · art-from-the-machine/Mantella · GitHub, [https://github.com/art-from-the-machine/Mantella/milestones?state=closed](https://github.com/art-from-the-machine/Mantella/milestones?state=closed)  
> 3. Releases · art-from-the-machine/Mantella \- GitHub, [https://github.com/art-from-the-machine/Mantella/releases](https://github.com/art-from-the-machine/Mantella/releases)  
> 4. GitHub \- art-from-the-machine/Mantella-Spell, [https://github.com/art-from-the-machine/Mantella-Spell](https://github.com/art-from-the-machine/Mantella-Spell)  
> 5. Skyrim Installation \- Mantella, [https://art-from-the-machine.github.io/Mantella/pages/installation.html](https://art-from-the-machine.github.io/Mantella/pages/installation.html)  
> 6. Mantella (AI NPCs) \- Easy Install, Faster Responses, Vision, Bartering : r/skyrimvr \- Reddit, [https://www.reddit.com/r/skyrimvr/comments/1f52sav/mantella\_ai\_npcs\_easy\_install\_faster\_responses/](https://www.reddit.com/r/skyrimvr/comments/1f52sav/mantella_ai_npcs_easy_install_faster_responses/)  
> 7. GitHub \- Pathos14489/Pantella, [https://github.com/Pathos14489/Pantella](https://github.com/Pathos14489/Pantella)  
> 8. abeiro/HerikaServer · GitHub \- CHIM Server, [https://github.com/abeiro/HerikaServer](https://github.com/abeiro/HerikaServer)  
> 9. Will KoboldCpp consider adding RAG functionality in the future? · Issue \#1239 \- GitHub, [https://github.com/LostRuins/koboldcpp/issues/1239](https://github.com/LostRuins/koboldcpp/issues/1239)  
> 10. What ai mod would you prefer? : r/skyrimvr \- Reddit, [https://www.reddit.com/r/skyrimvr/comments/1gw81cf/what\_ai\_mod\_would\_you\_prefer/](https://www.reddit.com/r/skyrimvr/comments/1gw81cf/what_ai_mod_would_you_prefer/)  
> 11. Releases · MinLL/MinAI \- GitHub, [https://github.com/MinLL/MinAI/releases](https://github.com/MinLL/MinAI/releases)  
> 12. GitHub \- MinLL/MinAI: Bridge between LLMs and various Skyrim Mods, [https://github.com/MinLL/MinAI](https://github.com/MinLL/MinAI)  
> 13. Public facing files for SkyrimNet \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin](https://github.com/MinLL/SkyrimNet-GamePlugin)  
> 14. Releases · MinLL/SkyrimNet-GamePlugin \- GitHub, [https://github.com/MinLL/SkyrimNet-GamePlugin/releases](https://github.com/MinLL/SkyrimNet-GamePlugin/releases)  
> 15. Leidtier/SKSE\_HTTP: A SKSE plugin to communicate with ... \- GitHub, [https://github.com/Leidtier/SKSE\_HTTP](https://github.com/Leidtier/SKSE_HTTP)  
> 16. Mantella, [https://art-from-the-machine.github.io/Mantella/](https://art-from-the-machine.github.io/Mantella/)  
> 17. Releases · art-from-the-machine/Mantella-Spell \- GitHub, [https://github.com/art-from-the-machine/Mantella-Spell/releases](https://github.com/art-from-the-machine/Mantella-Spell/releases)  
> 18. Mantella/README.md at main \- GitHub, [https://github.com/art-from-the-machine/Mantella/blob/main/README.md](https://github.com/art-from-the-machine/Mantella/blob/main/README.md)  
> 19. RE::ScriptEventSourceHolder Class Reference \- CommonLibSSE NG, [https://ng.commonlib.dev/classRE\_1\_1ScriptEventSourceHolder.html](https://ng.commonlib.dev/classRE_1_1ScriptEventSourceHolder.html)  
> 20. CommonLibSSE-NG/include/RE/T/TESObjectREFR.h Source File, [https://ng.commonlib.dev/TESObjectREFR\_8h\_source.html](https://ng.commonlib.dev/TESObjectREFR_8h_source.html)  
> 21. Stable LO Series X (Updated) : r/SkyrimModsXbox \- Reddit, [https://www.reddit.com/r/SkyrimModsXbox/comments/1638n0l/stable\_lo\_series\_x\_updated/](https://www.reddit.com/r/SkyrimModsXbox/comments/1638n0l/stable_lo_series_x_updated/)  
> 22. How well is Skyrim Reputation? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/p28p29/how\_well\_is\_skyrim\_reputation/](https://www.reddit.com/r/skyrimmods/comments/p28p29/how_well_is_skyrim_reputation/)  
> 23. Example Enhanced AI & Organic Factions Playthrough: DuffB \- YouTube, [https://www.youtube.com/watch?v=BzVD4DPQOiU](https://www.youtube.com/watch?v=BzVD4DPQOiU)  
> 24. SE Organic Factions and the Extension updated\! : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/xqh5tq/se\_organic\_factions\_and\_the\_extension\_updated/](https://www.reddit.com/r/skyrimmods/comments/xqh5tq/se_organic_factions_and_the_extension_updated/)  
> 25. LE Organic Factions and the Extension updated\! : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/vc8uj5/le\_organic\_factions\_and\_the\_extension\_updated/](https://www.reddit.com/r/skyrimmods/comments/vc8uj5/le_organic_factions_and_the_extension_updated/)  
> 26. Full Organic Factions Lite documentation released\! : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/j7y2q2/full\_organic\_factions\_lite\_documentation\_released/](https://www.reddit.com/r/skyrimmods/comments/j7y2q2/full_organic_factions_lite_documentation_released/)  
> 27. Shadow of the Dragon God, AI Framework, and Organic Faction Framework \- YouTube, [https://www.youtube.com/watch?v=zCXEsoDA5Cc](https://www.youtube.com/watch?v=zCXEsoDA5Cc)  
> 28. GitHub \- Mutagen-Modding/Synthesis: A patcher pipeline framework and GUI. Run collections of code-based mods to create content customized for your load order, [https://github.com/mutagen-modding/Synthesis](https://github.com/mutagen-modding/Synthesis)  
> 29. tr4wzified/ExperienceMutagenPatcher: Mutagen version of the Skyrim SE Experience zEdit Patcher \- GitHub, [https://github.com/tr4wzified/ExperienceMutagenPatcher](https://github.com/tr4wzified/ExperienceMutagenPatcher)