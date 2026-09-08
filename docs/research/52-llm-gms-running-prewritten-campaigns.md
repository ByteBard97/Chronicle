---
date: 2026-09-06
sources:
  - "Gemini deep research report, prompt 1 of notes/gm-agent-harness-research-prompts-2026-09-06.md (owner-run, delivered as 'Pre-Written Campaign LLM GMs.md')"
  - "Claude deep research report, same prompt (owner-run, delivered as 'claude - gm prompt1.md')"
topic: "Does real precedent exist for an LLM Game Master running an existing, pre-written tabletop campaign module (Curse of Strahd, Tomb of Annihilation, etc.), improvising around player deviation while staying anchored to the module's fixed plot/NPCs/locations?"
status: filed
---

# LLM GMs running pre-written campaigns — two independent passes

Two independent deep-research passes (Gemini, Claude) answering prompt 1 of
`notes/gm-agent-harness-research-prompts-2026-09-06.md`, run by the owner during
the 2026-09-06 GM/storyteller-pivot brainstorm. Both converge hard on the same
verdict and the same underlying engineering principle, despite citing almost
entirely different specific projects — strong independent confirmation.

## Verdict

**Yes, genuine, shipping precedent exists.** Running a fixed module is a
different, harder problem than freeform generation (fixed plot/NPC/location
truths that must not be contradicted, player deviation that must be absorbed
without railroading or losing the thread), and multiple real projects — some
academic and peer-reviewed, some shipped commercial products — solve it well
enough to be worth studying directly.

## The one load-bearing convergent principle (both reports, independently)

**Put rules, dice, state, and "has this beat fired" in deterministic code;
confine the LLM to intent-parsing and prose narration.** Every serious
implementation in both reports converges on this split — it is the same
"engine decides, LLM renders" pattern already found in NarrativeEngine-P
(report 51), ADR-0011's player-dialogue design, and the conversation-tier
design notes. Concretely this usually takes a 3-phase turn pipeline: (1) an
LLM pass converts free-text player input into a typed action/intent, (2) a
deterministic engine resolves it (dice, state, rule checks, spoiler-gating),
(3) a second LLM pass narrates the outcome in prose, masked to hide anything
not yet revealed.

## Strongest candidates found

| Project | License | What it actually does | Source |
|---|---|---|---|
| **SENNA / ChatRPG v3** (Aalborg Univ., ACM IUI '26 paper) | Base repo (`KarmaKamikaze/ChatRPG`) MIT; SENNA/v3 branch existence unconfirmed | Peer-reviewed, user-studied (12 participants). 5 agents: **Scribe** compiles a module into a "Narrative Graph" (nodes = milestones with status Completed/Ongoing/undiscovered, edges = conditions, guaranteed path to an End node); **Examiner** gates each player action against current graph state; **Navigator** advances/branches the graph; **Narrator** improvises prose within those bounds; **Archivist** updates memory. Empirically tested 4 deviation-handling strategies — **world-logic-grounded redirection (in-world consequences, NPC influence) preserved coherence without immersion cost; hard denials were the least-liked, "repeatedly described as frustrating."** | Claude |
| **shoemoney/eldritchdm** | Apache-2.0 | Discord bot, explicitly loads named commercial modules (`/load_adventure id:CoS` — Curse of Strahd, Lost Mine of Phandelver, Tomb of Annihilation) into a dedicated SQLite rules DB (`dm20-protocol`, 97 MCP tools covering full 5e SRD mechanics); LLM narrates only, cannot touch state directly. | Gemini |
| **Bobby-Gray/open-tabletop-gm** (+ `claude-dnd-skill`) | AGPL-3.0-or-later | Parses raw PDF/DOCX/Markdown into a lazy-loaded act/chapter tree + typed-edge relationship graph (NPCs/factions linked with debts, allegiances, grievances, each edge anchored to a verbatim source quote); steers deviation via background faction clocks/world pressure, not hard barriers — same finding as SENNA's user study, independently arrived at. | Both (independently found by each pass) |
| **AiChatTrpg** | Apache-2.0 | Built-in module parser turning a PDF/markdown adventure into scenes/NPCs/clues/triggers; scene-scoped context injection (only the active scene's data enters the prompt, not the whole book) plus a JSON ledger + rolling narrative summaries for cross-scene continuity. Pre-alpha. | Both |
| **seewhydee/my-gm-is-ai** | GPL-3.0 | Cleanest 3-phase pipeline (typed-JSON intent → deterministic Python engine → masked prose narration); explicit public/hidden data partition so secrets can't leak before an engine check unlocks them. | Gemini |
| **Familiar** (Foundry VTT) | Commercial, $6/mo | Most mature *shipped* product: reads an imported published D&D adventure's actual Foundry journals/actors/scenes (doesn't re-chunk a PDF, rides on Foundry's own structured import), enforces 5e combat rules in code the model can't touch. Good UX reference to trial cheaply. | Claude |
| **dm20-protocol** | Open (MCP server) | Loads named 5etools modules (CoS, LMoP, HotDQ, PotA, OotA, ToA, WDH, WDMM, BGDIA), auto-populates only the current chapter's entities, hides later chapters until progression — explicit spoiler/chapter gating. Module-running layer is roadmap, not yet validated. | Both |
| **John Polacek's D20Adventures** | — | Human-authored adventures as JSON encounter-node graphs with transition logic — clean DIY pattern, but documented the recurring failure directly: the LLM sometimes just doesn't obey its own transition rules. Useful as a "even a good graph still leaks" cautionary data point. | Gemini |

## Sobering data point neither pass sugarcoats

Two 2026 benchmarks quantify how hard "staying faithful to the script" actually
is: **NCP-Bench** (ICML 2026) found the best frontier model survived only
**42% of runs at 20 turns** with 40-68% fact-conflict rates across models, and
a hierarchical-memory baseline that cut conflict rates to 4% *pushed
player-input conflicts up to 38%* — no free lunch. **CoC-Seduce** (adversarial
Call of Cthulhu benchmark, 20 models, 5,376 samples) found "reasoning-enhanced
models offer no consistent robustness advantage" against players talking the
GM out of its own rules ("Seduced by the Narrative"). Both cited by the Claude
pass only — worth treating as a realistic ceiling on how far prompting alone
gets you, reinforcing why the deterministic-engine-owns-state split above
isn't optional polish, it's load-bearing.

## Relevance to Chronicle

This whole prompt was about running a *pre-written* module — not directly
Chronicle's use case (Chronicle isn't running Curse of Strahd, it's running
"Skyrim" as the fixed setting). But the architecture pattern transfers almost
exactly: **Skyrim's existing assets/lore/geography are the "pre-written
module,"** and a Chronicle GM agent has the identical problem these systems
solve — stay anchored to what's real and already true (existing NPCs,
locations, established lore) while improvising reactively and never
contradicting canon. SENNA's Narrative Graph (named milestone nodes +
conditioned edges + guaranteed path to resolution) and its empirical
"consequences beat hard denial" finding are the two most directly reusable
ideas — the second one is *already* Chronicle's own architecture, since NPCs
surfacing consequences through belief/rumor/grudge state is exactly the
"world-logic-grounded redirection" SENNA found players preferred.

## Licensing note

Apache-2.0 (`eldritchdm`, `AiChatTrpg`) and MIT (`ChatRPG` base) are genuinely
reusable as code, not just ideas. AGPL (`open-tabletop-gm`) and GPL
(`my-gm-is-ai`) are copyleft — ideas freely reusable, code reuse would carry
license obligations. None of this changes the earlier finding that
SkyrimNet/IntelEngine specifically ship no license at all.
