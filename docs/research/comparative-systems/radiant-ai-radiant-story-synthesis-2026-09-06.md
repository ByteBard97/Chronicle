# Radiant AI / Radiant Story: Synthesized Verdict (merging 3 independent reports — Gemini, Claude, Kimi)

Synthesis of three independent gap-research passes
(`gap-research-raw-agent-reports-2026-09-06/radiant-ai-gemini.md`,
`radiant-ai-claude.md`, `radiant-ai-kimi.md`) investigating Bethesda's own
Radiant AI/Radiant Story as actually shipped — the single most-flagged gap
across this project's whole comparative-systems effort (3 of 5 agents in
the mechanics-brainstorm synthesis independently named it the most
under-researched, most-actionable topic).

## TL;DR

**All three reports converge on the same verdict, and Kimi's pass — the
most rigorously sourced of the three — sharpens it into two named,
specific divergences rather than a single vague caveat: Radiant Story is
genuinely a storylet-role-casting engine at the data level, shipped,
extensible, and Chronicle should hook it rather than rebuild it.** The
casting/precondition-gating layer (pick a real NPC, pick a real location,
gate on real state, cast into a reusable template) is already shipped,
battle-tested across three titles. What's missing — narrative-quality
selection intelligence and any memory/provenance model — is exactly
Chronicle's differentiator, not something it's competing with the engine
to build. Kimi's own framing is the sharpest one-line summary any of the
three reports produced: **"Bethesda built a memoryless director; Chronicle
is a director-less memory."**

The smallest integration surface all three reports independently land on:
`SendStoryEvent` (Chronicle drives the engine with its own picks) +
`ForceRefTo`/`ForceRefIfEmpty` (Chronicle casts or biases roles) +
`OnStory*` events (observation) — all vanilla Papyrus; SKSE is a
nice-to-have for richer observation, not a hard dependency.

**Two things to flag before treating either as settled**: (1) the Oblivion
failure-mode anecdote disagreement (§3) is now resolved with high
confidence — Kimi's independent audit strongly corroborates Claude's
skeptical reading, with far more granular sourcing than either prior
report had; (2) a genuine, unresolved **citation venue discrepancy** on
the academic storylet paper both Claude and Kimi cite as their strongest
evidence for the core claim — see §2.1.

## 1. The node/condition system: how a live NPC gets cast at runtime

All three reports agree on the core mechanism in detail. A **Reference
Alias** is an abstract role container; the Story Manager fills it at
quest start via one of several fill types. Claude's report gives a
CK-wiki-sourced six-type enumeration (Specific Reference, Unique Actor,
Location Alias Reference, External Alias Reference, Create Reference to
Object, Find Matching Reference); Gemini's five-type table folds Unique
Actor into Specific Reference; **Kimi's report independently arrives at a
near-identical seven-type list** (adding Forced Reference as its own
category, sourced directly to the UESP QUST mod-file-format reference and
the TES Alliance quest-authoring workshop) — three independently-researched
enumerations converging on the same mechanism is a strong confidence
signal on this specific point.

**Find Matching Reference is the dynamic one all three reports center
on** — the Story Manager searches the world for an entity matching
author-defined boolean **Match Conditions** and binds it to the alias.
All three agree on the critical constraint: the search is restricted to
either the player's **Loaded Area** or the global pool of **Persistent
References/Unique Actors** — an NPC not flagged persistent/unique
effectively doesn't exist to a Find Matching Reference query once their
cell unloads. **Kimi adds a location-side detail neither Gemini nor Claude
covered**: `Find Location`'s selection is deliberately **exploration-biased**
— the engine tracks per-location discovered/cleared state and prefers
undiscovered targets, sourced directly to UESP's community-maintained
Radiant page, which also documents concrete cast-pool sizes for the
broadest templates ("Fetch Me That Book!"/"Shalidor's Insights": 140+
dungeons with a boss chest; the Companions' "Hired Muscle": 400+ citizens;
"Rescue Mission": 50+ dungeons). Kimi frames the consequence for Chronicle
directly: **registering Chronicle NPCs with the right factions, keywords,
and home locations makes them castable by vanilla radiant machinery with
zero patching of vanilla quests** — mod-added NPCs and DLC locations are
documented (UESP talk page) to already turn up as radiant targets with no
special integration work at all.

All three reports also agree: aliases fill in an **ordered list at quest
start**, later aliases can depend on earlier ones, and non-optional
aliases that can't fill **prevent the quest from starting at all**. Claude
and Kimi both independently name a **"Force Into Alias When Filled"** /
prioritized-fallback pattern (try NPC_A, else NPC_B) that Gemini doesn't
cover. The **Story Manager** itself is a decision tree of Branch/Quest
Nodes evaluating typed events (Change Location, Kill Actor, etc.) carrying
Event Data — all three describe this identically, and Kimi adds a
concrete worked example from the CK's own documentation (the item-brawl
world interaction: a dropped item cast as "prize," two condition-matched
NPCs cast as "brawlers," optional bystanders and a guard cast as
"chorus") that makes the storylet-with-casting framing unusually concrete.

## 2. Is this genuinely "storylet role-casting," or only superficial?

**All three reports independently answer yes, genuinely the same
mechanism — now a three-way convergence, not a two-way one, on the single
most decision-relevant question in this whole synthesis.**

- **Gemini's framing**: "Radiant Story is genuinely a Storylet role-casting
  system, but one that is severely burdened by the absolute necessity of
  3D physical embodiment and real-time AI package evaluation" — same
  mechanism, harder in practice because cast actors must physically travel
  through geometry, can be interrupted/killed en route, and have their
  baseline schedule hijacked once cast.
- **Claude's framing grounds the comparison in Kreminski & Wardrip-Fruin's
  "parametrized storylet" definition**, quoted verbatim, and calls Radiant
  Story's Find Matching Reference "a near-verbatim description" of it.
- **Kimi's framing is independently sourced and, in a genuinely useful way,
  goes further than either**: rather than citing the academic paper alone,
  Kimi traces the *design lineage itself* — Emily Short's retrospective
  application of the term "storylets with casting" to King of Dragon Pass,
  **corroborated by KoDP's own creator David Dunham agreeing publicly**
  ("Emily's categorization seems pretty accurate... they're chock full of
  assignable roles," from Dunham's own KoDP blog). Kimi then does a
  mechanism-by-mechanism mapping table (KoDP scene ↔ Story Manager quest
  node; OSL selector functions ↔ alias fill types with match conditions;
  "role required or scene doesn't run" ↔ non-Optional aliases blocking
  quest start; post-scene effects ↔ quest stages/fragments/packages) —
  this is the most granular version of the claim any of the three reports
  produces, and it's corroborated by a primary source (the KoDP creator's
  own agreement with the categorization) neither Gemini nor Claude cite.

### 2.1 A citation discrepancy, flagged rather than silently resolved

**Claude cites the academic storylet paper as Kreminski & Wardrip-Fruin,
*Sketching a Map of the Storylets Design Space*, ICIDS 2018 (LNCS 11318,
p.161). Kimi cites the same paper (same title, same authors) as FDG 2018.**
These are two different, real academic venues (International Conference
on Interactive Digital Storytelling vs. Foundations of Digital Games) —
one of the two reports has the venue wrong, or the paper was
presented/published at both (a workshop-then-conference pattern is not
unheard of, but neither report flags this itself). **This needs a direct
five-minute check of the paper's actual publication record before citing
the venue in any public-facing document** — the paper's existence and its
"parametrized storylet" content are corroborated by both reports
independently, so the underlying claim is not in doubt, only which
conference proceedings it appeared in.

### 2.2 Kimi's sharpest original contribution: two named, specific divergences

Where Gemini and Claude both note (in slightly different words) that
Radiant Story's casting is "one-shot at quest start, not continuously
re-evaluated," **Kimi goes substantially further and identifies two
distinct, precisely-named architectural gaps**, each with its own
transferability implication for Chronicle:

1. **Candidate selection is random-uniform, not scored.** KoDP's OSL
   selector functions are *best-fit* — `BestRelations(KnownClans)`,
   `StrongestMilitary(ClansWithPositiveAttitude(NeighboringClans))` — they
   rank candidates by a dramatic criterion and cast the optimum. Radiant
   Story's Find Matching Reference filters by boolean conditions and then
   **picks randomly** (or by distance, if Closest is set) — there is no
   native "most dramatically appropriate" scoring at all. Kimi's
   implication for Chronicle: this is exactly where Chronicle's belief
   state becomes load-bearing — conditions can query globals/quest stages
   Chronicle's own scripts maintain, letting Chronicle's epistemology
   steer casting *through the existing condition language* rather than
   requiring the engine's selection mechanism to be replaced.
2. **Template arbitration is structural, not salience-based.** Storylet
   theory (Kimi cites Emily Short's "Beyond Branching" essay specifically)
   distinguishes quality-based selection (player-visible options) from
   **salience-based** selection, where the system itself judges which
   content element is "most applicable at the moment." The Story
   Manager's arbitration is tree order plus first-match-wins, with Shares
   Event/Num-quests-to-start as coarse multiplicity controls — there is no
   dramatic-weight comparison between eligible templates. **Kimi cites a
   primary source neither other report has**: Bruce Nesmith's own 2026
   retrospective interview admitting the absence was felt internally —
   "we went too far with radiant stories in the process of development and
   the game felt flat, because we weren't using it as a tool to create the
   best stories."

Kimi's own verdict on this pair, worth quoting directly since it's the
sharpest formulation across all three reports: **"same genus, different
selection pressure. Chronicle should cite Radiant Story as a first-class
(and uniquely in-engine) instance of storylet-with-casting, while flagging
best-fit scoring and salience arbitration as the two features it must
supply itself — and noting that both are injectable through the condition
system rather than requiring the mechanism to be replaced."**

**Verdict on this section, now three-way confirmed and more precisely
specified than before: genuinely the same mechanism, not superficial.**
Casting-and-precondition-gating is shipped and proven; Chronicle's actual
value-add — narrative-quality/best-fit selection, salience-based
arbitration between eligible templates, and any memory/provenance model —
is precisely what the engine was deliberately built without, and (per
Kimi's specific finding) is injectable *through* the existing condition
system rather than requiring a parallel casting mechanism.

## 3. Documented failure modes: resolved with high confidence, not just flagged

All three reports cite overlapping Oblivion-era Radiant AI failure
anecdotes (the "starving guard" lawlessness loop, the skooma-merchant
murder cascade, a broom-and-rake tool-swap murder, a minotaur killing the
unicorn it was assigned to protect, a Skull of Corruption clone massacre),
all correctly distinguishing this system (Oblivion's need/schedule engine)
from Radiant Story (Skyrim/FO4's quest-casting engine covered above) —
that distinction is solid across all three.

**Gemini's report presented all five anecdotes as roughly equally
documented, citing a single source (Paavo Huhtala's blog, "What was
Radiant AI, anyway?") without differentiating which stories that source
actually corroborates versus debunks. Claude's report read the same piece
more skeptically and found only the skooma-merchant story soundly
attributed. Kimi's independent pass — citing the same underlying source
(`blog.paavo.me/radiant-ai`, referred to in Kimi's report by the blog's
URL-slug "paavohtl" rather than the author's name, same person, same
piece) — goes considerably further than either prior report and produces
a full six-row legend-by-legend audit table, the most granular treatment
of this question across the whole synthesis:**

| Legend | Kimi's traced source | Kimi's verdict |
|---|---|---|
| Skooma-den addicts kill dealer Nordinor | Emil Pagliarulo himself, official fan interview | **Real (pre-release testing)**; impossible in the final game as shipped/configured, though the addicts are set up to seek skooma in the market |
| Tester drops Skull of Corruption; NPC clones player; clone massacres NPCs | Unnamed Bethesda developer, PC Zone (April 2006) | **True — and reproducible in the 2025 remaster** (new detail neither Gemini nor Claude had) |
| Raker/sweeper swapped-tools murder | Only the anonymous TTLG-era fan summary | **Unsourced; mechanically plausible** |
| Hungry guard wanders off, town left unguarded, villagers loot | Only the fan summary | **Very likely fabricated** — no hunger variable exists in the shipped game at all, NPCs cannot be arrested, no "town protected?" check exists |
| NPC leaves mid-fight to buy a dagger, returns | Todd Howard, Play Magazine (April 2005) | **Developer-sourced but not reproducible in the final game** — NPCs have no economy interaction and cannot locate items in unloaded cells |
| NPCs steal from the player; shops emptied by NPC shoppers | Game Informer Oct 2004 cover story | **False as shipped** — NPCs "cannot buy food, or anything else"; stealing from the player was deliberately disabled pre-release per Pete Hines, to avoid player confusion about vanishing items |

**Resolution, now high-confidence rather than a two-way tiebreak: Kimi's
independent, more granular audit strongly corroborates Claude's skeptical
reading over Gemini's credulous one, and adds real nuance neither prior
report had** — the skooma-merchant story is real but only in **pre-release
testing**, not the shipped game as configured (a distinction Claude's
report didn't draw this finely); the Skull of Corruption story is not
just real but **still reproducible in the 2025 Skyrim/Oblivion remaster**;
and the Todd Howard "buy a dagger" anecdote, while developer-sourced, is
now separately flagged as **not reproducible in the final shipped
mechanics** — a genuinely new middle category ("real anecdote, describes
non-shipped behavior") that the prior two-report synthesis didn't have.
**Going forward: cite the skooma-merchant and Skull of Corruption stories
as real (with the important caveat on each — pre-release-only for the
former, remaster-reproducible for the latter); treat the starving-guard
story as very likely fabricated; treat the dagger-buying and NPC-shop-theft
stories as developer-described concepts that did not ship as described.**

**What all three reports agree actually shipped**: the retail
Oblivion/Skyrim build aggressively neutered the open-ended
need-satisfaction system. Claude and Kimi both independently source Bruce
Nesmith's account of Skyrim's specific design response — a deliberately
curated list of player-triggered reactions rather than open-ended
emergence. **Kimi adds a striking new quantitative data point neither
other report has**: a direct AI-package count across three Bethesda
titles — **roughly 7,200 packages in Oblivion (~50% scheduled), ~6,000 in
Skyrim (~25% scheduled), ~3,500 in Starfield (~6% scheduled, mostly
quest-tied)** — concrete numerical evidence for the twenty-year trajectory
away from unsupervised autonomous behavior and toward authored-but-
dynamically-cast content, replacing what was previously only a
qualitatively-argued trend. Kimi's own framing of the lesson: Chronicle's
grudges/rumors writing back into behavior is *exactly* the mechanism
family that produced Oblivion's chaos, so the historical record argues for
constrained, condition-gated behavior emission (packages, scenes, aliases
with Protected/Essential flags) rather than open-ended goal pursuit — "a
hard requirement, not a cautionary tale that doesn't apply."

**Also new from Kimi, not in the prior two-report version**: the E3 2005
"Estelle Renoit" demo sequence — often treated as either faked or
spontaneously emergent — is neither, per a direct quote from Bethesda
programmer Steve Meister: it was "a set of examples of the kinds of things
you can do with RAI... content made specifically for the E3 demo," a
deliberately staged, deterministic package sequence. And a separate,
genuinely shipped-and-unpatched mundane failure: an NPC that can fall off
a bridge and die unnoticed, permanently blocking the player from a
house-purchase questline — cited by Kimi as a real "quest-critical NPC
meets unsupervised simulation" casualty distinct from the famous
legendarium above.

## 4. What's actually exposed to a mod like Chronicle

All three reports converge tightly here — this remains the most
actionable section of the whole document, and Kimi's pass adds real
operational detail on top of the existing two-report consensus.

**Observation (read-only, lowest risk):**
- All three confirm vanilla Papyrus quest scripts receive typed
  `OnStory*` callbacks (`OnStoryKillActor`, `OnStoryChangeLocation`,
  `OnStoryScript`, and roughly two dozen to thirty more — bribe, flatter,
  craft item, discover dead body, relationship change, etc.) whenever the
  corresponding Story Manager event starts that quest. Kimi's enumeration
  (~30 events, sourced to the same community Papyrus-API dump Claude
  used) matches Claude's more complete list.
- All three note Chronicle can add its own nodes under existing vanilla
  event nodes using the **"Shares Event"** property so it observes without
  preempting vanilla selection.
- **Kimi adds an honest limitation neither Gemini nor Claude stated
  explicitly**: there is **no engine callback for "some other quest
  started" in general** — a mod cannot subscribe to vanilla quest starts
  globally. Observation of Chronicle-triggered events is complete (its own
  quests report themselves); observation of vanilla-triggered radiant
  events is necessarily partial and must be reconstructed from visible
  side effects (quest objects, alias persistence, actor packages). For
  Chronicle's actual purpose this is a minor caveat — the OnStory event
  family covers the meaningful social event types natively — but it's a
  real limit worth stating plainly rather than implying total observation
  coverage.
- **Kimi also surfaces dormant engine debug logging** (`bStoryManagerLogging`
  and `iStoryManagerLoggingEvent` INI settings, identified by modders
  within two weeks of Skyrim's release) — a development-time diagnostic
  channel, not a runtime API, but useful during Chronicle's own
  integration testing.
- SKSE's `RegisterForModEvent`/`SendModEvent` (and community extenders
  like `po3_PapyrusExtender`) expose richer/global observation beyond
  vanilla `OnStory*` — all three agree this is optional, not a hard
  dependency.

**Injection (the highest-value capability, and it's vanilla Papyrus):**
- `Keyword.SendStoryEvent(akLoc, akRef1, akRef2, aiValue1, aiValue2)` —
  all three reports independently name this the cleanest, most cooperative
  integration path — Chronicle picks the NPC/location by its own
  provenance/grudge logic and fires it as event data into a
  Chronicle-authored quest node using a "From Event" alias fill.
- `ReferenceAlias.ForceRefTo(ObjectReference)` / **`ForceRefIfEmpty`** (the
  safer, non-destructive variant, which Claude and Kimi both cover and
  Gemini doesn't) — described consistently across both as powerful but
  risky: it can bypass most CK fill conditions but triggers
  `EvaluatePackage()` re-evaluation on every actor in any running scene
  connected to that quest, and repeated calls during an active scene can
  permanently strip scene packages.
- `LocationAlias.ForceLocationTo(...)`/`ForceLocIntoAlias` — the
  location-alias equivalent, confirmed by all three.
- **Kimi adds a specific, concrete mechanism the other two reports don't
  cover: Quest priority (a 0–100 field on the quest record) arbitrates
  which quest's alias-owned package wins when two quests hold the same
  actor** — "the NPC will automatically start using this package, unless
  they are occupying another alias with higher priority," sourced to the
  Beyond Skyrim project's own Arcane University documentation. Kimi's
  concrete prescription for Chronicle: keep Chronicle's own quest priority
  modest so authored vanilla scenes preempt it, mark long-lived
  social-state quest aliases Optional and non-reserving wherever possible,
  and use `TryToEvaluatePackage` after state changes rather than fighting
  the package stack directly.
- **Kimi also surfaces a ready-made idiom neither other report names**:
  the same Arcane University documentation describes a "delayed reaction"
  pattern already used in shipped Bethesda-adjacent content — a Story
  Manager quest adds an NPC to a faction at stage 0 and stops, and later
  dialogue conditioned on that faction fires independently — which maps
  directly onto Chronicle's own "NPCs react later to things done to them"
  beats without any new engine mechanism required.

**De-confliction** (Claude and Kimi both cover this more thoroughly than
Gemini, and agree in detail): a community-standard **"Radiant Exclusions"
FormList** pattern that vanilla radiant quests are patched to skip when
choosing locations. All three agree on a real timing hazard: since radiant
quests **choose targets before the quest is taken, not when accepted**, an
exclusion registered after the engine has already queued a target won't
retroactively change it — Chronicle must claim proactively, before the
relevant Story Manager event fires. Kimi adds the general coexistence
discipline as an explicit three-part rule, sourced to community
how-to documentation: **add-only Story Manager nodes (never edit vanilla
nodes), respect event-consumption semantics (place/flag nodes so vanilla
quests aren't starved), and keep Chronicle's own alias reservations and
quest priority modest so authored scenes can still preempt it.**

## 5. Fallout 4's version

All three reports confirm FO4 uses the **same Story Manager/alias/
SendStoryEvent architecture**; the Papyrus signatures are verbatim
identical to Skyrim's, per Claude. Distinct emphases across the three:

- **Gemini** goes deepest on the Workshop system specifically —
  `WorkshopParentScript.psc` uses continuous automated `ForceRefTo` calls
  to assign procedurally generated settlers across dozens of unloaded
  settlements simultaneously, and notes this required extensive community
  patching (Unofficial Fallout 4 Patch) to stop Story Manager infinite-loop
  bugs in Minutemen radiant quests — real evidence the architecture scales
  but is fragile under heavy load.
- **Claude** goes deepest on the selection-architecture change: FO4
  exposes an explicit, configurable start-chance and a Random-vs-Recruitment
  quest-type split, making content-selection more overtly weighted-random
  than Skyrim's simpler tree-order-priority model.
- **Kimi independently confirms both of the above and adds two things
  neither other report has**: (1) **the Preston Garvey "quest vending
  machine" failure mode** as a named cautionary tale, quoting design
  criticism directly ("they can ruin characters… I associate literally
  nothing else with this man other than these dumb quests") — the
  clearest illustration in the whole synthesis of what happens when a
  radiant system has *no memory*: infinite templated repetition with zero
  variation annihilates characterization, which Kimi explicitly frames as
  precisely the gap Chronicle's belief/provenance layer would fill if
  applied to a Preston-Garvey-shaped NPC. (2) **A direct, sourced Bruce
  Nesmith quote explaining FO4's non-adoption of Skyrim's succession
  machinery was a deliberate philosophical fork, not a regression**:
  Fallout's "old school" vibe meant vendors don't run schedules and the
  team explicitly chose not to reuse the Skyrim-style
  aunt/uncle/sibling-succession system because they "didn't want to lose
  those cool NPCs that they had spent time crafting."

All three agree the pre-selection timing (targets chosen before the quest
is taken) carries over unchanged into FO4, and that FO4's generic-NPC
behavior remains package/schedule-driven, not a return to Oblivion's
need-cascade model.

## Final verdict

**How much of a GM/director layer does Bethesda's engine already provide
natively?** All three reports agree: nearly all of the hard mechanical
substrate — picking a real, live NPC (including mod-added ones); picking
a real location (with a documented exploration bias); gating on real
precondition state; casting those into a reusable template with dialogue,
packages, and scenes; firing the right template in response to world
events. This is a genuine, shipped, three-titles-battle-tested
parametrized-storylet engine. **Kimi's specific, quotable framing is the
best summary the whole research effort has produced: Bethesda built a
memoryless director; Chronicle is a director-less memory.**

**What it does not do — and where Chronicle is completing rather than
competing**, now specified more precisely than the two-report version
could manage: narrative-quality/best-fit selection scoring (Radiant
Story's Find Matching Reference is condition-filter-then-random, never a
scored optimum the way King of Dragon Pass's selector functions are), and
salience-based arbitration between eligible templates (tree order and
first-match-wins, not a dramatic-weight comparison — an absence Bruce
Nesmith's own retrospective confirms Bethesda felt internally). Neither
report finds any native memory/provenance model at all; Event Data is
ephemeral, gone once the quest starts — exactly the layer Chronicle exists
to add.

**The smallest actual integration surface, per all three reports
converging independently on nearly the same spine:** `SendStoryEvent`
(Chronicle drives the engine with its own picks) + "From Event" alias
fills (the engine casts them into Chronicle-authored templates) +
`ForceRefIfEmpty`/`ForceRefTo` (Chronicle overrides or biases casting when
needed, with Quest Priority as the arbitration lever when two quests
compete for the same actor) + `OnStory*` events for observation (with the
honest caveat that only Chronicle's own quests are fully observable, not
vanilla quest starts in general) + an exclusion FormList for
de-confliction. All of this is vanilla Papyrus plus the Creation Kit; SKSE
is optional, for richer observation only. **Chronicle should hook Radiant
Story as its casting-and-execution backend, not rebuild a parallel one,
and spend its own engineering budget entirely on the belief/provenance/
selection-intelligence layer the engine was deliberately built without.**

## Caveats carried over and consolidated across all three reports

- **Unresolved**: the citation-venue discrepancy on the Kreminski &
  Wardrip-Fruin storylet paper (ICIDS 2018 per Claude vs. FDG 2018 per
  Kimi) — confirm the actual publication venue before citing it publicly.
- The Oblivion anecdote sourcing question (§3) is now resolved with high
  confidence via Kimi's independent, more granular audit corroborating
  Claude's skeptical reading — but a direct five-minute check of
  Pagliarulo's original 2006 statement and the paavo.me blog post is still
  worthwhile before quoting any of it in a public-facing document.
- Claude's report flags that the Creation Kit wiki's "Quest Alias Tab"
  page blocked automated fetching during its research, recovering its
  fill-type enumeration from indexed snippets rather than the live page;
  Kimi's independently-sourced enumeration (via CK wiki mirrors and UESP)
  matches it closely, which raises confidence but doesn't fully substitute
  for a direct manual check.
- `ForceRefTo`'s "bypasses most CK fill conditions" behavior is documented
  as observed, not guaranteed, per Claude — verify a cast succeeded via
  `GetReference()` rather than assuming success.
- Some Fallout 4 behavioral details across all three reports derive from
  high-quality community reverse-engineering (mod documentation, wiki
  mirrors) rather than official Bethesda primary sources — reliable for
  engine behavior, but not official specs.
- Kimi's report is the only one of the three built primarily around a
  single unusually rigorous community source (paavo.me's 2025
  reverse-engineering deep dive, which itself verified claims against
  actual Construction Set/game data) — this gives it unusual depth on the
  Oblivion-era material specifically, but means its coverage is less
  independent of that one source than Gemini's or Claude's multi-source
  approach. Worth knowing when weighing how many genuinely separate
  sources back any single claim in this document.
