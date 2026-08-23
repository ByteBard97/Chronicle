# Skyrim SE/AE Economy-Simulation Mods: The Fidelity Ceiling and the Community Record

## TL;DR
- **No shipped Skyrim mod simulates a true living economy; the ceiling is player-centric price feedback (your own cumulative buying/selling nudges prices) plus static regional price tables — nothing models autonomous merchant wealth, production chains, or a world that trades without you.** The dagger-dump scenario is addressed only crudely: a handful of mods depress prices as you sell duplicates, but this is a per-keyword saturation counter, not a genuine market.
- **The walls in-engine mods hit are real but architecture-specific**: the 48-hour merchant-chest respawn, the merchant-chest-only-populates-via-barter-menu problem, the hard **32,767** vendor-gold cap (a signed 16-bit integer bug), the `fBarterBuyMin` price floor, and Papyrus performance/save-bloat costs. An external simulation that computes state out-of-process and injects results via SKSE bypasses most of the *computation* walls, but must still write results back through the same narrow engine hooks (barter price calc, vendor gold, leveled inventory) that constrain everyone.
- **The community record is unambiguous and long-running**: "why is the economy so static / make it living" is a perennial request dating to at least 2012, the merchant-gold cap is the single most-cited immersion complaint, and reception threads show even the best economy overhauls still "feel static" because they change *numbers*, not *behavior*. Mount & Blade and Kenshi are the repeatedly-cited bars.

---

## Key Findings

1. **The best-shipped fidelity is "reactive pricing centered on the player," not a simulated market.** Mods like *Supply and Demand*, *Reactive Markets*, and *The Gilded Road* make prices move in response to the player's own transactions and to regional tables — but no merchant has autonomous wealth, no goods flow between towns without the player carrying them, and production sources (mines, mills) do not feed markets dynamically.

2. **Exactly the dagger-dump scenario is handled by a small number of mods, all via per-item-keyword saturation counters** — never via a real market. *Reactive Markets* (2026) and *Supply and Demand* both track cumulative player buy/sell per item type and shift the price, with hard caps.

3. **"Merchant simulation" is almost entirely faked.** Caravan/trade-route mods either move NPCs cosmetically or adjust static regional price tables; none maintain persistent, self-updating merchant balance sheets or inter-merchant trade.

4. **The engine walls are well-documented and precise**, and a mod author's own scripting thread demonstrates the merchant-chest access problem firsthand.

5. **An external-process architecture is viable and has direct precedent** in the AI-follower modding scene (Mantella, Herika/CHIM), multiplayer (Skyrim Together Reborn), and Twitch integration (Skyrim CrowdControl) — all of which run code outside the game and inject results back via SKSE plugins + Papyrus events. No one has yet applied this pattern to the *economy*, which is the user's opportunity.

---

## Details

### Part A — The Mod Survey

#### A1. Supply/demand and price-response mods

The lineage runs from **kryptopyr's *Trade and Barter*** (the genre anchor, Oldrim 2013, SE port 2019, still updated January 2025) through a family of price-response mods. It is important to separate what each actually implements:

- **Trade and Barter (kryptopyr)** — *not* a supply/demand model. It exposes "many new variables to adjust the trade and barter rates in Skyrim, including merchant gold, trading perks, inventory respawn rates." Prices vary by **static modifiers**: faction rank/Thane status, friendship (Friend/Ally/Lover), race, and city size (each of the five major cities has a tuned multiplier). It is a richer set of *static* multipliers layered onto the vanilla formula, driven through the PerkEntryPoint "Mod Buy/Sell Prices" method. This is the most-installed economy mod and the community default.

- **Supply and Demand (mod 32365 SE / 101587 LE)** — the clearest player-centric feedback model. Per the mod page: "This mod simulates a challenging supply-and-demand based economy, centered around the player. Each time you buy or sell something, the price changes by 2% for each item. Buy ten ales, and they'll get 20% more expensive. Sell five pelts, and pelts of that kind will become worth 10% less." Its own bulk example maps directly onto the dagger scenario: sell ~20 identical items in a transaction and "the price will drop 40% on future sales." Duplicate items you buy become more expensive; even stolen goods appreciate; it reaches most of the game via keywords. This is *exactly* the dagger-dump depressor — but it is a per-keyword counter centered on the player, not a market.

- **Reactive Markets (mod 186295, shazdeh2, uploaded 26 July 2026)** — the most recent and most precisely the requested mechanic. "What you sell and buy affects future prices." Per the mod page: "Each individual item sold/bought, decreases/increases prices by 0.01%. Price drops are maxed at half item's price, and raised prices are maxed at twice their original." Calculated separately per vanilla `VendorItem*` keyword. Second layer: "clearing bandit hideouts (or forsworn camps in the case of the Reach) gives you a +1% positive buff for vendors in that hold" — a rare example of world-state (not just trades) feeding price. Runtime injection, no vanilla record edits, install/uninstall anytime. (New and lightly endorsed — 34 endorsements at time of research.)

- **The Gilded Road — Economy Overhaul (mod 169528)** — regional/logic-based static pricing, explicitly framed against static vanilla: "a common potato costs the same in the bountiful fields of Whiterun as it does on a distant, icy shore." Built entirely on runtime injection frameworks (Dynamic Pricing Framework, KID, CDIF) with "Zero Vanilla Edits." A "Pack Bulls and Storehouses" logistics addon to "automate trade routes" is described as forthcoming (treat as announced-but-unshipped).

- **Roleplaying in Skyrim — Evolving Economy (mod 149830)** — prices driven by area resources, season, distance from cities, Civil War stage, and faction reputation. Mechanism is a perk-based script that runs once plus a periodic update script on location change / MCM timer. Factor-driven but still fundamentally a lookup of static factors, not a simulation.

- **Trustinlies Price Overhaul, SEO, True Medieval / True Renaissance Economy, Economy Overhaul and Speechcraft Improvements (mod 9542)** — rebalance mods (adjust base values and merchant gold; make Speech matter). *Economy Overhaul and Speechcraft* is notable for production-flavored touches: "Mine owners will sell ores from their mine. Farm owners will sell what they produce."

**On the specific question — does ANY mod track cumulative player sales to depress prices (the dagger-dump)?** Yes: *Supply and Demand* and *Reactive Markets* both do, via per-keyword saturation counters with hard caps. Neither models the *world* absorbing 40 daggers; they model *this vendor category's* price sliding as you flood it. No shipped mod makes forty iron daggers ripple outward into a regional iron-price collapse.

#### A2. Merchant simulation — simulated vs. faked

- **Merchant gold**: every merchant mod (Rich Skyrim Merchants, 12k Merchants, More Gold in Stores, Trade and Barter) simply raises the static gold pool. None simulate merchant wealth accumulating from their own trade. Per UESP, "Gold is reset each time the merchant's inventory is reset or every 48 hours" — so any wealth you inject is wiped on the timer regardless.

- **Trade routes / caravans**: *Trade Routes — Regional Economy (taleden, mod 12358)* is the most sophisticated; it "dynamically adjusts the gold value and merchant supply of food, drinks, animal parts, ingredients, ores, ingots, gems, soul gems and spell tomes according to the actual supply and logical demand of each item in each hold." Its design assigns each item a trade-balance tier (Origin → Supply → Balanced → Demand → Destination) across holds, creating deterministic profitable routes. This is an elegant **static regional table**, not a live market — the "supply and demand" is precomputed geography, not responsive to what merchants actually buy or sell. (Community note: reported broken with SE 1.6+ for inn vendors.)

- **"Merchants physically travel"**: *Real Economy of Skyrim — Trade Caravans (mod 66482)* explicitly attempts "having merchant NPCs travel between locations and add or remove items from stores, based on checking store inventories," with Whiterun as a hub. This is the closest to literal merchant simulation but is small, niche, and limited.

- **Consequence mods**: *Bandit Economy (mod 32197)* / *Faction Economy (mod 101588)* — when you sell a weapon/armor to a general-goods merchant, there's a chance (≈50% for neutral merchants, 100% for fences) the item is passed into bandit/faction leveled lists and later equipped by NPCs. "Sell goods in Solitude, and you will see those weapons actually equipped on Imperials." This is the single best-shipped example of *the world visibly reacting to player economic behavior* — your sold loot re-enters the world on NPCs. It is one-directional (sales → NPC equipment), not a price loop.

#### A3. Production/regional-economy mods and overhaul economy layers

- **Economics of Skyrim (Thomas Kaira, Dark Creations, LE-era)** — the ambitious ancestor: an SKSE-dependent mod with "Regional Values" scripts, explicitly built because "there is some stuff this mod does that, on its own, Papyrus just can't do." Merchant smithing/enchanting services, location-based inventories. Abandoned before SE.

- **Dynamic Economy of Skyrim (mod 42726)** — SkyProc patcher generating craft/temper recipe prices via a formula; changes store inventory by location. Crafting-cost focused, not a market.

- **Production**: no shipped mod makes mines/mills feed markets dynamically. *Economy Overhaul and Speechcraft* has farmers/miners sell what they produce (static assignment). Player-side production business mods (Useable Sawmills, farm/mine player-homes, RP Chopping and Mining) exist but feed the *player's* income, not the market. A UESP forum veteran summarized the gap precisely: on whether clearing bandit camps lowers prices or over-hunting depletes food vendors — "no, I haven't seen it, and doubt it is in… If you mine all the ore you can out of the town mine, the resident miners keep on banging away."

- **Overhaul economy philosophies**:
  - **Requiem** treats the economy as a scarcity/anti-exploit problem, not a simulation. Its design intent (per 3BFTweaks/3Tweaks Requiem docs): "I found it unimmersive that I could 'force' NPCs to buy my limitless quantities of crap and it led to getting too much money too quickly" — so general merchants carry less gold, selling is throttled toward a Fallout-style barter feel, and gear/quest rewards are rebalanced so exploration pays. Requiem also introduced **weighted gold** (carry-weight cost per septim), which the Requiem team's own *Developer Diary #1: The Burdens We Carry* discusses at length, including that a Reddit survey showed players liked the idea but disliked the implementation. This is a rare **primary-source mod-author design writeup** on the balance-vs-simulation tension.
  - **Survival/needs mods** add gold sinks (food, rent, cures) rather than market fidelity.

#### A4. The scholarly/design layer — why deep economy sim is hard

Documented technical constraints (with primary sources):

- **Merchant chest mechanics.** Every merchant's sale inventory lives in a hidden "merchant chest" that "respawns every two days (48 hours) of in-game time, independent of whether the store or cell containing the chest has respawned" (UESP). Critically, a mod author (Qvorvm) trying to script automated selling documented on the Nexus forums that **merchant chests won't populate unless the barter menu has been opened**: "merchant chests are not respawning unless I first (manually) open their barter menu. When I don't, their chest look empty and the only gold the merchant has to buy my stuff is whatever they are currently carrying." `Reset()` on the chest half-worked but re-triggered on opening barter (re-granting the merchant 750g). The eventual working hack was to programmatically open and immediately close the barter menu. This demonstrates that **the sale inventory is only "real" at the moment of a barter transaction** — a fundamental obstacle to simulating merchant stock continuously.

- **Vendor gold cap.** Merchants break at **32,767** gold. Per UESP Skyrim:Merchants: "Trading with vendors becomes unreliable when their gold reserves exceeds 32,767. The game's internal trading mechanism mistakenly treats their gold quantity as a signed 16-bit integer, whose value could be between −32768 and 32767." A veteran (smr1957, Steam, Dec 2022): "Anything over approximately 32,000 gold will cause the merchants to break… you will not receive any gold for it… the gold limit is a game engine one." Investing via the Investor perk can push a merchant past 30k and trigger it. Two SKSE plugins exist purely to fix it: *BarterFix* (kassent, LE) and *Barter Limit Fix (mod 77173, SE)* — "Fixes a bug that can prevent the player from receiving gold when selling to a merchant if the merchant has more than 32,767 gold."

- **Merchant restock corruption.** *Merchant Stock Respawn Fix* documents a state where merchants stop restocking entirely; "the only way to restore the ability… is to basically buy-out their whole inventory, wait 48 hours" — the author speculates it relates to "the sheer number of items that we unload on the merchant." Directly relevant to the dagger-dump: flooding a merchant can corrupt its restock state.

- **Respawn timers.** Merchant chests (48h), ore veins (~30 days, sometimes never), and cells all respawn on independent, coarse schedules that no vanilla mechanism ties to economic activity.

- **Papyrus cost & save bloat.** Papyrus is slow and fragile for per-frame or per-item work; player-dropped/created references persist and bloat saves (UESP). Any per-item, per-merchant, continuously-updating simulation in Papyrus is a performance and stability risk — which is why *Economics of Skyrim* required SKSE and why modern price mods push the work into C++.

- **The barter price formula and its hard floor.** Per UESP: `price factor = 3.3 − 1.3 × min(Speech,100)/100`, from defaults `fBarterMax = 3.3` and `fBarterMin = 2.0`, which "defines a base vendor-selling-range of 200% to 330% of an item's base value, and a vendor-buying-range of 30% to 50%." Skill over 100 has no effect. Critically, `fBarterBuyMin` (default 1.05) hard-caps how low a buy multiplier can go via the PerkEntryPoint method — modders using the classic "Mod Buy/Sell Prices" entry point cannot push prices below ~105% of the floor, a genuine ceiling that only a native-code hook can bypass.

**Other games cited as the bar.** The community repeatedly names **Mount & Blade** (caravans, town prosperity, price arbitrage across towns) and **Kenshi** (production chains, town economies) as what Skyrim lacks; **X4** and RimWorld appear in adjacent discussions. Practitioners generally judge these un-portable because they were architected around a live economy, whereas Skyrim's is a static lookup evaluated only at the barter menu.

#### A5. The fidelity ceiling, the engine walls, and the external-process question

**Ceiling actually achieved:** the world reacting to player economic behavior tops out at (a) player-centric price saturation (*Reactive Markets*, *Supply and Demand*), (b) static regional arbitrage (*Trade Routes*), and (c) sold-loot reappearing on NPCs (*Bandit/Faction Economy*). There is no persistent merchant wealth, no autonomous inter-town trade, and no production→market loop.

**The engine hooks available to SKSE for writing economy state back:**
- **Native price-calc hook.** *Dynamic Prices Framework (mod 144874, JerryYOJ)* is an SKSE/CommonLibSSE DLL that "hooks into the pricing system of traders and provides a way to register a callback to modify the price on each item," exposing a C++ callback `(Actor* trader, InventoryEntryData* objDesc, uint16_t level, GFxValue& updateObj, bool is_buying)` returning a float multiplier, registered via JSON. This can bypass the `fBarterBuyMin` floor because it overrides the price *after* the vanilla calc.
- **Keyword/JSON additive modifier.** *Dynamic Pricing Framework (mod 167487, shazdeh2)* — the one *The Gilded Road* uses — adjusts buy/sell prices by keyword via JSON config, additively, with barter-menu indicators. (Note: two distinctly different mods share near-identical names.)
- **Classic PerkEntryPoint "Mod Buy/Sell Prices"** — what Trade and Barter uses; subject to the `fBarterBuyMin` floor.
- **Vendor gold, leveled-list inventory, and mod events** remain the other write surfaces.

**Has anyone driven Skyrim economy from an external process?** Not the economy specifically — but the *architecture is proven* in adjacent domains, which is the key finding for the user:
- **Mantella (mod 98631, "art from the machine")** runs a Python program *outside* the game that connects speech-to-text + LLM + text-to-speech. Its own description: "Mantella allows you to have natural, real-time conversations with NPCs by leveraging speech-to-text, LLMs, and text-to-speech technologies. NPCs have memories… are aware of in-game events, have vision, and can even perform actions." It originally communicated via file read/write, migrating to HTTP, and injects results back into the live game via **Leidtier's "SKSE HTTP" plugin + SKSE ModEvents** caught by Papyrus (plus mikastamm's Mantella Dialogue SKSE plugin for capture). LLM "actions" are JSON files consumed game-side.
- **Herika / CHIM (mods 89931 / 126330)** run a "Herika Server" (often in a WSL Linux distro) over HTTP; per the mod page, "the plugin is responsible for collecting events from the game… and sending them to the 'Herika Server'… It will also store the AI's responses and send them to the plugin, which will make them available to the follower in-game," using **queues** that play back in-game. CHIM adds function-calling actions ("trade with me, move here").
- **SkyrimNet** is the instructive counter-example: an in-process SKSE DLL that avoids IPC entirely — "Unlike other AI projects that take an external server approach, SkyrimNet uses an in-process design as a DLL" with "Direct Memory Access: Reads game state directly from memory" and a Papyrus API.
- **Skyrim Together Reborn (mod 69993, Tilted Phoques)** runs a dedicated external `STServer.exe` and syncs player/NPC/world state into every client via custom C++ netcode and an inter-plugin messaging API (STRPluginMessagingAPI).
- **General IPC primitives**: **Skyrim CrowdControl (Superxwolf, GitHub)** is the cleanest reference — an external program → **TCP socket → SKSE C++ plugin → Papyrus script executes effects**, with async threads managing the connection and command timeouts. Also available: **Papyrus HTTP Utils (mod 172953)**, **SkyUtilities** (async HTTP → Papyrus events, co-save serialized), **NL_CMD** (console/modevent framework), **PapyrusUtil/JsonUtil** (out-of-game-editable JSON), and **SKSE ModEvents** (`SendModEvent`/`SendAndRelayEvent`) as the dominant, safest return-injection method.

**Implication for the user's design.** An out-of-process simulation sidesteps the Papyrus performance and save-bloat walls entirely (the simulation isn't in Papyrus, and its state need not live in the save). It does *not* sidestep the *write-back* walls: results still enter the game through the barter price hook (best via a native price-calc hook like mod 144874 to escape `fBarterBuyMin`), vendor-gold values (mind the 32,767 cap unless a Barter Limit Fix-style plugin is present), and leveled-list/inventory injection — and the merchant-chest-only-populates-on-barter behavior means price is the reliable lever, while *stock quantity* remains awkward to drive continuously. The proven pattern is: external sim ↔ SKSE plugin (HTTP/TCP/file) → Papyrus via ModEvents / native functions → apply price multipliers and vendor gold at the barter moment.

### Part B — The Community Record

#### (a) Wishlist threads — the perennials

The "why is the economy so static / give us a living economy" request is one of the oldest recurring Skyrim mod ideas:
- **Nexus "dynamic economy for skyrim" (Mod Ideas, July 2012)** — a near-complete spec of the fantasy: per-city warehouses that deplete when looted ("I went to the warehouse and stole the carrots then there aren't any carrots in the city and if there is it's gonna be very expensive"), inter-city convoys of carts and ships with guards, the option to raid or defend convoys, shops that close when supply is cut, and military supply lines affecting camp loadouts. The author concedes "I know it's almost impossible." This 2012 wishlist essentially describes Mount & Blade grafted onto Skyrim and remains unbuilt.
- Recurring Steam/Reddit threads ("Mod that makes harder economy?", "More gold for merchants, better fun for the player", "Economy Mods") show the same two asks year after year: make money *matter* (scarcity) and make merchants *react*.
- The most-upvoted formulations consistently ask for (1) regional price differences enabling a traveling-merchant playstyle, and (2) consequences for dumping loot — the exact two things the mod ecosystem only partially delivers.

#### (b) Practitioner explanations — which wall is claimed

- **Merchant-chest-only-on-barter** (Qvorvm, Nexus scripting forum, 2021): the sale inventory and gold aren't scriptable without opening the barter menu — an *in-engine scripting* wall. An external sim that only sets *prices* and *gold* (not stock) at the barter moment largely sidesteps this.
- **32,767 vendor-gold cap** (UESP; smr1957 on Steam; kassent's BarterFix; Barter Limit Fix): a hard engine data-type limit (signed 16-bit int). Faced by anyone raising merchant wealth; fixed by an SKSE plugin. An external architecture still faces this when writing gold values unless the fix is present.
- **`fBarterBuyMin` floor** (gamesas/UESP): PerkEntryPoint price mods can't drop below ~105%; a native-code hook is required to bypass. Relevant to an external sim that wants to model a genuine price crash.
- **Papyrus performance / save bloat** (UESP; Economics of Skyrim requiring SKSE): the reason in-engine simulation is throttled — and the strongest argument *for* the user's out-of-process approach.
- **48-hour respawn / restock corruption** (UESP; Merchant Stock Respawn Fix): coarse timers unrelated to economic activity, and flooding a merchant can break restocking.

Precision note for the user: most of the harshest "it's impossible" claims are about doing the simulation *in Papyrus* or about *stock manipulation via merchant chests*. They bind an in-engine scripted mod. They do **not** bind an out-of-process simulation whose only in-game footprint is setting prices and gold at the barter moment via a native SKSE hook — with the caveats that the 32,767 cap and the price floor still apply at the write-back layer, and continuous *stock* control remains hard.

#### (c) Reception evidence — what still feels static

- Reception of *Trade and Barter* is positive but bounded: users call it the reliable default ("Trade & Barter works fine") that makes Speech and location matter, but it is understood to change *prices*, not add *behavior*.
- The recurring complaint after installing merchant-gold mods is that they overshoot immersion in the *other* direction. On the *Currency, Coin, and Economy Revamp* thread, user **kilyle** (Steam, July 2023) lamented that a Riverwood merchant used to have only ~750 gold ("I'd have to journey to a bigger city to sell the more expensive items, which was a pain but made things feel more real") but post-mod has ~7,000, so "it lacks that 'small villages are poor' kinda feel I had been enjoying."
- A frequent lament: even with regional mods, the world doesn't *do* anything — "You can take every piece of dwemer gear or strut out of every ruin and yet you'll still find ingots to buy from blacksmiths. There is no… economy." The praise/complaint pattern is consistent: overhauls succeed at rebalancing numbers and adding regional flavor, and fail at making the world feel alive, because none of them simulate agents.

---

## Recommendations

**Staged plan for the user's external-sim architecture:**

1. **Prove the write-back path first (weeks, not months).** Build the thinnest possible loop: external sim → SKSE plugin (start with **file or HTTP**, following Mantella's proven pattern; TCP per Skyrim CrowdControl if you need low latency) → Papyrus via **SKSE ModEvents** → apply a price multiplier through a **native price-calc hook** (model on *Dynamic Prices Framework* mod 144874, which returns a float multiplier per item and can bypass `fBarterBuyMin`). Benchmark: sell 40 iron daggers, watch the price of the iron/weapon keyword fall in the sim and reflect on the next barter open. **Threshold to proceed:** stable price updates with no barter-menu stutter across 100+ transactions.

2. **Handle the two hard write-back limits explicitly.** Ship/require a **Barter Limit Fix-equivalent** so merchant gold above 32,767 works, and decide early whether you drive **vendor gold** as a simulated balance sheet (recommended — it's your cleanest "merchant wealth persists" feature and the community's #1 ask) or leave it static. **Benchmark:** a merchant that visibly runs low on gold after buying your dagger haul and recovers over sim-days.

3. **Choose price-lever over stock-lever.** Because merchant chests only populate at the barter moment and flooding them can corrupt restock, make **price and gold** your primary simulated outputs and treat **stock quantity** as a secondary, cautiously-driven output (inject via leveled lists / KID-style distribution on a timer, not by writing chests continuously). **Threshold to add stock simulation:** only after price+gold is rock-stable.

4. **Model what no shipped mod does — autonomous, player-independent dynamics — since that is the entire differentiation.** Cumulative-sales price depression (dagger-dump) is table stakes (*Reactive Markets* already ships it); your edge is merchants trading *with each other*, production feeding markets, and regional shocks propagating *without* the player. Do all of this in the external process where Papyrus limits don't apply.

5. **Borrow the two best-received consequence mechanics** to make the sim *visible*: *Bandit/Faction Economy*-style "your sold loot reappears on NPCs," and *Reactive Markets*-style "clearing a camp shifts local prices." Visible consequences are what reception threads reward.

6. **Study the primary design writeups** before finalizing tuning: the **Requiem Developer Diary** (weighted gold, scarcity philosophy, the Reddit-survey feedback loop) and the *Trade Routes* Feature/Item Details articles (a fully worked static supply/demand table you can use as a sanity baseline for your dynamic one).

**What would change this plan:** if benchmarking in step 1 shows the native price hook is unstable across SE/AE runtime versions (a known fragility of native-code mods, which "are often tightly tied to the game executable version"), fall back to the keyword+JSON additive method (*Dynamic Pricing Framework* mod 167487) and accept the `fBarterBuyMin` floor as a modeling constraint.

---

## Caveats

- **Version/era binding.** Many technical claims (merchant-chest scripting, 32,767 cap, Papyrus limits) are stable across Oldrim→SE→AE, but *specific mods* are version-sensitive: *Trade Routes* is reported broken on SE 1.6+ for inn vendors, and native-code price hooks require rebuilding per runtime version. Oldrim-era "impossible" claims about Papyrus still largely hold, but SKSE/CommonLibSSE-NG has widened what native plugins can do.
- **Reactive Markets is very new (July 2026) and lightly endorsed (34 endorsements at time of research);** treat its robustness as unproven at scale.
- **Two mods named "Dynamic Pric(e/ing) Framework" are different** (mod 144874 = JerryYOJ native hook; mod 167487 = shazdeh2 keyword/JSON). Don't conflate them.
- **The external-process-for-economy pattern is inferred, not demonstrated** — Mantella/Herika/CrowdControl prove the plumbing works for AI dialogue, actions, and Twitch effects, but no shipped mod drives the *economy* this way. The user would be first; the plumbing risk is low, the game-design risk (making it fun, not just accurate) is the real unknown.
- **Skyrim Together's exact wire protocol** was not confirmed from a primary source; its architecture is described at a high level from the Tilted Online wiki.
- Several roundup sources (myotakuworld, fandomspot, sportskeeda) are secondary listicles; all mod-mechanic claims above are anchored to the mods' own Nexus pages or primary forum/wiki sources where possible.