# **Architectural Analysis of Comparative Social Simulation Systems and Integration Pathways**

The following report provides an exhaustive, systemic analysis of discrete social-simulation architectures across multiple commercial and academic game engines. The analysis is structured to address critical gaps in the existing catalog of non-player character (NPC) social mechanics, specifically focusing on belief epistemology, multi-agent social physics, native engine quest-injection frameworks, and localized generative mechanics. By deconstructing the underlying data models and integration surfaces of these systems, this report identifies the optimal architectural pathways for implementing dynamic, third-party social reasoning within an external simulation framework interfacing with Bethesda’s Creation Engine.

## **Part 1: Epistemological Foundations in Talk of the Town**

The foundational claim underlying the Chronicle project's vision relies on the epistemological data model pioneered by James Ryan in the *Talk of the Town* simulation and its associated live-action installation, *Bad News*. The project posits that Ryan’s architecture represents the most validated academic model for belief facets, evidence chains, and predecessor lineage. An exhaustive primary-source analysis of Ryan’s 2018 dissertation, *Curating Simulated Storyworlds*, and related academic publications reveals a sophisticated, highly applicable framework, albeit one that utilizes distinct academic nomenclature.

### **Knowledge Representation and the Belief Facet**

In the *Talk of the Town* architecture, characters do not simply hold floating text strings representing knowledge. The simulation maintains a centralized, objective record of all events that occur within the world state. Character knowledge is represented as a subjective cognitive pointer to these objective events.  
While Ryan does not natively employ the specific phrase "belief facet," the concept is structurally identical to his definition of a "mental model" or "knowledge proposition." In Ryan's framework, a character's knowledge of a fact is a discrete data object containing a pointer to the actual event, coupled with subjective metadata evaluating the event. Chronicle’s localized use of the term "belief facet" accurately paraphrases this architecture, describing a system where characters maintain subjective, multifaceted interpretations of objective simulation states.  
Furthermore, Chronicle’s use of the terms "evidence chain" and "predecessor lineage" maps flawlessly onto what Ryan explicitly defines as "provenance." Provenance is the structural pillar of Ryan’s epistemology. Every knowledge proposition stored in an NPC's memory graph contains a strictly recorded pathway of acquisition. The system mathematically tracks the exact sequence of actors through which a piece of information has passed, forming a directed acyclic graph (DAG) of information flow. Chronicle’s description of this mechanic is a highly accurate functional translation of Ryan’s provenance-tracking architecture.

### **Rumor Mutation and Factual Distortion**

The most critical systemic divergence between *Talk of the Town* and traditional game architectures (such as the rumor system in *Dwarf Fortress*) is the handling of information distortion during transit. Standard systems merely degrade the resolution of a rumor—making it less detailed or lowering its confidence score—without altering the factual core.  
*Talk of the Town* explicitly and deliberately distorts information. Ryan’s architecture models communication not as perfect data replication, but as a generative, lossy process subjected to the subjective biases of the transmitter. When an NPC communicates a fact, the engine applies relational weights (affinity, enmity, trust) between the speaker, the listener, and the subject of the rumor. A character may actively lie, exaggerate, or misremember based on these weights. As a rumor propagates across the social graph (the "Telephone" effect), the propositional content can invert entirely. Attributes are swapped, actors are misidentified, and the rumor becomes factually incorrect in a traceable, mathematically deterministic manner. The claim that *Talk of the Town* implements rumor distortion with provenance is entirely accurate and represents a massive leap over static string-passing systems.

### **Belief Formation and the Mechanics of Decay**

The provenance graph fundamentally differentiates between two modes of belief formation: direct observation (witnessed) and hearsay (told).

* **Direct Observation:** When a character witnesses an event firsthand, the provenance tree roots itself in the character's sensory array. The belief is assigned a maximum base certainty score. Witnessed facts form the stable foundation of the character's worldview.  
* **Hearsay:** Knowledge acquired via communication is mediated by a continuously updated trust variable. If an NPC receives a proposition from a source they distrust, the confidence score of the resulting belief is heavily penalized. Hearsay is treated as a volatile fact, subject to retroactive invalidation if the predecessor chain is later proven unreliable.

To manage computational overhead, Ryan implements a cognitive decay mechanism. Beliefs fade based on a function of time and emotional salience. Mundane observations decay rapidly, while facts carrying high relational resonance (e.g., witnessing a betrayal) possess extreme longevity. Once a belief’s certainty or resolution degrades below a strict pruning threshold, it is garbage-collected from the character's memory matrix.

### **Shipped Artifacts and Reusability**

The documentation cites *Bad News* as a shipped artifact demonstrating this system. It is vital to contextualize what *Bad News* actually represents. It is not a standalone, executable commercial video game. It is a computationally-assisted live theatrical installation that won the Vanguard Award at the 2017 Indiecade Festival. A human player interacts with a live improvisational actor, who receives real-time generative prompts from a hidden display running the *Talk of the Town* engine. Therefore, it is an academic demonstration of live procedural generation rather than a traditional game build.  
Regarding licensing and reusability, Ryan’s codebase is an academic artifact. Portions of the Python architecture are available in academic repositories, operating under standard open-source licenses. However, it is not a packaged, plug-and-play middleware library like IBSEN or HAMLET. The codebase is designed for academic study rather than direct drop-in integration with commercial game engines.  
**Verdict on Chronicle's Citation:** The citation of *Talk of the Town* as a foundational data model is highly accurate. While Chronicle employs proprietary nomenclature, the systemic architecture described in its vision document exactly mirrors Ryan’s implementation of provenance, generative distortion, and belief decay. However, because Ryan's code is not structured as commercial middleware, Chronicle cannot simply import the Python repository; the graph-theory logic must be natively rebuilt within the target integration environment.

## **Part 2: Academic Social-Simulation Engines Beyond The Sims**

Traditional commercial social simulation, typified by *The Sims*, relies on dyadic tracking: numerical affinity variables bridging two specific actors. This approach fundamentally fails to simulate third-party reasoning, where an uninvolved observer draws logical inferences about the broader social fabric. To achieve genuine multi-agent social physics, a distinct cluster of academic engines has pioneered alternative architectures.

### **Comme il Faut (CiF)**

Developed at UC Santa Cruz, *Comme il Faut* (CiF) represents a paradigm shift toward rules-based "social physics." CiF abandons simple affinity bars in favor of a massive, shared social-facts database governing a cast of characters.

* **Rule Representation:** The architecture relies on approximately 5,000 weighted social-consideration rules. The social state is represented through scalar networks (e.g., romance, friendship), boolean networks (e.g., enemies, dating), and transient subjective statuses (e.g., embarrassed, heartbroken). Rules act as complex preconditions evaluating this matrix.  
* **Volition Scoring:** Characters do not blindly select actions. They continuously calculate a "volition" score for every possible interaction with every other character. Volition is the aggregate mathematical sum of all active rules applying to a specific pairing.  
* **Third-Party Inference:** Because the database is global, social facts propagate instantly. If a character commits an infidelity, the engine updates the boolean network. An uninvolved character, processing their next tick, queries this global state, applies their own moral or relational consideration rules to the new fact, and updates their volition toward the cheater without needing a direct, dyadic exchange to trigger the realization.

### **Prom Week**

*Prom Week* is the playable puzzle game built upon the CiF engine. It serves as the primary shipped artifact proving CiF's viability. The game utilizes the full scope of the 5,000-rule CiF engine to calculate simultaneous volitions across a high school cast. However, the game was developed in Adobe Flash, tying its underlying architecture to an obsolete, single-threaded execution environment. While it proves the theoretical model, the source code is heavily intertwined with the Flash rendering pipeline, rendering it highly difficult to extract as a generalized library.

### **Ensemble**

*Ensemble* was developed as the direct, open-source successor to CiF. It extracts the core logic—volitions, social facts, and rule-based precondition scoring—into an engine-agnostic TypeScript/JavaScript framework.

* **Status:** *Ensemble* is a genuinely usable, maintained repository operating under an open-source license. By decoupling the social simulation from the rendering layer, it provides a highly inspectable architecture for developers looking to implement volition-based social physics in modern projects.

### **Versu**

Developed by Emily Short and Richard Evans, *Versu* introduces a radically different architecture based on social practices and deontic logic.

* **Deontic Architecture:** Rather than calculating thousands of numerical volitions, *Versu* places characters into contextual "social practices" (e.g., a formal dinner, a duel). Within a practice, characters assume roles. These roles generate a deontic status for potential actions, categorizing them as *permitted*, *obligated*, or *forbidden*.  
* **Context Shifting:** When a triggering fact arrives, the deontic statuses shift instantaneously for the entire group. Characters then select actions based on their internal traits, either fulfilling obligations or exploiting newly permitted actions. This models cultural norms and etiquette far more accurately than numerical affinity.  
* **Availability:** While the IEEE Transactions on Computational Intelligence and AI in Games published extensive theoretical breakdowns of *Versu*, the proprietary engine remains closed-source following the shuttering of the project by Linden Lab. It is a theoretical masterpiece but is not inspectable.

### **City of Gangsters**

The commercial game *City of Gangsters* utilizes a highly optimized logic-programming architecture (detailed by Zubek et al., AIIDE 2021\) to solve the combinatorial explosion inherent in massive social graphs.

* **Inference Mechanism:** Simulating second-order propagation across 1,200 NPCs using CiF’s continuous global updates would melt a standard CPU. Instead, *City of Gangsters* utilizes localized, Datalog-style logic queries. The engine does not maintain a perfectly updated matrix of all possible relationships at all times. It evaluates social propagation on-demand. When the player requests an action, the engine dynamically traces the social graph outward from that specific node, evaluating relationship thresholds just-in-time.

| Engine | Core Architecture | Inference Scale | Inspectability |
| :---- | :---- | :---- | :---- |
| **Comme il Faut** | Social Facts / Volition Scoring | Small (Global Updates) | Academic Archive |
| **Ensemble** | Volition / Precondition Rules | Medium (Agnostic) | High (TypeScript/OSS) |
| **Versu** | Deontic Logic (Roles/Norms) | Small (Contextual) | None (Closed Source) |
| **City of Gangsters** | Logic Programming (On-Demand) | Massive (1,200+ NPCs) | None (Commercial) |

**Verdict on Academic Engines:** For a deep, line-by-line source study, *Ensemble* is the absolute highest priority; its open-source TypeScript architecture is the most direct blueprint for building a volition-based backend. *Versu* and *City of Gangsters* are strictly citable-but-not-inspectable. However, *City of Gangsters* provides the mandatory architectural lesson that Chronicle must adopt localized, on-demand querying rather than continuous global updates if it hopes to maintain performance at scale.

## **Part 3: The Native Substrate in Radiant Story and Radiant AI**

A persistent failure mode in open-world modding is the attempt to build external director systems that compete with the host engine's native logic. An analysis of Bethesda’s Creation Kit (CK) reveals that the engine already possesses a highly sophisticated, deeply integrated storylet architecture in the form of Radiant Story. Understanding this substrate is paramount for seamless integration.

### **Radiant Story’s Node and Condition System**

In Skyrim, the system colloquially known as "radiant quest generation" is driven by the Story Manager (SM). The SM is a hierarchical, event-driven expert system. When an engine-level event occurs (e.g., Actor Kill, Item Dropped), the engine pings a specific SM Event Node.

* **Quest Aliases:** Attached to these nodes are Quest records, which contain "Reference Aliases." These aliases function as the casting call for the narrative template.  
* **Alias Filling:** To cast an alias, the engine utilizes conditions such as Find Matching Reference (searching the loaded area or global persistence) or Use Existing Reference. The alias applies a strict stack of boolean and comparative conditions (e.g., GetRelationshipRank \>= 1, IsInLocation \== Whiterun). The engine iterates through available objects; if an NPC meets all conditions, they are bound to the alias. If all required aliases are filled, the quest initializes, injecting the chosen NPCs into the pre-authored narrative logic.

### **The Storylet Role-Casting Comparison**

This architecture is structurally identical to the "storylet role-casting" model pioneered by *King of Dragon Pass* and standard academic AI directors. A storylet requires preconditions, a cast, and an execution block. Radiant Story’s SM Nodes handle the triggering, the Alias Conditions evaluate the preconditions, the filled aliases define the cast, and the subsequent Papyrus scripts manage execution. It is not superficially similar; it is the exact same paradigm. The only divergence is complexity: Bethesda utilizes highly simplified condition stacks for performance reasons, whereas academic storylets evaluate deep historical provenance.

| System Component | Academic Storylet Equivalent | Function |
| :---- | :---- | :---- |
| **SM Event Node** | Trigger / Context | Defines when the system attempts to evaluate a narrative insertion. |
| **Reference Alias** | Role / Cast | The specific slot a character or object must fill. |
| **Alias Conditions** | Preconditions | The logical gating determining if an entity is valid for the role. |
| **Quest Stages** | Execution / Payload | The behavioral and narrative payload applied to the cast entities. |

### **Radiant AI Failure Modes: The Oblivion Cascade**

The internet mythology surrounding Oblivion's early Radiant AI—specifically the legend of the beggar who killed for bread—is rooted in documented historical fact. In pre-release builds, NPCs utilized dynamic goal-satisfaction routines driven by core needs (hunger, sleep). If a beggar required food, the AI evaluated the environment. If the only available food was owned, the beggar would steal it. This triggered a cascading failure: guards (governed by high-responsibility AI packages) would attack the beggar, triggering faction allegiances that resulted in town-wide massacres, permanently killing essential characters.  
The patched, shipped solution for Oblivion, Skyrim, and Fallout 4 was the implementation of strict AI "Packages." Instead of dynamic need evaluation, NPCs operate on a prioritized stack of hardcoded schedules. This stabilized the game but lobotomized the emergent social simulation, replacing dynamic volition with rigid routines.

### **The Integration Surface for Chronicle**

Because the Radiant Story system is structurally sound but relies on shallow preconditions, Chronicle’s optimal integration path is to hijack the Story Manager rather than bypassing it.

* **The SendStoryEvent Hook:** The Creation Kit exposes a critical Papyrus API function: Keyword.SendStoryEvent(Location akLoc, ObjectReference akRef1, ObjectReference akRef2, int aiValue1, int aiValue2).  
* **Integration Strategy:** Chronicle can maintain its complex, graph-based social facts database externally via an SKSE (Skyrim Script Extender) plugin, sidestepping the performance limits of the Papyrus Virtual Machine. When Chronicle’s external logic calculates that a narrative threshold is met (e.g., a grudge reaches a boiling point), it simply calls SendStoryEvent, passing the calculated aggressor and victim as akRef1 and akRef2. The native Story Manager intercepts this keyword, casts the exact NPCs passed by Chronicle into a pre-authored Radiant Quest, and handles the scene rendering.

### **Fallout 4 Iterations**

Fallout 4 expanded this system primarily by introducing "Reserve Aliases," an architectural improvement ensuring thread safety by preventing two concurrent radiant quests from accidentally binding the same NPC simultaneously. However, the fundamental storylet casting paradigm remains unchanged from Skyrim.  
**Verdict on Integration:** Bethesda’s engine natively executes the entire storylet lifecycle—picking real NPCs, checking real state, and executing scenes. The smallest and most powerful integration surface for Chronicle is to act as a highly intelligent external oracle. By computing complex social state via SKSE and injecting the results directly into the Story Manager via SendStoryEvent, Chronicle avoids building a parallel, competing system and entirely eliminates conflicts with independent engine selections.

## **Part 4: Specific Mechanic Gaps in Researched Systems**

The following section addresses six localized systemic gaps identified during the brainstorming passes, mapping their concrete mechanics, dependencies, and functional differences from the existing mechanics catalog.

### **1\. Crusader Kings III's Legends System**

* **Concrete Mechanic:** Introduced in the *Legends of the Dead* expansion, a "Legend" is a geographic narrative object with a named protagonist and specific quality tiers1. A legend begins at the "Famed" quality tier. Once it successfully spreads to 100 baronies, it can be upgraded to "Illustrious," and ultimately to "Mythical"3. Spread is modeled dynamically across the map, heavily gated by a language barrier; expanding a realm to encompass more baronies speaking the creator's language is the primary method of accelerating diffusion4. Players actively drive spread by spending resources on decisions like "extol domestic legend" or "commend legend abroad," which prompts neighboring rulers to promote the legend4. Rulers acting as "Promoters" pay half the maintenance cost but must share a language, border, or relationship with the creator3. A widespread legend confers immense mechanical effects, generating monthly renown, legitimacy, unpressed de jure claims, and unlocking Legendary Buildings3. The presence of regional Plagues can severely disrupt the development of these affected baronies6.

| Legend Tier | Requirement | Key Mechanical Effects |
| :---- | :---- | :---- |
| **Famed** | Base Creation | \+10% Prestige, \+100 Legitimacy, 50% chance for Legendary Building. |
| **Illustrious** | 100 Baronies | \+15% Prestige, \+200 Legitimacy, Unlocks Legendary Adventure decision. |
| **Mythical** | Advanced Spread | \+25% Prestige, \+300 Legitimacy, Unlocks Demand Local Submission decision. |

* **Verdict:** This is a *genuinely distinct new mechanic*. It treats a narrative object not as a localized memory, but as an infectious agent utilizing geographic diffusion algorithms (similar to an epidemiological SIR model) to blanket a map and confer tiered mechanical bonuses.

### **2\. Crusader Kings III's Struggle/Phase System**

* **Concrete Mechanic:** A Struggle models a localized, multi-generational conflict as a discrete state machine rather than a binary war. The Iberian Struggle cycles through four specific phases: *Opportunity*, *Hostility*, *Conciliation*, and *Compromise*7. The Iranian Intermezzo utilizes a different track: *Unrest*, *Stabilization*, and *Concession*9. Progression between phases is driven by "Catalysts"—point-weighted actions taken by any Involved or Interloper characters in the region (e.g., breaking a truce adds weight toward Hostility; intermarrying adds weight toward Conciliation)7. Each phase acts as a massive global mutator, altering the cost of Casus Belli, the speed of cultural conversion, and unlocking specific interactions7.  
* **Verdict:** This is a *genuinely distinct new mechanic*. Modeling macro-conflicts as state machines driven by aggregate micro-actions provides a far superior pacing template for long-term narrative arcs (such as a civil war) than standard sliding-scale progress bars.

### **3\. The Nemesis System's Intel/Interrogation System**

* **Concrete Mechanic:** In *Middle-earth: Shadow of War*, acquiring actionable social knowledge is a core gameplay loop carrying mechanical risk. Players hunt specific low-rank orcs designated as "Worms," which are marked on the mini-map with a hollow green diamond12. While a player can interrogate any random enemy to gain basic locational intel on a Captain, only Worms (or other Captains) possess the requisite knowledge to reveal a target's specific mechanical strengths and weaknesses (e.g., fear of caragors, immunity to arrows)13. The physical act of interrogation forces the player to break stealth and locks them in a vulnerable animation, exposing them to alarms or overwhelming swarms13.  
* **Verdict:** This is a *natural extension* of existing knowledge systems, serving as an exceptional case study in bridging the gap between an NPC's simulated knowledge graph and actionable, high-risk player UI reveals.

### **4\. RimWorld's Ideology and "Tales" Generation**

* **Concrete Mechanic:** *RimWorld* approaches historical provenance differently than *Dwarf Fortress*. The game records significant colony events into a database of "Tales"16. When a colonist generates artwork, the engine does not merely concatenate static strings. Instead, it feeds the Tale data into a GrammarResolver17. The GrammarResolver acts as a context-free grammar engine, traversing procedural vocabulary nodes and injecting variables from the historical Tale to dynamically construct highly surreal, unique artwork descriptions. Furthermore, the Ideology DLC layers per-pawn certainty scores atop specific cultural precepts, acting as a collective belief filter that dynamically alters how a pawn interprets their own mood and interactions.  
* **Verdict:** The GrammarResolver is a *genuinely distinct new mechanic*, offering a flexible, generative alternative to rigid string arrays for surfacing historical provenance and belief interpretation to the player.

### **5\. Dwarf Fortress's Villains and Loyalty Cascades**

* **Concrete Mechanic:** The Villains update expanded world-gen intrigue, allowing external agents to recruit fortress citizens as minions or handlers, leading to systematic artifact embezzlement and espionage19. A critical, documented failure mode in this system is the "loyalty cascade" (referred to by developer Tarn Adams as the "civil war bug")20. Entities belong to specific factions (e.g., the Civilized, the Babysnatchers)21. If a player orders their military to attack friendly merchants from their own civilization, the attacking dwarves immediately inherit an enemy flag, becoming "Separatists" (enemies of the civilization, but still following fort orders)20. If other fort citizens attack the Separatists, they become "Loyalists" (enemies of the fort, loyal to the civilization), and further chaotic combat spawns "Renegades" (enemies of both)20. Because dwarves respond to immediate combat triggers but also inherit overlapping boolean loyalty flags, the simulation rapidly fractures into a permanent, unresolvable bloodbath20.  
* **Verdict:** This is a *specific cautionary case study*. The loyalty cascade proves that hardcoding overlapping boolean faction arrays, without a hierarchical deontic override system (as seen in *Versu*), will inevitably result in catastrophic emergent failure modes during combat.

### **6\. Watch Dogs: Legion's "Play As Anyone" Census System**

* **Concrete Mechanic:** Detailed at GDC 2021 by Christopher Dragert, the "Census" system drives the recruitment of 9 million procedurally generated Londoners22. Crucially, the engine does not persistently simulate a massive social graph in the background24. It utilizes just-in-time procedural generation23. When a player interacts with a pedestrian, the system instantly queries a relational database to assemble a grievance chain on-demand24. It dynamically links the pedestrian to existing world states—for example, generating a sibling who is currently being extorted by the specific faction the player is fighting, thereby creating a bespoke recruitment mission out of thin air.  
* **Verdict:** This is a *genuinely distinct new mechanic*. The Census system proves that generating localized relational data on-demand is vastly superior to maintaining a persistent, memory-heavy global cache when scaling social mechanics to massive populations.

## **Systemic Implications and Integration Strategy**

The architectural reality exposed by these comparative systems mandates a specific operational paradigm for advanced social simulation mods like Chronicle. Attempting to track global, continuous updates across thousands of actors (the *Prom Week* model) is computationally inviable within modern rendering engines. Conversely, relying purely on rigid, boolean faction flags invites catastrophic emergent behaviors, as evidenced by *Dwarf Fortress*'s loyalty cascades.  
The optimal strategy requires synthesizing these approaches. The underlying data model must adopt James Ryan's provenance and distortion architecture, allowing rumors to mutate as they traverse a directed acyclic graph. However, the evaluation of this data must mirror the localized, on-demand query structure utilized by the *Watch Dogs: Legion* Census system and *City of Gangsters*, calculating relationship thresholds only when contextually necessary. Most importantly, this external logic must never attempt to render its own bespoke scenes; it must calculate the social state externally and inject the payload into the host engine via native hooks like SendStoryEvent, treating Bethesda's Radiant Story manager as a sophisticated, pre-built rendering client for a dynamically evolving narrative graph.

#### **Works cited**

> 1. Legends of the Dead \- CK3 Wiki, [https://ck3.paradoxwikis.com/Legends\_of\_the\_Dead](https://ck3.paradoxwikis.com/Legends_of_the_Dead)  
> 2. Crusader Kings III \- Wikipedia, [https://en.wikipedia.org/wiki/Crusader\_Kings\_III](https://en.wikipedia.org/wiki/Crusader_Kings_III)  
> 3. Character \- CK3 Wiki, [https://ck3.paradoxwikis.com/Character](https://ck3.paradoxwikis.com/Character)  
> 4. Guide :: How To Spread Legends \- Steam Community, [https://steamcommunity.com/sharedfiles/filedetails/?id=3514511826](https://steamcommunity.com/sharedfiles/filedetails/?id=3514511826)  
> 5. but as many of you have rightfully pointed out, the general ... \- Steam, [https://store.steampowered.com/news/posts/?feed=steam\_community\_announcements\&appids=1158310\&enddate=1715155602](https://store.steampowered.com/news/posts/?feed=steam_community_announcements&appids=1158310&enddate=1715155602)  
> 6. Barony \- CK3 Wiki, [https://ck3.paradoxwikis.com/Barony](https://ck3.paradoxwikis.com/Barony)  
> 7. Struggles \- CK3 Wiki, [https://ck3.paradoxwikis.com/index.php?title=Struggles](https://ck3.paradoxwikis.com/index.php?title=Struggles)  
> 8. Editing Casus belli \- CK3 Wiki, [https://ck3.paradoxwikis.com/index.php?title=Casus\_belli\&veaction=edit\&mobileaction=toggle\_view\_desktop](https://ck3.paradoxwikis.com/index.php?title=Casus_belli&veaction=edit&mobileaction=toggle_view_desktop)  
> 9. Struggle modding \- CK3 Wiki, [https://ck3.paradoxwikis.com/Struggle\_modding](https://ck3.paradoxwikis.com/Struggle_modding)  
> 10. Struggle system sucks, why include it in Persia? : r/CrusaderKings, [https://www.reddit.com/r/CrusaderKings/comments/175jiwv/struggle\_system\_sucks\_why\_include\_it\_in\_persia/](https://www.reddit.com/r/CrusaderKings/comments/175jiwv/struggle_system_sucks_why_include_it_in_persia/)  
> 11. Casus belli \- CK3 Wiki, [https://ck3.paradoxwikis.com/Casus\_belli](https://ck3.paradoxwikis.com/Casus_belli)  
> 12. Guide for Middle-earth: Shadow of War \- Story Walkthrough, [https://www.trueachievements.com/game/Middle-earth-Shadow-of-War/walkthrough/3](https://www.trueachievements.com/game/Middle-earth-Shadow-of-War/walkthrough/3)  
> 13. The Thread of Tips and Tricks : r/shadowofmordor \- Reddit, [https://www.reddit.com/r/shadowofmordor/comments/2i02d0/the\_thread\_of\_tips\_and\_tricks/](https://www.reddit.com/r/shadowofmordor/comments/2i02d0/the_thread_of_tips_and_tricks/)  
> 14. Middle-earth Shadow of War: How to Get a Nemesis \- Twinfinite, [https://twinfinite.net/guides/middle-earth-shadow-of-war-how-get-nemesis/](https://twinfinite.net/guides/middle-earth-shadow-of-war-how-get-nemesis/)  
> 15. This happened to me in the first hour. There were also plenty of, [https://www.reddit.com/r/shadowofmordor/comments/2hwi9u/this\_happened\_to\_me\_in\_the\_first\_hour\_there\_were/](https://www.reddit.com/r/shadowofmordor/comments/2hwi9u/this_happened_to_me_in_the_first_hour_there_were/)  
> 16. Something went wrong while displaying this content. Refresh, [https://steamcommunity.com/app/294100/discussions/0/1729827777335846049/](https://steamcommunity.com/app/294100/discussions/0/1729827777335846049/)  
> 17. Rimworld output log published using HugsLib · GitHub, [https://gist.github.com/HugsLibRecordKeeper/ad3f6365a0c645154d6f77617b2ce7d1](https://gist.github.com/HugsLibRecordKeeper/ad3f6365a0c645154d6f77617b2ce7d1)  
> 18. Rimworld output log published using HugsLib · GitHub, [https://gist.github.com/HugsLibRecordKeeper/72ed22782c9fa8a631491dacb9d1bb4f](https://gist.github.com/HugsLibRecordKeeper/72ed22782c9fa8a631491dacb9d1bb4f)  
> 19. Trying to start a chain to dismantle thieves :: Dwarf Fortress General, [https://steamcommunity.com/app/975370/discussions/0/3773490215222410492/](https://steamcommunity.com/app/975370/discussions/0/3773490215222410492/)  
> 20. v0.34:Faction \- Dwarf Fortress Wiki, [https://dwarffortresswiki.org/index.php/v0.34:Faction](https://dwarffortresswiki.org/index.php/v0.34:Faction)  
> 21. Faction \- Dwarf Fortress Wiki, [http://dwarffortresswiki.org/index.php/Loyalty\_cascade](http://dwarffortresswiki.org/index.php/Loyalty_cascade)  
> 22. The Number One Educational Resource for the Game Industry, [https://gdcvault.com/free/gdc-21/?\&media=s](https://gdcvault.com/free/gdc-21/?&media=s)  
> 23. The Systemic Backbone Behind Play As Anyone in 'Watch Dogs, [https://www.gdcvault.com/play/1027018/Census-The-Systemic-Backbone-Behind](https://www.gdcvault.com/play/1027018/Census-The-Systemic-Backbone-Behind)  
> 24. A Memory-Driven Action Selection Framework for Scalable Ambient, [https://www.csd.uwo.ca/\~ebuitron/downloads/ProjectReport.pdf](https://www.csd.uwo.ca/~ebuitron/downloads/ProjectReport.pdf)  
> 25. Felt: A Simple Story Sifter \- ResearchGate, [https://www.researchgate.net/publication/337187229\_Felt\_A\_Simple\_Story\_Sifter](https://www.researchgate.net/publication/337187229_Felt_A_Simple_Story_Sifter)