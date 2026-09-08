# GM-agent harness research prompts (2026-09-06)

Three prompts for external web-research agents (Gemini, ChatGPT with
browsing, Perplexity, etc.), investigating LLM-as-Game-Master agentic
harnesses from three different angles. Background section first, then one
self-contained prompt per angle — paste each individually, they don't need
to run together.

## Background (read this before researching any of the three prompts below)

Chronicle is a Skyrim SE/AE mod: an external social-simulation service
tracking NPC beliefs, rumors, and grudges, plus a C++ game plugin that
reads/writes live game state. It's mid-pivot toward a new headline idea: a
GM/storyteller agent that behaves like a real tabletop Dungeon Master — it
holds a loose, evolving campaign premise and gradually fills in details in
reaction to what the player actually does, rather than generating one-shot
quests or following a fully pre-written script. The goal isn't a novel
architecture invented from nothing; it's finding out what already exists so
any solid, license-compatible ideas (or, for genuinely open-source work,
actual code) can be adapted rather than rebuilt from scratch.

**Already found, don't re-report these, do go past them:** an internal
research pass already turned up `Sagesheep/NarrativeEngine-P` (MIT,
self-hosted TypeScript campaign platform with a systemic "Arc Engine" that
advances storylines independent of player action, and an "Agency Engine"
giving NPCs escalating goals that surface as ambient rumors/events);
CALYPSO (AIIDE 2023 paper + public artifact, but assists a *human* DM rather
than running autonomously); `deusversus/aidm` (early-stage, thin on real
documentation); a 2025 arXiv paper on agentic vs. static GM AI (confirms
agentic outperforms empirically, architecture details not fully recovered).
Classic procedural drama-management (Façade, Left 4 Dead's AI Director) is
also already surveyed elsewhere in this project. The three prompts below are
aimed at territory that pass didn't cover.

Cite specific repos, papers, product docs, or detailed technical writeups
wherever possible. General impressions or marketing-page claims without a
citable source are much less useful than "repo X's README describes
architecture Y" or "paper Z's section 3 specifies algorithm W."

---

## Prompt 1: LLM GMs running *existing, pre-written* campaigns

Investigate tools, products, or research prototypes that use an LLM to run
an **existing, published tabletop campaign module** (e.g. D&D 5e's *Curse
of Strahd*, *Tomb of Annihilation*, or similarly structured commercial/
community adventures) as a Game Master, as opposed to generating a campaign
from scratch. This is architecturally a different problem from freeform
generation: the system must stay anchored to a fixed plot outline, fixed
locations, fixed NPCs and encounters from the source module, while still
improvising dialogue and adapting to player choices that deviate from the
module's assumed path.

Look for: any AI-DM product or open-source project that explicitly supports
loading a published module/adventure as source material (rather than only
freeform "make up a story" mode); how it represents the module's structure
internally (does it chunk the PDF/text into scenes/nodes? build a
retrieval index? hand-author a state machine?); how it handles a player
going off the module's expected path (does it improvise and reconverge,
railroad back, or lose coherence?); and any documented failure modes
specific to staying faithful to pre-written source material (hallucinating
content that contradicts the module, forgetting established NPCs/plot
threads, etc.). Include both shipped products (AI Dungeon Master bots,
VTT-integrated AI tools, Discord bots built for this) and academic/research
prototypes.

For each real candidate, report: architecture (as much as can be
determined), how it ingests/represents the source campaign, license/
availability, and maturity. End with a verdict: is there a genuine
precedent for "LLM agent running a fixed, pre-authored narrative structure
while improvising around it," and if so, what's the strongest one found?

---

## Prompt 2: LLM Game Masters operating *inside an existing video game world*

Investigate any project — shipped game, mod, or research prototype, for
*any* game engine, not specifically Skyrim — where an LLM-driven GM/director
agent generates original, emergent storylines and quest content **using an
existing game's own assets, locations, and lore**, reacting to the player's
actions and conversations with NPCs as they happen, rather than the LLM
generating a purely textual/abstract story disconnected from a real
explorable 3D (or 2D) world.

This is distinct from generic "AI Dungeon"-style text adventures (which
don't use a pre-built game world's real geometry/assets) and distinct from
classic procedural content generation (which places pre-authored content by
rule, not LLM reasoning). The target is specifically: an LLM-level agent
deciding *what story beat happens next* and grounding it in a real game's
existing map, NPCs, and items — for example, deciding a specific existing
NPC should receive a new schedule, a specific existing location should host
a new scene, or an existing quest-giver should offer content that wasn't
scripted at ship time.

Look particularly hard at the current wave of Skyrim/Bethesda-engine LLM-NPC
mods (SkyrimNet, Mantella, CHIM/HerikaServer and similar) for whether *any*
of them have shipped or documented a component that goes beyond dialogue/
rumor generation into actually authoring new quest-like content or lasting
world changes grounded in the game's own assets — cite the specific feature
and its documentation if so, or state plainly if none do. Also look outside
Skyrim: other open-world or RPG titles/mods where this has been attempted
(Baldur's Gate 3 modding scene, other Bethesda-engine games, indie
LLM-narrative experiments, academic game-AI papers using a real 3D testbed
rather than a text-only one).

End with a verdict: does real precedent exist for "LLM agent authoring new
content grounded in an existing game's real assets, reactive to player
behavior," and how close does the closest example actually get?

---

## Prompt 3: Multi-agent, multi-timescale architectures for long-horizon reactive storytelling

The working hypothesis (not yet validated) is that a GM agent like this
can't be a single LLM call — it likely needs multiple agents or passes
operating at different timescales: something like a slow-tick "campaign
architect" that plans/revises a story arc over a long horizon (hours/days
of in-game time), a faster "scene director" that decides moment-to-moment
beats and escalation within that arc, and an immediate per-interaction layer
that renders NPC dialogue in the moment. Investigate whether this
"hierarchical, multi-timescale agent" pattern has real precedent, either in
interactive-narrative/game-AI specifically or in the broader LLM-agent
literature.

Look for: hierarchical planning agent architectures (slow planner + fast
executor splits) in any domain, not just games — this pattern shows up
under names like "manager/worker agents," "slow-fast agent systems,"
hierarchical task decomposition, or long-horizon agents with periodic
replanning (Voyager-style agents, AutoGPT-lineage projects with a
plan-then-execute loop, etc.); any narrative-generation-specific work using
multiple LLM calls/agents at different granularities (a long-horizon plot
planner distinct from a scene-level or line-level generator); and concrete
engineering patterns for keeping a slow planner's output consistent with
what a fast layer actually executes (how do these systems avoid the fast
layer drifting away from what the slow layer intended, or the slow layer
re-planning in a way that contradicts what already happened).

End with a verdict: is multi-timescale/hierarchical agent decomposition a
well-established pattern for this kind of problem, what's the strongest
concrete precedent (with an architecture description, not just a name), and
are there known failure modes worth designing around from the start?
