# Six Smaller Game-Mechanics Gaps: Synthesized Verdict (merging 4 independent reports — Gemini, Claude, Kimi, Claude follow-up)

Synthesis of four independent gap-research passes covering Prompt 4 from
`notes/comparative-systems-gap-research-prompts-2026-09-06.md`: six smaller
gaps in already-researched games — CK3's Legends system, CK3's
Struggle/Phase system, the Nemesis System's intel/interrogation system,
RimWorld's Ideology DLC + Tales, Dwarf Fortress's Villains update +
loyalty cascade, and Watch Dogs: Legion's Census/grievance-chain system.
Sources: `gap-research-raw-agent-reports-2026-09-06/misc-gaps-gemini.md`,
`misc-gaps-claude.md`, `misc-gaps-kimi.md` (a third independent agent), and
`misc-gaps-claude-followup-numeric-detail.md` (a Claude follow-up pass
specifically supplying exact numeric/mechanical detail with direct
citations — this appears to have been requested to resolve the CK3 Legends
percentage-bonus gap flagged as unverified in the original 2-agent version
of this document).

**Source-quality note, carried over from the 2-agent version:** Gemini's
file answers all four gap-research prompts in one document; only its
Part 4 is used here. Claude's two passes (original + follow-up) are
markedly more rigorous throughout, dating releases and separating
wiki-confirmed facts from player-summary claims. Kimi's pass is
independently sourced and, on several items, gives the most granular
numeric detail of any of the four — including exact catalyst-point values
per action for CK3 Struggles and a mood-coupled Certainty regeneration
formula for RimWorld that neither Claude pass reported.

## TL;DR

**All four reports agree on the same headline pick and the same
cautionary tale.** CK3's Struggle system — a regional conflict as a cyclic
finite-state machine of named phases, with transitions driven by
accumulated "catalyst" points from character actions — is the single most
transferable pattern for modeling Skyrim's civil war as something other
than a binary questline, and is now specified down to individual action
point-values, not just phase names. Dwarf Fortress's "loyalty cascade"
(Toady One's own "civil war bug") is the sharpest cautionary tale in the
whole batch: a faction-membership failure where a single forced execution
can flip the executioners into enemies of their own civilization,
recursively, until the settlement destroys itself. Four of the six items
are natural extensions of Chronicle's existing belief/rumor/provenance/
faction model; two (Struggles, and Watch Dogs: Legion's lazy generation
architecture) are genuinely distinct patterns worth adopting as-is.

**The previously-flagged CK3 Legends percentage-bonus gap is now
partially resolved** (see §1) — Kimi's independent citation corroborates
part of Gemini's original figure, but not all of it.

## 1. CK3 Legends (Legends of the Dead, patch 1.12.1, March 2024)

**All four reports agree on the mechanic's shape**: a Legend is a
provenance-tagged narrative object (named protagonist, chosen Legend Seed
type — Heroic, Holy, or Legitimizing) that spreads barony-by-barony as a
resource-fed diffusion, gated by a language-similarity barrier at realm
borders, driven by a Court Chronicler assigned to Extol Domestic Legend or
Commend Legend Abroad. Kimi adds a precise mechanical nuance the other
three didn't state as clearly: spread is **not a scripted radius or a
per-tick adjacency-flux simulation** — each barony independently rolls a
chance-based acquisition gated by distance, county development level, and
geographic connectivity (e.g., rivers), with baronies beyond a distance
threshold simply ineligible. Quality-tier upgrades are gated purely by
cumulative geographic spread (Famed → 100 baronies → Illustrious → 300
baronies → Mythical), confirmed identically by Claude's original pass,
Claude's follow-up, and Kimi.

**The percentage-bonus discrepancy, now partially resolved:** the original
2-agent version of this document flagged Gemini's specific numeric table
(Famed: +10% Prestige/+100 Legitimacy/50% Legendary Building chance;
Illustrious: 100 baronies/+15%/+200; Mythical: "Advanced Spread"/+25%/+300)
as uncited and unverified. Two independent citation efforts since then
give a more precise picture:

- **Claude's follow-up** cites the CK3 wiki for **per-county** standing
  modifiers while a legend is active (not owner-personal rewards): +5/+10/
  +20 Popular Opinion by tier across all types, plus type-specific effects
  — Holy: +0.10/+0.15/+0.25 Monthly Control; Heroic: +5%/+10%/+20%
  Stationed Men-at-Arms Damage; Legitimizing: +1%/+2%/+6% Development
  Growth. Also cites completion rewards: a Mythical Legitimizing legend
  grants up to +600 Legitimacy and empire-wide claims.
- **Kimi**, independently, cites the CK3 wiki for **Owner** rewards
  (distinct from the per-county modifiers above): a Mythical Heroic legend
  grants **+25% Prestige and +300 Legitimacy**; a Mythical Legitimizing
  legend grants +0.50 monthly Renown, +600 Legitimacy, and an Unpressed
  Claim on every de jure title of the protagonist's primary empire title.
  Kimi also cites **Promoter** rewards (e.g., +4 Martial and +10% Prestige
  at Mythical Heroic) as a third, separate reward channel — explaining
  mechanically why AI rulers are willing to adopt someone else's legend.

**The upshot**: Gemini's Mythical-tier figure (+25% Prestige, +300
Legitimacy) is now independently corroborated — it matches Kimi's citation
of the Mythical Heroic *Owner* bonus exactly, even though Gemini's
original table didn't specify which legend type or reward channel
(Owner/Promoter/per-county) it was describing. Gemini's Famed and
Illustrious percentage figures, and the "50% Legendary Building chance"
and "Advanced Spread" labels, remain **uncorroborated by any of the other
three reports** and should still be treated as unverified. **For design
purposes: Claude's and Kimi's cited numbers (per-county modifiers, and
Owner/Promoter rewards at the Mythical tier) are safe to use; anything
from Gemini's table not independently matched above is not.**

**Catalog fit:** all four reports agree — natural extension of Chronicle's
existing rumor/provenance layer; the transferable novelty is the economic
gating (maintenance cost → spread → tier) and the county-stacking payoff
structure, plus the concrete distance/development/connectivity spread
gating Kimi specifically documented.

## 2. CK3 Struggles — the headline pick

**All four reports independently arrive at the same conclusion: this is a
genuinely distinct pattern, not an extension of anything Chronicle already
has**, and all recommend it as the template for Skyrim's civil war
specifically. Kimi's pass is now the most detailed of the four and should
be the primary design reference.

**Exact phase names and cycle** (corroborated across all four, with one
citation-quality note): Opportunity → (Hostility *or* Conciliation,
whichever competing catalyst track reaches threshold first) → both lead to
Compromise → decays back to Opportunity. **Citation-quality flag, from
Kimi**: a widely-read third-party guide (TheGamer) misprints the phase
list as including "Hospitality" — the correct name, confirmed against
Paradox's own Dev Diary #94 and the game data, is **Hostility**. Worth
knowing since this exact misspelling could easily propagate into a design
document if the wrong source gets cited later.

**Exact catalyst values — new in this revision, from Kimi's citation of
the CK3 wiki directly:** the Iberian Struggle's threshold is confirmed as
**1,000 points** on each of two competing tracks. Concrete per-action
point values: during Opportunity, breaking a truce with an Involved
character adds **+25** toward Hostility; exposing a secret or becoming a
rival/nemesis adds **+10**; a kill or forced conversion adds **+5**; there
is always **+1 yearly drift**. The mirrored conciliatory track awards +25
for unconditionally releasing an Involved prisoner, +10 for granting
independence or converting to the local culture/faith, down to +3 for
gifts and alliances. Character status (Involved / Interloper / Uninvolved)
gates who generates catalysts at all, determined by realm-capital location
and faith/culture membership. This is a substantial upgrade in specificity
over the 2-agent version of this document, which only had the phase
names, the 1,000-point threshold, and the 3-month debounce without
per-action weights.

**Per-phase action gating, also newly detailed by Kimi**: Hostility
enables the Forced Vassalization casus belli, halves CB costs against
different-faith targets, shortens truces by 900 days, imposes −30%
development growth and −10 different-culture/faith opinion. Conciliation
disables Invasion/Conquest CBs entirely, forbids executing Involved
prisoners, extends truces by 900 days, boosts development +30%, unlocks
cross-faith marriage. Compromise is an armed peace (+10 white-peace
acceptance, enforced truces, larger garrisons). Opportunity is the mobile
opening phase (cheap claims, Abduct/Claim Throne schemes unlocked). This
matches and extends Claude's original account (which gave the same general
shape — hostility cheaper/bloodier wars, compromise capping Struggle
Clashes — without these exact numbers).

**Endings**: Kimi confirms and names the specific Iberian Ending Decisions
— **Status Quo** (from Compromise, destroys the Hispania title, freezes de
jure boundaries), **Détente** (from Conciliation, requires alliance with
*every* independent Involved ruler, permanently disables holy wars between
the involved cultures), and a dominance-by-conquest ending. Both Claude
passes and Kimi confirm the Iranian Intermezzo variant uses different
phase names (Unrest → Stabilization → Concession) with its own catalyst
table — direct evidence the phase machine is a reusable engine with a
region-specific action vocabulary grafted on, exactly the transfer pattern
Chronicle would want for Skyrim's civil war.

**The documented balance trap, confirmed across all four sources**:
late-game Conciliation tends to dominate because gift-giving/city-upgrade
actions generate conciliatory catalysts easily at scale, making the
opposite phase (needed for some endings, e.g. Hostility to form Hispania)
hard to reach at large realm sizes — a concrete lesson for tuning catalyst
weights before shipping a Skyrim adaptation.

**Catalog fit:** unanimous across all four — genuinely distinct, a formal
region-scoped finite-state-machine layer for macro-conflict pacing with no
equivalent in Chronicle's current design or the original six-game catalog.
**This is now specified precisely enough (phase names, exact catalyst
point-values, exact per-phase action gating, named endings, a documented
balance trap) to design a Skyrim adaptation directly from this document**,
treating the specific numbers as a tunable starting point rather than a
literal port.

## 3. Shadow of War — worms and intel

**All three passes that cover this (Gemini, Claude's two passes, and
Kimi) agree on the mechanic and its catalog fit.** Low-rank orcs marked as
"worms" (plus scattered intel pickups) are interrogated to reveal a
specific captain's hidden Strengths/Weaknesses/Immunities/Vulnerabilities
and location; intel isn't spent as a resource, it's per-target knowledge
unlocked once, and exploiting a revealed Vulnerability guarantees a rune
drop. All agree the "cost" is situational risk rather than a price: worms
flee, are usually guarded, and a botched grab can kill the worm outright,
wasting the lead.

**New detail from Kimi, not in the prior 2-agent version**: intel can also
be acquired without any interrogation at all, from **environmental
artifacts** — dead orc bodies in the wild, bulletin boards in outposts,
and discarded documents in tents all grant the same reveal passively.
Also new: during the intel-selection screen itself, the player explicitly
cannot be harmed — a documented safety window around the otherwise-risky
grab. Claude's follow-up adds that interrogation is disabled once only one
unknown captain remains before the death-threat story mission (already
noted in the 2-agent version), and separately cites Chris Hoge's GDC 2018
talk ("Helping Players Hate (or Love) Their Nemesis") as developer
material on the design philosophy, though it documents relationship/
emotion design rather than the intel plumbing specifically.

**Catalog fit:** unanimous — natural extension of Chronicle's existing
provenance/knowledge-about-agents model, applied to actionable tactical
knowledge about a named adversary. The transferable refinement, per Kimi,
is the **typed tiering of knowledge sources** (grunt ≠ worm ≠ captain ≠
passive document) rather than a wholly new mechanic.

## 4. RimWorld — Ideology DLC and the Tale system

**All four reports agree on the core architecture**: ideoligions (built
from memes → precepts) define social roles and rituals; a per-pawn
**Certainty** score is a belief-strength axis distinct from but
interacting with mood. Claude's original pass gave the fullest formula
detail among the first two reports; Kimi now adds a mechanism neither
Claude pass reported explicitly:

**New from Kimi — mood-coupled Certainty regeneration**: Certainty
regenerates daily at a rate scaled by mood — roughly 1%/day at ≤20% mood,
2%/day at 50% mood, 3%/day at ≥80% mood, linearly interpolated between
those anchors. This creates a direct, named coupling — **unhappy pawns
are persuadable pawns** — meaning RimWorld's mood and belief systems are
mechanically linked, not parallel. Kimi also adds that **Apostasy**
precepts make defectors permanently easier to reconvert (×40-80% future
certainty loss) while imposing opinion penalties on them, and that a
*failed* Conversion Ritual actually **increases** the target's certainty
(a backfire mechanic none of the other three reports mentioned).

**The conversion-loss formula itself is corroborated verbatim across
Claude's original pass and Kimi**: 6% × Conversion Power of the Converter
× (×2 if Moral Guide) × Global Certainty Loss Factor of the convertee ×
Relic Conversion Power Factor × Trait/Meme Agreeableness × Storyteller
low-population boost.

**On the Tale/art-description system**: all four broadly agree, and
Kimi's framing of the DF-vs-RimWorld comparison independently converges on
almost the same language Claude's original pass used — DF's pattern is
**historiography** (the object cites the world's persistent historical
ledger); RimWorld's is **commemoration** (the object cites a session-local
colony event log mixed with fictional filler, drawn from a fixed
vocabulary of event types). Two independent reports reaching for nearly
identical framing is a good sign this characterization is robust, not an
artifact of one report's phrasing.

**Catalog fit:** all four agree — natural extension on both counts (belief
propagation with an explicit certainty scalar now shown to be mood-coupled;
Tales as provenance objects), with DF still the more ambitious reactive-
provenance variant to aim for if resources allow.

## 5. Dwarf Fortress — Villains update (v0.47.01, January 2020) and the loyalty cascade

**All four reports agree on the mechanic and, independently, treat the
loyalty cascade as the single sharpest cautionary tale in this whole
document.** The Villains update added intrigue "organisations" where
historical figures reach agreements (persuasion, blackmail, bribes) to
fund theft, sabotage, abduction, assassination, coups, and embezzlement;
civilizations counter with spymaster/law-enforcement surveillance and
fortress-mode interrogation of suspected agents (who may use pseudonyms).
Kimi frames this as "the closest shipped analogue to Chronicle's
evidence-chain ambitions in this batch" — a directed, multi-hop
conspiracy graph (agent → handler → villain master → plot) where graph
information is only accessible through risky social actions against its
nodes.

**The loyalty cascade, corroborated in detail by all four**: ordering an
attack on your own civilization's members (even accidentally, or executing
a citizen) flips the attackers into "Separatists" — enemies of their own
civilization who still follow fort orders. Citizens who then attack
Separatists become "Loyalists" (enemies of the *fort*, loyal to the civ);
further combat spawns "Renegades" (enemies of both). Because loyalty flags
are re-evaluated per hostile act with no damping, this recursively
fractures the settlement into a permanent, unresolvable civil war —
reportedly called the "civil war bug" by Toady One himself.

**New from Kimi — documented trigger variants and a partial fix**:
additional documented cascade triggers include attacking a werebeast
citizen while in dwarf form, attacking a berserk citizen (bug 7107 — the
defenders "lose loyalty and are hunted down as traitors"), and releasing
tamed enemy mounts, which instantly attack citizens and seed the cascade.
**As of DF v0.50, cascades "should periodically end on their own"** per
the DF wiki, and DFHack ships a dedicated `fix/loyaltycascade` command —
evidence the failure mode survived for years as an accepted hazard before
being partially mitigated, not something that was fixed outright. This
nuances the earlier framing slightly: the cascade is real and was
unrecoverable for most of the game's history, but the current version has
some self-resolution, which is worth knowing if anyone cites this as "an
unfixable bug" rather than "a long-standing, only-recently-mitigated one."

**Both Claude passes and Kimi independently draw the same design lesson
for Chronicle**: any mechanic that flips a membership/enemy flag as a side
effect of a forced action (execution, forced compliance, conscription)
needs damped, non-recursive transitions scoped to actual witnesses/
participants, or a single incident can cascade an entire settlement into
mutual hostility. Kimi states the underlying principle most precisely:
"when 'enemy of faction' and 'member of institution' are independent
labels, a single sanctioned act of violence can create an unrecoverable
logical contradiction that propagates to every actor who touches it" —
directly relevant to any civil-war or faction-membership mechanic Chronicle
designs, including CK3 Struggle's phase-gated action changes (§2) and the
misc-gaps synthesis's own loyalty-cascade guard already folded into the
master feature synthesis's design constraints.

**Catalog fit:** all four agree — the intrigue layer is a natural
extension of faction membership plus grudge tracking; the loyalty cascade
itself is a cautionary case study, not a mechanic to adopt.

## 6. Watch Dogs: Legion — Census and "Play as Anyone"

**All four reports agree this is a genuinely distinct architecture, and on
its core mechanism**: NPCs are not a fully pre-simulated persistent social
graph. Census generates a pedestrian's full profile, relationships, and
grievance chain **lazily, on-demand, at profiling/interaction time**
(internally called "uprezzing"). Claude's original pass and Kimi both name
primary sources directly and in close agreement: technology director
Martin Walsh, team lead designer Liz England, mission-systems lead Jurie
Horneman, and lead AI programmer Christopher Dragert (Kimi additionally
cites Dragert's specific GDC 2021 talk, "Census: The Systemic Backbone
Behind Play As Anyone").

**New from Kimi — the "spider-web," not forward-chained, generation
order**: Census generation isn't always occupation-first; it can anchor on
whatever fact is most salient in context (e.g., a pedestrian caught
mid-brawl locks personality and fashion first, with occupation filled in
afterward) — described by the developers as a deliberate technique to
avoid both "procedural soup" and stereotype templates. Kimi also names the
player-facing mechanical chain more precisely: scan → add to contacts →
(with the Deep Profiler upgrade) inspect schedule and **recruitment
leads** → complete the generated recruitment mission → operative joins.

**Both Claude passes and Kimi converge on the same core finding for the
prompt's central question**: the recruitment grievance is **assembled at
runtime and justified backward** from the generated profile, not drawn
from a pre-simulated social graph of wrongdoing — the developers'
own stated example, quoted independently by both Claude and Kimi: "we've
actually spawned somebody who doesn't like Dedsec, now let's give them a
reason why," explicitly linked by the developers themselves to Ben
Sunshine-Hill's "alibi generation" research (already a familiar concept in
this project's own RimWorld/DF offscreen-entity research). Consequences do
propagate forward once a character exists in the uprezzed layer — Kimi
confirms revenge missions can include kidnapping a player operative to
force a rescue.

**Catalog fit:** all four agree this is genuinely distinct relative to
Chronicle's presumed persistent-simulation approach — it's the opposite
performance trade-off (generate depth only where the player looks, versus
always-simulated), not an extension of anything already in the catalog.

## 7. New: Kimi's cross-cutting architectural observation

Kimi's pass includes a synthesis-level observation not present in either
Claude pass or Gemini's, worth surfacing on its own because it speaks
directly to Chronicle's central bet, not just to any one of the six items:

**"Spread and allegiance are cheapest to model as gated scalar state, not
as simulated process."** CK3 Legends is a funded scalar (spread chance →
barony count → tier); RimWorld belief is a per-pawn scalar (Certainty
0-100%) with typed attack/regeneration channels; CK3 Struggles are two
competing scalar tracks (catalyst points to a threshold) aggregated across
a region. In every case the scalar is legible to the player, tunable by
explicit action, and robust to simulation scale. **The one counterexample
in this batch where a shipped game instead maintained rich per-entity
relational labels (DF's civ/fort membership pair) is exactly the loyalty
cascade** — the richer, more provenance-preserving model was also the one
that catastrophically failed.

Kimi's own stated counterpoint is the sharper half of the observation and
matters more for Chronicle specifically: **scalar models sacrifice exactly
what Chronicle's vision document bets on — provenance.** CK3's legend does
not record who told it to whom; RimWorld's certainty does not record which
argument moved it; the struggle track does not record which specific
murder contributed its +5 points. Watch Dogs: Legion's read-time
consistency-manufacturing is offered as a pragmatic middle path; DF's
villains intrigue network is the one system in the whole batch showing
genuine multi-hop provenance (agent → handler → master) surviving
interrogation-based partial disclosure. This is a useful frame for
Chronicle's own design work going forward: every one of these five other
"gated scalar" systems achieves legibility and scale specifically by
giving up the thing Chronicle is betting its whole differentiation on —
worth remembering as a design pressure to resist when a scalar
simplification looks tempting for performance reasons.

## Final verdict

**Of the six, CK3 Struggles remains the one deserving unqualified "adopt
as a template" status, and it is now specified precisely enough to design
directly from** — all four reports converge on it independently, and
Kimi's citation of exact catalyst point-values, phase-gating effects, and
named endings upgrades this from "a good template shape" to "a fully
numbered reference implementation to adapt," not just a structural
analogy.

**Watch Dogs: Legion's Census architecture is worth treating as a real
fallback option, not a template to adopt now** — it's a fundamentally
different bet (generate-on-demand vs. Chronicle's stated always-simulated
premise) that should only be reached for if Chronicle's persistent
simulation actually misses Skyrim's frame-time budget.

**The other four (CK3 Legends, Shadow of War's intel system, RimWorld's
Ideology/Tales, DF's Villains intrigue) remain fine to treat as
citable-but-settled extensions from this batch of four reports** — none
need a further primary-source read before Chronicle's design work draws on
them. **The one exception, now partially rather than fully unresolved**:
Gemini's original Mythical-tier CK3 Legends figure (+25% Prestige/+300
Legitimacy) is corroborated (it matches Kimi's independently-cited
Mythical Heroic Owner-bonus tier); its Famed/Illustrious figures and the
"Advanced Spread"/"50% Legendary Building chance" labels remain
unverified and should not be used in a design document without a direct
wiki check.

**The loyalty cascade (§5) is still the one finding from this whole
document worth elevating beyond "settled reference"** — all four agents
treat it as a hard design constraint, not just an interesting fact, and it
directly informs Chronicle's non-goal against uncontrolled cascading
faction-flag mechanics. **New nuance from this revision**: the cascade has
some self-resolution as of DF v0.50, so cite it as "a long-standing,
only-recently-mitigated failure mode," not as permanently unrecoverable.

**Kimi's cross-cutting scalar-vs-provenance observation (§7) is worth
carrying forward into any actual Chronicle design work**, independent of
which of the six mechanics gets adopted — it's a direct articulation of
the tradeoff Chronicle's whole architecture is betting against the grain
of every other system in this batch.
