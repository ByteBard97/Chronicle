---
date: 2026-09-05
sources:
  - "Open Civil War SSE, Nexus 11076 (mod page, fetched 2026-09-05)"
  - "Open Civil War LE, Nexus 82128 (mod page, fetched 2026-09-05)"
  - "OCW_Readme.txt (file-metadata.nexusmods.com, fetched 2026-09-05)"
  - "palimptes.dev/ocw (simtam's own project page, fetched 2026-09-05)"
  - "SSE Organic Factions, Nexus 10289 (Wayback capture 2026-04-24)"
  - "Organic Factions Extension, Nexus 25471 + LE 82607 (mod pages, fetched 2026-09-05)"
  - "Civil War Overhaul Redux, Nexus 37906 (mod page, fetched 2026-09-05)"
  - "schofida/CWORR GitHub repo (API: license, commits, releases, issues, fetched 2026-09-05)"
  - "WARZONES - Civil Unrest for SSE, Nexus 2360 (Wayback capture 2026-06-01)"
  - "Skyrim at War Reborn, Nexus 79932 (Wayback capture 2026-06-01)"
  - "TCRF: The Elder Scrolls V: Skyrim/Civil War (fetched 2026-09-05)"
  - "UESP Skyrim:Civil War (fetched 2026-09-05)"
  - "Wayback CDX history for original CWO, Nexus LE 37216"
  - "r/skyrimmods 16gai2y 'Open civil war worth it?' (Wayback old.reddit capture)"
topic: "Skyrim Civil War expansion mod landscape — health, licenses, architectures, and build-on vs. inspire-only verdicts for a Chronicle group/faction-scale layer"
status: filed
---

# Skyrim Civil War Mod Landscape — Build-On vs. Inspire-Only

Survey of the Skyrim Civil War mod ecosystem (Open Civil War, Organic
Factions / Extension, Civil War Overhaul and its Redux successor, and the
ambient-war tier) plus the documented vanilla internals, answering: which of
these, if any, should Chronicle's prospective group/faction-scale layer treat
as a foundation, and which are inspiration only. This extends report
[19-skyrim-quest-injection-machinery.md](19-skyrim-quest-injection-machinery.md)
(which covered OCW's Story Manager bottlenecks and Organic Factions'
Story-Manager bypass at the mechanism level) with current health, license,
and reception data, and report
[15-skyrim-social-reactivity-mods.md](15-skyrim-social-reactivity-mods.md)'s
reactivity table on the faction-scale axis.

## 1. Open Civil War (simtam)

**Health.** Alive but sporadic. SSE page
([Nexus 11076](https://www.nexusmods.com/skyrimspecialedition/mods/11076)) is
at version 2.8.0, last updated 2023-06-02; the
[LE page](https://www.nexusmods.com/skyrim/mods/82128) shows version 2.8.0
last updated **2024-10-15** — so the mod still received file updates as of
late 2024. simtam maintains a public Google-Sheets issue tracker linked from
his own project page, [palimptes.dev/ocw](https://www.palimptes.dev/ocw),
where he describes OCW as "a research project, hacked in a janky way in the
hope of uncovering causes of bugs in the Skyrim civil war quest line." A
third-party patch ecosystem exists and is recent: schofida's *Serious Civil
War Defense for OCW* ([bethesda.net, Oct
2024](https://creations.bethesda.net/en/skyrim/details/a2946cba-0f33-432e-a05a-11eab949316d/Serious_Civil_War_Defense_for_OCW))
"edits numerous scripts and quest fragments including those for CWAttackCity,
CWSiege"; the SSE page lists 19 "mods using this mod" and translations in 8
languages.

**License / source status — premise not verifiable.** The task brief asserted
a source-available repo; I could not find one. GitHub repository search
(`opencivilwar`, `open civil war`, `OCW skyrim`, `topic:skyrim civil`)
returns nothing relevant; the GitHub user `simtam` has **zero public repos**;
GitLab project search is negative; Wayback CDX for `github.com/KkMX/OpenCivilWar*`
has **no captures** (the `kkmx` GitHub user that does exist is an unrelated
account). palimptes.dev contains no license statement. The Nexus permissions
text is JS-gated and could not be extracted; a permissions screenshot album
([imgur.com/a/mcUCfiF](https://imgur.com/a/mcUCfiF)) exists but is
image-only. What *is* verifiable: script source historically ships inside the
mod's BSA, and the extensive patch/translation ecosystem implies
permission-by-request is granted in practice. **Default legal position:
all-rights-reserved; do not vendor or hard-depend without written
permission.** simtam also warns OCW "is not recommended for mod merging...
some OCW scripts have hardcoded file names and form id reference numbers"
([palimptes.dev/ocw](https://www.palimptes.dev/ocw)) — brittle as a base for
another plugin.

**Architecture** (from the [SSE mod
page](https://www.nexusmods.com/skyrimspecialedition/mods/11076) and
[OCW_Readme.txt](https://file-metadata.nexusmods.com/file/nexus-readmes/1704/11076/OCW_Readme.txt)):

- A turn-based macro layer driven by the civil war map tables. One "turn"
  elapses per in-game day or per map-table change; the enemy faction moves
  first, then yours, modeled on Dice Wars. Three modes: **Fortuna**
  (randomized odds, default), **Standard** (odds derived from the map
  position; the war progresses without the player), **Wargamer** (manual
  turn-stepping, Risk-like; doubles as a quest-state repair tool).
- Map state: per-flag troop strength 0–6 = number of d6 rolled in battle
  resolution; recruitment per turn = 2 + controlled flags; total strength cap
  = 20 + controlled flags; a faction that loses all troops regains its
  capital with 3 strength. Battle odds = attacker dice vs. defender dice
  (+player rank bonus up to 7 on your side, +difficulty 1–6 on the enemy).
- Player-facing verbs: request hold battles via Rikke/Galmar at military
  camps; **off-screen battle resolution** ("tend the wounded") resolves with
  the same odds model and prints the dice; enemy counter-invasions siege a
  hold for up to 3 turns and auto-resolve if ignored; "upheaval" events flip
  a hold whose flags are all enemy-colored, *before Whiterun*, without any
  battle; enemy feigned withdrawals produce ambushes; cleared rogue forts
  halve their map strength.
- Execution: restores the cut city battles via the vanilla `CWAttackCity` /
  `CWSiege` machinery after the (unchanged) Battle of Whiterun; hold
  garrison/government swaps deliberately **wait until the player leaves and
  the cells unload** (the mod's own documented quirk), and it recommends the
  vanilla debug quest `mq302test` as the emergency force-flip.
- Documented incompatibilities: CWO / CWO Redux, Skyrim Civil War Commanders
  family, For the Stormcloak's, Holds The City Overhaul; compatible with Open
  Cities (which closes cities during battles). Uninstalling mid-war can
  strand the vanilla questline.

**Chronicle relevance.** OCW's Standard mode is the closest existing analog
of Chronicle's own doctrine: an abstract, tick-driven strategic layer whose
state lives outside the quest structure, dropping into engine quests only
for the discrete "city battle" / "hold flip" presentation moments, and even
offering fully off-screen resolution. Report 19's Story Manager bottleneck
warning stands; OCW's own workaround (defer swaps until cell unload) is the
same conclusion reached independently.

## 2. Organic Factions + Organic Factions Extension (EtherealCoder / "Ether Dynamics")

**Identity and health.** The framework, *SSE Organic Factions*
([Nexus 10289](https://www.nexusmods.com/skyrimspecialedition/mods/10289);
[Wayback capture](http://web.archive.org/web/20260424165950/https://www.nexusmods.com/skyrimspecialedition/mods/10289);
LE is Nexus 76803), is by **Ether Dynamics** — the renamed account of
EtherealCoder, who authored the *Organic Factions Extension*
([Nexus 25471](https://www.nexusmods.com/skyrimspecialedition/mods/25471),
v1.08; [LE 82607](https://www.nexusmods.com/skyrim/mods/82607)). Both were
last updated **2022-09-28**; the Extension's page references an author
hiatus. No updates in ~4 years as of this filing. No SKSE dependency in any
component; the framework requires the author's own *Enhanced AI Framework*
ESM.

**License.** Explicit custom terms on both pages: users may use the materials
**if and only if** they (1) give full credit and link back, and (2) **share
the source code of any new features they design that reference any piece of
the material**, with the same obligation cascading to downstream authors. The
framework ships as a master file precisely so users can "look at the guts."
This is a viral share-source clause, not an OSI license — usable for study,
awkward as a dependency (any Chronicle feature referencing it would inherit a
source-sharing obligation to the modding public).

**Architecture** (framework page + Extension page):

- Factions are persistent-actor groups that "level up, expand territory,
  secure resources, and be slain completely independent of the player."
  Leaders level independently, gaining unique abilities; followers accrue in
  combat-role-balanced compositions ("similar to how teams pick roles in
  competitive games"); wounded members heal over time.
- **Resource providers**: alchemists/armorers can be "wooed" into supplying a
  faction; goods physically travel and can be intercepted by the player,
  depriving the faction — an actual logistics loop.
- **MOBA-style "jungle" camps** that factions capture for support troops;
  patrols that block the player's fast travel into strongholds until beaten
  back; **automatic background conflict resolution** when two factions
  contest an area, without player presence.
- Named-NPC permanence: unique leaders "stay dead"; succession rules replace
  them on timers (e.g., Lost Valley's Barbarian → Sorceress leader chain,
  ~10–30 days; Mistwatch captains replaced after kills; killing 3+ captains
  triggers assassination contracts on the player in Windhelm).
- The Extension includes a **Civil War module**: two organic civil-war camps
  in the Reach that patrol/ambush, attempt to overrun each other (commander
  death stops reinforcement for 25+ days), with soldiers having "a
  significant % chance to be killed in random encounters while performing
  their duties" — persistent attrition outside the questline.
- A *Markarth Siege Sub-Faction* (Forsworn strike force camping outside
  Markarth, reinforced by giants/mammoths, attacking gate guards while
  sparing civilians) is the most Kenshi-world-state-like shipped content in
  the entire ecosystem.

**Script-load / save-bloat evidence — thin.** I could not retrieve a primary
source quantifying script load or save bloat (Reddit is rate-limited/blocked
to this session; see Evidence gaps). Verifiable signals: the framework added
an **"Organic Faction Lite"** lightweight version to its own main file — an
author-acknowledged performance tier; upgrades require a **new game** ("New
Game Required on Upgrade, incompatible with SSE Organic Factions Extension
v1.07"), i.e., its state is deeply save-coupled; report 19's source credited
the design as "far more resilient against script fatigue" than Story-Manager-
driven approaches precisely because it never triggers Story Manager cascades.
Treat "script-heavy/save-bloat-prone" as plausible-but-undocumented in this
pass.

**Reception.** ~500 Nexus posts each on framework and Extension; conceptually
admired (nothing else ships independent faction growth), but the 2022 dormancy
and new-game-required upgrades have kept it out of the big curated lists.
Thin evidence; see Evidence gaps.

## 3. Civil War Overhaul (ApolloDown) and successors

**Original CWO.** Released June 2013 on LE
([Nexus 37216](https://www.nexusmods.com/skyrim/mods/37216); announcement
write-up at [tes-skyrim.livejournal.com](https://tes-skyrim.livejournal.com/135548.html)).
Wayback CDX shows the page live (HTTP 200) from Dec 2013 through mid-2017,
**"hidden" by Dec 2018**, and serving "Mod unavailable" by Sep 2019
([example capture](http://web.archive.org/web/20190922024407/http://www.nexusmods.com/skyrim/mods/37216)).
ApolloDown never published a formal departure rationale that survives;
community accounts attribute the pull to burnout/community friction around
2016–2017 (he warned even in the mod description: "One day I may just drop
development entirely. Beware."). **Treat the "why" as community-reconstructed,
not author-confirmed.** His own description — preserved verbatim inside the
successor's page — remains the best primary document of both the mod and the
vanilla machinery (including his "Skyrim Sorcery" taxonomy: Script Lag,
Script Hiccup, Unexpected Value).

**Content worth salvaging as inspiration** (from the preserved
[description](https://www.nexusmods.com/skyrimspecialedition/mods/37906)):

- **Losable war.** Vanilla battles are functionally unwinnable for the enemy;
  CWO made every battle losable, made losing flip you to defense, and shipped
  a designed "epic loss" ending. "The war is no longer linear, it's dynamic
  on a very basic level."
- **Hold hostility + disguise.** After Whiterun, guards in enemy holds attack
  you on sight unless you wear the enemy's armor ("Greasers vs. Jocks" /
  "Denise, that outfit is so last month").
- **MURDERMAYHEM scoreboard**: soldier deaths on each side are tracked
  *everywhere, even outside battles*, and applied to battle reinforcements —
  the only shipped system where ambient player violence feeds the war state.
- **Spies/traitors** ("Eggs Benedict Arnold") in cities and camps who pick
  assassination targets — including the player once side-locked.
- **"Spanish Inquisition"**: random siege squads attacking a town you own
  while you go about your business.
- Restored missions beyond vanilla's three (of twelve designed); Season
  Unending side-switching; dragons crashing sieges; commanders (Ulfric/
  Tullius) at front lines; unique faction reward items.

**Successor: Civil War Overhaul Redux (CWORR), schofida.** Not a patch — a
ground-up rebuild "sticking to the vision of the original mod"
([README](https://github.com/schofida/CWORR/blob/main/README.md)).
Decisive facts for the build-on question:

- **License: MIT** (`LICENSE` in repo, copyright 2021 schofida) — the only
  legally clean code in this entire landscape. (Note: it is a rebuild of
  ApolloDown's design; the MIT covers schofida's implementation. No explicit
  ApolloDown blessing is documented in the repo — see Evidence gaps.)
- **Actively maintained**: latest commit **2026-09-04** (day before filing);
  releases through v1.1.1a (2025-07-30); 17 open issues, including
  *CWLockDuringSiegeScript papyrus spam* (#171, 2026-07), *Battle for
  Windhelm Won't Complete* (#158), *Rift status reverted after victory*
  (#166) — i.e., hold-swap and siege-script fragility persists even in the
  maintained rebuild, exactly report 19's risk class.
- Architecture: explicitly reuses the dormant vanilla **`CWCampaign` as the
  quest manager**, tracking campaign "phases" (configurable count of radiant
  missions before each city siege, separately for offense/defense); defense
  missions arrive by Courier; restores 6 additional cut missions with their
  cut voiced dialogue; all 9 cities siege-eligible; troop counts fed by
  radiant-mission success and hold adjacency; MCM configurability throughout;
  zEdit patcher for troop lists; extensive compat-patch tree in-repo
  (patches for Skyrim at War, Second Great War, Civil War Commanders, etc.).
- Requires new game; SKSE required.

## 4. Ambient-war tier

| Mod | Mechanism | State/persistence | Performance reputation |
|---|---|---|---|
| **Immersive Patrols** (Scrabbulor; [SSE 718](https://www.nexusmods.com/skyrimspecialedition/mods/718); LE 12977) | **Scriptless**: persistent patrol refs (~5 NPCs) with AI packages; 7 fixed large battles (~40 NPCs) with fort-capture behavior; allegiance hostility via custom factions | Fully persistent; battles are placed encounters; fort capture changes ownership flags | Best-in-class stability ("无脚本 / scriptless, free install/uninstall" per [Chinese mod-community survey](https://tieba.baidu.com/p/7038674725)); ~5.4M DLs (secondary listicle figure, unverified) |
| **WARZONES 2015 / Civil Unrest** (MyGoodEye; [SSE 2360](http://web.archive.org/web/20260601200101/https://www.nexusmods.com/skyrimspecialedition/mods/2360)) | **Spawn-based**: hundreds of spawn points, day/night-aware random encounters, "spawn-o-meter" spawn count, 24h WZ cooldowns, MCM/console tuning | Stateless spectacle; no ownership or memory | LE original notorious for crashes/save issues — ApolloDown's own FAQ: "Is this mod like Warzones? Because I liked warzones. Until it crashed my game. Like, a lot." SSE version reworked scripts/placement; author himself warns to moderate expectations |
| **Skyrim at War Reborn** (Patrick97030; [SSE 79932](http://web.archive.org/web/20260601164008/https://www.nexusmods.com/skyrimspecialedition/mods/79932), 2022; AE port [bethesda.net, Jan 2023](https://mods.bethesda.net/de/skyrim/mod-detail/4310675)) | **Persistent patrols, not script-spawned**: 200+ patrols / 2,000+ soldiers using caravan-style persistent markers, all marching simultaneously, respawnable; 6 campaign routes Solitude↔Windhelm; hold capture swaps the hold's patrol faction; unit roles (scouts/squads/armies), officers granting buffs, formations/shield walls, retreat-to-regroup logic; player command of 7–76 soldiers; Forsworn third front in the Reach | Killing soldiers visibly depletes patrols until respawn; "you may on very rare occasions run into the same patrol you stumbled on a while back" | Needs Actor Limit Fix ("too many NPCs → float/ignore combat"); patrols can spawn off-road; heaviest of the three |

Newer entries through filing date are **patches, not new systems**:
schofida's *Serious Civil War* series (Defense for OCW, Consequences, Final
Sieges, Fort Commanders — 2023–2024) extends OCW/CWORR battles, and CWORR
ships compat patches for Skyrim at War and Second Great War. No new
ambient-war mod of note surfaced 2024–2026.

**What players credit for "the war feels real"** (synthesized from the mod
pages' own design notes and the reception threads below): *persistence*
(meeting the same patrol later — SaW's explicit design goal), *emergence
from geography* (Dragon Bridge as natural bottleneck producing big battles —
SaW), *the war moving without you* (OCW upheavals/counter-invasions), and
*stakes* (losable battles, CWORR). Spawn spectacle alone (Warzones) reads as
a theme park.

## 5. Vanilla civil war internals, as documented

Primary sources: [UESP Skyrim:Civil War](https://en.uesp.net/wiki/Skyrim:Civil_War),
[TCRF Civil War sub-page](https://tcrf.net/The_Elder_Scrolls_V:_Skyrim/Civil_War),
and the preserved CWO/CWORR descriptions.

**Quest structure.** `CW` (parent) → `CWCampaign` (the quest manager
Bethesda built for a fully dynamic campaign, used by CWORR) → missions
`CWMission00`–`CWMission11` (only 03 "A False Front", 04 "Rescue from Fort
X", 07 "Compelling Tribute" shipped) → battles: `CWFortSiegeFort` (fort
battles), `CWFortSiegeCapital` (minor-capital sieges, dormant),
`CWSiege` (major sieges: Whiterun/Solitude/Windhelm only in shipping game),
`CWAttackCity` (jarl surrender scenes), `CWEscapeCity` (dormant), `CWAllies`
(dormant). A Bethesda developer's note at the top of `CWScript` warns
modders: "There's a lot of obsolete stuff in here from previous iterations
where it was more dynamic and free form... a lot of obsolete and deprecated
complexity" (TCRF).

**How hold ownership actually changes** (UESP + CWO console-command
documentation): jarl/steward/housecarl exile to the enemy capital and
replacement (with disposition changes); garrison swap driven by `CWScript`
functions; crime-faction swap that auto-clears the player's bounty in the
hold; civil-war map flag recoloring; per-hold military camps on the side that
doesn't hold it; thaneship reset opportunities. Documented fragility:
`GetMyEditorLocationHoldLocation` and
`DetermineAndSetCrimeFactionForSoldierActor` used `GetEditorLocation` on up
to 64 soldier aliases per battle; it "apparently returns a NONE sometimes,"
aborting garrison resets mid-loop — thousands of Papyrus errors (USSEP 2.0.5
fix); fort garrisons failing to repopulate (USSEP 1.2.7); siege scenes
disruptible by talking to soldiers (USSEP 2.0.4); the `mq302test` debug quest
as the unreliable force-flip. **The hold-swap is the single most
bug-accruing seam in the vanilla game** — every fix above is a USSEP entry.

**Cut content, the full list** (TCRF, verified against CWO/CWORR claims):

- Twelve radiant missions given in randomized pairs, with a rank-scaled
  **salary system** (Ulfric lets you donate pay to the cause); missions
  include scout-killing (00), settlement liberation with a soldier squad
  (01), resource sabotage (02 — mills/smelters still flagged in settlements),
  courier interception with horse markers (03), prison rescue (04), officer
  assassination (05), turncoat recruitment with a 16-NPC firefight (06),
  steward blackmail (07), **the giant Goldar and the painted cow** (08),
  war-plan theft (09), civilian sympathizer recruitment (10 — `CWAllies`,
  per-hold "Can show up at battles in this hold" factions, `TraitSympathizer*`
  keywords still on Riverwood NPCs), and the Orc vision-quest (11).
- City sieges in **all nine capitals**, with barricades still present but
  never enabled; full Jarl-showdown scenes for Markarth and Riften (including
  Galmar executing Ondolemar — whose coffin still appears in-game after a
  Stormcloak Markarth); **city escape sequences** (defending player leads the
  Jarl out through secret doors that exist but never activate).
- Removed troops: Stormcloak Mage, Imperial Wizard, Imperial Officer, the
  `FemaleSoldier` voicetype; the possibility of losing battles; a non-linear
  final battle in any hold.

## 6. Reception synthesis — alive vs. disappointing, and reactivity beyond the questline

**Disappointing, per players and mod authors alike**: the vanilla war is a
"facade" (ApolloDown's preserved essay: twelve-mission radiant structure
"hardcoded... to ONLY allow a very limited set of quests that operated
entirely linearly"); battles are unwinnable for the enemy; and after the war
ends the world doesn't notice — UESP documents that "a lot of people will
discuss it as if it is ongoing" post-completion and that Dark Brotherhood
war-related content never changes.

**Feels alive, per the same sources**: persistent patrols you re-encounter
(SaW); battles emerging from geography and patrol collisions rather than
scripts; the war advancing without player input (OCW upheavals, counter-
invasions, auto-resolving sieges); consequences for your allegiance outside
battles (CWORR hold hostility, disguises, spies); losability. OCW's
reception is "stable if you give scripts time" — one multi-year player
reports a level-85 save running OCW + the Serious Civil War series + Second
Great War, with the caveat that "quest completion after a battle can be
delayed... because the scripts need their time to run"
([r/skyrimmods 16gai2y via Wayback](http://web.archive.org/web/2023id_/https://old.reddit.com/r/skyrimmods/comments/16gai2y/open_civil_war_worth_it/)).

**Does any mod make the war respond to player action outside the questline?**
Partially, and only mechanically:

- CWORR/CWO: MURDERMAYHEM (every soldier death anywhere weakens future
  reinforcements); spies who hunt the player; Spanish Inquisition town
  sieges; dragons at sieges. This is the strongest shipped answer.
- OCW: clearing rogue forts halves their strategic strength; your rank and
  mission record feed battle odds.
- Skyrim at War: killing patrol soldiers depletes the roads until respawn.
- Organic Factions Extension: its Reach civil-war camps suffer persistent
  attrition (commanders stay dead 25+ days) from ambient fights.

**Nobody ships war state reacting to *political* acts** — no mod ties hold
allegiance, morale, or invasion targets to assassinations of named
characters, rumors, or economic disruption. The war-state/plot-coupling axis
is empty: exactly the niche Chronicle's belief/provenance machinery would
fill.

## Evidence gaps

1. **OCW license/source repo — unverifiable.** The brief's "source-available
   repo" does not exist at any locatable address (GitHub/GitLab/Wayback
   searches documented in §1). Either it was removed/renamed or the premise
   was mistaken. Actual Nexus permission terms are JS-gated; the imgur perms
   album is image-only and was not OCR'd. **Do not assume any reuse rights
   beyond study.**
2. **ApolloDown's reasons for pulling CWO** — hidden-by-Dec-2018 is wayback-
   verified; the *why* is community lore only.
3. **ApolloDown's stance on CWORR** — no documented permission/blessing found
   in the CWORR repo or page; the MIT license is schofida's on his own
   rebuild.
4. **Organic Factions script-load/save-bloat quantification** — Reddit was
   inaccessible to this session (pullpush 429, reddit 302/403); only
   circumstantial signals (Lite version, new-game-required upgrades) are
   cited. A follow-up pass with browser tooling could pull the Nexus Posts/
   Bugs tabs (500+ posts each).
5. **Organic Factions reception** beyond post counts — same access problem.
6. **Immersive Patrols download figure** (~5.4M) is from a third-party
   listicle, not Nexus directly.
7. **Skyrim at War Reborn current version/date** — the Nexus page is 403 to
   this session; the 2026-06 Wayback capture was used; exact version numbers
   not extracted.

## Build-on vs. inspire-only verdicts, ranked

Ranked by usefulness to Chronicle given its settled doctrine (external sim is
the sole source of truth; the engine only executes; report 19's
Story-Manager-bypass rule). Because of that doctrine, **no mod here is a
runtime dependency candidate** — "build-on" below means legally+technically
sound to reuse as code/reference/foundation.

1. **CWORR (schofida) — BUILD-ON (as reference implementation), inspire for
   design.** MIT, source on GitHub, maintained *this week*, and a working
   demonstration of how far the vanilla `CWCampaign`/siege skeleton can be
   stretched. If Chronicle ever stages on-screen sieges, CWORR's source is
   the legally clean place to copy staging patterns from. Its open issues
   (papyrus spam, stuck sieges, hold-status regressions) double as the
   risk map for driving that machinery. Salvage: losable-war structure,
   hold hostility + disguise, MURDERMAYHEM (ambient kills → war state),
   spies, Courier-dispatched defense missions.
2. **Vanilla civil-war machinery itself — BUILD-ON (as execution target).**
   The actual foundation Chronicle would drive: `CWCampaign` phases,
   `CWFortSiegeCapital`/`CWSiege`/`CWAttackCity` for presentation, the
   documented hold-swap seam (jarl/garrison/crime-faction/flag) for the
   rare flip moments. USSEP's fix history tells you precisely where it
   breaks — drive it sparingly, off the Story Manager, exactly as report 19
   concluded. TCRF's cut-content inventory is the free design document:
   missions 00–11, CWAllies, salary, escape sequences.
3. **Open Civil War — INSPIRE-ONLY (but the closest architectural analog).**
   Its Standard mode is Chronicle's own pattern — an abstract turn-ticked
   strategic layer, off-screen resolution as a first-class path, engine
   quests only for presentation, swaps deferred until cell unload. Study it
   freely; depend on it never (license unverifiable →
   all-rights-reserved; hardcoded FormIDs; author's own "janky research
   project" framing; sporadic maintenance).
4. **Organic Factions / Extension — INSPIRE-ONLY (best faction-sim design in
   the ecosystem).** Resource providers with interceptable logistics,
   succession chains, background conflict resolution, persistent-actor
   attrition, the Markarth siege sub-faction — the most Kenshi-like shipped
   content and the best proof that players tolerate off-screen faction
   simulation. But: dormant since 2022, viral share-source license,
   new-game-required save coupling. Take the design, not the code.
5. **Skyrim at War Reborn — INSPIRE-ONLY (persistence validation).**
   Demonstrates the single biggest "war feels real" lever — persistent,
   re-encounterable patrol actors — and its cost (2,000 live NPCs, Actor
   Limit Fix required). Chronicle's sim produces *reasons* for patrols;
   SaW proves the presentation value of keeping them persistent.
6. **Immersive Patrols — INSPIRE-ONLY (presentation-layer minimalism).**
   Proof that a scriptless, zero-state mod (packages + custom factions)
   carries most of the ambient-war feeling at near-zero risk — the cheap
   floor of this design space.
7. **WARZONES — NEGATIVE EXAMPLE.** Spawn spectacle without state: the
   community's crash/save-bloat poster child, and the clearest illustration
   of why "more NPCs fighting" is not a war. Useful only as the boundary
   case for what Chronicle's provenance-driven approach must not become.

**Bottom line for the group/faction-scale layer:** the field's two opposed
architectures (report 19) both still stand, and this pass adds the legal
map. Chronicle should treat **vanilla's dormant CWCampaign/siege skeleton
(driven sparingly, Story-Manager-bypassed) as the execution surface**, use
**CWORR's MIT source as the staging reference**, and mine **OCW's turn model
and Organic Factions' logistics/succession design** for the external sim's
own mechanics. The empty niche — war state coupled to political acts,
rumors, and assassinations rather than to quest stages — is precisely the
one Chronicle's belief/provenance architecture is built to occupy.
