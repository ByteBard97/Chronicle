---
date: 2026-09-06
sources:
  - "CALYPSO: LLMs as Dungeon Masters' Assistants, arXiv:2308.07540 (AIIDE 2023)"
  - "northern-lights-province/calypso-aiide-artifact, GitHub (fetched 2026-09-06)"
  - "Static Vs. Agentic Game Master AI for Facilitating Solo Role-Playing Experiences, arXiv:2502.19519 (2025)"
  - "deusversus/aidm, GitHub (fetched 2026-09-06)"
  - "Sagesheep/NarrativeEngine-P, GitHub — README, ARCHITECTURE.md via raw.githubusercontent.com (fetched 2026-09-06)"
  - "Game Knowledge Management System: Schema-Governed LLM Pipeline for Executable Narrative Generation in RPGs, MDPI Information 14(2):175 (fetch blocked, 403 — abstract-level only, via search snippet)"
  - "WebSearch: open-source LLM agent GM harnesses, AI Dungeon Master GitHub topics, long-horizon narrative planning RPG papers 2025-2026 (2026-09-06)"
topic: "Whether a real, buildable agentic-GM harness already exists for a Dungeon-Master-style agent that holds a loose evolving campaign premise and fills in detail reactively — could Chronicle port one in, or must it design its own?"
status: filed
---

# AI Dungeon Master / GM Agent Harnesses — Survey

Answers a direct question raised in a 2026-09-06 owner brainstorm on Chronicle's
headline direction: is there a real, inspectable agentic harness for "act like a
tabletop DM — hold a loose campaign idea, fill in details gradually in reaction to
the player" that Chronicle could port in, rather than design from scratch? This is
the gap in the repo's existing `comparative-systems/ai-directors-and-drama-management`
v1-v4 passes, which cover classic procedural drama management (Façade, Left 4 Dead's
Director) and simulation-grounded dialogue prior art (CICERO, Comme il Faut, Slice of
Life, Friends & Fables/ACE-1, Concordia) but not modern LLM-agent GM harnesses
specifically built around an evolving, self-revising campaign premise.

## Verdict

**No single harness is a drop-in port, but one is close enough to be a genuine
build-on candidate rather than pure inspiration: `Sagesheep/NarrativeEngine-P`
(MIT-licensed, actively developed, self-hosted).** Its architecture independently
converges on several ideas Chronicle already committed to — persistent per-entity
state with provenance-like tracking, world-level events that fire independent of
the player, ambient surfacing of NPC goal collisions as rumors — which is a strong
signal this is a validated shape, not a coincidence. Being MIT means actual code
patterns (not just the idea) are fair game to study closely, unlike everything else
below.

## Candidates, ranked

### 1. NarrativeEngine-P — the strongest match, real code, real license

Self-hosted, MIT, ~500 commits, v1.0.4, TypeScript. Three subsystems map almost
one-to-one onto what the owner described wanting:

- **Agency Engine** (`src/services/npc/agency/`): NPCs carry short-term "wants"
  that escalate into long-term "goals," resolved via dice rolls with tunable
  constants (`DRIVE_MULT`, `KARMA_CAP`), and a personality "hexagon" (6 axes,
  ±3) that drifts from outcomes (`applyGoalOutcomeNudge`, `hexDelta` clamped
  ±1 per tick). When two NPCs' goals collide, the collision surfaces as an
  **ambient rumor or event** — exactly the "you overhear a guard grumbling"
  behavior from this session's earlier brainstorm, already shipped code.
- **Arc Engine** (`src/services/arc/arcEngine.ts`): a "7-type systemic conflict
  engine" that runs `runArcTick()`/`runArcSpawn()` to introduce and advance
  large-scale storylines **independent of player action** — the closest thing
  found anywhere to "the GM has a loose campaign idea it gradually fills in."
  Arc ticks are tier-gated (fire on a cadence, not every turn).
- **Campaign/Timeline state**: a `Campaign` type (~70 fields) persisted via
  debounced autosave; a `Timeline`/`DivergenceRegister` pair tracks player-choice
  branching with "supersession rules" — structurally similar in spirit to
  Chronicle's own event-sourced branch-per-generation model (ADR-0004), independently arrived at.
- **Reactivity**: a `contextRecommender` runs an LLM pass to rank which archived
  scenes/lore are most relevant to what the player just did, feeding a
  multi-round "deep archive search" before the GM response generates — i.e.
  retrieval-then-render, the same shape as Chronicle's "engine decides, LLM
  renders" doctrine (ADR-0011), independently reinvented here for narrative recall
  instead of dialogue options.

Caveat found directly in the architecture map: **the GM doesn't explicitly
"decide" what happens next** — context selection and the agency/arc systems
surface what's narratively live, and generation reacts within those constraints.
That's a design choice worth noting, not a flaw: it's structurally identical to
Chronicle's own "provenance-anchored intervention, never an independently-rolled
event" principle, arrived at independently a third time.

### 2. CALYPSO (arXiv:2308.07540, AIIDE 2023) — real precedent, wrong shape

Academic, peer-reviewed, artifact repo public
(`northern-lights-province/calypso-aiide-artifact`). A Discord bot that assists
a **human** DM — distills monster/setting lore into brainstorming prompts,
explicitly preserves the human DM's creative agency rather than acting
autonomously. Real, citable prior art for "LLM helps run a game," but the wrong
shape for Chronicle's fully-autonomous-GM ambition — it's a copilot, not the
pilot. Worth citing for the "high-fidelity text + low-fidelity ideas the human
develops" framing if Chronicle ever wants a human-visible "why did the GM do
this" inspector, echoing ACE-1's already-filed "View Context" transparency
feature.

### 3. "Static vs. Agentic Game Master AI" (arXiv:2502.19519, 2025)

Directly on-topic title; PDF extraction failed (image-only pages), abstract-level
summary only. Compares a simple-prompt static GM against a multi-agent
ReAct-based agentic GM for solo RPG; agentic version measurably improved
immersion/curiosity. Confirms the general thesis (agentic beats static) but the
abstract gives no architecture detail worth porting — treat as supporting
evidence, not a build-on candidate. Worth a follow-up pass with a proper PDF-to-text
tool if this direction is pursued seriously.

### 4. deusversus/aidm — early-stage, undocumented, skip for now

Marketing-page-only description (24+ agents, ChromaDB memory, multi-phase turn
lifecycle); actual agent roles/orchestration logic not documented anywhere
public. 219 commits, active, but a "v5 blueprint" and a shelved v4 suggest
architectural churn, not stability. No visible license. Revisit only if it
matures and publishes real docs.

### 5. Game Knowledge Management System / G-KMS (MDPI, schema-governed pipeline)

Fetch blocked (403); title and abstract snippet suggest a "schema-governed LLM
pipeline for executable narrative generation" — potentially relevant to
Chronicle's own schema/provenance obsession, but unverified. Flag for a direct
read later, not acted on here.

## What this changes for Chronicle

- The "GM holds a loose campaign, fills it in gradually" idea is not
  speculative — NarrativeEngine-P is a real, running, MIT-licensed
  implementation of nearly this exact idea, independently built by someone
  with no connection to this project. That's a strong signal the shape is
  sound, not just appealing in theory.
- It does not need to be "ported" wholesale (it's a full TypeScript
  self-hosted campaign platform, not a Skyrim-embeddable component), but its
  **Arc Engine** and **Agency Engine** are close enough, real enough, and
  permissively-licensed enough to justify a much closer read than anything
  else surveyed — actual code study, not just architecture-as-idea, is
  legitimate here per its MIT license.
- Combined with the already-filed provenance-anchored-intervention principle
  (report 19/20, `comparative-systems/ai-directors-and-drama-management.md`)
  and ACE-1's belief-provenance convergence (v4 pass), this is now the fourth
  independent system to converge on "engine tracks/decides, LLM only renders."
  That convergence is the strongest available argument that Chronicle's
  existing architectural instincts are right, whatever shape the new headline
  pitch takes.

## Open follow-ups

- Read NarrativeEngine-P's actual `arcEngine.ts` and `agencyEngine.ts` source
  in full (not just the architecture map) if this direction gets picked up
  seriously — this report only saw a generated architecture summary, not the
  raw code.
- Re-fetch arXiv:2502.19519 via a proper PDF text extractor (WebFetch's got an
  image-only render) and the MDPI G-KMS paper directly (403'd this pass) if
  the "GM decides vs. GM surfaces" question needs deeper grounding.
- No system surveyed here (or in prior passes) does the specific thing SkyrimNet's
  GameMaster does inside a live Bethesda-engine game — every candidate above
  is a standalone text/chat platform. The Skyrim-embedding problem (turning an
  Arc/Agency-style engine's outputs into actual quest markers or world-state
  changes) remains entirely Chronicle's own design problem, not something any
  surveyed harness has solved.
