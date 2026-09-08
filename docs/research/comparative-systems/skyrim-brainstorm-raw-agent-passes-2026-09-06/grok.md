**1. Crusader Kings II / III**

### 1.1 Relationship/opinion tracking

**Directed pairwise opinion.**  
- Concepts: Track directed opinion scalars (A→B) in Python for every named NPC pair that interacts; surface as disposition deltas + tooltip-style dialogue lines citing the top modifiers. Triggers: witnessed crimes, gifts, civil-war side choice, dragon-attack survival. Player sees: NPC refuses service or greets with “You left my brother to the dragon.”  
- Rating: Medium — world-reactive when tied to hold events, but still personal-scale ledger.  
- Feasibility: Fully doable in headless Python + SKSE write-back of disposition; no geometry change. Papyrus only for one-shot dialogue hooks.  
- Overlap: (b) natural extension of existing belief/grudge engine (opinion = aggregated belief weight).

**Opinion modifier fields (scripting primitives).**  
- Concepts: Expose named modifiers (days, decay, revoke_reason) as Chronicle belief tags; e.g., “unjust arrest by Imperial” lasts 30 in-game days then decays. Player experiences timed hostility that can expire if player stays away.  
- Rating: Medium.  
- Feasibility: Python timers + SKSE disposition refresh; avoid Papyrus loops.  
- Overlap: (b).

**CK2 flat-then-drop vs CK3 gradual decay.**  
- Concepts: Implement gradual linear decay for temporary opinions (CK3 style) so hostility fades visibly over weeks.  
- Rating: Low — pure implementation detail, not headline.  
- Feasibility: Trivial in Python.  
- Overlap: (b).

**Succession opinion inheritance.**  
- Concepts: When a Jarl is replaced by civil-war conquest, heirs/retainers inherit 25–50 % of prior opinion (grudges heavier). Player sees new Jarl still hostile because “your side killed my father.”  
- Rating: High — civil-war reactivity, world in motion.  
- Feasibility: Python tracks Jarl succession events already visible via civil-war quest stages; SKSE updates new NPC disposition.  
- Overlap: (b).

**Typed opinion categories (CK3).**  
- Concepts: Split opinion into General / Attraction / Same-faction / Tyranny buckets; Attraction gated by orientation-compatible NPCs.  
- Rating: Low — adds bookkeeping without visible world motion.  
- Feasibility: Easy data model; UI surfacing limited by no custom menus without new research.  
- Overlap: (b).

**Vassal Stance categories (CK3).**  
- Concepts: Tag major NPCs (Thanes, housecarls) with stances (Courtly, Zealot, Belligerent); civil-war actions or dragon attacks apply stance-specific modifiers. Player sees Zealot NPCs celebrate Stormcloak victories more.  
- Rating: High — makes faction politics feel alive.  
- Feasibility: Python stance table + event triggers from civil-war stage changes.  
- Overlap: (c) new subsystem.

**Diplomacy-skill-scaled opinion.**  
- Concepts: Player Speech skill scales temporary opinion gains from persuasion.  
- Rating: Low — already partially covered by vanilla Speech.  
- Feasibility: SKSE can read Speech; trivial.  
- Overlap: (a).

**Prestige/piety-derived opinion.**  
- Concepts: Track player “renown” (dragon kills, civil-war rank) as a global modifier to NPC opinion, capped.  
- Rating: Medium — but global reputation is explicitly disallowed by design doctrine.  
- Feasibility: Blocked by design rule.  
- Overlap: (c) but forbidden.

**Tyranny as pooled vs itemized.**  
- Concepts: Pool “tyranny” from player imprisonments/executions (via mods or console) into a single decaying meter that affects all hold NPCs.  
- Rating: Medium.  
- Feasibility: Requires detecting imprisonment events (SKSE possible); Papyrus last resort.  
- Overlap: (b).

**Named gift/grant modifiers.**  
- Concepts: Giving gold/items creates timed opinion with stacking duration, not value.  
- Rating: Low — gift already exists; just better tracking.  
- Feasibility: Easy.  
- Overlap: (a).

**Explorable opinion UI.**  
- Concepts: Add a simple MCM or note-based “Explore Character Opinions” that lists top modifiers for any NPC.  
- Rating: Medium — legibility win.  
- Feasibility: MCM via SKSE; no new assets.  
- Overlap: (b).

### 1.2 Named relationships

**Discrete relationship flags.**  
- Concepts: Crystallize extreme opinion into Friend / Rival / Lover flags that unlock unique dialogue packages and AI package overrides (Friend follows more readily, Rival ambushes).  
- Rating: High — visible behavior change.  
- Feasibility: SKSE can swap AI packages; Python stores flags. Patent note: avoid automatic rank-rewriting.  
- Overlap: (b).

**Explicit opinion values + secondary effects.**  
- Concepts: Friend grants +fertility-style (marriage chance) or stress-on-death (mood drop when Friend dies).  
- Rating: Medium.  
- Feasibility: Death detection via SKSE OnDeath; mood write-back limited.  
- Overlap: (b).

**Formation always records a reason (“memory”).**  
- Concepts: Every Friend/Rival formation stores a one-sentence memory string used in later dialogue.  
- Rating: High — provenance already core; this surfaces it.  
- Feasibility: Perfect fit for existing engine.  
- Overlap: (a).

**Relations gate/protect AI behavior.**  
- Concepts: Friends refuse to join anti-player factions; Rivals preferentially start murder schemes (radiant).  
- Rating: High.  
- Feasibility: Python gates faction-join checks; SKSE can force dialogue rejection.  
- Overlap: (b).

**Inheritance of named relations on death.**  
- Concepts: Best Friend/Nemesis transfers to heir with opinion nudge.  
- Rating: Medium — succession already covered above.  
- Feasibility: Same as succession.  
- Overlap: (b).

**House-level relationship crystallization.**  
- Concepts: Track Feuding/Neutral/Faithful between major houses (Gray-Mane/Battle-Born, etc.); repeated murders shift the house relation, unlocking “Eradicate Rival House” radiant quests or alliance options.  
- Rating: High — world-scale.  
- Feasibility: Python house graph; civil-war already swaps Jarls.  
- Overlap: (c).

### 1.3 Secrets, hooks, leverage

**Secrets (typed, discoverable).**  
- Concepts: NPCs acquire Secrets (Adultery, Murder, Thalmor collaboration) via witnessed events; Spymaster-style “Find Secrets” task for player or follower.  
- Rating: High.  
- Feasibility: Extends existing belief/provenance; discovery via line-of-sight or dialogue.  
- Overlap: (a) already covered, needs surfacing.

**Expose vs Blackmail choice.**  
- Concepts: Player chooses Expose (public trait + imprisonment justification) or Blackmail (creates Hook).  
- Rating: High.  
- Feasibility: Dialogue branches + Python Hook object.  
- Overlap: (b).

**Hooks as spendable leverage.**  
- Concepts: One Hook per NPC; Weak single-use acceptance bonus, Strong forces acceptance on marriage/join-faction and blocks hostile schemes.  
- Rating: High.  
- Feasibility: Python currency; SKSE forces dialogue acceptance flags.  
- Overlap: (c).

**Explicit spend-value table.**  
- Concepts: Hard-coded acceptance bonuses per interaction type (Arrange Marriage +100, Force Vote, etc.).  
- Rating: Medium — implementation detail.  
- Feasibility: Table in Python.  
- Overlap: (b).

**Forgiving-trait hook abandonment.**  
- Concepts: Forgiving NPCs can drop a Hook for stress relief + opinion bonus.  
- Rating: Low.  
- Feasibility: Easy.  
- Overlap: (b).

### 1.4 Stress / internal-friction engine

**Psychological buffer gating out-of-character action.**  
- Concepts: NPCs gain Stress when forced to act against personality (Just NPC ordered to execute prisoner); high Stress triggers Mental Break.  
- Rating: High — independent world motion.  
- Feasibility: Python stress meter per NPC; triggers on civil-war orders or dragon-attack decisions.  
- Overlap: (c).

**Threshold breakdown events.**  
- Concepts: At 100/200/300 Stress fire named breaks (murder courtier, abdicate, trait change).  
- Rating: High.  
- Feasibility: Event system already planned; SKSE can force AI package or kill.  
- Overlap: (c).

**Coping mechanisms.**  
- Concepts: Breaks can add permanent coping traits (Drunkard) that alter schedules.  
- Rating: Medium.  
- Feasibility: Trait flags + AI package swap.  
- Overlap: (c).

**Trait→stress-source table.**  
- Concepts: Publish itemized table so player can predict (Ambitious gains stress from White Peace).  
- Rating: Medium — legibility.  
- Feasibility: Data only.  
- Overlap: (b).

### 1.5 Memories

**Structured, tagged memory objects.**  
- Concepts: Already core; ensure every memory has timestamp, type tag, participants, visibility.  
- Rating: High (already planned).  
- Feasibility: Core.  
- Overlap: (a).

**Retention-by-rank.**  
- Concepts: Only high-tier NPCs (Jarls, guild leaders) keep permanent memories; others fade.  
- Rating: Medium — performance win.  
- Feasibility: Python GC.  
- Overlap: (b).

**Memories queried by other systems.**  
- Concepts: Dialogue and schemes pull exact memory ID for narrative text.  
- Rating: High.  
- Feasibility: Core design.  
- Overlap: (a).

**Memory Viewer UI.**  
- Concepts: Dedicated notebook or MCM page listing an NPC’s memories.  
- Rating: High — legibility.  
- Feasibility: MCM or book object.  
- Overlap: (b).

### 1.6 Faction / collective political pressure

**Faction power as ratio, gating discontent.**  
- Concepts: Track military power of Stormcloak vs Imperial per hold; when ratio >80 % discontent accrues; at 100 % ultimatum (radiant rebellion).  
- Rating: High — civil-war reactivity.  
- Feasibility: Python reads civil-war stage + garrison sizes via SKSE.  
- Overlap: (c).

**Hard eligibility gates.**  
- Concepts: Imprisoned, underage, hooked, or high-opinion NPCs cannot join factions.  
- Rating: Medium.  
- Feasibility: Python gates.  
- Overlap: (b).

**Per-trait join/leave multipliers.**  
- Concepts: Ambitious 4× join chance, Content 0.01×.  
- Rating: Medium.  
- Feasibility: Data table.  
- Overlap: (b).

**Strong Hook forces faction membership.**  
- Concepts: Spend Strong Hook to force an NPC into a side for 10 years.  
- Rating: High.  
- Feasibility: Combined with Hooks above.  
- Overlap: (b).

**Powerful-vassal council-seat mechanics.**  
- Concepts: Top N Thanes demand council seats; denial −40 opinion.  
- Rating: Medium — limited council seats in Skyrim.  
- Feasibility: Dialogue only.  
- Overlap: (c).

### 1.7 Council mechanics

**Five discrete voting-stance archetypes.**  
- Concepts: Loyalist / Pragmatist / Glory Hound / Zealot / Malcontent scoring for Jarl decisions.  
- Rating: Medium.  
- Feasibility: Python scoring on civil-war votes.  
- Overlap: (c).

**Concrete vote thresholds.**  
- Concepts: Opinion-keyed support for revocation/imprisonment.  
- Rating: Low.  
- Feasibility: Easy.  
- Overlap: (b).

**Council obstruction firing penalties.**  
- Concepts: Firing a councilor applies timed opinion hit.  
- Rating: Low.  
- Feasibility: Easy.  
- Overlap: (b).

### 1.8 Schemes / plots

**CK2 plot power ratio.**  
- Concepts: Murder/abduct schemes scored by agent military contribution.  
- Rating: Medium.  
- Feasibility: Python scheme objects.  
- Overlap: (c).

**CK3 Personal vs Hostile schemes.**  
- Concepts: Personal (Sway/Befriend/Seduce) vs Hostile (Murder) with Potential/Secrecy/Advantage/Agent metrics.  
- Rating: High.  
- Feasibility: Full scheme subsystem; SKSE for execution events.  
- Overlap: (c).

**Agent recruitment scored.**  
- Concepts: Recruit agents who dislike target; Envious courtier exploit.  
- Rating: High.  
- Feasibility: Opinion query.  
- Overlap: (b).

**Discovery consequences stacking.**  
- Concepts: Discovered murder creates Rivals among relatives.  
- Rating: High.  
- Feasibility: Core.  
- Overlap: (a).

**Scheme-specific success tables.**  
- Concepts: Sway 95 % +25 opinion, etc.  
- Rating: Medium.  
- Feasibility: Tables.  
- Overlap: (b).

### 1.9 AI decision-making

**ai_chance / ai_will_do scoring.**  
- Concepts: Base weight + modifiers + vetoes for every major NPC decision.  
- Rating: Medium — infrastructure.  
- Feasibility: Python decision engine.  
- Overlap: (c).

**Twelve-to-thirteen hidden personality parameters.**  
- Concepts: ai_boldness, ai_vengefulness etc. drive behavior variance.  
- Rating: High — expected randomness.  
- Feasibility: Data model.  
- Overlap: (c).

**Two-layer visible/hidden state.**  
- Concepts: Visible traits + hidden personality values.  
- Rating: High.  
- Feasibility: Core.  
- Overlap: (b).

**AI archetype bucketing.**  
- Concepts: “Warlike” NPCs bank gold for war.  
- Rating: Medium.  
- Feasibility: Easy.  
- Overlap: (b).

### 1.10 Dread / intimidation

**Dread vs Boldness threshold.**  
- Concepts: High player Dread (from public executions/dragon kills) intimidates low-Boldness NPCs, forcing acceptance even at negative opinion.  
- Rating: High — visible power fantasy.  
- Feasibility: Python Dread meter; SKSE disposition override. Design note: not global reputation.  
- Overlap: (c).

### 1.11 Event-engine architecture

**MTTH vs on_action.**  
- Concepts: Prefer on_action hooks (state-change) over continuous MTTH polling for performance.  
- Rating: Medium — architecture.  
- Feasibility: Python event bus.  
- Overlap: (b).

**“Opinion-modifier soup” failure mode.**  
- Concepts: Avoid uncapped additive stacking; use stance vectors + memory flags.  
- Rating: High (lesson).  
- Feasibility: Design rule.  
- Overlap: (a).

**Sculptural Fiction vs Generative Social Simulation.**  
- Concepts: Hybrid — continuous state + storylet layer at thresholds.  
- Rating: High (design doctrine).  
- Feasibility: Core.  
- Overlap: (a).

**Emergence-detection thesis.**  
- Concepts: Persist readable records so player can infer narrative chains.  
- Rating: High.  
- Feasibility: Core.  
- Overlap: (a).

### 1.12 Genre neighbors

**King of Dragon Pass / Six Ages.**  
- Concepts: Clan-level (hold-level) social state; advisor-team predictions; value-trade-off choices with no optimal answer.  
- Rating: High — world motion.  
- Feasibility: Hold-level meters; dialogue advisors.  
- Overlap: (c).

**Wildermyth.**  
- Concepts: Relationship bindings + contextual-casting storylets that search party for matching history; discard unread simulation depth.  
- Rating: High.  
- Feasibility: Storylet matcher in Python.  
- Overlap: (c).

**Total War (Three Kingdoms).**  
- Concepts: Loyalty meter + hard-threshold defection with region. Failure mode: invisible inter-vassal relations.  
- Rating: Medium — loyalty already partial.  
- Feasibility: Visible meters required.  
- Overlap: (b).

**Mount & Blade II.**  
- Concepts: Scalar relationship with no threshold→action catalog = no social fantasy.  
- Rating: Low (negative lesson).  
- Feasibility: N/A.  
- Overlap: (a) warning.

**Twilight Bazaar thesis.**  
- Concepts: Discrete presentable knowledge objects (“bargaining chips”); verb framing (“Gossip” vs “Socialise”) changes interpretation.  
- Rating: High.  
- Feasibility: Inventory-style rumor objects.  
- Overlap: (a) strengthens existing.

---

**2. Kenshi**

### 2.1 World states / town overrides

**Boolean world-state flags → town overrides.**  
- Concepts: Killing/imprisoning a Jarl or faction leader flips hold “Destroyed / Prosperous / Civil-War” state; on player leave, town record swaps (new guards, vendors, building states).  
- Rating: High — classic world reactivity.  
- Feasibility: SKSE can disable/enable NPC refs and change cell ownership on unload; no geometry edit. Research needed for safe cell swap.  
- Overlap: (c).

**Single-leader vs multi-leader collapse.**  
- Concepts: Small factions collapse on one kill; large (Imperial/Stormcloak) need multiple.  
- Rating: High.  
- Feasibility: Python leader tracking.  
- Overlap: (c).

**Kill/imprison equivalence + release-rollback.**  
- Concepts: Imprisoning a leader satisfies “dead” for overrides; releasing rolls back.  
- Rating: High — rescue narratives.  
- Feasibility: Detect prison state via SKSE.  
- Overlap: (b).

**Fixed override vocabulary.**  
- Concepts: Malnourished, Half-destroyed, Civil War, Destroyed, Prosperous, Faction-takeover.  
- Rating: High.  
- Feasibility: Pre-author override packages.  
- Overlap: (c).

**Priority-ranked override chains.**  
- Concepts: Most conditions satisfied wins.  
- Rating: Medium.  
- Feasibility: Python priority.  
- Overlap: (b).

**Swap only while unloaded.**  
- Concepts: Silent wait until player leaves.  
- Rating: Medium (implementation).  
- Feasibility: OnCellDetach hook.  
- Overlap: (b).

**Player-owned buildings collateral.**  
- Concepts: Accept or protect player houses in overridden towns.  
- Rating: Low — pain point.  
- Feasibility: Flag player-owned.  
- Overlap: (b).

**Faction HQ relocation.**  
- Concepts: After takeover, faction moves HQ.  
- Rating: Medium.  
- Feasibility: Marker move.  
- Overlap: (c).

**“Broken squad” degradation.**  
- Concepts: Leaderless Holy Nation → weaker “Strayed Paladins” spawns.  
- Rating: High.  
- Feasibility: Spawn-table modifiers.  
- Overlap: (c).

**Power vacuums grow rival footprint.**  
- Concepts: Kill one faction leader → neighboring faction colonizes zone.  
- Rating: High.  
- Feasibility: Homeless spawn retune.  
- Overlap: (c).

**Zone-level spawn-table retuning.**  
- Concepts: Leader death shifts wilderness spawns.  
- Rating: High.  
- Feasibility: SKSE spawn overrides.  
- Overlap: (c).

**Most-modded layer lesson.**  
- Concepts: Prefer fewer, completable branches over micro-leaders.  
- Rating: High (design).  
- Feasibility: N/A.  
- Overlap: (a).

### 2.2 Faction relations scalar

**−100..+100 with two thresholds.**  
- Concepts: −30 hostile-on-sight, +50 allied (guards ignore, gift, assist).  
- Rating: Medium — vanilla has similar.  
- Feasibility: Easy.  
- Overlap: (a).

**Witnessed crime overrides scalar.**  
- Concepts: Line-of-sight crime always attacks regardless of alliance.  
- Rating: High.  
- Feasibility: Core witness system.  
- Overlap: (a).

**Relation-changing action table.**  
- Concepts: Concrete deltas for attack, heal, buy freedom, Pacifier service.  
- Rating: Medium.  
- Feasibility: Tables.  
- Overlap: (b).

**No passive decay.**  
- Concepts: Relations stick until acted upon.  
- Rating: Low.  
- Feasibility: Easy.  
- Overlap: (b).

**Alliance knock-on costs.**  
- Concepts: Joining one faction costs relations with rivals.  
- Rating: High — already partially true.  
- Feasibility: Event on join.  
- Overlap: (a).

### 2.3 Crime, bounty, legal system

**Non-telepathic crime.**  
- Concepts: Strict line-of-sight witness triggers.  
- Rating: High.  
- Feasibility: Core.  
- Overlap: (a).

**Crime-severity table.**  
- Concepts: Trespassing → Terrorism with expiry, jail, bounty.  
- Rating: Medium.  
- Feasibility: Extend vanilla.  
- Overlap: (b).

**Linear bounty-expiry.**  
- Concepts: Statute of limitations scaled to severity.  
- Rating: Medium.  
- Feasibility: Python timers.  
- Overlap: (b).

**Recognition scales with bounty.**  
- Concepts: High bounty recognized faster by more NPCs.  
- Rating: Medium.  
- Feasibility: SKSE detection.  
- Overlap: (b).

**Prison converts to slavery.**  
- Concepts: In certain holds, caged → slave mines.  
- Rating: Medium (lore stretch).  
- Feasibility: Possible with existing slave mods research.  
- Overlap: (c).

**Delegated legal systems.**  
- Concepts: Minor factions share wanted-list with major umbrella.  
- Rating: Medium.  
- Feasibility: Namespace in Python.  
- Overlap: (b).

**Only occupation-typed characters issue bounty.**  
- Concepts: Guards/military only.  
- Rating: Low.  
- Feasibility: Easy.  
- Overlap: (a).

### 2.4 AI packages / squad data model

**Squads + AI Packages + Dialogue Packages.**  
- Concepts: Leader, prioritized action lists, unloaded-func path.  
- Rating: Medium — infrastructure.  
- Feasibility: SKSE AI package swap.  
- Overlap: (b).

**AI contracts.**  
- Concepts: Temporary package override (allied NPC joins player).  
- Rating: High.  
- Feasibility: Follower system extension.  
- Overlap: (b).

**Off-screen simulation suspended.**  
- Concepts: Unloaded chunks freeze; world progress via boolean flags only.  
- Rating: High (performance lesson).  
- Feasibility: Design rule.  
- Overlap: (a).

**Shallow “remembers you” flag.**  
- Concepts: DA_Remember_Character on player faction.  
- Rating: Low — already surpassed.  
- Feasibility: N/A.  
- Overlap: (a).

---

**3. Shadows of Doubt**

**23-field Citizen Profile.**  
- Concepts: Expand NPC data with discoverable fields (blood type, shoe size, schedule) stored in Python; player notebooks fill them.  
- Rating: Medium — investigation flavor.  
- Feasibility: Data only; no new assets.  
- Overlap: (c).

**Static/dynamic/relational citizen data.**  
- Concepts: Unique ID, appearance hash, financials, social graph.  
- Rating: High.  
- Feasibility: Core graph.  
- Overlap: (b).

**Deterministic physical/digital trace.**  
- Concepts: Purchases leave receipt objects + ledger entries; footprints hash-linked.  
- Rating: High — but geometry limits.  
- Feasibility: Spawn misc items; research needed for persistent footprints.  
- Overlap: (c).

**Periodic global visibility-check sighting loop.**  
- Concepts: Pairwise LOS checks append sighting records.  
- Rating: High.  
- Feasibility: SKSE LOS queries; throttle heavily.  
- Overlap: (a).

**Three-phase memory decay.**  
- Concepts: Precise → Fuzzy → Purged; time accuracy first.  
- Rating: High.  
- Feasibility: Core belief decay.  
- Overlap: (a).

**“Facts” provenance graph.**  
- Concepts: Corkboard-style links with reliability weights.  
- Rating: High — perfect for existing.  
- Feasibility: Python graph; UI via notes or MCM.  
- Overlap: (a).

**Fingerprint/name resolution chain.**  
- Concepts: Player builds own print database via notebook.  
- Rating: Medium.  
- Feasibility: Data.  
- Overlap: (c).

**Per-citizen alibi timelines.**  
- Concepts: Overlay walked routes to find contradictions.  
- Rating: High for investigation mods.  
- Feasibility: Schedule logging; map UI limited.  
- Overlap: (c).

**Citizens can lie.**  
- Concepts: Innocent NPCs bend truth if presence looks bad.  
- Rating: High.  
- Feasibility: Dialogue condition on stress/incrimination.  
- Overlap: (b).

**Press-appeal mechanic.**  
- Concepts: Publicize case → witnesses come forward (cost).  
- Rating: Medium.  
- Feasibility: Event.  
- Overlap: (c).

**Batch-precompute-then-deviate scheduling.**  
- Concepts: Precompute daily routines; only deviate in real time.  
- Rating: High (performance).  
- Feasibility: Python batch on day start.  
- Overlap: (b).

**Body-discovery failsafes.**  
- Concepts: Layered guarantees so bodies are always found.  
- Rating: Medium.  
- Feasibility: Event chain.  
- Overlap: (b).

**Case Generator as provenance-anchored intervention.**  
- Concepts: Killer selected by archetype then executes real crime against simulated relationships; no disconnected clues.  
- Rating: High — director pattern.  
- Feasibility: Storylet + real graph.  
- Overlap: (c).

---

**4. The Nemesis System**

**Procedurally generated enemies from template.**  
- Concepts: Randomized appearance/personality for bandit captains; persistent after encounters.  
- Rating: High — but patent boundary.  
- Feasibility: Avoid hierarchy rank-rewriting; single-NPC memory OK. Research patent carefully.  
- Overlap: (c) restricted.

**Discrete combat-outcome “verbs”.**  
- Concepts: Player death → orc gains power/taunt; flight → confidence; injury → scar + dialogue.  
- Rating: High.  
- Feasibility: OnDeath/OnHit SKSE; scar via texture swap research.  
- Overlap: (c).

**Combinatorial dialogue selection.**  
- Concepts: Fragments filtered by archetype/rank/outcome/condition.  
- Rating: High.  
- Feasibility: Dialogue system extension.  
- Overlap: (b).

**Ranked hierarchy with vacancy-filling.**  
- Concepts: Automatic promotion on death.  
- Rating: Low — patent + design doctrine forbid automatic rank-rewriting.  
- Feasibility: Blocked.  
- Overlap: (c) forbidden.

**Autonomous background hierarchy events.**  
- Concepts: Duels, hunts, feasts independent of player.  
- Rating: High — world motion.  
- Feasibility: Off-screen Python events that surface as rumors.  
- Overlap: (c).

**Domination, followers, betrayal.**  
- Concepts: Dominate → follower; Blood-Brother loss → revenge ambush.  
- Rating: Medium — domination stretch for Skyrim.  
- Feasibility: Follower system; ambush events.  
- Overlap: (c).

**Tuned probability curves.**  
- Concepts: Survival chance inverse to active rivalries; ambush throttle.  
- Rating: Medium.  
- Feasibility: Easy.  
- Overlap: (b).

**Only named captains carry persistent memory.**  
- Concepts: Masses are stateless.  
- Rating: High (performance lesson).  
- Feasibility: Design rule already in force.  
- Overlap: (a).

**Feature-creep near-failure.**  
- Concepts: Cut back from multi-bar morale to personal villains.  
- Rating: High (lesson).  
- Feasibility: N/A.  
- Overlap: (a).

**Patent boundary.**  
- Concepts: Protected is avatar↔NPC1 changing NPC2 in hierarchy + dialogue/appearance. Free: single NPC memory, per-observer grudges, standalone succession.  
- Rating: Critical constraint.  
- Feasibility: Stay inside free zone.  
- Overlap: (a).

---

**5. RimWorld**

### 5.1 Mood / mental-break

**Mood-bar with Mental Break Threshold.**  
- Concepts: Per-NPC mood scalar; bands Minor/Major/Extreme with MTB.  
- Rating: High.  
- Feasibility: Python; surface as dialogue/AI change.  
- Overlap: (c).

**Weighted-random-within-band selection.**  
- Concepts: Traits gate and re-weight breaks.  
- Rating: Medium.  
- Feasibility: Easy.  
- Overlap: (b).

**Named break catalogue.**  
- Concepts: Sad wander, Tantrum, Berserk, Fire starting, Murderous rage, etc.  
- Rating: High.  
- Feasibility: Map to AI packages or kill.  
- Overlap: (c).

**Multi-channel telegraphing.**  
- Concepts: Mood bar, alerts, tooltip thoughts, visual icon.  
- Rating: High.  
- Feasibility: Limited UI; use dialogue + notifications.  
- Overlap: (b).

**Fixed recovery windows.**  
- Concepts: Arrest, downing, or time ends break.  
- Rating: Medium.  
- Feasibility: Easy.  
- Overlap: (b).

**Catharsis thought.**  
- Concepts: Large temporary mood bonus after break to prevent spiral.  
- Rating: High.  
- Feasibility: Easy.  
- Overlap: (b).

**“Story generator” design pillar.**  
- Concepts: Mechanics must include loss and recovery.  
- Rating: High (doctrine).  
- Feasibility: N/A.  
- Overlap: (a).

### 5.2 Opinion / social-thought

**Opinion computed on demand.**  
- Concepts: Live sum of thoughts; never stored scalar.  
- Rating: Medium.  
- Feasibility: Matches existing.  
- Overlap: (a).

**Thought_Memory objects with duration/stack.**  
- Concepts: Age, durationDays, stackLimit, renew on reapply.  
- Rating: High.  
- Feasibility: Core.  
- Overlap: (a).

**Published numeric social-thought table.**  
- Concepts: Insulted −15/20d, Rescued +15/30d, etc.  
- Rating: Medium.  
- Feasibility: Tables.  
- Overlap: (b).

**Social fights from insults.**  
- Concepts: Probabilistic escalation to fight → catharsis or anger.  
- Rating: High.  
- Feasibility: SKSE combat start.  
- Overlap: (c).

### 5.3 Storyteller / director

**Incidents on MTB.**  
- Concepts: Different “Storyteller” personas (Classic/Randy) control threat spacing.  
- Rating: High.  
- Feasibility: Python director.  
- Overlap: (c).

**Raid-point formula.**  
- Concepts: Wealth + population → intensity; thresholds gate raid types.  
- Rating: Medium — wealth-gaming risk.  
- Feasibility: Detect player wealth carefully.  
- Overlap: (c).

**Wealth-gaming failure mode.**  
- Concepts: Any trusted input will be gamed; prefer un-launderable or fully visible.  
- Rating: High (lesson).  
- Feasibility: Design.  
- Overlap: (a).

### 5.4 Off-screen entity persistence

**Object-identity preservation.**  
- Concepts: WorldPawns keep same object; needs/relationships persist.  
- Rating: High.  
- Feasibility: Python already does this.  
- Overlap: (a).

**Mothball tier.**  
- Concepts: Lazy daily tick for inactive.  
- Rating: High (perf).  
- Feasibility: Easy.  
- Overlap: (b).

**Abstract per-day need accounting.**  
- Concepts: Fixed daily rates for caravans.  
- Rating: Medium.  
- Feasibility: Easy.  
- Overlap: (b).

**Reachability-graph GC.**  
- Concepts: Mark critical pawns; discard rest. Failure modes: over-keep / under-pin.  
- Rating: High.  
- Feasibility: Implement carefully.  
- Overlap: (b).

**Alibi generation pattern.**  
- Concepts: Generate backstory only when interacted with.  
- Rating: High.  
- Feasibility: Core.  
- Overlap: (a).

---

**6. Dwarf Fortress**

### 6.1 Stress / emotion → behavior

**Two hidden stress axes.**  
- Concepts: Short-term + long-term; both elevated for breakdown.  
- Rating: High.  
- Feasibility: Python dual meters.  
- Overlap: (c) (extends RimWorld mood).

**Personality facets modulate mapping.**  
- Concepts: Bravery, stress vulnerability, anxiety.  
- Rating: Medium.  
- Feasibility: Data.  
- Overlap: (b).

**Branching temporary + permanent insanity.**  
- Concepts: Tantrum → Melancholy / Berserk / Catatonic.  
- Rating: High.  
- Feasibility: AI package + death.  
- Overlap: (c).

**Strange moods.**  
- Concepts: Positive takeover: claim workshop, hunt materials, artifact or insanity.  
- Rating: High — Skyrim craftable artifacts.  
- Feasibility: Force AI to furniture; spawn unique item.  
- Overlap: (c).

**True state-machine takeover.**  
- Concepts: mood_type enum suppresses normal jobs.  
- Rating: Medium.  
- Feasibility: AI package priority.  
- Overlap: (b).

**Pause-and-announce legibility.**  
- Concepts: Center camera + colored announcement.  
- Rating: High.  
- Feasibility: SKSE camera + message.  
- Overlap: (b).

**Slow decay-to-baseline recovery.**  
- Concepts: Quality bedrooms, temples, socializing; “Therapy Squad”.  
- Rating: High.  
- Feasibility: Need tracking.  
- Overlap: (c).

**Historical failure cascade dampened.**  
- Concepts: Dual-axis + years-long to prevent tantrum spirals.  
- Rating: High (lesson).  
- Feasibility: Design.  
- Overlap: (a).

### 6.2 Memory

**Three-tier fixed-slot buffer.**  
- Concepts: 8 short / 8 long / core; strongest-wins contention.  
- Rating: High.  
- Feasibility: Core improvement.  
- Overlap: (b).

**Grouped strongest-wins slot contention.**  
- Concepts: Same-group replace only if stronger; else overwrite weakest.  
- Rating: Medium.  
- Feasibility: Easy.  
- Overlap: (b).

**Time-gated promotion between tiers.**  
- Concepts: Year → long-term; revisit → 1-in-3 core + personality change.  
- Rating: High.  
- Feasibility: Timers.  
- Overlap: (b).

**World-vs-personal data split.**  
- Concepts: Global historical_event log; personal lossy buffer.  
- Rating: High.  
- Feasibility: Core.  
- Overlap: (a).

### 6.3 Physical evidence / provenance

**Engravings/slabs from real historical links.**  
- Concepts: Player or NPC creates memorial that names real figures/events.  
- Rating: High.  
- Feasibility: Spawn static objects with generated text.  
- Overlap: (c).

**Memorial slabs resolve ghosts.**  
- Concepts: Engrave for dead → lay ghost; deconstruct re-raises.  
- Rating: Medium (lore stretch).  
- Feasibility: Possible with existing ghost systems.  
- Overlap: (c).

**Artifact descriptions from creator preferences + events.**  
- Concepts: Unique items carry generated history; can be stolen/warred over.  
- Rating: High.  
- Feasibility: Item data + Python history.  
- Overlap: (c).

### 6.4 Rumor system

**Six discrete confidence tiers.**  
- Concepts: Direct witness → “heard recently” → legend.  
- Rating: High.  
- Feasibility: Core.  
- Overlap: (a).

**Time-stamped decay at nested scopes.**  
- Concepts: Individual / site / culture / civilization.  
- Rating: High.  
- Feasibility: Nested timers.  
- Overlap: (b).

**Hard rule: content never distorted.**  
- Concepts: Only sanctioned falsehood is secret-identity misattribution; otherwise true but less detailed.  
- Rating: High (design).  
- Feasibility: Core rule already close.  
- Overlap: (a).

---

**7. AI directors / drama management**

### 7.1 Shipped architectures

**Façade Beat Manager.**  
- Concepts: Select next beat from library on discourse + tension score. Failure: shallow self-awareness, single-room scale.  
- Rating: Medium (lessons).  
- Feasibility: Storylet selection.  
- Overlap: (c).

**Left 4 Dead Director.**  
- Concepts: Four-state FSM (Build-Up → Peak → Relax) driven by player stress; multimodal telegraph before spike.  
- Rating: High.  
- Feasibility: Python pacing FSM; audio/dialogue stingers.  
- Overlap: (c).

**King of Dragon Pass storylet engine.**  
- Concepts: Constraint-satisfaction match over state; advisor commentary.  
- Rating: High.  
- Feasibility: Already noted.  
- Overlap: (c).

**PaSSAGE.**  
- Concepts: Playstyle vector; next encounter by dot-product. Failure: annotation overhead, drift, pacing flattening.  
- Rating: Medium.  
- Feasibility: Track player vector carefully.  
- Overlap: (c).

**DeepMind Concordia.**  
- Concepts: LLM proposes intent; deterministic validator mutates state; only validated Event Statement narrated.  
- Rating: High — architecture for any LLM layer.  
- Feasibility: Future-proof.  
- Overlap: (c).

**RimWorld Storyteller.**  
- Concepts: Already covered.  
- Rating: High.  
- Feasibility: As above.  
- Overlap: (c).

### 7.2 Formal/academic lineages

**Symbolic narrative planning (IPOCL).**  
- Concepts: Character actions motivated by own goals. Failure: state explosion.  
- Rating: Low (commercial loser).  
- Feasibility: Avoid full planning.  
- Overlap: (c).

**DODM.**  
- Concepts: Intervention actions must be strong enough; weak actions fail regardless of algorithm.  
- Rating: High (lesson).  
- Feasibility: Design.  
- Overlap: (a).

**Targeted Trajectory Distribution MDPs.**  
- Concepts: Steer toward distribution of experiences, not single best story.  
- Rating: High.  
- Feasibility: Director goal.  
- Overlap: (c).

**Plan-based mediation (Mimesis).**  
- Concepts: Intervene or accommodate; reframe past only if unobserved.  
- Rating: High.  
- Feasibility: Event mediation layer.  
- Overlap: (c).

**Daggerfall quest format.**  
- Concepts: Templates gated by reputation economy; QuestMachine ticks.  
- Rating: High — radiant already exists.  
- Feasibility: Extend radiant with reputation.  
- Overlap: (b).

**Storylet academic thread.**  
- Concepts: Generate quests from world state at generation time; space grows with state.  
- Rating: High.  
- Feasibility: Core.  
- Overlap: (c).

**Storylet role-casting.**  
- Concepts: Highest-value pattern: precondition-gated role slots filled by real entities.  
- Rating: High.  
- Feasibility: Core.  
- Overlap: (c).

### 7.3 LLM-narrator record

**AI Dungeon / Hidden Door.**  
- Concepts: Memory drift, ungroundedness, latency.  
- Rating: Critical constraint.  
- Feasibility: Avoid pure LLM state.  
- Overlap: (a).

**NCP-Bench.**  
- Concepts: Long-horizon constraint satisfaction fails hard without explicit state.  
- Rating: Critical.  
- Feasibility: Keep symbolic core.  
- Overlap: (a).

**Orchestrated Reality / WorldLines.**  
- Concepts: Parameterized-Action POMDP; Plan→Diff→Validate→Apply.  
- Rating: High.  
- Feasibility: Architecture.  
- Overlap: (c).

**Neuro-symbolic TSL automata.**  
- Concepts: Automaton decides prompt modifiers; 96 %+ adherence.  
- Rating: High.  
- Feasibility: Future.  
- Overlap: (c).

**Slice of Life.**  
- Concepts: Deterministic social sim + LLM surface text only; no dialogue→state feedback.  
- Rating: High.  
- Feasibility: Design rule.  
- Overlap: (a).

**Function-calling validity gate.**  
- Concepts: Structured calls into constraint backend never invalid.  
- Rating: High.  
- Feasibility: Future.  
- Overlap: (c).

**Drama Llama.**  
- Concepts: 3–4 pivot points; LLM improvises within bounds.  
- Rating: Medium.  
- Feasibility: Future.  
- Overlap: (c).

**Symbolically Scaffolded Play.**  
- Concepts: Role-differentiated scaffolding; shared JSON memory.  
- Rating: High.  
- Feasibility: Design.  
- Overlap: (b).

**Friends & Fables Franz→ACE-1.**  
- Concepts: Separate “face” from “truth”; atomic memory units; View Context feature.  
- Rating: High — closest commercial analog.  
- Feasibility: Exactly matches Chronicle goal.  
- Overlap: (a).

### 7.4 Failure-mode taxonomy

**(1–10) Visible railroading, ungrounded generation, agency-destroying optimization, memory inconsistency, deceptive provenance, static-world exposure, unsolvable content, promised policy not implemented, simulation illegibility, perceived-vs-statistical fairness.**  
- Concepts: Treat as checklist for every new feature.  
- Rating: Critical.  
- Feasibility: Design doctrine.  
- Overlap: (a).

---

**5. Ranked top 10** (across entire catalog)

1. **House-level / hold-level relationship crystallization + power-vacuum overrides** (CK + Kenshi) — turns civil-war and dragon attacks into visible, lasting world reconfiguration.  
2. **Storylet role-casting with real entities** (Wildermyth / academic) — every generated situation feels authored because the actual grudge-holder is cast.  
3. **Hooks as spendable leverage currency** (CK) — gives player concrete verbs that change the political board.  
4. **Dual-axis stress + named mental breaks with catharsis** (RimWorld + DF) — independent NPC psychological lives that react to world events.  
5. **Boolean world-state town/hold overrides on leader death/imprisonment** (Kenshi) — the classic “I killed the Jarl and the town changed” fantasy.  
6. **Left-4-Dead-style pacing FSM with multimodal telegraph** — keeps threat and social drama from feeling random.  
7. **Provenance-anchored Case Generator** (Shadows of Doubt) — crimes and schemes always leave real, inspectable traces.  
8. **Dread vs Boldness threshold** (CK) — intimidation that overrides opinion without becoming global reputation.  
9. **Atomic memory units + View Context** (Friends & Fables) — the exact architecture Chronicle already aims for; surface it hard.  
10. **Strange moods / artifact generation from real history** (DF) — unique, story-bearing items that can be stolen and warred over.

**6. Explicit discard list** (Low items not worth reconsidering)

- Prestige/piety-derived global opinion (design doctrine forbids global reputation).  
- Automatic hierarchy vacancy-filling / rank-rewriting (Nemesis patent + doctrine).  
- Pure MTTH continuous polling (performance death on Papyrus/SKSE budget).  
- Uncapped opinion-modifier soup (CK2 failure mode already diagnosed).  
- Full symbolic narrative planning (IPOCL) — state explosion, commercial loser.  
- Shallow DA_Remember_Character flag (already surpassed by provenance).  
- Mount & Blade-style scalar with no threshold→action catalog (proves the negative).  
- Wealth-point director inputs that can be laundered (RimWorld exploit).  
- Any pure-LLM state mutation without validator (all 2026 benchmarks).  
- Micro-leader over-branching (Kenshi Reactive World fragility lesson).

**7. Catalog gaps**

- **Skyrim-native radiant quest reputation economy** (Daggerfall-style templates already exist but are under-documented here).  
- **Follower affinity / disposition tiers** beyond simple disposition (vanilla has limited; mods like Amazing Follower Tweaks add more — worth explicit research).  
- **Thalmor / Civil-War “occupation” mechanics** that already swap Jarls and banished NPCs — the catalog treats succession abstractly but Skyrim has concrete, reversible hold-control state that should be first-class.  
- **Dragon-attack aftermath** (destroyed buildings, refugee NPCs, temporary famine) — Kenshi-style overrides could hook directly into existing dragon scripts.  
- **No coverage of The Sims** (explicitly noted as missing; still relevant for daily-need and relationship crystallization patterns).