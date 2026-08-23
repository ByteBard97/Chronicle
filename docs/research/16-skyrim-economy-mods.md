---
date: 2026-08-23
sources:
  - "Skyrim Economy Modding Research.md"
  - "compass_artifact_wf-5f564260-54c3-5477-997c-802f1ad8b403_text_markdown.md"
topic: "Skyrim economy-simulation mod prior art"
status: filed
---

# Skyrim Economy Mod Prior Art (Merged)

Two independently commissioned research reports (referred to below as
**[Gemini]** and **[Compass]**) survey the same ground: shipped Skyrim
economy/pricing/merchant mods, the engine-level barter/vendor-gold
constraints they hit, and the community wishlist/reception record. This
research was requested speculatively; economic simulation itself remains
**out of scope for Chronicle until the belief tier is proven** (see
`docs/research/00-index.md`'s open-questions log, "slated v0.4"). File
this now as the ready reference for when that milestone arrives, rather
than treating it as informing current work.

> **Evidence-base note**: unlike the reactive-NPC pair
> ([15](15-skyrim-social-reactivity-mods.md)), neither report here flags a
> Reddit-access gap — both cite Reddit threads directly alongside Nexus
> mod pages, UESP, and Steam discussions. Citation quality is more uniform
> across this pair than the reactive-NPC pair.

## Findings

- **[BUILD-ON] Both reports agree on the ceiling: player-centric price
  feedback plus static regional tables, never an autonomous market.**
  [Gemini]: "the fidelity ceiling achieved by in-engine mods is limited to
  static global multipliers and local item category counters." [Compass]:
  "the best-shipped fidelity is 'reactive pricing centered on the
  player,' not a simulated market" — no merchant has autonomous wealth,
  no goods flow between towns without the player carrying them, and
  production sources (mines, mills) do not feed markets dynamically.
  [Compass] adds a sourced quote confirming the production-loop gap
  directly: a UESP forum veteran, asked whether over-mining depletes
  ore, answered "no, I haven't seen it, and doubt it is in… If you mine
  all the ore you can out of the town mine, the resident miners keep on
  banging away."
- **[BUILD-ON] The exact "dagger-dump" scenario Chronicle's design docs
  use as a canonical test case is already partially solved — but only as
  a per-keyword counter, not a market.** Both reports agree *Supply and
  Demand* (sasnikol) does this: selling ~20 identical items in one
  transaction drops that item's price ~40% via a 2%-per-item saturation
  counter. [Compass] adds a second, more recent implementation [Gemini]
  never mentions: **Reactive Markets (mod 186295, shazdeh2, uploaded 26
  July 2026)** — "each individual item sold/bought decreases/increases
  prices by 0.01%," capped at half/double the original price, computed
  per vanilla `VendorItem*` keyword, with a second layer where "clearing
  bandit hideouts (or forsworn camps in the case of the Reach) gives you
  a +1% positive buff for vendors in that hold" — a rare example of
  world-state (not just direct trades) feeding price. [Compass] flags it
  as new and lightly endorsed (34 endorsements at time of research) —
  treat its robustness as unproven at scale, not as a mature reference
  implementation.
- **[DISAGREEMENT — the load-bearing one] How completely does an
  external-process architecture bypass the engine walls?** [Gemini]'s
  conclusion is unqualified: an external simulation service "bypasses
  every major historical bottleneck" and "every major technical boundary
  documented in community practitioner discourse." [Compass] is
  materially more precise and should be treated as the more trustworthy
  framing: an external process "sidesteps the Papyrus performance and
  save-bloat walls entirely... It does *not* sidestep the *write-back*
  walls: results still enter the game through the barter price hook,
  vendor-gold values (mind the 32,767 cap), and leveled-list/inventory
  injection." [Compass]'s precision note is the one to carry forward
  verbatim into any ADR: *most of the harshest "it's impossible" claims
  are about doing the simulation in Papyrus or about stock manipulation
  via merchant chests — they do not bind an out-of-process simulation
  whose only in-game footprint is setting prices and gold at the barter
  moment via a native SKSE hook, but the 32,767 cap and the
  `fBarterBuyMin` price floor still apply at that write-back layer, and
  continuous stock control remains hard.*
- **[BUILD-ON] Concrete write-back mechanisms for an external price sim,
  from [Compass] (absent from [Gemini]).** Two distinctly-named-but-
  different "Dynamic Pric(e/ing) Framework" mods matter and should not be
  conflated: **mod 144874 (JerryYOJ)** is a native SKSE/CommonLibSSE DLL
  hooking the price-calc system directly, registering a C++ callback
  `(Actor* trader, InventoryEntryData* objDesc, uint16_t level,
  GFxValue& updateObj, bool is_buying)` returning a float multiplier —
  this is the one path that can bypass the `fBarterBuyMin` floor, because
  it overrides price *after* the vanilla calculation. **Mod 167487
  (shazdeh2)**, the one *The Gilded Road* actually uses, is a
  keyword/JSON additive-modifier framework subject to the classic
  PerkEntryPoint floor. [Compass]'s staged recommendation: prototype
  against the native hook (mod 144874) first; if it proves unstable
  across SE/AE runtime versions (native plugins are tightly
  version-bound), fall back to the keyword+JSON approach and accept the
  `fBarterBuyMin` floor as a real modeling constraint.
- **[RISK] Two hard engine limits any write-back path must plan for.**
  The 16-bit signed-integer vendor-gold cap at **32,767** (both reports;
  [Gemini] traces the SKSE fixes *Barter Limit Fix* and *Sales Overflow
  Solved*; [Compass] cites the same UESP source and a Steam quote from
  smr1957). And the **`fBarterBuyMin` price floor** (default 1.05,
  [Compass] only) — PerkEntryPoint-based price mods cannot push a buy
  multiplier below ~105% of the vanilla floor; only a native-code hook
  bypasses it. If Chronicle ever wants to model a genuine price crash
  (not just a damped one), the native hook is not optional.
- **[RISK] Merchant chests only populate on barter-menu open — a
  mechanical wall that shapes what's controllable.** [Compass] cites a
  mod author's (Qvorvm) first-hand forum account: scripted auto-selling
  found merchant chests silently empty because "merchant chests are not
  respawning unless I first (manually) open their barter menu" — the
  eventual working hack was to programmatically open and immediately
  close the barter menu. **Practical implication for Chronicle, stated
  explicitly by [Compass]: choose price and vendor-gold as the primary
  simulated write-back levers; treat stock quantity as secondary and
  timer-driven (leveled-list/KID-style injection), not something to
  write continuously.** [Gemini] documents the 48-hour merchant-chest
  reset timer and a separate "flooding a merchant can corrupt its
  restock state" finding (*Merchant Stock Respawn Fix*) that reinforces
  the same conclusion from a different angle.
- **[DESIGN-INPUT] The best-received "world visibly reacts" precedent
  is one-directional, not a price loop.** Both reports single out
  *Bandit Economy* / *Faction Economy*: items sold to a merchant have a
  chance (~50% neutral merchants, 100% fences per [Gemini]) of re-entering
  bandit/faction leveled lists and later appearing equipped on NPCs —
  "sell goods in Solitude, and you will see those weapons actually
  equipped on Imperials." [Compass] calls this the single best-shipped
  example of the world reacting to player economic behavior, precisely
  because it's visible and legible, not because it's a market.
- **[DESIGN-INPUT] External-process architecture has strong adjacent
  precedent, just not for economy specifically.** [Compass] surveys the
  IPC landscape Chronicle would be joining: Mantella (file→HTTP evolution,
  Leidtier's SKSE_HTTP + ModEvents), CHIM/Herika (WSL-hosted server over
  HTTP with in-game queues), Skyrim Together Reborn (dedicated
  `STServer.exe` + custom netcode), and — the cleanest reference pattern —
  **Skyrim CrowdControl**: external program → TCP socket → SKSE C++
  plugin → Papyrus executes effects, with async threads managing
  connection/timeouts. [Compass]'s explicit conclusion: "the
  external-process-for-economy pattern is inferred, not demonstrated...
  the plumbing risk is low, the game-design risk (making it fun, not just
  accurate) is the real unknown."
- **[RISK] Requiem's own postmortem is a rare primary-source design
  writeup on the balance-vs-simulation tension**, per [Gemini]: Requiem's
  authors deliberately chose scarcity/anti-exploit design over simulation
  fidelity ("I found it unimmersive that I could 'force' NPCs to buy my
  limitless quantities of crap") and their weighted-gold experiment (carry
  weight cost per septim) was liked in concept but disliked in
  implementation per their own Reddit survey — worth reading before
  Chronicle finalizes any economy-tuning philosophy, since it's a
  documented instance of a design choice the community pushed back on
  after shipping.

## Recommendations (synthesized from both reports' proposal sections)

1. **Prove the write-back path first, staged in weeks not months**
   ([Compass]): external sim → SKSE plugin (file or HTTP first, TCP if
   latency matters) → Papyrus via ModEvents → a native price-calc hook
   modeled on mod 144874. Benchmark: sell 40 iron daggers, confirm the
   price reflects on the next barter-menu open with no stutter across
   100+ transactions.
2. **Decide early whether vendor gold is a simulated balance sheet or
   left static** — [Compass] recommends simulating it (a merchant that
   visibly runs low on gold after a big buyout and recovers over sim-days
   is "the community's #1 ask" and the cleanest "merchant wealth
   persists" feature), but this requires shipping or requiring a Barter
   Limit Fix-equivalent for the 32,767 cap.
3. **Price and gold before stock.** Only add continuous stock simulation
   once price+gold write-back is proven stable — per the merchant-chest
   mechanical wall above.
4. **Differentiate on what no shipped mod does**: merchants trading with
   each other, production feeding markets, regional shocks propagating
   without the player present. Cumulative-sales price depression (the
   dagger-dump) is table stakes, already shipped by *Reactive Markets*;
   it is not Chronicle's differentiator on its own.
5. **Borrow the two best-received visible-consequence mechanics** when
   the economy tier is built: *Bandit/Faction Economy*'s "sold loot
   reappears on NPCs," and *Reactive Markets*'s "clearing a camp shifts
   local prices" — reception evidence favors visible, legible
   consequences over numerically-accurate but invisible ones.

## Mod survey table (merged; price model / tracking column cross-checked across both reports)

| Mod | Price model | Cumulative sales tracking | Mechanism | Ceiling / limit |
|---|---|---|---|---|
| Trade and Barter (kryptopyr) | Static multipliers: faction rank, Thane status, friendship, race, city size | No | PerkEntryPoint "Mod Buy/Sell Prices" | Cannot react to market saturation; the community default, not a simulation |
| Supply and Demand (sasnikol) | Player-centric saturation: ±2% per item transacted | Yes, per item/category | Event-driven Papyrus scripts on trade containers | Script-queue delay on bulk trades; centered on player only |
| Reactive Markets (shazdeh2, mod 186295) | ±0.01% per item, capped at 0.5×–2× original, per `VendorItem*` keyword | Yes | Runtime injection, zero vanilla record edits | New (July 2026), lightly endorsed, unproven at scale |
| Trade Routes — Regional Economy (taleden) | Static geographic supply/demand table (Origin→Supply→Balanced→Demand→Destination tiers) | No (node-based) | Cell-load Papyrus scripts, vendor inventory injection | Raw goods only; reported broken on SE 1.6+ for inn vendors; high cell-load Papyrus latency |
| The Gilded Road / Dynamic Pricing Framework (mod 167487) | Keyword/JSON additive multipliers by region/specialization | Partial | SKSE runtime injection (KID/CID), zero vanilla edits | Still subject to `fBarterBuyMin` floor |
| Dynamic Prices Framework (JerryYOJ, mod 144874) | Native C++ callback overriding price post-calc | N/A (framework, not a policy) | SKSE/CommonLibSSE DLL hook | Can bypass `fBarterBuyMin`; version-bound to SE/AE runtime |
| Bandit Economy / Faction Economy | N/A (item-flow, not pricing) | N/A | Sold items re-enter faction leveled lists | One-directional; no price feedback |
| Requiem | Scarcity/anti-exploit rebalance + weighted gold | No | Static rebalance + carry-weight cost per septim | Weighted gold liked in concept, disliked in implementation per the team's own player survey |

## Caveats

- **Version/era binding**: merchant-chest scripting, the 32,767 cap, and
  Papyrus limits are stable across Oldrim→SE→AE, but specific mods are
  version-sensitive — *Trade Routes* is reported broken on SE 1.6+ for
  inn vendors, and native-code price hooks require rebuilding per
  runtime version.
- *Reactive Markets* is unproven at scale (34 endorsements at time of
  research) — do not treat it as a validated reference implementation.
- The two "Dynamic Pric(e/ing) Framework" mods (144874 vs. 167487) are
  unrelated despite the near-identical name; don't conflate them in
  future citations.
- The external-process-for-economy pattern is inferred from adjacent
  domains (dialogue, actions, Twitch integration), not demonstrated for
  economy specifically — Chronicle would be first. Per [Compass]: "the
  plumbing risk is low, the game-design risk... is the real unknown."
- [Gemini]'s source document embedded six base64 PNG data-URIs in place
  of its barter-formula math; those are not reproduced here. For the
  record, in plain text: base price is adjusted by global barter
  variables `fBarterMax`/`fBarterMin`, interpolated by Speechcraft skill
  (capped at 100) and perks, giving separate purchase and sell
  multipliers; see [Compass]'s §A4 UESP citation for the exact vanilla
  formula (`price factor = 3.3 − 1.3 × min(Speech,100)/100`) instead —
  it's the same fact, stated as text rather than an embedded image.
