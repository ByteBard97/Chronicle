---
date: 2026-08-26
sources:
  - "NPC Psychological State Mapping Research.md"
topic: "translating internal emotional/psychological state into legible NPC behavior — second independent pass"
status: filed
---

# Emotion/Behavior Legibility, v2

Second independent pass on the same ground as
[emotion-behavior-legibility-rimworld-dwarf-fortress.md](emotion-behavior-legibility-rimworld-dwarf-fortress.md).

# **Systemic Architectural Analysis: Translating Internal Psychological States into Expressive AI Behaviors for 3D Role-Playing Simulations**

## **1\. The Architectural Challenge of Simulated Psychology in Spatial Environments**

The integration of complex, unseen psychological variables into visible, legible non-player character (NPC) behaviors represents one of the most sophisticated engineering challenges in systemic game design. The objective of the "Chronicle" project—an external Python-based social-simulation service that tracks internal beliefs such as grudges, grief, and fear for roughly one hundred and fifty named NPCs, subsequently injecting resulting behaviors into the *The Elder Scrolls V: Skyrim* engine—requires a highly robust translation layer. This layer must bridge abstract mathematical matrices operating in a headless process with the embodied physical actions executed by the game engine's Radiant AI system. If the system fails to translate these states effectively, the player will perceive the resulting behavioral shifts not as intentional narrative developments, but as artificial intelligence (AI) logic errors or engine glitches.  
To architect a solution that avoids this pitfall, this report examines the methodologies utilized by industry-leading systemic simulations, specifically isolating the stress systems of *Dwarf Fortress* and the mood volatility mechanics of *RimWorld*. By deconstructing the deterministic state-machine overrides utilized in the former and the weighted stochastic selection algorithms employed in the latter, the analysis provides a comprehensive roadmap for adapting these discrete logic frameworks to a real-time, 3D action role-playing game. Furthermore, the analysis heavily emphasizes the critical concepts of "procedural acting" and "legibility"—ensuring the player correctly attributes sudden changes in NPC behavior to the underlying social simulation. Finally, the report outlines the technical limitations of the *Skyrim* Papyrus Virtual Machine (VM) and prescribes optimal methods for injecting high-priority AI packages via SKSE (Skyrim Script Extender) to achieve seamless, performant behavioral overrides without inducing script latency or stack dumps.

## **2\. Theoretical Foundations: Expressive AI, Procedural Acting, and the Legible Mind**

Before examining specific algorithmic implementations, it is necessary to establish the theoretical framework that governs how human players interpret simulated computational behaviors. Game design theorists and artificial intelligence researchers conceptualize this challenge through the dual lenses of Expressive AI and HCI (Human-Computer Interaction) legibility1.

### **2.1. Expressive AI and the Illusion of an Inner Life**

The evolution of architectures for virtual agents reveals a history of principled trade-offs between optimization, scalability, and behavioral richness2. Dominant AI paradigms in the game industry, such as Finite State Machines (FSMs) and Behavior Trees (BTs), have historically optimized for qualities like robustness and predictable pathfinding. However, in making these necessary trades, the nuance of the decision-making process and the capacity for expressive performance are frequently deprioritized2.  
Expressive AI, a concept heavily championed by researchers such as Michael Mateas in the context of interactive drama, focuses on creating computational artifacts that a human audience perceives as intelligent, meaningful, and emotionally grounded2. In a traditional combat AI framework, the architecture optimizes for spatial reasoning and tactical challenge4. Conversely, in a systemic social simulation like the Chronicle mod, the ultimate measure of the agent is not the elegance of its internal algorithms, but the quality of its external performance2.  
This theoretical perspective gives rise to the practical goal of "procedural acting," a methodology where the execution of an AI task is intentionally imbued with character and style to communicate internal justifications2. If an NPC in the Chronicle system experiences a severe spike in their internal "grief" metric, the system must not simply decrement a background productivity multiplier. It must fundamentally alter the physical expression of the character in the 3D space to communicate that grief, acting as a bridge between the unseen Python logic and the player's sensory experience.

### **2.2. The Legible Mind in Game Design**

Legibility, in the context of human-computer interaction, refers to the ease with which users can read, understand, and predict the behavior of a complex interface1. Applied to NPC behavior, the "legible mind" refers to the simulated consciousness as it appears through readable artifacts: texts, speech acts, and physical behaviors1. The modern era of generative AI excels at producing highly legible, predictable outputs that mimic consciousness, but true systemic simulation requires a different type of legibility—one that maps direct causality from a specific event to a specific behavior1.  
If an NPC suddenly abandons their post at a market stall to wander aimlessly or flee into a building, a lack of behavioral legibility will inevitably cause the player to assume the pathfinding navmesh is broken, or that an underlying Papyrus script has stalled. To bridge this cognitive gap, the game environment must provide "meta-legibility"—signals that explicitly connect the external action to the internal variable1. Both *Dwarf Fortress* and *RimWorld* solve this legibility problem through distinct mechanisms dictated by their isometric perspectives, detailed logging, and UI paradigms. Translating these two-dimensional UI solutions into a first-person or third-person 3D environment requires converting abstract telegraphing into concrete spatial and auditory cues.

## **3\. Dwarf Fortress: Deep State Accumulation and Deterministic Fracture**

*Dwarf Fortress* approaches the modeling of psychological states through deep, longitudinal tracking of memory, emotion, and exposure to trauma. The game utilizes highly deterministic mappings based on intrinsic personality facets to dictate the exact nature of a character's psychological breakdown, resulting in a systemic cascade often referred to by the player base as a "tantrum spiral"5.

### **3.1. The Calculus of Stress: Short-Term Emotion and Long-Term Memory**

Internally, the stress level of a dwarf is mathematically tracked using two distinct numerical axes: short-term stress and long-term stress, operating independently but continuously feeding into one another7.  
Short-term stress operates on a scale ranging from \-100,000 to \+100,0007. This value fluctuates rapidly based on immediate emotional reactions to stimuli in the environment. Examples include being caught in the rain, eating a masterwork meal crafted from preferred ingredients, or witnessing the death of a fellow citizen7. Short-term stress correlates directly with the creature's immediate mood, represented in the game's UI by simple status icons ranging from ecstatic to miserable7.  
Long-term stress operates on a separate scale ranging from \-50,000 to \+120,0007. This metric represents a gradual, persistent accumulation of short-term stress over years of simulated time. Under standard engine parameters, long-term stress is highly resistant to rapid change; it can increase by a maximum of 20,160 points per year, and decrease by a maximum of 43,564 points per year7. This ensures that a dwarf requires years of sustained trauma to become irrevocably damaged, but also requires years of sustained luxury to fully recover7.  
The mechanical bridge between these two metrics is the dwarf's memory system. A dwarf possesses a strict limit of eight long-term memory "slots"10. When a dwarf experiences a strong emotion, it generates "stress points" based on a designated severity multiplier. For example, feeling "Horrified" upon seeing a corpse carries a severe \+1 stress multiplier, while feeling "Blissful" carries a highly beneficial \-1 multiplier9. If a dwarf is repeatedly subjected to negative stimuli before positive memories can be organically formed and retained, their long-term memory slots fill entirely with negative anchors10. This creates a relentless source of passive stress generation that is exceedingly difficult to flush out, fundamentally altering the dwarf's psychological baseline10.

### **3.2. Personality Facets as Deterministic Modifiers**

The rate at which a dwarf accumulates these stress points, and the specific behavioral breakdown they exhibit when critical thresholds are crossed, is heavily modified by an array of underlying, procedurally generated personality traits8. The game engine assigns these personality values based on creature definitions in the raw text files, generally operating on a scale with a designated minimum, median, and maximum (e.g., \[PERSONALITY:STRESS\_VULNERABILITY:0:45:100\])11.  
Several key traits dictate the flow of the psychological simulation:

* **Stress Vulnerability:** This value acts as a flat multiplier on the impact of negative thoughts. Lower values indicate a naturally higher resilience to trauma, while high values guarantee rapid escalation toward a breakdown11.  
* **Bravery:** This trait determines the specific emotional reaction a dwarf has to traumatic events, most notably the sight of corpses. A brave dwarf may only register the event as making them "Uneasy," whereas a cowardly dwarf will be "Horrified," accumulating vastly more short-term stress from the exact same spatial stimulus9. Continued exposure can alter this, eventually leading to a "hardened" status where the dwarf feels nothing upon seeing death9.  
* **Propensities (Anger, Depression, Anxiety):** These traits act as strict routing mechanisms for the AI state machine. When a dwarf's combined short-term and long-term stress exceeds critical failure thresholds, these propensities determine the exact *type* of behavioral breakdown that occurs6.

### **3.3. Thresholds and the Behavioral Decision Tree**

When a dwarf reaches specific numerical thresholds of positive (negative-impact) stress, the game alters their baseline status, eventually triggering a state-machine transition into a temporary breakdown7.

| Stress Threshold | Engine Status Indicator | Mechanical and Behavioral Impact |
| :---- | :---- | :---- |
| \+10,000 | Early Warning Phase | Initial negative thoughts begin to populate the UI. The entity functions normally but is trending downward. |
| \+25,000 | "Stressed" Status | The UI status icon flashes with a downward red arrow. Vulnerability to temporary emotional breakdowns begins.7 |
| \+50,000 | "Haggard" Status | Physical descriptions in the text logs alter (e.g., "drawn and haggard"). The frequency of temporary breakdowns increases significantly.7 |
| \+100,000 | "Harrowed" Status | Severe, persistent psychological damage. The dwarf faces an imminent and constant risk of permanent, terminal insanity.7 |

The mapping of these stress thresholds to specific behaviors operates as a deterministic routing based on the dwarf's highest propensity trait6:

> 1. **High Anger Propensity mapped to Tantrum:** The dwarf forcibly cancels all current jobs, begins toppling furniture, destroying constructed buildings, and physically attacking fellow citizens or tame animals6. This state ignores legal parameters and often initiates a violence cascade.  
> 2. **High Depression Propensity mapped to Depression:** The dwarf cancels all active jobs and wanders the fortress aimlessly, becoming entirely unresponsive to the world and completely ceasing industrial output6.  
> 3. **High Anxiety Propensity mapped to Obliviousness:** The dwarf stumbles around oblivious to their surroundings, failing to react to threats or engage with tasks6.

If the stress remains unchecked and the threshold remains above critical levels, these temporary breakdowns eventually escalate into permanent, unrecoverable states of insanity. Tantrums escalate into **Berserk** rages where the dwarf attempts to murder anyone in sight until killed; Depression escalates into terminal **Melancholy** where the dwarf intentionally starves or drowns themselves; and Obliviousness degenerates into **Stark Raving Mad** behavior, wherein the dwarf strips off their clothing and babbles erratically until they die of dehydration5.

### **3.4. The Distinction Between Strange Moods and Psychological Breaks**

It is a common design misconception that "Strange Moods" are a byproduct of the stress system. In *Dwarf Fortress*, strange moods are distinct, periodic, inspiration-driven events triggered when a fortress population exceeds twenty dwarves and the global artifact cap has not yet been reached16. A strange mood operates as an absolute state-machine hijack: the dwarf drops all tasks, claims a specific workshop, and demands specific materials to construct a legendary artifact16.  
However, strange moods intersect violently with the psychological system upon their failure. If the dwarf cannot acquire the necessary materials within a handful of simulated months, the mood collapses. This failure instantly bypasses the standard stress accumulation limits and injects the dwarf directly into the terminal insanity decision tree (Berserk, Melancholy, or Stark Raving Mad) regardless of their prior psychological health15.

### **3.5. Job Interruption and State-Machine Transitions**

When a psychological threshold is crossed, the *Dwarf Fortress* engine handles the behavioral shift via an immediate and forceful job cancellation6. The dwarf's currently active task (e.g., hauling stone, mining a vein, engraving a wall) is instantly aborted, generating a system notification to the player (e.g., "Urist McMiner cancels dig").  
The underlying architecture operates as a rigid finite state machine (FSM) override. The breakdown state is injected into the entity at the highest possible priority level, suppressing the standard utility logic or behavior tree evaluations that normally guide the dwarf to satisfy physiological needs6. During a tantrum, the dwarf registers no standard needs for food, water, or sleep; they are entirely consumed by the execution of the breakdown state6. Only upon the expiration of the temporary breakdown does the state machine return control to the standard job queue.

### **3.6. Resolution Mechanics: Decay versus Permanence**

In *Dwarf Fortress*, temporary breakdowns resolve naturally as the short-term state expires (typically lasting several days), returning control to the standard job queue. However, the underlying long-term stress does not vanish; it must mathematically decay over time6.  
This decay requires extreme, intentional player intervention to resolve. The player must architect the environment to flood the dwarf with positive modifiers: providing masterwork meals, constructing legendary dining rooms, carving indoor waterfalls to generate positive mist thoughts, and strictly isolating the dwarf from traumatic stimuli like corpses or combat8. Terminal insanity states (Berserk, Melancholy, Stark Raving Mad), conversely, possess no resolution mechanics whatsoever and are permanently fatal to the character's utility within the simulation6.

## **4\. RimWorld: Threshold Volatility and Weighted Stochastic Selection**

While *Dwarf Fortress* relies on deep historical memory tracking and deterministic routing based on traits, *RimWorld* utilizes a highly volatile, immediate mood system coupled with a weighted stochastic (random) selection algorithm to determine the nature of a breakdown. This creates a vastly different cadence for the player, emphasizing immediate crisis management over decade-long psychological conditioning.

### **4.1. Mood Tiers and the Mean Time Between (MTB) Triggers**

In *RimWorld*, a pawn's psychological state is governed by a singular, highly visible "Mood" percentage (0-100%), which is modified dynamically by a stack of active thoughts with specific durations19. Breakdowns in this engine are not guaranteed the exact moment a pawn's mood drops below a given threshold; rather, the game utilizes a Mean Time Between (MTB) ticking system to introduce stochastic unpredictability19.  
The game engine periodically checks the pawn's state through a master method, typically identified in the decompiled C\# source code as MentalBreakerTick21. This ticking mechanism evaluates whether the mood has fallen below specific, tiered thresholds, each possessing a different MTB value:

* **Minor Break Threshold:** Operates on an MTB of 5.0 in-game days20.  
* **Major Break Threshold:** Operates on an MTB of 1.0 in-game days20.  
* **Extreme Break Threshold:** Operates on an MTB of 0.6 in-game days20.

Because this system relies on MTB rather than absolute boolean triggers, a pawn can hypothetically sit within the Extreme Break threshold for several hours of gameplay without breaking, or they might break almost immediately upon crossing the line. This stochastic timing prevents players from min-maxing exact-tick interventions, maintaining narrative tension and forcing players to proactively manage mood rather than reacting at the exact millisecond of failure19.

### **4.2. Break Selection Algorithm: BreakCanOccur and RandomElementByWeight**

Once the MTB trigger successfully fires, the *RimWorld* engine must select which specific mental break to apply to the pawn. It does not map deterministically to a single personality trait like *Dwarf Fortress*. Instead, the C\# codebase utilizes a dynamic filtering method, tracked in the source as MentalBreakWorker.BreakCanOccur22.  
This method builds a comprehensive list of all currently eligible mental breaks for that specific threshold tier. Once the pool of valid breaks is established, the game utilizes a core utility function, Verse.GenCollection.RandomElementByWeight, to select the specific behavior from the list22.  
Every mental break in the game's XML definitions possesses a base selection weight. However, pawn traits heavily modify these mathematical weights. For example:

* A pawn possessing the "Pyromaniac" trait applies a massive multiplier to the weight of the "Fire Starting Spree" break, ensuring it is highly likely to be selected.  
* A pawn with the "Gourmand" trait applies a heavy weight multiplier to the "Food Binge" break.

This hybrid architectural approach—a weighted random selection heavily modified by deterministic trait characteristics—ensures that pawns generally act in accordance with their established personalities, while still allowing for emergent, unpredictable systemic results that prevent the game from feeling overly rigid22.

### **4.3. Telegraphing: The "Break Risk" UI Mechanics**

Legibility in *RimWorld* is handled almost exclusively through its graphical user interface. The game features an omnipresent alert system docked on the right side of the screen. As a pawn's mood approaches and subsequently crosses critical thresholds, highly visible warnings ("Break Risk: Minor", "Break Risk: Major", "Break Risk: Extreme") appear, accompanied by distinct auditory cues26.  
This explicit telegraphing informs the player exactly *why* a pawn is at risk of misbehaving. The player can click the affected pawn, open the dedicated "Needs" tab, and directly read the exact numerical modifiers (e.g., "Ate without table \-3", "Witnessed ally's death \-5", "In intense pain \-10") that are currently suppressing the mood score. This absolute transparency ensures the player blames their own base management or recent environmental factors rather than the AI engine when a pawn begins smashing critical components.

### **4.4. Resolution Mechanics: Catharsis versus Violent Intervention**

*RimWorld* features a highly structured, mechanically impactful resolution system. If a mental break is allowed to run its course without player intervention, the behavior state eventually expires. Upon natural expiration, the pawn receives a specific thought modifier termed "Catharsis," which applies a massive \+40 mood offset for a duration of 3 in-game days27. This massive buff effectively acts as a mechanical cooldown for the system; it renders the pawn highly resistant to further mental breaks, providing the player with a critical grace period to fix the underlying logistical or environmental issues causing the stress27.  
Alternatively, the player can choose to forcefully intervene in the simulation:

> 1. **Arrest and Imprisonment:** A colonist assigned to the Warden role can attempt to arrest the breaking pawn. If successful, this immediately terminates the mental break by changing their faction status to prisoner. However, doing so completely negates the Catharsis buff and applies an additional "-8 Was Imprisoned" debuff, ensuring the pawn remains at high risk for further breaks upon their eventual release27.  
> 2. **Violent Suppression:** Players can draft other pawns to physically beat the breaking pawn into submission using blunt or lethal weapons. While this successfully aborts the break state, it results in severe pain debuffs, potential permanent injury, or accidental death27. Interestingly, downing a pawn via pain shock *does* grant the Catharsis buff upon waking, creating a brutal but mechanically viable intervention strategy27.

## **5\. Adapting Simulation Mechanics for the "Chronicle" Engine**

Transitioning these sophisticated simulation mechanics from top-down, UI-heavy management simulators into a real-time, 3D Action RPG like *Skyrim* introduces immense technical and design hurdles. *Skyrim*'s Creation Engine does not natively support deep, psychological ticking for hundreds of NPCs. The Chronicle mod's architecture—tracking beliefs in a headless Python process and pushing them into the game engine—is the correct structural approach to bypass engine limitations. However, it must interface cleanly with the Papyrus Virtual Machine and the Radiant AI package system to function without catastrophic performance degradation.

### **5.1. Evaluating AI Paradigms: Why Utility AI is Superior for Skyrim**

When mapping continuous psychological variables (grief, fear, grudges) to discrete actions, the developer must choose an AI paradigm. The industry standard approaches include Finite State Machines (FSM), Behavior Trees (BT), Goal-Oriented Action Planning (GOAP), and Utility AI4.

* **FSMs and Behavior Trees:** These are binary and hierarchical. As seen in *Dwarf Fortress*, when a threshold is met, the FSM completely overrides all other logic18. In a 3D RPG, this binary snapping (an NPC instantly transitioning from forging a sword to running in terror the millisecond fear hits 61\) appears jarring and artificial.  
* **GOAP:** While excellent for emergent behavior, writing custom planners for 150 NPCs requires immense computational overhead and is highly prone to edge-case failures in an open world4.  
* **Utility AI:** This paradigm replaces binary state transitions with scored action selection4. Every potential action is assigned a utility score based on weighted input curves. The agent simply selects whichever action scores highest at a given tick4.

For Chronicle, Utility AI paired with Sigmoid curves is the optimal approach for the headless Python backend29. Instead of using hard thresholds, the Python backend should utilize a Sigmoid (Logistic) curve for each emotional belief:  
![][image1]  
Where ![][image2] is the raw belief score (e.g., Fear), ![][image3] is the inflection threshold (e.g., 60), and ![][image4] is the steepness of the curve30. This ensures that as a grudge score rises from 50 to 70, the probability (utility score) of the NPC executing a hostile action scales smoothly, rather than snapping on like a light switch29. The Python engine evaluates these curves, and when the utility score for a breakdown action surpasses the score for their standard schedule, the Python script sends the execution command to Skyrim.

### **5.2. Translating Python Data to Papyrus AI Overrides**

Once the Python backend determines an action is necessary, it must manipulate *Skyrim*'s AI. *Skyrim* operates on a package stack system32. Every NPC possesses a base list of packages (e.g., sandbox at the market from 8 AM to 6 PM, sleep from 10 PM to 6 AM). When multiple packages are valid based on time and conditions, the engine selects the highest-priority package in the stack32.  
To inject a behavioral breakdown without permanently destroying the NPC's base schedule, Chronicle must utilize **Quest Aliases**34.

> 1. Chronicle should maintain a background, invisible Quest in the Creation Kit assigned an exceptionally high Priority value34.  
> 2. When the Python process determines an NPC has crossed a utility threshold, it communicates with the SKSE C++ plugin (via JSON parsing using PapyrusUtil or direct socket communication)36.  
> 3. A Papyrus script dynamically forces the target NPC into a specific Reference Alias within that high-priority Quest38.  
> 4. This Alias holds the specific breakdown AI Packages (e.g., Chronicle\_Grief\_SandboxHome). Because the Quest possesses a high priority, packages applied through its aliases are injected at the very top of the NPC's package stack, immediately overriding their base schedule32.

### **5.3. Managing EvaluatePackage() and Papyrus VM Constraints**

Merely placing an NPC into an alias does not immediately alter their current action; the engine must be instructed to recalculate the package stack. This is achieved via the Papyrus command Actor.EvaluatePackage()39.  
However, EvaluatePackage() carries severe caveats. Invoking this function can yield highly undesired results with in-progress Travel packages40. If an NPC is currently in the middle of a navmesh transition from Riverwood to Whiterun, calling EvaluatePackage() may cause the current travel package to persist for a random duration until a specific pathing node is reached, making the AI look temporarily broken or unresponsive33. To mitigate this, breakdown packages injected by Chronicle should utilize "Near Self" or "Near Package Start" location data to prevent long-distance pathing conflicts when the stack is re-evaluated33.  
Furthermore, the developer must strictly adhere to the performance constraints of the Papyrus VM. *Skyrim*'s script engine operates on strict time budgets per frame, controlled by the INI setting iMaxOpsPerFrame41. By default, Papyrus is only allotted 1.2ms of computation time out of a standard 16.67ms frame time (at 60 FPS)41.  
If Chronicle's Python backend dumps state updates for 150 NPCs simultaneously, running 150 JSON reads, 150 alias fills, and 150 EvaluatePackage() calls in a single frame will catastrophically overwhelm the VM. This results in severe script lag, delayed animations, frozen AI, and potential save file bloat as the VM attempts to catch up41.  
To ensure stability, the SKSE plugin or the parsing Papyrus script must implement a queueing system. The Python backend sends state transitions as they occur, but the Papyrus engine must stagger the alias fills and EvaluatePackage() calls over several frames (e.g., processing a maximum of 3-5 NPCs per second). This ensures script execution remains well below the iMaxOpsPerFrame threshold, maintaining a stable 60 FPS while the social simulation continues seamlessly in the background44.

## **6\. Legibility Techniques for 3D Spatial Environments**

In a 3D, fully voiced game like *Skyrim*, the player does not have access to a UI overlay flashing "Break Risk: Major." If an NPC alters their behavior, the player must be able to read the *intent* of that alteration seamlessly in the physical space2. Legibility must be meticulously engineered into the visual and auditory presentation of the mod.

### **6.1. Visual and Spatial Telegraphing**

To prevent the appearance of AI pathfinding bugs, the altered AI packages must utilize highly specific Idle Animations.

* When a Grief package is injected, the package should heavily utilize the PlayIdle Papyrus function or the package's built-in idle marker assignment46. Rather than simply standing still, the NPC should use animations like IdleSad, IdleWarmingHands, or sitting dejectedly on a bed.  
* For Fear or Anxiety, packages should utilize faster pacing movement types rather than standard walking, and incorporate physical distancing logic (ensuring the package evaluates a larger keep-away radius from the source of the fear).

### **6.2. Auditory Telegraphing via the Story Manager**

The most potent tool for legibility in *Skyrim* is voice dialogue. When an NPC is under the effects of a Chronicle breakdown alias, the mod must intercept their standard dialogue greetings.  
The Papyrus architecture provides the SendStoryEvent function, which interfaces directly with the game's Story Manager39. Chronicle can use this to force the engine to push specific ambient dialogue lines tailored to the psychological state. If an NPC possesses a Grudge \> 60 against the player, the system triggers an event that suppresses standard merchant greetings and forces the NPC to use hostile ambient dialogue (e.g., "You've got a lot of nerve coming around here").  
For severe emotional breakdowns, the alias should contain an AI package utilizing the ForceGreet flag. If the player approaches a grieving NPC, the NPC actively initiates dialogue to say, "Leave me alone, I can't bear this right now." This immediately informs the player that the erratic behavior is a designed narrative state, establishing absolute legibility and preventing the assumption of a game glitch.

### **6.3. Resolution: The "Catharsis" Equivalent**

To prevent the simulated world state from deteriorating into permanent gridlock (as seen in unchecked *Dwarf Fortress* spirals), Chronicle must implement a resolution mechanic mirroring *RimWorld*'s Catharsis system27.  
If an NPC successfully completes a breakdown package (e.g., spends 12 in-game hours executing the Grief\_Sandbox alias), the Python backend should automatically decay the grief score and apply a "Catharsis" boolean to that specific character. For a designated duration (e.g., 48 in-game hours), that NPC becomes mathematically immune to further grief or fear breakdowns in the utility scoring algorithm. This ensures the 3D space remains dynamic and playable. Furthermore, this resolution should be made legible: upon exiting the alias, the NPC should be assigned a high-priority dialogue line for their next interaction (e.g., "I've had a hard time lately, but I'm feeling better"), cleanly communicating the end of the behavioral arc to the player.

## **7\. Strategic Recommendations and Implementation Summary**

To successfully implement the Chronicle social-simulation service within the strict constraints of the *Skyrim* engine, the architecture must synthesize the deep state tracking of *Dwarf Fortress* with the stochastic, easily resolvable mechanics of *RimWorld*, all filtered through the spatial legibility requirements of a 3D environment.

### **7.1. Recommended Threshold-to-Behavior Mapping**

| Psychological State | Python Trigger Methodology | Papyrus Alias & Package Implementation |
| :---- | :---- | :---- |
| **Grief** (e.g., Score \> 70\) | Sigmoid curve ensures the utility score scales smoothly over time. | **Alias Injection:** Sandbox\_Isolated. The NPC retreats to a private marker, utilizing IdleSad animations. Overrides standard work packages. |
| **Grudge** (e.g., Score \> 60\) | Utility score spikes heavily if the target of the grudge enters a specific spatial radius. | **Alias Injection:** Follow\_Target\_Distance. The NPC stalks or glares at the target, utilizing SendStoryEvent to force hostile ambient dialogue. |
| **Fear** (e.g., Score \> 80\) | Evaluated via MTB ticks (mirroring *RimWorld*) to prevent constant stuttering and oscillation. | **Alias Injection:** Flee\_From\_Target or Sandbox\_Hide. The NPC actively avoids the target, employing fast-paced movement modifiers. |

### **7.2. Core Architectural Directives**

> 1. **Backend Calculation (Python):** Maintain all belief tracking in the external Python process. Use Utility AI sigmoid curves to score the likelihood of a breakdown, checking these scores on an MTB tick system to prevent rapid, immersion-breaking behavioral oscillation.  
> 2. **SKSE Injection (C++ / JSON):** Pass state changes to the game sparingly. Never update 150 NPCs per frame. Queue the updates to rigorously respect the iMaxOpsPerFrame limits of the Papyrus VM, processing only a few EvaluatePackage() calls per second.  
> 3. **Alias-Driven State Machines (Creation Kit):** Do not permanently edit base NPC records. Create a master Chronicle Quest with high priority. Dynamically force NPCs into reference aliases containing the breakdown AI packages, allowing the engine's native stack rules to handle the override gracefully.  
> 4. **Absolute Legibility:** Ensure every injected package utilizes explicit idle animations, spatial distancing, and interceptive dialogue (via SendStoryEvent or forced greetings). The player must physically see and hear the NPC's emotional state to accept the simulation as intentional design rather than engine failure.

By adhering strictly to these architectural paradigms, the Chronicle system can successfully circumvent the rigid limitations of traditional game AI, achieving a level of procedural acting that profoundly deepens the player's engagement with the simulated world without sacrificing engine stability.

#### **Works cited**

> 1. The Legible Mind: How Generative AI Flattens Consciousness, [https://bircu-journal.com/index.php/birci/article/download/8232/pdf](https://bircu-journal.com/index.php/birci/article/download/8232/pdf)  
> 2. An Architecture for Argument-Driven, Dynamic Character Performance, [https://ojs.aaai.org/index.php/AIIDE/article/download/36832/38970/40909](https://ojs.aaai.org/index.php/AIIDE/article/download/36832/38970/40909)  
> 3. Expressive AI: A Hybrid Art and Science Practice \- ResearchGate, [https://www.researchgate.net/publication/2572141\_Expressive\_AI\_A\_Hybrid\_Art\_and\_Science\_Practice](https://www.researchgate.net/publication/2572141_Expressive_AI_A_Hybrid_Art_and_Science_Practice)  
> 4. AI and NPC Behavior Systems in Video Game Development, [https://videogamedevelopmentauthority.com/ai-and-npc-behavior-systems/](https://videogamedevelopmentauthority.com/ai-and-npc-behavior-systems/)  
> 5. Dwarf Fortress (Video Game) \- TV Tropes, [https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/DwarfFortress](https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/DwarfFortress)  
> 6. Mental breakdown \- Dwarf Fortress Wiki, [https://dwarffortresswiki.org/index.php/Mental\_breakdown](https://dwarffortresswiki.org/index.php/Mental_breakdown)  
> 7. Stress \- Dwarf Fortress Wiki, [https://dwarffortresswiki.org/Stress](https://dwarffortresswiki.org/Stress)  
> 8. DF2014:Stress \- Dwarf Fortress Wiki, [https://dwarffortresswiki.org/index.php/DF2014:Stress](https://dwarffortresswiki.org/index.php/DF2014:Stress)  
> 9. Avoiding stress from siege cleanup. How to strategically engineer, [https://www.reddit.com/r/dwarffortress/comments/aeqtfy/avoiding\_stress\_from\_siege\_cleanup\_how\_to/](https://www.reddit.com/r/dwarffortress/comments/aeqtfy/avoiding_stress_from_siege_cleanup_how_to/)  
> 10. I think I've figured out the stress spiral \- thoughts? : r/dwarffortress, [https://www.reddit.com/r/dwarffortress/comments/hjt112/i\_think\_ive\_figured\_out\_the\_stress\_spiral\_thoughts/](https://www.reddit.com/r/dwarffortress/comments/hjt112/i_think_ive_figured_out_the_stress_spiral_thoughts/)  
> 11. The game is broken right now and the fun is starting to fade. \- Reddit, [https://www.reddit.com/r/dwarffortress/comments/bnrzq3/the\_game\_is\_broken\_right\_now\_and\_the\_fun\_is/](https://www.reddit.com/r/dwarffortress/comments/bnrzq3/the_game_is_broken_right_now_and_the_fun_is/)  
> 12. DF2014:String dump \- Dwarf Fortress Wiki, [https://dwarffortresswiki.org/index.php/DF2014:String\_dump](https://dwarffortresswiki.org/index.php/DF2014:String_dump)  
> 13. String dump \- Dwarf Fortress Wiki, [https://dfwk.ru/String\_dump](https://dfwk.ru/String_dump)  
> 14. Status icon \- Dwarf Fortress Wiki, [https://dwarffortresswiki.org/index.php/Status\_icon](https://dwarffortresswiki.org/index.php/Status_icon)  
> 15. DF2014:Status icon \- Dwarf Fortress Wiki, [https://dwarffortresswiki.org/index.php/DF2014:Status\_icon](https://dwarffortresswiki.org/index.php/DF2014:Status_icon)  
> 16. Strange mood \- Dwarf Fortress Wiki, [https://dwarffortresswiki.org/index.php/Strange\_mood](https://dwarffortresswiki.org/index.php/Strange_mood)  
> 17. Full text of "Dwarf\_Fortress\_-\_Boatmurdered.pdf (PDFy mirror)", [https://archive.org/stream/pdfy-Rh647daG51aaK0jJ/Dwarf\_Fortress\_-\_Boatmurdered\_djvu.txt](https://archive.org/stream/pdfy-Rh647daG51aaK0jJ/Dwarf_Fortress_-_Boatmurdered_djvu.txt)  
> 18. Game++. Part 1.2: C++, game engines, and architectures \- PVS-Studio, [https://pvs-studio.com/en/blog/posts/1375/](https://pvs-studio.com/en/blog/posts/1375/)  
> 19. (A rant on mental breaks) Should sheriffs/therapists be introduced as, [https://www.reddit.com/r/RimWorld/comments/4x4qah/a\_rant\_on\_mental\_breaks\_should\_sheriffstherapists/](https://www.reddit.com/r/RimWorld/comments/4x4qah/a_rant_on_mental_breaks_should_sheriffstherapists/)  
> 20. What xml file is general mental break frequency stored? : r/RimWorld, [https://www.reddit.com/r/RimWorld/comments/9s277v/what\_xml\_file\_is\_general\_mental\_break\_frequency/](https://www.reddit.com/r/RimWorld/comments/9s277v/what_xml_file_is_general_mental_break_frequency/)  
> 21. Rimworld output log published using HugsLib \- GitHub Gist, [https://gist.github.com/45d48f8feaec81e278a27038759ca617](https://gist.github.com/45d48f8feaec81e278a27038759ca617)  
> 22. Rimworld output log published using HugsLib · GitHub, [https://gist.github.com/HugsLibRecordKeeper/a8c22b726bed5e74b82c39f0cb81b03c](https://gist.github.com/HugsLibRecordKeeper/a8c22b726bed5e74b82c39f0cb81b03c)  
> 23. Rimworld output log published using HugsLib · GitHub, [https://gist.github.com/HugsLibRecordKeeper/e3b86b9b1b5b1c98c94977f69d12f2b9](https://gist.github.com/HugsLibRecordKeeper/e3b86b9b1b5b1c98c94977f69d12f2b9)  
> 24. Rimworld output log published using HugsLib · GitHub, [https://gist.github.com/HugsLibRecordKeeper/2b397b327d9926ecf8c8616a021a5143](https://gist.github.com/HugsLibRecordKeeper/2b397b327d9926ecf8c8616a021a5143)  
> 25. Rimworld output log published using HugsLib · GitHub, [https://gist.github.com/HugsLibRecordKeeper/61f7dfc9b1c8a10fcf962caa6fa1bc34](https://gist.github.com/HugsLibRecordKeeper/61f7dfc9b1c8a10fcf962caa6fa1bc34)  
> 26. Grief : r/RimWorld \- Reddit, [https://www.reddit.com/r/RimWorld/comments/pef5u1/grief/](https://www.reddit.com/r/RimWorld/comments/pef5u1/grief/)  
> 27. Mental Break Expiration VS Violence Solution : r/RimWorld \- Reddit, [https://www.reddit.com/r/RimWorld/comments/1gsya5r/mental\_break\_expiration\_vs\_violence\_solution/](https://www.reddit.com/r/RimWorld/comments/1gsya5r/mental_break_expiration_vs_violence_solution/)  
> 28. Do you also beat the crap out of pawns on breakdown : r/RimWorld, [https://www.reddit.com/r/RimWorld/comments/1bytvpu/do\_you\_also\_beat\_the\_crap\_out\_of\_pawns\_on/](https://www.reddit.com/r/RimWorld/comments/1bytvpu/do_you_also_beat_the_crap_out_of_pawns_on/)  
> 29. Talks \- Ark, [http://delta.center/events-copy-copy](http://delta.center/events-copy-copy)  
> 30. A summary for Utility AI \- Whether I have understood everything, [https://www.reddit.com/r/gameai/comments/hz1xci/a\_summary\_for\_utility\_ai\_whether\_i\_have/](https://www.reddit.com/r/gameai/comments/hz1xci/a_summary_for_utility_ai_whether_i_have/)  
> 31. Game AI Pro 1 \- Feineigle.com, [http://feineigle.com/book\_reports/2024/game\_ai\_pro\_1/](http://feineigle.com/book_reports/2024/game_ai_pro_1/)  
> 32. Aniya, my custom voiced follower mod, needs a working relax function., [https://www.reddit.com/r/skyrimmods/comments/tibyxn/aniya\_my\_custom\_voiced\_follower\_mod\_needs\_a/](https://www.reddit.com/r/skyrimmods/comments/tibyxn/aniya_my_custom_voiced_follower_mod_needs_a/)  
> 33. Keeping an NPC in Place in Special Edition? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/k3xrq8/keeping\_an\_npc\_in\_place\_in\_special\_edition/](https://www.reddit.com/r/skyrimmods/comments/k3xrq8/keeping_an_npc_in_place_in_special_edition/)  
> 34. Dialogue Order : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/kwfctc/dialogue\_order/](https://www.reddit.com/r/skyrimmods/comments/kwfctc/dialogue_order/)  
> 35. I found a way to change an NPC's packages using scripting. \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/b8lf9o/i\_found\_a\_way\_to\_change\_an\_npcs\_packages\_using/](https://www.reddit.com/r/skyrimmods/comments/b8lf9o/i_found_a_way_to_change_an_npcs_packages_using/)  
> 36. PapyrusUtil Updated for Skyrim Anniversary Edition (SKSE v2.1.2, [https://www.reddit.com/r/skyrimmods/comments/qy9fra/papyrusutil\_updated\_for\_skyrim\_anniversary/](https://www.reddit.com/r/skyrimmods/comments/qy9fra/papyrusutil_updated_for_skyrim_anniversary/)  
> 37. GitHub \- Pathos14489/Pantella, [https://github.com/Pathos14489/Pantella](https://github.com/Pathos14489/Pantella)  
> 38. Question about AI packages : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/62lsg9/question\_about\_ai\_packages/](https://www.reddit.com/r/skyrimmods/comments/62lsg9/question_about_ai_packages/)  
> 39. papyrus.xml \- GitHub Gist, [https://gist.github.com/st4rdog/3470de541941d3e9b5b1](https://gist.github.com/st4rdog/3470de541941d3e9b5b1)  
> 40. EvaluatePackage function \- Actor script | Skyrim SE \- Papyrus Index, [https://papyrus.bellcube.dev/skyrimse/script/actor/function/evaluatepackage/](https://papyrus.bellcube.dev/skyrimse/script/actor/function/evaluatepackage/)  
> 41. \[Guide\] Papyrus INI settings, and why you shouldn't touch them, [https://www.reddit.com/r/skyrimmods/comments/2gwvwl/guide\_papyrus\_ini\_settings\_and\_why\_you\_shouldnt/](https://www.reddit.com/r/skyrimmods/comments/2gwvwl/guide_papyrus_ini_settings_and_why_you_shouldnt/)  
> 42. Myths and Legends: Papyrus Ini Settings \- Thallassa's Thoughts, [https://thallassathoughts.wordpress.com/2016/09/16/myths-and-legends-papyrus-ini-settings/](https://thallassathoughts.wordpress.com/2016/09/16/myths-and-legends-papyrus-ini-settings/)  
> 43. LF solutions for infinite loading screen Skyrim AE \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1kkv2rc/lf\_solutions\_for\_infinite\_loading\_screen\_skyrim\_ae/](https://www.reddit.com/r/skyrimmods/comments/1kkv2rc/lf_solutions_for_infinite_loading_screen_skyrim_ae/)  
> 44. Is there a more elegant way to diagnose which mod is causing, [https://www.reddit.com/r/skyrimmods/comments/1cczyng/is\_there\_a\_more\_elegant\_way\_to\_diagnose\_which\_mod/](https://www.reddit.com/r/skyrimmods/comments/1cczyng/is_there_a_more_elegant_way_to_diagnose_which_mod/)  
> 45. Gotojuch, Dominik (2025) Controlled design of human-like agents, [https://theses.gla.ac.uk/85486/1/2025GotojuchPhD.pdf](https://theses.gla.ac.uk/85486/1/2025GotojuchPhD.pdf)  
> 46. Simple guide to activate player idle animations. (PC, No Mods, [https://www.reddit.com/r/skyrim/comments/aui4ld/simple\_guide\_to\_activate\_player\_idle\_animations/](https://www.reddit.com/r/skyrim/comments/aui4ld/simple_guide_to_activate_player_idle_animations/)  
> 47. Papyrus Автозаполнение — Creation Kit Русский, [https://tesck.ru/index.php/Papyrus\_%D0%90%D0%B2%D1%82%D0%BE%D0%B7%D0%B0%D0%BF%D0%BE%D0%BB%D0%BD%D0%B5%D0%BD%D0%B8%D0%B5](https://tesck.ru/index.php/Papyrus_%D0%90%D0%B2%D1%82%D0%BE%D0%B7%D0%B0%D0%BF%D0%BE%D0%BB%D0%BD%D0%B5%D0%BD%D0%B8%D0%B5)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAABSCAYAAADpeojRAAAEX0lEQVR4Xu3dX8gmUxgA8ON/irIoKfm/shdSSFIkFBdulEghN5IropYNF0pyQ0qulJvlyjXZRJFyJymiJRuJJFuU2iTO2ZnZ78x5z/u9M2Pf93u/9verp3PmmdPMfO9e7NOZmTMhAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAADARDti/Bbj33IHAADr42BQsAEArDUFGwDAmlOwAQCsOc+wAQCsOTNsAABrTsEGALDmFGwAAGtOwQYAsKbOD02hlse3vREAAP/DWWVigf1lAgCAab6M8U+Mn0Iz47MrxoF8QLQ7xttFbojPywQAAOPUnqNKuZ1F7sdie6jXw2zxBwDAQA+E+QVb7ukY5xS5McrjAQAwUPfQe+mzYrs2Zow/ygQAAMO8EzaKtvdj3NLffcS8gi3l72rbx2J8EZrn4Uq3x9hbJgEAGCa9bNAVbSme7+8+rFawPZH1P4lxqO3XxqbbqYuWrsivYbMAADhmHR+aoqpWFNVye7J+2n92278iy+dqx1iGfWIpAQBsgUvKRKtWWNVyuUX7kyFjAADIzCugavlarvNK6O8/L+t3LojxQ5ks5Lc9NwsAgGPC3aFe/HwX47QyGWbHXp/lykLqr6zfeSj0n3ljuLSO3ap8WiYAgK2Tlu34IDSF1m1t7vcYHx8Z0VcWbKe3ufT2Z3qhIPXPDLPLgXS+jnFSmeSw7t+h5uEysQLXlAkAYHv4KMYpZXKEeQXJKmzluYeqXeNVMV4tkyuQZllPLpMAwPZQKyqGSDN3z5bJJXs5NOvBPRKmXfdzZWKJToxxX9u/J8Zxbb923Q+27Q15coBTY9zR9m/Nd1Skt333l0kAYHv4PsadZXKAP8vECl0d6oXPIu+WiSXa07aPx3ghbKxXV173m237a4zLw+z+eU4ITcF2cYyfY3wT46LeiFlDjw0ArKHrysQCW/0f/9SCLX31YYpUHJWzX2l2sRaddH2vZdud/Lq7Wbfkq6yfPBVmj53i0Xb/TW2bCsLc/W37dy/bmPKbAQBMMrVg+7BMLPBG6J9nzDm7sV3bLTxcO0b6dNi5bb+2fMpmuuOll0Ty7WfaNlc7NwDAUqyqYEvnuDLbri1tMk96gzbprvPaYjvpnsXLZ9cuzPqbKQvC7hZ1t/1k2+am/GYAAJMMKdheDM2YIVFzKDTfY023UQ+EZtyOfMAIZ2T9vTFuzLYva9tLQ/8W6SJpbPrsWLIzy3d/T/mCxUsxdhU5AIClGVKw1YyZYUvH797yPNrGzNSN1a2Z90svO+33AgCYbFUF2zKlBYlX5eYyAQCwbOlzWKmgym81DjGmYLs3xltFzjpmAAALpCUryufPxsyEjSnYkoNh4xzvFfsAAFiCfWUCAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgKPmP99KKXTgrXBxAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAZCAYAAAAFbs/PAAAAfklEQVR4XmNgGAU0BhxAvBWIXwNxCFRsIxBfBWJ2mCIY6ANibyT+fyA+gsQGYRTwF40PUsCKxAYZiBdgmIgPpDCQqOEJA6YGfmROJQNEwRIoH8S+hZBm+IbEBgM7IL4HxBIMEMWBUFoXiL8CsSZCKQIIAXEuGj8ZiT8KhjoAAFCWGrOOSSeSAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAaCAYAAAC3g3x9AAAA9UlEQVR4XmNgGAWjgCLABcQ7gfglEDtBxXYA8WkgZoQpIhawAvE7JP5/ID4KxExAvAuI/yLJEQVABqDzQZgfSiNbRhRoR+ODDJkJZRsiS0BBLBAHoQviAmYMEAPV0CWg4CCUFgHij8gSuMBWBswggAFmBlQ5UFDoI/HBAOQSkKJ+KB/EfoKQZlgHxOxQdjcDqoHbgHg3Eh8MWhkgirSAeDKU/RwqZw7ER6BsEFjMgGrgRiB+j8SHA1isLkTjL4WrgAB0F24G4jtIfJJBMgOqgYeAeBMSnyyAbOAHIDZC4pMFnkJpUO7ClRpIBrVAnIUuOApGCgAAo6w2nGFbeLkAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAaCAYAAABhJqYYAAAAp0lEQVR4XmNgoCcQBmJTdEF08BKI/0PxAVQp7ECMAaLYA10CG5jLAFFMFIA5gyBgZIAobEMS2wjEj4GYBUkMDPIZIIp5oPx3UPoTEM+HsuHgPQPCCXugNMhkkFgmlA8HMPfeQRN3QOMzMDEgFIPwblRpVFDEgOre50A8HSGNCtCDrAqIL0LZE4BYGUkOrHA7Ej8eiBciyaEAkIAWFjEQ5kATHwVDFgAA95EpcIRVUuUAAAAASUVORK5CYII=>