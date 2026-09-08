# **Systemic Conflict Analysis of Dynamic Relationship-Rank Writes in Skyrim SE/AE**

## **Mechanics of the Creation Engine Relationship-Rank Subsystem**

Skyrim’s social affinity architecture relies on an integer-based relationship-rank scale bounded between \-4 and 41. This metric establishes the baseline disposition between two actors—predominantly between the player character (PlayerRef 00000014\) and an NPC reference—and governs low-level engine decisions such as dialogue topic visibility, greeting frequency, crime tolerance, and interior cell permissions1.

| Rank Value | Engine Designation | Functional Rights and Gameplay Consequences |
| :---- | :---- | :---- |
| **4** | Lover / Spouse | Unlocks marriage dialogue via RelationshipMarriageFIN; grants maximum crime forgiveness and the Lover's Comfort resting bonus2. |
| **3** | Ally | Unlocks follower recruitment conditional branches in DialogueFollower; NPC assists the player in lethal combat2. |
| **2** | Confidant | Permits taking medium-value owned items without triggering theft flags; unlocks friendly greeting pools1. |
| **1** | Friend | Enables standard friendly greetings ("Fine day with you around"); allows taking low-value items (\<25 gold)1. |
| **0** | Acquaintance | Default baseline for standard townspeople; standard dialogue trees and commercial interactions1. |
| **\-1** | Rival | Activates dismissive or irritated greeting pools; triggers refusal of basic favors2. |
| **\-2** | Foe | Heightened annoyance; completely conditions out polite or helpful dialogue branches. |
| **\-3** | Enemy | Active verbal hostility; heightened probability of triggering hired thug contracts. |
| **\-4** | Archnemesis | Maximum organic hostility; actively attacks or assists hostile factions against the player during disturbances9. |

Unlike static attributes authored in plugin records (TESNPC), relationship rank is a dynamic pointer-pair state stored within the runtime save file (ESS) and modified via the Papyrus native methods Actor.SetRelationshipRank(Actor akOther, int aiRank) and Actor.GetRelationshipRank(Actor akOther)4. In vanilla game architecture, these mutations are strictly event-driven: they execute via one-off script fragments embedded in quest stage completions, such as finishing a favor, delivering an item, or winning a brawl13.  
When an SKSE plugin such as ChronicleBridge continuously or periodically overwrites relationship ranks at native runtime to reflect external social simulations, it introduces an active, continuous authority over a system that the Creation Engine assumes is static outside explicit player-driven milestones.

## **Mod Interaction Profiles: Reading vs. Writing Systems**

### **Relationship Dialogue Overhaul**

*Relationship Dialogue Overhaul* (RDO) completely overhauls the ambient and direct vocal interactions of Skyrim’s NPCs by conditioning over 5,000 spliced vanilla audio lines across more than 50 voice types5.  
During standard gameplay, RDO acts strictly as a read-only consumer of relationship ranks. Its quest dialogues and greeting topics evaluate GetRelationshipRank via dialogue condition arrays to select appropriate lines5. RDO does not run continuous polling scripts to manipulate townsperson disposition. However, it introduces a severe behavioral rule: any NPC whose relationship rank drops to \-1 or lower (Rival, Foe, Enemy, Archnemesis) will systematically refuse commercial trade, innkeeper services, carriage transportation, and skill training5. Under RDO, the trade dialogue branch is conditioned out entirely and replaced with cold dismissals or direct insults5.  
This creates immediate failure states among the 19 Whiterun NPCs managed by Chronicle. If simulated rumors or grudges drive the ranks of Adrianne Avenicci, Carlotta Valentia, Ysolda, or Anoriath below 0, RDO locks their merchant barter menus completely5. Similarly, if Danica Pure-Spring (Master Restoration) or Amren (One-Handed) drop into negative ranks, their training dialogues disappear5. While RDO contains an MCM menu and diagnostic cheat spells capable of invoking SetRelationshipRank to force affinity changes, these are manual debugging utilities rather than automated background scripts16. Consequently, Chronicle’s native writes will silently override any manual fixes applied by the player through RDO's interface.

### **Follower Management Frameworks**

Follower frameworks such as *Nether's Follower Framework* (NFF), *Amazing Follower Tweaks* (AFT), and *Extensible Follower Framework* (EFF) govern companion behavior using dedicated faction structures (PotentialFollowerFaction 0005C84D and CurrentFollowerFaction 0005A1A4) linked to relationship ranks7.  
These frameworks maintain complete quiescence regarding passive, unrecruited townspeople. Citizens such as Heimskr, Sigurd, Lillith Maiden-Loom, or Olava the Feeble will never be evaluated or written to by follower scripts during ambient routines. The interaction hazard occurs exclusively when a player utilizes force-recruitment powers (such as AFT's "Tweak Make Follower" or NFF's companion force-hire) to recruit an otherwise non-follower Whiterun citizen, or recruits a vanilla candidate like Amren7. In these scenarios, the framework fires a one-time Papyrus script sequence that enrolls the NPC into follower factions and calls SetRelationshipRank(PlayerRef, 3\) to ensure companion compliance7.  
If Chronicle executes a runtime write that drops a recruited follower's rank below 3, the follower frameworks encounter contradictory internal states. In NFF and AFT, companions whose relationship drops below ally status can experience package stalls, refusal to wait or trade gear, spontaneous dismissal routines, or lethal infighting during combat encounters due to conflicting faction and disposition checks7.

### **Romance and Marriage Overhauls**

Romance and marriage modifications directly target key Whiterun citizens, most notably Ysolda and Carlotta Valentia27. *Amorous Adventures* (AA) implements dedicated questlines for both NPCs—specifically "Ysolda's Tough Lesson" and Carlotta's "A Key to Her Heart"27. Upon successfully concluding these romance narratives, AA fires script fragments that enroll the NPCs into romance factions and execute SetRelationshipRank(PlayerRef, 4\)30.  
Because AA and similar romance mods rely fundamentally on quest stages (GetStage) to track overall narrative progression while evaluating relationship ranks for moment-to-moment intimacy and dialogue options, a downward write from Chronicle creates a desynchronized split-brain condition9. The mod’s quest stage remains permanently completed (e.g., stage 100), yet the underlying actor affinity is demoted to Rival or Foe. Under these conditions, affection dialogue branches fail their condition checks, intimate scenes abort prematurely, and the NPC delivers hostile greeting lines while their quest log indicates they are the player's devoted partner9. In polygamy mods that support multiple spouses, dropping a married NPC's rank below 4 revokes the Lover's Comfort resting bonus and corrupts domestic sandbox packages3.

### **Expansive Social and Radiant Systems**

*Interesting NPCs* (3DNPC) operates within an isolated architecture. When 3DNPC manipulates relationship ranks, it does so strictly on its own bespoke actors—such as automatically setting companions like Rumarin or Zora to Rank 4 upon recruitment36. 3DNPC does not modify, query, or overwrite the relationship ranks of the 19 vanilla Whiterun citizens.  
*Skyrim Reputation* takes a global, indirect approach to social standing. Rather than actively writing to individual actor-to-actor relationship integers, it tracks the player’s deeds through global variables and applies regional disposition adjustments using broad faction reaction modifiers3. Because *Skyrim Reputation* does not target individual actor relationship-rank memory addresses, there is no direct variable collision. However, aesthetic contradictions can occur if Chronicle lowers an NPC’s individual rank to Rival while *Skyrim Reputation* applies a positive hero modifier to the surrounding regional faction3.  
Conversely, radiant quest additions such as *Missives* and *Sidequests of Skyrim* introduce direct write collisions. Upon completing radiant delivery or retrieval tasks for Whiterun merchants and citizens, these mods run Papyrus fragments that call SetRelationshipRank(PlayerRef, 1\) to reward the player with Friend status19. If Chronicle’s simulation later recalculates a grudge and demotes that citizen, the social reward gained from the radiant board is silently erased19.

## **Conflict Typology: Flapping Conditions vs. Destructive Clobbering**

An essential technical inquiry is whether Chronicle’s runtime writes trigger high-frequency "flapping" race conditions or unidirectional destructive clobbering. A true flapping condition requires two autonomous software processes running asynchronous execution loops (such as two distinct OnUpdate() timers or SKSE thread dispatches) that continually assert contradictory values to the same variable, causing the engine to oscillate rapidly between states.  
Investigation confirms that true script flapping does not occur with the 19 Whiterun townspeople. No major Skyrim mod—including RDO, AFT, NFF, 3DNPC, or the base game master files—runs an active background polling script designed to monitor and reset citizen relationship ranks. Every third-party mod that writes relationship ranks does so via discrete, event-driven triggers: advancing a quest stage, exiting a specific dialogue topic fragment, or activating an MCM debugging tool4.  
Instead, the failure pattern is **unidirectional destructive clobbering and state desynchronization**:

\[Discrete Event: Radiant/Favor Quest\]          \[ChronicleBridge Runtime Service\]  
                     │                                         │  
    Completes Task (e.g. Bring Tusk)                 Simulates Rumor / Grudge Shift  
                     │                                         │  
          Calls SetRelationshipRank(1)                         │  
                     │                                         │  
                     ▼                                         ▼  
           \[Actor Memory Address\] ◄──────────────── Periodic Native Write:  
              RelationshipRank \= 1                  Sets RelationshipRank \= \-1  
                     │  
                     ▼  
        \[Desynchronized Engine State\]  
   • Quest Stage \= Completed (100)  
   • Engine Relationship Rank \= Rival (-1)  
   • Result: RDO Trade Menus Lock; "Thane of Whiterun" Counter Disrupted

When a player completes a vanilla favor—such as giving Brenuin an Argonian Ale, retrieving Amren’s family sword, delivering a mammoth tusk to Ysolda, or handling Carlotta Valentia’s dispute with Mikael—the engine calls SetRelationshipRank(PlayerRef, 1\)27. This sets the citizen to Friend status, satisfying the progression conditions for the major regional quest *Thane of Whiterun* ("Assist the people of Whiterun: 3/3"). If Chronicle subsequently recalculates that NPC's social standing based on background rumors and demotes them to Rank 0 or \-1, the engine state desynchronizes. The favor quest remains flagged as permanently finished in the player's quest journal, but the NPC’s affinity reverts to neutral or hostile. If this occurs before the Thane quest evaluates its completion tally, player progression towards acquiring the Thane title, Breezehome, or Lydia can be obstructed.

## **Comparative Mod Interaction Matrix**

| Mod Name | Execution Architecture | Runtime Trigger | Target NPCs in Whiterun | Interaction Classification | Behavioral Failure Mode |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Relationship Dialogue Overhaul (RDO)** | Read-only in ambient play; write-only via debug MCM5 | Dialogue topic evaluation (GetRelationshipRank)5 | All 19 Whiterun NPCs5 | Unidirectional Read Consumption5 | Drops to Rank \-1 or lower lock barter menus and training trees, replacing them with verbal insults5. |
| **Nether's Follower Framework (NFF)** | Event-driven write on recruitment7 | Player command or MCM force-recruit (SetRelationshipRank 3\)7 | Potential companions (Amren; Ysolda via mods)7 | Post-Recruitment Clobbering7 | Companion package breakdown, refusal to accept combat orders, spontaneous auto-dismissal7. |
| **Amazing Follower Tweaks (AFT)** | Event-driven write on recruitment20 | "Tweak Make Follower" spell interaction20 | Any non-child humanoid21 | Post-Recruitment Clobbering21 | AI package stalls, failure to track follow-distance packages, reversion to standard town routines26. |
| **Amorous Adventures (AA)** | Event-driven write on stage completion30 | Quest stage Papyrus fragments (SetRelationshipRank 4\)30 | Carlotta Valentia, Ysolda27 | Quest-State Desynchronization28 | Quest stage remains complete while affinity drops, terminating romantic dialogue and intimacy scenes9. |
| **Interesting NPCs (3DNPC)** | Event-driven write on custom actors36 | Internal quest stages and follower recruitment36 | None (Proprietary actor roster)36 | Zero Direct Interaction | Coexists safely; 3DNPC does not query or modify vanilla Whiterun citizens. |
| **Skyrim Reputation** | Read-only per actor; writes global factions3 | Regional crime and quest-completion listeners3 | Broad regional populations37 | Semantic Contradiction | No direct memory collision; townsperson hostility may visually clash with overarching hero status3. |
| **Missives / Sidequests of Skyrim** | Event-driven write on radiant completion19 | Radiant delivery turn-in (SetRelationshipRank 1\)19 | Merchants and citizens issuing jobs19 | Radiant Reward Overwrite19 | Chronicle overwrites the earned Friend rank, nullifying the radiant gameplay reward19. |

## **Cascading Engine and Sandbox Side Effects**

Direct, dynamic modification of an NPC’s relationship rank without adjusting underlying factions or quest stages triggers multiple cascading engine side effects across the simulation.

### **Cell Ownership and Trespassing Rules**

Interior cell access throughout Skyrim is heavily governed by owner disposition. In residences such as Carlotta Valentia’s house, House Gray-Mane, or the Battle-Born compound, an actor at Rank 1 (Friend) or higher grants the player "friendly trespass" privileges, permitting entry during daytime hours without alarms4. Furthermore, an NPC’s relationship rank establishes a direct economic ceiling on items the player may pick up without triggering theft flags4. If Chronicle executes a downward rank shift from Rank 1 to Rank \-1 while the player is inside an NPC's residence, the engine immediately flags the player as a criminal intruder, causing the homeowner to draw weapons and dispatch guards.

### **Merchant and Trainer Subsystems**

Under baseline vanilla parameters, merchants continue to trade even at neutral or slightly cold ranks. However, across modern modded installations running RDO or economic balance mods, trade menus require non-negative relationship ranks5. Adrianne Avenicci, Carlotta Valentia, Ysolda, and Anoriath serve as the economic backbone of Whiterun. Forcing their ranks below zero deprives the player of smithing, alchemy, food, and general goods vendors5. For Danica Pure-Spring and Amren, dropping below Rank 0 shuts down Restoration and One-Handed training5. In Ysolda's specific case, relationship ranks also govern her speechcraft checks during the Daedric quest *A Night to Remember*, where an adversarial rank locks out persuasion routes for the wedding ring.

### **Combat Escalation, Brawls, and Assistance**

An actor’s probability of reporting crimes or drawing weapons during an assault scales with their base Assistance actor value multiplied by their RelationshipRank. At Rank 3 (Ally) or Rank 4 (Lover), townspeople will intervene in violent conflicts to defend the player, drawing daggers against hostile bandits or city guards7. If Chronicle lowers an NPC's affinity to Rank \-4 (Archnemesis), their confidence and aggression profiles invert to favor the player's opponents10. During scripted, non-lethal tavern brawls, an NPC at Rank \-4 has a significant probability of treating unarmed punches as criminal assault, drawing lethal weapons, or alerting city guards to initiate a municipal riot10.

### **Child Welfare and Hearthfire Adoption**

Lucia, the orphaned child in Whiterun, is governed by the Hearthfire adoption framework39. The adoption dialogue branch is heavily conditioned on relationship rank: the player must first raise her disposition by gifting a gold coin, which executes a script elevating her to Friend status39. If Chronicle’s grudge simulation incorporates Lucia or lowers her affinity due to secondary social ties, the adoption dialogue sequence fails its condition checks, permanently locking the player out of adopting her39. Similarly, manipulating the ranks of Lars Battle-Born and Braith can corrupt their quest scripts during their bullying resolution quest.

## **Strategic Recommendations for ChronicleBridge**

To prevent destructive state desynchronization while preserving the expressive realism of Chronicle's social simulation, the native C++ SKSE bridge must introduce structured architectural safeguards prior to executing rank writes.

### **Relationship Floors and Invariant Clamping**

ChronicleBridge should implement strict query checks against engine state before altering relationship ranks, establishing hard programmatic floors:

* **Spouse and Companion Invariant**: The bridge must query whether the targeted NPC belongs to CurrentFollowerFaction (0005A1A4) or RelationshipMarriageFIN (00019809)7. If either returns positive, Chronicle must enforce an immutable lower bound of Rank 2 (Confidant) or Rank 3 (Ally), ensuring domestic dialogue and companion combat behavior remain intact1.  
* **Vanilla Favor Awareness**: The plugin should inspect the completion state of core Whiterun favor quests, such as Favor01 or FavorJobsBeggar14. If an NPC has completed their primary favor quest, Chronicle should clamp their relationship floor at Rank 0 (Acquaintance), preventing civic and commercial lockouts under RDO while still allowing the simulation to strip away Friend bonuses1.  
* **Adoption Protection**: Lucia should be hard-coded with an affinity floor of Rank 0 to ensure the Hearthfire adoption engine remains functional39.

### **Decoupling Simulation Grudges from Engine Ranks**

The most robust architectural solution involves decoupling Chronicle’s grudge and rumor simulation from the engine's core Actor.SetRelationshipRank variable entirely. Because SetRelationshipRank is heavily overloaded across the Skyrim ecosystem to handle disparate concerns—theft permissions, marriage dialogue, merchant availability, follower recruitment, and quest flags—using it as a generic slider for dynamic social simulations causes widespread collateral damage4.  
Instead, ChronicleBridge should maintain its internal grudge and rumor metrics in independent SKSE memory structures or custom global variables. When Chronicle requires an NPC to express hostility, mistrust, or cold behavior, it can apply these consequences via dedicated, high-priority AI package overrides, temporary disposition factions, or dynamic dialogue topic conditions injected through SKSE. This approach achieves dynamic, emergent social simulation while preserving the underlying Creation Engine relationship ranks upon which third-party dialogue, marriage, and follower frameworks fundamentally depend4.

#### **Works cited**

> 1. Is there a way to become Alvor's friend in Skyrim even if my ... \- Quora, [https://www.quora.com/Is-there-a-way-to-become-Alvors-friend-in-Skyrim-even-if-my-PC-doesnt-follow-Hadvar-from-Helgen-Following-Hadvar-is-the-only-way-I-know-to-become-his-friend](https://www.quora.com/Is-there-a-way-to-become-Alvors-friend-in-Skyrim-even-if-my-PC-doesnt-follow-Hadvar-from-Helgen-Following-Hadvar-is-the-only-way-I-know-to-become-his-friend)  
> 2. Help\! Faendal hates my guts now\!\!\!\!\!\! : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/td2maq/help\_faendal\_hates\_my\_guts\_now/](https://www.reddit.com/r/skyrimmods/comments/td2maq/help_faendal_hates_my_guts_now/)  
> 3. r/skyrimmods on Reddit: Are there any disposition mods, that make, [https://www.reddit.com/r/skyrimmods/comments/zz5g8k/are\_there\_any\_disposition\_mods\_that\_make/](https://www.reddit.com/r/skyrimmods/comments/zz5g8k/are_there_any_disposition_mods_that_make/)  
> 4. Skyrim & Creation Kit: How to incrementally change an NPC's, [https://www.loverslab.com/topic/190448-skyrim-creation-kit-how-to-incrementally-change-an-npcs-disposition-towards-the-player-in-the-player-dialogue-tab/](https://www.loverslab.com/topic/190448-skyrim-creation-kit-how-to-incrementally-change-an-npcs-disposition-towards-the-player-in-the-player-dialogue-tab/)  
> 5. Relationship Dialogue Overhaul \- RDO \[XB1\] \- Skyrim Creations, [https://creations.bethesda.net/de/skyrim/details/5840/Relationship\_Dialogue\_Overhaul\_\_\_RDO\_\_XB1\_](https://creations.bethesda.net/de/skyrim/details/5840/Relationship_Dialogue_Overhaul___RDO__XB1_)  
> 6. Custom Spouse mod? \- UESP Forums, [https://forums.uesp.net/viewtopic.php?t=35395](https://forums.uesp.net/viewtopic.php?t=35395)  
> 7. Help\! My follower wants to murder me : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1s5d4k0/help\_my\_follower\_wants\_to\_murder\_me/](https://www.reddit.com/r/skyrimmods/comments/1s5d4k0/help_my_follower_wants_to_murder_me/)  
> 8. Editing NPC Disposition : r/CreationKit \- Reddit, [https://www.reddit.com/r/CreationKit/comments/17h8qc6/editing\_npc\_disposition/](https://www.reddit.com/r/CreationKit/comments/17h8qc6/editing_npc_disposition/)  
> 9. Top 50 female Companion+replacers and more : r/skyrimmods, [https://www.reddit.com/r/skyrimmods/comments/1hp5b5a/top\_50\_female\_companionreplacers\_and\_more/](https://www.reddit.com/r/skyrimmods/comments/1hp5b5a/top_50_female_companionreplacers_and_more/)  
> 10. Console command to make NPC's hostile or fight each other?, [https://gamefaqs.gamespot.com/boards/615805-the-elder-scrolls-v-skyrim/71638112](https://gamefaqs.gamespot.com/boards/615805-the-elder-scrolls-v-skyrim/71638112)  
> 11. SetRelationshipRank function \- Actor script | Skyrim SE \- Papyrus, [https://papyrus.bellcube.dev/skyrimse/script/actor/function/setrelationshiprank/](https://papyrus.bellcube.dev/skyrimse/script/actor/function/setrelationshiprank/)  
> 12. Skyrim Creation Kit script to set relationship : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/54c6cm/skyrim\_creation\_kit\_script\_to\_set\_relationship/](https://www.reddit.com/r/skyrimmods/comments/54c6cm/skyrim_creation_kit_script_to_set_relationship/)  
> 13. Creation Kit Tutorial 01 Quest "The Tour" \#skyrim \#gaming \- YouTube, [https://www.youtube.com/watch?v=sVAWZop3upg](https://www.youtube.com/watch?v=sVAWZop3upg)  
> 14. Adding Relationship rank? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/cesr4c/adding\_relationship\_rank/](https://www.reddit.com/r/skyrimmods/comments/cesr4c/adding_relationship_rank/)  
> 15. Quest script doesn't work properly :: Skyrim Creation Kit (Public), [https://steamcommunity.com/groups/SkyrimCKPublic/discussions/1/3194744685908164101/](https://steamcommunity.com/groups/SkyrimCKPublic/discussions/1/3194744685908164101/)  
> 16. About RDO. : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/9ad5jw/about\_rdo/](https://www.reddit.com/r/skyrimmods/comments/9ad5jw/about_rdo/)  
> 17. Searching for a Relationship Rank Stat Editor Mod : r/skyrimmods, [https://www.reddit.com/r/skyrimmods/comments/y961it/searching\_for\_a\_relationship\_rank\_stat\_editor\_mod/](https://www.reddit.com/r/skyrimmods/comments/y961it/searching_for_a_relationship_rank_stat_editor_mod/)  
> 18. Skyrim Relationship Dialogue Overhaul MCM Demonstration v1.1, [https://www.youtube.com/watch?v=kVA60XrwrG4](https://www.youtube.com/watch?v=kVA60XrwrG4)  
> 19. Befriend NPC mod? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/il9ng8/befriend\_npc\_mod/](https://www.reddit.com/r/skyrimmods/comments/il9ng8/befriend_npc_mod/)  
> 20. Mods or other method to make NPC a follower? :: The Elder Scrolls V, [https://steamcommunity.com/app/489830/discussions/0/1636417554420501260/?l=russian](https://steamcommunity.com/app/489830/discussions/0/1636417554420501260/?l=russian)  
> 21. Destroying the Dark Brotherhood and having Cicero as a companion?, [https://www.reddit.com/r/skyrimmods/comments/2wfads/destroying\_the\_dark\_brotherhood\_and\_having\_cicero/](https://www.reddit.com/r/skyrimmods/comments/2wfads/destroying_the_dark_brotherhood_and_having_cicero/)  
> 22. Can I get some help with the Make Anyone Your Follower Mod?, [https://www.reddit.com/r/skyrimmods/comments/1gonxx/can\_i\_get\_some\_help\_with\_the\_make\_anyone\_your/](https://www.reddit.com/r/skyrimmods/comments/1gonxx/can_i_get_some_help_with_the_make_anyone_your/)  
> 23. Mods or other method to make NPC a follower? :: The Elder Scrolls V, [https://steamcommunity.com/app/489830/discussions/0/1636417554420501260/?l=german](https://steamcommunity.com/app/489830/discussions/0/1636417554420501260/?l=german)  
> 24. Skyrim创作 \- The Expendables, [https://creations.bethesda.net/zh-CN/skyrim/details/ad95562e-7b25-4e9d-bf53-f5f0795111ad/Kdot3391Test\_Followers](https://creations.bethesda.net/zh-CN/skyrim/details/ad95562e-7b25-4e9d-bf53-f5f0795111ad/Kdot3391Test_Followers)  
> 25. If you have multiple followers in Skyrim and one of them accidentally, [https://www.quora.com/If-you-have-multiple-followers-in-Skyrim-and-one-of-them-accidentally-hits-each-other-making-them-hostile-towards-each-other-how-can-you-fix-that-and-make-them-non-hostile](https://www.quora.com/If-you-have-multiple-followers-in-Skyrim-and-one-of-them-accidentally-hits-each-other-making-them-hostile-towards-each-other-how-can-you-fix-that-and-make-them-non-hostile)  
> 26. Help with a few console commands (if they exist) for use in relation, [https://www.reddit.com/r/skyrim/comments/2hnrd6/help\_with\_a\_few\_console\_commands\_if\_they\_exist/](https://www.reddit.com/r/skyrim/comments/2hnrd6/help_with_a_few_console_commands_if_they_exist/)  
> 27. Do you agree/disagree about these quests? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/v14qty/a\_review\_of\_amorous\_adventures\_do\_you/](https://www.reddit.com/r/skyrimmods/comments/v14qty/a_review_of_amorous_adventures_do_you/)  
> 28. Amorous Adventures (Video Game) \- TV Tropes, [https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/AmorousAdventures](https://tvtropes.org/pmwiki/pmwiki.php/VideoGame/AmorousAdventures)  
> 29. Elder Scrolls 5: Skyrim Anniversary \- Isekai Mods \- Steam Community, [https://steamcommunity.com/sharedfiles/filedetails/?l=finnish\&id=3040304315](https://steamcommunity.com/sharedfiles/filedetails/?l=finnish&id=3040304315)  
> 30. How can I steal Nazeems wife? (I am Nazeem, she needs to be my, [https://www.reddit.com/r/skyrimmods/comments/p3bffl/how\_can\_i\_steal\_nazeems\_wife\_i\_am\_nazeem\_she/](https://www.reddit.com/r/skyrimmods/comments/p3bffl/how_can_i_steal_nazeems_wife_i_am_nazeem_she/)  
> 31. Amorous Adventures Extended \[V1.2.1 \] (2019/01/11) \- LoversLab, [https://www.loverslab.com/topic/105221-amorous-adventures-extended-v121-20190111/page/3/](https://www.loverslab.com/topic/105221-amorous-adventures-extended-v121-20190111/page/3/)  
> 32. Amorous Adventures \[v3.4\] (2018/06/02) \- Page 92 \- LoversLab, [https://www.loverslab.com/topic/29971-amorous-adventures-v34-20180602/page/92/](https://www.loverslab.com/topic/29971-amorous-adventures-v34-20180602/page/92/)  
> 33. Amorous Adventures addon for Karliah? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/exyyvb/amorous\_adventures\_addon\_for\_karliah/](https://www.reddit.com/r/skyrimmods/comments/exyyvb/amorous_adventures_addon_for_karliah/)  
> 34. Relationship Dialogue Overhaul \- set NPCs as "married"? \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1uo5lah/relationship\_dialogue\_overhaul\_set\_npcs\_as\_married/](https://www.reddit.com/r/skyrimmods/comments/1uo5lah/relationship_dialogue_overhaul_set_npcs_as_married/)  
> 35. I need help with the marriage system. : r/skyrim \- Reddit, [https://www.reddit.com/r/skyrim/comments/1vo3bb6/i\_need\_help\_with\_the\_marriage\_system/](https://www.reddit.com/r/skyrim/comments/1vo3bb6/i_need_help_with_the_marriage_system/)  
> 36. Rumarin (Interesting NPC's) thinks we're married?? : r/skyrimmods, [https://www.reddit.com/r/skyrimmods/comments/12a1lqd/rumarin\_interesting\_npcs\_thinks\_were\_married/](https://www.reddit.com/r/skyrimmods/comments/12a1lqd/rumarin_interesting_npcs_thinks_were_married/)  
> 37. What mods that have been made do you think Bethesda should, [https://www.reddit.com/r/skyrimmods/comments/1bf9gsz/what\_mods\_that\_have\_been\_made\_do\_you\_think/](https://www.reddit.com/r/skyrimmods/comments/1bf9gsz/what_mods_that_have_been_made_do_you_think/)  
> 38. What are your favorite Roleplay characters/builds and what mods do, [https://www.reddit.com/r/skyrimmods/comments/13kr7v4/what\_are\_your\_favorite\_roleplay\_charactersbuilds/](https://www.reddit.com/r/skyrimmods/comments/13kr7v4/what_are_your_favorite_roleplay_charactersbuilds/)  
> 39. \[GUIDE\] Adopt any child via console commands : r/skyrim \- Reddit, [https://www.reddit.com/r/skyrim/comments/16i6e7/guide\_adopt\_any\_child\_via\_console\_commands/](https://www.reddit.com/r/skyrim/comments/16i6e7/guide_adopt_any_child_via_console_commands/)