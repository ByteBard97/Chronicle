---
date: 2026-08-23
sources:
  - "AI Drama Managers and Directors.md"
topic: "AI drama managers / director architectures across games and academic literature"
status: filed
---

# AI Directors and Drama Management

Single-source survey of drama-management and AI-director architectures
across academic interactive-narrative research (Façade, narrative
planning, Experience Management, Concordia) and shipped commercial
systems (Left 4 Dead's Director, RimWorld's Storytellers, Shadows of
Doubt's case generator, PaSSAGE). Filed here rather than in the main
numbered `docs/research/` series because — like the Crusader Kings and
real-time-spatial-sim files already in this folder — it's cross-game
comparative material informing Chronicle's reactivity/GM design, not
Skyrim-substrate research tied to an accepted ADR. Its companion piece,
[19-skyrim-quest-injection-machinery.md](../19-skyrim-quest-injection-machinery.md),
covers the Skyrim-specific mechanics for actually wiring a GM layer into
the game; this file covers the design patterns for what that layer
should *decide*, independent of engine.

This is ahead-of-need research: `docs/architecture.md`'s Build order
lists "**prospective drama management**" under **Defer** — no GM/director
layer is in Chronicle's current build order. Some ground here already
overlaps this folder's existing Crusader-Kings coverage (King of Dragon
Pass and Wildermyth are already covered in depth in
[ck-postmortems-and-design-lessons.md](ck-postmortems-and-design-lessons.md)
and
[ck-failure-modes-and-reactivity-loop.md](ck-failure-modes-and-reactivity-loop.md))
and the spatial-sim files ([Shadows of
Doubt](spatial-sim-shadows-of-doubt-nemesis-kenshi.md) is already covered
there from a witness/memory-decay angle) — not re-filed here where it
overlaps; see "Not repeated here" below.

## Findings

- **[BUILD-ON] The universal four-stage director pipeline, cross-
  validated against report 19's independent Skyrim-specific framing.**
  Every architecture surveyed — from Façade's Beat Manager to Concordia's
  LLM Game Master — decomposes into: (1) **input signals** (live state:
  player stress, colony wealth, NPC belief graphs, faction assets), (2)
  **recognition/sifting** (evaluative logic — pacing FSMs, Prolog
  constraint satisfaction, storylet matching — that isolates dramatically
  interesting configurations), (3) **intervention selection** (a concrete
  structural choice: adjust a spawn budget, draw a storylet, instantiate
  a quest template), (4) **presentation/surfacing** (multimodal render:
  UI, dialogue barks, journal entries). This is the same shape report 19
  arrives at independently for Skyrim's IntelEngine — worth treating as a
  validated architecture for Chronicle's own eventual GM layer, not a
  framing coincidence.
- **[DESIGN-INPUT] Façade's four documented failure modes are a direct
  checklist against any future beat/storylet-driven Chronicle layer.**
  (1) Shallow character self-awareness — autonomous characters execute
  beat parameters without genuine internal state, i.e. they're reactive
  to the director, not to each other; Chronicle's belief/grudge graph is
  explicitly the fix for this, since NPCs would act from their own
  tracked beliefs rather than beat-assigned behavior. (2) Spatial/
  environmental constraints — Façade's beat manager only worked in a
  tightly confined single room; expanding physical space "dramatically
  expands the state space" and breaks coordination — a direct warning
  against a monolithic beat-manager approach for an open, ~1,000-NPC
  Whiterun-scale world. (3) Absence of inciting incidents — pure
  reactivity to player input means players get dropped in without clear
  framing; any Chronicle GM layer needs an explicit "why does this matter
  now" framing step, not just reactive triggering. (4) NLP reductionism —
  nuanced input collapsed to a binary affinity score reads as jarring;
  relevant if Chronicle ever parses free-text player/NPC dialogue into
  scalar state changes (the same "format-valid ≠ content-valid" caution
  already flagged in
  [03-hybrid-llm-symbolic-architecture.md](../03-hybrid-llm-symbolic-architecture.md)).
- **[RISK] RimWorld's Storyteller wealth-scaling is a documented,
  exploitable failure mode directly relevant if Chronicle's economy tier
  (deferred to v0.4, see
  [16](../16-skyrim-economy-mods.md)/[18](../18-skyrim-economy-mods-v2.md))
  ever feeds a pacing/intervention system.** Threat Points scale with
  raw colony market value rather than defensive capability, so players
  learn to deliberately destroy or gift away surplus wealth to suppress
  raid intensity — "wealth management" as an exploit. The generalizable
  lesson: **any numeric metric driving GM interventions must track a
  cause the player can't trivially game by manipulating the metric
  itself, distinct from the systemic reality the metric is meant to
  proxy.** If a future Chronicle director ever uses, say, aggregate
  grudge-intensity or rumor-spread-volume as an intervention trigger,
  this is the specific exploit shape to design against.
- **[BUILD-ON] Left 4 Dead's four-state pacing FSM (Build Up → Peak →
  Sustained Peak → Relax) is the cleanest shipped model of legible
  intensity pacing**, and its fairness mechanism is explicit and
  transferable: state transitions are always multimodally signaled
  (ambient audio shifts, distinct musical stingers per threat type,
  character audio barks) *before* the intervention lands, so a spike in
  difficulty never reads as untelegraphed. Its one documented exploit —
  players lingering in "safe zones" to manipulate the stress counter — is
  a second instance of the same "player games the metric, not the
  underlying threat" failure class as RimWorld's wealth exploit.
- **[DESIGN-INPUT] Shadows of Doubt's "Case Generator," read as
  provenance-anchored intervention rather than witness/memory mechanics
  (the angle
  [spatial-sim-shadows-of-doubt-nemesis-kenshi.md](spatial-sim-shadows-of-doubt-nemesis-kenshi.md)
  already covers).** A killer is selected by archetype (Corporate
  Cutthroat, Dating Service Stalker, Apartment Sniper, etc.), then
  *physically executes the crime using in-engine systems*, leaving
  evidence determined entirely by their actual simulated history and
  actions — a business card and graffiti for the Corporate Cutthroat
  (targeting a real career rival from the simulated employment graph),
  lipstick and a note for the Dating Service Stalker (from the simulated
  in-world dating app), bullet trajectories from an apartment the sniper
  actually occupies. **No clue is ever spawned from a template disconnected
  from simulation state — evidence has "complete physical provenance."**
  This is the load-bearing precedent for report 19's "provenance for
  free" quest-blandness fix and for Chronicle's own inspectability
  requirement (`docs/decisions/0007-inspectability.md`): a GM
  intervention should be *generated from*, and fully traceable back to,
  actual tracked simulation state — never an independently-rolled event
  merely decorated with simulation-flavored text after the fact.
- **[BUILD-ON] PaSSAGE (Thue et al., Neverwinter Nights) is the concrete
  prior-art implementation of player-modeling-driven content selection**,
  useful if Chronicle's GM layer ever wants to vary *what kind* of
  intervention surfaces per player rather than just *whether* one fires.
  Player actions are pre-annotated with modifiers to a five-element style
  vector (Fighter/Power Gamer/Tactician/Storyteller/Method Actor, after
  Robin Laws' RPG archetypes); the next encounter is chosen by dot-
  product match between the player vector and each candidate encounter's
  annotation vector. Documented trade-offs, directly relevant to scoping:
  **authorial annotation overhead** (every branch/dialogue/item needs
  manual multi-dimensional annotation — multiplies content cost), **vector
  drift** (mechanically-motivated actions, like smashing crates for a
  key, get misread as playstyle signal), and **pacing flattening**
  (pure preference-adaptation creates a feedback loop that strips
  contrasting beats, e.g. no quiet conversational content ever reaches a
  player who tested as a Fighter). None of these are solved problems —
  file as known costs of adding player-modeling to a future GM layer, not
  as a recommended must-have.
- **[BUILD-ON] DeepMind's Concordia is the most directly transferable
  academic pattern for an LLM-narrated, symbolically-grounded GM**, and
  it's the same hybrid-neurosymbolic shape Chronicle's own architecture
  already commits to (`docs/decisions/0003-substrate-choice.md`,
  [03-hybrid-llm-symbolic-architecture.md](../03-hybrid-llm-symbolic-architecture.md)).
  Its loop: agents emit natural-language *intent* strings; the GM
  intercepts and validates each intent against grounded variables
  (physical presence, inventory, spatial bounds) — if valid, it updates
  grounded state and synthesizes a natural-language "Event Statement"
  describing the outcome; if invalid, it tells the agent why the action
  failed; either way, the Event Statement is pushed into nearby agents'
  memory logs. **The concrete, reusable idea: an LLM should never be
  allowed to directly mutate world state — it emits intent, a grounded
  validator (symbolic, deterministic) accepts/rejects and performs the
  actual mutation, and only the validator's outcome gets narrated back.**
  This is a slightly more mechanized version of the same principle
  report 19 independently states for IntelEngine ("LLM restricted to
  narrative framing... symbolic state governs engine logic").
- **[RISK] The "unconstrained generation breakdown" failure catalogue is
  a direct warning against ever letting an LLM freely narrate Chronicle
  world-state changes without a validation layer.** Documented failure
  modes of autoregressive-LLM-only narrative systems: hallucinated goals/
  items/characters that don't exist in game state (quest progression
  stalls), state amnesia (items vanish, dead characters reappear), and
  causal/world-logic collapse (physically impossible actions destroy
  mechanical agency). All three are avoided, per this report's own
  conclusion, only by the hybrid neurosymbolic pattern above — symbolic
  layer as absolute truth, LLM as reader/narrator/validated-API-caller
  only. Chronicle's belief-facet store already commits to this
  separation; this is corroborating literature, not a new design
  requirement.
- **[DESIGN-INPUT] Symbolic narrative planning (IPOCL and successors) is
  academically important but not directly actionable at Chronicle's
  scale — filed for completeness, not as a build target.** Classical
  planners (STRIPS/PDDL-style) treat story generation as search over
  character/environment actions from an initial state to an authored
  goal state; IPOCL's contribution was forcing every individual action to
  be motivated by that character's own goals (preventing "suicidal
  puppet" actions purely to satisfy the global plot). Its documented
  failure modes — combinatorial state explosion with added
  agents/locations, precondition rigidity breaking on unscripted emergent
  player actions, and heavy knowledge-engineering overhead — are exactly
  why storylet/precondition-filtering systems (King of Dragon Pass,
  Wildermyth — already covered in this folder's CK files) won out
  commercially over full symbolic planning, and why Chronicle's own
  design (sparse-graph, provenance-tracked events + a future
  precondition-filtering sifter) already tracks the commercially-proven
  branch of this lineage rather than the academically-elegant one.

## Universal director pipeline table (from this report)

| System | Input | Recognition | Intervention | Presentation |
|---|---|---|---|---|
| Façade | Discourse acts, spatial vectors | Tension level + zero-sum affinity score | Select next beat from authored library | Joint ABL dialogue + physical animation |
| Left 4 Dead Director | Damage, health, mobility, incapacitations | Intensity threshold + FSM pacing stage | Zombie population caps, item drop queues | Music cues, horde spawns, ambient barks |
| RimWorld Storytellers | Colony wealth, adaptation timer, colonist count | Threat-point budget + event cooldowns | Roll event category (raid/trade/eclipse/disease) | Warning envelope, alert sound, spawn vectors |
| Shadows of Doubt | NPC routines, phone logs, footprints | Killer-archetype trigger via relationship graph | Execute physical crime, drop physical clues | In-world crime-scene discovery, news reports |
| King of Dragon Pass | Faction state, magic, season, clan mood | Prolog constraint satisfaction | Priority-band filtering, storylet draw | Storylet modal + advisor commentary |
| PaSSAGE | Tracked player actions | Vector dot-product playstyle match | Select next encounter module | Instantiate encounter + customized dialogue |
| Concordia GM | Agent NL intent strings | Grounded variable validation | Update grounded variables, advance clock | Natural-language Event Statement to memory |

## Not repeated here

King of Dragon Pass's and Wildermyth's mechanics (storylet
precondition-filtering, priority banding, character-pair bindings,
legibility-through-visual-interface) are already covered in depth in
[ck-postmortems-and-design-lessons.md](ck-postmortems-and-design-lessons.md)
and
[ck-failure-modes-and-reactivity-loop.md](ck-failure-modes-and-reactivity-loop.md);
Shadows of Doubt's witness/memory-decay/provenance-graph detective
mechanics are covered in
[spatial-sim-shadows-of-doubt-nemesis-kenshi.md](spatial-sim-shadows-of-doubt-nemesis-kenshi.md)
and
[spatial-sim-legal-boundaries-and-witness-propagation.md](spatial-sim-legal-boundaries-and-witness-propagation.md).
This file only adds the Case Generator's provenance-anchoring lesson
(new framing on already-known ground) plus genuinely new material: Façade,
formal narrative planning, Left 4 Dead, RimWorld, PaSSAGE, and Concordia.

## Caveats

- Single-source report — no independent cross-check exists yet for this
  ground.
- Several citations (Façade failure modes, PaSSAGE trade-offs) are to a
  thesis/paper this session did not independently re-read; treat as this
  report's synthesis of that literature, not a primary-source
  verification.
