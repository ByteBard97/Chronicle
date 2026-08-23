# **Architectural Limits and Technical Evolution of Economy Simulation Mods in Skyrim Special Edition**

The economy of *The Elder Scrolls V: Skyrim* relies on hardcoded base prices, fixed merchant chest containers, local cell reset timers, and an infinite loop of loot generation1. Over more than a decade of modding across Original Skyrim (Oldrim) and Skyrim Special Edition/Anniversary Edition (SE/AE), community developers have attempted to introduce realistic micro- and macro-economic behavior3. These efforts range from basic multiplier adjustments to complex regional supply-and-demand algorithms3.  
However, attempts to build deeply responsive economic simulations within Skyrim’s native Creation Engine have repeatedly hit severe engine walls3. These technical limits include Papyrus Virtual Machine thread execution bottlenecks, save game bloat, fixed record overwrites, and hardcoded integer bit-width limits in native engine code3.

## **Part A — Mod Survey: Mechanisms, Models, and Macro-Economies**

### **1\. Lineage of Price Response and Supply/Demand Systems**

Early attempts to overhaul Skyrim's economy focused on altering static pricing variables3. In the vanilla engine, base item prices (![][image1]) are modified by the global barter variables fBarterMax and fBarterMin, adjusted for the player's Speechcraft skill (![][image2]) and relevant perks3. The transaction purchase multiplier (![][image3]) and sell multiplier (![][image4]) are calculated via linear interpolations between these engine floats3.  
The earliest structural overhaul, *Trade and Barter* by kryptopyr, introduced a contextual multiplier layer2. Instead of dynamically altering base item definitions, it manipulates vendor buy/sell multipliers based on variables such as city tier (capital versus village), local hold location, player faction standing, Thane status, property ownership, and merchant race5. While *Trade and Barter* provides the illusion of local market conditions, its underlying state model remains static: selling a high volume of a specific good does not alter that good's market value over time8.  
To address regional commodity imbalance, *Trade Routes \- Regional Economy* by taleden established a geographic supply-and-demand matrix1. *Trade Routes* assigns origin data to primary trade goods—such as timber, ores, food, and regional alcohol1. The mod calculates price and availability based on the distance between the local merchant's hold and the commodity's source node1. Furthermore, it monitors specific world-state quest flags (such as clearing an overrun mine) to dynamically recalculate regional resource availability1. However, *Trade Routes* operates exclusively on raw crafting materials and consumables; it does not extend dynamic pricing to weapons, armor, or enchanted items12.  
True dynamic price response driven by player transaction volume was achieved in mods such as *Supply and Demand* by sasnikol5. This mod implements a cumulative saturation model: when the player sells large quantities of a specific item class (e.g., soul gems or ore) to a merchant, a Papyrus script updates an internal counter that depresses the purchase price for subsequent sales7. Conversely, purchasing out a merchant’s stock drives prices up7.  
The state of the art in native dynamic pricing evolved with the release of the *Dynamic Pricing Framework (DPF)* by shazdeh2 and its primary implementation, *The Gilded Road*1. Modern frameworks bypass Papyrus-driven record overwrites entirely6. Utilizing SKSE plugins alongside Keyword Item Distributor (KID) and Container Item Distributor (CID), *The Gilded Road* injects dynamic price modifiers at runtime based on regional specialization without modifying base .esp records or polling heavy script loops6.

| Mod Name | Price Model | Cumulative Sales Tracking | Primary Mechanism | Compatibility Posture | Technical Limits Hit |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Trade and Barter** \[cite: 5, 7\] | Multiplier adjustments (location, standing, speech)2 | No8 | Papyrus MCM setup, global variable overrides8 | High (soft overrides via MCM)11 | Static base values; cannot react to market saturation8. |
| **Trade Routes \- Regional Economy** \[cite: 1, 3, 5\] | Regional supply/demand based on geography & quests1 | No (node-based, not volume-based)1 | Cell-load Papyrus scripts, vendor inventory injection3 | Moderate (requires patches for custom items/nodes)2 | High Papyrus latency on cell reload; restricted to raw goods9. |
| **Supply and Demand** \[cite: 7, 13\] | Transaction-volume saturation pricing7 | Yes (tracks cumulative buys/sells per item category)7 | Event-driven Papyrus scripts on trade containers7 | Moderate (can stack multiplicatively with other mods)5 | Script queue delays when trading items in bulk8. |
| **Dynamic Pricing Framework / The Gilded Road** \[cite: 1, 5, 6\] | Geographic & vendor specialization multipliers6 | Partial (framework supports dynamic scaling)5 | SKSE runtime injection via KID & CID6 | High (zero vanilla record modifications)5 | Native barter engine hooks restrict fine-grained formula replacement3. |
| **Evolving Value Economy (SkyRem \- EVE)** \[cite: 5, 8, 16\] | Macro-environmental (seasons, Civil War state)8 | No8 | Global script monitoring season/quest state8 | High (designed as a complementary layer)8 | Coarse-grained updates; lacks item-level volume tracking8. |

### **2\. Merchant Simulation, Persistent Wealth, and Item Flow**

Vanilla Skyrim merchants are static transaction interfaces tied to hidden vendor chests in cell storage8. Merchants do not hold real wealth; their gold re-populates via hardcoded engine reset timers (typically every 48 hours in game time)11. Several mod lineages attempted to replace this illusion with physical item flow and persistent wealth7.  
*Faction Economy* established a dynamic item distribution loop7. When a player sells gear—such as high-tier weapons, enchanted items, or armor—to a general merchant, the mod intercepts the transaction7. Rather than allowing the item to vanish upon vendor chest restock, *Faction Economy* injects the sold items directly into the leveled lists of active world factions (e.g., Bandits, Vampires, Dawnguard, and Thalmor)7. If a player sells a collection of enchanted weapons to Belethor in Whiterun, those exact item FormIDs can appear equipped on bandit leaders or enemy mages in surrounding holds days later7.  
Other mods attempted to alter merchant agency5. *NPCs Learn to Barter* applies Speechcraft perks and skill trees to merchant NPCs, making high-level vendors progressively harder to trade with5. *Dynamic Merchants* attempted to simulate vendor wealth progression by tracking player transactions and altering cell-reload inventory distributions based on accumulated profit9.  
Multiple modding practitioners formulated designs to track persistent actor wealth and buyer-matching mechanics8. The standard structural blueprint involves tagging non-merchant NPCs with income tiers (e.g., lower, middle, upper class) and evaluating sold vendor items against nearby NPC budgets during cell reset routines8. Items purchased by NPCs would transfer directly to their personal actor inventories, while unbought items would filter into regional bandit storage chests8. However, implementing these buyer-matching pipelines natively in Papyrus proved unviable due to the computational cost of processing thousands of potential buyer arrays8.

### **3\. Production Chains, Regional Macro-Economies, and Gold Sinks**

A persistent structural failure of Skyrim's economy is hyper-inflation18. Dungeon plundering generates high-value loot with zero production costs, rapidly overwhelming the game's sparse financial sinks2. Mod authors have addressed this through two distinct strategies: business ownership simulations and comprehensive financial sink frameworks4.  
Mods such as *Windstad Mine*, *Heljarchen Farm*, *LC\_Build Your Noble House*, and *RE \- Real Estate* allow players to buy, build, and operate production facilities4. These mods utilize daily script loops to calculate income and resource extraction20. However, because these production outputs dump generated gold or raw materials directly into player chests without deducting wealth from a finite regional treasury, they frequently worsen inflation rather than mitigating it4.  
To balance this wealth creation, economy overhauls introduce structural gold sinks and loot distribution constraints11:

* **Loot Depletion Overhauls**: *Scarcity*, *MorrowLoot Ultimate*, and *Open World Loot (OWL)* strip high-tier gear (Ebony, Glass, Daedric) from generic leveled lists, restricting dungeon loot to low-value common goods11.  
* **Alternative Currencies**: *Coins of Interesting Nature (C.O.I.N.)* replaces modern Septims found in ancient Nordic ruins and Dwemer ruins with non-viable historical currencies (Haralds, Dumacs)15. Players must pay conversion fees at regional bank institutions to convert ancient coins into spendable Septims15.  
* **Service Sinks and Upkeep Costs**: Frameworks such as *Honed Metal* require players to pay blacksmiths and court wizards market-rate fees for forging, tempering, and enchanting gear15. This transforms crafting from an infinite money generator into an expensive gold sink15. Taxation systems (*Simple Taxes*, *Taxes of the Nine Holds*) impose daily recurring property, horse, and follower upkeep costs12.

### **4\. Technical Constraints, Engine Limits, and External Architecture Evaluation**

Mod developers attempting in-engine economic simulations inevitably encounter four hard technical boundaries built into the Creation Engine architecture3.

#### **The 16-Bit Signed Integer Vendor Gold Bug**

In the unpatched Creation Engine, merchant gold is stored and processed as a 16-bit signed integer (int16\_t)10. The engine's maximum positive vendor gold value is ![][image5] (![][image6])10. If a mod or console command raises a merchant’s gold count above 32,767 (e.g., setting vendor gold to 35,000), the value overflows internally into negative numbers10.  
When the player attempts to sell an item to a vendor whose gold exceeds 32,767, the barter validation routine fails: the player receives zero gold for the transaction, while the merchant keeps the sold item10. Fixing this bug required low-level memory patching via SKSE C++ plugins (*Barter Limit Fix*, *Sales Overflow Solved*) to hook the engine's barter calculation function and broaden the variable storage register10.

#### **Papyrus Virtual Machine Architecture and Stack Latency**

Papyrus is an interpreted, event-driven scripting language designed for lightweight quest handling, not real-time macro-economic simulation3. It operates under strict execution quotas per frame (defaulting to 1.2ms of execution time per frame).  
When an economy mod attaches script listeners (such as OnItemAdded or OnContainerChanged) to vendor chests, every transaction triggers a thread8. If a player sells multiple items simultaneously, or if a global script polls dozens of merchant chests across Skyrim to recalculate supply/demand matrices, the Papyrus execution queue backs up3. Unfinished script instances accumulate in the save file, resulting in script lag, delayed menu responses, stack dumps, and permanent save game bloat3.

#### **Static FormID Base Records and Overwrite Conflicts**

In the Skyrim database schema, base item prices are hardcoded into individual record definitions (WEAP, ARMO, INGR, ALCH)3. Skyrim’s plugin load order follows a strict last-load-wins record inheritance model3.  
If an economy mod alters the base price of an Iron Dagger in its .esp file, it completely overwrites any other mod altering that same record (such as weapon stat rebalancers, animation assignment mods, or mesh replacement mods)3. Patching these conflicts historically required complex external SkyProc or xEdit automated patchers3. Modern frameworks bypass this by manipulating runtime engine hooks rather than record database definitions5.

#### **Micro-Economic Execution Outside the Native Engine**

The fidelity ceiling achieved by in-engine mods is limited to static global multipliers and local item category counters5. An external-process simulation service—operating as an independent executable communicating with Skyrim via an SKSE C++ memory bridge—completely circumvents these engine walls:

* **Papyrus Bypass**: Heavy computations (such as solving dynamic differential equations for supply/demand matrix equilibrium, tracking thousands of individual NPC transaction histories, and simulating cross-province trade caravans) occur in native C++ or Rust code outside TESV.exe. The Papyrus Virtual Machine is completely untouched.  
* **Save Bloat Elimination**: Global state arrays, provenance metadata, and transaction registers reside in an external database or memory cache. The .ess save file remains lean, storing only an ID pointer.  
* **Overcoming Native Limits**: Dynamic pricing is injected into the engine at the moment of menu opening via raw C++ memory writes to barter hooks, bypassing engine record edits and native variable constraints6.

## **Part B — The Community Record and Practitioner Discourse**

### **1\. Wishlist Perennials and Community Demands**

Community discussions across r/skyrimmods, Nexus Forums, and modding communities reveal persistent dissatisfaction with Skyrim's static economic architecture1. Over a twelve-year period, community "mod idea" and "wishlist" posts recur along specific tropes1.

#### **The Iron Dagger and Smithing Spam Meme**

The most ubiquitous community complaint centers on the lack of market saturation physics1. The classic formulation asks why a player can forge fifty enchanted Iron Daggers of Paralysis, sell them all to Belethor in Whiterun, and face zero economic repercussions1.  
Players repeatedly express a desire for two specific mechanical reactions:

> 1. **Price-Depressive Saturation**: Selling fifty daggers should immediately cause local vendors to refuse further daggers or drop their purchase value to zero septims due to local market oversupply2.  
> 2. **World-State Diffusion**: Sold crafted gear should physically filter into the world, causing local guards, city citizens, or regional bandits to spawn wielding those exact fifty enchanted daggers in subsequent encounters1.

#### **The Living Economy and Supply Node Model**

Wishlists frequently request a macroeconomic simulation where resource extraction nodes directly dictate item availability and city wealth1. Highly upvoted posts ask for systems where razed farmlands in Whiterun cause grain prices in Solitude to skyrocket, or where capturing an iron mine in Markarth starves the Imperial Legion of military supplies, altering weapon prices across the province1.  
Users consistently demand a game world where money is a finite resource, merchants trade among themselves, and NPC caravans physically move goods across the map where they can be raided by bandits or protected by the player4.

### **2\. Practitioner Explanations and Technical Proofs**

When community members post ambitious economic wishlists, mod authors and engine-knowledgeable practitioners intervene to explain the technical walls that prevent native implementation3.

#### **Finite Macro-Economies versus Infinite Leveled-List Spawning**

Mod authors emphasize that Skyrim’s game loop is inherently non-economic4. Practitioner comments point out that true economic simulation requires a closed loop where gold and resources are finite4.  
In Skyrim, leveled lists infinitely generate wealth out of thin air every time a cave or dungeon resets4. Because enemies and chests continually spawn pristine steel weapons, gold coins, and gems, player supply is functionally infinite4. Modders explain that without replacing the entire game's loot, encounter, and spawning systems, dynamic pricing alone cannot create a true economy because the supply side is unconstrained by real resource limits4.

#### **Papyrus Array Limits and Runtime Memory Overhead**

When users ask why a mod cannot track the transaction history of every item FormID for every merchant in Skyrim, practitioners cite engine data structure limits3. In Papyrus, array allocations were historically capped at 128 entries (later expanded to 8,192 in SSE, but still fundamentally restricted in memory footprint)8.  
Running complex dynamic tables—such as evaluating every item sold against a global array of potential buyers and dynamic price indexes—requires constant iteration over heavy data structures8. Practitioners note that performing these checks inside Papyrus thread queues leads to frame drops, delayed menu interactions, and thread starvation3.

#### **Base Record Conflicts and Patcher Friction**

Engine modders explain that changing item base prices requires either modifying base record definitions (FormIDs) or hooking the native C++ barter functions3. Editing base records breaks compatibility with every other mod touching those items unless users run automated external patchers (such as SkyProc, zEdit, or xEdit scripts)3.  
Until the modern emergence of SKSE runtime injection tools like KID, CID, and DPF, modders were forced to choose between breaking mod compatibility or settling for coarse global variable multipliers (fBarterMax/fBarterMin)3.

### **3\. Reception Evidence and Comparative Game Benchmarks**

The gap between what economy mods promise on their mod pages and how players evaluate them in discussion threads highlights a persistent pattern of immersion breakdown2.

#### **Community Evaluation of Existing Overhauls**

* **Trade and Barter**: Universally praised as an essential utility mod for establishing regional flavor and tightening price dials2. However, experienced players note that after the early game (levels 1–15), its pricing adjustments fail to prevent hyper-accumulation2. Once the player reaches mid-level dungeon crawling, the sheer volume of high-tier loot renders regional price markups irrelevant2.  
* **Trade Routes**: Praised for its geographic logic and trade roleplay potential1. However, it is frequently criticized for its narrow focus on raw goods, its heavy script overhead on cell load during long play sessions, and its inability to alter the value of weapons, armor, or player-crafted items9.  
* **Artificial Difficulty versus Economic Simulation**: A recurring complaint in economy mod reception threads is that most mods equate a better economy with arbitrarily expensive goods and impoverished merchants2. Players express frustration when general merchants are stripped of all gold, turning trading into a tedious exercise of traveling from town to town to sell basic loot2. Users continuously seek responsiveness rather than mere artificial scarcity2.

#### **Comparative Game Benchmarks: Mount & Blade, Kenshi, and X4**

In economy discussion threads, Skyrim’s modded economy is frequently compared unfavorably to games with purpose-built economic engines2:

* **Mount & Blade: Bannerlord**: Frequently cited as the ideal model for regional trade mechanics8. Players admire how town prosperity, village production nodes, raw material tariffs, and physical trade caravans dynamically dictate item prices across Calradia8.  
* **Kenshi**: Highlighted for its finite local shop funds, regional supply scarcity, and the ability of player-built outposts to alter regional trade dynamics29.  
* **X4: Foundations**: Cited as the gold standard of physical supply-chain modeling4. Players point out that in *X4*, every space station and weapon requires real raw materials to build, and trade ships physically transport goods between factories4. Destroying a transport ship causes genuine resource shortages in nearby shipyards4.

When modders analyze whether these systems could be ported into Skyrim natively, the consensus among engine practitioners is that Skyrim's engine cannot support such architectures4. The Creation Engine's actor limits, pathfinding constraints, lack of background simulation threads, and non-finite spawning models prevent the creation of real production-chain logistics inside the engine executable4.

## **Conclusion and Strategic Synthesis**

The history of Skyrim economy modding demonstrates a clear architectural progression3. In-engine modding has reached its structural ceiling3. While SKSE frameworks such as DPF, KID, and CID have eliminated the old limitations of static record overwrites, in-engine mods remain fundamentally constrained by the synchronous execution environment of the Papyrus VM and the game's infinite loot-spawning loops3.  
An external-process architecture—wherein an independent simulation service computes macro-economic state off-thread and injects results into Skyrim via a native SKSE C++ memory plugin—bypasses every major technical boundary documented in community practitioner discourse:

> 1. **Resolution of Script Bottlenecks**: By shifting dynamic pricing algorithms, transaction history registers, and supply/demand matrices to an external process, Papyrus execution queues are completely freed3. Thread starvation, menu delay, and save game bloat are entirely eliminated3.  
> 2. **Infinite Data Scale**: Provenance metadata (e.g., tracking who forged an item, who bought it, and how many times it was traded) can be stored in external high-performance databases, completely unconstrained by Papyrus array boundaries or .ess save file size limits3.  
> 3. **Bypassing Native Bit-Width Constraints**: External C++ injection hooks can manipulate barter calculations directly in game memory during container activation, dynamically overcoming native integer overflow limits without risking save file corruption6.  
> 4. **Fulfilling the Product Thesis**: The community's decade-long demand—a reactive economy where selling fifty daggers depresses local prices, alters regional supply chains, and physically equips sold goods onto local world factions—is computationally impossible inside Papyrus1. An external service coupled with SKSE runtime memory injection provides the exact system architecture required to cross this technical ceiling.

#### **Works cited**

> 1. Dynamic economy : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/y4uzd4/dynamic\_economy/](https://www.reddit.com/r/skyrimmods/comments/y4uzd4/dynamic_economy/)  
> 2. Is there someone who uses Economy Mods? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/14as94h/is\_there\_someone\_who\_uses\_economy\_mods/](https://www.reddit.com/r/skyrimmods/comments/14as94h/is_there_someone_who_uses_economy_mods/)  
> 3. Skyrim Needs A Proper Price Overhaul\! Vanilla Prices Are Nonsense\! \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/5fiz8u/skyrim\_needs\_a\_proper\_price\_overhaul\_vanilla/](https://www.reddit.com/r/skyrimmods/comments/5fiz8u/skyrim_needs_a_proper_price_overhaul_vanilla/)  
> 4. LF sugestions to turn Skyrim into factory building game like X4 from Egosoft : r/skyrimmods, [https://www.reddit.com/r/skyrimmods/comments/1l0sth1/lf\_sugestions\_to\_turn\_skyrim\_into\_factory/](https://www.reddit.com/r/skyrimmods/comments/1l0sth1/lf_sugestions_to_turn_skyrim_into_factory/)  
> 5. New Economic Framework: Dynamic Pricing Framework : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1pwbosn/new\_economic\_framework\_dynamic\_pricing\_framework/](https://www.reddit.com/r/skyrimmods/comments/1pwbosn/new_economic_framework_dynamic_pricing_framework/)  
> 6. \[RELEASE\] Stop looting urns. Start playing like a Tycoon. "The Gilded Road" – True Economy Overhaul is out now. : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1qazzdq/release\_stop\_looting\_urns\_start\_playing\_like\_a/](https://www.reddit.com/r/skyrimmods/comments/1qazzdq/release_stop_looting_urns_start_playing_like_a/)  
> 7. Best mods for... merchants\! : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/mtapui/best\_mods\_for\_merchants/](https://www.reddit.com/r/skyrimmods/comments/mtapui/best_mods_for_merchants/)  
> 8. Is there a mod that simulates a more complex economy, like if I sell 50 daggers of paralysis and absorb health I might run into NPC's wielding them a few days later? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/ev7wkz/is\_there\_a\_mod\_that\_simulates\_a\_more\_complex/](https://www.reddit.com/r/skyrimmods/comments/ev7wkz/is_there_a_mod_that_simulates_a_more_complex/)  
> 9. \[HELP\] Immersive Economy Mods : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/2q4j0c/help\_immersive\_economy\_mods/](https://www.reddit.com/r/skyrimmods/comments/2q4j0c/help_immersive_economy_mods/)  
> 10. Mod release: 32767 max vendor gold fix : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/9dqpzc/mod\_release\_32767\_max\_vendor\_gold\_fix/](https://www.reddit.com/r/skyrimmods/comments/9dqpzc/mod_release_32767_max_vendor_gold_fix/)  
> 11. Too Much Money? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/76rl27/too\_much\_money/](https://www.reddit.com/r/skyrimmods/comments/76rl27/too_much_money/)  
> 12. Fixing Skyrims Economy : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/80l00e/fixing\_skyrims\_economy/](https://www.reddit.com/r/skyrimmods/comments/80l00e/fixing_skyrims_economy/)  
> 13. Looking for a mod that will make buying and selling items give me less gold : r/skyrimmods, [https://www.reddit.com/r/skyrimmods/comments/pkw3k0/looking\_for\_a\_mod\_that\_will\_make\_buying\_and/](https://www.reddit.com/r/skyrimmods/comments/pkw3k0/looking_for_a_mod_that_will_make_buying_and/)  
> 14. Is there a mega-merchant mod that will buy all your stuff? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/yo3q2m/is\_there\_a\_megamerchant\_mod\_that\_will\_buy\_all/](https://www.reddit.com/r/skyrimmods/comments/yo3q2m/is_there_a_megamerchant_mod_that_will_buy_all/)  
> 15. What have you done to balance your game's economy? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1v7g20w/what\_have\_you\_done\_to\_balance\_your\_games\_economy/](https://www.reddit.com/r/skyrimmods/comments/1v7g20w/what_have_you_done_to_balance_your_games_economy/)  
> 16. Economy Difficulty and Synergies : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/13nz0d9/economy\_difficulty\_and\_synergies/](https://www.reddit.com/r/skyrimmods/comments/13nz0d9/economy_difficulty_and_synergies/)  
> 17. Does anyone know a mod that makes merchants more dynamic? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/8kjt0s/does\_anyone\_know\_a\_mod\_that\_makes\_merchants\_more/](https://www.reddit.com/r/skyrimmods/comments/8kjt0s/does_anyone_know_a_mod_that_makes_merchants_more/)  
> 18. How do you guys balance economy? (discussion about mods and settings) \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/52l7k4/how\_do\_you\_guys\_balance\_economy\_discussion\_about/](https://www.reddit.com/r/skyrimmods/comments/52l7k4/how_do_you_guys_balance_economy_discussion_about/)  
> 19. Ways to make "Looting Dead Enemies" not the primary source of income? : r/skyrimmods, [https://www.reddit.com/r/skyrimmods/comments/16a1gim/ways\_to\_make\_looting\_dead\_enemies\_not\_the\_primary/](https://www.reddit.com/r/skyrimmods/comments/16a1gim/ways_to_make_looting_dead_enemies_not_the_primary/)  
> 20. Player Home that's Upgradeable and a Gold Sink? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/ra6qxx/player\_home\_thats\_upgradeable\_and\_a\_gold\_sink/](https://www.reddit.com/r/skyrimmods/comments/ra6qxx/player_home_thats_upgradeable_and_a_gold_sink/)  
> 21. Mod recommendations for a "peasant to thane/knight" playthrough? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/1r0l8v4/mod\_recommendations\_for\_a\_peasant\_to\_thaneknight/](https://www.reddit.com/r/skyrimmods/comments/1r0l8v4/mod_recommendations_for_a_peasant_to_thaneknight/)  
> 22. Barter Fix : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/ense06/barter\_fix/](https://www.reddit.com/r/skyrimmods/comments/ense06/barter_fix/)  
> 23. Mod release \- Sales Overflow Solved : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/jgdasm/mod\_release\_sales\_overflow\_solved/](https://www.reddit.com/r/skyrimmods/comments/jgdasm/mod_release_sales_overflow_solved/)  
> 24. Is there a way to give traders more money? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/tz3fy3/is\_there\_a\_way\_to\_give\_traders\_more\_money/](https://www.reddit.com/r/skyrimmods/comments/tz3fy3/is_there_a_way_to_give_traders_more_money/)  
> 25. \[Suggestion\] Skyrim Dynamic Economy Overhaul : r/skyrimmods, [https://www.reddit.com/r/skyrimmods/comments/b8vw6p/suggestion\_skyrim\_dynamic\_economy\_overhaul/](https://www.reddit.com/r/skyrimmods/comments/b8vw6p/suggestion_skyrim_dynamic_economy_overhaul/)  
> 26. \[PC\] \[Request\] Dynamic Economy Mod : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/7c6ucq/pc\_request\_dynamic\_economy\_mod/](https://www.reddit.com/r/skyrimmods/comments/7c6ucq/pc_request_dynamic_economy_mod/)  
> 27. \[Request\] Immersive Economy : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/2vqbpy/request\_immersive\_economy/](https://www.reddit.com/r/skyrimmods/comments/2vqbpy/request_immersive_economy/)  
> 28. Mount & Blade: Skyrim Edition \- Is it possible? : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/3iu5af/mount\_blade\_skyrim\_edition\_is\_it\_possible/](https://www.reddit.com/r/skyrimmods/comments/3iu5af/mount_blade_skyrim_edition_is_it_possible/)  
> 29. Stock Market of Skyrim has been released : r/skyrimmods \- Reddit, [https://www.reddit.com/r/skyrimmods/comments/mhubho/stock\_market\_of\_skyrim\_has\_been\_released/](https://www.reddit.com/r/skyrimmods/comments/mhubho/stock_market_of_skyrim_has_been_released/)  
> 30. Whats a mod that after all these years your still waiting to be created ? : r/skyrimmods, [https://www.reddit.com/r/skyrimmods/comments/14wu4wk/whats\_a\_mod\_that\_after\_all\_these\_years\_your\_still/](https://www.reddit.com/r/skyrimmods/comments/14wu4wk/whats_a_mod_that_after_all_these_years_your_still/)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAaCAYAAADFTB7LAAABZklEQVR4Xu2WTytFURTFF4nIhJGUqQkGkonkT/kABspAKSZKvgAlc0MDRebmBibkGxgqxRRFmSoT9nb27e27nHMn3rtX3F+t3t5r3/fO6p7z7ntAzT/hIyKG57P5cetZRlh4jweOC9EMm2UxgBDwnAeO2J0tldT2Kim/VFIBu0SbbFZBKmDMq4QHfA/zKFoirzL2EQLOW98m2m6Mv0jd5VJYRFh8x/pXN/NUFlDRxW9Et6I1mikH+AUBi7ZRfQ05R77SyQYxzoYxxUYRReEUnR1a/UJ+rFaOXP3m6qL3JNELn9h0+A+6FHWLNpB/TvJi2o9YPeS8U6s7RNNW/4he0YnrsyA+0Dr1igbIdiY7BnxNUxhF47z0IB7wXnQlOrNen6OrVi+Ihq1uSUDl2l79WToWtSN8cZ4R/hGt2Owd4RgMIh/qTrRr9RbCz2lT6BNNsimMIWylMuEHCItrSKYfcb+mpubP8Akt9VZzBAwyTAAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAaCAYAAACHD21cAAAAlElEQVR4XmNgGGxAB4j50QUJgf9oGCaGEzxnwK4A2QCsAJckSPwZuiAMNDLg1vgOiJXQBWFgIQNEoy26BBBEoQsgA1EGzEBpQFaAD6BrJBgo2EARA5kaQaCaAaJRBV0CBvajCyABvDbeRReAggYGPBo7GSCS8egSDBBxUGhjBSBJdygNSgShQNwG5YshqRsFo4BCAADlUysq9K81gAAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAaCAYAAAAue6XIAAABtElEQVR4Xu2WzytEURTHD+VHQlmTYmVlIcqGppSNnUTZsFBWNrKQHcmCYm1nIRspkiyoyT+gRBKirGRBKFbifLvnNmeON4Zy30jvU9/OOd9zZ+55b97cGaKEhEjejfLx0/W/zhp9b/NncmsubSNOMMC5xFwcSsSaft2IGwwwIzEXFaxN+npNcPpYe6wuyj3IvcTvPCpBweblKu9QPXCscvQHVB07+k4hn1I1mJU4TgW+qyCtcgxzoepHlUc9Ai/i9Rg/GN0qf6PMQPBHVC9qWBDlBWHB1CuU2Xxa+QD+mfFAbMPajYbEGzU+gD9svFrWPKuR1aT8Glapqi111sjHIH0eFsDD0Jp18S04KZYkL2PNsVJS6/U632Edsbalbic3SyT1lHn+vPw3Hug3vpVa60r17QU8sV5ZRabn80lVt0m+KzEo1ZQ90BhrUfI71qrkOMOXJfdEXUhQmil7IxxjHvgtkuNTayD3S+nZklhJMQ0L/EYnrF7ln5K7yxOsA1YJa1/1HyTi9dfKD04rq9iaTBW5Zxd06gY5P0Vu2IL+g8uH/zRweqR14y9yw9ogd9IkJPwrPgD5aXYMnm1skQAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAaCAYAAAAue6XIAAABk0lEQVR4Xu2WwSsFURTGj2ywkZSVZG0hJUtZKGsLUSxYqLeiWNqRnZX8A1Yikb2F/8DGRshKkgXJTon7mXPffHOaO29oZmzmV6dzznfPe3Pe7dy5T6SmJpUvY634bX3hHEi+h79LVHNnF6oEDdyoD3GpHjWzvFA1aGBLfYguZ2eSXVM6M87OnU1KuJEX9XlGpVTw8A6Kx2kNXFGM9TnKK4d3CvEG5WBb/br8866CC4rRzC3lbxQXMQI4mPiOJ833ND9sVrRgiuJPiRuCvkxrRTQLRp2tUr7mbITyIDsm35e4oU3SAfRro/2FV5Pn3gBbuKhaw+gA+pIViWErKBMmt8+0eSrzkl4IDU0zx6qnwfoDxaz7GCPAOkYg9L0/DEhUwOZPPOAP4yDY2ntaB9CGNO5T/yjJK3lF/amzZ9IxEkeUl86uxD+kTTXEPc2KGOg8Lpm7WjT+FQRwE/qdDTXh9WmT96svlQ/1g5Js8ESiOQe4xns15pHx+QLlpTMm8XXNdDrrNlq7JN+p+HOEM1RTU1OTwTezPHBAhouKmQAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD0AAAAZCAYAAACCXybJAAACLklEQVR4Xu2Wu0sdURDGR6OC8YEiopYKFtoJChYWgo8iKNhKmjRqJfYK3j/AQsTKxsZCBC0sFEErBQkkNoJKmhQSq4SAiqRIoTOeHe/xu7Oviza6P/jgzjdz5uzZvXvOEmVkvCu6WWVoAk2sUjRTsIdGAjrInrOYXk/cs0aC35+DeDKffkQmEK+K9ZVczdazinhqyY2LkiKLlHie9YE1APm4XnX50kLGWP9Y1Z6HF9DHuvZiYZtczQT4UegNDZP/NCX+AbF/TXG9IlkmV7TkeThQY1wg1sVxwmpAk7mAeIYK+66x5rw4rBeOC6UNYlzMfhDjJFgXh/RBvrD+gJekb1gvXEsirih+QqGSXN0vTKTkBuIScn13Ai2wfrP++0UGs1TYKxa9u0kWLPwlV2vtqklZYbWC106ur+wzspco4t16MSJ57JUKafATTY9zSn5zwqghu0cn2Tf/0PCUsF6psCZV9O/XgomUhL1G2n8X/M3At95Z6XWGZlp00XI2IuKXo1kEUTfWWvR64PeCL4ifQzMKa3L1Bg0fsbwkWPMqsiHhk9MTBOki5w9jIgprcss7YvWDFll3WsBskBtX4XlhWHMo41SYk3nQE1bJ+T2YiELeERk0zWpmfQ/iT16NXqClnFd3GXjWGYpELVrQ/EdyHyX6Gzkml5NdPxWN5C5UjolvkCuGUzQM5C9svZ8+U+QWdIAJj3oq4nx+DfDL7c0j38TviiHWKJoZGRkZGS/IA9NJvVnBagj9AAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD0AAAAZCAYAAACCXybJAAABUUlEQVR4Xu2VMUtCURiGD0Tg2BA0uzgGFYpuzk5NQW39hQajkBD8DxH1B9xcdOoHtDWE+A+aGgTDloj6XrwXP9/OtWvhlS/PAy/c83xePK/cc3Vuce4ke+RGklPJseSdZqZ5lLxKPiX7NIOLs0mzfwGKHZAb09ocXIhJKn0kOSG/KnIskkCZWhScS6wrM5+Y4Cv9oa4xz5qS5MxN912fHfvpsnDTM8rAFVkqMG+xXDJPkoEk7xYo7SsYuw2PL6v1Q+RicN1T66zB95+z9OEr/Ry5HfJw+rG/lXTUGvOCWmdN6tI++IdoK8ezhuRe8qbcqvhzaf2CssKvS+PGa5ZGwN4vWP7E0H0/38uAj8q8bEf3pAGfv2Q5jy3JC0tjoDTeMam4kfTJ7dLaAih9xTIJPNZVlUM3+dO3Bko3WfrgM6RjATylvG9L+w8EAoFAILDOfAFeC2sqYC3cXwAAAABJRU5ErkJggg==>