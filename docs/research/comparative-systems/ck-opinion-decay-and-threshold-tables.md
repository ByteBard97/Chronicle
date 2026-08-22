> Filed 2026-08-22 in `docs/research/comparative-systems/` — external research
> (Compass), not code-verified. A second, independent pass over similar
> ground to `ck-mechanics-inventory.md`; this one's emphasis is the CK2
> vs. CK3 decay-model difference and concrete numeric threshold/value
> tables. Feeds the scenario-ladder / reactivity design work, not any
> accepted ADR.

# CK2/CK3 Social-State Mechanics Inventory: A Reference for NPC Belief-and-Behavior Simulation

## TL;DR
- **Both games run character behavior off a single scalar "opinion" per directed pair, decorated with typed, timed, stacking modifiers — but the two games differ in one respect crucial to your design: CK2 modifiers hold flat then vanish at expiry, while CK3 modifiers decay gradually over a timed duration.** For a provenance/mutation system, CK3's model (graceful decay, named reasons on relations, a persistent "memory" log) is the closer precedent.
- **Behavior is triggered two ways: deterministic gates (opinion/strength crossing a hard threshold flips a boolean — e.g., faction discontent begins accruing once faction military power exceeds 80% of the liege's; vassals with ≥80 opinion cannot join factions; opinion ≤ −40 unlocks Declare Rival) and probabilistic scoring (`ai_will_do`/`ai_chance`/MTTH weightings where opinion, traits, and situation multiply a base chance).**
- **CK3 layers four systems you can borrow wholesale for provenance-driven grudges: secrets (typed, discoverable, convertible to hooks), hooks (weak/strong/perpetual with explicit acceptance values), stress (0–400 with breakdowns at 100/200/300), and character memories (logged life events with fade rules that later fuel events). Named relations (friend/rival/lover/nemesis) crystallize from opinion+events and each carries an explicit opinion value (±60 / ±120) plus a stress-on-death value.**

---

## Key Findings

1. **Opinion is the master variable in both games.** Every directed character→character pair has an opinion score (practically −100 to +100). It gates AI behavior deterministically at thresholds and feeds probabilistic acceptance scores for interactions. The value is a sum of typed, itemized modifiers shown in a hover tooltip/ledger.

2. **The CK2→CK3 decay change is the single most design-relevant difference.** CK2 temporary modifiers stay at full magnitude for a fixed number of months then snap to zero; CK3 modifiers decay gradually over a timed duration (the CK3 wiki repeatedly calls timed modifiers "decaying"/"growing").

3. **Threshold→action mechanisms are a mix of deterministic gates and weighted RNG.** Faction ultimatums, rival-declaration eligibility, and dread intimidation are hard gates; plot/scheme firing and who-joins-a-murder-plot are probabilistic scoring with opinion as a dominant term.

4. **CK3's secrets/hooks/stress/memories quartet is a ready-made provenance-and-consequence toolkit.** Secrets have provenance (who discovered them), convert to hooks (typed obligations with explicit spend values), and memories log life events with fade rules — exactly the "who told them / how it accumulates" spine you describe.

5. **AI scoring is documented and moddable.** CK3 exposes twelve `ai_*` personality values (boldness, greed, honor, rationality, vengefulness, zeal, etc.) that are added/subtracted inside `ai_will_do`/`ai_chance` blocks via `ai_value_modifier`; CK2 uses `ai_will_do` and named multipliers per trait.

---

## Details

### (1) The Opinion System

**Data model.** In both games, opinion is a directed scalar (A's opinion of B need not equal B's opinion of A) that runs practically from −100 to +100. It is computed as the sum of individually-named modifiers, each of which is one of: a permanent structural source (traits, same/different faith, same dynasty, tyranny), or a timed temporary source (gifts, granted titles, imprisonment aftermath, event outcomes).

**CK2 stacking & decay.**
- Opinion bonuses stack additively regardless of source (traits, bloodlines, artifacts, great works all sum). (CK2 wiki Modifiers; forum corroboration.)
- Temporary modifiers in CK2 are flat-then-drop: a modifier is defined with a value and a duration in months (the CK2 fandom Opinion page tabulates each with "T — time in months that modifier is active"), holds its full value for that window, then disappears entirely. Community and forum posts confirm players experience the modifier "jumping" from full value to 0 at expiry; a long-standing player suggestion thread asked Paradox to make them decay gradually instead (which CK3 later did).
- A concrete decay-rate exception exists even in CK2/CK3 for specific mechanics: the CK3 offensive-war penalty is defined in defines as `OFFENSIVE_WAR_PENALTY_PER_MONTH = 0.5` and `OFFENSIVE_WAR_PENALTY_DECAY_PER_MONTH = 0.5` with `OFFENSIVE_WAR_PENALTY_GRACE_PERIOD = 6` months — i.e. after 6 months at war the attacker gains −0.5 opinion/month with all vassals, decaying at the same 0.5/month once at peace.

**CK3 stacking & decay.**
- CK3 opinion modifiers are organized into typed categories the tooltip surfaces: **General** (affects everyone), **Attraction**, **Same Dynasty** (with sub-categories Virtues & Sins and Faith Hostility), **Relations**, **Tyranny**, plus **Opinion of Predecessor** on succession. (CK3 wiki Character page.)
- Timed modifiers decay gradually over their duration rather than holding flat: the wiki calls a revoked court position a "decaying −30 Opinion," and Patch 1.19 notes explicitly reference fixing "decaying and growing opinions… when they only have a timed duration."
- **Concrete permanent/structural values (CK3 Character page):**
  - General opinion from personal **Diplomacy skill: −8 to +92** across the skill range.
  - Trait penalties (apply to everyone): **Murderer −15, Sadistic −10, Peasant Leader −10**; situational modifiers **Attacked An Ally −25, Broken Truce −50**; Tyranny scales **−1 to −1000**.
  - **Attraction:** Beautiful/Handsome/Comely = **+30/+20/+10**, Homely/Ugly/Hideous = **−10/−20/−30**; Brave **+10**.
  - **Same Dynasty:** base Same Dynasty **+5**; Bastard **−15**, Legitimized Bastard **−10**; Kinslayer variants **−5** each.
  - **Faith Hostility:** faiths are rated Righteous/Astray/Hostile/Evil giving **0 / −10 / −20 / −30** opinion; Pluralist doctrine halves this malus (−50%), Fundamentalist doubles it (+100%). Crucially, the malus depends on how the *other* character's faith views yours, not vice versa.
  - **Virtues & Sins (Faith page):** **+10 same-faith opinion (and +1 monthly piety) per virtue trait; −10 (and −1 piety) per sin trait.**
- **Concrete timed values (various CK3 wiki pages):**
  - **Granted title:** "All opinion modifiers from granting titles last 50 years and can stack" (Titles page). Usurping a title: **−50** with previous owner. Holding >2 duchies (King+): **−15** per excess duchy from all vassals.
  - **Send Gift:** boost **lasts 5 years**; value is formula-scaled by giver Diplomacy and target Greed (no fixed number); the Thoughtful perk gives **+100%** gift opinion.
  - **Released prisoner, no demands:** **+20 opinion for 10 years** (costs 10 dread). Ransom paid by liege: **+5 for 1 year**. Executing a prisoner: **−20** with victim. Escape-from-prison: **−30 with jailor for 10 years**. (Prisoner / Character decisions pages.)
  - **Powerful vassal not given a council seat: −40 opinion** (Subjects page) — one of the largest single penalties.
  - **Treasury reallocation:** **−100 to +30 for 5 years** depending on magnitude of change.
- **Opinion of Predecessor (succession inheritance):** heir temporarily inherits **25% of a positive** opinion but **50% of a negative** opinion vassals held toward the late liege (CK3 Character page) — a deliberate asymmetry so grudges outlive their targets more than goodwill does. This is itself a decaying modifier.
- **The tooltip/ledger:** hovering the opinion number lists every active modifier by its label and value, with an end-date for temporary ones (e.g., "Respect: −20"; a "Sent gift" line with an expiry date). This itemized, provenance-labeled presentation is the closest shipped precedent to your "who told them / why they feel this" ledger.

### (2) Threshold→Action Catalog

**Faction joining / revolt math (CK3).**
- *State read:* faction Military Power = ratio of (combined military strength of all faction members) ÷ (liege's strength without those members); plus each vassal's opinion of liege.
- *Threshold:* per the CK3 Subjects page, "Military Power is the ratio between the combined military strength of all faction members and the military strength of the liege. When the ratio is above 80% the Faction will gain discontent" (below 80% it falls; the Hard Rule perk raises the liege's effective threshold to 100%). Discontent rises faster the further above 80% the faction sits. "A faction will deliver its ultimatum shortly after discontent reaches 100%"; refusal → civil war. Ultimatum can also fire early on an unjust imprisonment.
- *Hard eligibility gate (deterministic):* a vassal **cannot create/join a faction** if landless, underage, ceremonial, the liege has a strong hook/alliance/truce on them, they're in the same bloc, **or they have ≥80 opinion** of the liege; also can't join if terrified (unless discontent is already rising). AI vassals additionally won't join against a friend/lover liege (player vassals can). Per the Subjects page, "If the ultimatum is accepted, the liege will lose -20 Dread and Legitimacy. If it is refused, it will start a civil war."

**Faction math (CK2) — richer AI weighting, directly instructive for your weights.**
- *Alert/fire thresholds:* player warned at **70% strength**; AI leaders issue ultimatums at a **minimum 75%**, with big likelihood boosts at **100% and 150%**; the Antiking faction can fire as low as **50%**.
- *Per-trait join multipliers (deterministic multipliers on a probabilistic decision):* Ambitious **4×**, Envious/Greedy/Impaler/Deceitful **2×**, Proud/Brave/Arbitrary **1.5×**; Content **0.01×**, Imbecile **0.01×**, Inbred **0.1×**, Craven **0.1×**, Slow **0.2×**, Kind/Charitable/Honest **0.5×**, Humble **0.75×**, Just **0.75×**.
- *Opinion-of-liege gating (deterministic 0× cutoffs plus scaling multipliers):* e.g. for Independence factions, opinion **>80 = 0×** (will leave if in), **>60 = 0×** (won't join), **>40 = 0.5×**, **<0 = 1.5×**, **<−50 = 2×**, **<−75 = 4×**. Crown Authority and Succession factions have parallel tables. Distance and religion/culture differences add further multipliers (e.g. different religious group 2×, >400 distance 2×).

**Council obstruction (CK3).** Powerful vassals (3 at county tier, 4 at duchy, 5 at kingdom/empire) deterministically demand a council seat; denial applies **−40 opinion**. A vassal holding a hook on their liege can use **Demand Council Position** (weak or strong hook both force it), and once installed cannot be removed for 25 years.

**Plot formation & recruitment — who joins a murder plot and why (CK2).**
- *State read:* a prospective backer weighs their opinion of the plotter relative to their opinion of the target ("people join plots usually based on how much they like you relative to how much they like/dislike the person you are plotting against"), plus the plotter's prestige, plus the backer's traits.
- *UI signal:* each candidate shows a green (will join), yellow/"bribe" (will join after a small opinion boost or a bribe), or red (won't join even bribed) icon.
- *Plot power & firing (probabilistic, MTTH-based):* intrigue plots gain power from plotters' intrigue; the assassination event has a base MTTH cut **~67% per 100% plot power** (breakpoints at 100/150/200%) and further **~40% per 10% plot power a given plotter contributes, up to 90%** — so a 200%-power plot with a 90%-contributing backer sees a ~3-month MTTH for that backer. More plotters (not just stronger ones) massively accelerate firing. Non-kill plots (e.g. Fabricate Claim) instead have explicit gates: **75% power + 3 backers → 60% chance**, or **100% power + 5 backers → 90% chance**.

**Scheme recruitment — who joins (CK3).** In CK3 the murder plot became the Murder *scheme* with *agents*. Agents are drawn mostly from the target's or your own court; acceptance is scored: most characters face a **−10 "nothing to gain" penalty unless they dislike the target**, and personality (hidden Boldness/Compassion/Honor/etc.) drives willingness. Practical exploit documented by players: marry an Envious/Deceitful or Zealous-of-a-foreign-faith courtier into the target's court so they "hate everyone" and join freely. Character **rivals of the target get extra protection** as murder targets, and being at war grants **−50 success to Murder, −500 to Abduction**.

**Rival / friend / lover interventions.**
- *Declare Rival (CK3):* eligibility gate at **opinion ≤ −40**; declaring on a greater ruler grants prestige + a "Challenged Goliath" modifier, on a lesser ruler costs a little prestige (anti-spam) + an "Agitator" modifier.
- *Murder motivation:* CK3 players report assassination attempts overwhelmingly originate from the character's declared **rival** — i.e., the rival relation is the dominant read for AI-initiated murder.
- Friends/lovers act as *protective* interventions: an AI vassal who is a friend or lover of the liege is deterministically blocked from joining factions; lovers can foil murder attempts (human-shield mechanic).

**Dread intimidation (CK3) — a second scalar that overrides opinion.**
- *State read:* the acting character's Dread (0–100; 150 cap for nomads) vs. the target's hidden Boldness.
- *Thresholds (deterministic):* per the CK3 Attributes page, "A character becomes intimidated by characters whose dread is 20 above their own boldness and terrified by characters whose dread is 45 above their own boldness. This includes negative boldness" (Craven = −200 Boldness, so terrified of everyone; Content = −50). Intimidated/Terrified give flat acceptance bonuses (e.g. Intimidated **+50** to accept Blackmail, Terrified **+100**) that bypass negative opinion, and a terrified vassal can't join factions unless discontent is already rising. Dread drifts toward Natural Dread (from traits) at **0.5/month**.

### (3) CK3's Additions

**Secrets.** Characters acquire a secret when they do something criminal/shunned. Provenance matters: secrets are discovered by random event or the spymaster's **Find Secrets** task, and the discoverer chooses **Expose** (applies the secret's penalty publicly) or **Blackmail**. Secret types (with severity governed by the discoverer's faith doctrines): Attempted-murder / Murdered, Raided Estate, Plotting a coup (always criminal), Cannibal, Deviant, Sodomite, Incestuous, Practices-in-secret, Non-Believer, Witch, Lover, Illegitimate-child (two variants), Embezzled treasury/resources, Cheated at examinations, Requested Incursion. Secrets are removed when they become invalid (e.g. Lover secret ends if a marriage legitimizes it; Attempted-to-murder ends if the target dies otherwise). Doctrine-based secrets can convert into open traits if both the character's and liege's faiths accept the trait. Two witches can't blackmail each other and instead unlock a **+20 opinion** reveal interaction.

**Hooks (typed obligations — your "who owes whom" spine).** One hook per character at a time; a stronger/longer hook replaces a weaker one. Three tiers:
- **Weak** — single use; for most interactions only adds acceptance, doesn't force. Duration mostly 10 years. Sources: Blackmail (over a *shunned* secret), Favor, Obligation (halves court-position salary), Crime Accomplice, House Head (permanent), Indebted/Manipulation/Threatened (10y, *fabricable*), Won Trial-by-Combat, plus DLC hooks.
- **Perpetual** — permanent, reusable with a **5-year cooldown**, only adds acceptance. E.g. Loyal Hostage, Filial Piety (from birth under that tenet).
- **Strong** — reusable with **5-year cooldown**; for most interactions **forces** acceptance, and passively blocks the target from joining factions, declaring war, imprisoning, or demanding conversion from the holder. Sources: Blackmail over a *criminal* secret (lasts until secret exposed), Fabrication (10y), Loyalty (permanent), Saved Life (permanent), Best Friend under Ritualized Friendship tradition, Blood Brother, etc.
- **Spending values (weak → strong):** Arrange Marriage **+100 → +200 acceptance**; Imprison **+30 → Forced**; Demand Conversion **+50 → Forced**; Invite to Scheme **+100 → Forced**; Offer Guardianship **+200 → Forced**; Force to Join Faction (strong only) **Forced**; Modify Vassal Contract **Forced/Forced** (no tyranny); Force Vote **Forced** (target votes your candidate 100 years). Abandon Hook (Forgiving trait) refunds **−20/−42 stress** and grants **+50 opinion** with the recipient. Hooks explicitly **cannot** be used for Call to War, Offer Peace, Hire Mercenaries, Offer Vassalage, Invite to Activity, etc.

**Stress (0–400).** Primary gain: taking actions that conflict with the character's **personality traits** (a Just character imprisoning without cause, a Compassionate character plotting murder). Stress imposes escalating Health/fertility penalties by level. Per the CK3 Attributes page: "Stress ranges from 0 to 400… A character breaching the threshold of 100, 200, or 300 stress for the first time will immediately suffer a Mental Break… If a character reaches 400 Stress, it will trigger a level 3 mental break event and they will lose 100 Stress. 400 is the maximum stress value." Breaks can be survived by bearing the pain, or resolved by adopting coping traits (Drunkard, etc.); level-3 breaks can injure/kill the character, make them murder a courtier (gaining Murderer), force abdication, or change a personality trait. Per the same page, "Mental break events can only trigger once every 5 years (8 years with the 'Mental Resilience' lifestyle perk from the 'Whole of Body' lifestyle)" if a stress level persists. Personality traits determine both stress susceptibility and (for AI) behavior including Dread resistance.

**Character memories (your provenance log, shipped).** Added in patch 1.7.0 (Friends & Foes). Per the patch notes (verbatim): "Characters now have Memories of things happening in their lives (children born, battles won, rivals killed, etc etc.). These memories are used in events and other content. For example, if you are murdered your assassin might cite a grievance that your killer had against you. These memories might fade with time, and are usually lost on death." When a named relation forms, a **reason is recorded and shown** ("Kaiser Heinrich and King Philippe shared an excellent feast in Aachen"; "Basileus Andreas swore to avenge the death of Aristarchos, slain in battle by Ulf Munk"). Memories are preserved longer or forever for player-controlled and high-tier rulers. Private memories (took a lover, committed murder) are hidden unless it's your own character or observer mode. Viewable in a dedicated Memory Viewer.

**Schemes' use of relationship state.** Schemes split into Personal (Sway/Befriend/Seduce/Romance — no agents/secrecy, scored off Diplomacy + target opinion + trait compatibility + rank difference) and Hostile (Murder/Abduct/etc. — use agents + secrecy). Relationship state feeds directly: agent willingness keys off disliking the target/liege; Befriend and Seduce success weight trait compatibility and existing opinion; rivals resist being murdered; friends/lovers gain protective foils. Potential/Success is capped at 95% (except contract schemes), the schemer's own skill contributing up to 30% Potential with the rest from agents.

### (4) Relationship Crystallization

**How they form.** In both games, repeated interactions/events plus opinion push a pair toward one of three axes — friendship, love, or conflict — each with escalating tiers. CK3 formalizes this as **Childhood → Adulthood → Lifelong** relations (each type has three levels); friendship and conflict are mutually exclusive with each other but either can co-exist with love. Adulthood relations are gained/lost via events; Lifelong relations (Best Friend, Soulmate, Nemesis) require an existing adulthood relation and are capped at one of each.

**Explicit opinion values (CK3 relations table, Friends & Foes):** Friend **+60**, Best Friend **+120**; Lover/Crush **+60**, Soulmate **+120**; Rival **−60**, Nemesis **−120**; childhood Bully–Victim **−20**. Notably, relations also carry a **stress-on-death** value — roughly **±10 stress for love relations and −35 stress when a rival/nemesis dies** — so losing (or outliving) a bonded character is itself a stress event. Blood Brother confers Friend-equivalent benefits **plus a mutual strong hook** and an alliance.

**What they unlock.**
- Friend/Best Friend: large opinion, protective faction-blocking (AI liege's friend can't be recruited into factions against them), inheritance of the relation to the heir on succession (Best Friend passes to heir unless prior opinion < −30), a strong hook under the Ritualized Friendship tradition when upgraded to Best Friend.
- Lover/Soulmate: attraction-gated (sexual orientation set ~age 10, immutable); enables romance content and murder-foiling.
- Rival/Nemesis: enables Declare Rival at ≤ −40 opinion, drives AI-initiated murder schemes, applies large negative opinion.
- Named-relation formation always records a **reason** (memory) surfaced in the Relationships tab.

**How they end.** Adulthood relations can be ended by events or manually (Declare Rival, or ending a friendship); rivalries/friendships can decay if the underlying opinion collapses; relations are usually lost on death (but Best Friend/Nemesis can transfer to a closely-related heir with a mutual +60 opinion nudge if opinions are too low to inherit directly). Lover secrets dissolve when marriage/concubinage legitimizes them.

### (5) AI Decision-Making

**CK3 (documented on the AI-modding wiki page + Dev Diary #104).** AI behavior is influenced through four layers: **defines** (`common/defines/ai`, e.g. `BETROTHAL_MIN_AGE`), **chance/triggers** (`ai_chance`, `ai_will_do`, `ai_potential`, `ai_score`), **AI personality values**, and **script** (story cycles/events/on_actions; the conqueror AI runs a ~2000-line scripted effect).

The twelve moddable personality parameters (visible in-debug by hovering the head icon): `ai_boldness`, `ai_compassion`, `ai_energy`, `ai_greed`, `ai_honor`, `ai_rationality`, `ai_sociability`, `ai_vengefulness`, `ai_zeal`, `ai_war_chance`, `ai_war_cooldown`, `ai_amenity_spending`, `ai_amenity_target_baseline`. Documented behavioral meanings: **Boldness** = resistance to others' Dread + willingness to act; **Compassion** = prisoner treatment; **Energy** = how often it considers a Decision; **Greed** = reluctance to spend gold; **Honor** = honoring alliances/relationships & willingness to become a scheme Agent; **Rationality** = how much stronger its army must be before declaring war; **Sociability** = frequency of Character Interactions; **Vengefulness** = drive to punish transgressions; **Zeal** = eagerness for holy war.

**The scoring idiom (from the AI-modding page's worked example):**
```
ai_chance = {
  base = 10
  modifier = { add = 100  has_trait = chaste }
  modifier = { factor = 0  has_trait = deviant }
  ai_value_modifier = { ai_zeal = 1 }
}
```
`modifier {add=…}` adjusts the base if a trigger is true; `modifier {factor=…}` multiplies (factor 0 = veto); `ai_value_modifier` adds/subtracts a personality value times a coefficient. AI picks the higher-scoring event option. This is the exact pattern to replicate for scoring NPC social actions: base weight + additive situational modifiers + multiplicative vetoes + personality-scaled terms.

**Dev Diary #104 economic/behavior archetypes:** the AI is bucketed into archetypes (e.g. Warlike for bold+greedy characters — Wrathful/Impatient/Ambitious/Vengeful — who bank gold into a war chest; Cautious characters keep a defensive gold buffer) that shape spending and war initiation.

**CK2 (Decision/Objective modding).** CK2 uses `ai_will_do` scoring and `ai_acceptance` for interactions; the "Do It!" button is greyed if score ≤ 0, and the computed value is stored to `local_ai_acceptance_score`. Faction/plot joining is scored via the named per-trait multipliers listed in §2 (Ambitious 4×, Content 0.01×, etc.), which is the most transparent shipped table of "trait → propensity" weights and a strong template for your grudge/obligation propensity model.

---

## Recommendations

**Adopt CK3's data model as your baseline, not CK2's.** Represent each NPC→subject belief as a scalar with a stack of typed, individually-labeled modifiers, each carrying (value, source/provenance tag, timestamp, duration, decay flag). Use CK3-style **gradual decay** for most temporary modifiers (linear toward zero over the duration) so grudges soften believably; reserve flat-then-vanish only where you want a hard cliff. Benchmark to change this: if playtesters report grudges feel like they "snap off," you've accidentally shipped CK2 semantics.

**Stage the build in this order:**
1. **Opinion + itemized ledger first.** Ship the directed scalar and the hover tooltip that lists every modifier with its provenance label and expiry. This is the spine everything else reads. Use CK3's asymmetric succession-inheritance rule (25% of positive, 50% of negative) as your template for how beliefs propagate/persist past their origin.
2. **Deterministic threshold gates second.** Implement a small set of hard gates keyed to the scalar (e.g. ≥80 = loyal/won't-defect; ≤−40 = eligible-to-declare-rival; a dread-analog with Intimidated/Terrified at +20/+45 over a boldness stat). These are cheap, legible, and give immediate emergent behavior.
3. **Probabilistic action scoring third.** Port the `ai_chance` idiom literally: `score = base + Σ additive_situational + Σ (personality_value × coef)`, with `factor=0` vetoes. Seed personality with a CK3-style vector (boldness, vengefulness, honor, sociability, greed, zeal). Use CK2's per-trait multiplier table (Ambitious 4×, Content 0.01×…) as your first-draft weights for "propensity to initiate a hostile social action."
4. **Provenance/consequence quartet last.** Layer secrets (typed, discovered-by-X, expose-or-blackmail), hooks (typed obligations with explicit forced/+acceptance spend values), a stress-analog (0–N with breakdowns at fixed thresholds that gate out-of-character actions), and a memory log (life events with fade rules, preserved for "important" NPCs) that feeds later event/dialogue selection — including citing a specific grievance when an NPC initiates a hostile act, exactly as CK3's assassin-grievance example does.

**Concrete numeric starting points to copy:** relation values ±60/±120 for friend/rival vs best-friend/nemesis; a stress spike (~−35) when a bonded rival/nemesis dies; council-snub-style penalty −40; broken-promise −50; faction/defection eligibility cutoff at 80; stress breakpoints every 100 up to a 400 cap with a 5-year break cooldown; dread-analog drift 0.5/month toward a trait-derived baseline; gift-analog boost lasting ~5 years and scaling with a diplomacy stat.

**Thresholds that should change your approach:** if NPC-initiated actions feel too frequent/random, raise base MTTH and lean harder on `factor=0` vetoes (CK3's approach) rather than tuning additive weights; if they feel too deterministic/predictable (the common CK3 complaint that "it's always your rival"), widen the candidate pool and add more personality-scaled noise (CK2's approach). Aim for the midpoint the two games bracket.

---

## Caveats

- **Version drift.** CK3 figures reflect wiki pages verified for v1.19 (2026); CK2's Factions/Plot pages are flagged "potentially outdated" (last verified ~v2.8). Paradox rebalances these numbers across patches — treat specific values as design references, not immutable constants.
- **Formula-scaled values aren't fixed.** Several important CK3 opinion sources (Send Gift, Sway) are computed from Diplomacy/Greed/scheme-power and have no single published number; only their durations (e.g. gift = 5 years) are hard facts.
- **Some widely-cited numbers are community, not official.** The −100/+100 opinion range, the −40 declare-rival threshold, and older "−5/−15 same-vs-different-culture" figures are community-reported or superseded (current CK3 uses the Cultural Acceptance system); the official wiki doesn't state them as single explicit values. A few "murder relative = −100/−40" figures circulating online are CK2 *mod* values, not base-game CK3.
- **Plot-power MTTH formula (CK2)** comes from a detailed forum reverse-engineering rather than official docs; the exact reduction percentages (67% per 100% power, 40% per 10% contribution) are community-derived and were patch-sensitive.
- **AI internals are partly hardcoded.** The CK3 AI-modding page states plainly that portions of AI (e.g. army behavior) are "hardcoded" and not moddable/observable; the `ai_*` values and `ai_chance` blocks are the documented-and-exposed surface, not the whole decision engine.

---

### Source List (primary/official prioritized)
- **CK3 Wiki:** Hooks; Character/Characters (opinion categories, values, predecessor inheritance, relations); Subjects (faction military-power 80%, discontent, −20 dread on accepted ultimatum, powerful-vassal −40); Attributes (stress 0–400 & breakpoints 100/200/300, dread Intimidated +20/Terrified +45, boldness); Faith (virtues/sins ±10); Titles (title-grant 50yr stacking, usurp −50); Prisoner; Character decisions; Court (decaying −30); Council; Culture; Resources; Modifiers; AI modding (`ai_*` params, `ai_chance` example); Patch 1.5 & 1.19; Friends and Foes (patch 1.7 memories, relation values).
- **CK2 Wiki:** Factions (strength thresholds, trait/opinion multipliers); Plot (plot power, backer icons, gate percentages); Modifiers; Decision modding (`ai_will_do`, `ai_acceptance`); Opinion (fandom, "T = months" tables).
- **Paradox Dev Diaries / forums:** DD #5 (Schemes/Secrets/Hooks), DD #19 (Factions & Civil Wars, 80% threshold), DD #31 (Stress), DD #104 (AI archetypes), DD #106 (memories/relations), plot-power MTTH reverse-engineering thread.
- **Modding artifacts:** DelnarErsike defines list (offensive-war penalty defines), jesec/OldEnt CK3 script logs, Sililex ck3-claude-skill AI notes.
- **Community references (flagged where used):** GameRant, GameWatcher, Fandom, Neoseeker, FandomSpot, SegmentNext — used for corroboration/clarification, not as primary sources for contested numbers.