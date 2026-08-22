> Filed 2026-08-22 in `docs/research/comparative-systems/` — external
> research (Compass), not code-verified. A second independent pass over the
> same three games as `spatial-sim-shadows-of-doubt-nemesis-kenshi.md`
> (Shadows of Doubt, Nemesis System, Kenshi), with two distinguishing
> contributions: **(1) it corrects a factual error in that earlier
> file** — the Nemesis patent it cites (US 11,806,626) is not a Nemesis
> patent at all (it covers streaming bonus-round audience participation);
> the correct family is **US 10,926,179 B2** (parent) plus continuations
> US 11,660,540 B2 and US 12,201,908 B2, with a precise claim-by-claim
> breakdown of what's actually covered vs. free to use; **(2) it frames
> each game's witness/grudge propagation unit differently** (SoD:
> per-citizen precomputed batch simulation; Kenshi: faction-as-memory-unit,
> not per-NPC; Nemesis: true per-NPC memory, patent-encumbered). Feeds the
> scenario-ladder / reactivity design work, not any accepted ADR.

# Legible NPC Belief, Grudge & Succession Systems in Real-Time Walk-Around Worlds: A Design & Legal Research Document

## TL;DR
- **Shadows of Doubt** proves per-observer knowledge at city scale is shippable by *not* simulating it in real time — citizen routines are precomputed each day in a 10–15 second batch, sightings are logged by a global visibility loop, and memories decay by rules; **Kenshi** proves grudges/reputation scale by treating "the faction" as the memory unit (instant faction-wide knowledge when witnessed) rather than per-NPC; **the Nemesis System** is the only one of the three that truly does per-NPC memory of specific player encounters — and it is patent-encumbered until 2036.
- The load-bearing fakes: SoD fakes the *illusion* of continuous life (citizens are frozen/LOD'd when off-screen, murders are pre-simulated at ~60× when the city loads); Kenshi fakes off-screen towns entirely (they despawn and respawn as swapped "town override" prefabs gated by boolean "world states"); Nemesis fakes the *world* (only the named captains/warchiefs carry persistent memory and rank; the masses are disposable fodder).
- For your Skyrim mod: freely copy SoD's provenance-graph evidence model and decaying-memory rules and Kenshi's witness-propagation + AI-package/world-state architecture (neither is patented); be careful only around the Nemesis patent's *specific combination* — a player↔NPC interaction that changes a **second** NPC's parameters, tied to a rank hierarchy, with memory-driven dialogue and fort/vendetta features.

## Key Findings

1. **Shadows of Doubt's knowledge model is a provenance graph of "facts" linking "evidence" folders, populated by a rules-based (not real-time) simulation.** Cole Jefferies precomputes each citizen's 4–10 daily journeys in a batch before each day; sightings are recorded by a global loop that checks whether traveling citizens can see each other; memories start ~100% accurate and decay based on familiarity, distinctiveness, witness age/alertness. Detective play traverses this via an "incrimination" flow model with weighted, reliability-limited edges.

2. **The Nemesis System is the genuine article for per-NPC memory** — but its mechanical anatomy (procedural orcs with strengths/fears, promotion into vacancies, memory surfacing in dialogue, domination/betrayal) is exactly what Warner Bros. patented. The granted claims are narrower than press coverage implies: the independent claims require a **second** NPC's parameters to change from an avatar↔first-NPC interaction.

3. **Kenshi deliberately does NOT simulate witnesses individually** — "if one can see you do the deed, they all can see." Crime is a reputation delta against a faction, larger in cities than wilds. Off-screen settlements are not simulated at all; they are swapped prefab "overrides" triggered by boolean "world states." One developer (Chris Hunt) sustained this precisely *because* he faked the world aggressively.

4. **Patent status:** The Nemesis family = **US 10,926,179 B2** (parent, expires **Aug 11, 2036**), **US 11,660,540 B2** (expires ~April 11, 2036), and **US 12,201,908 B2**, plus pending app US 2025/0108303 A1. Note: the patent number in the original brief, "US 11,806,626," is **unrelated** — it covers bonus gameplay/audience-participation streaming, not Nemesis. Cite **US 10,926,179 B2** instead.

---

## Details

### (1) Shadows of Doubt (ColePowered Games / Cole Jefferies)

**What an NPC "is."** Every citizen has an assigned address, employer, work hours, associates, daily routine, favourite venues, plus identifying attributes. The player-facing identity is the **Citizen Profile**: per the Shadows of Doubt Wiki, it consists of **23 pieces of identifying information** (name, face, blood type, shoe size, height, address, job, etc.). The single most important field is the **name** — it is required to resolve cases; all other attributes are triangulation aids and can be individually vague. The game generates a full city where every room of every building is enterable, then populates it with hundreds of citizens, "the hay in your needle-in-a-haystack search."

**How knowledge is represented.** Cole Jefferies' DevBlog 10 ("Gameplay Loop") describes the core data model:
- Every "thing" — citizens, addresses, buildings, objects — has its own **case-file window** aggregating discovered information.
- **"Facts"** are separate objects that **link two or more evidence folders together**, represented visually as strings on the corkboard. "They are the building blocks of the detective mechanics."
- The **incrimination system** propagates a value along the fact-graph: incrimination flows from a *source* (e.g., a stab wound) through facts to connected evidence. Each fact/connection has a **reliability** that limits how much incrimination transfers. On the corkboard, the amount transferred is shown by string redness, reliability by string width, and direction by animation.

This is, mechanically, exactly the **provenance graph** the mod wants: nodes = evidence folders, edges = facts with a reliability weight, and a flow algorithm that concentrates "guilt" on a node.

**How NPCs acquire knowledge.** From DevBlog 8 ("Simulating a City"):
- **Witnessing:** A global check loops through traveling citizens and tests mutual visibility ("green lines" = seeing each other; "red" = already familiar). Citizens can also see through lit windows across the street.
- **Memory fidelity:** memories "start off by being pretty much 100% accurate, but over time they become fuzzier." Duration depends on: whether/how well they know the person, the target's visual distinctiveness, whether the target behaved strangely, the witness's general memory (degrades with age), and the witness's alertness level. As memories fade, **time accuracy degrades first**, then the memory is lost entirely and won't surface under questioning. This creates natural investigative time-pressure.
- **Being told / records:** Players can reconstruct facts from documents — employee files (which tie fingerprints to names), the City Hall citizen database, wallets/IDs, call logs, CCTV. After a press appeal, witnesses may proactively come forward (spending resources raises the chance).
- **Lying:** citizens who know their presence looks incriminating "may actually choose to lie or bend the truth" even when innocent; Jefferies flagged lying as underexplored.

**How detective play traverses the provenance graph.**
- **Fingerprints:** Every procedurally generated citizen has unique prints. A fingerprint scanner lifts prints from the weapon, surfaces, and even footprints; prints are tied to a name via employee records, the City Hall database, asking the person, or forcibly printing an unconscious/handcuffed citizen. There is no separate print "database" — the player maintains their own via the notebook.
- **Alibis / timelines:** Questioning produces a per-citizen **timeline** of who they saw and where, plotted on a map as walked routes; two citizens' timelines can be overlaid to find contradictions.
- **Witness interviews:** walk up, introduce, ask about the time window; recall probability is higher for known people or out-of-place strangers.

**Performance at city scale — what's faked vs. simulated.** This is the crux for the mod:
- **Routines are NOT real-time.** DevBlog 8: simulating hundreds of citizens live "would be a hugely intensive task… That's why I've chosen not to handle it in real-time." Instead the game spends **10–15 seconds** before each day computing every citizen's full day of activities. Deviations (e.g., finding a body) are computed live because "there will never be more than a handful of citizens requiring deviations."
- **The murder is pre-simulated.** DevBlog 10: the murder is simulated *as the city loads*, running a day at **~60× speed** until someone is killed, so the player doesn't wait.
- **Off-screen citizens are cheap.** DevBlog 15 ("Moving in the Citizens"): performance cost is scaled dynamically by proximity to what's on-screen, making "95% of the citizens at any one time relatively insignificant."
- **Failsafes over fidelity:** bodies are guaranteed to be found via layered fallbacks — signs of forced entry, "suspicious" sounds (a scream), and finally the body beginning to smell so neighbours investigate.

**Legibility successes/failures (reviews & postmortems).** Reviewers praise the world's density and the genuine feel of the investigative process (PCGamesN contrasts it favourably with Skyrim's shallow loops). But the recurring failure is **legibility of the win-condition**: GameCritics notes cases "just fizzled out" without leads and that connecting evidence through the corkboard UI is fiddly; players report that flimsy circumstantial links (a single fingerprint on a nearby object) can "solve" a case, so motive and method feel absent. Known bugs (NPCs freezing after giving jobs; save-bloat performance decay) are widely reported. Performance is the biggest technical complaint — the voxel + raycast-lighting renderer, not the citizen sim per se, is the main FPS cost, but high population counts do add CPU load. The full 1.0 release shipped on **September 26, 2024** (PC, PS5, Xbox Series X|S), so mid-EA dev-blog specifics (2018) should be treated as directional.

**Modding/data access.** The game runs Unity IL2CPP; the community uses BepInEx 6. Text/dialogue content uses the **DDS system** (loaded via DDSLoader). Decompiled mods (e.g., Piepieonline's EvidenceObfuscation/EvidenceLinkModifiers) confirm the evidence graph is manipulable: mods can strip fingerprints from employee records or swap addresses for phone numbers in the city directory — i.e., they operate directly on evidence-node fields and the fact links. (Official mod support is limited: a text editor and in-game city editor; deeper access requires the community "Mono" branch + BepInEx.)

### (2) The Nemesis System (Monolith Productions / WB)

**Origin & design intent.** Design director Michael de Plater (per GameSpot/Game Developer) traces it to a cancelled Batman project and to the "scarred villain" archetype: "We wanted to make a villain simulator, and make scarring and memory and that relationship into a personal nemesis." The two design goals in his Shadow of Mordor postmortem: (1) systems that empower players to create/share their own stories, and (2) leverage new-gen hardware through AI innovation. He also framed it through self-determination theory (competence, autonomy, relatedness).

**Mechanical anatomy.**
- **Generation:** every enemy is procedurally generated — name, appearance, personality, strengths, and weaknesses (e.g., fear of fire, immunity to stealth). Traits include tribe/group membership sharing behavioural preferences.
- **Memory of specific encounters:** an orc who defeats you, or survives/flees an encounter, remembers it; on the next meeting he taunts you about it and may have gained a fear (from fleeing) or a strength. Memory surfaces in **dialogue** selected based on the detected past event.
- **Promotion/succession:** orcs occupy a **ranked hierarchy** (grunts → captains → warchiefs → overlords). Killing or being killed opens vacancies; NPCs are promoted/demoted to fill them, with power positively correlated to rank. Bodyguards can be assigned to warchiefs.
- **Domination / followers / betrayal (Shadow of War):** you can dominate orcs to make them followers/spies, place them in the hierarchy, and they can **betray** you (or be loyal); de Plater described expanding "stories of saviours, of loyalty or betrayal, and stories of friendship." Chris Hoge's GDC 2018 talk ("Helping Players Hate (or Love) Their Nemesis") covers tuning these emotional relationships. "Social vendettas"/Social Conquest let one player's nemesis invade another player's game and let players assault each other's forts.
- **Feature churn (postmortem):** the system nearly drowned in feature creep — at one point multiple Uruk factions each had separate Morale and Discipline bars ("their Hierarchy UI looked somewhat like a Christmas tree"); the team cut back toward the original "personal villains" core, keeping Domination.

**The load-bearing simplification.** Only the named captains/warchiefs in the ranked Uruk hierarchy carry persistent memory and rank state; the vast majority of orcs are disposable fodder. The "living world" feeling is produced by a small roster of stateful agents against a backdrop of stateless masses — press described it as a system where "any random enemy you faced in-game could gradually be developed into a unique rival."

**The legal layer — what is and isn't covered.**

The patent family (assignee Warner Bros. Entertainment Inc.; inventors de Plater, Hoge, Roberts, Valerius, Newton, Stephens; priority date March 26, 2015) all share the title *"Nemesis characters, nemesis forts, social vendettas and followers in computer games."* Granted members:

- **US 10,926,179 B2** — parent; filed Mar 25, 2016 (App. 15/081,732); granted Feb 23, 2021; **adjusted expiration Aug 11, 2036**; **36 claims** (1–18 method, 19–35 apparatus, 36 means-plus-function). Independent claims: 1, 19, 36.
- **US 11,660,540 B2** — continuation; granted May 30, 2023; adjusted expiration ~Apr 11, 2036.
- **US 12,201,908 B2** — continuation (granted, 2024/2025).
- **US 2025/0108303 A1** — pending continuation application.

**Correction to the brief:** The number cited in the task, **US 11,806,626, is NOT a Nemesis patent** — per its USPTO grant document it covers "systems and methods for enabling audience participation in bonus game play sessions" (game-streaming bonus rounds), an unrelated invention with a different priority chain. The relevant granted patent to cite is **US 10,926,179 B2**. The original 2016 publication number was US 2016/0279522 A1 (the same application as the parent).

**Verbatim independent claim 1 (US 10,926,179 B2), the load-bearing claim** (source: USPTO grant PDF):
> "1. A method comprising: controlling, by a processor, game events in a computer-implemented game, the game events involving an avatar that is operated in response to input from a player, and a first non-player character that is controlled by the processor to respond to and automatically oppose avatars based on first character parameters defined in a computer memory; detecting, by the processor, occurrence of a predefined one of the game events involving an interaction between the avatar and the first non-player character; changing, by the processor, second character parameters defined in at least one of the computer memory or a second computer memory for control of a second non-player character in the game based on the detecting, wherein the second non-player character is controlled by the processor to respond to and automatically oppose avatars based on the second character parameters defined in the at least one of the computer memory or the second computer memory; and outputting, to an output device, an indication of the second character parameters that are changed by the changing."

Claim 19 recites the identical limitations as an apparatus (processor + memory + display device); claim 36 is a means-plus-function video-game apparatus.

**What this actually claims (precise delineation):**
- **Covered by the independent claims:** an interaction between the player's avatar and a **first** hostile NPC that causes the game to **change the parameters of a *second*, different** hostile NPC, and then surface that change to the player. The "second NPC changes because of what you did to the first NPC" linkage is the inventive core the examiner allowed after six rejections over five years — prosecution repeatedly turned on adjusting a *second* NPC's parameters, not merely one NPC remembering you (per Eastgate IP's prosecution summary).
- **Narrowed further by dependent claims:** the faction being a **ranked hierarchy** where rank correlates with power; changing a **rank**; changing rendered appearance / personality / ability / a "player-interaction score"; **selecting dialogue** to indicate memory of the event; **power centers/"forts"**; and **social vendetta** sharing across players' game instances.
- **NOT covered (adjacent designs that remain free):**
  - A **single** NPC that simply remembers and reacts to its own encounters with the player (the independent claims require a *second* NPC whose parameters change). This is exactly the SoD/Kenshi pattern and is safe.
  - **Faction succession generically** — NPCs being promoted to fill vacancies — is only claimed *in combination with* the avatar→first-NPC→second-NPC parameter-change chain. Standalone succession (as in Kenshi world states, or Crusader Kings) is not the claimed invention.
  - Reputation/grudges accumulating **per observer** without the two-NPC linkage.
- **Legal fragility:** the Finnegan analysis (Del Monaco/Howes, Westlaw) notes the patent never faced a §101 (abstract-idea) rejection during prosecution but is "eminently challengeable" under *Alice* in litigation — it recites only generic computer components. Commentators (VGC; Jason Schreier) call the practical threat "overblown"; the deterrent is legal-fee risk, not certainty of validity. WB has never litigated it, and the developer, Monolith Productions (a 31-year-old studio), was **shut down on February 25, 2025**, alongside the cancellation of its Nemesis-powered *Wonder Woman* game.

### (3) Kenshi (Lo-Fi Games / Chris Hunt)

**The witness model.** Kenshi's defining simplification: **crime is only a crime if witnessed, but a witness is the whole faction.** Community consensus and the Kenshi Wiki agree: "There is no concept of killing witnesses in the game — if someone saw it happen, their whole faction knows instantly." If no faction member sees an act, there is (mostly) no reputation consequence; you can wipe out a squad in the wilds with no survivors and take little/no hit. Any character who witnesses a crime against their faction or an ally may turn hostile, even a normally allied faction.

**What propagates vs. stays local.**
- **Faction standing** is a numeric relation. At **−30** a faction turns hostile; at **+50** it becomes allied (community-verified thresholds).
- **Magnitude scales with location and target rank:** crimes in **cities** hurt relations much more than skirmishes in the wilds ("fighting someone in the middle of nowhere has very little effect on faction relations" — per the patch note that introduced situational AI). Fighting/killing a faction's **leader** costs more rep than a guard; healing a leader gains more than healing a guard. Diplomat-tagged NPCs give large swings.
- **Local vs. global:** hostility from a witnessed crime can be local/among present squads, while the reputation delta is global to the faction. Bounties are per-faction and large ones (e.g., >10k) are effectively permanent.

**NPC memory of the player.** Vanilla Kenshi's per-character memory is thin and dialogue-driven, exposed via the FCS **Dialogue Conditions & Effects**:
- `DA_Remember_Character` (effect) paired with the condition that triggers "if the NPC has spoken with a player character before… The entire player faction is then known." — i.e., memory is a boolean flag, and it attaches to the *player faction*, not a rich per-encounter record.
- A 2018 patch note announced a "new dialog/AI hybrid system that takes into account situation details and remembers what you've done in the past," plus thugs who can insult you in town then ambush you outside — a lightweight, dialogue-gated memory.
- **Fame/renown:** writer Natalie Mikkelson (Hunt's sister/business partner) confirmed in the Lo-Fi "Ask Me Anything" that defeating strong enemies or carrying bounties makes NPCs recognise/fear/comment on you — but she acknowledged it was "spread thin because of the limitless characters and combinations."

**What's simulated off-screen (almost nothing) — town overrides & world states.** This is Kenshi's biggest, most instructive fake:
- **World States** (FCS: World States, Kenshi Modding Wiki) are sets of boolean conditions (NPC alive/dead/imprisoned, town okay/destroyed, player ally/enemy of faction, player involvement). They are just flags and checks.
- **Town Overrides** swap a town's residents/faction/buildings when a world state flips. Crucially (per the modder Shidan): "When the town is unloaded from player view, it and its residents are despawned… and a new town with new residents is spawned in its place." **Nothing happens off-screen** — "the factions don't actually send forces to take locations." If the player is present when an override should trigger, "the game will simply wait for them to leave." Overrides only apply while the town is unloaded; on import, all world states are unapplied and reapplied.
- Off-screen fights, migrations, sieges are **not simulated** in vanilla; the world state changes are discrete prefab swaps, not continuous simulation. (Third-party mods like the "Kenshi Virtual Simulation Engine" bolt on an external C++/Python process reading game RAM to fake persistence — direct evidence that vanilla does not do it.)

**AI packages / data model (FCS).** The Forgotten Construction Set exposes: **Squads** (with Leader, Dialogue Leader/Squad, Faction, AI Packages, ChooseFromList randomized rosters), **AI Packages** (lists of prioritized actions with Signal Functions determining when a package ends and its target, plus an "Unloaded Func" for behavior while unloaded), and **Dialogue Packages** (grouped by event triggers, with "Inherits From" for shared lines). AI contracts (from dialogue) temporarily override a squad's normal packages. This package/goal architecture is directly analogous to what a Skyrim mod would want for "NPCs initiate actions based on state." (A C# SDK, OpenConstructionSet, also exists for programmatic edits.)

**What one developer could/couldn't sustain (postmortems).** Kenshi was ~12 years in development, on the **OGRE engine** (begun ~2006–2008). Chris Hunt confirmed to Siliconera: "For the first five or six years, I worked alone on it full time whilst juggling a minimum wage security guard job during the nights to get by." Notably (per The Spieler / Trip Harrison), Hunt "wrote less than one percent of it" — nearly all writing was by Natalie Mikkelson. The design abandons quests, cutscenes, and storyline; fiction is delivered through dialogue, scavenged documents, and environmental detail. Hunt's own reflection (PC Games Insider): after a decade, "Not much [learned], but if you keep your fans happy and treat them with respect they will give the same back." The takeaway: a solo dev sustained a "living world" *only* by refusing to simulate it — witnesses collapse to factions, off-screen towns collapse to prefab swaps, and memory collapses to booleans.

### (4) Synthesis — the load-bearing simplification in each

| Game | The fake players never noticed | The honest simulation players felt |
|---|---|---|
| **Shadows of Doubt** | Life isn't continuous: routines are batch-computed daily (10–15 s), the murder is pre-run at ~60× on load, 95% of citizens are near-free when off-screen, and bodies are *guaranteed* found via smell/scream/forced-entry failsafes. | Per-observer knowledge with provenance: who saw whom, from where, when — and memories that decay in fidelity (time-accuracy first) so investigations have real time pressure. |
| **Nemesis System** | The world isn't alive — only the named captains/warchiefs hold memory/rank state; the masses are stateless fodder. | A specific orc genuinely remembers *your* specific humiliations and taunts you about them, then climbs to fill the vacancy you created. |
| **Kenshi** | Off-screen settlements don't exist: they despawn and respawn as swapped prefab "overrides" gated by boolean world states; nothing is simulated when unloaded. | Consequence: witnessed crimes ripple to faction standing (scaled by place and target rank), bounties persist, and the world visibly reconfigures around your big actions. |

**Mechanisms worth copying (unencumbered):**
1. **SoD's fact-graph + incrimination flow** for belief-with-provenance: evidence nodes, typed "fact" edges carrying a **reliability weight**, and a propagation pass concentrating a value on a node. This is the single most directly reusable structure for "who saw what, who told whom, how the story mutated."
2. **SoD's rules-based memory decay** (fidelity as a function of familiarity, distinctiveness, strangeness, witness age/alertness; time-accuracy degrades before the memory drops). Cheap and legible.
3. **SoD's batch-precompute-then-deviate scheduler** — compute NPC day-plans in a short batch, only recompute live for the handful reacting to events. Essential for Skyrim-scale performance.
4. **Kenshi's witness→faction propagation** as the cheap default: local hostility from present witnesses, global reputation delta scaled by location and victim importance.
5. **Kenshi's AI Package / Signal-Function / world-state architecture** for "NPCs initiate actions from state," including an explicit **unloaded** behavior path.

**Mechanisms worth adapting (add per-observer richness carefully):**
- Add a **per-observer** grudge/reputation layer *on top of* Kenshi-style faction standing (the mod's stated goal). Keep per-NPC records only for a bounded roster of "named" NPCs (the Nemesis lesson) and fall back to faction-level state for the crowd.
- Adapt Nemesis **succession** (promotion into vacancies) using Kenshi-style **world-state flags** rather than continuous simulation — but keep it standalone (NPC promoted on a vacancy) to stay clear of the patent's two-NPC-linkage claims.
- Adapt SoD's **provenance-mutation** idea (memories degrade, time-accuracy first) to model rumor mutation across the "who told whom" chain — each retelling lowers reliability of the resulting fact edge.

**Patent/legal constraints (concrete rules for the mod):**
- **Safe:** an NPC remembering and reacting to *its own* encounters with the player; per-observer reputation/grudges; standalone faction succession; memory surfacing in dialogue for that same NPC. None of these fall within the Nemesis independent claims, which require a **second** NPC's parameters to change from an avatar↔first-NPC interaction.
- **Risky (avoid the specific combination):** an avatar↔NPC-A interaction that automatically changes **NPC-B's** parameters *and* NPC-B occupies a rank hierarchy *and* the change surfaces in NPC-B's dialogue/appearance — that stacked combination is the patented core (US 10,926,179 B2, claims 1/19). Also avoid "forts/power centers" whose characteristics are driven by nemesis parameters, and cross-player "social vendetta" sharing.
- The patent is challengeable under *Alice*/§101 but nobody wants the legal bill; treat **2036** as the practical clear date and design around the claim rather than through it. (As a non-commercial Skyrim mod your exposure is low, but the claim boundary is still the cleanest design guide.)

**Performance tricks that made city-scale knowledge simulation shippable:**
- **Precompute in batches, simulate deviations live** (SoD: 10–15 s/day plan).
- **Fast-forward off-screen setup** (SoD: murder pre-simulated at ~60×).
- **Proximity-scaled LOD for agents** (SoD: 95% of citizens near-free off-screen).
- **Collapse the memory unit** where players won't notice: faction-as-witness (Kenshi), named-roster-only memory (Nemesis).
- **Swap prefabs instead of simulating** off-screen world change (Kenshi town overrides gated by boolean world states; unapplied/reapplied on load).
- **Guarantee outcomes with failsafes** rather than emergent reliability (SoD body-discovery via forced-entry/scream/smell).

## Recommendations

1. **Build the core as an SoD-style provenance graph now.** Model beliefs as (subject, predicate, value, source, confidence) records and link them with reliability-weighted "fact" edges; run an incrimination-style propagation for any query ("who does NPC X blame?"). This is unencumbered and is the backbone the brief asks for. *Benchmark to change course:* if per-fact propagation costs too much at Skyrim cell scale, cap graph depth and only propagate within a settlement.
2. **Adopt a two-tier memory model.** Named/tracked NPCs (a bounded roster — think Nemesis's named captains) get rich per-encounter records with decay; everyone else contributes only to faction-level reputation (Kenshi). *Threshold:* if the named roster exceeds ~50–150 active entries and frame time suffers, demote least-recently-interacted NPCs to faction-level state.
3. **Schedule like SoD.** Precompute daily AI packages/goals in a batch on cell-load or day-rollover; only recompute for NPCs with an active reaction. Use Kenshi-style world-state booleans for off-screen settlement changes (prefab/state swaps) instead of live simulation.
4. **Stay patent-safe by construction.** Enforce a design rule: reputation/grudge changes propagate **observer→(that observer's opinion of)→player**, and NPC promotion triggers on **vacancy flags**, never as "interaction with NPC-A automatically rewrites NPC-B's combat parameters + rank + dialogue." Keep forts/vendetta-sharing out of scope. Re-evaluate freely after **August 2036**.
5. **Instrument legibility early.** SoD's main critique is players not knowing why they won/lost. Expose the provenance graph to the player (a corkboard-style debug/lore view) and make grudge causes inspectable ("Ulfric distrusts you because Ralof told him you sided with the Imperials"). *Threshold to iterate:* if playtesters can't explain an NPC's hostility, add a surfaced "because…" line keyed to the top-weighted fact edge.

## Caveats
- **Source asymmetry:** SoD's internals are documented first-hand by Cole Jefferies in dated dev blogs (2018) and corroborated by decompiled mods; some specifics may have changed by the 1.0 release (Sept 26, 2024). Kenshi's internals are documented mainly by the community (FCS wiki, modder Shidan) rather than by Lo-Fi directly — reliable but not official. Treat exact numeric thresholds (−30 hostile, +50 ally) as community-verified, not developer-published.
- **Patent analysis is not legal advice.** The delineation of covered vs. free designs is based on the granted claim text (US 10,926,179 B2) and published legal commentary (Finnegan; Eastgate IP); an actual clearance opinion requires counsel. The patent's validity under *Alice* is untested in court.
- **The brief's patent number was incorrect** (US 11,806,626 is unrelated to Nemesis, covering streaming bonus-game/audience-participation); this document uses the correct family (US 10,926,179 / 11,660,540 / 12,201,908).
- **"Nemesis-lite" is genuinely hard.** Multiple commentators note the full system required a specific combination of intent, time, money, and expertise; the patent is less a barrier than the engineering itself. Scope the mod's ambition to the two-tier model above rather than a full villain simulator.

## Sources
- ColePowered Games dev blogs (Cole Jefferies): DevBlog 8 "Simulating a City," DevBlog 10 "Gameplay Loop," DevBlog 15 "Moving in the Citizens."
- Shadows of Doubt Wiki (Fandom): Citizen Profile (23 fields). PCGamesN, GameCritics, Boiling Steam, GMTK/Mark Brown (Substack) reviews & analysis. Thunderstore (Piepieonline EvidenceObfuscation), Shadows of Doubt Modding wiki (Miraheze), Steam developer posts (sean.campbell). Fireshine Games 1.0 launch (Sept 26, 2024).
- US Patent 10,926,179 B2 (Google Patents + USPTO grant PDF) — claims, inventors, priority, expiration Aug 11, 2036; US 11,660,540 B2 (US 2021/0245057 A1); US 12,201,908 B2; US 2025/0108303 A1. Finnegan ("Will 101 Be a Nemesis…," Del Monaco/Howes). Eastgate IP; VGC; Game Developer; Engadget/Eurogamer; GeekWire (Monolith closure Feb 25, 2025).
- Michael de Plater postmortem (Game Developer/Gamasutra); GameSpot ("Inspired by Batman"); Chris Hoge GDC 2018 (GDC Vault / Game Developer).
- Kenshi Wiki & Kenshi Modding Wiki (Fandom): Guide to Faction Relations, World States, FCS: World States, FCS: AI Packages, FCS: Squads, FCS: Dialogue, Dialogue Conditions & Effects, Bounty. Steam community threads (modder Shidan on town overrides/world states). Lo-Fi Games (patch notes; "Ask Me Anything" with Natalie Mikkelson). Siliconera, PC Games Insider, GameSkinny (Chris Hunt interviews). The Spieler/Trip Harrison. Wikipedia (Kenshi). OpenConstructionSet (GitHub); Kenshi Virtual Simulation Engine (itch.io).