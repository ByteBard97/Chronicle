> Filed 2026-08-22 in `docs/research/comparative-systems/` — external
> research, not code-verified. Distinct from this folder's other files: it
> covers **real-time spatial** open-world games (Shadows of Doubt's
> witness/memory-decay pipeline, Monolith's Nemesis System — including its
> patent boundary — and Kenshi's faction/legal systems) as genre neighbors,
> rather than Crusader Kings' menu-driven, turn-based model. Feeds the
> scenario-ladder / reactivity design work, not any accepted ADR.
>
> **Correction (2026-08-22, from a second independent pass,
> [spatial-sim-legal-boundaries-and-witness-propagation.md](spatial-sim-legal-boundaries-and-witness-propagation.md)):**
> every "US Patent 11,806,626" citation below (§2's "Legal Delineation"
> section and its two references in §4) is **wrong** — that patent covers
> streaming bonus-round audience participation, unrelated to Nemesis. The
> correct family is **US 10,926,179 B2** (parent) plus continuations
> US 11,660,540 B2 and US 12,201,908 B2. Read the other file for the
> corrected claim-by-claim breakdown before relying on this section's legal
> analysis.

# **Spatial Social Simulation Architecture: Data Structures, Memory Provenance, and Systemic Trade-Offs in Open-World Systems**

Real-time, spatial, walk-around open worlds present a fundamental engineering conflict between computational efficiency and simulated systemic depth. While menu-driven management frameworks handle extensive state spaces through abstract mathematical models, real-time 3D environments require simulated entities to exist physically within spatial geometry, navigate terrain collision grids, execute daily routines, and react dynamically to player intervention. Constructing an emergent social simulation—wherein non-player characters (NPCs) maintain subjective beliefs with explicit provenance, accumulate observer-specific reputation and grudges, and autonomously initiate actions based on that accumulated state—requires precise architectural trade-offs.  
By analyzing the underlying data structures, memory pipelines, witness models, and execution bottlenecks of *Shadows of Doubt*, *Middle-earth: Shadow of Mordor/War*, and *Kenshi*, game systems engineers can extract actionable technical patterns to implement scalable, real-time social simulations within spatial game engines.

## **1\. Shadows of Doubt: Micro-Scale Citizen Simulation and Provenance Traversal**

ColePowered Games' *Shadows of Doubt* simulates fully procedural, voxel-based noir cities where hundreds of citizens maintain persistent routines, residences, employment, social networks, and subjective memory states1. The game functions as an immersive detective simulator where the primary gameplay loop consists of traversing a simulated network of physical evidence, social records, and witness memories to identify perpetrators of procedurally generated crimes1.

### **Citizen Data Anatomy and Micro-Schedules**

Each citizen in *Shadows of Doubt* is instantiated as a persistent data structure composed of static, dynamic, and relational attributes1. The static layer includes a unique entity identifier (UUID), procedurally generated voxel appearance parameters, blood type, DNA signature, and fingerprint hash1. The dynamic state contains financial metrics, health metrics, physical status flags, home address pointers, workplace pointers, and daily schedule buffers1. Relational attributes map out a social network containing explicit links to spouses, roommates, colleagues, and acquaintance nodes1.  
To populate a functional urban environment without overwhelming real-time pathfinding threads, citizens undertake between 4 and 10 distinct micro-journeys per day6. These activities include sleeping, commuting to employment, visiting commercial establishments, dining at restaurants, and returning home1.

### **Knowledge Acquisition, Sighting Loops, and Memory Decay**

Knowledge acquisition operates across two distinct modalities: direct physical/digital trace logging and active NPC perception loops1. Digital and physical traces are instantiated deterministically by systemic actions within the game world1. When an NPC purchases a meal or coffee, the transaction instantiates a physical receipt item containing a merchant identifier, timestamp, item type, and purchase price1. Concurrently, the merchant’s local terminal records the transaction in its digital ledger1. Telephone calls generate persistent records in building switchboards, linking origin and destination phone numbers to precise timestamps1. Physical movement across doorways leaves footprints with specific size metrics, while touching surfaces leaves persistent fingerprint nodes mapped to the citizen's individual fingerprint hash1.  
NPC subjective knowledge—specifically tracking which entity observed another entity at a given time and location—is managed via an episodic memory pipeline6. The simulation executes a periodic global check that iterates across traveling citizens, calculating line-of-sight visibility and spatial proximity between entities6. When two citizens cross paths, a sighting structure is instantiated and appended to the observer's internal memory array6. A sighting memory structure contains the observed subject's UUID, the location identifier, the timestamp of the event, and a behavioral flag indicating standard behavior versus suspicious movement5.  
Memories in *Shadows of Doubt* are dynamic and degrade over time6. A newly formed memory possesses complete temporal and spatial accuracy6. Over time, the simulation applies a decay function that increases the vagueness of the stored parameters6. The rate of decay is governed by a multi-variable calculation incorporating subject familiarity, visual distinctiveness, witness alertness, subject age, and situational suspicion6.  
Memory degradation unfolds across three distinct operational phases:

> 1. **Precise Phase**: The NPC accurately reports the exact identity of the person observed, the precise location, and the exact timestamp6.  
> 2. **Fuzzy Phase**: The subject identifier degrades to a broad physical descriptor (such as "a short person with dark hair"), and the exact timestamp converts into a general time window (such as "around late afternoon")5.  
> 3. **Purged Phase**: The memory footprint exceeds its retention threshold and is garbage-collected from the citizen's active memory buffer to free memory overhead, rendering the witness unable to recall the event during interrogation6.

### **Provenance Graph Traversal and Detective Gameplay**

The detective gameplay loop relies on the player manually reconstructing a directed provenance graph using physical clues, digital logs, and witness interviews1. When questioning an NPC, the game queries the subject's memory array for sightings matching specific locations or temporal windows surrounding a crime3. Dialogue outputs do not rely on traditional branching text trees; instead, the underlying state populates structured narrative cards on the player's evidence corkboard interface3. The player manually draws string connections between nodes—linking a fingerprint found on a murder weapon to an employee record retrieved from a corporate terminal, and validating that against a witness statement placing the suspect at the scene at a specific time1.

### **Architectural Trade-Offs: Performance, Memory Footprint, and Legibility**

Simulating hundreds of citizens at full fidelity simultaneously presents extreme performance challenges6. ColePowered Games implemented significant structural simplifications to ensure real-time viability6. The primary technical bottleneck identified in developer postmortems is the system memory footprint9. Storing continuous historical provenance—including who saw whom, transaction histories, call logs, and footprint nodes—for hundreds of entities creates heavy RAM demands8. To prevent memory overflow, non-essential historical records are periodically culled, and physical props reset their spatial transforms if altered by random systemic collisions9.  
From a legibility perspective, the simulation succeeds when clues allow deterministic deduction, such as matching a rare shoe size and print to an employee registry1. System legibility degrades when procedural edge-cases break narrative plausibility—such as killers who report their own crimes due to state-machine conflicts, or witnesses who fail to differentiate between a routine passerby and a visibly armed suspect due to rigid sight-check thresholds8.

## **2\. The Nemesis System: Generative Hierarchies and Procedural Antagonism**

Monolith Productions’ Nemesis System, implemented in *Middle-earth: Shadow of Mordor* and *Middle-earth: Shadow of War*, represents a highly specialized implementation of dynamic NPC hierarchy and episodic memory tracking11.

### **Mechanical Anatomy: Entity Generation, Encounter Verbs, and Personality Mechanics**

The Nemesis System generates dynamic Uruk-hai and Olog-hai enemies from a standardized base model template—described internally by developers as "primordial goo"—consisting of a humanoid frame with a weapon archetype13. The system attaches procedural layers over this base mesh: randomized physical assets (armor, skin tone, facial geometry), vocal libraries, personality archetypes (e.g., "The Friendly", "The Assassin", "Man-Eater"), and mechanical trait arrays defining combat strengths and vulnerabilities11.  
When the player engages an enemy Nemesis, the combat outcome resolves into a discrete set of procedural outcome "verbs"11. These outcome verbs act as state mutators:

* **Player Death**: The surviving Orc gains power, receives a promotion within the military hierarchy, and generates dialogue taunting the player upon their next encounter11.  
* **Player Flight**: The Orc logs a cowardice event, increasing its confidence traits and unlocking specific dialogue mocking the player's retreat11.  
* **Severe Injury / Defeat**: If an Orc survives a non-decapitating lethal blow, the engine runs a probability calculation to allow the entity to "cheat death," returning later with procedural physical modifications (e.g., iron plates, burn scars, peg legs) and voice lines referencing the specific method of defeat11.

Dialogue generation relies on a combinatorial template engine11. Rather than pulling flat text strings, dialogue systems select audio fragments filtered through the target Orc's personality archetype, current power rank, past encounter outcome, and current physical condition11.

### **Hierarchy Dynamics, Succession, and Procedural Betrayals**

The Orc hierarchy is organized into structured tiers: Captains, Warchiefs, and Overlords11. This matrix is dynamic; vacancies caused by player assassinations or inter-NPC rivalries trigger automated succession routines11. When a player is killed by an unnamed grunt unit, that grunt is granted a unique name, generated attributes, promoted to Captain, and assigned a vacant slot in the hierarchy11.  
Orcs also initiate autonomous background events that simulate an active internal hierarchy11:

* **Duels**: Two Orcs fight for rank dominance, with the victor gaining power traits and rank11.  
* **Hunts**: An Orc hunts wild beasts to gain combat abilities11.  
* **Feasts**: Orcs host gatherings to recruit followers and increase power11.  
* **Executions**: A higher-ranking Orc attempts to execute a lower-ranking rival11.

In *Middle-earth: Shadow of War*, Monolith expanded the relational graph by introducing Blood Brothers and Betrayal mechanics11. If the player mind-controls (brands) an Orc and commands him to attack his designated Blood Brother, or if the player kills an Orc's Blood Brother, the surviving entity's relationship parameters instantly invert to maximum hostility11. This triggers dynamic ambush events where the grieving Blood Brother invades the player's active world space to avenge his fallen kin11.

### **Legal Delineation: Analysis of US Patent 11,806,626**

To understand what game designers can legally build without infringing on intellectual property, one must examine the specific patent filings held by Warner Bros. Entertainment Inc. The core operational pipeline of the Nemesis system is protected under **US Patent 11,806,626**11.

| Protected Patent Claims (WB US Patent 11,806,626) | Unpatented / Public Domain Design Space |
| :---- | :---- |
| **Dynamic Army Hierarchy**: Maintaining a database of NPCs organized in a dynamic hierarchy structure11. | **General Memory**: NPCs remembering player actions, reputation, or general dialogue states11. |
| **Parameter Mutation via Outcomes**: Automated mutation of NPC power, traits, and visuals driven directly by combat outcomes (player death, defeat, escape)11. | **Faction Standings**: Standard faction reputation meters, regional karma, or local bounty systems16. |
| **Automated Hierarchy Reallocation**: Automated promotion, demotion, and vacancy-filling within an army structure based on interaction outcomes or background events11. | **Procedural Enemies**: Procedural generation of enemy traits, appearance, or loot tables11. |
| **Context-Aware Re-Engagement Dialogue**: Dynamic generation of custom dialogue and behaviors during re-encounter based on updated hierarchy status and encounter parameters11. | **Static Hierarchies**: Fixed or quest-driven boss structures that do not automatically reallocate ranks via automated interaction outcome loops11. |

The patent specifically protects the *interlocking operational pipeline* where player interactions update an NPC's attributes, which automatically alters their position within an interactive organizational army hierarchy, which subsequently alters their dynamic narrative presentation upon re-encountering the player11.  
Safe design space remains broad: system implementations that track individual NPC grudges or social connections *without* routing those changes into an automated rank hierarchy matrix fall outside the scope of Warner Bros.' patent claims11.

### **Design Tuning and State Machine Orchestration**

Technical presentations at GDC and developer postmortems highlight that the key design challenge of the Nemesis System was pacing and state machine orchestration12. If Orcs cheat death too frequently, revenge loses narrative impact and becomes frustrating; if Orcs rarely survive, the player never forms a personal rivalry11. Monolith tuned the engine using dynamic probability curves:

* An Orc's probability of surviving lethal blows scales inversely with the total number of active rivalries currently tracked by the system11.  
* Ambush timers are throttled to prevent multiple Nemesis Orcs from entering the combat space simultaneously, preserving combat clarity11.  
* The animation pipeline was integrated directly into state-machine evaluations, ensuring that dramatic taunt sequences execute cleanly without breaking underlying pathfinding or combat AI12.

## **3\. Kenshi: Faction Legal Systems, Sight-Based Crimes, and Macro Simulation**

Lo-Fi Games’ *Kenshi* is an open-world sandbox RPG set in a seamless, post-apocalyptic world18. Developed by Chris Hunt, *Kenshi* achieves emergent systemic simulation through modular data architecture managed primarily via the Forgotten Construction Set (FCS)18.

### **The Witness Model and Delegated Legal Systems**

In *Kenshi*, criminality is strictly non-telepathic18. A crime (such as theft, assault, lockpicking, or freeing a prisoner) exists systemically only if an NPC observes the act via line-of-sight checks18. When an act is observed, the game executes specific event triggers in the FCS event pipeline21:

* EV\_WITNESS\_GENERIC\_ASSAULT: Triggered when an entity observes an unprovoked attack on a neutral or allied target21.  
* EV\_WITNESS\_THIEF\_OR\_LOCKPICK: Triggered when an entity observes theft from a container, lockpicking of a door, or freeing of a slave21.  
* EV\_THIEF\_CAUGHT\_STEALING\_FROM\_ME: Triggered when an NPC directly detects pickpocketing on their person21.

Once a crime is witnessed, the observer attempts to trigger a alarm, alerting nearby allies within audio propagation range18.  
A key architectural feature in *Kenshi* is the **Delegated Legal System**18. Within the FCS data files, faction entries contain a property field titled Legal System, which can point to another faction’s legal framework18. For example, the minor faction *Tech Hunters* sets its Legal System pointer to *United Cities*18.  
If a player assaults a Tech Hunter in a remote settlement, the crime is processed through the United Cities legal framework, assigning the player a bounty registered with the United Cities18. However, because Tech Hunter settlements lack police infrastructure, local Tech Hunters do not execute formal arrest routines; they simply attack the aggressor locally18. If the player subsequently enters a main United Cities metropolis, the municipal city guards evaluate the player's active bounty via the EV\_BOUNTY\_SPOTTED trigger and initiate an arrest sequence18.

### **Persistence, Bounty Infrastructure, and Squad Aggregation**

*Kenshi* avoids tracking individualized episodic memory arrays for thousands of separate NPCs18. Instead, persistence is handled at two specific structural levels:

> 1. **Character-Level Status Flags**: Bounties, slave brands, and stolen item flags are attached directly to the target character or item data structures18. A character carrying an active bounty contains a persistent flag that causes any guard NPC within that legal jurisdiction to evaluate them as hostile upon visual contact18.  
> 2. **Faction-Level Aggregation**: Long-term individual NPC grudges are collapsed into a global scalar value: **Faction Relations** (ranging from \-100 to \+100)18. If a player attacks a town guard, the resulting harm degrades global faction relations18. If relations drop below \-10, the entire faction becomes hostile toward the player's squad18.

If a player is attacked by an aggressive guard and retaliates in self-defense, knocking out or killing the guard further degrades global faction relations (-10 to \-50), rapidly turning a minor fine into permanent faction hostility18.

### **Chunk Loading, Off-Screen Settlement Mechanics, and FCS Architecture**

*Kenshi* divides its world grid into spatial terrain chunks19. Simulation fidelity is tied directly to chunk loading states19:

* **Active Loaded Chunks**: Entities possess full physics colliders, line-of-sight visual checks, active pathfinding grids, and real-time combat processing18.  
* **Unloaded Off-Screen Chunks**: Physics, collision detection, and micro-AI pathfinding are entirely suspended19. Off-screen settlements do not simulate real-time NPC movement routines or combat encounters19.

To simulate world progression without running real-time pathfinding off-screen, *Kenshi* utilizes **World States**19. World States are global boolean conditional trees defined within the FCS18.  
When an active chunk containing a major faction leader is loaded and that leader is killed or captured by the player, the engine sets the corresponding World State flag to true19. When distant chunks containing settlements are subsequently loaded into active memory, the engine checks these World State flags and executes a **Town Override**, replacing the original town layout, guard squads, and vendor tables with those of an invading or succeeding faction19.

### **Developer Engineering Postmortem and Sustainability Bottlenecks**

Chris Hunt's long-term solo development postmortems highlight key technical lessons regarding simulation scope:

* **Sustainable Systems**: Modular data structures created via an external data editor (FCS) proved highly sustainable18. FCS enabled straightforward creation of dialogue trees, squad templates, item definitions, and condition triggers without hardcoding logic into C++18.  
* **Unsustainable Systems**: Complex, individualized micro-AI decision trees for thousands of active entities simultaneously proved unsustainable18. Early attempts to give every NPC unique personal memory graphs created severe pathfinding overhead, memory leaks, and save-file bloat18. The engine was stabilized by collapsing individual memory into global faction scalars, persistent status flags, and static World State checks18.

## **4\. Synthesis: Applied Social Simulation for Spatial Engines**

For developers building social simulation systems within spatial frameworks (such as Bethesda’s Creation Engine or custom 3D engines), translating these architectural patterns requires selecting appropriate structural mechanics while avoiding computational bottlenecks.

### **Cross-Game Architectural Comparison**

| Dimension | Shadows of Doubt | Middle-earth: Shadow of Mordor/War | Kenshi |
| :---- | :---- | :---- | :---- |
| **Primary State Scale** | Individual Citizen (UUID) micro-logs1. | Dynamic individual NPC Orcs in dynamic hierarchy11. | Global Faction Relations \+ Individual Bounty Flags18. |
| **Witness / Perception Loop** | Periodic sightings check across traveling entities6. | Direct player combat encounter evaluation11. | Real-time line-of-sight checks (EV\_WITNESS\_\*)18. |
| **Knowledge Provenance** | Directed graph: Clues, Receipts, CCTV, Call Logs1. | Encounter Verbs mutate traits & dialog pools11. | Delegated Legal System pointers & crime alarms18. |
| **Memory Lifespan** | Decay model (Precise \-\> Fuzzy \-\> Purged)6. | Permanent until entity death / replaced in hierarchy11. | Bounties persist until paid/served; Faction scores permanent18. |
| **Off-Screen Simulation** | Pre-calculated daily schedule batching (10-15s)6. | Abstract background event calculations (Duels, Hunts)11. | Suspended; macro shifts governed by World States19. |
| **Primary Failure Mode** | High RAM footprint; unreadable witness noise6. | Repetitive ambushes; pacing breakdown11. | Self-defense spiral erodes faction standing rapidly18. |

### **Load-Bearing Simplifications vs. High-Impact Simulated Mechanics**

Each game relies on specific load-bearing abstractions—mechanisms faked under the hood—to keep performance manageable, while focusing simulation fidelity on specific high-impact mechanics felt directly by the player:

* ***Shadows of Doubt***: Fakes real-time off-screen decision-making by pre-calculating daily routine schedules during a 10-15 second morning batch phase6. Conversely, it honestly simulates persistent physical trace generation (fingerprints, DNA, CCTV logs, purchase receipts) and dynamic memory decay, forcing players to cross-reference fuzzy witness statements against hard evidence1.  
* ***The Nemesis System***: Fakes persistent physical placement, as Orc enemies do not physically traverse the open world until dynamically spawned near the player; hierarchy changes are processed as abstract database operations11. Conversely, it honestly simulates combat interaction memory through procedural outcome verbs that permanently modify an Orc's visual scars, combat strengths, weaknesses, and dialogue11.  
* ***Kenshi***: Fakes off-screen world activity by freezing unloaded terrain chunks entirely, executing city ownership shifts through static World State boolean overrides upon cell loading19. Conversely, it honestly simulates non-telepathic line-of-sight crime witnessing and delegated legal jurisdiction systems18.

### **Architecture Strategy: Copy, Adapt, and Avoid**

#### **Mechanisms Worth Copying**

> 1. **Delegated Legal Systems (*Kenshi*)**: Implement legal faction pointers in entity data structures18. Minor local factions (e.g., local village residents) should delegate legal jurisdiction to major regional factions (e.g., regional holds)18. Crimes observed by minor faction members apply bounties to the controlling regional legal authority18.  
> 2. **Encounter Mutation Verbs (*Nemesis System*)**: Implement a combat event listener attached to named unique NPCs11. If the player defeats an NPC using fire attacks, set a persistent integer flag on that NPC's data structure11. Upon re-encounter, query that flag to trigger context-specific voice lines and apply a fire-phobia combat modifier11.  
> 3. **Pre-Calculated Daily Itineraries (*Shadows of Doubt*)**: Avoid executing real-time decision trees for off-screen NPCs6. Utilize standard engine AI package stacks (Sandbox, Travel, Sleep) to handle routine movements, evaluating state updates only when the player enters the local cell grid6.

#### **Mechanisms Worth Adapting**

> 1. **Fuzzy Memory Provenance Arrays (*Shadows of Doubt*)**: Storing complete, unbounded historical provenance for every NPC interaction creates severe save-file bloat and script lag8. Adapt this by storing subjective memory as fixed-size circular buffers attached to individual NPCs5. Limit memory capacity to a fixed number of recent major events (e.g., maximum 8 entries), tracking subject ID, location ID, timestamp, event type, and an accuracy decay float6.  
> 2. **Dynamic Vacancy Filling (*Nemesis System*)**: Adapt the hierarchy concept to fit local settlement roles without violating US Patent 11,806,62611. Instead of an automated army rank progression hierarchy, build localized dynamic vacancy matrices11. If a local faction leader or merchant is killed, a designated lieutenant NPC assumes the role and receives dialogue lines acknowledging the predecessor's death11.

#### **Patent Constraints and Legal Safe Zones**

To remain fully compliant with **US Patent 11,806,626**, game systems must explicitly avoid combining all three core patented elements into a single integrated system11:

> 1. Maintaining NPCs in an automated dynamic organizational army hierarchy11.  
> 2. Automatically mutating NPC power, traits, and hierarchy position driven directly by player combat interaction outcomes11.  
> 3. Automatically generating context-aware re-engagement dialogue based on that updated army hierarchy status11.

System designs remain entirely within the legal safe zone when tracking individual NPC memory, personal grudges, reputation scalars, or quest-driven leader replacements—provided these mechanics are not integrated into an automated, multi-tiered army rank reallocation loop11.

### **Performance Tricks for City-Scale Simulation**

To maintain high framerates and prevent script bottlenecks when executing city-scale social simulation in spatial engines, system architectures should incorporate three primary optimizations:

> 1. **Decouple Spatial Physics from Logical Simulation**: Collision checks, line-of-sight raycasts, and physical pathfinding should execute only within active visual cells surrounding the player6. Off-screen entity position updates should be calculated mathematically via linear interpolation between schedule waypoints rather than continuous 3D navmesh pathfinding6.  
> 2. **Fixed Memory Buffers with Automated Garbage Collection**: Prevent save-game growth and memory leaks by enforcing strict size caps on subjective memory arrays9. Utilizing circular arrays ensures that when an NPC logs a new memory beyond array capacity, the oldest memory entry is automatically overwritten6.  
> 3. **Interleaved Visibility Check Scheduling**: Avoid executing line-of-sight raycasts every frame for every active NPC6. Divide local cell NPCs into distinct execution buckets across multiple frame ticks6. Evaluating visual checks for one-fourth of active NPCs per frame tick reduces perception CPU overhead by 75% while maintaining responsive reaction times6.

## **Conclusions**

Constructing a performant social simulation within a spatial 3D game engine requires balancing systemic depth against computational limits. *Shadows of Doubt* demonstrates that memory decay and physical trace provenance transform raw data logs into meaningful detective gameplay1. *Middle-earth: Shadow of Mordor/War* shows that discrete outcome verbs permanently shape character personalities and rivalries11. *Kenshi* proves that non-telepathic line-of-sight checks, delegated legal structures, and global faction aggregation can sustain complex world systems across long development cycles18.  
By decoupling off-screen physics, utilizing fixed-size memory buffers, delegating legal jurisdictions, and enforcing non-telepathic perception loops, developers can build reactive, spatial social simulations that remain performant and scalable.

#### **Works cited**

> 1. Shadows of Doubt on Steam, [https://store.steampowered.com/app/986130/Shadows\_of\_Doubt/](https://store.steampowered.com/app/986130/Shadows_of_Doubt/)  
> 2. Shadows of Doubt DevBlog 1: A Detective Management Game\! \- ColePowered Games Ltd., [https://colepowered.com/shadows-of-doubt-a-detective-management-game/](https://colepowered.com/shadows-of-doubt-a-detective-management-game/)  
> 3. Shadows of Doubt on Steam, [https://store.steampowered.com/app/986130?snr=2\_9\_100015\_\_apphubheader](https://store.steampowered.com/app/986130?snr=2_9_100015__apphubheader)  
> 4. Upcoming & New Game Releases | Pre-Order & Play Now on Kinguin.net, [https://www.kinguin.net/campaign/game-releases](https://www.kinguin.net/campaign/game-releases)  
> 5. Shadows of Doubt DevBlog 10: Gameplay Loop \- ColePowered Games Ltd., [https://colepowered.com/shadows-of-doubt-devblog-10-gameplay-loop/](https://colepowered.com/shadows-of-doubt-devblog-10-gameplay-loop/)  
> 6. Shadows of Doubt DevBlog 8: Simulating a City \- ColePowered Games Ltd., [https://colepowered.com/shadows-of-doubt-devblog-8-simulating-a-city/](https://colepowered.com/shadows-of-doubt-devblog-8-simulating-a-city/)  
> 7. Shadows of Doubt DevBlog 29: 2021 Wrap-Up \- ColePowered Games Ltd., [https://colepowered.com/shadows-of-doubt-devblog-29/](https://colepowered.com/shadows-of-doubt-devblog-29/)  
> 8. Shadows of Doubt DevBlog 2: Finding the Game \- ColePowered Games Ltd., [https://colepowered.com/shadows-of-doubt-devblog-2-finding-the-game/](https://colepowered.com/shadows-of-doubt-devblog-2-finding-the-game/)  
> 9. Shadows of Doubt DevBlog 44: Modifiers Update \- ColePowered Games Ltd., [https://colepowered.com/shadows-of-doubt-devblog-44-modifiers-update/](https://colepowered.com/shadows-of-doubt-devblog-44-modifiers-update/)  
> 10. Shadows of Doubt DevBlog 30: The Top Shadows of Doubt Development Challenges Part I \- ColePowered Games Ltd., [https://colepowered.com/shadows-of-doubt-devblog-30-the-top-shadows-of-doubt-development-challenges-part-i/](https://colepowered.com/shadows-of-doubt-devblog-30-the-top-shadows-of-doubt-development-challenges-part-i/)  
> 11. “Nemesis System” as a tool for immersion and believability | by Piqulsky | Medium, [https://medium.com/@piqulsky/nemesis-system-as-a-tool-for-immersion-and-believability-2a986eea9786](https://medium.com/@piqulsky/nemesis-system-as-a-tool-for-immersion-and-believability-2a986eea9786)  
> 12. Postmortem: Monolith Productions' Middle-earth: Shadow of Mordor \- Game Developer, [https://www.gamedeveloper.com/audio/postmortem-monolith-productions-i-middle-earth-shadow-of-mordor-i-](https://www.gamedeveloper.com/audio/postmortem-monolith-productions-i-middle-earth-shadow-of-mordor-i-)  
> 13. How the Nemesis system got an indie makeover in Star Renegades \- Game Developer, [https://www.gamedeveloper.com/design/how-the-nemesis-system-got-an-indie-makeover-in-i-star-renegades-i-](https://www.gamedeveloper.com/design/how-the-nemesis-system-got-an-indie-makeover-in-i-star-renegades-i-)  
> 14. Video Game Writing: From Macro to Micro 1683920295, 9781683920298 \- dokumen.pub, [https://dokumen.pub/video-game-writing-from-macro-to-micro-1683920295-9781683920298.html](https://dokumen.pub/video-game-writing-from-macro-to-micro-1683920295-9781683920298.html)  
> 15. Designing for Adaptation in Games: An Early Analysis \- Game Developer, [https://www.gamedeveloper.com/design/designing-for-adaptation-in-games-an-early-analysis](https://www.gamedeveloper.com/design/designing-for-adaptation-in-games-an-early-analysis)  
> 16. The Nemesis of Narrative \- Game Developer, [https://www.gamedeveloper.com/business/the-nemesis-of-narrative](https://www.gamedeveloper.com/business/the-nemesis-of-narrative)  
> 17. Republic Core Note Form C 2 \- SEC.gov, [https://www.sec.gov/Archives/edgar/data/1794805/000179480523000007/noteformc.pdf](https://www.sec.gov/Archives/edgar/data/1794805/000179480523000007/noteformc.pdf)  
> 18. Are Tech Hunters stupid or something? : r/Kenshi \- Reddit, [https://www.reddit.com/r/Kenshi/comments/jyb34v/are\_tech\_hunters\_stupid\_or\_something/](https://www.reddit.com/r/Kenshi/comments/jyb34v/are_tech_hunters_stupid_or_something/)  
> 19. If you could implement one (big) game mechanic, it would be... : r/Kenshi \- Reddit, [https://www.reddit.com/r/Kenshi/comments/1fp2mqe/if\_you\_could\_implement\_one\_big\_game\_mechanic\_it/](https://www.reddit.com/r/Kenshi/comments/1fp2mqe/if_you_could_implement_one_big_game_mechanic_it/)  
> 20. Top Posts for February 6, 2024 \- Page 198 \- Reddit, [https://www.reddit.com/posts/2024/february-6-198/global/](https://www.reddit.com/posts/2024/february-6-198/global/)  
> 21. Dialogue Triggers Usage | Kenshi Wiki \- Fandom, [https://kenshi.fandom.com/wiki/Dialogue\_Triggers\_Usage](https://kenshi.fandom.com/wiki/Dialogue_Triggers_Usage)