# Chronicle Implementation Pass — NPC Social-Mechanics Catalog (Claude pass, 2026-09-06)

Per-item format: **Concept** (what Chronicle tracks / trigger / what the player sees) · **Rating** H/M/L with reason · **Feasibility** · **Overlap** (a) covered, needs surfacing / (b) small extension / (c) new subsystem.

---

## 1. Crusader Kings II / III

### 1.1 Relationship/opinion tracking

**Directed pairwise opinion**
- Concept: Chronicle already derives disposition from beliefs; add an itemized "why" ledger per NPC pair, surfaced via a dialogue option ("What do you think of Nazeem?") that reads the top 3 signed contributors aloud.
- Rating: M — the ledger itself is personal-scale, but *itemization with causes* is the legibility backbone every High item below depends on.
- Feasibility: Pure Python-side derivation + dialogue injection via the C++ plugin; cheap.
- Overlap: (a) — covered; needs the surfacing layer.

**Opinion modifier fields (lifetime/decay/multiplier/legal-right primitives)**
- Concept: Give Chronicle belief-derived modifiers a schema: duration, decay curve, stack count, and a `justifies:` field (a belief that justifies a guard arrest, a refusal to trade, an attack) so consequences are typed rights, not just numbers.
- Rating: H — `justifies` converts invisible state into legible permission for visible NPC action ("You were seen robbing Belethor — the guard has cause").
- Feasibility: Schema work in Python; consequences map to existing engine verbs (crime gold, faction hostility) via C++.
- Overlap: (b) — extension of grudge typing.

**CK2 flat-then-drop vs CK3 gradual decay**
- Concept: Per-belief decay curves: fresh outrage decays gradually; formal debts hold flat then expire on repayment date.
- Rating: L — invisible tuning detail; players never see the curve shape, only its endpoints.
- Feasibility: Trivial in Python.
- Overlap: (a).

**Succession opinion inheritance (negative inherited 2× positive)**
- Concept: When a Chronicle-tracked NPC dies, heirs/kin inherit 25% of goodwill toward the player but 50% of grudges, with a memory citing the parent ("My father never forgave you").
- Rating: H — grudges that outlive their holders make the world feel like it has history, and Skyrim has named families everywhere (Battle-Borns, Grey-Manes).
- Feasibility: Needs a kinship map per hold (hand-authored once from vanilla data); Python-side inheritance; dialogue surfacing.
- Overlap: (b).

**Typed opinion categories**
- Concept: Split disposition into typed channels (personal, factional, pious, fear) so the same NPC can like you personally while despising your Stormcloak allegiance — and say so.
- Rating: M — enables genuinely good dialogue ("You're a decent sort, for an Imperial lapdog"), but it's plumbing until dialogue surfaces it.
- Feasibility: Python-side; needs channel-aware dialogue templates.
- Overlap: (b).

**Vassal Stance categories**
- Concept: Type each named citizen by stance toward their Jarl (loyalist, war-hungry, parochial, zealot); hold-level events (a new war levy, a Thane appointment) apply belief deltas only to matching stances.
- Rating: H — makes hold politics differentiate visibly: the same event splits a town into camps that argue about it in the inn.
- Feasibility: One-time stance tagging of named NPCs (LLM-assisted, human-reviewed); Python event fan-out.
- Overlap: (b) — belief fan-out by audience type is new.

**Diplomacy-skill-scaled opinion**
- Concept: Player Speech skill adds a scaled baseline to first impressions.
- Rating: L — Skyrim already has Speech affecting prices/persuasion; duplicating it adds a ledger entry, not motion.
- Feasibility: Trivial.
- Overlap: (a).

**Prestige/piety-derived opinion**
- Concept: Titles the player actually holds (Thane of X, Guild Master, Archmage) grant audience-specific belief baselines — guards defer, Thalmor sneer.
- Rating: M — cheap reactivity to real progression; bounded (per-audience, not global reputation, respecting the design ban).
- Feasibility: Read quest/faction state via C++; Python maps to per-faction stances.
- Overlap: (b).

**Tyranny pooled vs itemized**
- Concept: Track player abuses *per hold* as itemized justified-grievance entries (unpunished thefts, assaults witnesses reported) that guards and Jarl dialogue cite specifically; each expires separately.
- Rating: M — itemized (CK2-style) beats pooled here because provenance is Chronicle's identity; pooled tyranny is just a bounty bar Skyrim already has.
- Feasibility: Extends crime beliefs already planned; per-hold storage is native to Chronicle's shape.
- Overlap: (a)/(b).

**Named gift/grant modifiers with fixed durations**
- Concept: Gifts and favors create typed, decaying obligation beliefs with remembered specifics ("You brought my daughter that amulet") that NPCs repay unprompted — a discount, a warning about an ambush, a rumor shared early.
- Rating: H — unprompted repayment is a visible "the world remembers" moment, the positive mirror of grudges.
- Feasibility: Item-given detection needs C++ inventory hooks (verify feasibility of gift-menu interception — flag for research); rest is Python.
- Overlap: (b).

**Explorable opinion UI / sentiment map mode**
- Concept: A Chronicle journal page (MCM or in-game book UI) showing per-hold sentiment toward the player and, CK-style, letting the player inspect any A→B pair they have evidence about.
- Rating: M — strong for legibility, but out-of-world UI; gate B→C pair visibility behind what the *player* has witnessed/heard to stay diegetic.
- Feasibility: SkyUI/MCM panel fed by Python via C++; well-trodden modding ground.
- Overlap: (a) — surfacing.

### 1.2 Named relationships (crystallization)

**Discrete relationship flags overriding the scalar**
- Concept: When belief-derived disposition crosses thresholds with qualifying history, crystallize a named state — Friend, Sworn Friend, Rival, Enemy — that unlocks unique behaviors (friends warn you of rumors about you; enemies spread them).
- Rating: H — named states are what players screenshot and talk about; a scalar never is.
- Feasibility: Python state machine; behaviors map to existing Chronicle verbs.
- Overlap: (b) — thresholds exist, crystallized unlocks don't.

**Explicit values + secondary effects per relation (incl. stress-on-death)**
- Concept: Relations carry mechanical riders: a Friend merchant gives real discounts (C++ barter hook); a Rival's death near the player spawns suspicion beliefs in their kin regardless of actual culprit.
- Rating: M — riders make relations matter mechanically, not just verbally.
- Feasibility: Barter/disposition hooks exist in SKSE ecosystem; suspicion-on-death is pure Chronicle.
- Overlap: (b).

**Formation always records a reason**
- Concept: Every crystallized relation stores its founding memory and NPCs cite it verbatim-ish in dialogue ("Ever since you pulled me out of that Forsworn camp...").
- Rating: H — this is the cheapest high-visibility move in the whole catalog; provenance is already Chronicle's core, this just speaks it.
- Feasibility: LLM dialogue generation from the memory record; already the plan.
- Overlap: (a) — pure surfacing.

**Relations gate/protect AI behavior**
- Concept: Relations gate participation in collective action: a Friend refuses to join a mob/posse against you, and tells you who organized it.
- Rating: H — betrayal-proofing and informants make social state tactically meaningful.
- Feasibility: Python-side candidate filtering when Chronicle casts group events.
- Overlap: (b).

**Inheritance of named relations on death**
- Concept: A dead Sworn Friend's sibling approaches the player once ("My brother spoke well of you") with a one-step trust head start; a Nemesis's kin inherit the feud.
- Rating: M — good texture on top of grudge inheritance (1.1); same kinship-map dependency.
- Feasibility: Same kinship map as above.
- Overlap: (b).

**House-level relationship crystallization**
- Concept: Family/clan-level standing (Grey-Manes, Battle-Borns, the Silver-Bloods, Riften's Black-Briars) accumulated from member interactions, with named tiers (Feuding/Neutral/Faithful) gating clan-wide behavior: shop prices, door access, brawl provocations, letters.
- Rating: H — Skyrim's hand-authored family feuds are begging for a live layer; clan standing is world-in-motion at a scale one NPC ledger never reaches.
- Feasibility: Clan roster tagging (one-time); Python aggregation; drift-to-neutral over time.
- Overlap: (c) — aggregation to a collective unit is a new subsystem.

### 1.3 Secrets, hooks, leverage

**Typed, discoverable, provenance-tracked secrets**
- Concept: Chronicle assigns/derives secrets for named NPCs (skooma habit, Thalmor informant, affair, embezzling the Jarl) as beliefs with restricted witness sets; the player discovers them via overheard scenes, found letters, or investigation.
- Rating: H — secrets are the single best conversion of Chronicle's provenance engine into gameplay: *who knows what* becomes the play space.
- Feasibility: Seeding secrets touches lore-canon questions (keep them plausible, non-quest-breaking); overheard-scene delivery via existing dialogue scene tech — flag scene-injection method for research.
- Overlap: (b) — restricted-audience beliefs are a natural extension.

**Expose vs. Blackmail choice**
- Concept: On discovering a secret, player dialogue offers Expose (belief broadcast to the town — visible social consequences for the target) or Hold (gain a leverage token).
- Rating: H — a real strategic choice with visible divergent outcomes; expose-day in a small town is a trailer moment.
- Feasibility: Exposure = Chronicle rumor injection (already core); leverage token is new Python state.
- Overlap: (b).

**Hooks as spendable leverage currency**
- Concept: Held leverage becomes a spendable dialogue resource: force a merchant discount, make a guard look away once, force an NPC to share what they know — one hook per NPC, strong secrets reusable with cooldown.
- Rating: H — leverage-as-currency is the missing *verb* that makes knowing things fun rather than trivia.
- Feasibility: Dialogue-tree options conditioned on Python state; modest.
- Overlap: (c) — a genuinely new player-facing economy.

**Explicit spend-value table**
- Concept: Internal tuning table for what each hook strength can force; expose a coarse version in-fiction ("He'd do a lot to keep this quiet").
- Rating: L — necessary tuning, not a feature.
- Feasibility: Trivial.
- Overlap: (b).

**Forgiving-trait hook abandonment**
- Concept: Player can *release* leverage ("Your secret's safe with me — no strings") converting it into a strong gratitude/obligation belief.
- Rating: M — a mercy verb that differentiates playstyles and produces loyal informants; quiet but characterful.
- Feasibility: Trivial once hooks exist.
- Overlap: (b).

### 1.4 Stress / internal-friction engine

**Psychological buffer gating out-of-character action**
- Concept: Per-NPC strain value that rises when events force them against temperament (a pacifist priest witnessing a massacre, a proud merchant forced to beg after a dragon attack).
- Rating: M — only worth it as the *input* to visible breaks below; invisible strain alone is ledger.
- Feasibility: Python; needs temperament tags per named NPC (reuse stance tagging).
- Overlap: (c) — Chronicle has no internal-state axis.

**Threshold breakdown events**
- Concept: Strain thresholds fire visible break scenes: a shopkeeper closes up and drinks at the inn for days; a guard quits; a widow publicly confronts the Jarl. Fired as Chronicle-directed scenes, cited to real causes.
- Rating: H — this is post-dragon-attack *aftermath made human*, the exact "world reacts to world events" ask.
- Feasibility: Behavior changes = AI package swaps via C++ (schedule override tech — verify against Chronicle's current package toolkit); scenes via dialogue injection.
- Overlap: (c).

**Coping mechanisms**
- Concept: Post-break NPCs adopt persistent visible coping tags (drinks nightly, won't leave the temple, hostile to dragons topic) that dialogue references.
- Rating: M — persistence of aftermath; texture multiplier on breaks.
- Feasibility: Schedule tweak + dialogue tag; cheap once breaks exist.
- Overlap: (c) rider on breaks.

**Documented trait→stress-source table**
- Concept: Internal mapping of temperament→strain sources (Vengeful NPCs gain strain when *denied* revenge — nice inversion).
- Rating: L — tuning table, not player-visible.
- Feasibility: Trivial.
- Overlap: rider.

### 1.5 Memories (persistent life-event log)

**Structured, tagged, participant-linked memory objects**
- Concept: Chronicle's beliefs ARE this; ensure schema parity: timestamp, type tag, participants, visibility scope (public/private).
- Rating: M — foundational; rating reflects it's already the plan.
- Feasibility: Done/planned.
- Overlap: (a).

**Retention-by-rank**
- Concept: Named/important NPCs keep full memory; generic citizens keep only folded summaries (ties directly to the HIPIF folding pattern in the GM research).
- Rating: M — invisible but load-bearing for perf on hundreds of NPCs.
- Feasibility: Python memory-tiering; needed anyway.
- Overlap: (b).

**Memories queried by other systems, not just displayed**
- Concept: Every Chronicle-generated scene/quest/dialogue must cite a real memory ID as its motive — the assassin names the actual slight; the design rule from CK becomes a hard invariant.
- Rating: H — as an invariant it's the anti-hallucination guarantee that separates Chronicle from AI-Dungeon-style narrators.
- Feasibility: A validation rule in the Python engine; enforce at generation time.
- Overlap: (a) — elevate to invariant.

**Dedicated Memory Viewer UI**
- Concept: Diegetic version: NPCs can be *asked* what they remember about a topic/person; answers read from the belief store with provenance ("Heard it from Hulda").
- Rating: H — interrogation of the social graph as a conversation verb; also the player's debugging tool.
- Feasibility: Dialogue + LLM rendering of belief records; core-competency work.
- Overlap: (a) — surfacing.

### 1.6 Faction / collective political pressure

**Faction power ratio gating discontent**
- Concept: Per-hold civic discontent that accrues when grievance-holding citizens outweigh the Jarl's standing, fed by war levies, unresolved crimes, dragon damage without relief.
- Rating: H — a town that can visibly sour (and say why) is world-in-motion at the correct scale.
- Feasibility: Python aggregation over existing beliefs; surfaced via inn talk, guard barks, market scenes.
- Overlap: (c) — collective aggregation again.

**Hard eligibility gates independent of probability**
- Concept: Deterministic gates on who can join collective actions (guards can't join a mob against their own Jarl unless discontent > X; kin never join actions against family).
- Rating: M — invisible, but prevents absurd casts — a correctness feature for every generated group event.
- Feasibility: Python candidate filtering (same slot as IntelEngine's Pass1/2/3 filter).
- Overlap: (b).

**Per-trait join/leave multipliers**
- Concept: Temperament-weighted propensity table for joining protests, mobs, posses, conspiracies.
- Rating: L alone / feeds H systems — pure casting math.
- Feasibility: Trivial.
- Overlap: (b).

**Strong Hook or resource threshold can force membership**
- Concept: Player can spend leverage to force an NPC into (or out of) a collective action — pull a councilman out of the anti-player faction.
- Rating: M — connects the leverage economy to hold politics; good synergy piece.
- Feasibility: Trivial once both systems exist.
- Overlap: (b).

**Powerful-vassal council-seat demands**
- Concept: Influential citizens (clan heads, guild reps) demand standing with the Jarl; snubs create typed grievances the player can exploit or mend — visible court scenes at hold capitals.
- Rating: M — good hold-politics texture; risks lore-fragility in holds with thin courts.
- Feasibility: Scene injection at courts; moderate.
- Overlap: (b).

### 1.7 Council mechanics

**Voting-stance archetypes with scoring formulas**
- Concept: When a hold faces a Chronicle-generated decision (rebuild the burned district vs. fund the war levy), named advisors take archetype-driven positions and argue in court; outcome shifts hold state.
- Rating: M — deliberation scenes are alive-feeling but heavy to stage; better as occasional set-pieces than a running system.
- Feasibility: Multi-NPC scene staging is the hard part — flag for research.
- Overlap: (c).

**Concrete vote thresholds keyed to opinion**
- Concept: Player lobbying (persuade, bribe, leverage) visibly flips advisor positions before a court decision.
- Rating: M — turns hold decisions into playable social puzzles.
- Feasibility: Depends on 1.7.1.
- Overlap: (c) rider.

**Council obstruction firing penalties**
- Concept: Skip — Skyrim courts lack the standing council structure to make firing legible.
- Rating: L — insufficient vanilla scaffolding.
- Feasibility: n/a.
- Overlap: n/a.

### 1.8 Schemes / plots

**CK2 plot power as contribution ratio**
- Concept: NPC conspiracies (against the player, a Jarl, a rival clan) gather power from recruited members' influence; power level gates which escalation events can fire.
- Rating: M — engine math for the H item below.
- Feasibility: Python.
- Overlap: (c).

**Personal vs. Hostile scheme split w/ Secrecy+Breach**
- Concept: Hostile schemes against the player run with a Secrecy meter; each recruited agent is a potential leak — a Friend tips you off, a bribed agent defects, 5 breaches collapse the plot publicly. The player can *counter-investigate* using the same belief tools.
- Rating: H — being the *target* of a legible, leaky conspiracy is a story generator: forewarning, betrayal, exposure day all fall out of provenance.
- Feasibility: Fully Python until the ambush/confrontation fires (existing IntelEngine-style dispatch pattern); strong fit.
- Overlap: (c) — the headline-grade new subsystem in the CK section.

**Agent recruitment opinion/trait-scored**
- Concept: Conspiracies recruit from real grievance-holders (memory-cited); no grievance pool in town = no plot possible.
- Rating: H — grounding rule that makes conspiracies feel earned, not random.
- Feasibility: Python casting filter.
- Overlap: (b).

**Discovery consequences explicit and stacking**
- Concept: Exposed plotters take visible social damage (kin distancing, shop boycotts, arrest if evidence suffices), which itself seeds the next grudges.
- Rating: M — closes the loop; consequence-of-consequence.
- Feasibility: Reuses exposure machinery.
- Overlap: (b).

**Scheme-specific outcome tables (Sway/Befriend/Seduce)**
- Concept: Player-initiated social campaigns as multi-day background schemes: Befriend (chance-gated warm-up visits), Sway an advisor before a vote.
- Rating: L–M — background dice for social progress risk feeling gamey vs Chronicle's "everything from real events" identity; only adopt the *structure* (multi-step, interruptible), not the RNG.
- Feasibility: Easy.
- Overlap: (b).

### 1.9 AI decision-making

**ai_chance scoring idiom (base + additive + multiplicative vetoes)**
- Concept: Adopt as Chronicle's standard decision function for all NPC choices: base weight + belief-derived modifiers + hard vetoes (kinship, fear, relations).
- Rating: M — architecture, invisible but everything sits on it; pairs with LLM as tie-breaker/flavor rather than decider.
- Feasibility: Python; aligns with Slice-of-Life's deterministic-core principle from §7.3.
- Overlap: (b).

**Hidden personality parameters (boldness, vengefulness, honor...)**
- Concept: 6–8 hidden per-NPC dials modulating all scoring (who retaliates, who forgives, who gossips, who reports crimes).
- Rating: H — the "expected randomness" engine: outcomes vary by person and are retroactively explainable, which is exactly what makes sim gossip about *people* not systems.
- Feasibility: One-time tagging (LLM-assisted from vanilla dialogue/lore per NPC, human-spot-checked); Python.
- Overlap: (c) — Chronicle has events and beliefs but no personality layer.

**Two-layer visible/hidden state split**
- Concept: Deliberate doctrine: temperament visible through behavior/dialogue only, never as displayed stats.
- Rating: M — doctrine, not feature; prevents the Twilight-Bazaar OCEAN failure (invisible detail) *and* the spreadsheet failure (visible numbers kill fiction).
- Feasibility: Free.
- Overlap: doctrine.

**AI archetype bucketing**
- Concept: Bucket NPCs into named behavior archetypes (Zealot, Opportunist, Gossip, Stoic) that pick response *patterns* to events, on top of the dials.
- Rating: M — compresses tagging effort and gives dialogue writers/LLM stable voices to target.
- Feasibility: Easy.
- Overlap: (c) rider on personality.

### 1.10 Dread / intimidation

**Dread vs Boldness threshold gates**
- Concept: A fear axis orthogonal to disposition: NPCs who've witnessed the player's violence (or heard credible rumors of it) become Intimidated/Terrified — comply while resenting, won't join plots, may flee shops when you enter. Per-observer, provenance-cited (respects the no-global-reputation rule inherently).
- Rating: H — fear-with-provenance is dramatic, visible (flinches, compliance, emptied rooms), and mechanically distinct from liking.
- Feasibility: Python axis + bark/behavior hooks; strong fit.
- Overlap: (b) — new axis over existing witness machinery.

### 1.11 Event-engine architecture lessons

**MTTH vs on_action triggering**
- Concept: Chronicle standard: consequences fire on_action (state change) wherever possible; MTTH-style random polling only for background color.
- Rating: M — architecture doctrine that keeps causality legible.
- Feasibility: Free.
- Overlap: doctrine.

**"Opinion-modifier soup" failure mode**
- Concept: Cap simultaneous active modifiers per relationship; crystallize overflow into named states (1.2) instead of stacking numbers.
- Rating: M — a guardrail with direct design consequence (crystallization becomes the pressure valve).
- Feasibility: Free.
- Overlap: doctrine.

**Sculptural vs Generative hybrid**
- Concept: Chronicle's storyteller = storylet layer (authored beat shapes) over continuous belief sim — adopt explicitly as the architecture sentence for the GM tier.
- Rating: H — it *is* Chronicle's architecture thesis, now with a literature name.
- Feasibility: Already the direction.
- Overlap: doctrine.

**Emergence-detection thesis (persistent readable records)**
- Concept: Every consequential event leaves a player-discoverable record (dialogue, letters, courier news) so chains can be inferred.
- Rating: H — the difference between simulation and *story* is exactly this inferability.
- Feasibility: Delivery channels needed (couriers, inn talk, notice boards).
- Overlap: (a) — surfacing doctrine.

### 1.12 CK's genre neighbors

**King of Dragon Pass clan-level state + advisor legibility**
- Concept: Hold-level (not per-NPC) mood/stability advised diegetically — the player's housecarl/steward comments on hold state and predicts reactions ("Raise the levy now and the Grey Quarter will boil over").
- Rating: H — an in-fiction advisor is the cheapest legibility surface for all collective state, and Skyrim gives every player a housecarl.
- Feasibility: Housecarl dialogue driven by Python summaries; easy-moderate.
- Overlap: (a)/(c) — new advisor role surfacing collective state.

**Wildermyth contextual-casting trigger engine**
- Concept: Storylet library where every Chronicle beat declares role preconditions and casts *real qualifying NPCs* (the actual widow, the actual rival) — the §7.2 role-casting pattern as the generation core.
- Rating: H — the single most transferable pattern in the catalog per its own literature; makes generated content read authored.
- Feasibility: Python storylet engine; the GM harness research already points here.
- Overlap: (c) — the generation layer itself.

**Wildermyth "unreadable depth is wasted depth"**
- Concept: Kill-criterion: any sim feature with no surfacing channel within one milestone gets cut or shelved.
- Rating: H as doctrine — it's the exact critique that started this whole pivot (grudges were unread depth).
- Feasibility: Free.
- Overlap: doctrine.

**Total War "green but seceded" failure**
- Concept: Guardrail: any variable that can trigger a betrayal/defection must have been surfaceable to the player beforehand (warnings via advisor/rumors).
- Rating: M — trust-preserving rule for the conspiracy system.
- Feasibility: Free.
- Overlap: doctrine.

**Bannerlord control group (number without presentation = nothing)**
- Concept: Negative example; enforces that every scalar ships with threshold→action catalog + presentation.
- Rating: M — doctrine.
- Feasibility: Free.
- Overlap: doctrine.

**Twilight Bazaar: bargaining chips (knowledge as inventory objects)**
- Concept: Secrets/rumors the player learns become *journal-visible knowledge items* (with source and reliability) that can be told, sold, traded, or lied about — knowledge as usable inventory, including planting false rumors (Chronicle's mutation system run deliberately).
- Rating: H — solves "players forget what they know about whom" and gives rumor mutation a player-facing verb; deeply on-brand.
- Feasibility: Journal UI + dialogue verbs; the lie path needs careful belief-injection design (flag: false-belief provenance modeling).
- Overlap: (b)/(c) — player-held knowledge inventory is new.

**Twilight Bazaar: verb framing ("Gossip" vs "Socialise")**
- Concept: Name Chronicle's player verbs evocatively and specifically (Gossip, Confide, Accuse, Spread Word) — the verb names do interpretive work.
- Rating: M — cheap, real effect on perceived depth.
- Feasibility: Free.
- Overlap: doctrine.

---

## 2. Kenshi

### 2.1 World states / town overrides

**Boolean world-state flags → town overrides + wilderness spawns**
- Concept: Per-settlement state vector (prosperity, damage, occupation, leadership) driven by Chronicle events (dragon attacks, war progress, player acts), expressed through the channels Skyrim allows: merchant inventories/prices, guard counts, NPC schedules, enabled/disabled clutter piles, refugee spawns.
- Rating: H — town-level visible change IS "a world in motion"; this is the macro payoff layer for everything else.
- Feasibility: No geometry edits allowed, so expression = actor/inventory/schedule/light-object toggles via C++; achievable but the expression vocabulary needs a dedicated design pass (flag: verify which world-change verbs the plugin can safely persist across saves).
- Overlap: (c) — settlement state is a new aggregate.

**Single-leader vs multi-leader collapse patterns**
- Concept: Named-NPC dependency graphs per institution: kill/jail the Silver-Blood head and Markarth's economy shifts; some institutions need multiple removals.
- Rating: H — "important people matter structurally" is deeply Skyrim-compatible (the game already has replacement Jarls for the civil war).
- Feasibility: Hand-author dependency graphs for the ~30 institutions that matter; Python evaluates, C++ expresses.
- Overlap: (c).

**Kill/imprison equivalence + release-rollback**
- Concept: "Neutralized" = dead OR jailed; freeing a jailed figure rolls consequences back — enabling rescue-mission stories the storyteller can dispatch.
- Rating: M — mostly invisible logic, but it unlocks the rescue/restore story family.
- Feasibility: Python condition semantics.
- Overlap: (b).

**Small fixed override vocabulary (whole-record swap)**
- Concept: Adopt the *smallness* lesson: 5–6 named settlement states (Prosperous, Strained, Damaged, Grieving, Occupied, Emptied) with defined expression bundles, not a continuum.
- Rating: M — discrete named states are legible and testable; a continuum isn't.
- Feasibility: Easy; the bundles are the work.
- Overlap: design shape for 2.1.1.

**Priority-ranked override chains**
- Concept: Deterministic precedence when multiple states apply (Occupied beats Prosperous).
- Rating: L — necessary plumbing.
- Feasibility: Trivial.
- Overlap: rider.

**Swap only while unloaded**
- Concept: Apply settlement-state changes only when the player is away from the cell; arriving to find it changed (with citable causes) rather than watching it pop.
- Rating: M — a correctness rule that doubles as drama ("I came back and the market was half-empty").
- Feasibility: C++ cell-load hooks; standard.
- Overlap: doctrine.

**Player-owned buildings collateral**
- Concept: Guardrail: never let settlement states damage player homes/containers.
- Rating: M — save-safety trust; the Kenshi pain point inverted into a rule.
- Feasibility: Exclusion list.
- Overlap: doctrine.

**Faction HQ relocation**
- Concept: Skip for v1 — Skyrim factions are too asset-anchored to relocate credibly without geometry edits.
- Rating: L — infeasible under the no-geometry rule.
- Feasibility: Blocked.
- Overlap: n/a.

**"Broken squad" degradation instead of deletion**
- Concept: Shattered groups persist as remnants: a broken bandit clan becomes scattered desperate robbers with dialogue citing their fall; a purged Thalmor patrol route spawns vengeful stragglers.
- Rating: H — defeat leaving visible wreckage-people instead of silence is cheap and extremely alive-feeling.
- Feasibility: Spawn dispatch via the IntelEngine-style pattern; moderate.
- Overlap: (c) — remnant modeling is new.

**Power vacuums grow rival footprints**
- Concept: Clearing a bandit fort lets a rival group (or Forsworn, or wolves, or a legitimate patrol) claim the vacuum after N days, chosen by proximity+relations — the player's clean-up visibly reshapes who holds the map.
- Rating: H — consequence-of-absence is the sim talking without the player doing anything; direct dragon/war synergy (attacks create vacuums).
- Feasibility: Skyrim already has cell respawn; Chronicle overrides *what* respawns via C++ — flag: verify safe respawn-override technique.
- Overlap: (c).

**Zone-level spawn-table retuning**
- Concept: Road danger as visible state: war escalation or a fallen leader changes which encounters spawn on which roads; couriers/innkeepers warn about specific roads.
- Rating: H — players feel the world through roads; road-state + warnings is legibility built in.
- Feasibility: Encounter-zone spawn overrides via C++ (same research flag as above).
- Overlap: (c).

**Reactive World vs Living World modding lesson**
- Concept: Doctrine: fewer, well-expressed settlement branches beat many fragile ones; every branch needs a restoration path.
- Rating: M — scope discipline with a shipped-evidence pedigree.
- Feasibility: Free.
- Overlap: doctrine.

### 2.2 Faction relations scalar

**Two-threshold scalar (hostile / allied package)**
- Concept: Per-faction player standing with exactly two named thresholds, where *allied* is a rich behavior bundle (guards stop hassling, members share rumors early, heal you, defend you) — not a number, a package.
- Rating: M — the bundle is the insight; Skyrim factions partially do hostility, never the positive package.
- Feasibility: Per-behavior C++ hooks; incremental.
- Overlap: (b).

**Witnessed crime overrides the scalar**
- Concept: Already Chronicle doctrine (provenance over aggregate); keep as invariant.
- Rating: M — identity-confirming invariant.
- Feasibility: Done.
- Overlap: (a).

**Documented relation-delta table (incl. Pacifiers)**
- Concept: A "Pacifier" NPC per major faction — pay/quest to mend standing, who *refuses with a stated reason* if your record makes mending absurd, and names what you'd have to fix first.
- Rating: H — refusal-with-reason is provenance speaking; reputation repair as gameplay, not menu.
- Feasibility: Dialogue + Python conditions; easy.
- Overlap: (b).

**No passive decay of faction relations**
- Concept: Faction-level standing doesn't decay on its own; only acts (or Pacifiers) move it. Individual emotional beliefs decay; institutional memory doesn't.
- Rating: M — a principled asymmetry that reads as "institutions keep books."
- Feasibility: Config.
- Overlap: (b).

**Alliance knock-on costs**
- Concept: Publicly aiding one side (civil war, Dawnguard/Volkihar, clan feuds) applies itemized standing costs with their named rivals, told to the player's face by affected NPCs.
- Rating: H — choices with visible social prices across the map = world reacting to allegiance, the civil-war ask directly.
- Feasibility: Python fan-out on quest-state changes read via C++.
- Overlap: (b).

### 2.3 Crime, bounty, legal system

**Strictly non-telepathic crime (witness LOS events)**
- Concept: Chronicle's founding principle; harden as invariant and *market it* — "crime in Chronicle spreads at the speed of gossip, not telepathy."
- Rating: H — the fix to Skyrim's most-mocked system (psychic guards) is a headline bullet on its own.
- Feasibility: Requires suppressing/intercepting vanilla bounty broadcast — flag: research the safe interception point (known hard problem in Skyrim modding).
- Overlap: (a) — core identity, needs the engine-side interception to be real.

**Published crime-severity table (expiry, sentence, bounty)**
- Concept: Typed crimes with per-type expiry and sentence, tracked per-hold with provenance (who reported).
- Rating: M — structure under the H item above.
- Feasibility: Python.
- Overlap: (b).

**Linear bounty-expiry / notoriety threshold**
- Concept: Small crimes are forgotten by communities over time (witness beliefs fade); infamous acts never fade and must be *resolved* (fine, quest, Pacifier).
- Rating: M — forgiveness curves make crime playable rather than permanent-stain.
- Feasibility: Python decay curves per belief type.
- Overlap: (a)/(b).

**Recognition scales with bounty + takes time**
- Concept: Being recognized is a process: guards who've *seen the notice* (a belief!) recognize fastest; civilians only know infamous descriptions; disguise/timing matters; recognition fires a visible double-take bark before action.
- Rating: H — moment-to-moment tension from the belief system, felt every time you walk into town.
- Feasibility: Per-NPC recognition state in Python + bark/behavior hooks; notice-distribution as literal courier objects.
- Overlap: (b) — recognition-as-belief is a natural but new application.

**Prison converts to slavery in some jurisdictions**
- Concept: Jurisdictional flavor: Markarth sends prisoners to Cidhna Mine (vanilla-consistent!), Riften's jail is bribable, Windhelm's is harsh to elves — hold legal *character* expressed through what arrest means.
- Rating: M — differentiates holds; partially vanilla already, Chronicle deepens.
- Feasibility: Mostly dialogue/outcome variation; moderate.
- Overlap: (b).

**Delegated legal systems (shared wanted-list namespaces)**
- Concept: Hold-level wanted lists with explicit sharing rules: Imperial-held holds share bounty knowledge via couriers (travel time = spread time); Stormcloak holds separately; independent enclaves (Forsworn, Orc strongholds) keep their own — and the sharing topology *changes as the civil war moves*.
- Rating: H — legal-knowledge topology that reorganizes with the war is the civil-war reactivity ask in concrete, provenance-native form.
- Feasibility: Python graph + courier events; delightful fit.
- Overlap: (b) — hold-level belief namespaces extend the engine naturally.

**Only occupation-typed characters issue bounties**
- Concept: Only stewards/captains/Jarls can formalize a bounty; a witnessed crime with no surviving authority reachable = no bounty (kill the witness before they report — dark but coherent).
- Rating: M — makes the report *chain* tangible and interceptable.
- Feasibility: Python role checks.
- Overlap: (b).

### 2.4 AI packages / squad substrate

**Squads + AI Packages + Dialogue Packages data model**
- Concept: Chronicle's dispatch unit = "party" (roster, purpose, package set, dialogue set), mirroring how the engine already thinks.
- Rating: M — internal shape, matches SkyrimNet/IntelEngine precedent.
- Feasibility: Established pattern.
- Overlap: (b).

**AI contracts (dialogue-issued temporary overrides)**
- Concept: NPCs can ask *the player* for temporary help (walk me to Rorikstead, guard my shop tonight) generated from real needs (fear beliefs, threats) — and remember the answer.
- Rating: H — NPCs initiating requests from real state flips the usual direction of Skyrim interaction; highly visible.
- Feasibility: Dialogue + escort package dispatch (IntelEngine proves the pattern).
- Overlap: (b).

**Off-screen fully suspended, faked via flags**
- Concept: Adopt honestly: Chronicle doesn't simulate off-screen movement; it advances state via events + travel-time math, and *presents* arrivals/consequences (RimWorld/Kenshi both prove players can't tell).
- Rating: M — perf doctrine enabling scale on the Mac mini.
- Feasibility: Free (it's the cheap option).
- Overlap: doctrine.

**Shallow dialogue-boolean memory (anti-pattern)**
- Concept: Negative example — Chronicle's per-encounter provenance is precisely the upgrade; cite in marketing comparisons.
- Rating: L — nothing to build.
- Feasibility: n/a.
- Overlap: (a).

---

## 3. Shadows of Doubt

**23-field Citizen Profile**
- Concept: Skip wholesale ID fields (blood type, prints); adopt the *load-bearing name* lesson: every Chronicle-tracked citizen is findable by name via asking around (NPCs give directions from their own knowledge).
- Rating: M — name-driven wayfinding through the social graph is quiet but constant texture.
- Feasibility: Python knowledge queries + dialogue.
- Overlap: (b).

**Static/dynamic/relational data split (social-network graph)**
- Concept: Explicit per-NPC relational graph (kin, employer, friends, drinking buddies) — the substrate for inheritance, gossip routing, and casting.
- Rating: H — the graph IS the rumor topology; hand-author once from vanilla data and everything else improves.
- Feasibility: One-time data pass (LLM-assisted extraction from vanilla dialogue/relationships, reviewed); Chronicle likely has partial.
- Overlap: (a)/(b) — formalize and complete.

**Deterministic trace instantiation (receipts, ledgers, footprints)**
- Concept: Selected Chronicle events leave physical evidence objects: a threatening letter, a torn journal page, blood by the stable, a merchant's ledger discrepancy — placed in-world, readable, provenance-linked.
- Rating: H — physical evidence makes the invisible sim *touchable* and enables player-driven investigation of NPC schemes.
- Feasibility: Object spawning + book-text generation via C++; placement heuristics need care (flag: safe container/world placement).
- Overlap: (c) — evidence generation is new.

**Periodic LOS sighting loop → memory records**
- Concept: Chronicle's witness system; add the *sighting record* nuance for movement (who was seen where/when) feeding alibis below, but sample sparsely (named NPCs, notable moments) for perf.
- Rating: M — enabling layer for investigation play.
- Feasibility: C++ LOS sampling exists in SkyrimNet-adjacent tech; budget-bound.
- Overlap: (b).

**Three-phase memory decay (Precise→Fuzzy→Purged)**
- Concept: Witness beliefs degrade in *specificity*, not into falsehood: "Ralof stabbed him at midnight" → "a Nord in a blue coat, late that night" → gone; degradation rate scales with familiarity and distinctiveness.
- Rating: H — specificity decay makes rumor content feel human and makes *time pressure* a mechanic (ask witnesses early).
- Feasibility: Python belief-schema feature; LLM renders the vague versions.
- Overlap: (b) — Chronicle mutates in transit; decay-in-place is the missing sibling.

**Facts provenance graph with reliability-weighted edges**
- Concept: Internal reliability weighting on belief edges (eyewitness > secondhand > tavern chain) governing NPC confidence and willingness to act ("I'd not hang a man on tavern talk").
- Rating: H — reliability-gated *action* is what makes provenance mechanically real: a guard needs an eyewitness, a gossip needs nothing.
- Feasibility: Python edge weights + action thresholds.
- Overlap: (b).

**Fingerprint/name resolution chain**
- Concept: Skip forensics; adopt the resolution-chain shape for *rumor subjects*: "a scarred Redguard woman" resolves to a name only when a knower connects description to identity — including wrongly.
- Rating: M — misidentification stories (the wrong person blamed) fall out naturally and are excellent drama.
- Feasibility: Python identity-resolution beliefs; LLM dialogue.
- Overlap: (b).

**Per-citizen alibi timelines**
- Concept: NPCs can account for their whereabouts from schedule+sighting records; lies detectable by cross-referencing witnesses — the player-as-investigator loop for Chronicle-generated crimes.
- Rating: M — high ceiling, but only worth building after evidence objects + sightings exist; sequencing note, not doubt.
- Feasibility: Python queries over schedule history; moderate.
- Overlap: (c).

**Citizens can lie**
- Concept: NPCs with incriminating-looking truths (or loyalty conflicts) may lie, governed by temperament dials; lies are beliefs-about-what-I-said, discoverable via contradiction.
- Rating: H — lying NPCs elevate every conversation from database query to judgment call; Chronicle's provenance makes catching them fair.
- Feasibility: Python + careful LLM constraint (the lie must be *chosen* by the sim, rendered by the LLM — Slice-of-Life division).
- Overlap: (c).

**Press-appeal mechanic**
- Concept: Player can pay a courier/town-crier to publicize a question or accusation hold-wide — a broadcast rumor-injection lever with cost, flushing out knowers (or panicking the guilty).
- Rating: M — a fun deliberate use of the rumor engine; also the storyteller can use it against the player.
- Feasibility: Rumor injection + response casting; easy on the engine.
- Overlap: (b).

**Batch-precompute-then-deviate scheduling**
- Concept: Chronicle plans NPC days in batch (Python, off the frame budget) and only computes deviations live — the perf shape for everything schedule-touching.
- Rating: M — architecture; proven at hundreds-of-citizens scale.
- Feasibility: Native to the external-service design.
- Overlap: doctrine.

**Body-discovery failsafes**
- Concept: Every consequential hidden state (a body, a planted letter, an unexposed plot at maturity) carries layered guaranteed-discovery escalations so no story dead-ends silently.
- Rating: H — as a *generalized invariant* it's the anti-"unsolvable generated content" rule from §7.4; every dispatched story must carry its own failsafe.
- Feasibility: Python: each storylet declares discovery ladder at authoring time.
- Overlap: doctrine → engine invariant.

**Case Generator (provenance-anchored intervention)**
- Concept: Chronicle's storyteller commits crimes/schemes *through the sim*: pick archetype + cast real relationship (the embezzling steward robs the actual strongroom; the jealous suitor attacks the actual rival), so every clue traces to real state. Identical to §7 role-casting; listed here as the crime-flavored instance.
- Rating: H — the pattern that makes generated mysteries fair-play solvable.
- Feasibility: Storylet engine + evidence objects.
- Overlap: (c) — the generative director acting through sim state.

---

## 4. Nemesis System

*(Design rule in force: no automatic rank-rewriting hierarchies; patent boundary respected — single-NPC memory, per-observer grudges, and standalone succession are explicitly free.)*

**Procedural enemies from base template (appearance, voice, personality, weakness)**
- Concept: Named recurring *persons* generated at consequence-moments only (the bandit who fled, the survivor of the massacre): name, epithet, temperament dials, a remembered weakness/tell the player learned.
- Rating: H — named survivors are the single most repeatable "the world remembers me" clip generator.
- Feasibility: Actor generation/renaming via C++ (SkyrimNet ecosystem proves renaming/persistent custom actors — verify Chronicle's technique); voice = TTS pipeline already planned.
- Overlap: (c).

**Combat-outcome verbs mutate persistent state (death/flight/scar)**
- Concept: Fights Chronicle observes produce typed persistent consequences: fled enemies remember and resent; a player defeat creates a boastful survivor; near-death survivors carry visible gear/behavior changes and reference the specific fight.
- Rating: H — the beloved core, fully patent-free at single-NPC scope.
- Feasibility: Combat-event hooks via C++; scarring = equipment/face-tint swaps within safe limits (flag: verify persistent appearance-edit safety).
- Overlap: (b) — combat consequences into the belief engine.

**Combinatorial dialogue selection (archetype × rank × history × condition)**
- Concept: Chronicle's LLM dialogue conditioned on exactly these four axes, with the *history* slot always a real memory ID (the §1.5 invariant).
- Rating: M — Chronicle's LLM already beats fragment combinatorics; the lesson is the conditioning axes.
- Feasibility: Prompt-context discipline.
- Overlap: (a).

**Ranked hierarchy with automated vacancy-filling**
- Concept: DISALLOWED as automatic chains per design rule. Permitted narrow form: standalone succession — a killed bandit chief's gang gets a *storyteller-chosen* successor (an existing named member, cast by the storylet engine, announced via rumor), no cascading parameter rewrites.
- Rating: M — succession-as-story keeps the good part (power abhors a vacuum) without the encumbered combination.
- Feasibility: Python casting; explicitly route around US 10,926,179 B2's two-NPC-linkage + hierarchy + surfacing combination — keep a written design memo documenting the avoidance.
- Overlap: (b).

**Autonomous background hierarchy events (duels, hunts, feasts)**
- Concept: Background *social* events among tracked NPCs (a feud brawl, a wedding, a falling-out) that fire while the player is elsewhere and arrive as rumor/changed state — Chronicle's world moving on its own.
- Rating: H — off-screen social motion delivered as news is the "alive without me" proof players cite.
- Feasibility: Pure Python events + rumor delivery; cheap and high-yield.
- Overlap: (b).

**Domination/betrayal (Blood Brother revenge invasion)**
- Concept: Skip domination (no player mind-control in Chronicle's fiction); keep the *loyalty-conflict* kernel: an NPC forced to act against a bonded ally (via player leverage) can later betray the player at a dramatic moment, with the storyteller timing it.
- Rating: M — betrayal-as-consequence-of-coercion closes the leverage economy's moral loop.
- Feasibility: Python state + storyteller timing.
- Overlap: (b).

**Cross-player vendettas**
- Concept: Skip — narrowest patent edge, no multiplayer in scope.
- Rating: L.
- Feasibility: Blocked/out of scope.
- Overlap: n/a.

**Tuned probability curves for pacing (rivalry caps, ambush throttles)**
- Concept: Hard caps: max active named rivals, min days between hostile dispatches at the player, no converging simultaneous ambushes — pacing hygiene stolen wholesale.
- Rating: M — invisible but the difference between drama and harassment.
- Feasibility: Config in the dispatch layer (IntelEngine's scarcity rule is the same lesson independently reached).
- Overlap: doctrine.

**Only named captains carry state; masses are fodder**
- Concept: Chronicle's tiering doctrine confirmed: full state for named/promoted NPCs, folded summaries for the crowd — the feeling of a living world comes from a small stateful roster.
- Rating: H as doctrine — it's the perf-and-design answer to "how does this run on one Mac mini."
- Feasibility: Native.
- Overlap: doctrine.

**Feature-creep near-failure ("Christmas tree" meters)**
- Concept: Guardrail: cap simultaneous tracked axes per NPC; when tempted to add a meter, add a *named state* instead.
- Rating: M — scope discipline from the system's own developers.
- Feasibility: Free.
- Overlap: doctrine.

---

## 5. RimWorld

### 5.1 Mood / mental-break system

**Mood scalar + per-pawn break threshold with three risk bands**
- Concept: Per-NPC composure derived from active beliefs/strain (merged with CK §1.4 — build once); thresholds trait-modified per NPC.
- Rating: M — input layer; see breaks for the payoff.
- Feasibility: Python.
- Overlap: (c) — same subsystem as CK stress; unify.

**Weighted-random-within-band break selection (deterministic band, eligibility-filtered choice)**
- Concept: When an NPC breaks, the *severity* is deterministic from state, the *flavor* is weighted choice filtered by temperament and situation (a devout NPC prays obsessively; a drinker binges; a coward flees town) — the RimWorld selection shape verbatim.
- Rating: H — same crisis, different people, different visible behavior = characterful reactivity.
- Feasibility: Python selection + package swaps.
- Overlap: (c) rider on breaks.

**Named break catalogue across three intensities**
- Concept: Author ~15 Skyrim-appropriate break behaviors (shutters the shop, drinks for days, sleeps in the temple, picks a fight, leaves town for a relative's, rants in the market, stops speaking).
- Rating: H — the visible vocabulary of aftermath; directly the dragon-attack/war payoff.
- Feasibility: Each = schedule/package bundle + dialogue; the authoring is the cost.
- Overlap: (c).

**Multi-channel telegraphing (bar, alerts, itemized tooltip, visual indicator)**
- Concept: Diegetic telegraphs only: visibly troubled idles/barks before a break; companion/housecarl comments; innkeeper mentions so-and-so's state — no UI meters on NPCs.
- Rating: M — pre-break legibility makes breaks feel earned, not random.
- Feasibility: Bark conditions + advisor dialogue.
- Overlap: rider.

**Fixed recovery windows + intervention verbs**
- Concept: Breaks end on schedule OR via player intervention verbs (console them citing the cause, buy the drink, resolve the grievance, escort them home) — interventions leave gratitude beliefs.
- Rating: H — giving the player a *helping* verb converts aftermath from scenery into gameplay; underserved fantasy in Skyrim.
- Feasibility: Dialogue verbs + Python state.
- Overlap: (b) rider.

**Catharsis anti-spiral thought**
- Concept: Post-break NPCs get temporary resilience so towns don't death-spiral after mass-casualty events; DF's tantrum-spiral history is the cautionary twin.
- Rating: M — invisible stability engineering, mandatory at town scale.
- Feasibility: Python.
- Overlap: rider.

**"Story generator" pillar: loss AND recovery**
- Concept: Doctrine: every negative arc Chronicle can inflict must have an authored recovery arc (rebuilt stall, remarriage, return to town) — the world heals visibly too.
- Rating: H as doctrine — recovery arcs are half of "alive," and mods chronically forget them.
- Feasibility: Storylet library discipline.
- Overlap: doctrine.

### 5.2 Opinion / social-thought system

**Opinion computed on demand, never stored**
- Concept: Disposition = live query over active beliefs (Chronicle's model already); guarantees itemized "why" is always available.
- Rating: M — confirms architecture.
- Feasibility: Done.
- Overlap: (a).

**Thought_Memory duration/stack-limit/renew semantics**
- Concept: Adopt the stacking rules: repeat offenses renew rather than infinitely stack, capped counts, diminishing per-stack effect.
- Rating: L–M — tuning semantics preventing modifier soup.
- Feasibility: Python schema.
- Overlap: (b).

**Published numeric social-thought table**
- Concept: Author Chronicle's own belief-impact table (insult, gift, rescue, harmed-my-kin...) as data, moddable by users.
- Rating: M — moddability is Skyrim-community currency; expose the table as JSON.
- Feasibility: Config externalization.
- Overlap: (b).

**Social fights as probabilistic escalation**
- Concept: Grievance pairs can escalate to visible brawls (vanilla brawl system!) chosen by the storyteller at dramatic moments, with onlookers forming beliefs.
- Rating: H — public brawls citing real grudges = the sim erupting into the game layer where everyone can see it.
- Feasibility: Vanilla brawl scenes triggerable — verify triggering technique via C++; onlooker beliefs native.
- Overlap: (b).

### 5.3 Storyteller / pacing director

**MTB incident sampling, then plausible-composition backfill**
- Concept: Chronicle's storyteller schedules drama by pacing (per-hold and global MTB clocks) and *then* casts it from real state — pacing decides when, the sim decides what/who (alibi-generation marriage of director + provenance).
- Rating: H — this is Cassandra-for-Skyrim, the headline architecture; the catalog's single most direct pitch ancestor.
- Feasibility: The GM harness three-tier design already filed; this is its mid-tier scheduling policy.
- Overlap: (c) — the storyteller tier itself.

**Raid-point formula gating intensity and content types**
- Concept: Player-threat budget from level/gear/followers/deeds gating which hostile dispatches are eligible (no assassin squads at level 5), with the *threshold ladder* learnable through experience.
- Rating: M — fairness scaling for hostile content; keep inputs honest (see next).
- Feasibility: Python formula reading C++-provided player state.
- Overlap: (b).

**Wealth-gaming failure mode (director inputs get gamed)**
- Concept: Guardrail: pace off *events that actually occurred* (provenance-verifiable) rather than off launderable proxies like carried gold.
- Rating: M — Chronicle's provenance base is inherently the fix; write it down as a rule.
- Feasibility: Free.
- Overlap: doctrine.

### 5.4 Off-screen persistence (WorldPawns)

**Object-identity preservation across loaded/unloaded**
- Concept: Chronicle Python state is continuous regardless of cell loads (already true by architecture); never rebuild an NPC's social state from summaries.
- Rating: M — architecture confirmation with a shipped precedent.
- Feasibility: Native.
- Overlap: (a).

**Mothball tier (daily tick + catch-up before re-entry)**
- Concept: Distant NPCs tick daily; a catch-up pass runs when the player approaches their cell — the LOD scheme, concretely.
- Rating: M — the perf shape for 700+ tracked NPCs on one box.
- Feasibility: Python scheduler.
- Overlap: (b).

**Abstract per-day accounting for travelers**
- Concept: Traveling NPCs (couriers, refugees, war parties) advance by travel-time math, spawning real encounters only if the player crosses their projected path.
- Rating: M — cheap believable off-screen travel; feeds road-state.
- Feasibility: Python + conditional spawn dispatch.
- Overlap: (b).

**Reachability GC with critical-pawn pinning (+ both failure modes)**
- Concept: State GC for generated NPCs/beliefs: pin anyone referenced by active storylets, relations to named NPCs, or player memory; fold and discard the rest — with explicit tests for the over-keep (save bloat) and under-pin (broken references) failure twins.
- Rating: M — unglamorous save-health engineering that decides whether Chronicle survives 200-hour saves.
- Feasibility: Python GC + serialization discipline; test-heavy.
- Overlap: (c) — lifecycle management is new engineering.

**Alibi generation (retroactive consistent backstory)**
- Concept: Generated NPCs get history filled in only when inspected, constrained to consistency with already-visible facts — the storyteller's cast members arrive cheap and deepen on contact.
- Rating: H — the scaling trick that makes a big cast affordable AND the Hidden-Door ungroundedness caveat applies: once presented, facts are canon forever (write-once).
- Feasibility: Python lazy-fill with canon locking.
- Overlap: (b).

---

## 6. Dwarf Fortress

### 6.1 Stress / emotion → behavior

**Dual-axis stress (short-term + slow long-term, both required for breakdown)**
- Concept: Two-axis strain: acute (event-driven, fast decay) + chronic (slow accumulation); visible breaks need both — so towns weather one bad day but *sustained* war/hardship visibly hollows people out.
- Rating: H — chronic-hardship arcs are exactly the civil-war-reactivity texture: a border town two months into occupation *feels* different.
- Feasibility: Python; merge into the unified strain subsystem (CK 1.4 / RW 5.1).
- Overlap: (c) — same unified subsystem.

**Personality facets modulating stress mapping**
- Concept: Temperament dials (from §1.9) modulate gain/capacity/recovery per NPC.
- Rating: M — covered by the personality layer; confirm dials include resilience axes.
- Feasibility: Config.
- Overlap: (b).

**Branching breakdown outcome tree + permanent insanity flavors**
- Concept: Adopt the *branching* (repeat breaks escalate along a path: mope → melancholy; brood → violence) but soften permanence: reserve irreversible states (leaves Skyrim, permanent hermit) for rare storyteller-approved arcs.
- Rating: M — escalation paths give repeat hardship narrative direction; full DF permanence is too punishing for beloved named NPCs.
- Feasibility: Python state machine.
- Overlap: (c) rider.

**Strange moods (positive-flavored takeover producing an artifact)**
- Concept: Rare inspiration seizures: a smith obsessively forges a named masterwork citing a real event ("in memory of the Whiterun dead"), a bard composes a song about the player's actual deed that then *spreads as a rumor-object*.
- Rating: H — the world metabolizing events into named cultural artifacts is peak "alive," and the song-as-rumor is pure Chronicle.
- Feasibility: Item creation with generated names/descriptions via C++; song = dialogue/bard-performance injection (flag: bard-performance injection technique).
- Overlap: (c).

**True state-machine takeover (not job-queue insertion)**
- Concept: Breaks/moods replace the NPC's package stack entirely rather than adding a task — engine-honest and interruption-proof.
- Rating: L–M — implementation correctness note.
- Feasibility: C++ package-stack control.
- Overlap: rider.

**Pause-and-announce legibility**
- Concept: Diegetic equivalent of DF's announcement: significant break/mood onsets get a witnessed scene or immediate rumor ("Did you hear? Alvor smashed his own forge last night") — never silent state flips.
- Rating: H — the no-silent-consequences rule, positively framed.
- Feasibility: Rumor/scene dispatch; native.
- Overlap: (a) doctrine.

**Slow needs-driven recovery (+ Therapy Squad trick)**
- Concept: Recovery driven by fulfillable needs (temple, tavern, work, family time) that the *player can facilitate* (donate to the temple, fund the tavern, deliver the letter) — town recovery as playable content.
- Rating: M — pairs with 5.1 intervention verbs into a "helper" content family.
- Feasibility: Python needs + a few quest verbs.
- Overlap: (b).

**Tantrum-spiral failure cascade (deliberately dampened)**
- Concept: Guardrail twin of Catharsis: cap simultaneous breaks per settlement; chronic decline needs storyteller sign-off past a threshold.
- Rating: M — mandatory stability engineering.
- Feasibility: Config.
- Overlap: doctrine.

### 6.2 Memory (fixed-slot buffer)

**Three-tier fixed-slot store (8 ST / 8 LT / core)**
- Concept: Adopt bounded per-NPC salient-memory slots for *dialogue-priority* (what an NPC brings up unprompted) over the full belief store (what they can answer if asked) — bounded salience, unbounded knowledge.
- Rating: M — solves "which memory does the LLM lead with" with a principled, cheap structure.
- Feasibility: Python salience layer feeding prompt context.
- Overlap: (b).

**Grouped strongest-wins slot contention**
- Concept: One salient memory per category (grief, grudge, gratitude, fear); new events must beat the incumbent to displace it.
- Rating: L–M — salience tuning detail.
- Feasibility: Trivial.
- Overlap: rider.

**Time-gated promotion → core memory causes permanent personality change**
- Concept: Repeatedly-revisited memories can permanently shift an NPC's temperament dials (a betrayed merchant becomes suspicious *as a trait*, dialogue voice included) — events that change who people are, not just what they know.
- Rating: H — permanent character change from lived history is the deepest possible "the world remembers"; rare-by-design keeps it special.
- Feasibility: Python promotion rule + regenerate the NPC's voice-card; cheap.
- Overlap: (b) — striking extension.

**World-log vs personal-buffer split (historical figures only)**
- Concept: Chronicle keeps one global canonical event log; per-NPC memory stores references into it — dedup by construction, provenance native, and the log doubles as the storyteller's folded input.
- Rating: M — architecture with a 20-year-proven precedent.
- Feasibility: Likely close to current design; confirm.
- Overlap: (a).

### 6.3 Physical evidence / provenance objects

**Engravings/slabs generated from real historical links**
- Concept: Commissioned/emergent memorial objects: a plaque for dragon-attack victims naming real dead, a carved stone for a resolved feud — inspectable, generated from the event log.
- Rating: H — permanent physical world-changes that cite real history; the strongest allowed form of world mutation under the no-geometry rule (placed objects, not edited meshes).
- Feasibility: Placeable memorial activators with generated text via C++ — verify persistent placed-object safety in saves.
- Overlap: (c) — with 3.x evidence, forms the physical-provenance family.

**Memorial slabs resolve ghosts (bidirectional persistent link)**
- Concept: Unresolved deaths haunt socially (recurring grief beliefs, rumors, a widow who can't move on) until a resolution act (burial, justice, memorial) closes the loop — resolution as content.
- Rating: M — grief-with-closure arcs; strong for the aftermath family.
- Feasibility: Python arc + one quest verb.
- Overlap: (b).

**Artifact descriptions from creator's prefs + linked events; artifacts propagate**
- Concept: Named items with provenance records that *accumulate* (forged for X after Y; stolen by Z; recovered at W) — read on inspection, cited in dialogue, and the storyteller can build beats around famous objects.
- Rating: H — traveling provenance-objects thread otherwise-unrelated stories together; Skyrim's item system carries custom names/descriptions well.
- Feasibility: C++ item description writes; provenance in Python.
- Overlap: (c).

### 6.4 Rumor system

**Six confidence tiers of secondhand knowledge**
- Concept: Belief confidence tiers (witnessed / told-by-witness / heard-recently / heard-vaguely / legend) gating specificity of what NPCs can tell and what actions they'll take on it.
- Rating: M — merges with SoD reliability edges (3.x); build once.
- Feasibility: Python.
- Overlap: (b).

**Four nested scopes decaying simultaneously (individual/site/culture/civ)**
- Concept: Knowledge decays at individual level but persists longer as hold-level "common knowledge" and longest as legend — the player's great deeds fade from specifics into reputation into tavern legend, each tier voiced differently.
- Rating: H — hearing your own deed degrade into legend over 100 hours is a long-game payoff nobody else ships.
- Feasibility: Python scope tiers; LLM voices each register.
- Overlap: (b).

**Content never distorted in transit (DF's rule) — vs Chronicle's mutation**
- Concept: Chronicle deliberately breaks DF's rule (mutation is a feature) — adopt the *bounded* hybrid: facts-of-record (who died) resist mutation; interpretive content (why, how it looked) mutates freely; identity misattribution allowed at low confidence tiers.
- Rating: H — the mutation-bounds design decision is load-bearing for fairness (players must be able to trust *some* layer) and this is the principled boundary.
- Feasibility: Belief-schema field: mutability class.
- Overlap: (a) — refines the core mechanic.

---

## 7. AI directors / drama management

### 7.1 Shipped architectures

**Façade Beat Manager (+ its four failure modes)**
- Concept: Beat library with tension targets for Chronicle's scene director; inherit the fixes: NPCs must react to *each other's real state* (Chronicle has it), scale by staying scene-scoped, always establish an inciting frame ("since the dragon came...").
- Rating: M — historical template; the failure list is the value.
- Feasibility: Informs storylet schema.
- Overlap: doctrine.

**L4D Director (pacing FSM + multimodal pre-telegraphing)**
- Concept: Per-hold tension FSM (Calm → Rising → Crisis → Aftermath → Recovery) driving dispatch eligibility, with every state transition telegraphed *before* the intervention (rumors of movement, nervous guards, ravens) — never an untelegraphed spike.
- Rating: H — pacing states + mandatory telegraphs are the difference between a director and a random-event mod.
- Feasibility: Python FSM; telegraph = rumor/bark dispatch (native).
- Overlap: (c) — pacing layer of the storyteller.

**KoDP storylet engine (constraint match, priority bands, advisor modal)**
- Concept: Covered at 1.12/3.x (role-casting core + advisor surfacing); confirm priority-banding so must-fire beats outrank color.
- Rating: H (already counted).
- Feasibility: —
- Overlap: (c).

**PaSSAGE playstyle vector (+ drift and pacing-flattening costs)**
- Concept: Light playstyle sensing to *bias* (never filter) content mix; deliberately schedule contrast beats against the player's type — adopting the failure lesson as the design.
- Rating: L–M — playstyle adaptation is second-order polish; contrast rule is the keeper.
- Feasibility: Easy later.
- Overlap: (b) rider on storyteller.

**Concordia GM loop (intent → validate → mutate → narrate event statement)**
- Concept: THE integration contract: LLM proposes intents; the Python/C++ validator accepts/rejects against real state; only validator outcomes mutate state; the narrated Event Statement is what enters NPC memories.
- Rating: H — the anti-hallucination spine for every LLM-touching part of Chronicle; non-negotiable.
- Feasibility: Enforced pipeline shape; aligns with LLMaker/Orchestrated-Reality evidence below.
- Overlap: doctrine → hard architecture invariant.

**RimWorld Storyteller** — counted at 5.3; the headline framing candidate ("a storyteller for Skyrim").

### 7.2 Formal lineages

**IPOCL character-motivation requirement**
- Concept: Invariant: every storyteller-directed NPC action must be justified by that NPC's own state (motive-citing, no plot puppets) — reject beats that cast unwilling actors.
- Rating: H — the "no suicidal puppets" rule is the fairness core of believable direction.
- Feasibility: Casting-validator rule.
- Overlap: doctrine.

**DODM: intervention vocabulary too weak (authorship problem)**
- Concept: Lesson: invest in a *rich verb set* for the director (dispatch, rumor, scene, evidence, schedule change, settlement state, memorial) before investing in clever selection policy.
- Rating: M — sequencing wisdom: verbs before brains.
- Feasibility: Roadmap shape.
- Overlap: doctrine.

**Targeted Trajectory Distributions (steer toward a distribution, not one best story)**
- Concept: Storyteller optimizes for a healthy *mix* (per-hold variety targets across story families) rather than a single optimal arc — agency-preserving by construction.
- Rating: M — principled anti-railroading policy, cheap to encode as quotas.
- Feasibility: Python scheduling policy.
- Overlap: (b) rider.

**Mimesis intervention vs accommodation (+ revise-unseen-world rule)**
- Concept: When the player breaks a running beat: default accommodate (recast, replan); intervention never *undoes* player action; retroactive fixes only touch what no one has observed (write-once canon from 5.4).
- Rating: H — the player-derailment policy every dispatched story needs on day one.
- Feasibility: Storylet engine replan rules.
- Overlap: doctrine.

**Daggerfall QuestMachine (reputation-economy-embedded templates)**
- Concept: Radiant-style templates gated by Chronicle standing tiers, so the same template *means* differently at different standings (a desperate plea vs a formal commission) — and study Daggerfall Unity's open-source QuestMachine for the runtime-instantiated quest format.
- Rating: M — proven radiant shape; the embedding-in-economy lesson is the point.
- Feasibility: Directly studyable OSS precedent.
- Overlap: (b).

**Breault storylet quest engine (possibility space grows with state)**
- Concept: Confirmation: state-anchored generation scales with play rather than exhausting; design storylets to key off *accumulated* state (feuds, debts, legends) so late-game content is richer, not repetitive.
- Rating: M — validates the whole bet; encode as "prefer preconditions over templates."
- Feasibility: Authoring guideline.
- Overlap: doctrine.

**Questgram mixed-initiative caution**
- Concept: Human-authored storylet shapes + machine casting/filling — not fully autonomous story invention; matches the DungeonsDeep split.
- Rating: M — division-of-labor doctrine.
- Feasibility: Authoring pipeline.
- Overlap: doctrine.

**Storylet role-casting (the named highest-value pattern)**
- Concept: Counted at 1.12/3.x — the generation core.
- Rating: H.
- Overlap: (c).

### 7.3 LLM-narrator record

**AI Dungeon / Hidden Door failures (memory drift, ungroundedness, latency, over-smart NPCs)**
- Concept: Four inherited rules: state lives outside the model; facts are write-once at presentation; latency budget enforced per tier (fast local mouth, slow cloud brain); NPCs deliberately imperfect so the player has room to matter.
- Rating: H — the requirements document for the LLM integration, from the category's gravestones.
- Feasibility: Already reflected in the three-tier + KV-cache plan.
- Overlap: doctrine.

**NCP-Bench numbers (42% survival past 20 turns; <14% commitments kept)**
- Concept: Chronicle's answer: commitments live as Python constraint records checked per beat, not as model memory; adopt NCP's Invariant/Ordering/Achievement typing for storylet commitments.
- Rating: M — a typed-commitment schema with benchmark pedigree.
- Feasibility: Python.
- Overlap: (b).

**Orchestrated Reality (canonical JSON tree; Plan→Diff→Validate→Apply)**
- Concept: Adopt the delta pipeline for all storyteller writes: schema-validated diffs against canonical state, content-hashed, rejected on conflict — and schematize *everything* that must not drift.
- Rating: H — the concrete write-path design for the Concordia contract.
- Feasibility: Python engineering; well-specified precedent.
- Overlap: doctrine → engineering spec.

**Neuro-symbolic TSL automata (96% vs 15% adherence)**
- Concept: For hard invariants (never reveal X before Y; never kill quest-critical NPCs), a deterministic automaton gates what the LLM is even *prompted* to do per turn — constraints enforced outside the model.
- Rating: M — heavyweight; reserve for the few invariants that justify formal enforcement.
- Feasibility: Simplified FSM version is enough; full TSL synthesis is research-grade.
- Overlap: (b) rider.

**Slice of Life (deterministic core decides; LLM renders only; no dialogue→state feedback)**
- Concept: Chronicle's division exactly: sim decides outcomes, LLM voices them; player dialogue affects state only through validated intent extraction, never through the LLM's own narration.
- Rating: H — with Concordia, the two-sentence constitution of the whole integration.
- Feasibility: Pipeline discipline.
- Overlap: doctrine.

**LLMaker function-calling validity gate (0 invalid vs never-passing free-form)**
- Concept: All LLM→engine communication is structured function calls / schema'd JSON — no free-text parsing anywhere in the write path.
- Rating: M — measured, decisive; already best practice.
- Feasibility: Free (design choice).
- Overlap: doctrine.

**Drama Llama (authored pivot points, free improvisation between)**
- Concept: Chronicle beats declare 3–4 hard pivot conditions; everything between improvises freely — the looseness dial with a named precedent.
- Rating: M — the authoring ergonomics for storylet writers.
- Feasibility: Storylet schema.
- Overlap: (b).

**Symbolically Scaffolded Play (role-differentiated rigidity)**
- Concept: Rigid scaffolds for functional roles (quest-givers, guards, stewards); loose scaffolds for color roles (drunks, bards, children) — constraint budget spent where correctness matters.
- Rating: M — a per-role prompting policy, cheap and evidence-backed.
- Feasibility: Prompt-template tiers.
- Overlap: doctrine.

**Friends & Fables ACE-1 (face/truth split; atomic memory units; View Context)**
- Concept: Three adoptions: engine-is-truth (have it), atomic single-fact memory records ranked by type/recency/relevance (Chronicle's beliefs — confirm atomicity), and a debug/transparency View Context surface showing what the GM saw when it generated a beat (dev tool first, curious-player MCM later).
- Rating: H — independent commercial convergence on Chronicle's exact architecture, plus View Context is a trust feature the community would love.
- Feasibility: Logging + MCM panel.
- Overlap: (a)/(b).

### 7.4 Failure-mode taxonomy (10 items)
- Concept: Adopt wholesale as Chronicle's release checklist — each of the ten becomes a written invariant with an owner and a test: (1) no repeated nullification of player action; (2) write-once presented facts; (3) distribution-steering not best-story-forcing; (4) engine-side memory, zero model-memory dependence; (5) generated content labeled honestly in tone, always opt-in-able; (6) revisited locations reflect state (settlement-state system is the fix); (7) every dispatched story carries completability failsafes; (8) every stated rule (MCM descriptions, docs) must match runtime behavior — audit at release; (9) no sim depth without a surfacing channel (the pivot's founding rule); (10) seed/vary repeated outcomes so reloads don't expose the machinery.
- Rating: H — the taxonomy is the QA spine for the whole mod.
- Feasibility: Process + tests.
- Overlap: doctrine.

---

## 5) Ranked Top 10 (build-first, across the entire catalog)

1. **RimWorld Storyteller pacing + storylet role-casting (5.3 + 1.12/7.2)** — the headline: a pacing director casting real grievance-holders into authored beat shapes is "RimWorld's storyteller for Skyrim" and everything else plugs into it.
2. **Settlement world-states with visible expression bundles (2.1)** — town-level visible change is the macro proof the world moves, and the payoff channel for war/dragon events.
3. **Traveling legal/rumor topology (2.3 delegated systems + non-telepathic crime)** — news and bounties that physically travel and reorganize with the civil war; the provenance engine made felt, and the "no psychic guards" bullet markets itself.
4. **Named survivors + combat-consequence verbs (4.1/4.2, patent-safe scope)** — the per-clip "world remembers me" generator.
5. **Break/aftermath system with intervention verbs (5.1 + 1.4 + 6.1 unified)** — dragon attacks and war produce human aftermath the player can help heal; loss AND recovery.
6. **Secrets + expose/blackmail + leverage economy (1.3)** — converts knowing-things into a player verb set; the provenance engine's native gameplay.
7. **Autonomous background social events delivered as news (4.5)** — cheapest "alive without me" per engineering dollar.
8. **Physical provenance objects: evidence, memorials, named artifacts (3.3 + 6.3)** — the sim made touchable; permanent world-marks within the no-geometry rule.
9. **Knowledge-as-inventory bargaining chips incl. planted lies (1.12 Twilight Bazaar)** — makes the player a first-class node in the rumor graph, weaponizing the mutation feature.
10. **Fear axis with provenance (1.10)** — a second visible social dimension, dramatic and cheap, inherently compliant with the no-global-reputation rule.

(Load-bearing non-features assumed underneath: Concordia/Slice-of-Life validation contract, hidden personality dials, the failure-mode checklist.)

## 6) Discard list (don't reconsider)

- **Diplomacy-skill opinion scaling (1.1)** — duplicates vanilla Speech; pure ledger.
- **Decay-curve shape choice (1.1)** — invisible tuning, decide once, never revisit as a feature.
- **Explicit hook spend-value table as player-facing (1.3)** — tuning data, not content.
- **Council obstruction/firing (1.7)** — no vanilla court scaffolding to hang it on.
- **CK background-RNG social schemes as dice (1.8 Sway/Befriend)** — RNG social progress contradicts Chronicle's everything-from-real-events identity; keep only the multi-step structure.
- **Faction HQ relocation (2.1)** — blocked by the no-geometry rule; credibility floor unreachable.
- **Kenshi shallow dialogue-boolean memory (2.4)** — anti-pattern, nothing to build.
- **SoD forensic ID fields (blood type, prints, shoe size) (3.1)** — wrong fiction for Skyrim; keep only name-resolution.
- **Nemesis cross-player vendettas (4.7)** — out of scope and the narrowest patent edge; permanently closed.
- **Nemesis automatic rank-rewriting hierarchy (4.4)** — already design-banned; succession-as-story covers the value.
- **PaSSAGE playstyle vectors as a filter (7.1)** — pacing-flattening risk exceeds value; keep only the contrast-beat lesson.
- **Full TSL formal synthesis (7.3)** — research-grade machinery; a hand-written FSM achieves the needed invariants.

## 7) What the catalog is missing

- **CK3 Legends (Legends of the Dead)** — narrative objects with protagonists, quality tiers, and *province-by-province geographic spread* via promotion spending: a shipped rumor-propagation-with-map-footprint system, the closest CK mechanic to Chronicle's core, absent from §1.
- **Nemesis intel system (worms, intel items)** — information-as-collectible revealing a target's traits/location before engagement; rhymes with the leverage economy and SoD facts graph; absent from §4.
- **RimWorld Ideology (ideoligions, precepts, rituals, conversion, per-pawn certainty)** — the collective-belief layer above individual mood; directly relevant to hold/faith-level belief aggregation; absent from §5.
- **RimWorld art descriptions from Tales** — colony artworks citing real recorded events: the DF-engraving pattern shipped in RimWorld; the catalog mentions Tales only inside the GC item.
- **DF Villains update (v0.47)** — world-gen intrigue networks, agents, interrogation: DF's own secrets-and-schemes layer, parallel to CK §1.3; absent from §6.
- **DF loyalty cascade** — the famous emergent failure where punishing a citizen makes executioners traitors to their own civilization, cascading: a canonical cautionary tale for any faction-membership logic.
- **Prom Week / CiF (Ensemble, open-source)** — ~5k-rule social-physics engine with history-referencing social facts; the largest academic omission in §7.
- **Talk of the Town (Ryan)** — NPCs with subjective, fallible knowledge models degraded through observation and hearsay — the only known system implementing rumor *distortion with provenance*, i.e., Chronicle's exact core loop, academically; belongs in §7 above nearly everything else.
- **Versu (Short/Evans)** — social-practice-based agents evaluating actions against roles/norms; the Façade lineage's other branch.
- **Watch Dogs: Legion recruitment chains** — population-scale generated grievance→questline hooks (every pedestrian recruitable via a procedurally derived grievance); a shipped grievance-to-content pipeline.
- **Bethesda's own Radiant Story/Radiant AI** — the in-engine conditional role-casting quest system Chronicle sits on top of and will be compared against; its absence from a catalog feeding a Skyrim mod is the oddest gap.
- **The Sims** — already flagged by the catalog itself as pending separate research.
