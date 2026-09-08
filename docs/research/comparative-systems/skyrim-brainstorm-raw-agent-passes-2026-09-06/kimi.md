 I'll work through the full catalog systematically. Given the volume, I'll maintain tight formatting as requested.

---

## 1. Crusader Kings II / III

### 1.1 Relationship/opinion tracking

**Directed pairwise opinion**
- **Concept:** Chronicle tracks `OpinionOf(A, B)` as a signed integer per NPC pair, computed from a modifier stack. Player sees it via a custom UI widget (like SkyUI's relationship panel) or dialogue prefix ("I see you're on good terms with Jarl Balgruuf..."). Modifiers are named and itemized: "Saved from bandits +15", "Stole my sweetroll −5". Faction members inherit base opinion toward the player from their faction head.
- **Rating:** Medium — useful scaffolding, but on its own it's just another ledger. Becomes High only when it drives visible behavior (factions, dialogue gating).
- **Feasibility:** Straightforward. Python holds the modifier stack; SKSE plugin injects opinion-derived dialogue conditions and UI text. No new research needed.
- **Overlap:** (b) Natural extension — Chronicle already has beliefs about NPCs; this formalizes a numeric aggregation layer with named modifiers.

**Opinion modifier fields (scripting primitives)**
- **Concept:** Chronicle's modifier schema expands to include `decay`, `multiplier`, `crime_flag`, `non_aggression_pact`, `obedient`. Example: a "Blood Price" modifier decays over 30 in-game days; a "Thane" modifier is non-decaying and gates specific dialogue. Crime flags auto-generate bounty dialogue from guards.
- **Rating:** Medium — infrastructure. The `crime` and `obedient` fields are High because they directly change what NPCs will do for you.
- **Feasibility:** Schema change in Python; SKSE reads flags to gate dialogue/AI packages. Trivial.
- **Overlap:** (b) Extension of existing belief weighting.

**CK2 flat-then-drop decay vs. CK3 gradual decay**
- **Concept:** Chronicle uses CK3-style gradual linear decay for all temporary opinion modifiers. A "Favor" granted today is +20, tomorrow +19, etc., visible in the UI as a shrinking bar. This avoids the CK2 "cliff" where a modifier vanishing suddenly flips an NPC from ally to enemy.
- **Rating:** Low — implementation detail, not player-visible fun. Matters for feel but isn't a headline.
- **Feasibility:** Trivial math in Python.
- **Overlap:** (a) Already how any sane decay system works; just needs surfacing.

**Succession opinion inheritance**
- **Concept:** When a Jarl dies, their steward/heir inherits a fraction of the predecessor's opinion toward the player — but negative opinion inherits at 50% weight while positive inherits at 25%. So if you murdered the old Jarl's friend, the new Jarl still distrusts you. Visible when the new Jarl's opening dialogue references their predecessor's stance ("My father spoke... poorly of you").
- **Rating:** High — makes the world feel continuous across deaths, a major Skyrim weakness (NPCs die and are replaced by blanks).
- **Feasibility:** Requires hooking into Skyrim's actor death / replacement events via SKSE. Documented in SKSE source. No new research.
- **Overlap:** (c) New subsystem — succession state tracking.

**Typed opinion categories (CK3)**
- **Concept:** Opinion breaks into General, Attraction (gated by SexualOrientation trait + beauty gear), Same Faction, Relation (family), Tyranny, Predecessor Opinion — each itemized in tooltips. A guard might say "I don't care that you're Thane, that face is ugly" because Attraction is a separate track.
- **Rating:** Medium — adds texture but mostly UI depth. Attraction-gated dialogue is High for romance mods.
- **Feasibility:** UI-heavy but doable with SKSE/Scaleform or a custom MCM. No new techniques.
- **Overlap:** (b) Extension — existing beliefs can be tagged by category.

**Vassal Stance categories (CK3)**
- **Concept:** Skyrim holds are assigned "Stance" tags: Militaristic (favors war, penalizes peace), Mercantile (favors trade, penalizes high taxes), Religious (favors temple investment, penalizes Daedra worship). Jarl actions (raising taxes, building fortifications, hosting feasts) apply opinion modifiers only to NPCs subscribed to matching stances. A Militaristic housecarl loves when the Jarl arms the guards; a Mercantile merchant hates the tax hike to pay for it.
- **Rating:** High — makes holds feel politically distinct and reactive to Jarl policy, not just the player.
- **Feasibility:** Stance assignment is static data. Jarl "policy" events need to be inferred from game state (e.g., detecting when guard count increases via SKSE cell scan) or injected via Chronicle-driven radiant events. Moderate complexity.
- **Overlap:** (c) New — stance vectors don't exist yet.

**Diplomacy-skill-scaled opinion**
- **Concept:** Player Speech skill contributes a flat opinion bonus/penalty with all NPCs. Speech 100 → +20 opinion baseline; Speech 0 → −10. Visible as "Charismatic" or "Unimpressive" in first meetings.
- **Rating:** Low — passive scalar, not reactive. Skyrim already has Speech checks.
- **Feasibility:** Trivial.
- **Overlap:** (a) Essentially covered by existing disposition; just a formula tweak.

**Prestige/piety-derived opinion**
- **Concept:** Player "Renown" (derived from completed quests, thaneships, civil war rank) gives small opinion bonuses capped at +10. Negative renown (known thief, low bounties) penalizes 10× faster. Bards sing of high renown; guards comment on infamy.
- **Rating:** Medium — Renown as a visible global stat is good, but the opinion math is invisible.
- **Feasibility:** Renown is a computed aggregate in Python. SKSE injects dialogue conditions. Straightforward.
- **Overlap:** (b) Extension of existing reputation tracking.

**Tyranny as pooled vs. itemized**
- **Concept:** "Tyranny" tracks unjust acts by the player (unjust imprisonment via follower framework, execution of surrendered enemies, overriding a Jarl's decision in a Chronicle event). CK2-style: each act is a separate −20 modifier with 1-year expiry. Visible in a "Tyranny Ledger" UI. Guards and citizens reference specific acts ("You had Roggvir executed without a trial!").
- **Rating:** High — gives moral weight to player choices, makes "evil" playthroughs structurally different, not just aesthetic.
- **Feasibility:** Requires defining what counts as "unjust" in Skyrim terms. Most acts need Chronicle event hooks (not base game detection). Moderate.
- **Overlap:** (c) New — tyranny meter doesn't exist.

**Named gift/grant modifiers with fixed durations**
- **Concept:** Giving gold/items to NPCs creates named modifiers: "Gold Gift +X for Y days", "Artifact Gift +Z". Giving a hold's artifact (e.g., Balgruuf's Greatsword) gives massive bonus. Repeated gifts extend duration rather than stacking. Visible when NPCs reference the gift in greetings.
- **Rating:** Medium — bribery is already in Skyrim. The "extend duration" twist is subtle.
- **Feasibility:** Trivial. Hook into existing gift/trade events via SKSE.
- **Overlap:** (b) Extension of existing favor tracking.

**Explorable opinion UI**
- **Concept:** An MCM or in-game book UI lets the player inspect any A→B opinion in the world, and a map mode colors holds by average sentiment toward the player. "Why does Winterhold hate me?" → click, see the modifier stack.
- **Rating:** Medium — legibility tool, not gameplay. Essential for a complex mod but not a selling point.
- **Feasibility:** Custom UI via SKSE/Scaleform or Dear ImGui overlay. Well-trodden ground.
- **Overlap:** (b) Better surfacing of existing data.

### 1.2 Named relationships (relationship crystallization)

**Discrete relationship flags overriding the scalar**
- **Concept:** Beyond numeric opinion, NPC pairs can crystallize into Friend, Rival, Lover, Nemesis. These are boolean flags that unlock unique mechanics. Friend/Rival are mutually exclusive; Lover can coexist with either. Visible via unique dialogue lines, quest hooks (Rival challenges you to a duel), and schedule changes (Lover meets you at the Bannered Mare).
- **Rating:** High — discrete named relationships are far more legible and story-generating than opaque numbers.
- **Feasibility:** Straightforward. Python stores flags; SKSE gates dialogue and AI packages.
- **Overlap:** (b) Natural extension — existing grudge system becomes the "Rival" flag; add Friend/Lover.

**Explicit opinion values + secondary effects per relation**
- **Concept:** Friend gives +60 opinion and +20% follower damage; Rival gives −60 and may sabotage your crafting. Lover gives +60 and a "Lover's Comfort" rested bonus if you sleep near them. Nemesis −120, they send hired thugs and refuse all services. On death: stress event (mood debuff) if Friend/Lover dies; mood buff if Nemesis dies.
- **Rating:** High — mechanical consequences make relationships matter to gameplay, not just fiction.
- **Feasibility:** Follower damage buffs via SKSE perk injection. Crafting sabotage requires hooking crafting stations. "Stress" needs Chronicle's mood system (see 1.4). All doable.
- **Overlap:** (b) Extension — adds mechanical effects to relationship flags.

**Formation always records a reason (a "memory")**
- **Concept:** When a relationship flag forms, Chronicle logs a specific memory: "Nazeem became your Rival after you publicly insulted him at the Bannered Mare, 4th of Frostfall, 4E 201." Viewable in a "Relationships" MCM tab. NPCs reference this in dialogue.
- **Rating:** Medium — flavor/legibility. Critical for debugging but not a headline feature.
- **Feasibility:** Trivial — provenance is Chronicle's core competency.
- **Overlap:** (a) Already covered by existing belief provenance.

**Relations gate/protect AI behavior**
- **Concept:** A Jarl's Friend cannot be recruited into a conspiracy against them. A Lover may foil an assassination attempt on you (human-shield event). Rivals are the dominant source of NPC-initiated murder-scheme motivation. A Rival blacksmith overcharges you and gives poor tempering results.
- **Rating:** High — makes the social graph directly change what NPCs *do*, not just what they say.
- **Feasibility:** Gating recruitment/dialogue is easy. "Foil assassination" requires an event system. Blacksmith overcharge needs crafting hook. Moderate.
- **Overlap:** (b) Extension — uses existing relationship flags to gate behavior.

**Inheritance of named relations on death**
- **Concept:** If your Best Friend dies, their sibling or child may inherit the relationship (with a +60 opinion nudge). "Your father was my dearest friend; I will stand by you." Or a Nemesis's heir swears vengeance.
- **Rating:** High — solves the "replacement blank NPC" problem and creates generational stories.
- **Feasibility:** Requires detecting heir relationships via SKSE (GetActorBase, GetParent, etc.). Well-documented.
- **Overlap:** (c) New — inheritance logic.

**House-level relationship crystallization (CK3)**
- **Concept:** Skyrim's major families (Battle-Born vs. Gray-Mane, Black-Briar, Silver-Blood) accumulate House relations: Feuding, Neutral, Faithful. Member actions (gift to house head +20%, best friends +20%, murder discovered −20%) shift the house meter. Feuding houses get −30 cross-opinion, −25 marriage acceptance (if using marriage mod), +15 hostile scheme success. After 50 years of no relevant actions, drift toward Neutral.
- **Rating:** High — makes Skyrim's existing family tensions (Battle-Born/Gray-Mane) mechanically real and player-influenceable.
- **Feasibility:** House definitions are static data. Cross-opinion is a Python aggregation. Marriage gating requires a marriage framework hook. Moderate.
- **Overlap:** (c) New — house-level system doesn't exist.

### 1.3 Secrets, hooks, leverage

**Secrets (typed, discoverable, provenance-tracked)**
- **Concept:** NPCs acquire Secrets when doing illicit acts: Thieves Guild membership, Dark Brotherhood contract, Talos worship (in Stormcloak-held holds), adultery, embezzlement from the treasury. Secrets are discovered via random events or a Spymaster NPC's "Find Secrets" task (skill contest vs target's Sneak/Speech). Provenance tracked: "Uthgerd is a secret Talos worshipper [learned from Heimskr, who witnessed her praying]."
- **Rating:** High — secrets create asymmetric knowledge, blackmail opportunities, and faction intrigue.
- **Feasibility:** Secret types are static. Discovery is a periodic Python roll. Spymaster NPC could be a custom follower or a vanilla one repurposed (e.g., Maven Black-Briar). Straightforward.
- **Overlap:** (b) Extension — beliefs already have provenance; "secret" is a privacy tag.

**Expose vs. Blackmail choice**
- **Concept:** Upon discovering a secret, player chooses: Expose (applies permanent public trait, e.g., "Known Thieves Guild Member", unlocking guard harassment, exile dialogue) or Blackmail (creates a Hook). Refusing blackmail auto-exposes.
- **Rating:** High — creates genuine player choice with faction-level consequences.
- **Feasibility:** Trait application via SKSE AddSpell/AddPerk or custom keyword. Dialogue gating via SKSE conditions. Straightforward.
- **Overlap:** (b) Extension — adds a decision fork to secret discovery.

**Hooks as spendable leverage currency**
- **Concept:** A Hook on an NPC is a spendable resource. Weak Hook: single-use, +50 acceptance on one request, 10-day expiry. Strong Hook: reusable (30-day cooldown), can force acceptance on interactions (e.g., force a guard to look the other way). Strong Hooks also block the target from joining factions against you or imprisoning you. Perpetual Hook: permanent, acceptance-only.
- **Rating:** High — turns social knowledge into actionable currency, not just lore.
- **Feasibility:** Hook inventory is Python state. "Force acceptance" means overriding Skyrim's dialogue/AI responses via SKSE — doable but requires careful injection. Blocking imprisonment means hooking into crime/bounty system (documented in SKSE crime hooks). Moderate.
- **Overlap:** (c) New — leverage currency doesn't exist.

**Explicit spend-value table**
- **Concept:** Concrete values: Force Guard to Ignore Crime = 1 Strong Hook. Force Jarl to Grant Title = 2 Strong Hooks. Force NPC to Join Faction = 1 Strong Hook. Some interactions cannot be forced (e.g., forcing marriage is disallowed for design reasons). Values visible in a "Social Ledger" UI.
- **Rating:** Medium — legibility feature. Good for players but not exciting on its own.
- **Feasibility:** Trivial data table.
- **Overlap:** (b) Extension of Hook system.

**Forgiving-trait hook abandonment**
- **Concept:** A player with "Forgiving" trait (or high Mercy personality) can voluntarily release a Hook. This relieves player "Stress" (mood buff) and gives the target a decaying +20 opinion bonus. Leverage as emotional transaction, not extraction.
- **Rating:** Medium — nice roleplay beat, but niche.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension — adds a spend option to Hooks.

### 1.4 Stress / internal-friction engine

**A psychological buffer gating out-of-character action**
- **Concept:** Chronicle adds a Stress meter (0–400) per NPC. NPCs gain stress when acting against traits: an Honest NPC lying in dialogue; a Cowardly NPC being ordered to charge. Player gains stress when acting against their chosen/backstory traits. Stress gates certain dialogue options (high stress → can't lie smoothly, can't intimidate effectively).
- **Rating:** High — adds a "roleplay cost" to min-maxing, making character build matter socially.
- **Feasibility:** Stress is a Python float. Trait definitions are static. Gating dialogue via SKSE conditions. Straightforward.
- **Overlap:** (c) New — stress system doesn't exist.

**Threshold breakdown events**
- **Concept:** Crossing 100/200/300 stress triggers a Mental Break event. At 100: "Stressed" — NPC may binge drink at tavern, wander, or insult someone. At 200: "On Edge" — may start a fistfight, destroy furniture, or go catatonic for a day. At 300: "Breakdown" — may attack friend/foe, flee the hold, or change a personality trait permanently. At 400: resets to 300 with a severe break. 5-year cooldown between breaks.
- **Rating:** High — visible, dramatic world events that make NPCs feel alive and unstable.
- **Feasibility:** Break events are Chronicle-driven radiant events injected via SKSE (move NPC to tavern, trigger faction fight, etc.). Trait change requires SKSE SetActorValue or custom keyword swap. Moderate complexity.
- **Overlap:** (c) New — breakdown events.

**Coping mechanisms**
- **Concept:** After a break, NPC may adopt a coping trait: Drunkard (frequents taverns, −2 Speech, +stress relief when drinking), Flagellant (visits temple, −1 Health, +stress relief), Comfort Eater (visits market, −1 Speed, +stress relief). Permanent but with trade-offs.
- **Rating:** Medium — adds texture but coping traits are mostly background simulation.
- **Feasibility:** Trait application via SKSE. Schedule changes via AI package override. Straightforward.
- **Overlap:** (b) Extension of stress system.

**A documented, itemized trait→stress-source table**
- **Concept:** A visible in-game "Personality Guide" or MCM table showing exactly what stresses each trait. Honest: stressed by lying, theft, bribery. Brave: stressed by fleeing, surrendering. Greedy: stressed by donating, paying full price. Lets players optimize for their build or deliberately test limits.
- **Rating:** Low — reference material, not gameplay.
- **Feasibility:** Trivial documentation.
- **Overlap:** (a) Already implied by any trait system.

### 1.5 Memories (persistent life-event log)

**Structured, tagged, participant-linked memory objects**
- **Concept:** Every NPC has a memory log: timestamp, type tag (`battle_won`, `relative_murdered`, `feast_attended`, `dragon_attack_survived`), participant refs, visibility (Public/Private). "Battle of Whiterun — fought for Stormcloaks — witnessed Ulfric's speech." Memories are queryable by other systems.
- **Rating:** High — the substrate for all emergent narrative. Invisible alone but enables everything else.
- **Feasibility:** Core to Chronicle's existing design. Trivial.
- **Overlap:** (a) Already covered.

**Retention-by-rank**
- **Concept:** Important NPCs (Jarls, faction leaders, player) retain memories permanently. Random citizens' memories fade after 1 in-game year unless promoted by strong emotion. Private memories (secret murder) never spread unless the NPC chooses to tell.
- **Rating:** Medium — simulation hygiene. Prevents bloat but not player-visible.
- **Feasibility:** Trivial Python GC logic.
- **Overlap:** (a) Already covered by belief decay.

**Memories are queried by other systems**
- **Concept:** A guard's dialogue generator pulls the exact memory ID of a real grievance: "I haven't forgotten how you let that dragon burn the Western Watchtower" — referencing the specific `dragon_attack_survived` memory where the guard's brother died because the player was late.
- **Rating:** High — makes dialogue feel deeply contextual and specific rather than generic.
- **Feasibility:** Requires a dialogue injection system. SKSE can add topics dynamically; Papyrus can set global variables for dialogue conditions. Moderate — Skyrim dialogue is static-baked, so dynamic injection is limited without custom voice acting. Text-only (subtitles) is feasible; voiced requires xVASynth or silence.
- **Overlap:** (a) Already covered — just needs better surfacing.

**Viewable in a dedicated Memory Viewer**
- **Concept:** An MCM or in-game journal UI showing your own memory log and (with high Speech) the memory log of NPCs you've interviewed.
- **Rating:** Medium — legibility tool.
- **Feasibility:** UI work. Straightforward.
- **Overlap:** (a) Better surfacing.

### 1.6 Faction / collective political pressure

**Faction power as a ratio, gating discontent accrual**
- **Concept:** A "Discontent" faction in a hold (e.g., Stormcloak sympathizers in Solitude) accrues monthly discontent only if their combined follower count / gold / weapon stock exceeds 80% of the Jarl's resources. At 100% discontent, they issue an ultimatum (quest trigger: suppress or negotiate). Unjust imprisonment of a faction member immediately triggers ultimatum.
- **Rating:** High — makes civil war feel like an actual brewing conflict with measurable pressure, not just a questline.
- **Feasibility:** Faction resources computed from Chronicle's inventory tracking (via SKSE container scanning) or abstracted. Ultimatum as radiant quest. Moderate.
- **Overlap:** (c) New — collective pressure system.

**Hard eligibility gates independent of probabilistic layer**
- **Concept:** NPCs cannot join a rebellion faction while imprisoned, underage, bound by a hook/alliance, terrified, or if their opinion of the Jarl is ≥80. AI won't join against a Friend/Lover Jarl. Player can override with a Strong Hook.
- **Rating:** Medium — mostly invisible rules that prevent absurd outcomes.
- **Feasibility:** Trivial eligibility checks.
- **Overlap:** (b) Extension of existing faction/opinion systems.

**Per-trait join/leave multipliers**
- **Concept:** Published propensity table: Brave 2× join rebellion, Cowardly 0.1×, Greedy 2× (if promised loot), Honest 0.5× (dislikes conspiracy). Visible in an "Intelligence Report" on hold stability.
- **Rating:** Low — simulation detail, not player-visible.
- **Feasibility:** Trivial math.
- **Overlap:** (b) Extension.

**A Strong Hook or resource threshold can force faction membership**
- **Concept:** Spend a Strong Hook to force an NPC to join a faction for 10 years. Or pay a mercenary threshold (5000 gold) to buy their membership.
- **Rating:** Medium — actionable but niche.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension of Hook system.

**Powerful-vassal council-seat mechanics**
- **Concept:** Skyrim's "powerful vassals" = housecarls and stewards. They demand a "council seat" (a daily audience with the Jarl). Denial applies −40 opinion. A Strong Hook forces the seat, after which they can't be removed for 25 years. In Skyrim terms: forcing a Jarl to keep a disliked steward.
- **Rating:** Medium — CK council doesn't map cleanly to Skyrim's flat structure. Would need significant adaptation.
- **Feasibility:** Requires custom "council" abstraction not present in vanilla. Moderate.
- **Overlap:** (c) New — council abstraction.

### 1.7 Council mechanics

**Five discrete voting-stance archetypes**
- **Concept:** In a Chronicle-driven "Hold Council" event (radiant), NPCs vote on policy: Loyalist (supports Jarl), Pragmatist (stability-focused), Glory Hound (favors war), Zealot (favors temple), Malcontent (obstructs). Each stance computed from traits + opinion + realm power. Player can lobby voters before the council.
- **Rating:** High — if surfaced as actual quests/events where the player campaigns for votes. Invisible otherwise.
- **Feasibility:** Requires building a council event system from scratch. Significant Papyrus/SKSE work. High effort.
- **Overlap:** (c) New.

**Concrete vote thresholds**
- **Concept:** Visible thresholds: a voter supports imprisoning a target only if their opinion of the target is <−30. Supports title grant if opinion >+50. Published in a "Political Guide" book item.
- **Rating:** Medium — legibility.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension.

**Council obstruction can trigger firing penalties**
- **Concept:** Removing a councilor applies "Recently Fired" opinion modifier. Doing it repeatedly stacks.
- **Rating:** Low — too granular for Skyrim's structure.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension.

### 1.8 Schemes / plots

**CK2 plot power is a levy-contribution ratio**
- **Concept:** Conspiracy power in a hold = sum of (conspirator's follower count × role multiplier). Housecarls contribute 2×, foreign agents 0.33×, court members 2× against rulers. At 50%/100%/150%/200% power, event-opportunity pacing increases (more chances to strike).
- **Rating:** Medium — good for internal simulation but mostly invisible unless surfaced in a "Conspiracy Dashboard."
- **Feasibility:** Math in Python. UI surfacing needed.
- **Overlap:** (b) Extension of faction pressure system.

**CK3 schemes split into Personal and Hostile**
- **Concept:** Personal schemes: Befriend, Sway, Romance — scored off Speech + opinion + trait compatibility. Hostile: Murder, Abduct, Frame — use Potential (max success, capped), Secrecy (monthly detection roll, 5 Breaches = collapse), Advantage (resource spent to execute), Agent Acceptance (opinion delta + traits + Hook coercion).
- **Rating:** High — makes social manipulation feel like a minigame with risk/reward.
- **Feasibility:** Requires a scheme execution system with periodic rolls, agent recruitment UI, and event injection. Significant build. Agent acceptance can reuse existing opinion system.
- **Overlap:** (c) New — scheme subsystem.

**Agent recruitment is opinion/trait-scored**
- **Concept:** Recruiting an agent against a target: most NPCs have a "nothing to gain" penalty unless they dislike the target. Marrying an Envious/Deceitful NPC into the target's court yields free agents. Rivals of the target get extra protection as murder targets.
- **Rating:** High — creates emergent recruitment puzzles and marriage-of-convenience stories.
- **Feasibility:** Requires NPC marriage/location tracking. SKSE can detect spouse and location. Straightforward.
- **Overlap:** (b) Extension of existing opinion + relationship system.

**Discovery consequences are explicit and stacking**
- **Concept:** Discovered murder attempt applies −40 opinion with target's family, −20 with their faction. Surviving relatives become Rivals and may launch their own murder schemes. A discovered scheme creates a permanent "Attempted Murderer" public memory.
- **Rating:** High — consequences cascade, creating feud stories.
- **Feasibility:** Trivial — memory + opinion modifiers.
- **Overlap:** (b) Extension.

**Scheme-specific success/outcome tables**
- **Concept:** Befriend success → Friend flag + removes target from factions against you. Befriend failure → opinion cascade across whole court (−10 with everyone who liked the target). Sway → +25 opinion. Seduce → +20 opinion + possible Lover secret.
- **Rating:** Medium — outcome tables are necessary but not exciting in themselves.
- **Feasibility:** Trivial data.
- **Overlap:** (b) Extension of scheme system.

### 1.9 AI decision-making

**A documented `ai_chance`/`ai_will_do` scoring idiom**
- **Concept:** Chronicle's NPC decision-making uses base weight + additive modifiers + multiplicative vetoes + personality-scaled terms. Visible in debug MCM: "Why did NPC X do Y? Base 10 + Brave +5 + Opinion −3 × Coward Veto 0 = 12."
- **Rating:** Low — internal implementation detail.
- **Feasibility:** Trivial Python.
- **Overlap:** (a) Already how any decision system works.

**Twelve-to-thirteen exposed hidden personality parameters**
- **Concept:** Hidden AI parameters: `ai_boldness`, `ai_compassion`, `ai_greed`, `ai_honor`, `ai_rationality`, `ai_sociability`, `ai_vengefulness`, `ai_zeal`, etc. Each with documented meaning. Honor governs alliance-keeping; Vengefulness drives punishment. These are invisible to the player but produce behavioral variance that feels "explainable in retrospect."
- **Rating:** Medium — invisible layer that produces visible variance. Essential for simulation but not a selling point.
- **Feasibility:** Trivial static data.
- **Overlap:** (b) Extension — existing traits can be decomposed into these parameters.

**A two-layer visible/hidden state split**
- **Concept:** Player sees traits/opinion; hidden personality values produce surprises that are retroactively explainable. "I didn't expect Uthgerd to betray me, but her hidden Vengefulness is 90."
- **Rating:** Medium — design philosophy, not a mechanic.
- **Feasibility:** Already implied by hidden params.
- **Overlap:** (a) Already covered.

**AI archetype bucketing**
- **Concept:** NPCs bucketed into archetypes: "Warlike" (bold+greedy, banks gold for war), "Schemer" (high intrigue, low honor), "Diplomat" (high sociability, high honor). Archetypes shape spending/war-initiation patterns and can be inferred by the player over time.
- **Rating:** Medium — useful for predictability but requires long observation.
- **Feasibility:** Trivial classification.
- **Overlap:** (b) Extension.

### 1.10 Dread / intimidation

**Dread vs. Boldness threshold gates**
- **Concept:** Player/NPC Dread stat (from cruel acts, executions, wearing daedric armor) vs target's Boldness. Dread > Boldness+20 = Intimidated (+30 acceptance). Dread > Boldness+45 = Terrified (can't join factions against you, flees combat). Dread decays monthly toward a baseline. A Cowardly NPC (low Boldness) is terrified of almost everyone.
- **Rating:** High — makes "fear" a distinct social axis from "opinion," enabling tyrant playthroughs.
- **Feasibility:** Dread is a Python scalar. Boldness from traits. Acceptance gating via SKSE. Straightforward.
- **Overlap:** (c) New — dread system.

### 1.11 Event-engine architecture

**MTTH vs. `on_action` event-driven hooks**
- **Concept:** Chronicle uses `on_action` hooks (state-change triggers) for major events (death, quest completion, crime witnessed) rather than MTTH polling. State changes fire events immediately; MTTH is reserved for ambient rumors.
- **Rating:** Low — architecture decision, not player-visible.
- **Feasibility:** Trivial design choice.
- **Overlap:** (a) Already how event systems work.

**"Opinion-modifier soup"**
- **Concept:** Deliberate guardrail: Chronicle caps modifier stacking at 10 per relationship, and uses stance vectors + memory flags rather than ever-more numeric precision. Prevents unreadable tooltips.
- **Rating:** Low — anti-failure-mode.
- **Feasibility:** Trivial.
- **Overlap:** (a) Best practice.

**Sculptural Fiction vs. Generative Social Simulation**
- **Concept:** Chronicle uses continuous state simulation underneath, but surfaces it through authored storylet layers at key thresholds. Example: the underlying numeric "discontent" is invisible; when it crosses 80%, an authored "Tension in the Hold" storylet fires with specific dialogue and quest hooks.
- **Rating:** Medium — design philosophy. The storylet layer is High if implemented well.
- **Feasibility:** Requires a storylet authoring system. Significant.
- **Overlap:** (c) New — storylet layer.

**Emergence-detection / pattern-recognition thesis**
- **Concept:** Events leave persistent records so later decisions can cite them. A blacksmith's son dies in a dragon attack → later the blacksmith joins the Stormcloaks → player infers grief-driven choice. The system doesn't force this narrative; it just preserves the chain.
- **Rating:** High — this is the core fantasy of Chronicle.
- **Feasibility:** Requires memory linking + queryable causality. Already in scope.
- **Overlap:** (a) Core design.

### 1.12 CK's genre neighbors

**King of Dragon Pass / Six Ages**
- **Concept:** Clan-level social state (ancestral favor, advisor traits). Action execution is storylet selection during seasonal phases. In Skyrim: "Hold Council" meets every season (30 days), presenting 3 storylet options based on hold state. Advisors (steward, housecarl, court wizard) offer contextual predictions. "No obviously best answer" design — every choice is a value trade-off.
- **Rating:** High — structured, legible, and fits Skyrim's seasonal calendar.
- **Feasibility:** Requires storylet authoring + seasonal trigger. Moderate.
- **Overlap:** (c) New — seasonal storylet system.

**Wildermyth**
- **Concept:** Character-pair relationship bindings (Rivals/Lovers/Friends) + emergent physical-transformation tags. Dynamic casting: storylets search active NPCs for matching history/traits/relationships. Visual comic-panel interface surfacing motivation. Explicitly discarded deeper overland simulation because "unreadable depth is wasted."
- **Rating:** High — dynamic casting of real NPCs into story roles is exactly what makes generated content feel authored.
- **Feasibility:** Storylet precondition engine in Python. Comic panels require UI art (or text equivalent). High effort.
- **Overlap:** (b) Extension — uses existing relationship flags.

**Total War (Three Kingdoms/Attila)**
- **Concept:** Scalar Loyalty/Satisfaction with named trait-affinity sources. Hard-threshold defection with region. Failure mode: invisible inter-vassal relations caused mass defection. Lesson for Chronicle: make all decisive variables visible.
- **Rating:** Low — lesson learned, not a mechanic to port.
- **Feasibility:** N/A
- **Overlap:** (a) Design lesson.

**Mount & Blade II: Bannerlord**
- **Concept:** Single −100..+100 relationship per lord with per-action deltas. Almost no NPC-initiated action reads the score. Cited as "control group" proving a legible number alone, without threshold→action catalog, produces no social fantasy.
- **Rating:** Low — negative lesson. Chronicle must avoid this.
- **Feasibility:** N/A
- **Overlap:** (a) Design lesson.

**The "Twilight Bazaar" thesis**
- **Concept:** (1) OCEAN/Big-Five personality failed; replaced by smaller discrete trait pool. (2) "Bargaining chips" — social knowledge as discrete, presentable, lie-capable inventory objects. Players forgot invisible knowledge. (3) The interaction verb frames interpretation: "Gossip" prompts backstory construction; "Socialise" produces nothing.
- **Rating:** High — critical lessons for Chronicle's design. "Bargaining chips" as tangible inventory items (notes, letters, blackmail material) is a concrete implementation.
- **Feasibility:** Discrete knowledge items = SKSE inventory injection or custom MiscObject forms. Straightforward.
- **Overlap:** (b) Extension — makes provenance tangible.

---

## 2. Kenshi

### 2.1 World states / town overrides

**Boolean world-state flags driving town overrides and homeless spawns**
- **Concept:** Chronicle tracks boolean world-state flags: "Jarl Balgruuf dead", "Whiterun sacked by Stormcloaks", "Dragonsreach destroyed". These drive two outputs: town override (merchant tables, guard spawns, building states) and wilderness spawn shifts (bandit camps grow in weakened holds). Nothing more granular.
- **Rating:** High — makes the world visibly change after major events.
- **Feasibility:** Town overrides in Skyrim are hard without altering base assets. Can simulate via SKSE-spawned references, faction ownership changes, and merchant inventory injection. "Homeless spawns" = wilderness encounter table shifts. Moderate — Skyrim's cell system is resistant to dynamic overhaul.
- **Overlap:** (c) New — world-state layer.

**Single-leader vs. multi-leader collapse patterns**
- **Concept:** Small factions (e.g., a bandit camp) collapse when leader killed. Large factions (Stormcloaks) require multiple leader kills + supply-chain disruption. Killing a mine boss degrades the capital's economy. Killing a defensive town's boss lets neighbors fall to invaders.
- **Rating:** High — creates strategic depth in faction warfare.
- **Feasibility:** Faction "supply chain" is abstracted (Python variables). Capital degradation = merchant gold reduction, fewer guard spawns. Invasion logic requires SKSE to trigger faction battles. High effort.
- **Overlap:** (c) New.

**Kill/imprison equivalence, and release-rollback**
- **Concept:** Imprisoning a world-state-linked leader satisfies "dead" conditions. Releasing them rolls back the flag. Supports rescue-mission narratives. Some overrides require capture-then-release sequence to persist.
- **Rating:** Medium — good for quest design but niche.
- **Feasibility:** Trivial state logic.
- **Overlap:** (b) Extension of world-state system.

**A small fixed override vocabulary**
- **Concept:** Overrides: Malnourished, Half-destroyed, Civil War, Destroyed, Prosperous. Each swaps the town record: faction, resident roster, bar squads, building states, vendor tables. "Prosperous" is relative. In Skyrim: a "Prosperous" Whiterun has more merchants, richer inventories, more citizens in streets.
- **Rating:** High — visible world state changes are the most direct "alive world" signal.
- **Feasibility:** Hard without base asset edits. Can approximate via SKSE-spawned NPCs, container inventory edits, and faction ownership. Very high effort.
- **Overlap:** (c) New.

**Priority-ranked override chains**
- **Concept:** When multiple overrides satisfy, the one gated by most world states wins. Whiterun might chain through 5 ranked owners depending on global alive/free vector.
- **Rating:** Medium — implementation detail.
- **Feasibility:** Trivial Python logic.
- **Overlap:** (b) Extension.

**The swap only executes while town is unloaded**
- **Concept:** Town changes only when player is not present. If player is in Whiterun during a siege, the game silently queues the override until they leave.
- **Rating:** Low — technical constraint, not a feature.
- **Feasibility:** Standard Skyrim cell reset behavior.
- **Overlap:** (a) Standard engine behavior.

**Player-owned buildings are collateral damage**
- **Concept:** Documented pain point: if Whiterun is overridden to "Destroyed", player homes in Whiterun may be affected. Chronicle must explicitly protect player-owned references.
- **Rating:** Low — anti-failure mode.
- **Feasibility:** Trivial blacklist.
- **Overlap:** (a) Best practice.

**Faction headquarters can relocate**
- **Concept:** If a faction loses their HQ, they relocate to a newly-acquired town. Stormcloak HQ moves from Windhelm to Riften if Windhelm falls.
- **Rating:** Medium — cool but requires significant questline rewriting.
- **Feasibility:** Hard — Skyrim quest stages reference specific locations. Would need quest patching. High effort.
- **Overlap:** (c) New.

**"Broken squad" degradation instead of faction deletion**
- **Concept:** Beaten factions persist as weaker remnants. A defeated Stormcloak faction spawns "Remnant Rebel" bandits in the wilderness instead of vanishing.
- **Rating:** High — makes the world feel like it has history, not binary win/loss.
- **Feasibility:** Remnant spawns via SKSE leveled list injection or direct actor spawning. Moderate.
- **Overlap:** (c) New.

**Power vacuums grow a rival faction's footprint**
- **Concept:** Killing one faction's regional leader causes a neighboring faction's wilderness spawns to colonize the vacated zones. Killing the Silver-Blood mine boss lets the Forsworn expand into that reach.
- **Rating:** High — dynamic faction borders without explicit war.
- **Feasibility:** Abstracted as spawn-table shifts. Moderate.
- **Overlap:** (c) New.

**Zone-level spawn-table retuning**
- **Concept:** Leader death/capture shifts which squads spawn in which wilderness zones, globally keyed on alive/free vector.
- **Rating:** Medium — invisible unless player notices new encounter types.
- **Feasibility:** SKSE can modify leveled lists at runtime or spawn specific encounters. Documented.
- **Overlap:** (b) Extension of world-state system.

**The system is the most-modded layer**
- **Concept:** Lesson: "more world-state branches" is not automatically better. Each branch must be discoverable and completable. Chronicle should start with 3–4 clear world states per hold, not 20 micro-states.
- **Rating:** Low — design lesson.
- **Feasibility:** N/A
- **Overlap:** (a) Design lesson.

### 2.2 Faction relations scalar

**A −100..+100 per-faction scalar with two named thresholds**
- **Concept:** Faction relations: <−30 = hostile (attack on sight). >+50 = allied (gift food, assist combat, ignore bounties except witnessed crimes). Between = neutral. In Skyrim: Thieves Guild vs. guards, Stormcloaks vs. Imperials.
- **Rating:** Medium — Skyrim already has faction hostility. The "allied" bundle is new.
- **Feasibility:** Skyrim's faction system already handles hostility. Allied bundle requires SKSE to override combat assistance and bounty behavior. Moderate.
- **Overlap:** (b) Extension of existing faction system.

**Witnessed crime overrides the scalar entirely**
- **Concept:** Anyone who personally witnesses a crime against their faction attacks even at alliance level. The scalar gates default disposition only.
- **Rating:** Medium — realistic but mostly prevents "exploits" rather than adding fun.
- **Feasibility:** Crime witness detection via SKSE crime events. Straightforward.
- **Overlap:** (a) Standard Skyrim behavior.

**A documented table of relation-changing actions**
- **Concept:** Concrete deltas: attacking member (−10 to −50 by rank), healing wounded (+1 to +5, hard-capped), turning in bounty (+2), buying slave freedom (+4), selling to slavery (+1). "Pacifiers" NPC service: pay gold to improve relations, with banded fees and cooldown.
- **Rating:** Medium — good for legibility but not exciting.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension.

**No passive decay of faction relations**
- **Concept:** Faction relations don't decay automatically. Bounties decay separately. You must actively repair a broken faction relation.
- **Rating:** Low — design choice.
- **Feasibility:** Trivial.
- **Overlap:** (a) Design choice.

**Alliance-procedure knock-on costs**
- **Concept:** Joining the Stormcloaks costs −75 with Imperial factions. Turning in a hostile faction's leader-bounty is an irreversible break.
- **Rating:** Medium — creates meaningful choice but requires alliance framework.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension.

### 2.3 Crime, bounty, and delegated legal system

**Crime is strictly non-telepathic**
- **Concept:** Crime requires line-of-sight witness. No telepathic guards. Witness raises local alarm; alarm propagates to nearby guards. If no witness, no bounty.
- **Rating:** High — fixes Skyrim's most immersion-breaking system.
- **Feasibility:** Requires overriding Skyrim's crime system via SKSE. The engine's native crime system is telepathic; replacing it is hard but documented (see SKSE crime hooks, Po3's Papyrus extender). High effort.
- **Overlap:** (c) New — crime system overhaul.

**A full published crime-severity table**
- **Concept:** Trespassing (1 hr expiry), Looting (2 hr), Assault (4 hr), Burglary (8 hr), Theft (scaled to item value), Escaping prison (never expires), Terrorism (never expires), Kidnapping (never expires). Jail sentence = half expiry. Bounty value scaled.
- **Rating:** Medium — legibility improvement.
- **Feasibility:** Trivial data.
- **Overlap:** (b) Extension of crime system.

**Linear bounty-expiry formula**
- **Concept:** Bounty decays in real-time. ~4 hours per 100 bounty. Notoriety >10,000 = never expires. >50,000 = only paying bail (2× bounty) clears it.
- **Rating:** Medium — realism improvement.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension.

**Recognition scales with bounty size**
- **Concept:** Police recognize wanted characters fastest; civilians only recognize infamous. Recognition takes time — you can dash through town before being spotted.
- **Rating:** High — makes bounty evasion a skill, not just avoiding the hold.
- **Feasibility:** Requires SKSE to implement recognition cones/cooldowns. Moderate.
- **Overlap:** (c) New.

**Prison converts to slavery in pro-slavery jurisdictions**
- **Concept:** In holds with slavery (e.g., under certain modded or Chronicle-driven policies), caged characters can be enslaved and sent to mines. Slaver NPCs attempt to enslave any unconscious non-allied character.
- **Rating:** Medium — dark, niche. Fits some playthroughs but not a headline.
- **Feasibility:** Requires slavery framework. Moderate.
- **Overlap:** (c) New.

**Delegated legal systems**
- **Concept:** A minor faction (e.g., a mine) delegates legal system to a major faction (e.g., Markarth). Crimes against the minor faction accrue as bounty with the major faction, but only major-faction settlements have police.
- **Rating:** Low — too abstract for Skyrim's structure.
- **Feasibility:** Trivial abstraction.
- **Overlap:** (b) Extension.

**Only specific occupation-typed characters can issue a bounty**
- **Concept:** Only guards, soldiers, and law-enforcement roles can create bounties. A random farmer witnessing a crime can't issue a bounty, only raise alarm.
- **Rating:** Medium — realism.
- **Feasibility:** Trivial filter.
- **Overlap:** (b) Extension.

### 2.4 AI packages / squad data model

**Squads, AI Packages, Dialogue Packages**
- **Concept:** Chronicle groups NPCs into Squads (patrols, caravans, guard teams) with a Leader, Dialogue Leader, Faction, and prioritized AI Package list. Off-screen squads use a simplified "Unloaded Func" behavior path.
- **Rating:** Medium — infrastructure for group behavior.
- **Feasibility:** Skyrim has AI packages natively. Chronicle can override them via SKSE SetActorValue or package stacks. Moderate.
- **Overlap:** (c) New — squad abstraction.

**AI contracts**
- **Concept:** Dialogue-issued temporary package overrides. Hire a mercenary → they temporarily join your squad AI package. Contract expires after duration or event.
- **Rating:** Medium — mercenary contracts are already in Skyrim (vanilla follower system).
- **Feasibility:** Trivial via existing follower framework.
- **Overlap:** (a) Covered by vanilla.

**Off-screen simulation is fully suspended**
- **Concept:** Unloaded cells freeze entirely. World progression is faked via boolean world-state flags, not continued simulation. In Skyrim: accept this limitation. Don't try to simulate off-screen combat.
- **Rating:** Low — technical reality.
- **Feasibility:** N/A
- **Overlap:** (a) Standard engine behavior.

**A shallow dialogue-boolean model of "the NPC remembers you"**
- **Concept:** `Remember_Character` flag per NPC: "has spoken with player before." Situational memory of past deeds plus insult-then-ambush thug behavior. Lightweight.
- **Rating:** Medium — basic but necessary.
- **Feasibility:** Trivial.
- **Overlap:** (a) Covered by existing belief system.

---

## 3. Shadows of Doubt

**A 23-field Citizen Profile per NPC**
- **Concept:** Chronicle tracks rich NPC profiles: name, blood type (for alchemical reactions?), shoe size (for footprint matching), height, address, job, faction, secrets. Each field independently discoverable. Player builds profiles via investigation.
- **Rating:** Medium — investigation depth is fun for detective playthroughs but not a universal headline.
- **Feasibility:** Static data in Python. Discovery via dialogue, books, or SKSE-detected observation. Straightforward.
- **Overlap:** (b) Extension — adds fields to existing NPC records.

**Static/dynamic/relational citizen data**
- **Concept:** Static: appearance, blood type, fingerprint. Dynamic: wealth, health, home/work pointers, daily schedule. Relational: social-network graph (spouse, roommate, colleague, acquaintance).
- **Rating:** Medium — substrate for investigation.
- **Feasibility:** Social graph from Skyrim's RelationshipRank and faction data. Schedule from AI package analysis. Straightforward.
- **Overlap:** (b) Extension.

**Deterministic physical/digital trace instantiation**
- **Concept:** Purchase spawns physical receipt + merchant ledger entry. Phone calls log to building switchboards. Footprints/fingerprints left spatially and hash-linked to actor. In Skyrim: buying an item creates a "Receipt" misc item in the merchant's container. Murder weapon retains fingerprint (alchemical trace?).
- **Rating:** High — makes the world feel materially consistent and investigable.
- **Feasibility:** Receipts = custom MiscObject forms spawned via SKSE. "Fingerprints" can be abstracted as alchemical/ magical traces (more Skyrim-appropriate). Moderate.
- **Overlap:** (c) New — trace system.

**A periodic global visibility-check sighting loop**
- **Concept:** Pairwise line-of-sight checks between traveling NPCs. Positive check → sighting record (observed UUID, location, timestamp, suspicious flag) appended to observer's memory.
- **Rating:** High — creates alibis, witness networks, and conspiracy detection.
- **Feasibility:** LOS checks in Skyrim are expensive. Must be throttled (e.g., only in loaded cells, only every 5 seconds, only for nearby pairs). SKSE + Papyrus can do this but performance is a concern. High effort.
- **Overlap:** (c) New — sighting system.

**Three-phase memory decay**
- **Concept:** Precise → Fuzzy → Purged. Precise: exact identity/location/time. Fuzzy: broad descriptor, time window. Purged: garbage-collected. Decay rate = familiarity + distinctiveness + alertness + age.
- **Rating:** Medium — simulation depth, mostly invisible.
- **Feasibility:** Trivial Python.
- **Overlap:** (a) Already how belief decay should work.

**A "Facts" provenance graph with reliability-weighted edges**
- **Concept:** Every discovered thing has a case file. Facts are link objects connecting evidence folders, with reliability limiting incrimination flow. Visualized as corkboard strings (redness = incrimination, width = reliability). In Skyrim: a "Case File" book UI or MCM page.
- **Rating:** High — turns investigation into a tangible, visual puzzle.
- **Feasibility:** Custom UI (Dear ImGui or Scaleform). Graph layout in Python. Moderate to high effort.
- **Overlap:** (b) Extension of provenance — adds visualization.

**Fingerprint/name resolution chain**
- **Concept:** Traces lifted from weapons/surfaces tied to identity via records, database, or forcible sampling. Player builds their own notebook.
- **Rating:** Medium — investigation minigame.
- **Feasibility:** "Forcible sampling" = SKSE interaction with unconscious actors. Straightforward.
- **Overlap:** (b) Extension of trace system.

**Per-citizen alibi timelines**
- **Concept:** NPC daily routes plotted on map. Two timelines overlay to surface contradictions. "You say you were at the market, but the guard saw you at the keep."
- **Rating:** High — classic detective gameplay, very legible.
- **Feasibility:** Map UI requires custom overlay. Schedule data from AI packages. High effort.
- **Overlap:** (c) New — alibi system.

**Citizens can lie**
- **Concept:** NPCs whose true presence is incriminating may lie or bend truth even when innocent. Explicitly under-explored in Shadows of Doubt.
- **Rating:** High — makes interrogation a skill check, not just data retrieval.
- **Feasibility:** Requires deception logic in Python + dialogue injection for lies. Moderate.
- **Overlap:** (c) New — deception system.

**Press-appeal mechanic**
- **Concept:** Publicizing a case (via bard, courier, or town crier) prompts witnesses to proactively come forward. Resource-cost lever.
- **Rating:** Medium — good for breaking dead ends.
- **Feasibility:** Bard/courier dialogue injection via SKSE. Straightforward.
- **Overlap:** (b) Extension of rumor system.

**Batch-precompute-then-deviate scheduling**
- **Concept:** Daily routines precomputed in batch before day starts. Only deviating NPCs (reacting to body, alarm) computed in real-time. Murder pre-simulated at load.
- **Rating:** Low — optimization technique.
- **Feasibility:** Skyrim's AI packages are already precomputed. Chronicle can layer deviations on top.
- **Overlap:** (a) Standard engine behavior.

**Body-discovery failsafes**
- **Concept:** Layered guarantees ensure a body is always found: signs of forced entry, scream, smell of decomposition. Not purely emergent.
- **Rating:** Medium — prevents unsolvable cases.
- **Feasibility:** Trivial event triggers.
- **Overlap:** (b) Extension of event system.

**The "Case Generator" as provenance-anchored intervention**
- **Concept:** A murder case is generated by selecting a killer archetype (Corporate Cutthroat, Stalker, Sniper) who then executes the crime using real simulated relationships. The Corporate Cutthroat targets a real career rival; evidence (business card, graffiti) points to real simulation state. No clue is ever disconnected from state.
- **Rating:** High — the gold standard for procedural mystery. Every clue is grounded.
- **Feasibility:** Requires a case generation engine + real relationship graph + clue placement via SKSE. Very high effort.
- **Overlap:** (c) New — case generator.

---

## 4. The Nemesis System

**Procedurally generated enemies from a base template**
- **Concept:** Named enemies (bandit chiefs, dragon priests) generated from templates with randomized appearance, voice type, personality archetype (The Braggart, The Coward, The Fanatic), and mechanical traits (fear of fire, immunity to sneak). NOT the Uruk hierarchy — just the template randomization.
- **Rating:** Medium — adds variety but randomization alone isn't a social system.
- **Feasibility:** Appearance randomization via SKSE face morphs. Voice type limited by vanilla assets. Personality as data. Moderate.
- **Overlap:** (c) New — enemy generation.

**Discrete combat-outcome "verbs" that mutate persistent state**
- **Concept:** Player Death → surviving enemy gains power, taunts next encounter. Player Flight → enemy logs cowardice, gains confidence. Severe Injury → enemy returns with scars (equipment change) and references the defeat method.
- **Rating:** High — creates personal villains with history.
- **Feasibility:** Scars = equipment swap via SKSE. Taunts = dialogue injection (text only). Power gain = stat buff via SKSE. Moderate.
- **Overlap:** (c) New — personal enemy state.

**Combinatorial dialogue selection**
- **Concept:** Audio fragments chosen by: personality + rank + past outcome + current condition. "You burned me last time, Dragonborn — I've learned to fear the flame!"
- **Rating:** High — makes enemies feel responsive.
- **Feasibility:** Requires xVASynth or text-only subtitles. Combinatorial selection logic in Python. Moderate.
- **Overlap:** (b) Extension of enemy state.

**A ranked hierarchy with automated vacancy-filling**
- **Concept:** EXPLICITLY DISALLOWED by Chronicle design rules. Do not implement.
- **Rating:** N/A
- **Feasibility:** Patent-encumbered. Skip.
- **Overlap:** N/A

**Autonomous background hierarchy events**
- **Concept:** EXPLICITLY DISALLOWED (requires ranked hierarchy).
- **Rating:** N/A
- **Feasibility:** Skip.
- **Overlap:** N/A

**Domination, followers, and betrayal**
- **Concept:** EXPLICITLY DISALLOWED (ranked hierarchy + domination chain).
- **Rating:** N/A
- **Feasibility:** Skip.
- **Overlap:** N/A

**Tuned probability curves for pacing**
- **Concept:** Survival probability scales inversely with active rivalries (prevent saturation). Ambush timers throttled. In Skyrim: if you have 3 active nemeses, no new nemesis can form until one is resolved.
- **Rating:** Medium — necessary anti-frustration.
- **Feasibility:** Trivial.
- **Overlap:** (a) Best practice.

**The load-bearing simplification: only named captains carry persistent memory**
- **Concept:** Only named boss-level NPCs carry persistent memory. Grunts are stateless. In Skyrim: only named NPCs (bandit chiefs, dragon priests, faction leaders) get Chronicle tracking. Random bandits are forgotten.
- **Rating:** Medium — design constraint, not a feature.
- **Feasibility:** Trivial whitelist.
- **Overlap:** (a) Performance necessity.

**Documented feature-creep near-failure**
- **Concept:** Lesson: don't track separate Morale/Discipline bars for every faction. Keep it simple.
- **Rating:** Low — design lesson.
- **Feasibility:** N/A
- **Overlap:** (a) Best practice.

**Patent boundary**
- **Concept:** What's protected: avatar↔first-NPC interaction changing a second NPC's parameters in a ranked hierarchy, surfacing in dialogue. What's free: single NPC remembering its own encounters; per-observer reputation; standalone faction succession without two-NPC linkage. Chronicle stays safely in the free zone.
- **Rating:** N/A
- **Feasibility:** Legal research already done.
- **Overlap:** N/A

---

## 5. RimWorld

### 5.1 Mood / mental-break system

**A mood-bar scalar with a per-pawn Mental Break Threshold stat**
- **Concept:** NPC Mood meter (0–100) with individual Break Threshold (default 35%, modified by traits). Three bands: Minor (below threshold, ~10 days to break), Major (below 4/7 threshold, ~3 days), Extreme (below 1/7 threshold, ~0.7 days). Visible as a color-coded bar in Chronicle UI.
- **Rating:** High — visible, predictable crisis moments.
- **Feasibility:** Mood computed in Python. UI via SKSE overlay. Straightforward.
- **Overlap:** (c) New — mood system.

**A documented weighted-random-within-band selection algorithm**
- **Concept:** Band is deterministic; specific break within band is weighted random filtered by eligibility. Pyromaniac keeps "Fire starting spree" eligible. Rage break less likely in small settlements. Jailbreaker needs reachable prisoner.
- **Rating:** Medium — implementation detail.
- **Feasibility:** Trivial Python.
- **Overlap:** (b) Extension of mood system.

**A large named break catalogue**
- **Concept:** Minor: Sad wander, Food binge, Hide in room, Insulting spree. Major: Tantrum, Psychotic wandering, Corpse obsession. Extreme: Berserk, Fire starting spree, Murderous rage, Catatonic. In Skyrim: NPCs can binge drink at taverns, wander the wilderness, insult passersby, start fistfights, or go on murder sprees.
- **Rating:** High — visible, dramatic world events.
- **Feasibility:** Breaks as Chronicle-driven radiant events. Requires SKSE to move NPCs, trigger combat, etc. Moderate.
- **Overlap:** (c) New — break catalogue.

**Multi-channel telegraphing/legibility**
- **Concept:** Threshold-marked mood bar, escalating alerts with sound intensity, itemized thought tooltip, visual state indicator (name color + lightning bolt icon colored by aggressiveness).
- **Rating:** Medium — legibility essential but not a feature.
- **Feasibility:** UI work. Straightforward.
- **Overlap:** (a) Surfacing.

**Fixed recovery windows per break type**
- **Concept:** Breaks last a fixed duration. Endable early via arrest (chance-based, −8 "was imprisoned" thought), downing/beating (only way to stop Berserk), forced-calm spell.
- **Rating:** Medium — necessary mechanics.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension.

**A named anti-spiral device: the "Catharsis" thought**
- **Concept:** After a break resolves, NPC gets +40 mood for 2.5 days (Catharsis). Prevents cascading breakdowns.
- **Rating:** Medium — invisible stabilizer.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension.

**Design-pillar framing**
- **Concept:** "Story generator" framing — mechanics must include loss and recovery, not just loss.
- **Rating:** Low — design philosophy.
- **Feasibility:** N/A
- **Overlap:** (a) Design principle.

### 5.2 Opinion / social-thought system

**Opinion is computed on demand, never stored**
- **Concept:** Opinion is live sum of active thoughts + base + modifiers. Recomputed every query. In Chronicle: opinion is always current, never stale.
- **Rating:** Low — implementation detail.
- **Feasibility:** Trivial.
- **Overlap:** (a) Already how any sane system works.

**`Thought_Memory` objects with explicit duration and stack limit**
- **Concept:** Each thought has age, duration, stack limit, and diminishing returns. Duplicate thoughts renew existing rather than stacking. "Insulted −15/20 days, stacks 10× at ×0.9 each."
- **Rating:** Medium — prevents exploit stacking.
- **Feasibility:** Trivial.
- **Overlap:** (a) Standard belief decay.

**A large published numeric table of social-thought values**
- **Concept:** Concrete values visible to player: Insulted −15, Kind words +15, Slighted −5, Deep talk +15, Harmed me −15, Botched surgery −20, Rescued me +15. Family base opinions: spouse +30, lover +35, ex −15. Death penalties: killed spouse −65, killed parent −80.
- **Rating:** Medium — legibility.
- **Feasibility:** Trivial data.
- **Overlap:** (b) Extension.

**Social fights as probabilistic escalation from insults**
- **Concept:** Every insult has small chance to trigger a fistfight, resolved as cathartic (+mood) or angering (−mood).
- **Rating:** Medium — adds spice to social interactions.
- **Feasibility:** Fistfights via SKSE StartCombat with fists only. Straightforward.
- **Overlap:** (b) Extension.

### 5.3 Storyteller / world-event pacing director

**Incidents sampled from probability tables on a mean-time-between basis**
- **Concept:** World events (bandit raids, dragon attacks, merchant caravans) are not simulated causally but rolled on a schedule. Different "Storyteller" personas: "Classic" (big threats ~3.75 days apart), "Randy Random" (~1.13 days).
- **Rating:** High — makes the world feel unpredictably alive without simulating everything.
- **Feasibility:** Event scheduler in Python. SKSE injects events. Straightforward.
- **Overlap:** (c) New — event director.

**A published raid-point formula**
- **Concept:** Threat intensity = (Wealth + Followers) × Difficulty × Adaptation. Wealth linearly interpolated. Minimum thresholds gate specific threat types (dragon attack needs 5000 points, giant attack needs 1000).
- **Rating:** Medium — learnable curve, good for legibility.
- **Feasibility:** Trivial math.
- **Overlap:** (b) Extension of event director.

**A documented, exploitable failure mode: wealth-gaming**
- **Concept:** Threat scales off raw wealth, so players hide wealth to suppress raids. Lesson: any input a director trusts as ground truth will be gamed. Chronicle should use un-launderable inputs (completed quests, NPC deaths) rather than inventory value.
- **Rating:** Low — design lesson.
- **Feasibility:** N/A
- **Overlap:** (a) Best practice.

### 5.4 Off-screen entity persistence

**Object-identity preservation across loaded/unloaded boundary**
- **Concept:** Off-map NPCs are the same object in Python, not regenerated. Needs, health, relationships preserved.
- **Rating:** Medium — essential for consistency but invisible.
- **Feasibility:** Trivial — Python is the source of truth.
- **Overlap:** (a) Core architecture.

**A "mothball" tier**
- **Concept:** NPCs with no active changes tick once per day instead of continuously. Catch-up tick before re-entry.
- **Rating:** Low — optimization.
- **Feasibility:** Trivial.
- **Overlap:** (a) Performance feature.

**Abstract per-day need accounting for caravans**
- **Concept:** Caravan members use fixed daily hunger/forage rates rather than per-meal simulation.
- **Rating:** Low — optimization.
- **Feasibility:** Trivial.
- **Overlap:** (a) Standard.

**A reachability-graph garbage collector**
- **Concept:** "Critical" NPCs (faction leaders, quest targets, anyone with relation to on-map NPC) preserved. Others discarded. Failure modes: over-keeping (bloat) and under-pinning (broken relationships).
- **Rating:** Low — memory management.
- **Feasibility:** Trivial.
- **Overlap:** (a) Standard.

**"Alibi generation"**
- **Concept:** Generate visible info up front; retroactively generate invisible backstory only when player interacts. Player can't tell if NPC "was always there" or was just given history.
- **Rating:** Medium — powerful illusion but requires careful implementation.
- **Feasibility:** Requires lazy backstory generation. Moderate.
- **Overlap:** (c) New — alibi generation.

---

## 6. Dwarf Fortress

### 6.1 Stress / emotion → behavior mapping

**Two hidden numeric stress axes**
- **Concept:** Short-term stress (visible mood) + long-term stress (slow accumulation, years to rise/fall). Breakdowns require both axes elevated. In Skyrim: a NPC can seem fine day-to-day but have years of trauma, then one more death triggers collapse.
- **Rating:** High — creates "slow burn" narratives and surprises that feel earned.
- **Feasibility:** Two floats per NPC. Trivial.
- **Overlap:** (b) Extension of stress system.

**Personality facets modulating stress mapping**
- **Concept:** Bravery (gain rate), stress vulnerability (breaking point), anxiety (dissipation rate), depression propensity, anger propensity.
- **Rating:** Medium — invisible modifiers.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension.

**A branching outcome tree of temporary breakdowns**
- **Concept:** Tantrum (throws objects, starts fights), Depression (cancels jobs, repeats into Melancholy), Obliviousness (aimless wandering). Permanent insanity: Melancholy (stops eating), Stark Raving Mad (ignores needs), Berserk (attacks all), Catatonic.
- **Rating:** High — dramatic, visible, and permanent consequences make stress matter.
- **Feasibility:** Tantrum = SKSE-triggered combat/vandalism. Depression = AI package override. Permanent states = trait application. Moderate.
- **Overlap:** (b) Extension of break catalogue.

**Strange moods**
- **Concept:** Positive-flavored takeover: NPC enters mood, claims a workspace, hunts for specific materials. Success = unique artifact + skill gain. Failure = insanity/death. In Skyrim: blacksmith enters "Inspired" mood, demands specific ore, produces a unique-named weapon.
- **Rating:** High — creates unique items and personal stories.
- **Feasibility:** Requires custom crafting event + unique item generation. Moderate.
- **Overlap:** (c) New — mood-driven crafting.

**A true state-machine takeover**
- **Concept:** Mood sets a distinct enum that suppresses normal AI entirely. Not just a high-priority task.
- **Rating:** Low — implementation detail.
- **Feasibility:** SKSE can override AI packages completely. Straightforward.
- **Overlap:** (a) Standard AI override.

**Pause-and-announce legibility**
- **Concept:** Game pauses, centers camera, colored announcement: "Uthgerd has gone stark raving mad!" Attributes threshold to specific individual at specific moment.
- **Rating:** Medium — good for visibility but can be intrusive.
- **Feasibility:** SKSE can pause game, move camera, display notification. Straightforward.
- **Overlap:** (a) Surfacing.

**Slow decay-to-baseline recovery**
- **Concept:** Recovery via fulfilled needs: quality bedroom, legendary dining hall, meaningful work, temple prayer, tavern socializing. "Therapy Squad" = scheduled military training that satisfies needs.
- **Rating:** Medium — recovery mechanics are necessary but not exciting.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension.

**A documented historical failure cascade**
- **Concept:** Pre-rewrite "unhappiness" model produced tantrum spirals. Current model slows and individualizes breakdowns. Lesson for Chronicle: don't let one death collapse a whole city.
- **Rating:** Low — design lesson.
- **Feasibility:** N/A
- **Overlap:** (a) Best practice.

### 6.2 Memory

**A three-tier fixed-slot memory store**
- **Concept:** 8 short-term slots, 8 long-term, larger core store. Grouped by category; strongest per group holds slot. New same-group thought replaces only if stronger. New different-group overwrites weakest existing.
- **Rating:** Medium — creates realistic forgetting but mostly invisible.
- **Feasibility:** Trivial Python.
- **Overlap:** (a) Already how buffer systems work.

**Time-gated promotion between tiers**
- **Concept:** Short-term memory survives ~1 year → promotes to long-term. Long-term periodically revisited (re-applies stress). 1-in-3 chance to promote to core memory → permanent personality-facet change, then removed from long-term.
- **Rating:** High — memories literally change who NPCs are over years.
- **Feasibility:** Trivial Python.
- **Overlap:** (b) Extension of memory system.

**A two-tier world-vs-personal data split**
- **Concept:** Global `historical_event` log (unbounded). Personal memory is small, lossy buffer referencing global log.
- **Rating:** Low — architecture.
- **Feasibility:** Trivial.
- **Overlap:** (a) Standard.

### 6.3 Physical evidence / provenance objects

**Engravings and slabs generated from serialized links**
- **Concept:** Inspecting a memorial slab surfaces a generated description naming actual depicted figures and events. Weighted over which events get chosen. Recent events disfavored.
- **Rating:** Medium — flavor for world items.
- **Feasibility:** Requires custom book/slab objects with dynamic text. SKSE can set book text at runtime (documented). Moderate.
- **Overlap:** (b) Extension of provenance.

**Memorial slabs resolve ghosts without a body**
- **Concept:** Slab for dead figure records arrival/death/killer. Lays ghost to rest. Deconstructing slab re-raises ghost. Bidirectional provenance link.
- **Rating:** High — ties into Skyrim's existing ghost mechanics and gives them narrative weight.
- **Feasibility:** Requires ghost encounter system + slab object. Moderate.
- **Overlap:** (c) New — ghost resolution mechanic.

**Artifact descriptions pull from creator's preferences and linked historical events**
- **Concept:** Unique items have generated descriptions from creator's memories. "This axe was forged by Uthgerd after her brother's death at the Western Watchtower." Artifacts propagate: stolen, moved, warred over. "Destroyed" artifacts flagged Hidden, can respawn.
- **Rating:** High — makes unique items feel historically grounded and valuable beyond stats.
- **Feasibility:** Dynamic item naming/description via SKSE. Artifact propagation requires tracking item reference across containers/cells (hard in Skyrim — items lose identity when moved). High effort.
- **Overlap:** (c) New — artifact provenance.

### 6.4 Rumor system

**Six discrete confidence tiers of secondhand knowledge**
- **Concept:** Knowledge confidence: Direct possession → heard recently → heard generally → legend → none. About artifact locations, NPC whereabouts, etc.
- **Rating:** Medium — adds texture to information.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension of rumor system.

**Time-stamped decay at four nested scopes**
- **Concept:** Decay at individual, hold government, hold culture, and civilization level. Detailed knowledge fades over weeks; reputation persists.
- **Rating:** Low — simulation detail.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension.

**A hard design rule: content is never distorted in transit**
- **Concept:** Rumors are true but less detailed. Only sanctioned falsehood is misattributed identity (vampires, agents). Killing witnesses and hiding the body suppresses rumor spread.
- **Rating:** High — makes information warfare tangible. Hiding bodies matters.
- **Feasibility:** Trivial — rumor fidelity is a design choice.
- **Overlap:** (a) Design principle already in scope.

---

## 7. AI directors / drama management

### 7.1 Shipped director architectures

**Façade's Beat Manager**
- **Concept:** Selects next authored beat based on discourse signals and tension/affinity score. In Skyrim: a "Scene Director" for companion conversations or Jarl court scenes, selecting beats based on current social state.
- **Rating:** Medium — good for authored scenes but limited to confined spaces.
- **Feasibility:** Requires scene/quest authoring. Moderate.
- **Overlap:** (c) New — beat director.

**Left 4 Dead's Director**
- **Concept:** Four-state FSM (Build Up → Peak → Sustained Peak → Relax) driven by damage/health/mobility. Controls spawn caps and item drops. Always telegraphed before intervention (audio shift, music stinger, character barks).
- **Concept for Skyrim:** "Wilderness Director" for travel encounters: tension builds based on time since last combat, player health, follower status. Peaks spawn ambush, then relaxes with a safe camp and loot. Musical stingers via SKSE audio playback.
- **Rating:** High — makes wilderness travel feel paced and cinematic.
- **Feasibility:** SKSE can spawn encounters, play audio, track player state. Moderate.
- **Overlap:** (c) New — travel director.

**King of Dragon Pass's storylet engine**
- **Concept:** Prolog-style constraint match over faction/magic/season/clan-mood, drawing from priority-banded storylets, presented as advisor commentary.
- **Concept for Skyrim:** Seasonal "Hold Council" storylets (see 1.12).
- **Rating:** High (see 1.12).
- **Feasibility:** (see 1.12).
- **Overlap:** (c) New.

**PaSSAGE**
- **Concept:** Player actions annotated with playstyle vector modifiers (Fighter/Tactician/Storyteller/Method Actor). Next encounter selected by dot-product match.
- **Concept for Skyrim:** Chronicle tracks player playstyle (Combat/Stealth/Magic/Social). Radiant quests and encounters selected to match. A Social player gets more dialogue quests; a Combat player gets more bandit camps.
- **Rating:** Medium — risks flattening experience (pure Fighter never sees quiet content).
- **Feasibility:** Playstyle vector computed from action history. Trivial. Encounter selection requires radiant quest hooks. Moderate.
- **Overlap:** (c) New — playstyle tracking.

**DeepMind Concordia's LLM Game Master loop**
- **Concept:** Agents emit intent strings; GM validates against grounded variables; updates state; synthesizes Event Statement; pushes to nearby agents' memory.
- **Concept for Skyrim:** NOT using LLM for state mutation. Instead: NPCs emit "intent" (attack, flee, gossip) to Chronicle Python engine. Engine validates against real state (line of sight, inventory, faction). On success, engine mutates state and generates a memory entry. On failure, generates a "failed intent" memory.
- **Rating:** Medium — good architecture principle but not player-visible.
- **Feasibility:** Trivial — this is essentially how Chronicle already works.
- **Overlap:** (a) Core architecture.

**RimWorld's Storyteller**
- **Concept:** See 5.3.
- **Rating:** (see 5.3)
- **Feasibility:** (see 5.3)
- **Overlap:** (see 5.3)

### 7.2 Formal/academic drama-management lineages

**Symbolic narrative planning (IPOCL)**
- **Concept:** STRIPS-style search forcing every character action to be motivated by their own goals. Prevents "suicidal puppet" actions.
- **Concept for Skyrim:** NPC actions in Chronicle must pass a "motivation check": does this action serve the NPC's goals (survival, wealth, revenge, loyalty)? If not, veto and replan.
- **Rating:** Medium — invisible but produces believable behavior.
- **Feasibility:** Requires goal-based AI planner. High effort.
- **Overlap:** (c) New — motivation engine.

**Declarative Optimization Drama Management (DODM)**
- **Concept:** Search-based drama management found not to transfer when intervention actions were too weak. Lesson: the available authorial vocabulary matters more than the algorithm.
- **Rating:** Low — design lesson.
- **Feasibility:** N/A
- **Overlap:** (a) Best practice.

**Targeted Trajectory Distribution MDPs**
- **Concept:** Director steers toward a distribution of experiences, not a single optimal trajectory. Preserves agency.
- **Concept for Skyrim:** Chronicle's event director maintains a "target distribution" of event types (30% combat, 20% social, 20% exploration, 30% mystery). If the player has had 5 combats in a row, the next roll is heavily biased toward non-combat.
- **Rating:** Medium — invisible stabilizer.
- **Feasibility:** Trivial.
- **Overlap:** (b) Extension of event director.

**Plan-based mediation (Mimesis)**
- **Concept:** When player breaks the plan, mediator intervenes (blocks) or accommodates (replans). Retroactive revision limited to unobserved world aspects.
- **Concept for Skyrim:** If player kills a quest-critical NPC early, Chronicle can retroactively establish that the NPC had a twin (unobserved) or that the quest goal can be achieved another way. But if the player *saw* the NPC die alone, no revision.
- **Rating:** High — saves broken quests and makes the world feel robust.
- **Feasibility:** Requires quest-state monitoring + fallback authoring. High effort.
- **Overlap:** (c) New — quest mediation.

**Daggerfall's actual quest format**
- **Concept:** 227+ quests gated by guild/social-class membership and reputation rank. Templates mean different things at different reputation levels. "Radiant content" works because templates are embedded in a reputation economy.
- **Concept for Skyrim:** Chronicle's radiant quests are not generic "kill bandit" but contextually modified by player's current reputation with the quest-giver's faction. High reputation = "Retrieve our stolen artifact." Low reputation = "Prove yourself by killing a giant."
- **Rating:** High — makes radiant quests feel authored and responsive.
- **Feasibility:** Requires a template quest system with parameter injection. Moderate.
- **Overlap:** (c) New — contextual radiant quest system.

**A published storylet academic thread**
- **Concept:** Quest engine generates quests from world state at generation time. Space of possible quests grows as world state enriches.
- **Concept for Skyrim:** The more NPCs die, relationships form, and factions shift, the more quest material exists. A feud between two families generates a "mediate the feud" quest. A dragon attack generates a "recover the remains" quest.
- **Rating:** High — world-driven quest generation is the ultimate "alive world" signal.
- **Feasibility:** Requires storylet precondition engine + quest template system. High effort.
- **Overlap:** (c) New — generative quest system.

**Storylet role-casting**
- **Concept:** Treat every situation as a storylet with precondition-gated role slots. Cast real, specific sifted entities into roles.
- **Concept for Skyrim:** A "Bandit Ambush" storylet has slots: BanditLeader (must be a Rival of player or faction enemy), Victim (must be a Friend of player traveling nearby), Location (must be a road between two holds). The engine searches real NPCs and picks ones that match.
- **Rating:** High — the single highest-value pattern. Makes generic events feel personal.
- **Feasibility:** Requires storylet engine + real-time NPC query. Moderate.
- **Overlap:** (c) New — role-casting engine.

### 7.3 LLM-narrator-specific failure/success record

**AI Dungeon / Hidden Door consumer record**
- **Concept:** Lessons: memory drift, ungrounded generation, latency kills pacing. NPCs that self-organize optimally leave players with nothing to do.
- **Rating:** Low — negative lessons for Chronicle. Confirms avoiding LLMs for state mutation.
- **Feasibility:** N/A
- **Overlap:** (a) Design validation.

**NCP-Bench (2026)**
- **Concept:** Benchmark: LLMs fail at long-horizon constraint satisfaction. Fact conflicts in 40–68% of runs. Only ~3.5% reach 100 turns without conflict.
- **Rating:** Low — academic validation.
- **Feasibility:** N/A
- **Overlap:** (a) Design validation.

**Orchestrated Reality / WorldLines**
- **Concept:** Formalizes LLM world as Parameterized-Action POMDP. LLM proposes, validator commits schema-validated deltas. Un-schematized details still drift.
- **Rating:** Low — architecture reference.
- **Feasibility:** N/A
- **Overlap:** (a) Design validation.

**Neuro-symbolic TSL automata**
- **Concept:** Correct-by-construction automaton decides LLM prompt modifier each turn. 96% adherence vs. 15% pure LLM.
- **Rating:** Low — academic reference.
- **Feasibility:** N/A
- **Overlap:** (a) Design validation.

**Slice of Life**
- **Concept:** Deterministic symbolic simulation core + LLM only for surface text. Never let dialogue feed back into simulation state.
- **Rating:** Low — architecture reference.
- **Feasibility:** N/A
- **Overlap:** (a) Design validation.

**Function-calling as a hard validity gate (LLMaker)**
- **Concept:** LLM emits structured function calls into constraint-enforcing backend. Zero invalid outputs.
- **Rating:** Low — architecture reference.
- **Feasibility:** N/A
- **Overlap:** (a) Design validation.

**Drama Llama (2025)**
- **Concept:** LLM-powered storylets where human authors write 3–4 pivot triggers, LLM improvises within bounds.
- **Concept for Skyrim:** Human authors write storylet preconditions and outcomes; LLM generates dialogue text within those bounds. But Chronicle explicitly avoids LLMs for state mutation, so this is text-only.
- **Rating:** Medium — possible future text generation layer, but not core.
- **Feasibility:** Requires LLM integration. High effort, uncertain value.
- **Overlap:** (c) New — optional text layer.

**Symbolically Scaffolded Play ("The Interview")**
- **Concept:** No single prompt design reliably improves play. Over-constraining diminishes improvisation. Working pattern: rigid structure for quest-givers, loose for open-ended roles, shared JSON memory.
- **Rating:** Low — design lesson.
- **Feasibility:** N/A
- **Overlap:** (a) Design validation.

**Friends & Fables' Franz-v1 → ACE-1 redesign**
- **Concept:** Core lesson: separate AI Game Master ("face") from campaign engine ("truth"). Replace hierarchical memory with atomic memory units. Add "View Context" so players inspect what the GM saw.
- **Concept for Skyrim:** Chronicle's Python engine is already the "truth." The C++ plugin is the "face." Add a "View Context" debug UI showing exactly what data the plugin queried for a given NPC response.
- **Rating:** Medium — legibility feature.
- **Feasibility:** Trivial debug UI.
- **Overlap:** (b) Extension — better surfacing.

### 7.4 Named, general failure-mode taxonomy

**Visible railroading**
- **Concept:** Repeated nullification of player action. Chronicle must avoid: if player kills an NPC, they stay dead. No "essential" flags overridden by Chronicle.
- **Rating:** Low — anti-pattern.
- **Feasibility:** N/A
- **Overlap:** (a) Design guardrail.

**Ungrounded generation**
- **Concept:** Retroactively deciding facts at presentation. Chronicle must pre-commit to world state before player encounters it.
- **Rating:** Low — anti-pattern.
- **Feasibility:** N/A
- **Overlap:** (a) Design guardrail.

**Agency-destroying optimization**
- **Concept:** Director forcing a single "best" story. Chronicle must maintain a distribution of valid outcomes.
- **Rating:** Low — anti-pattern.
- **Feasibility:** N/A
- **Overlap:** (a) Design guardrail.

**Memory inconsistency**
- **Concept:** Forgotten facts. Chronicle's atomic memory + Python source-of-truth prevents this.
- **Rating:** Low — anti-pattern.
- **Feasibility:** N/A
- **Overlap:** (a) Core architecture.

**Deceptive provenance**
- **Concept:** Generated content disguised as authored. Chronicle should label generated quests as "Rumored" or "Emergent" so players know the system generated them.
- **Rating:** Low — transparency issue.
- **Feasibility:** Trivial.
- **Overlap:** (a) Best practice.

**Static-world exposure**
- **Concept:** Returning to a location that hasn't changed exposes the simulation as static. Chronicle must ensure visited locations show signs of time passing (new rumors, moved NPCs, changed merchant inventories).
- **Rating:** Medium — requires continuous micro-updates.
- **Feasibility:** Moderate — requires periodic cell updates.
- **Overlap:** (b) Extension of world-state system.

**Unsolvable/unrewarding generated content**
- **Concept:** A quest that silently breaks. Chronicle must test all generated quest paths or constrain generation to verified templates.
- **Rating:** Low — anti-pattern.
- **Feasibility:** N/A
- **Overlap:** (a) Best practice.

**Promised policy not implemented**
- **Concept:** A stated rule that runtime doesn't match. Chronicle must ensure documented mechanics actually work.
- **Rating:** Low — QA issue.
- **Feasibility:** N/A
- **Overlap:** (a) Best practice.

**Simulation illegibility**
- **Concept:** Depth that presentation can't surface. Lesson: don't simulate population growth if the player can't see it.
- **Rating:** Low — design lesson.
- **Feasibility:** N/A
- **Overlap:** (a) Best practice.

**Perceived-vs-statistical fairness mismatch**
- **Concept:** Math can be fair but feel unfair. Chronicle must telegraph probabilities and avoid "hidden rolls."
- **Rating:** Low — design lesson.
- **Feasibility:** N/A
- **Overlap:** (a) Best practice.

---

## 5. Ranked Top 10

1. **Storylet Role-Casting (§7.2)** — Casting real NPCs with real grudges into storylet slots makes every generated event feel personally authored rather than templated; the single highest-leverage pattern for an "alive world."

2. **World-State Town Overrides (§2.1)** — Boolean flags driving visible hold changes (merchant tables, guard spawns, building states) after civil war/dragon events; the most direct way to make Skyrim's world react to history.

3. **Case Generator with Provenance-Anchored Clues (§3)** — Murders where the killer is a real NPC with real motives, evidence points to real simulation state, and clues are never disconnected; turns investigation into a genuine puzzle.

4. **Named Relationship Crystallization + Mechanical Effects (§1.2)** — Friend/Rival/Lover/Nemesis flags with gameplay consequences (follower buffs, crafting sabotage, duel challenges, human shields); discrete relationships are infinitely more legible than opaque opinion numbers.

5. **Stress / Mental Break System (§1.4, §6.1)** — Per-NPC stress with threshold-triggered visible breakdowns (tavern binges, fistfights, murderous rage, catatonia); makes the social simulation spill into the streets as observable chaos.

6. **Dread / Intimidation Scalar (§1.10)** — A second social axis separate from opinion; enables tyrant playthroughs where NPCs obey out of fear, join factions out of terror, and flee combat; distinct from vanilla Speech checks.

7. **Faction Power / Discontent Accrual (§1.6)** — Rebellion factions accrue discontent based on measurable power ratios, with hard thresholds for ultimatums; makes civil war a simmering, player-influenceable pressure system rather than a binary questline.

8. **Non-Telepathic Crime / Witness System (§2.3)** — Crime requires line-of-sight witnesses, alarm propagation, recognition scaling with bounty, and witness killing to suppress rumors; fixes Skyrim's most immersion-breaking system and makes stealth/social play deeper.

9. **Contextual Radiant Quests from World State (§7.2 Daggerfall + storylet thread)** — Radiant quests that draw from real faction tensions, recent deaths, and relationship graphs, modified by reputation rank; makes the "infinite quest" loop feel responsive rather than repetitive.

10. **Alibi Timelines + Contradiction Overlay (§3)** — NPC daily routes plotted and overlayable; the core of a detective gameplay loop that leverages Skyrim's existing schedules and makes time/location into real evidence.

---

## 6. Explicit Discard List

- **CK2 flat-then-drop decay (§1.1)** — Implementation detail, not a feature. CK3 gradual is obviously better.
- **Diplomacy-skill-scaled opinion (§1.1)** — Passive scalar; Skyrim already has Speech checks. Doesn't make the world feel alive.
- **CK3 Council mechanics (§1.7)** — Doesn't map to Skyrim's flat hold structure without inventing a council abstraction that doesn't exist in the world.
- **Kenshi: Swap only while unloaded (§2.1)** — Technical constraint, not a design choice.
- **Kenshi: Off-screen simulation suspended (§2.4)** — Engine reality, not a feature.
- **Nemesis: Ranked hierarchy + vacancy-filling (§4)** — Explicitly patent-encumbered and design-forbidden.
- **Nemesis: Domination/betrayal chains (§4)** — Patent-encumbered.
- **RimWorld: Mothball tier / abstract need accounting / GC (§5.4)** — Optimization internals, invisible to players.
- **RimWorld: Wealth-gaming lesson (§5.3)** — Design lesson, not a mechanic.
- **DF: State-machine takeover detail (§6.1)** — Implementation detail.
- **DF: Two-tier world/personal split (§6.2)** — Architecture, not player-facing.
- **All LLM-specific academic entries (§7.3)** — Validate Chronicle's avoidance of LLMs but are not mechanics to implement.
- **All failure-mode taxonomy items (§7.4)** — Anti-patterns and lessons, not buildable features. Most are already guarded against by Chronicle's architecture.
- **Total War / Bannerlord / Twilight Bazaar as negative lessons (§1.12)** — Already absorbed as design principles.
- **CK3 Vassal Stance (§1.1)** — Actually kept in Top 10 thinking, but on second thought: Skyrim holds don't have enough policy levers to make stances meaningful. Too much abstraction for too little visible payoff. **Moved to discard** — better to invest in world-state overrides.

---

## 7. Missing from Catalog

- **Crusader Kings III: Struggle / Phase system** (e.g., Iberian Struggle) — A multi-phase regional conflict with distinct rules per phase (Opportunity, Hostility, Tension, Compromise). Each phase enables/disables specific interactions and CBs. Not in catalog. For Skyrim: the Civil War could have phases (Cold War, Open Conflict, Stalemate, Reconciliation) that change what quests, crimes, and alliances are possible hold-by-hold.

- **RimWorld: Ideoligion / Belief system (Ideology DLC)** — Social conflicts driven by divergent memes (proselytizing, cannibalism, slavery approval). Rituals, moral guides, and conversion mechanics. Notably absent despite the catalog covering base RimWorld extensively. For Skyrim: holds could have divergent religious practices (Talos worship intensity, Daedra tolerance) that create social friction and conversion quests.

- **Dwarf Fortress: Relationships (family, friends, grudges) in world generation** — The worldgen layer creates historical family trees, affairs, and wars before play begins. The catalog covers in-fortress memory but not the worldgen social layer. For Skyrim: pre-seeding the world with generated historical grudges and marriages so NPCs already have history when the player first meets them.

- **Shadows of Doubt: The actual social simulation of citizens (marriages, affairs, employment, finances)** — The catalog covers the detective/investigation layer well but misses that citizens have full simulated lives (they get paid, pay rent, form/break relationships, get fired, move houses) independent of the player. For Skyrim: NPCs could have simulated economics (salary, rent, savings) that drive their behavior (desperate NPCs turn to theft, wealthy NPCs throw feasts).

- **Kenshi: The slavery economy as a social system** — Beyond the legal note, the catalog doesn't cover how slavery is an economic system (slave camps produce goods, slave rebellions have economic consequences, freeing slaves shifts faction production). For Skyrim: a more detailed economic web where hold prosperity is tied to mine production, which is tied to labor conditions.

- **The Nemesis System: Orc "Blood Brothers" and rivalry networks** — The catalog mentions Blood Brothers briefly but doesn't detail the pre-War social graph (who hates whom, who is whose rival, who trained together). For Skyrim: pre-established rivalries between bandit chiefs or faction members that the player can exploit or be caught in.

- **Wildermyth: Legacy / generational carryover** — Heroes retire, their traits and relationships influence the next generation. The catalog covers relationships but not legacy. For Skyrim: a "generational" mode where time passes, NPCs age and die, and their children inherit modified traits and memories.