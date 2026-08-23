---
date: 2026-08-23
sources:
  - "Skyrim Economy-Simulation Mods — Deep Research Report.md"
topic: "Skyrim economy-simulation mod prior art — third independent pass"
status: filed
---

# Skyrim Economy Mod Prior Art, v2

Third independent research pass on the same ground as
[16-skyrim-economy-mods.md](16-skyrim-economy-mods.md) (itself a merge of
two reports) — same naming pattern as
[08-social-sim-literature-v2.md](08-social-sim-literature-v2.md). Reaches
the same top-line conclusion as 16 independently (player-centric price
feedback and static regional tables are the ceiling; no shipped mod runs
the economic *simulation* from an external process), and adds enough
distinct evidence — different named mods, hard vote/download numbers, an
abandonment-quote for the one mod that did solve the dagger-dump case —
to file separately rather than blend into 16. Economic simulation remains
out of scope for Chronicle until the belief tier is proven (v0.4) — see
[00-index.md](00-index.md)'s open-questions log.

## What's genuinely new here (not in report 16)

- **[RISK — quantified] The community demand has a hard number, and it's
  large.** The canonical 2019 "sell 50 daggers of paralysis, see them on
  NPCs later" thread sits at **1,485 upvotes / 151 comments**, with its
  top reply ("one of the best ideas I've seen for a mod") at 847 upvotes.
  Report 16 characterizes this demand qualitatively; this report supplies
  the number that makes it citable as a strong, not just perennial,
  signal.
- **[BUILD-ON] Supply and Demand's own author explicitly disowns the mod
  — sharper than report 16's framing.** Report 16 notes Supply and
  Demand implements per-item cumulative-sale price depression. This
  report adds the author's own Future Development note verbatim: "I
  don't intend on building Supply and Demand any further, and would
  advise against using it unless you want some wacky behavior. Arrows in
  particular tend to rise and fall to some extremes, and can be exploited
  easily." The one mod that shipped the exact mechanic Chronicle's design
  docs use as a canonical test case was abandoned by its own author at
  proof-of-concept quality, with a named failure mode (arrow-price
  extremes) — worth citing directly if Chronicle's own design ever cites
  Supply and Demand as a working reference; it isn't one.
- **[BUILD-ON] Concrete numbers for the 2025–2026 native-code pricing
  generation, absent from report 16.** shazdeh2's Dynamic Pricing
  Framework (Dec 2025): ~54,500 unique downloads, 464 endorsements by
  mid-2026, 177-upvote announcement thread. The Gilded Road (Jan 2026,
  built on that framework): ~15,200 unique downloads, 375 endorsements in
  seven months, **1,049-upvote / 112-comment release thread**. These
  numbers matter for one specific claim: the native-hook architecture
  (price control moved from Papyrus/perk records into native SKSE
  plugins with JSON config, "no scripts, no dirty edits, no save bloat,
  can install/uninstall mid-game") is not a niche curiosity — it's the
  most enthusiastically received economy mod release in the dataset,
  which is direct community validation that the "external computation,
  thin engine footprint" pattern Chronicle is betting on is exactly what
  players want and reward.
- **[BUILD-ON] Master Trader's reverse-pickpocket trick for merchant gold
  — a concrete, named mechanism report 16 doesn't cover.** Vendor gold
  lives in the merchant's hidden chest, not the actor, so it "can't be
  tampered with directly, at least not in a live fashion" (author's own
  words). Master Trader's workaround: reverse-pickpocket gold onto the
  merchant at barter-menu open, strip it on close. This is a reusable,
  documented pattern for any Chronicle write-back path that needs to set
  vendor gold to a simulated value at the moment of interaction, distinct
  from the native price-calc hooks report 16 already covers.
- **[DESIGN-INPUT] Two shipped mods report 16 doesn't mention, both
  relevant to scope-setting.** **Stock Market of Skyrim** (2021) is a
  genuine financial-simulation outlier: 20+ stocks with fluctuating
  prices, dividends, a two-currency exchange, indexes, and *player
  actions* moving prices (completing East Empire Company quests raises
  its stock; killing Vittoria Vici tanks it), with in-world news
  reflecting events — built as a tech-demo for a larger project, not
  adopted widely, but proof that "your actions move an abstracted market"
  is buildable and has shipped once. **Conquest of Skyrim** (2023, WIP)
  is the most literal *production* simulation found in this research —
  captured mines "hire miners" to produce a metal stream, cities manage
  gold/food/metal/wood, farms/mills upgrade — but scoped entirely to the
  player's own faction, i.e., a strategy-layer resource sim bolted onto
  Skyrim, not a living NPC-driven market. Neither changes the top-line
  conclusion (no autonomous NPC-to-NPC economic behavior has shipped),
  but both are useful precedent citations for specific sub-mechanics
  (abstracted market indices; resource-node production) if Chronicle's
  v0.4 economy tier wants a lighter-weight model than full per-merchant
  simulation.
- **[DESIGN-INPUT] Faction Economy's own origin story is a direct
  precedent for "the community asked for exactly this."** Its release
  post states: "Faction Economy is based on a Reddit discussion. The
  question was, 'Can items we sell show up on NPCs?'" — a rare case of a
  mod author explicitly building the community's most-upvoted ask,
  confirming both that this specific mechanic (sold loot reappearing on
  NPCs) was demand-driven, not author-invented, and that shipping
  directly against a named wishlist thread is a viable playbook.
- **[RISK] A calibration point on how much the community's aspirational
  bar (Mount & Blade, Kenshi, X4) actually holds up.** Report 16 cites
  these as "the repeatedly-cited bar" without qualification. This report
  adds a corrective from inside the Kenshi community itself: top Kenshi
  threads argue "Kenshi doesn't have a real economy" and that "there is
  no actual economy, there are world states tied to NPCs" — even in
  overhaul mods. Implication: the bar Skyrim modders imagine when they
  invoke these games is partly aspirational even for the cited games
  themselves. A genuinely reactive Chronicle economy (if/when built)
  would exceed, not merely match, the games commonly held up as the
  standard — worth knowing so the v0.4 economy tier isn't scoped against
  an imagined ceiling nobody has actually shipped anywhere.
- **[BUILD-ON] A second, independently-stated "which wall is real"
  precision check that agrees with report 16's core disagreement-
  resolution.** This report's own synthesis: walls from leveled-list
  churn, chest-bound gold, and Papyrus-resident state are "already
  bypassed by native hooks and injection frameworks"; the 32,767 gold
  cap "needs an engine fix regardless of where the simulation lives";
  save-permanence "dissolves entirely if state lives outside the save."
  It explicitly identifies the two things **nobody has built or even
  attempted**: continuous event exfiltration from the engine at scale
  (feeding an external simulator every transaction, not just price
  reads), and NPC-merchant persistent state (inventory, balance sheet,
  production) independent of the chest-respawn timer. This sharpens
  report 16's "throughput of the bridge" framing into two specific,
  named, unattempted engineering problems — the more concrete of the two
  framings, worth carrying into any ADR text on the eventual economy
  tier.

## Not repeated here

Trade & Barter / Trade Routes as the static-multiplier baseline, the
32,767 signed-16-bit vendor-gold cap, the `fBarterBuyMin` price floor,
the merchant-chest-only-populates-on-barter mechanical wall, Bandit/
Faction Economy's sold-loot-reappears-on-NPCs pattern, and the general
Papyrus-throughput/save-bloat wall are all already filed in
[16](16-skyrim-economy-mods.md) from its two sources and substantially
overlap this report's coverage of the same ground — not re-filed here to
avoid duplication.

## Caveats

- Numbers (endorsements, downloads, upvotes) are point-in-time
  (mid-2026) snapshots from this report's research date and will drift.
- Reddit thread vote/comment counts are as reported by this source and
  were not independently re-verified against live Reddit by this session.
