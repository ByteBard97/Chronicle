> Filed 2026-09-05 in `docs/research/comparative-systems/` — external
> research, not code-verified. Distinct from this folder's other files:
> it is a **focused Kenshi deep-dive on the collective/world-scale
> layer** (world states & town overrides, the faction-relations scalar,
> the crime/bounty/delegated-legal machinery, and player reception),
> complementing the two existing spatial-sim passes
> (`spatial-sim-shadows-of-doubt-nemesis-kenshi.md` and
> `spatial-sim-legal-boundaries-and-witness-propagation.md`), which
> cover Kenshi's witness/legal basics and per-NPC-vs-faction memory
> framing. The individual-NPC layer is deliberately out of scope here.
> Sources are the Kenshi wikis (Fandom, kenshi.wiki, the huijiwiki
> Chinese mirror), the Lo-Fi Games dev blog, modder-community
> documentation, and long-form player analyses; anything resting on a
> single source is marked **[single-source]**. Feeds the
> scenario-ladder / reactivity design work, not any accepted ADR.

# Kenshi's Collective Layer: World States, Faction Relations, and the Delegated Legal System

Kenshi (Lo-Fi Games, 2018) is the strongest shipping example of a
real-time, spatial open world whose *felt* dynamism comes almost
entirely from **coarse, faction-level state** rather than per-NPC
simulation. This report maps that collective layer in depth: what the
state actually is in the data, what flips it, what players see, and
which parts of it players credit for the "living world" feeling.

One correction up front: the earlier spatial-sim pass states "if
relations drop below −10, the entire faction becomes hostile." Two
independent community references — the Fandom wiki's
[Guide to Faction Relations](https://kenshi.fandom.com/wiki/Guide_to_Faction_Relations)
and the compiled [kenshi.zone Faction Relations report](https://kenshi.zone/en/faction-relations) —
both give **−30** as the hostile threshold and **+50** as the alliance
threshold. Treat −30/+50 as correct (community-verified, not
developer-published).

## 1. World States and Town Overrides

This is Kenshi's headline collective mechanic and the one the modding
community builds on most. The two existing spatial-sim files
established the basic shape (boolean flags → prefab swap on cell
load); this section goes deeper into triggers, chaining, vocabulary,
and shipped examples.

### 1.1 What the system is, in the developer's own words

Lo-Fi's own description ([Blog #25, Aug 2018](https://lofigames.com/blog-25-kenshi-at-tokyo-game-show/),
posted alongside update 0.98.48) is the primary source:

- World states affect **"the spawns and town states"** of factions.
  Two output channels, nothing more: *town overrides* (what a
  settlement is replaced with) and *homeless spawns* (whether/how many
  of a faction's squads appear in the wilderness).
- **Small factions are one-switch systems:** "take out their leader
  (Moll of Flotsam, for example) and the rest of the faction will fall
  into disarray. Wandering squads from that faction will lessen or
  disappear entirely, and their hometown will likely become destroyed
  or even taken over by another faction."
- **Large factions are multi-switch networks:** killing Emperor Tengu
  alone does not collapse the United Cities; "you'll likely have to
  find and destroy the bosses of individual towns or other strategic
  outposts." Crucially, the dev blog describes **ripple logic beyond
  the leader's hometown**: "taking out the slave farms and camps
  around a town will greatly reduce its access to vital supplies and
  hence have a negative effect on it, despite the boss still being
  alive. Taking out the boss of a strong defensive town will mean that
  nearby towns fall to invading enemies."
- The blog is explicit that **the player cannot take towns** — "town
  overrides does not mean that you as the player can take over towns"
  — only NPC factions can receive them.
- Legibility support: allied faction leaders (Esata, Simion, Moll, the
  Phoenix) give "strategic tips on the best ways to take [their
  enemies] down," i.e. the world-state graph is partially surfaced
  through dialogue.

### 1.2 Trigger semantics: kill, imprison, release

From the [Fandom World States page](https://kenshi.fandom.com/wiki/World_States)
and the [kenshi.zone World States report](https://kenshi.zone/en/world-states)
(two corroborating community sources):

- **Killing and imprisoning are usually equivalent.** Where a
  condition requires a character dead, imprisonment generally
  satisfies it. Where a condition requires a character alive, it means
  **alive AND free** — sitting in a cage counts as not-alive. The
  FCS-internal "Okay" check means alive-and-free.
- **Release rolls the state back.** If an imprisoned leader tied to
  homeless spawns is freed, the spawns return and some town overrides
  switch back — read by the community as deliberate support for
  rescue-mission narratives. A few overrides *require* the
  capture-then-release sequence to persist (Holy Mines → Slave
  Traders and Okran's Shield → Reavers switch to their destroyed
  states on a *second* visit if the captured character stays gone).
- Named exceptions: the Dust King's "Bandit Demands" event only stops
  if he is *dead*; the Hive Attack base assaults only launch if the
  Hive Queen is *kidnapped*, not killed (the stated in-fiction intent
  is a rescue mission).
- Recruiting a world-state-tied character (Seto, Bo) does not exempt
  them — the flags read the same while they stand in your squad.

### 1.3 The override vocabulary and priority rules

Per the [kenshi.zone World States report](https://kenshi.zone/en/world-states)
and the [huijiwiki 城镇覆盖 (Town Overrides) page](https://kenshi.huijiwiki.com/wiki/%E5%9F%8E%E9%95%87%E8%A6%86%E7%9B%96):

- A town's residents, bar squads, owning faction, and town type are
  all **properties of the town record** — and the override list is
  itself a property. An override swaps the whole property bundle: new
  faction, new residents, new bar squads, new building states.
- Overrides come from a small fixed vocabulary: **Malnourished** (flag
  unchanged, supply cut, everyone starving), **Half-destroyed** (some
  buildings rubble, thinner garrison), **Civil war** (filed internally
  as Malnourished + Half-destroyed for Sho-Battai), **Destroyed /
  Ruins** (two distinct internal names that look near-identical on the
  ground), **Prosperous**, or **a faction name** (who takes over).
- **"Prosperous" is a relative label, not a description.** The Fandom
  wiki's trivia note: it only means this is the *best* override
  available for that town — it can still have more rubble and more
  malnourished NPCs than the default state. Drifter's Last under the
  Free Traders is the canonical example (guards, police station,
  thieves' guild — internally named `prosperous`).
- **Priority:** when multiple overrides' conditions are satisfied, the
  one gated by the *most* world states wins; ties break to whichever
  comes first in the town's override list in the FCS data (huijiwiki).
  Bad Teeth is the most heavily branched shipped example — five
  ranked overrides (Half-destroyed, Destroyed, Shek Kingdom, Kral's
  Chosen, United Cities).

### 1.4 What actually changes in a town

Synthesizing the above with the complete override inventory at
[Raider King's Town Overrides guide](https://raiderking.com/kenshi-town-overrides/):

- **Ownership** (faction flag, map color), **population** (entire
  resident roster swapped), **buildings** (intact vs. rubble;
  ownership of shops changes hands), **spawns/patrols** (the new
  owner's garrison squads; zone-level homeless spawns change
  separately), **vendor tables**, and **town type**.
- The swap happens **only while the town is unloaded** — the old town
  despawns and the new one spawns (the mechanism documented in the
  earlier spatial-sim pass from modder Shidan: the game waits for the
  player to leave). Raider King independently confirms: you must get
  far enough away that the town unloads before the override appears.
- **Player-owned buildings are collateral.** The Fandom Guide to
  Faction Relations states overridden towns "are entirely new
  locations and any Player-Owned Buildings in Town are completely
  forgotten by the game." kenshi.zone flags a **direct conflict in
  the wiki record**: the Heft page says player buildings are *not*
  safe, while the general Town Overrides page says purchased buildings
  survive. Unresolved — see Evidence Gaps.
- Some overrides only take effect on the **second visit** (Holy Mines
  → Slave Traders; Okran's Shield → Reavers).
- Faction **headquarters relocate**: if the Shek Kingdom gains Stack
  or Bad Teeth, the Shek Faction HQ (and Esata) can move there from
  Admag ([kenshi.zone Admag report](https://kenshi.zone/en/admag)).

### 1.5 Notable shipped examples

The full inventory is Raider King's
[complete list](https://raiderking.com/kenshi-town-overrides/);
highlights, cross-checked against the
[Fandom World States page](https://kenshi.fandom.com/wiki/World_States)
and [ISK Mogul's Holy Nation world-states guide](https://www.iskmogul.com/kenshi-holy-nation-world-states/):

- **The Hub:** notable precisely for its *absence* — it has **no
  town override in vanilla** (it appears in no override inventory, and
  kenshi.zone lists it among the safe places to own property). The
  Tech Hunter towns (Black Scratch, Flats Lagoon, Mourn, World's End,
  Waystations) likewise have none. The world-state web covers the
  warring great powers and the minor warlords, not the neutral
  infrastructure towns.
- **Blister Hill (Holy Nation capital):** Phoenix out → Ruins;
  Phoenix + Seta + Valtena all out → **Flotsam Ninjas** if Moll is
  alive-and-free, **Holy Nation Outlaws** if she is not. There is a
  UC takeover override in the data that is **invalid/unreachable** in
  vanilla **[single-source: Raider King]**.
- **Rebirth (the HN slave camp):** same three-leader condition →
  Flotsam Ninjas (Moll ok) or HN Outlaws (Moll out).
- **Stack / Bad Teeth:** Seta out → Shek Kingdom (if Esata ok) →
  Kral's Chosen (if Flying Bull ok instead) → Ruins/UC variants deeper
  in the chain. This is the chaining pattern at its clearest: the same
  town cascades through up to five owners depending on the *global*
  vector of who is alive.
- **Okran's Shield:** Valtena out → United Cities (Tengu ok) → Ruins
  → Reavers (Tengu + Tsugi out, Valamon ok) → Shek Kingdom (player
  allied with Shek, Esata ok). Note the Shek branch is gated on a
  **player-alliance world state**, not just deaths; and if the player
  later kills Tengu, the Shek *abandon* it to Ruins.
- **Shek cities:** Admag falls to the **Berserkers** if Esata dies;
  Squin cascades Shek → Kral's Chosen → Berserkers depending on
  Esata/Mukai/Flying Bull.
- **United Cities:** the slave-supply ripple from the dev blog is
  realized in data — killing slave-farm bosses (Ren, Haga, Grande,
  Ruben, Wada...) drives towns toward Malnourished/Half-destroyed or
  **Empire Peasants** (a peasant-revolt faction) once Tengu and the
  nobles fall; Trader's Edge can flip to the **Anti-Slavers** if
  Tinfist lives and both Longen and Tengu are gone.
- **Tinfist (Anti-Slavers):** his death is the *enabling* condition
  for Slave Trader takeovers of the Fishing Village, Cult Village,
  Settled Nomads, and a Distant Hive Village — a dead abolitionist
  expanding the slave economy is the system's most cited emergent
  beat.
- **Esata / Phoenix / Tengu deaths** also degrade their armies:
  leaderless Holy Nation spawns weaker **Strayed Paladins**, leaderless
  UC spawns **Samurai Rogue** bandits — the "broken squad" pattern
  below.
- **Factions cannot be fully deleted** in most cases: beaten factions
  persist as weaker "broken" squads, and some settlements always keep
  their flag (HN keeps Holy Farms/Watchtower/Narko's Trap; UC keeps
  Tengu's Vault; the Shek keep Last Stand). Only a handful (Skin
  Bandits, Reavers, Manhunters, Slave Hunters, Traders Guild, maybe
  Yabuta Outlaws) can be reduced to zero spawns, settlements, and
  events. Three base assaults — Wrath of God, Challenger of the
  Undefeated, Invincible Vengeance — can persist **indefinitely**,
  leaderless.
- **Power vacuums create "invasion" spawns:** killing the Western
  Hive Queen causes the Southern Hive's homeless spawns to colonize
  zones across the map — the clearest shipped example of one
  faction's collapse *growing* another faction's footprint
  (Fandom Guide to Faction Relations + kenshi.zone, two sources).

### 1.6 Zone-level effects beyond towns

[ISK Mogul's Holy Nation guide](https://www.iskmogul.com/kenshi-holy-nation-world-states/)
documents the second output channel in detail: leader deaths retune
**which squads spawn in which zones** — killing Seta starts Shek
patrols spawning in Border Zone/Okran's Gulf/Okran's Pride (if Esata
lives), Kral's Chosen patrols (if Flying Bull lives), Berserkers in
Okran's Gulf (if Ghost lives); killing Valtena thins HN patrols in
Okran's Valley/Bast and removes them from Skimsands entirely. The
"world state" is thus not just a town-swap flag but a **global spawn
table modifier** keyed on the alive/free vector of ~40 named
characters.

### 1.7 How the modding community extends it

The world-state/override layer is the single most-extended system in
the Kenshi mod scene — itself reception evidence (§4):

- **[Reactive World](https://logu.jp/kenshi-mod-reactive-world/)**
  (Japanese community write-up; also recommended in
  [RoyalCDKeys' 2025 mod guide](https://royalcdkeys.com/blogs/news/best-kenshi-mods-2025-top-enhancements-mods-guide))
  adds large numbers of new triggers and overrides: e.g. a fractured
  Cannibal faction with many tribes, multiple Inquisitors to keep the
  Holy Nation functioning, bandit splinter factions after the Dust
  King dies. Patch ecosystems exist around it (e.g. the
  [LKO × Reactive World patch](https://catalogue.smods.ru/archives/185562)
  adding allied-faction takeovers and trade cultures for new owners).
- **[Living World](https://gamejunkie.pro/kenshi/living-world/)**
  takes the same machinery in a *restorative* direction: kill the
  Cannibal Grand Wizard and Deadcat reclaims its old capital; kill the
  Meat Lord and Deadcat gets First Village back; allied players can
  *choose* which allied faction receives a town. Notably, Living
  World pushes past the vanilla "player can never own towns" rule.
- A Chinese-community comparison thread
  ([tieba: Reactive World vs Living World](https://tieba.baidu.com/p/7698585502))
  is direct player discourse comparing the two approaches — Reactive
  World praised for depth but criticized for fragility (too many
  micro-leaders to hunt down, performance problems from cannibal
  corpse-piles), Living World praised as "simple and effective."
  Useful design signal: **more world-state branches ≠ better**; each
  branch must be discoverable and completable.
- Individual fix mods patch specific override chains players found
  unsatisfying, e.g.
  [Okran's Shield Belongs to the Shek FIRST](https://catalogue.smods.ru/archives/179015),
  which reorders a vanilla chain the author felt was illogical —
  evidence that players engage with override *ordering* as content.

## 2. The Faction Relations scalar

Two corroborating community sources: the Fandom
[Guide to Faction Relations](https://kenshi.fandom.com/wiki/Guide_to_Faction_Relations)
and [kenshi.zone's Faction Relations report](https://kenshi.zone/en/faction-relations).
The earlier spatial-sim files established the scalar (−100..+100) and
faction-as-memory-unit framing; this section pins the thresholds,
gated behaviors, and change vectors.

### 2.1 Thresholds and gated behaviors

- **−30: hostile on sight.** The whole faction attacks. Some factions
  (Cannibals, Berserkers, Swamp Ninjas, Fogmen, Slave Hunters) are
  hardwired hostile regardless of the number.
- **+50: allied.** The bundled behavior changes (both sources agree):
  gate guards stop searching you; members hand out food and medicine;
  they assist you in combat and bandage your downed characters; **your
  bounties are ignored** (except crimes they personally witness);
  allied factions may **send troops to defend your outpost** when a
  third faction assaults it (e.g. ally HN → HN troops arrive when the
  Shek Kingdom attacks your base).
- **Witnessed crime overrides the scalar:** anyone who sees you commit
  a crime against their faction or its allies may attack *even at
  alliance-level relations*. The scalar gates default disposition, not
  event-driven hostility.
- Display: the faction panel rounds to whole numbers; hovering a
  visited settlement on the map shows several decimals — the community
  uses this to verify micro-changes (0.01-scale healing gains).
- Between −30 and +50: neutral — enter towns, trade. No intermediate
  named bands; the design is two thresholds, not a ladder.

### 2.2 How relations change

| Action | Effect | Notes |
|---|---|---|
| Attack faction members | Drops; faster for high-rank targets | Prolonged mass fighting eventually flips even neutral factions hostile |
| Imprison someone in a cage + initiate dialogue | −1 | |
| Put someone in a Peeler Machine | Drop ∝ victim's faction standing | |
| Attack/imprison a **Diplomatic Status** character | Severe drop | "Diplomat" = plot-important NPC, with hidden mechanics: mostly immune to ranged targeting, bodyguards retaliate one-at-a-time in self-defence, and can usually still be talked to even by a hated player |
| Heal faction wounded | Gain ∝ target's importance | **No witness needed**; healing a leader can pull −100 → +5 in seconds; a mook is ~0.01 per 100 healing. **Hard cap at +5** — enough to stop hostilities, never enough to ally |
| Turn in a bounty via dialogue | +2 (+5 with the Holy Nation if you refuse payment) | Flat regardless of bounty size; a few named leader bounties give much larger swings (see the [Bounty page](https://www.kenshi.wiki/w/Bounty): Phoenix → +70 Shek/−75 HN, Esata → +80 HN/−75 Shek, Bugmaster → +70 Shek/−80 HN) |
| Buy a slave's freedom | +4 with the slave's faction | Repeatable; freeing 38 times (−100 → +50) costs c.38k–760k Cats depending on slave skill |
| Sell characters into slavery | +1–2 with slaver factions | |
| Pacifiers | Cash-for-relations bar NPCs | Pay banded fees (100k/75k/55k/35k/15k for majors; 50k/40k/30k/20k/10k for Anti-Slavers/Flotsam/Hounds); each payment lifts you only to the bottom of the next band; 2-hour cooldown per pacifier. **Refuse service** if you allied their mortal enemy or killed/imprisoned their key figure — and they tell you why |

### 2.3 Decay

No source documents any passive decay of faction relations; both
guides treat the scalar as permanent until changed by an action (and
the existence of a paid pacifier economy implies it does not heal on
its own). Bounties (§3) decay on their own schedule — a separate
mechanism. **[Community consensus, not developer-published.]**

### 2.4 Alliance knock-on chains

Allying with faction A does not automatically set you hostile with
A's enemies — but most alliance *procedures* carry an immediate,
itemized bill (both sources):

- Join **Flotsam Ninjas** via Moll → Holy Nation **−75**.
- Join **Anti-Slavers** via Grey → United Cities, Traders Guild,
  Slave Traders **−30 each**.
- Join **Rebel Farmers** via Boss Simion → UC and Slave Traders **−25
  each**.
- Take Seto from Esata → Holy Nation **−10**.
- Ally **Skeleton Bandits** → severe damage with Crab Raiders and Skin
  Bandits.
- Turning in a hostile faction's *leader* bounty is generally an
  outright break with that faction (numbers in §2.2).
- Counter-examples: allying HN or UC does **not** auto-anger the
  other; allying the Shek Kingdom does not necessarily offend HN
  unless you pick the hostile dialogue branch when turning in the
  Bugmaster.

The starting *inter-faction* relation table is itself authored:
Rebel Farmers sit at −100 toward the UC but only −50 toward the Slave
Traders — kenshi.zone reads this as design text (the rebels hate the
aristocracy, not the trade), flagged there as interpretation, not
stated fact.

### 2.5 The bodyguard/healing behaviors

The alliance behavior bundle (food gifts, combat aid, bandaging
downed player characters, ignoring bounties) is documented in both
relation sources. The temporary-escort pattern — allied troops
aiding the player on campaign — appears in the dev blog ("some of
their troops might aid you temporarily in your path of destruction")
and in the outpost-defense aid events. There is no evidence of a
general "bodyguard contract" system tied to relation bands in
vanilla **[evidence gap — see §5]**.

## 3. Crime, bounty, and the delegated legal system

The witness model (line-of-sight, faction-as-memory, EV_WITNESS_*
dialogue triggers) is covered in the two existing spatial-sim files
and not repeated here. This section adds the accrual/persistence
math, the prison/enslavement flows, and the delegation data.

### 3.1 Crime categories and persistence math

The [kenshi.wiki Bounty page](https://www.kenshi.wiki/w/Bounty)
publishes the full crime table (single wiki page, but internally
consistent with the loading-screen tips it quotes):

| Crime | Expire time | Sentence | Bounty |
|---|---|---|---|
| Trespassing | 4 h | 2 h | c.100 |
| Looting (robbing unconscious) | 20 h | 10 h | c.500 |
| Assault (incl. self-defence against a faction) | 20 h | 10 h | c.500 |
| Burglary (lockpicking) | 40 h | 20 h | c.1,000 |
| Theft (taking owned items) | 100 h | 50 h | c.2,500 |
| Escaping prison | 100 h | 50 h | c.2,500 |
| Terrorism (attacking a noble; freeing slaves) | 200 h | 100 h | c.5,000 |
| Kidnapping | 200 h | 100 h | c.5,000 |

- **The expiry formula is linear: 4 hours per c.100 of bounty.**
  Jail time is half the expiry time. This is Kenshi's
  statute-of-limitations mechanic: crime *does* wash out, on a clock
  scaled to severity.
- **Notoriety threshold:** above **c.10,000** a bounty never expires
  on its own. Up to c.25,000 it can still expire if served in jail;
  above that, only **bail at 2× the bounty**, paid to the Police Chief
  / Inquisitor / Hundred Guardian (faction-dependent), clears it.
- **Recognition scales with bounty size:** "The bigger your bounty,
  the more people are going to recognize you. Police and bounty
  hunters are the sharpest spotters, while civilians will only
  recognize the most infamous of criminals" (loading-screen tip quoted
  on the Bounty page) — and recognition takes time, so a wanted
  character can dash through town if they avoid attention.
- Fine print: UC and Traders Guild **share** bounties, so characters
  wanted by both show doubled values **[FCS note on the Bounty page]**;
  bounties occasionally bug and vanish.

### 3.2 Prison and enslavement flows

From the same Bounty page and the Faction Relations guide:

- Factions that will actually cage wanted players: **United Cities,
  Shek Kingdom, Holy Nation, Mongrel, and Bounty Hunters**. They knock
  the character out and cage them; the sentence runs at half the
  expiry clock.
- **Pro-slavery jurisdictions convert prison into slavery:** a caged
  character may be enslaved before their sentence ends and shipped to
  the faction's slave mines (Rebirth for the HN; slave farms for the
  UC/Traders Guild economy). Slavers strip all gear on enslavement.
- Slaver NPCs attempt to enslave **any non-allied unconscious
  character** they encounter — the mechanism that turns a lost
  wilderness fight into the iconic Kenshi slavery arc.
- Player-side interactions with the same machinery: buying slaves
  free (+4 relations, §2.2), selling characters into slavery (+1–2
  with slaver factions), and a family of documented turn-in exploits
  (re-caging the same bounty, no "already turned in" check) listed on
  the Bounty page — evidence the turn-in pipeline is a thin,
  exploitable state machine.

### 3.3 Jurisdiction delegation in the data

The [huijiwiki 法律体系 (Legal System) page](https://kenshi.huijiwiki.com/wiki/%E6%B3%95%E5%BE%8B%E4%BD%93%E7%B3%BB)
gives the FCS-level structure (single wiki, but this is a data-table
page; the headline fact — Tech Hunters delegating to the UC — is
corroborated by the earlier spatial-sim pass's independent sourcing):

- A faction's **Legal System** property can point at another faction.
  **All factions using the same legal system share wanted lists**: a
  crime witnessed and reported by any bounty-capable character makes
  you wanted by every faction on that legal system, and you can be
  turned in to any of them that has police/cages.
- The shipped delegation table:
  - **United Cities legal system** ← United Cities, Bounty Hunters,
    Traders Guild, Slave Traders, Free Traders, Tech Hunters, Empire
    Peasants, Machinists.
  - **Holy Nation** — itself only.
  - **Shek Kingdom** — itself only.
  - Factions with no legal system set issue bounties **in their own
    name only**; those bounties do not propagate to any umbrella.
- **Who can issue a bounty:** only characters of occupation types
  `OT_MILITARY` or `OT_LAW_ENFORCEMENT` belonging to a real (non-
  "pseudo") faction. The per-character "assigns bounties" flag is
  documented as non-functional. Corner case: crimes against the
  Southern Hive produce a bounty that never appears in the wanted list
  because the faction has issuers but fails the listing conditions.
- Cross-faction consequence shape: commit a crime against a Tech
  Hunter shop and you are wanted across the entire UC umbrella — but
  only UC cities have the police infrastructure to arrest you; the
  local settlement just attacks. (This is the "delegated legal"
  pattern the earlier files already recommended copying; the table
  above is the shipped instance inventory.)

### 3.4 Alarm propagation

The earlier spatial-sim pass covers the observer-runs-to-raise-alarm
behavior and the EV_WITNESS_* trigger set. This pass found **no new
corroborated data** on alarm radius, propagation timing, or guard
convergence rules — flagged in §5.

## 4. Player reception: which systems produce the felt dynamism

Kenshi sits at ~95% positive across tens of thousands of Steam reviews
([Game8](https://game8.co/articles/latest/541) cites 95% over 69,000
reviews in 2023). The reception pattern across reviews, video essays,
and modding behavior:

**What gets named:**

- **The prison/slavery fail-state loop** is the most-cited
  "this game is different" beat. NeverKnowsBest's January 2019 video
  review is literally billed "Getting beaten by starving mobs, sold
  into slavery and eaten by cannibals is a good thing! (and here's
  why)" ([RPGWatch listing](https://rpgwatch.com/news/kenshi--review-neverknowsbest-41660.html)).
  The slavery arc works *because* it is collective machinery (slavers
  enslave any unconscious non-ally; cages convert to mines) rather
  than scripted quests.
- **World states / town overrides** are the mechanic the community
  *extends*: the two flagship overhaul mods (Reactive World, Living
  World) are both world-state expansions, with patch ecosystems and
  cross-language player discourse comparing them
  ([tieba comparison thread](https://tieba.baidu.com/p/7698585502),
  [Japanese mod write-up](https://logu.jp/kenshi-mod-reactive-world/)).
  Players engage deeply enough to debate override *ordering* and to
  author fix-mods for single chains
  ([Okran's Shield mod](https://catalogue.smods.ru/archives/179015)).
- **The indifferent, un-leveled world** ("you are not special") is the
  review headline — Rock Paper Shotgun's
  [Wot I Think (2018)](https://indie.rpgwatch.com/news/kenshi--review-rock-paper-shotgun-41475.html)
  ("You might as well ask me to review atmospheric pressure") and the
  [SsethTzeentach review (Mar 2019)](https://rpgwatch.com/news/kenshi--video-review-ssethtzeentach-41971.html),
  which was the game's mainstream breakout. The felt dynamism is
  attributed to *consequence and indifference*, not to NPCs having
  inner lives.
- **Emergent-narrative essays** (e.g.
  [Mechanics of Magic, 2024](https://mechanicsofmagic.com/2024/06/14/rwp-essay-emergent-narrative-in-kenshi/),
  [The Daily Fandom](https://thedailyfandom.org/kenshi-2018/))
  credit the *interaction* of systems — crime, slavery, factions,
  wounds — rather than any single one.

**What exists but players barely notice:**

- The **world-state ledger itself is silent**: no journal entry ever
  tells you the world changed ([kenshi.zone](https://kenshi.zone/en/world-states)).
  Guide-site framing ("the world of Kenshi might seem to most players
  relatively static" —
  [Raider King](https://raiderking.com/kenshi-town-overrides/))
  implies many players never discover overrides unaided; the devs
  added leader "strategic tips" dialogue precisely because the system
  was illegible.
- The **faction-relations scalar's micro-movements** (0.01-per-heal
  gains, decimals hidden in map hover text) are invisible in normal
  play; the visible surfaces are the two thresholds.
- The **delegated-legal table** is essentially never discussed as
  such; players experience it as "the UC hates me now, why" (the
  earlier spatial-sim file's cited r/Kenshi "Are Tech Hunters stupid
  or something?" thread is exactly this confusion surfacing).
- The tieba thread's criticism of Reactive World (too many
  micro-leaders, broken chains, perf cost) is the clearest player-side
  statement of the failure mode: **collective-state branches that
  players cannot discover or complete read as bugs, not depth.**

**Reading for Chronicle:** the felt dynamism comes from (a) fail-state
machinery that recontextualizes defeat (prison/slavery), (b) visible
reconfiguration of familiar places (town overrides), and (c) a world
that acts without the player (patrol/invasion spawn shifts). The
connective scalar and legal-delegation plumbing are load-bearing but
invisible — players credit their *effects*, never their existence.

## 5. Evidence gaps

- **FCS-internal world-state field structure.** The Kenshi Modding
  Wiki (FCS: World States) was unreachable (HTTP 403) during this
  pass; exact field names for override condition lists come only via
  wiki prose, not the data files or a data-dump repo. The huijiwiki
  dialogue-framework page does confirm the dialogue-level `world
  state` condition and the `trigger campaign / lock campaign / unlock
  campaign` effects exist as FCS primitives.
- **Alarm propagation mechanics** (radius, timing, guard convergence)
  beyond what the earlier spatial-sim files established — no new
  sources found.
- **Faction-relations decay:** absence of evidence, not evidence of
  absence; no developer statement located.
- **Blister Hill's invalid UC override** — single-source (Raider
  King).
- **Player-owned buildings under overrides:** two wiki pages directly
  contradict each other (kenshi.zone documents the conflict); the
  safe-town list (The Hub, Mongrel, Mourn, Black Scratch, Waystations,
  Flats Lagoon) is community lore.
- **"Destroyed" vs. "Ruins"** as internal override names — possibly
  two labels for one state; unresolved per kenshi.zone.
- **World State Routes** (the faction-*growth* counterpart to
  collapse): the Fandom page is a stub listing factions with no
  conditions; the system's full condition graph is undocumented
  anywhere found.
- **Reception quantification:** no telemetry; "players credit X" rests
  on reviews, essays, and mod-download behavior, not survey data.
- The relations thresholds (−30/+50), healing cap (+5), pacifier
  bands, and expiry formula are all **community-verified, not
  developer-published** — treat exact numbers as ~correct, not
  authoritative.

## 6. Transferability to a real-time first-person RPG with per-hold law (Skyrim)

Ranked by expected value-for-effort, assuming a Chronicle-style
event-sourced belief layer underneath:

1. **Delegated legal systems → per-hold jurisdiction pointers.**
   Highest transfer. Kenshi's shipped table (eight factions sharing
   the UC umbrella; majors self-hosted) maps one-to-one onto Skyrim's
   holds: minor factions (a village, a coven, a caravan company) point
   at the hold's legal system; crimes witnessed locally accrue to hold
   bounty; only hold capitals have arrest infrastructure. Chronicle
   already exceeds the witness side; this is the missing *output*
   structure. (Already recommended in both earlier passes — the
   shipped delegation table in §3.3 is the existence proof at scale.)
2. **The linear bounty expiry curve + notoriety threshold.** A
   statute of limitations (4 h per 100c, jail at half, permanent above
   a threshold, bail at 2×) is trivially cheap, legible, and produces
   the "lay low for two days" gameplay Skyrim's bounty system lacks.
   The recognition-scales-with-bounty rule (guards sharp, civilians
   only spot infamous criminals) is the natural fit for a
   first-person disguise/hood game.
3. **Threshold-bundled faction behavior.** Two legible thresholds
   (−30/+50) each carrying a *bundle* of behavior changes (gate
   searches stop, gifts, combat aid, healing the player's downed
   characters, bounty-blindness, outpost defense) rather than a
   gradient. Bundles at thresholds are far more legible in first
   person than continuous gradients — the player can learn "allied =
   they patch me up."
4. **Kill/imprison equivalence + release-rollback.** Making
   imprisonment satisfy "dead" conditions, and making release revert
   the world state, buys rescue-mission narratives for free and keeps
   the world state *reversible* — important in a 200-hour RPG where
   the player may want to undo a cascade. Chronicle's event log makes
   reversal natural.
5. **"Broken squad" degradation instead of faction annihilation.**
   Leader death → weaker remnant spawns (Strayed Paladins, Samurai
   Rogues) rather than zero spawns. Cheap, avoids content deletion,
   and keeps regions dangerous-but-different. Directly applicable to
   Skyrim's radiant faction encounters.
6. **Town overrides — adapt, don't copy.** The prefab-swap works in
   Kenshi because towns are stateless and the player can't own them.
   Skyrim towns are dense with quests, ownership, and persistent refs;
   a wholesale swap is too destructive (Kenshi itself forgets player
   property — its most-cited override bug-adjacent pain point, with
   the wiki record contradicting itself). The transferable core is
   **graded state overlays on the same town** (Kenshi's own
   Malnourished/Half-destroyed/Civil-war vocabulary): swap guard
   factions, shop inventories, crowd composition, and building states
   *in place*, driven by Chronicle's world-state flags, rather than
   replacing the location.
7. **Escalating, potentially-permanent base assaults — use with
   care.** They are the faction-level "the world retaliates" signal
   and work well as consequence for attacking leadership, but
   Kenshi's never-ending assaults (Wrath of God et al.) are a known
   frustration; a Chronicle implementation should cap escalation and
   offer an in-fiction off-ramp (Kenshi's own pacifier/turn-in
   economy is the model for off-ramps).
8. **Do not copy: the silent ledger and the whole-faction instant
   witness.** Kenshi's invisible world-state journal is its biggest
   legibility failure (devs bolted on tip dialogue post-hoc);
   Chronicle's provenance model should surface "the world changed
   because you did X" diegetically. And the faction-as-memory-unit
   collapse — acceptable in Kenshi's zoomed-out presentation — would
   read as psychic NPCs in first person; Chronicle already exceeds it.

**The AI-layer intersection (collective only):** patrols and invasion
waves are zone spawn tables keyed on the leader alive/free vector;
base assaults are dialogue-triggered **campaigns** (`trigger campaign`
FCS effect) launched by events, escorted by allied-faction aid as a
relation benefit; allied troops joining the player's campaign are
**AI contracts** (temporary package overrides) issued through
dialogue. Faction wars are *not* simulated — border conflict is
authored co-spawning, and conquest is the override system, not
movement of armies. For Chronicle: collective military behavior =
spawn-table and package data gated on world state, never an off-screen
war simulation.

### Key sources

- Lo-Fi Games, [Blog #25 — world states developer summary (Aug 2018)](https://lofigames.com/blog-25-kenshi-at-tokyo-game-show/)
- Kenshi Wiki (Fandom): [World States](https://kenshi.fandom.com/wiki/World_States), [Guide to Faction Relations](https://kenshi.fandom.com/wiki/Guide_to_Faction_Relations)
- kenshi.wiki: [Bounty](https://www.kenshi.wiki/w/Bounty)
- kenshi.zone compiled reports: [World States](https://kenshi.zone/en/world-states), [Faction Relations](https://kenshi.zone/en/faction-relations), [Admag](https://kenshi.zone/en/admag)
- Kenshi中文维基 (huijiwiki): [法律体系 / Legal System](https://kenshi.huijiwiki.com/wiki/%E6%B3%95%E5%BE%8B%E4%BD%93%E7%B3%BB), [城镇覆盖 / Town Overrides](https://kenshi.huijiwiki.com/wiki/%E5%9F%8E%E9%95%87%E8%A6%86%E7%9B%96), [对话框架与概括 / Dialogue structure](https://kenshi.huijiwiki.com/wiki/%E5%AF%B9%E8%AF%9D%E6%A1%86%E6%9E%B6%E4%B8%8E%E6%A6%82%E6%8B%AC)
- [Raider King — complete Town Overrides inventory](https://raiderking.com/kenshi-town-overrides/); [ISK Mogul — Holy Nation world states](https://www.iskmogul.com/kenshi-holy-nation-world-states/)
- Mods as reception evidence: [Living World](https://gamejunkie.pro/kenshi/living-world/), [Reactive World write-up (JP)](https://logu.jp/kenshi-mod-reactive-world/), [Reactive vs Living World player thread (tieba)](https://tieba.baidu.com/p/7698585502), [LKO×Reactive World patch](https://catalogue.smods.ru/archives/185562), [Okran's Shield reorder mod](https://catalogue.smods.ru/archives/179015)
- Reception: [RPS Wot I Think via RPGWatch](https://indie.rpgwatch.com/news/kenshi--review-rock-paper-shotgun-41475.html), [NeverKnowsBest review via RPGWatch](https://rpgwatch.com/news/kenshi--review-neverknowsbest-41660.html), [SsethTzeentach review via RPGWatch](https://rpgwatch.com/news/kenshi--video-review-ssethtzeentach-41971.html), [Mechanics of Magic emergent-narrative essay](https://mechanicsofmagic.com/2024/06/14/rwp-essay-emergent-narrative-in-kenshi/), [The Daily Fandom essay](https://thedailyfandom.org/kenshi-2018/), [Game8 on Steam rating](https://game8.co/articles/latest/541)
