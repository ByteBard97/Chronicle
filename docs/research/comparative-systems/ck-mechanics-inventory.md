> Filed 2026-08-22 in `docs/research/comparative-systems/` — external research
> (Gemini), not code-verified. Feeds the scenario-ladder / reactivity design
> work, not any accepted ADR. **Caveat**: several numeric thresholds in this
> document (e.g. specific opinion gates for faction join/leave, relationship
> termination values) are rendered only as embedded formula images
> (`[image13]` etc.), not as text — those exact numbers aren't
> machine-readable from this file as filed. Re-derive from the cited sources
> directly if a specific number becomes load-bearing for a design decision.
> **Update:** [ck-plaintext-numeric-values-inventory.md](ck-plaintext-numeric-values-inventory.md)
> covers much of the same ground with exact values as plain text — check
> there first before re-deriving from primary sources.

# **Crusader Kings Social Simulation Architecture: Mechanics Inventory and System Specifications**

## **The Opinion System**

The social simulation model underpinning *Crusader Kings II* (CK2) and *Crusader Kings III* (CK3) relies on a directed, asymmetric graph where every character maintains an individual numerical opinion value of every other known character1. These opinion values range from a functional minimum of ![][image1] to a maximum of ![][image2]3. This opinion value directly dictates AI behavior, tax and levy extraction yields, and interaction acceptance likelihoods1.

### **Data Representation and Storage**

In both engines, opinion values are stored as double-precision floating-point numbers, evaluated dynamically by summing static modifiers, trait bonuses or penalties, relational modifiers, and temporary event-driven modifiers4. Scripted opinion modifiers are defined within the common/opinion\_modifiers/ database directory4.  
Opinion modifiers possess parameters determining their numerical magnitude, lifetime duration, decay characteristics, and legal or social permissions4.

| Parameter | Type | Functional Scope & Behavior | Example Definition |
| :---- | :---- | :---- | :---- |
| opinion | Double | Additive value added directly to the relational score4. | opinion \= \-25 \[cite: 4\] |
| days / months / years | Integer | Fixed temporal lifetime of the modifier4. | months \= 160 \[cite: 4\] |
| decay | Boolean | Enables linear daily or monthly decay toward zero over the duration4. | decay \= yes \[cite: 4\] |
| multiplier | Integer | Controls the stacking count of a single modifier instance6. | multiplier \= 2 \[cite: 6\] |
| revoke\_reason | Boolean | Grants a legal right to revoke a title without incurring tyranny4. | revoke\_reason \= yes \[cite: 4\] |
| prison\_reason | Boolean | Grants a legal right to imprison the target character4. | prison\_reason \= yes \[cite: 4\] |
| execute\_reason | Boolean | Grants a legal right to execute the target character4 | execute\_reason \= yes \[cite: 4\] |

### **Stacking Rules, Decay Curves, and Inheritance**

Opinion modifiers behave according to explicit stacking and decay rules:

> 1. **Decay Dynamics**: Standard timed modifiers expire discretely when their duration timer reaches zero4. When decay \= yes is declared, the effective value ![][image3] at time ![][image4] decays linearly from initial value ![][image5] across total duration ![][image6]:  
>    ![][image7]  
>    For instance, common\_interests\_opinion \= { opinion \= 20 decay \= yes } decreases continuously over its scripted timeframe4.  
> 2. **Stacking Behavior**: By default, applying an identical modifier overwrites the existing timer unless script specifies stacking via multiplier6. Certain action-specific penalties stack additively without limit, such as tyranny penalties7.  
> 3. **Succession Inheritance**: Non-elective succession in CK2 passes ![][image8] of temporary opinion modifiers on subjects from the predecessor to the primary successor, damping immediate post-succession volatility8.  
> 4. **Global System Modifiers and Defines**: Global parameters scaled by prestige and piety are capped at hard limits via engine defines9. In CK2, PRESTIGE\_OPINION\_MAX \= 10 limits prestige-based opinion to ![][image9]9. Piety opinion for clergy is calculated as Piety divided by PIETY\_OPINION\_DIV \= 50 up to PIETY\_OPINION\_MAX \= 109. Negative piety scales five times faster than positive piety9.

### **Concrete Scripted Examples of Opinion Modifiers**

Scripted modifiers establish explicit political and legal causes within the game files:

* declared\_war: Represents an aggressive war declaration, granting opinion \= \-25 for months \= 160 and setting revoke\_reason \= yes4.  
* opinion\_dishonorable: Applied when a character commits a dishonorable act, giving opinion \= \-10 for months \= 60 and setting prison\_reason \= yes4.  
* opinion\_rebel\_traitor: Imposed on treasonous rebels, conferring opinion \= \-100 for months \= 1200, prison\_reason \= yes, and revoke\_reason \= yes4.  
* recently\_fired\_from\_council: Penalty for firing an advisor, imparting opinion \= \-5 for years \= 210.  
* fired\_from\_council: Major council dismissal penalty, applying opinion \= \-15 for years \= 1510.  
* squeezed\_extra\_tribute: Extortion penalty from steward actions, giving opinion \= \-15 for years \= 1010.  
* refused\_extra\_tribute: Penalty when a vassal rejects tribute demands, setting opinion \= \-15 for years \= 510.

### **Display and Tooltip Construction**

The engine exposes these calculations to players through a dynamically parsed ledger and context-sensitive tooltips11. The breakdown renders the base relation, character trait vectors, state-level modifiers, and itemized temporal modifiers12. In CK3, opinion sources are further stratified into typed categories:

* **Attraction Opinion**: Evaluated exclusively between characters where sexual orientation permits attraction, modified by physical traits such as Beauty or Disfigured13.  
* **Vassal Stance Opinion**: Categorized into Courtly, Glory Hound, Parochial, and Zealot categories, where actions such as holding feasts or raising crown authority apply targeted modifiers exclusively to vassals subscribed to that archetype7.  
* **Liege/Direct Vassal/Dynasty Opinion**: Targeted sub-opinions that alter scope-specific actions without shifting general world opinion13.

## **The Threshold-to-Action Catalog**

The engine transitions character social state into autonomous action whenever internal variables cross numerical thresholds7. These triggers operate either deterministically through hard logic gates or probabilistically via scaling mean-time-to-happen evaluation or AI action scoring16.

### **Faction Joining, Power Math, and Revolts**

Factions represent organized collective political pressure against a liege1.

#### **Crusader Kings II Mechanics**

Faction Power is mathematically calculated as the sum of all faction member army levies divided by the liege's total army levies1. AI leaders can fire ultimatums at ![][image10] strength, with massive weight increases at ![][image11] and ![][image12]16. Exceptions include the Overthrow Khagan nomad faction and the Antiking faction, which can fire at ![][image8] strength due to specialized external support structures16. Joining and leaving behaviors are gated by specific opinion thresholds and trait multipliers16.

| Faction Type | Opinion Gate to Leave | Opinion Gate to Join | Key Trait Multipliers |
| :---- | :---- | :---- | :---- |
| **Succession** | **![][image13]** (![][image14] weight)16 | ![][image15] (joins), ![][image13] (![][image16])16 | Ambitious (![][image17]), Envious (![][image18]), Content (![][image19])16 |
| **Crown Authority** | **![][image13]** (![][image14] weight)16 | ![][image20] (![][image21]), ![][image20] (![][image17])16 | Brave (![][image21]), Arbitrary (![][image21]), Just (![][image22])16 |
| **Independence** | **![][image13]** (![][image14] weight)16 | ![][image23] (![][image21]), ![][image20] (![][image17])16 | Deceitful (![][image18]), Impaler (![][image18]), Craven (![][image24])16 |

A character *cannot* join factions under specific hard conditions: if they are Imprisoned, Incapable, a Child, bound by a Non-Aggression Pact or Truce, under the Discouraged from Factionalism modifier (![][image25] opinion, applied for 10 years via Spymaster Scheme or 100 years via Intrigue Focus), or serving as a voting councilor in a content council16.

#### **Crusader Kings III Mechanics**

In CK3, the military power ratio is evaluated continuously, setting ![][image26] relative strength as the critical discontent accumulation threshold7. When military power exceeds ![][image26], discontent ticks upward each month at a rate proportional to the excess power; when power falls below ![][image26], discontent decreases7. Each additional active faction in the realm lowers the base discontent threshold by ![][image27]23. An ultimatum triggers deterministically when discontent reaches ![][image11], or immediately if the liege executes an unlawful imprisonment7. Furthermore, possessing a Strong Hook over a character allows forcing them into a faction for a mandatory 10-year period7.

### **Council Obstruction Mechanics**

Under the CK2 *Conclave* architecture, councilors evaluate liege war declarations, law changes, and title revocations based on five discrete voting stances dictated by traits, realm power, and opinion8. The evaluation checks whether opinion is ![][image28] with positive relationship flags to assign a Loyalist stance; otherwise, it scores trait and power vectors across the remaining four stances17.

| Stance | Primary Objective | Key Selection Criteria & Modifiers | Voting Behavior |
| :---- | :---- | :---- | :---- |
| **Loyalist** | Support the liege in all non-self-destructive actions17. | Content (+10), Trusting (+5), Friend (+10), Lover (+5), Close relative (+10), Opinion ![][image28] (+10), ![][image29]17. Negative opinion completely disables this stance17. | Votes YES unconditionally on liege proposals unless the action directly revokes their own title17. |
| **Pragmatist** | Maintain realm stability and threat balance17. | Base weight 30, Cynical (+10), Craven (+10), Just (+10), Paranoid (+10)17. Scaled up if land size outweighs military strength17. | Opposes wars against superior targets; approves reclaiming de jure land and revoking titles from over-powerful vassals17. |
| **Glory Hound** | Seek realm prestige through military glory17. | Brave (+10), Honest (+10), Proud (+10)17. Scaled up if army strength is high relative to land size17. | Opposes attacking weak neighbors; approves aggressive expansion against strong external opponents17. |
| **Zealot** | Expand religious dominance17. | Zealous trait, high Piety, religious focus17. | Approves all actions against holy enemies or infidels; blocks internal wars among same-faith vassals17. |
| **Malcontent** | Restrict liege authority and obstruct realm administration17. | Base weight 15, Ambitious (+5), Envious (+10), Rival of liege (+20), or holding excessive sub-realm power17. | Votes NO on all liege-favorable proposals unless directly rewarded17. |

### **Scheme and Plot Recruitment Mechanics**

Hostile schemes in CK3 (such as Murder or Abduct) evaluate four central metrics during operation25:

* **Potential**: Caps maximum theoretical success (default limit ![][image30])25. Schemer skills contribute up to ![][image31]; remaining percentage is populated by recruited Agents25.  
* **Secrecy**: Determines monthly detection probability25. If secrecy fails, the scheme incurs a Breach25.  
* **Breaches**: Incremental failure counter25. Reaching 5 Breaches results in mandatory scheme collapse and schemer discovery25.  
* **Advantage**: Generated resource used to trigger execution25. Gains \+1 base Advantage per 5 points of Intrigue above 1525. Executing requires a minimum of 5 Advantage25. Spending 10, 15, or 20 Advantage grants ![][image32], ![][image33], or ![][image34] success chance boosts respectively25.  
* **Agent Acceptance**: AI characters join as agents based on opinion delta (![][image35]), personality traits (e.g., Sadistic, Deceitful), or through forced coercion via Hooks14.

## **Crusader Kings III Social Engine Additions**

CK3 overhauled the social simulation layer by introducing discrete systems for information management, coercion, psychological pressure, narrative memory tracking, and scheme execution loops12.

### **Secrets and Blackmail Mechanics**

Secrets represent hidden illegal or socially taboo acts committed by characters26. They are instantiated upon the execution of prohibited actions, such as Adultery, Witchcraft, Murder Attempt, or Illegitimate Birth25.  
Secrets are uncovered through character event choices or via the Spymaster's Find Secrets task, which rolls a periodic skill contest against the target's Intrigue and Secrecy25. Uncovering a secret presents a dual choice:

> 1. **Expose**: Instantly applies the secret as a permanent character trait (such as Adulterer or Murderer), triggering general opinion maluses and granting the liege an Imprisonment Reason if the secret violates local faith or realm laws26.  
> 2. **Blackmail**: Initiates a blackmail interaction26. If the target complies, the schemer gains a Hook26. Blackmail over a *Shunned Practice* yields a **Weak Hook**, whereas blackmail over a *Criminal Practice* yields a **Strong Hook**26. If the target refuses blackmail, the secret is exposed automatically26.

### **The Hook Architecture**

Hooks serve as formal diplomatic leverage over another character26. A character can only hold one active Hook over a specific target at a time; new, stronger, or longer-lasting hooks overwrite weaker ones26.

Weak Hooks Matrix:  
\- Single-use consumption model.  
\- 10-year default expiry (e.g., Favor, Blackmail over Shunned Secret, Indebted, Manipulation).  
\- Permanent duration exception: House Head hook over newborn dynasty members.  
\- Mechanical Effects: Adds fixed acceptance bonus to interactions; halves court position base salary expenses.

Strong Hooks Matrix:  
\- Reusable model subject to interaction cooldowns.  
\- Perpetual or 10-year duration (e.g., Blackmail over Criminal Secret, Hook Fabrication, Loyalty).  
\- Mechanical Effects: Forces absolute acceptance on interactions; forces maximum realm priest tax contributions; blocks liege imprisonment; forces mandatory 10-year faction participation.

7  
Special interactions allow characters with the Forgiving trait to expend hooks to clear internal stress (![][image36] stress for Strong Hooks, ![][image37] for Weak Hooks), applying a decaying ![][image38] opinion bonus to the target27.

### **The Stress Engine**

The Stress system acts as a psychological buffer gating characters from acting contrary to their assigned personality traits14. Stress is gained when taking decisions or actions that conflict with personality flags14:

* Honest characters gain stress when executing Blackmail or hostile schemes14.  
* Greedy characters gain stress when granting titles or gifting gold14.  
* Compassionate characters gain stress when executing or torturing prisoners14.

Stress ranges from 0 to 300 points, broken into three 100-point bands calculated as ![][image39]14. Crossing 100, 200, or 300 points immediately fires a Mental Break Event14. Resolving a Mental Break forces the character to select a Coping Mechanism (such as Comfort Eater, Drunkard, or Flagellant)13. These traits permanently alter character attributes and introduce opinion penalties, but grant passive stress relief multipliers (![][image34] to ![][image40] stress loss) during stress-reducing activities13.

### **Character Memories System**

Introduced in Patch 1.7 (*Friends & Foes*), the Memory engine tracks life events as structured data objects attached to character instances12. Each memory contains a timestamp, a memory type tag (such as battle\_won, relative\_murdered, or feast\_attended), participating character references, and a visibility scope (Public vs Private)12.  
Memories fade dynamically over time based on narrative weight12. Retention upon character death is dictated by title rank defines (NDefines::NCharacter::MEMORY\_RETENTION\_BY\_TIER)12. Player-controlled characters and high-tier rulers (Kings and Emperors) retain memories permanently for historical reference12. Memories are queried directly by dialogue generators, dueling context checks, and scheme execution logic12. If an AI character initiates a Murder scheme against a rival, the murder event dynamically pulls the exact memory ID of the original slight to populate the narrative dialogue12.

## **Relationship Crystallization**

While numerical opinion varies smoothly, *Crusader Kings* crystallizes extreme social states into named, discrete relationship states12. These states function as explicit boolean flags, overriding base AI logic and unlocking unique mechanics12.

| Relationship Flag | Underlying Drivers | Unlocked Mechanics | Termination / End Conditions |
| :---- | :---- | :---- | :---- |
| **Friend** | High positive opinion (![][image13]), successful Befriend scheme, positive activity events12. | ![][image41] Loyalist council stance weight17; stress loss during shared activities12; joins personal schemes12. | Character death; opinion dropping below ![][image42]; rival-triggering event12. |
| **Best Friend** | Tier-2 elevation event from Friend state12. | Complete immunity to joining hostile schemes against target; massive stress mitigation; automatic activity joining12. | Exposure of betrayal secret; character death12. |
| **Lover** | Successful Seduce scheme, high attraction opinion14. | Unlocks Elope scheme25; high pregnancy chance25; intervention in assassination events12. | Exposure of adultery or infidelity; rivalry event; break-up interaction12. |
| **Soulmate** | Successful Romance scheme or elevation from Lover12. | Complete scheme protection; zero stress from spousal demands; massive prestige and piety gains12. | Character death; severe betrayal12. |
| **Rival** | Negative opinion (![][image20]), slight events, feud triggers, caught plotting12. | ![][image43] Hostile Scheme success chance14; enables Fabricate Hook scheme14; stress loss upon rival execution or murder14. | Character death; formal reconciliation event chain12. |
| **Nemesis** | Deepened rivalry via severe actions (e.g., executed child, blinded relative)12. | Unlocks unique execution and mutilation decisions12; extreme AI priority for aggressive hostile actions12. | Death of target (triggers post-mortem defilement events)12. |

## **AI Decision-Making Engine**

The character AI in *Crusader Kings* evaluates potential decisions, event choices, and diplomatic offers using a scoring function driven by personality attributes, opinion vectors, and engine defines18.

### **Scoring Evaluation Architecture**

In Paradox script, actions are scored using ai\_will\_do, ai\_chance, or ai\_score blocks18. The mathematical structure evaluates a base weight, applies additive or multiplicative conditional modifiers, and factors in AI personality dimensions:  
![][image44]  
Script definitions utilize structured blocks to calculate these choices dynamically based on traits and personality dimensions:

ai\_chance \= {  
    base \= 10  
    modifier \= {  
        add \= 100  
        has\_trait \= chaste  
    }  
    modifier \= {  
        factor \= 0  
        has\_trait \= deviant  
    }  
    ai\_value\_modifier \= {  
        ai\_zeal \= 1.5  
        ai\_boldness \= \-0.5  
    }  
}

18

### **Core AI Personality Vectors**

Every character's traits modify 13 fundamental AI personality parameters stored on the character instance, ranging numerically from ![][image45] to ![][image46]13.

* **ai\_honor**: Dictates alliance adherence, treaty keeping, and plot participation4. High honor characters rarely break Non-Aggression Pacts or join dishonorable murder plots4. Modifiers include Honest (![][image38]), Just (![][image41]), and Deceitful (![][image47])13.  
* **ai\_greed**: Controls financial evaluation, ransom demands, gift opinion responsiveness, and willingness to spend gold4. Modifiers include Greedy (![][image46]) and Content (![][image47])14. High greed AI increases extra tax demands14.  
* **ai\_boldness**: Determines military aggression, resistance to Dread, and willingness to press faction ultimatums against superior lieges18. High boldness reduces the intimidating effect of Liege Dread23. Modifiers include Wrathful (![][image48]), Brave (![][image38]), and Craven (![][image47])13.  
* **ai\_rationality**: Controls strategic decision-making and force evaluation7. High rationality forces the AI to measure enemy troop counts, financial reserves, and terrain bottlenecks before declaring war4.  
* **ai\_vengefulness**: Dictates retaliatory priority7. High vengefulness characters aggressively target Rivals, execute captured foes, and join hostile feuds7. Modifiers include Forgiving (![][image1]) and Vengeful (![][image46])13.  
* **ai\_zeal**: Governs participation in Crusades, Great Holy Wars, and heretic executions4. Modifiers include Zealous (![][image46]) and Cynical (![][image1])13.  
* **ai\_compassion**: Controls mercy during events, release of prisoners without ransom, and refusal to execute non-criminals or children7. Modifiers include Compassionate (![][image46]) and Sadistic (![][image45])13.

### **Engine Execution Defines**

AI processing loops consult global defines in common/defines/00\_defines.txt and common/defines/ai/ to maintain performant evaluation loops18. Key defines establishing global execution thresholds include:

* BETROTHAL\_MIN\_AGE \= 12: Prevents AI characters from evaluating betrothals for characters under age 1218.  
* WAR\_MIN\_POWER\_DIFF\_FOR\_DECLARATION \= 0.8: Requires the AI to possess at least ![][image26] of the target's power before initiating standard war logic17.  
* MIN\_OPINION\_TO\_JOIN\_PLOT \= \-20: Establishes the opinion floor below which an AI character will consider joining a hostile plot against a target.  
* DREAD\_EFFECT\_BOLDNESS\_MULT \= \-1.5: Scales how Dread directly subtracts from an AI character's effective boldness rating.

#### **Works cited**

> 1. Vassals \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Vassals](https://ck2.paradoxwikis.com/Vassals)  
> 2. Beginner's guide \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Beginner%27s\_guide](https://ck2.paradoxwikis.com/Beginner%27s_guide)  
> 3. Extended Mechanics & Flavor (EMF) \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Extended\_Mechanics\_%26\_Flavor\_(EMF)](https://ck2.paradoxwikis.com/Extended_Mechanics_%26_Flavor_\(EMF\))  
> 4. Modifiers \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Modifiers](https://ck2.paradoxwikis.com/Modifiers)  
> 5. Patch 2.5 \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/index.php?title=Patch\_2.5\&mobileaction=toggle\_view\_desktop](https://ck2.paradoxwikis.com/index.php?title=Patch_2.5&mobileaction=toggle_view_desktop)  
> 6. Commands \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Commands](https://ck2.paradoxwikis.com/Commands)  
> 7. Subjects \- CK3 Wiki, [https://ck3.paradoxwikis.com/Subjects](https://ck3.paradoxwikis.com/Subjects)  
> 8. Conclave \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Conclave](https://ck2.paradoxwikis.com/Conclave)  
> 9. Defines \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Defines](https://ck2.paradoxwikis.com/Defines)  
> 10. Council \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Council](https://ck2.paradoxwikis.com/Council)  
> 11. Patch 2.6 \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Patch\_2.6](https://ck2.paradoxwikis.com/Patch_2.6)  
> 12. Patch 1.7 \- CK3 Wiki, [https://ck3.paradoxwikis.com/Patch\_1.7](https://ck3.paradoxwikis.com/Patch_1.7)  
> 13. CK3AGOT/Traits \- CK3 Wiki, [https://ck3.paradoxwikis.com/CK3AGOT/Traits](https://ck3.paradoxwikis.com/CK3AGOT/Traits)  
> 14. Traits \- CK3 Wiki, [https://ck3.paradoxwikis.com/Traits](https://ck3.paradoxwikis.com/Traits)  
> 15. Editing Modifiers \- CK3 Wiki, [https://ck3.paradoxwikis.com/index.php?title=Modifiers\&veaction=edit\&mobileaction=toggle\_view\_desktop](https://ck3.paradoxwikis.com/index.php?title=Modifiers&veaction=edit&mobileaction=toggle_view_desktop)  
> 16. Factions \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Factions](https://ck2.paradoxwikis.com/Factions)  
> 17. Council vote \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Council\_vote](https://ck2.paradoxwikis.com/Council_vote)  
> 18. AI modding \- CK3 Wiki, [https://ck3.paradoxwikis.com/AI\_modding](https://ck3.paradoxwikis.com/AI_modding)  
> 19. Playing as a vassal \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Playing\_as\_a\_vassal](https://ck2.paradoxwikis.com/Playing_as_a_vassal)  
> 20. Nomadism \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Nomadism](https://ck2.paradoxwikis.com/Nomadism)  
> 21. Editing Nomadism \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/index.php?title=Nomadism\&veaction=edit§ion=1\&mobileaction=toggle\_view\_desktop](https://ck2.paradoxwikis.com/index.php?title=Nomadism&veaction=edit&section=1&mobileaction=toggle_view_desktop)  
> 22. Distribution of power guide \- Crusader Kings II Wiki, [https://ck2.paradoxwikis.com/Distribution\_of\_power\_guide](https://ck2.paradoxwikis.com/Distribution_of_power_guide)  
> 23. Beginner's guide \- CK3 Wiki, [https://ck3.paradoxwikis.com/Beginner%27s\_guide](https://ck3.paradoxwikis.com/Beginner%27s_guide)  
> 24. Editing Beginner's guide \- CK3 Wiki, [https://ck3.paradoxwikis.com/index.php?title=Beginner%27s\_guide\&veaction=edit§ion=4\&mobileaction=toggle\_view\_desktop](https://ck3.paradoxwikis.com/index.php?title=Beginner's_guide&veaction=edit&section=4&mobileaction=toggle_view_desktop)  
> 25. Schemes \- CK3 Wiki, [https://ck3.paradoxwikis.com/Schemes](https://ck3.paradoxwikis.com/Schemes)  
> 26. Hooks \- CK3 Wiki, [https://ck3.paradoxwikis.com/Hooks](https://ck3.paradoxwikis.com/Hooks)  
> 27. Interactions \- CK3 Wiki, [https://ck3.paradoxwikis.com/index.php?title=Interactions\&mobileaction=toggle\_view\_desktop](https://ck3.paradoxwikis.com/index.php?title=Interactions&mobileaction=toggle_view_desktop)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAABRElEQVR4Xu2WsUoDQRCGR4xgp5WksbKzEmIhaEgQFBREMJUoCIIPYCUhja0QUlho5ZNYiM9h6xMIYqkzu/+663hRye6CIfvBDzP/LHc/x3FzRIXCWLDImtKmYoa1ps0cbLP6rHdoGFesJ9RzZM/O+7FhFv4S+gf02XhjPbIuaPiNXNgQFzSk6gFIv6y85HTp+40dVaEE8e5Ufx70Qg9+VkYNH/pS7wW9cAg/K7Hhd1Gv+rGhDX9D+UmJDX+MesWPDevwO8pPSmz4I9QNPzY04R8o/5Np8hf6i6qIDd9Grb/vm/D165SU2PCymKTe8mPDPvzfFlsUo4a/Uf1l0AtuAWblp/AnVD3TnvRuCzueWQPlJcM9Va3r8BDZ77f4C6wd1LUvJyzin6F+IbvB/wUt1j3Z34m6moXcsl5Zp3pQKBQKhcnhAw65dX1uFN28AAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAABaklEQVR4Xu2WsUoEMRCGI3hgp9VhY2VnJWghqNwhKCiIoJUoCMI9gJXINdcKYmGhle8hWIi9b2DrEwhiYaEzycTkfpPbzQaLg3zww8w/yeZnOTanVKEwFsyRJtAEWqQVNP+DLdIV6VsU45L0KvW0Mmtn3FgzJf689E/SN+ILjQCfpGfSuYofZMP62KA+oRfA/QJ4tcAHjeJCxdeHQjHs3UN/5vVMX/xkUjY1De/7XO96PXMofjIpm3LD70i97Maarvhr4FcSOjBGbvhjqRfdWLMq/gH4lYQOjJEb/kjqJTfWrIu/D/4v9iF19WK2DZEbvis1ft83xMefUyWhA2PkhueLietNN9bsiV91sf0hdGCMpuFvoR94PWMvwGRSNo0Kf6LCM/S4t7ew5Y10DV4t8OEh7FtF3fiLlPl+s98mbUs9ObTCwH5P6ndlbvBG1AmfQof0qMzfiVmY+dyRPkinOEjhAY1CoVAojBU/g++C7k/65ckAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAaCAYAAADFTB7LAAABrElEQVR4Xu2WTytEYRTGTyRJpJSlkJRPYIFSUnaysPMBZmWvWFuxkJSi2Fj4AFI2tkqJhaxsrJQIISvO471y5pnz3j/TzO7+6jR3fs95/9w7c++MSEnzGdOaYpnCJ4sI61pnLItwp/WtdaB1lByj0nhgkcETizxgkdhGdiWefWjdsjRgXBtLic/nMi9hwAgHBuSHLCX4DpYJfRLfCPwOS49tCc29HBDeRz2p9UbOcq/1wjJhUWrnc/EW9vD6rrRWyVnQv8LSwPPVMC2h6YYDB2+D/B6Ma51qvUvIcYzqtk0JyHtYWp4lNC1w4JB3g39sSnoOkOOEoniLepxI6NsjnzY2z9yPWsssLXkmAV4f7lx2FmRfLIlLybiTvYWZtJ6YB8hmWBLoWWJpuZDQ1M6BAfkry4TYBgekOos9J9Ezx5KJXaENCb6fAwPyUZbKmvzP2WWOmZivYkJC47VWp9ashMcO3LDp89iX8KBnWiSMx1x4ba2Of8n6DjeMehc5l/rHFgKL4FMoCsbh567pDErxK4Ex/ExtKhWtIZYpFD2hhrAl2f+IwDGLkpKSOvgBPpB1pNTqs6cAAAAASUVORK5CYII=>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAcAAAAcCAYAAACtQ6WLAAAAbElEQVR4XmNgGBwgB10ABi4B8X90QRgASWCVFGOASKxDFlQGYgcgngOVnADlowCcRoIASOIzuiAMgCQb0AVBgIMBj5E1DHgkPwDxOST+XyQ2WFcEEv8YEpthIRAfBeISBhzG1wKxH7rgKMAHAMCtGTqyv2evAAAAAElFTkSuQmCC>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABgAAAAaCAYAAACtv5zzAAAA8ElEQVR4Xu2Svw4BQRDGR6VQ6khU4hU0ColGq6DxLF5BqaLQkHgCiSeQqBQ6WlQSL8Bs5iKznznZ3G3nfsmX3Zlv/lw2R/QPtFldTMbgwnqxlqxNcnfKzZ3SB80p3QtiQDKghYbC+StMhjAjaa6iAWR+qtDG0DqPHknTCQ2DTAseJE1DNAwyLQht2pLULSA/ZpUg5xG6wKo7J+eRNdKGxmpErJobxOh/OJCYZTQUzn8auV+xh/WFjilJvoEGfddj7NEhKXBvWWH1SX5bl2uqOg0OxDg3OBDj3Fwhjr7AsU/OHWuijVjUWWtWDY2Cgji8AQVbRUcvBN39AAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAaCAYAAABozQZiAAAAeElEQVR4XmNgGPLgPxH4GRCfh2mAgeVAvANNDKZBB4s4fgEGhGZ0gCJmy4BpKwiAFL1GF2RA03wbmQMFqgwQRXnoEgzYXYMCXjEQoQgXwOVfgkCdAaKxDF2CGLCAAaKZBU2cKEC2k0GAvpphGrBhQyR1o2AU0BEAAMmzLsXJ0A0pAAAAAElFTkSuQmCC>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAABoUlEQVR4Xu2VvytGYRTHjxT5kaKQMhgMBhmUbLJYGPgDzMwMpLBKInZK/AGiDCwii8xSVhaU1SBxzr3P877n+d7z3JsySPdT33q+3/P8OLf3vc8lKvkb3LJ2WF9YUHRQfj2XdgwcDaxmDB3YkIwXlfdIPo6hhUxE9QcziHpc3ur8A2uhUk2RujSnvTDF2mets9pYY35CEdhUTVhOkLzeyOQg7ZfBI1YWZQsD4JjsDf2DaL8GXiO+CbJcihrDBjyYy/gMvKbonAybrHOqHjQbljMNeKxcvLw4p0b+Y2SR/1N7fwje2jiWH7GGlH9jDSsvjcfe7FzeKTww1kAs1/SyBpV/ZXW7cdHaDBf0e43p+gD4F4rfl8ldtArZCaUb9DkfayCWe25YS8o/UTh/nrWifIC1+SNku+A91lrNHHhr/j34Cs8YUHYDuXBxQ0GyGQwdHxhQ+tPpfSZYe8pnkMnTbnztfG21nNDocvnGdbI+WSPBjCpS68KQaaGwMethA+pYl5ROvIKaRj4/B6w71iTUNPqqQWT9BmuUtR2WSkpKSv4H38TIgC4WY/6lAAAAAElFTkSuQmCC>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAABBElEQVR4Xu2QMQoCQQxFI1aChQqCjZVnsLSwEhuv4BUsbL2AWNh5CBER2UoQ7+EprCw1cdbVzSazM7Igyjz4sLxJMtkBCPwxHS4caHDBaGNKXPpw40JggFlgLmDq1+njhDnmHH/XwNRWX8fuuCx1xZwwXdCXqkN2VkVwTvg2aUuRl2aRW3GZhzTIxidLSd6Kb0OhS00xMyHUwB2lZ9oyFLqUhm8D1W+4BP1yzVvxbaD6LZegX655K74NVL/jEvTLNW/Ft4Hq91yCfjm5JZd5SINsUH3EJTIGeZbkEujJD0KoiTvKxLQ9eL6ClHdGsWtihvF3OVXxJfpgfuqIabGzQCAQ+BnuZzJh3FAGlGAAAAAASUVORK5CYII=>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADsAAAAZCAYAAACPQVaOAAAB8klEQVR4Xu2WvytGURjHn2RhkMFAfiQlQhY/M8mAyWCQRbHLxIJNFoqYlPIPYFEsihgwUigLxSCbUgoD5+mcU8/7vee99773vb2W86lv936/z/Oe9573vefcS+Tx/Cc9Sr9KZ0rPUJO8Kw1iWAiOMciBGvA80Wpzfq/0KGqWeXLnTnjAVgzzgMfLpivT0+aosSSljmzEHJeV9pU6KdgTyYXSHoYJwQm4JtMM+bdSnagzw6YmWQG/pbQBWWyaSH/BNBZiUoGB4Qt8AwUngth/XzIOfg18Ivg2+VRqwUIErk1ih/SdI6mn4ERcyJ5Kcc68gE8F/sJ8Np0TDBS1pMf9MEfWdkaH5o50bcAcLa9KfcKnimv9xOFBqQhDRRVljldmfLvILEMUXFa34LvAJ2KG9EVMYSEG+G9EsUq6vxgLgBxzVnheLomwv/wRFnLA3p5xGSXdP4YFAS+JJeG5f1H4XXEeCx6A11K+hE32QOkQMt7cuH8TcgmOx74XfCQTpBv5tk2LsMm6anMmK4fcgv0MZ/zMlj4UbrjGMAV4XH5ndcG1EsjeSD/uXCxQ8PHF8Dgd4AuO3V2fsGDgHZrr3cbzS0fYhZ5iYODPnAs/Kc4Lyg9lf6Oy3JC+4HUsCC4xEDSS/nw/6WevR8K/TFx5PB6Px5OQP2WYkR17RccOAAAAAElFTkSuQmCC>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAZCAYAAAB3oa15AAAB4UlEQVR4Xu2WzyttURTHl4deZICUwUvJREnp/QF0UyYmyoQMKAkDAxmI6ZsJI0M/kqGZQtGb+TVkYsBEETFhIBMl1mrvxfI9+7j7Zuh86ttZ3+9eZ9917j3ndogyfi6DrFfWKesI1izS04RhPpoxAMpYFRgG+IuBQQZTHlmHxivLrD0MQ5SyplkH5Da2m1vqya1VeX/Omnxf/eCZNeHrIUru1xHI6vxxlrXOaqBkTyo1rBPWAH19AZL/DmTVxm/5zLLK2jb+HyV7+sDvs8YgiyLtAjYonGO/1E/GK5KX+HrEe0ujqX+xRo0vCBxIic2lPjZekXwcvNJuaiH0OdHgQEpsLrXcRojkcpsqD6xrcrfOrcml74/xBYMDKbG51HK7IZLfQdZP7rmz4Lkt4POCAymxudRpv8ANhoDdZ9H4HZPnBQdSYnOpd41XJA/91yuXrG7jpb/H+DlTfwkOpMTmaYNKPo+h4Qq89FeCjwIHUpYonGM/eiWUKaE1zNCnkjZAEYVzyYaNf/GZpTeQKfLQLmBIrt++rqSd/44OjrKU+6yTVUtu2LZPHY4z1n9fb1JyH8sMBh45Z8XXxazcx9L3kNeGNXJvkV2wZpliXVD421XuMTC0kruInD9mZGRkZGQkeANh1aERUBn3wQAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAZCAYAAAB3oa15AAAB5klEQVR4Xu2VyytFURTGVx4zAwOZyISBPEr+AHVT/gAmZEBJMTCQkcfMTJhQJiKZMZNHyMxryMTASBFRQsmAEmvdvXfW/c4+d9+LmfOrr7O/b6+zz97nsQ9Rwv+ll/XJOmedQJ9GauowDNGAgaUagwBNGChkYo4X1rHyjkXWAYY+ilmjrCMyA+vBNa5PazajwvDOGrbtPoqO1+rJKu1xirXGqqJoTSxlrDNWD+W3gI3M7jRbFD1/mbWt/ARFa7rAH7IGIcuJ0AJCSM0rhmTyItvut15To9oFrAHl8+IvFnCKIZl8CLyjRbWFXK4TS2gBcmdczVtmdxrJ5TVCJJfX1PHEuiHz6typXOoqlM+b0ALalN9hPSovSM06ZILk95B1k/nuNHhuI/gg2RbgQ2qvwcc9gVsMAX3dBeV3VR7kJwvQ9dLeU94huW+vd1yx2pWX+g7lp1U7Kzghh+wSzxhStD5uopLPYKjQT1GQ+lLwOYETcsjPSfJyyLEevcOXOXx9mKGPJW4C46wVDMnU1iv/YTNNpydzyEc7hyGZ+hLwWXETR2lk15kn8+ceI9Pv2yUuWPu2vUnRcTSTGFjknCXbLmSlvrt+xyqZ7fCBVQt9mhHWJfnvrgO3YE0zmUWk7DEhISEhISHCFy0mnP8FmdPiAAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAWCAYAAABHcFUAAAAAdklEQVR4XmNgGAWjYBQMPPgPxHfQBQcDsGGAOK4aXWKwgE9A/BddcDAAJgZIyO1Alxgs4AADxIEghw4q4M8AcdiAAwEgfgnEK9AlBgpMA+LfQGyELkFvEMIwiIoFRiDeBcQ3gZgdTW5AAAsQe6ALjoJRMApoCABGWRFi13W6wwAAAABJRU5ErkJggg==>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABcAAAAWCAYAAAArdgcFAAABAklEQVR4Xu2RwapBYRDHh6SuuKXYKcVLsLCzvy6WJBZCslRSdu76PoAH8BiewRMIO3uFxMz9vnPM/edEbM+v/nXmN9N8NYfI50mGnDzKd7lw5lCnVP0yGTLLNJs77iVkyQxc0XokhOIRsmQMLmt9AvwXpwROs9VFjMySnpZM3Po+eKHDOaEkMx/VIm1lW0syQ+In4B3KnJqql3TnZM7yLvhP60fgNS0yM5IP6P0hr0lzAD5pfR08suI0UGpkyS+4nPVB8BrphzkVzh56LjK0ACc/UrwXa/p/iianoGoX5zQaqY/gHLxuPOXsUAoHztl+f5NZELi1XX44EZSKKgofn8dcAT7UNHpdHv+CAAAAAElFTkSuQmCC>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAWCAYAAABHcFUAAAAAg0lEQVR4XmNgGAWjYGDBDCC+ji44UCAbiP8DsQe6BL2BBBB/BOKj6BIDBRYB8V8gNkGXoDewZ4BE0RR0iYECXAwQB4mjSwwG4M8AcdyARxs2sAqIjwMxE7rEYACODJCQa0GXGAygB4jfAzEPusRgAaCQGwWjgBhQSySugWkYBaMACwAAWycWUl75xJYAAAAASUVORK5CYII=>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAWCAYAAABHcFUAAAABXElEQVR4Xu2VMS8FQRDHR0iIJxQShUQkD41SJb6BXk2ilHgKiUalUSi0GpVeI1qt+AI6X0ClkyDC/N/OeuNvbh0vUcj9kkl2fjO3u3d7955Iwz9jT2OFZQ2WNNY1prnQD28a55QvuLyKO40LjQFJ/bgO0fJNv6EtaSIPFmMXgT4mb6wvMMEZuWXzJWYk3kDkwBALYtYnmODAC2XK/Bx5Bj33gYs2BTfO0vGaB2OSmnd6tS6D5vfJ16FqU+BG0poefCCf+vMRbHlpwB+z/AYcAa675IID9UmXP7txl7ypDhck+SOWBfJTn+dCwLXGobgj8+BTxkS75IfNb5Mvgf5TlgXQP8Eyg+IJuUXzI+Sr4Dteo9yDU3my8ZXGqKt9gMXxAno2zNfhQWOTXOmdeqE8vPn8pXmQ/8RFweAJfXmpjVsJfscepTfRqo2xWQ8vlv8JqoLhJ8RE1zQ0NPwZ73+HYag4KjjbAAAAAElFTkSuQmCC>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABcAAAAWCAYAAAArdgcFAAAAyElEQVR4XmNgGAUkgv/oAtQC2xloZLgYA8RgmhgOMtQNSmMDLOgCxAIvIOZhwG+4PxAHoAsigSfoAiBgDsTPoWx8hoNABhD/RhdkgOgBOQ4DIBtGyHAQCALiGCT+JQYcQZaLxifGcBBIYkBEPieaHBygG0Ss4SDwAIjj0QVhYBUDwnZcGBcAybEBcTAQf0OTwwm6GfAbCgKPGFCDIhGIbZH4OEE/A37DcYVxKxC/RheEAQkGzCBBt6QNiLnQxJBBCLrAKBgFhAEAm2AyZ+P+ibgAAAAASUVORK5CYII=>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABcAAAAWCAYAAAArdgcFAAAA1klEQVR4Xu2SvQ4BURCFJyISP+ER9N5BryMoJUKlUXsC3sOr8AbbaEVEo6ZRcCabZZyMuxvb7pd8xZx7M7N3siIFGWjDJezwQV5usA6b8AKfsP91408OHEjcXM2N18jLlDIHaXiNHk6m6KoGHBrOHHh4AxMWEg9n9H6DQw+9eOfQMIQTU0eScWXaeMWhw1w+L6zSmYv+kicOAxzhlEOPHWxRVqLaol9cgSMJr1C2cE9Zj2qLvs6uYga7pn6jk5PdsR6/dryGVw65Yaj5BtY4NIw5KChI5wWw0zYbylokMQAAAABJRU5ErkJggg==>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAWCAYAAAC/kK73AAABvElEQVR4Xu2WvyuFYRTHD5Jfg7IRZZCUwSaRH1lMBhsDBkoUBoSyKmW1sBkwkMVoNMkgir+BLCIpEs/3Pue59/G9z+u9P4zvp06953POPe/p9ngukYSEglkx0csyBwZMrJqoIh9igkUxfJs4o7zLy6NoEttbofma5sypiTextVC9INzLfS4CLgR6vsi9m5gmtyv2i/jXxTHomFyz+jjQs0BuUn2IuMUbWQRIH0cM2vYKDvhBlgR6hsn1qS8nD+IWPzdxydLj08QSHirFDlr/VbbA77H0GBLb00O+Xf04eRC3OKg1ccNS7BFMUy920LIvFfgTlh6jYns6ybeqXyQPclkc4Ojee/mriVkvlwaxg3AbMPBHLD3GxPZ0k29TP0ce5Lo4wE31IBH9JWILG1wQ60Nn34H7Hj395DvU89kH+SwO0PvI0oHiPrk69fj2/gI9U+RG1IfIZ3F3zZaauPMLDgy6Jef+8OJAzw65TfUhcl0cPTNefmji2stTlEn2sI+AC730OeCQt5BzhGYwUfUaE1csXyTzAdzdeK7OlFNEvRRuXp+fJPuXFLjPcjC4Pf76X2bLxAHLhISEhOL4AcTpgJJr0YOOAAAAAElFTkSuQmCC>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADMAAAAWCAYAAABtwKSvAAAAeklEQVR4Xu3RoQ2FABAD0EN/g8Hh/wDMgWEMwi6EhCkwsAmCETDsgIAjZ0gXIIW+pOaqmjMTEfmav2f39FiwGT2LJ8GCRe05PCUWTFLP5hmwYNJZfCLHgs3PXjLkLrMYNWHBrLEYVWHB7hq14pFZYTGqxYLdjAcRkcedzL0RV4zLTugAAAAASUVORK5CYII=>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAWCAYAAABHcFUAAAABEUlEQVR4Xu2UPQoCMRCFU4j4b2FjIWht7xU8hr2Nx7D3HF7AxsJGbBW8hoWCoCI6w25w9pHNZuNPIfngweblMZlNsqtU4A8Zo2FhhEbMEI281EkL0p30iOWKzkudEwlPWqQZqaPeb2qVnP4MPk0V0UyhgAbQRUPzzaY420BTwNfHiE9TbdI1fmb1ZADYkGrg8cdiXdOnqaMY8xGx1xcewvN8jzX8QlbyNmXCpcaaNFWWI5O4FMzCtQZnmmiacC2o4ezO4NlqTEiX+HlJqog5I1kFJWUVZfUCmqwaNxhztgReAltB09wBxgxn5miqaIfSLvVeGf5jekGUxOTx9p9IA1JVRYtuE4kXuEMI1g4EAj/lCfW0W75M5E8qAAAAAElFTkSuQmCC>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC4AAAAWCAYAAAC/kK73AAABoUlEQVR4Xu2VTSuEURTHj5fytlCyIWIpJAvFxsbCfAsrJVsvRbGwkZIvYEchsZGlpRUWovgGii0LIXH/7n3Mef5z732mZ7bPr05zz++c7j0zc+cZkYKC3CybmGQZ4clEO0sPHSwM4yzy8GPinPIJlYdAXyxifUOqnoteSR8CLj3OBw+jYzTQ96F8TWCzE3L9zmexycIwa6KV3DXlIXpYeGhJFhhwWxUS4KdYEn2UN4r/DVc7+IWJK5aKLxOLWDSLPWg1VbbA77LMwDc0wODHUr4uO+lyCvzY71ga3nXSJXajJS0d8KcsIwxLuB97jVDuGy4BV/dR5W8m5lUu3WI3WdHSAX/EMkLo0/ZxJtn9TSaeJdBXJ7awxgWx3nf3faxL4IAAG2L7B7lAoOeFZQKKe+TwhwE/QD4EekODv0plbcu5afKab/dab+JBFxKwwT25kvPVEhvcVzv0OA1qcypH/63K/2iQyk0+Pc43QEKsNib2Smpi/SHfZuKGpf468ezGmv9Esg4L1QBqC2697/LOcvkfPD1mWCpwxQ5YFhQUFNTGL8gnfd6xnGJpAAAAAElFTkSuQmCC>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAWCAYAAADTlvzyAAAAdklEQVR4XmNgGAWjYDgBGSD+DsQL0MRpApYC8R0gZkaXoCZIAOL/QByBJk51wAvET4B4M7oEtUE/A8RHcugStAAcDBDL5NElaA0EGCAWb0eXoDVIZYBYHIMuQQ8Asvg1uiCtgQYDxOK56BL0AAfQBUbBKKApAABSxxFZsHyFUQAAAABJRU5ErkJggg==>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAWCAYAAABHcFUAAAABSUlEQVR4Xu2Uv0oDQRCHRxQUES0EOxEUG59ABB/AlzC9EC0EG6sgWljY2tv6F8HSNiQPYOdzBFTE7C87a8afk72cEQu5DwZ2vpnbm7u9RKTin3EQYoNlCTZZjMJHiGvKV00+iOMQbYn9iMuv5Z+zLHFDy7PjPB5CHIWYkF8eCptdkFtXX4aioTB4jiWbYLOGFYEF9SvkcxQNhfosS8N7WsxIbN7r13qMqz8kn6NoKNCSeE/LttCpLKrYsVKBP2OZYZihAPrmTf5q1j3SULtckOhPWWZA/xXLATRDnIg5MsuYxM32yU+qr5PPgf4blhnQP8cygeI5uTX1U+RzoP+WpQNO5UXXjyGmTe0TbIYP0FJTXwb037F0eKPcffj0S7MgH8ZZULtnacAb+vZRK0/i/I91pH/DLV1jWIs3VHJeMPyGGO+aioqKP6ML/BpXhT6UJFwAAAAASUVORK5CYII=>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABoAAAAZCAYAAAAv3j5gAAAAjUlEQVR4XmNgGAUDCGTRBWgFHgPxfyyY6uAeA6oFp1GlqQduAHEAuiAtwDUGOll0GYj9GVCDzxVFBZXAeQbUyG9B49MU4Ex5TAyYyRMfJgSIVUcSeAXEIWhiXxloYBE212MToxhcQRdggFiSii5IKahmgBgMK/NA7I8IaeoCUQZEmUeTPDQKRsEoYGAAAAS/MsG9MV6RAAAAAElFTkSuQmCC>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAABxklEQVR4Xu2VzyttURTHlyeeXylPSFEGRgYGIr1ESiYM+B+UgTJg4EcxoiQlyvApkbEMDPwJMpYyMjCilImJxPrae9+7zvfuffVmr9f51Lf297vW2Xvde+45VyTn3+Bata/64IKhVcrXS/jNQYRaVQOHHh4I62XjA8gnOIyBxmO/rvF+rFj+osvnTd7fqZYKVQfqGM56MK06Um2rfqnGQ0M5qlQblPVI6VcN/zOS4SDr18gzsSzKqWqOQ8lucE4+gMzmWG+Rt8DXU5YEvwFcYO95s88CPECAc6wvyVt2yX9LOADqF/f7sfAAgVgO36K6iOR/TadkhxvOlqMDgFR+phow/lk1aDwGTz3ZGbD5imrdr/lA9oFUbulW9Rn/pOrw67LXHkjpuyYcWEGeSeUWW+8l/yju24sS2/iHuHze+9QAqTxwpVo1/kGy/Yvi7lKU1MabqiG//iPxvu8GWyAf678lXwCN1RwqL2aNW8obAmSzHHreOBB36+w+k6pD40tA872qUdwTCT9jG5Q6n+N916Z6V41kOoqg1s6huP3tYLEPm6FStad6FfcwpMDfD/5Tb1RTVLOccGDA9TuqUXFn5uTk5Px3fALawYFm/zP2NQAAAABJRU5ErkJggg==>

[image27]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAZCAYAAADAHFVeAAABOklEQVR4Xu2UIUsEURSFD1gsJkHTNpNYDPZN/oBFxOAvsAsabaIoCAbLJtMW267BpmIVk0VUxD8gRhG913nrnDnvzTyTaT44zD3nvsednbc8oKXky3QSnnVcmU41zNERzwM2gp+kzFkMeSO+QDVL/b2QMRfhuWkamlZN92W7Hh2kXCPOP8UvmV4lS7KjgTBAPMzPhvnTICc3bAHxsHWqD6jO4sMuUX7GtWr7h20U5zSN6uAjU598Ft88JX6X/Jgt06Fk+ou74rPU/VGUF6rnUO5ZNs1Tr5En5If1TM/kff0D+Xeqf/GzcDF3KDZPSM7oy7j324V9ROqTpTLmTAMU6/fFR7xpgOZhM0j3PDsWn8QbK6G+NX1Qj/FBenOMeUR1wDnVFfxCvUGxuHYRGt424P2uaSR5S0vLP/ANBLNWNhhBinYAAAAASUVORK5CYII=>

[image28]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAWCAYAAABHcFUAAAAAgElEQVR4XmNgGAWjgHbgPxBnogsOBjABiJ8CMT+6xGAAIEeBQm42usRgAPkMEMeZoEsMFgBy3BZ0wcEAfBggjhsUoAiIHwOxHLrEQAAZBkjIFKNL0BswAvFeIH7CMEiKBlsGSMiEoEsMBOAC4h50wVEwCigEtUTiGpiGUTAKsAAA3AwVbD6+axYAAAAASUVORK5CYII=>

[image29]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHsAAAAWCAYAAADgreP7AAABlklEQVR4Xu3YTysFURgG8Jf8yconEGWrlISFlLKQnY2kdBEb9lY+gIWNb6AsfR47CxuxkKwsSJznzpkcz/w7Z/KvPL96655n3pmpee/cuY2ZiIhI16KrQ1eDvCHBiKs1DuXvGHP15mrAr4/8OtW4Zft1eIP8jJihoeeFsmdXm5Q1wXE07F8UO+wDyvZ8HmvfVZ997bDxSyEJYgaGnhXKlnzeS3mV/Dwpw0ZvD4eBJw6kXtOwly3rmaN8yuerlJcJz5EybLix4hfq2DToVpqGvWFZzzTlEz7fpZwNu5oP1qnDBuzTH6zvg8+SIHbYs5RP+nyH8tCQFY/fZthw7erM1ePnWMrgIqcUfj5hwa/DuxNmfI5nd5VXy+7sUNthA/bFnzxpCRewCXq2KVv3eR3+AnHFunB15z9fWvEZLpFiLjp6Tik78Xkq7NPhsAZe5PAzGsfQwFuIGRiek9yH9WhJxn0M27c4rHBuH3c0yx8zkqBpODn05S9WHqz4Rg3qhp1vC6vJLQck5hgS0AX7R644EBEREZHv9Q6JB3SnK/PcoQAAAABJRU5ErkJggg==>

[image30]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAABy0lEQVR4Xu2VzStFURTFz0QpH0UopShKUpTCkJQJE/4IpaR8DORrIiWJMDBTYsLIQIpMzCRjGRgy8RFGhMTe757jrbPeee8xk+6vVu+utfe9d7ffu+8aE/M3OBOtiD65AJSZzPUU2kU5HFqqOQjAA+nxGHiH5l0chtDGO3tcaH1uspxAM9aq1xFlOhx6pUe0IZoXFYs6XUMmBk3qWt2NQ5nTnl9OoPkUeSaUBQkNMRvI2IfQnjnyiPo8ytKizY+UDdkcYR9Cew7JI0vkM6InP1M2Y/M2yNT320/VK9QQrZWK9gP5r3A3Qk5sNgqZ+l7wB6IH8MiuqBm89rWC18HzwadFb6r/LY4bm/VBFkJ7rjgkakRN4PXpr7DHvJAUzk3UtCB6EQ1YXwU9IULbZrDeQP7WRNv7MYvGv0Ct6Am8I9tgp6Jx8NfG7x8RTYP3KBIdU/Zm/As4j1+3km2wYfKh/gvy3xyZqLkSMvVb4CdFm+Ad2lfPoeWdAxN9dThYt2gdvIe+InS4FlGHiU7EH6tDn8I1UYlowkR9jV5Hkg9ROYcm+bpz8PZS0JVfirZFBVRDdkz0xN6L6qiG4LYZ3bw+ZO2iZb8UExMT8z/4AvMGgnp1RYZFAAAAAElFTkSuQmCC>

[image31]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACYAAAAZCAYAAABdEVzWAAABo0lEQVR4Xu2VTytFURTFj1LyJ0UhZUAZGyiZycQExYSPYOrPgBRjSYmZASU+gAwM5ANITKUMjJhQppLEXu7Z7+273r6XZyTdX606a+19zznvvHffCaHgb3Ap2hZ9cMHQHvLrFQyIajkk6kVNHEZ4QxgvGa8gH+XQA43jcTwd/Vy5/EV3zFuivxUtlqoJqGNz1oNJ0b5oXdQqGtGGPLChV1GzyTAhHzV8nZNhIetXyDNe5qLHv2My3tgxeYX7MF4jb4FvpCyXXvLegrwI4BzjU/KWTfJVcRcqJ+QNKF4O3yY6cfJfoYt4E1SbH4XkDVeeRYPGY+NZb3YuWOyBvLeBrNyCn0m/8U+irjj+7tkKeEH2SlZusfU+8o8hOb0fowtOkWeycuVCtGz8fUj3L4hWjU/hTa4Z/mzBbvSM96xlnrzXf0O+hNfMWQ15BdkMh5E3DkLy1dl5xkR7xqfoCUnzbEgu1/Po9bSUhpjjjusQvYuGUh1lUOvkMCS3i92Y92FT4Fo5E72IrqhmQd+B6Fo0QTXLIQcGPL8hGhZtpUsFBQUF/4NPDH+DGi/JXtAAAAAASUVORK5CYII=>

[image32]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAZCAYAAACo79dmAAABgUlEQVR4Xu2WTytFURTFd0z8GRobyIhQSplKMiAj+QKSDAxNDJQJZapkZEAZ+QImEiZGZEDxEUwUUTJgbee+7Lvc+86+z5uo86vVO2udfc7Z78+974ok/j+j0DV0AU3QnOWZg2bSy0FGN/lPGj8YX0Pzew6biR5QJAtnx9AUNAhtQLvQEHRnairzwUEB3ORRfvobbnYR2jRe2SdfGf6EitCadg4JbnYbmjVe3+CW8Q3RrGYPJb/XixkrnnOieDbRmo7sVfUG9eQqArfQAjQOzZj80Yz/hLdZe7s5zzK9eBj9+peNn5dwO7OMkHfjabYI/o2WcWXGq9BONq67tra5V5dhWSmeZvUbsNj6JejAeBexA5UnaICyWLN9kp+fJK+wjxJb0Cah5p3yWLM8t1KQsY/iWbBHvlXCurL/+DWohbJp+X0W+yieBSfQK9QFdUpYc5Or+GEdOuUww551Bs0Z78LTrDIs4X6p9WUPNkq9/folPMSMSbgOKqMPHIlEIpFonC8/RHPuBPROowAAAABJRU5ErkJggg==>

[image33]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADYAAAAZCAYAAAB6v90+AAABxElEQVR4Xu2WvytGURjHn0ESslgYbAyyMKCMsikmZbCJxeI/UMpAKYM/wH8gycKoDCRsfhULEguyKPE8nXPenvvtnPu+97y3GM6nvr3n+z3PPec+3fvee4kSiXr5Ya2xHnBCMcyaxfCvGWA1Ymg5Y3XZ8QmZJpE58uelM8paJrOZqCE7XeGL9aG81MqxGjxh52dY26wlm3VWKiLBjXx8s45ZQ5TfGK61BdkYeAG9sItBDL6FQ/RTuLF31ieGlK3vtV5TzUdTZKG8xiSX/w8i+SJ4RzvrRflL1oTydVFmY3sYksnPle+wWYv9dbSyxpWvmzIb28GQTP4MmTxQ5EGhwfPoAV8YXDAP15jvUZ53xR4xBKRGrpj2wgrrRuVepLiIXs1hGVxjTThBJt/HkEx+hCGwocYLrE3lXZOFKXKga6wZJyjcgOTrGCrewEv9pPJ4y9ZMTGP6tnFck38tX+aQV8QgZFKvX+ry7osib2PENdaGE2Q+k3CtaU+mucCATL1+Oq6qcSHyNnZIjU9Puoi5srnQZ8fuuxAJ7TvCulc+VFeV6AMDdLPuWKc4oTgk86EbQs5pnnXLmoK5mjnAIJFIJBKJf8Qvz+6GoXGhKeYAAAAASUVORK5CYII=>

[image34]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADYAAAAZCAYAAAB6v90+AAAB2UlEQVR4Xu2WvS8FQRTFp0CBaDQUOgpUCpGoRHQSGkShEyLRKHUqBYlE4Q/wH4iIRCiFRsRH5SuhIREaRKPhnuyMXMfdZ3cfiWJ+ycmbc/bOzM7b3dl1LhIpl3fRouiWDyi6ROMc/hXVojYODTpEVRx6jkRNvn3gkkUyE87Of51Z0ZuoTjTkkkmtiVHzojxqepUPmeXHRGuiOZ81flYUhCey4Jopn61TznWrlPWRB+zBBgdFsAZmrCvE2bPoVfkAaip8u9V7zU++MFkG4kVYGdp4fhjkM+QD9aIH5c9EA8qXBZ9wVqyFbSofQH6sfIPPavxvoFbUr3zZFFnYlkv6NasMnp85gPyeMmwo2Cg0fB4t5HPDA2YBffgdU+qK3XFIoAZXTHswL7pUuQmK8+gx6fYNHMPuxiDf5tAl+T6HxLJqT4tWlA+LzE2ejk/O3iBA2gKQL3GowJga1A8qz7dsZrIubE9USZnue0E+YGUBvCI6KUO9fqlbd0cmSk0cwD9+KupRGnFf++IziccaNTLNCQcuqde744Jq56LUxAHUWDrURcK5z0G7b4fvQiZt3m7RjfJpdT9SuGMKeAVcu++L1uy65EM3DZzTpOhKNEzHMrPDQSQSiUQi/4gPgbOSaDpQfxoAAAAASUVORK5CYII=>

[image35]: <data:image/png;base64,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>

[image36]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAABL0lEQVR4Xu2VMUpDQRCGJzFgF0hhZZFbWJpLCCkCqUxhbwpJaQorm7ReIAdIYWmVFMEjiF3AQjBNsBAzk50h834WFBwFYT/4ecw/w87s4+0+okKhwgkaShMN5hiNSI5Yn6xzjUesl316h+RR7UpFIIeUGkydZ009OFC/mo4lN8CM1QMPa34VabZAM8OfDXVKqdkl64l1w9qwVr5IkboHfYqW1XQcA0oNZJCW88V7dLF5/gRKfOviMC4oLT4HP/edIXZizzBhHNB+oe/I6Gg8dJ7wrv5XSA1u6MfYbnGoN/WNK9aziw3cZBiy6CTj+WYYCzX1rsEPQRZ+zXh+CHlz+PuRt4uDhmHf45rS6brTGPlgdVkNStdBriacMaVG/neDyD0l18c9qw65QqFQ+DdsAWILXUek76jOAAAAAElFTkSuQmCC>

[image37]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAABCUlEQVR4Xu2UMapCMRBFRyxUsFBQsLH/2xBBsBFbK7fgKiys7FyM8isLwQUIWtrZ2WghojPmRcMlg8Ifiw85cCFzEjKBvBeiROLJD4oITU4OpTVjzolTy+ol58apPlc4JpxdNq6QW1N+Tdsim28i7hLUckBxIaWIM0M2ltQjTqs94mYoLZArKIKTZkeotUPFvCkFck1W4LXmmjfDN9jiBOnNNW+O/7OmgdOaa/5Bnl4LPsk7cB3WHs1/BWyGtUfzf2JE8Y3RYe0RF16zCX1yG+/B4yGGUHtizoQr58wZcDrkXnJpJi92SC/z8sh2s7F8y1+jzVlzDpwFzIW0OHPOL6cBc4lEIvFvuAMPUV0smCejIAAAAABJRU5ErkJggg==>

[image38]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAABH0lEQVR4Xu2UMWpCQRCGRyyimEILQRBJYWNhY2NvaeMVvI82djaew0a08AAWaT1EIAFBm2TW3cX3fnf2jSTYZD/4YffbmZ1FHhIl/jldFI42CkeHU0L513wLQWaco1vXyda83o71nFEEwMeEehp0/9BqwKnQNJmaF5SA9OsZt0RZROgi5LePCvkomgb/qC+3NnnLVcjDJR9F02BqPjN7/xH3Mk4aLvkoDzc4cBjuPZK/4g+12ds2ERyGe4/ko2gaPjh9cDgM9x7JRylqqJCtOYHHYbj3GLdAWUToImSFgmxf9uOfOoeEXCGapi3Zv4Mhp8a5cA65CsuE7H1Nztity7kKJZpHGQacd7L1czjLMuJsODtOC87UrFEkEonEk/kBOJRrUXVUyXwAAAAASUVORK5CYII=>

[image39]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHAAAAAZCAYAAADpG6rZAAADx0lEQVR4Xu2YWchNURTHFyFEZMqLRDJnSkiRiEQeyRSZlamkiLzJUB4NRUqJ8oAHRXn5QsqLB0WmB2WIKBmikFj/9l7uuuvudb5zXd/3Xdf51erb+7f3d87eZ517zt6HqKCgoH64YcV/wHuOzla2ET+tqJbmEviAwkkkdnI85JivO/1j1HrRJluRoA9HJysT1DqWzATi4DONmx29TWBPU69X2nEMN24xx0kq3aQeaDsey9Ni3TKX4xNH+1j/QJXXUJM6RlV4CexG/sFTCVxu6vXKCSuYNxwXON6SP+ddHK+MQ99nCWdJOSGrLRdeApeQf/DnVJnAr6Zer3hzAlkJhJ9q3LnohY+mLsDhV5ki1b8qvAT2oHDwR7aBWcAxVNVX0F8YSCuwneOUlQovgWMo+L7G74teQDn1/54Hns+Nl0AgJ5a4zjGurEd4hNh+MqhDqn6Z4zzHXdUOhsQ6bgi8m1DGe1ZAXRYD/WNd2M3xQ9XvUXm7JasNeAncT2m/mYLvF+t67hrPA8/nJiuB3al0ch2TdCdmVPQeegL3VVnacB5hbHRgpCoLK1UZbZtUXZzHLSsMXgKxcEn59RQ8fqFAz1PjeeD53GQl0IIFgAwGd79QTQI1WX4rhUcWyk8orPos8v/o2xxLrUjgJfAYpf1GCh7zB1nzSXng+dxUk0DBDmiEqVtsf0F8KvDYAleMvxQ9GGbavnN0UO0a/aj18BK4h9IeNw58l1iXcVg8DzyfGy+Bq61Q2AHl+QWmVqn2OB5ImvRFyB4LdKVwbN2ewvMaL4HYx8Fja6WxifXO73ng+dx4CVzHMcDKiB2Q/QW+UGWANny+sngXDGDDjUWCbJyFoxT2bcD+b8eEAy+pcvOeIms88POMuxq98NjUBbh3VkZS/avCS+Aa8g8Orx9lstgRvqkyQNsX40BvCm32RmniGE+lR5RmIMfpWEZbr1LTb2dJuRRZCcTi64xx6Kv7Yx6p/4fDTZ4i1b8qshKIFz8+BV2jsLHHIJCc1FeXixQGs4rjSHSHo9NxILZp4PH+2stxk2Nw9JLApxQWDPjkpSeMMrYxOM8Mjtcct1W7sMgKgx2jxGjdKTosqMBBqvwyAwZR6DeBSq8We4Nq9Hz+CC+By1R5FsdZCidbq7xlOmW/O7PAgmQLld+p2FIAPE4XUthWaObEvxM5tlHoZ9lhRY1s4PhM4SuMB/a2eELd4Zhi2iwtlsBGoeYL1MLUPL5GTiBWj01W1hlFAjOo+eK0AjWPEQm0L+9GIbXIaGvw/mzU611QUFBQUNCi/ALRcE2vhzFhrwAAAABJRU5ErkJggg==>

[image40]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADYAAAAZCAYAAAB6v90+AAAB+0lEQVR4Xu2Wv0scQRzFBxSbWCliUlj5A0SLpAhCCgu1U2JlSCFpJDY2aQUhVQqFEAsLS/8DkZAmKQUbCYmdJiHaJBAUgoqNIPp9zIw+H+Pd3p6CxXzgcfPefmfm5nZvdpzLZOrl3LRg+qMXiAHTlIZ3RbvpsYYJnpiaNAx8M3WE9qbzi1Reu3R+6wy76xOhnZr41HRMHjVD5GOW8pOmVdPbkD26rCiJTpQCNQfkX4RsjjKgY61INiIeqAcfNShDamBF71Bn8L8pOzKdkI+grjG0e4NnqvnSFBmowdRKftb5fq8og8f/R0H+RnwEY+6T3zY9J18XRRamoM//RPZJMoD8O/mHIXsQPiPNplHydVPLwlALjekF5/M1DZ3P/0mGDQUbBaPfo1t8zeiARVh2vh9PXumO/dVQQA3uGHvwzvST8iTx1y4q3gVTxDr2n8lHkG9oKCxSe8a0RJ7nqImyHePC2sinFoD8vYbEoXjUj5PXR7Yw1RaGk4beHRAznEbAj+CVVBbBK+KpZKjnlzrefaWoNDFocb7mTHJdLI5JOtbLRMZsaeB8Pe+O89SuiUoTR7CroW7Q1B/aqX477irvC+14LlRS/cEz0x75m+qqUrRjj/OPGx6fD3KN6TLtmr7qBWLd+YPuTeA7TZt+mSbkWmG+aJDJZDKZzD3iAvnLlWORY0gVAAAAAElFTkSuQmCC>

[image41]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAAA6klEQVR4Xu2QzwpBURCHR1bKAqVsPIYHsJKNV/A+srDzEJIkNkryGp7CSlbMuPfijplz5yCr+epXt2/+nS6A4+RocMFoY0pc/poeZow5Ya6YWb78YIQ5pt81SHqrz7KdCxcCZ8we0wH9UXVIaq9UBGcidkh7FHlpF7kpl0VIi0J88ijJB4kd8EdZof45l6Af1/ydrGjNIRl7g2oLLkE/rvkgsQPUv+QS9OOaDxI7QP0rLkE/Tm7CZRHSohDUv+YSGYK8S3KFWIayvyDllUHqmph++l3OdRjhi7+li9lidpgWq5nZcOE4jvNnbmNbYB4iF0LCAAAAAElFTkSuQmCC>

[image42]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACAAAAAWCAYAAAChWZ5EAAAA6ElEQVR4Xu2RPQ4BURSFH/FTKG1gGpVliMoOrEDHKuxFolFQKFQKnUpEQ2EBCpWKezP3TU5OHmFmNMyXnOSd783c9ybjXMEP0ZMMJFXeIIaSDsssTCRnWzcldwujbkd9BD01fFjX3BRc2RwyDrhUhL6Y3U1yge7h91LBh4WcrjfQPfxeboQusIDu+coFVi4e3AKnfQbd85UL6NB+wM3JKckFSlbezTN0L2LpYr9k6V7P+hgdVoF+hbXunaB7crvAWlInh8OP1JVawKWCfw8G0d6AvjeXGT7UZ4sPCQfzStvWUbJbUPC3PAC5zVTE1dKBgQAAAABJRU5ErkJggg==>

[image43]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAWCAYAAABQUsXJAAABhElEQVR4Xu2WvUrFQBCFRxDRwkLBRhBrLX0CwcrGUlFBfAQrwVaxE0FQeysrS8HWUvzBQvABLEQbe0V0JrtDJifZuXshYpMPDsmcmZ2d5C7hEnV0KD+spXhNccV6RPMvWUSDWYZYBr6I92MxPinTBYfRb4V91g2Fhl5TzVsNVyrq6zWeZW2z5liXZdoHmzUhzeQBdsivt0O/sWaq6QJcj/Ek6wu8JLjYI2f4XkjNKMSW7MEFXOzR1vALJj4z9xvmPoucDZWc4eULoUfnoZoumKKQm49XZZP1ZOIsvGGQnOHtkfhgHZvYsgUx9pUv1zh4NXCRR6/hkREK9euYAM4hru2hP2Wu7sKyCv0OL0h90/FRJqja8xpil+xC8ofXh0bEe0fTgF8XqX8FL0nThin6HX4gegfgK2usIfCk/gW8JLihhze85PbAu2d9gqesUvN/F+n/jWaK1DAWfauoI1tEYdMV1iDrlkKNvP0mUvvuUjpXI7uwRU7RAKapfEEuz2h0dHT8H79rTYGNNPpd0gAAAABJRU5ErkJggg==>

[image44]: <data:image/png;base64,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>

[image45]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAABiElEQVR4Xu2WzysFURTHj1+lCCvZqFc2slIsFPJSFl5JsRL1ivwBlrKxVbKklJ1/wUIWUv4JKStlSUqWnDP3XPfMtxkmzXgL91Pfuudz5r17Zt57M48oEmkpQ5waygyGOW0ogS7OFMoquOTccXo4W5wPDXLAudd1P7ljBkI7oVv9iNbXWlfGC9QX5DZsGueHtfhBLVknLvUYuFKQK5e3oXVYe8SdQb1jamFPfSXIGz9luKLD43FLphbW1P8JfeQ2ezAOh/RY39D1ZGgn1NXPgK8E+Q3IZu3GFRl+Q9fjoZ0wrX4VfOn0kttoFHyR4dd1PRHaCbPqV8B/0UHhjYokC7l3S28QG5T/Ouvrusb7+7x6/DqVimxwilIpMrw8mGS9ENoJy+p/erD9mmcUlB72u+GPod43tXCovhJuOefkPnafJqVPSOqsAdBJ7Z/CnkfOEbhSqFG4qpjdcFiC3L/Fy29iUdedqSMc4rd1/cp5N72WMse54tyQ+yOXxwnnjbOJjUgkEon8Hz4BnLJ+mXk5rKMAAAAASUVORK5CYII=>

[image46]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAABrElEQVR4Xu2WQStFQRTHhyhFWMlGvbKRlWKhkJeyoKRYiXpFPoClbGyVLCll5ysospCy9AWkrJQlKVlYcM7MGTP3b96bua8kNb/61zn/M2fm3Pfevfcplcn8Kf2kCpoBBkgtaALtpHE0f4ML0h2pk7RB+hQhe6R7iXuUWdPrypoO8Qclv5K8KT7QCPAC+ZkyB9Y8zw7rYwf1CV0458PgJYEbIfzJ1TvQ9zC3sHcC+ZaXMzvilyalidc8BbzU4XHdgpczK+KXppmmbmX6HjwPh7T4/rzEY66sqYo/CX6U0IEx+B7gvlbPSxl+TeIRV9ZMiL8MfpTQgY3oUqZnCPyU4VclHnVlzZT4S+B/YzdJ1a1pK8DPbq71YUG5PsT3qxLj831GfPw5RQkdWA9ee4ymkDI8v5g4nnVlzaL4sRfbD0IHhnhGQxV7Gw1/CPmulzP74pcmpemGdKrM125VU8UL4jy0F3qc27ew5ZF0AF4SuDlSUe5TRW27ZRp+frPP98ScxG2FFQb2NyV+Jb17tVLEhi/LNOmSdK3MH7l6HJHeSOtYKMM5GplMJpP5V3wBEfeMCmDuERAAAAAASUVORK5CYII=>

[image47]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAAA/UlEQVR4Xu2UMQoCMRBFRyxUtNBCEEQsbCxsbOwtbbyC99HGzsabiB7BwtZDCAqCNjrZJGz2u4NCYiHmwYfMS8gMS1iiyJ/TQ2FoozB0OAWUoXkIQeaco1nXSZ+ppdthwWFu2e2EBr0OWslxwVAXl1AC0tdTboUyBL5D5Xlv7FAXs1bpZk7IzSXvjbr07NT2EfcdJzWX/FfAZlhbJJ9QpPTAJ3kHnsPaInlvTpwBOGyGtUXyXpRJX3oFj82wtii3RBmCNQrSzdzHPzMOyXNB2JL+HYw4Vc6ds8+c0ExJD9HkTMxaveWvMeQcSDdawJ7LmLPh7Dgt2ItEIpGf4QnadV3uhYXOUgAAAABJRU5ErkJggg==>

[image48]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACUAAAAZCAYAAAC2JufVAAABBElEQVR4Xu2UvQ5BQRCFh6hFo1J4C4+gVkh0ElErFUrRexeNREmj8RBeQRSiEHay98Y6dnZnRTT2S05u9syZnfuTu0SZP2eFhkAdDUMLjW9xjyiUazt1NVc0POAgV41AbujUkuDmGD00yH5S/KyavVRoNqqiQf4+n/cRn2wk9bC/La6sw2tZjzRAYkxyD/vuH8jrpbNWIw2Q4PwETYEm2XwfCyXlK9VqZ9ve4Jr7x8Xg/B7NGNykpUtyfmZ0RJOeD5lESsOZ5LxveKXwFuBHwY1C+AaXnIw64E1JzgdJaQrdFHMzGhjVyB4HoWyQlMa50QhNgM+pi9GG/IeuijUamUwm82MeBC5cqBawNzYAAAAASUVORK5CYII=>