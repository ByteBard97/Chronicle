---
date: 2026-08-23
sources:
  - "GM_Agent_and_Radiant_Machinery_Research.md"
topic: "AI drama managers / director architectures — second independent pass"
status: filed
---

# AI Directors and Drama Management, v2

Second independent pass on the same ground as
[ai-directors-and-drama-management.md](ai-directors-and-drama-management.md),
from the general-field part ("Prompt A") of a combined report whose
Skyrim-specific part is filed as
[20-skyrim-quest-injection-machinery-v2.md](../20-skyrim-quest-injection-machinery-v2.md).
Same naming pattern as
[17](../17-skyrim-social-reactivity-mods-v2.md)/[18](../18-skyrim-economy-mods-v2.md).
This pass goes considerably deeper into the academic drama-management
lineage (declarative optimization, plan-based mediation) and the LLM-era
consumer record (AI Dungeon, Hidden Door) than the first pass — file
separately rather than merge given how much is genuinely new.

## What's genuinely new here (not in the first pass)

- **[RISK] The Declarative Optimization Drama Management (DODM) failure
  record is the single most load-bearing new finding: the optimizer is
  the least important part of a drama manager.** Nelson and Mateas
  re-applied Weyhrauch's search-based drama management (which had worked
  on a simplified *Deadline*) to *Anchorhead* and found the results
  **did not transfer**; switching to offline reinforcement learning
  didn't help either. Their conclusion: the available DM actions were
  "simply too weak to affect measured story quality" — an authorship
  problem, not an optimization problem. With a synthetic "maximally
  powerful" action set (a causer/denier/re-enabler for every plot point),
  even a weaker algorithm performed well. **Direct implication for any
  future Chronicle GM: invest in the intervention vocabulary (courier
  notes naming a real employer, hired thugs traceable to a real grudge,
  faction mobilizations anchored to tracked resources) before investing
  in clever selection logic — a dumb picker over a rich, provenance-
  carrying action set beats a sophisticated picker over a thin one.**
- **[RISK] A director that optimizes a single quality metric can destroy
  player agency by forcing its own "best" story.** Roberts et al.'s
  response — Targeted Trajectory Distribution MDPs — aims the director at
  an author-specified *distribution* of experiences rather than one
  optimal trajectory. Generalizes directly to RimWorld's Randy Random
  persona (bounded-but-undirected randomness is a legitimate design
  point, not a lesser one) and argues against ever tuning a future
  Chronicle GM purely to maximize one legibility/drama score.
- **[BUILD-ON] Plan-based mediation (R. Michael Young's Mimesis lineage)
  supplies a formal license for retroactive reframing that matches
  Chronicle's own no-invisible-decisive-variables doctrine exactly.**
  When a player does something the authored plan didn't anticipate, the
  mediator either **intervenes** (blocks/undoes the action) or
  **accommodates** (replans so the action is absorbed). The documented
  failure: repeated intervention makes players "realize their behavior is
  limited" — i.e. accommodate, don't block, whenever possible. The 2013
  extension is the load-bearing piece: giving the mediator a model of
  character knowledge widens the accommodative search space by
  replanning *past* events, but explicitly "only as long as the planner
  maintains story-world consistency by restricting modifications of past
  events to aspects of the world unobserved by the user." **This is the
  formal, citable version of "a rumor can retroactively reveal what
  really happened, exactly where the player couldn't have observed the
  truth already" — directly reusable if Chronicle's GM layer ever needs
  to justify a retcon-shaped reveal (the widow's grudge existed all
  along; the player just never saw the belief update happen).**
- **[BUILD-ON] Daggerfall's actual quest format is now precisely
  documented, correcting the vaguer "QRC/QBN" gloss in the first pass and
  in report 19/20.** 227 shipped quests (241 with the CompUSA edition),
  gated by **guild/social-class membership and reputation** — the same
  "Domestic Squabble" template means something different at reputation
  rank 0 vs. rank 7. Donald Tipton's **Template v1.11** decompiles the
  binary format into readable source ("more like a complex INI file"):
  resource declarations (Item, Person, Place, Clock, Foe) plus task
  blocks driven by startup/timer/condition triggers. Daggerfall Unity's
  open-source reimplementation runs this as a documented **QuestMachine**
  — quests instantiated from text source at runtime, parsed by
  regex-matched `ActionTemplate` factories, ticked at 10 Hz, serialized to
  JSON save state, with third-party-registerable actions (150+ community
  quest-pack quests exist in this format). **The longevity lesson stated
  explicitly: Daggerfall's radiant content works because templates are
  embedded in a reputation economy, not because the templates themselves
  are clever** — corroborates report 19's "provenance for free" thesis
  from the oldest possible source in the lineage.
- **[BUILD-ON] The storylet academic thread names the closest published
  architecture to a sifter-fed GM.** Breault et al. built a quest engine
  that **generates quests from world state at generation time**, rated by
  human judges as comparable to human-authored quests, with the
  significant property that "the creation of possible quests increases
  as the game progresses" — richer world state yields richer quest
  material. This is a direct academic endorsement of Chronicle's core
  bet (quests anchored to live simulation state scale *with* the
  simulation instead of exhausting a fixed template space), independent
  of any Skyrim-specific argument. Caveat from mixed-initiative studies
  (Questgram): designers gave generation and suggestion features a
  "mixed response," mostly over abstract actions and random placement —
  treat generative quest tooling as a creativity scaffold for human
  authors, not a fully autonomous author, at least as currently studied.
- **[RISK] The AI Dungeon / Hidden Door consumer record is the sharpest
  cautionary evidence yet against unconstrained LLM narrative generation
  — new in this pass entirely.** AI Dungeon's failures read as a
  checklist of what a symbolic substrate prevents: characters "forgot who
  they were after a few exchanges," NPCs changed gender mid-scene, a
  frozen vampire would bite the player again the very next turn, and
  players had to hand-maintain a "pin" memory that "felt like learning a
  programming language" — with **memory drift remaining the category's
  #1 complaint as of 2026 reviews**. Hidden Door (a more sophisticated
  attempt — structured plot beats, explicit setup/payoff data structures,
  a game-engine layer tracking every character/item/location) still
  failed on **ungroundedness**: "the story is written only as far as it's
  been presented to the player… the treasure chest doesn't have traps,
  and doesn't not have traps" — so choices retroactively change the
  *present*, not just the future, which "undermines autonomy" even when
  players can't articulate why. The reviewer's fix list is close to a
  ready-made Chronicle design checklist: commit to and track a world
  state, outline consequences *before* presenting choices, let failure
  consequences actually disrupt world state, and generate more material
  than the reader consumes. Also newly documented: **turn-cycle latency
  kills pacing** (90–120 seconds per cycle in one research director;
  10–20 seconds with "thinking" disabled, at the cost of more
  hallucination), and Retail Mage's team had to **deliberately make their
  AI dumber** because NPCs that optimally self-organize "leave players
  with nothing to do" — a direct rediscovery of the old Sims-design
  lesson, worth flagging for Chronicle's own NPC-agency tuning once an
  LLM tier is added (currently deferred per `docs/architecture.md`'s
  build order).
- **[BUILD-ON] 2024–2026 research has landed almost exactly on
  Chronicle's own hybrid architecture — new, specific citations.** **Drama
  Llama** (2025): an LLM-powered storylets framework where authors write
  only 3–4 natural-language "pivot point" triggers and the LLM improvises
  within them — explicitly positioned on the same authorial-intent vs.
  character-autonomy axis this literature keeps returning to. **The
  Interview** (prompt-engineering study of generative NPC dialogue)
  formalizes **Symbolically Scaffolded Play**: no single prompt design
  guarantees better play, over-constraining "actively diminishes
  improvisation," and the working pattern is *role-differentiated*
  scaffolding — rigid symbolic structure for quest-giver roles, loose
  structure for improvisational suspects, with fuzzy parameters persisted
  in a shared JSON memory schema. A 2026 AI-native-games survey's stated
  open problems — "persistent memory, world-state tracking, and
  long-term consequence management remain fragile," inference
  cost/latency must shape mechanic design, generated content must survive
  verification against rules — are named as still-open in the general
  literature, which the report explicitly notes Chronicle's symbolic sim
  "solves by being the substrate" rather than needing to solve at the
  LLM layer. Its closing claim is worth carrying forward precisely:
  **nobody has yet shipped an LLM director whose interventions are
  verified against a live belief/grudge/faction simulation inside a
  commercial-scale RPG** — that is the specific uncovered front Chronicle
  would occupy if it ever builds this layer.
- **[DESIGN-INPUT] The seven documented ways directors break player
  trust, consolidated across the whole literature in this report's own
  synthesis — a more complete taxonomy than the first pass's trust-hazard
  list.** (1) Visible railroading — repeated action-nullification. (2)
  Ungrounded generation — retroactively rewriting the world at
  presentation time. (3) Agency-destroying optimization — forcing one
  "best" trajectory. (4) Memory inconsistency — forgotten facts turn play
  into prompt maintenance. (5) Deceptive provenance — generated content
  disguised as authored content, or forced without consent. (6)
  Static-world exposure — sending players to just-cleared locations,
  spotlighting that the world didn't actually change. (7) Unsolvable/
  unrewarding generated content — completion or reward paths that
  silently break. Each pairs with a named design countermeasure in the
  source (accommodate over block; sim-first framing; target distributions
  not optima; symbolic sim as sole truth; opt-in/legible generated
  content; track intervention history to avoid repeats; failsafe
  doctrines plus native completion paths) — worth lifting as a checklist
  wholesale if Chronicle ever drafts an ADR for a GM/director layer.

## Not repeated here

Façade's beat-manager mechanics, the universal four-stage pipeline table,
RimWorld's wealth-exploit and Left 4 Dead's pacing FSM, Shadows of
Doubt's provenance-anchored case generator, PaSSAGE's player-modeling
trade-offs, and DeepMind Concordia's grounded-validation loop are already
filed in
[ai-directors-and-drama-management.md](ai-directors-and-drama-management.md)
and substantially overlap this report's coverage of the same systems —
not re-filed here. King of Dragon Pass and Wildermyth mechanics remain
filed in this folder's Crusader Kings files, as noted there.

## Caveats

- Single-source addition; citations to specific papers (Nelson & Mateas,
  the 2013 Mimesis extension, Drama Llama, The Interview) were not
  independently re-read by this session — treat as this report's
  synthesis, not primary-source verification.
- The 2026 AI-native-games survey and consumer-product claims (AI
  Dungeon/Hidden Door reception, turn-cycle latency figures) are
  point-in-time and will drift.
