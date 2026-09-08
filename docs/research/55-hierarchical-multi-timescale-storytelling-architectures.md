---
date: 2026-09-06
sources:
  - "Deep-research report on angle 3 of notes/gm-agent-harness-research-prompts-2026-09-06.md (owner-run, delivered as 'Hierarchical Storytelling Agent Architectures.md')"
topic: "Second independent deep-research pass specifically on multi-agent, multi-timescale architectures for long-horizon reactive storytelling"
status: filed
---

# Hierarchical multi-timescale storytelling architectures — second pass

A second independent deep-research pass focused entirely on angle 3 of
`notes/gm-agent-harness-research-prompts-2026-09-06.md` (report 54 answered
all three angles in one document; this one goes deeper on angle 3 alone, with
almost entirely different named precedents — strong independent corroboration
of the pattern, weak overlap on specifics, which is exactly what you want from
a second pass).

## Verdict

Confirms report 54's angle-3 verdict independently: **multi-timescale
hierarchical decomposition is validated, not speculative**, with concrete
research precedents at every tier. Chronicle's hypothesized three-layer split
(slow campaign architect / mid scene director / fast interaction renderer)
"maps almost one-to-one onto validated systems."

## New precedents this pass found (little overlap with report 54's list)

- **CoDi** (Kim et al., AIIDE 2025, public code — `Speeditidious/CoDi`) — a
  4-agent pipeline (Planner → Director → Character Agents → Editor) across
  three phases (Setup/Simulation/Editing). The Director evaluates ongoing
  character discourse against narrative goals and issues high-level steering
  instructions rather than scripting lines — and is explicitly given
  authority to **verbalize world-state changes and physical consequences**
  so actors share a non-hallucinated view of reality. Beat a baseline
  director-actor framework 61.8% of the time by eliminating plot stalling
  while preserving character agency.
- **StoryVerse** (Wang et al., Autodesk Research, FDG 2024) — introduces
  **Abstract Acts**: a high-level dramatic beat ("a character encounters a
  life-threatening predicament") with explicit logical prerequisites and
  *unbound placeholders* populated at runtime, rather than hard-coding which
  world entities fill the beat. An Act Director runs an iterative
  Plan-Generate → Plan-Review → Revise loop once prerequisites are met; when
  a player disrupts the world (e.g. kills an intended quest participant), the
  Act Director **replans around surviving entities** to still fulfill
  authorial intent. Code unreleased (research prototype only).
- **HAMLET** (Chen et al., 2025) — designed for live embodied theater, not
  games, but its core mechanism transfers directly: a Planner/Transfer/
  Advancer split where the **Advancer stays dormant during fluid player
  interaction and intervenes only on deadlock or timeout** — i.e., the
  supervisory tier is silent by default and threshold-triggered, not
  continuously steering. Actor-level cognition uses an explicit dual-process
  model (Fast/Slow/Silence per turn) to avoid uniform, robotic compliance.
- **SHOW-1 / Showrunner** (Fable Studio) — generates full episodic scripts by
  chaining prompts that simulate deliberate slow-thinking, anchored to a
  persistent multi-agent social simulation (characters accumulate long-term
  histories/goals/emotional valence). Proprietary/commercial, idea-only.
- **DOC / Re3** — same as report 54's finding (independent convergence, third
  time this specific pair has surfaced across this research arc).

## The genuinely new contribution: engineering synchronization patterns

Where this pass adds real value beyond report 54 is a named taxonomy of
*how* to keep timescales from desynchronizing — concrete enough to design
against directly:

1. **Decoupled outcome-oriented invariants.** Don't have the slow layer
   command an NPC to say an exact line or walk to an exact coordinate — that
   shatters believability and breaks brittlely if the player takes an
   unexpected path. Instead the planner asserts a **semantic goal predicate**
   ("a target's guilt is revealed to the player") and a mid-layer monitor
   (StoryVerse's Act Director, HAMLET's Transfer Agent) evaluates whether
   *any* path the player actually took satisfies it — persuasion, forensic
   evidence, blackmail all equally count. The fast layer keeps full
   improvisational freedom; only the *outcome* is checked.
2. **Neuro-symbolic state tracking via NLI graphs.** The **SDR framework**
   (Chu et al., COLM 2024) extracts every proposed line/action into
   subject-relation-object triplets and checks them against a structured
   world-state database with a natural-language-inference model — detecting
   entailment, neutral, or **explicit contradiction** (an actor asserting an
   NPC is alive when the engine registered them dead) and intercepting the
   turn *before* it renders or enters memory. This is a concrete, buildable
   mechanism for the exact "state contradiction" failure mode found
   independently in commercial products (Friends & Fables mixing up whether
   a creature was dead or alive) elsewhere in this research arc.
3. **Runtime quality gates / critic feedback loops.** SDR's own 3-stage
   pipeline: cosine-similarity screening against recent dialogue (suppresses
   repetition/circular exchanges) → a diagnostic critic scores the flagged
   line against dossiers/objectives with explicit failure feedback → a
   regeneration pass incorporating that critique, before anything commits.
4. **Information Folding** (HIPIF) — the mechanism for why a slow planner
   doesn't choke on context: micro-level dialogue collapses into an episodic
   beat when an interaction ends; beats collapse into an immutable factual
   delta when a scene ends; the campaign architect only ever reads the
   folded summary (factional balances, known secrets, updated dispositions),
   never the raw transcript. Directly solves the "how does the slow tier
   afford to look at everything that happened" problem without the
   replanning-drift risk report 54 flagged for prose-based summaries — here
   what's folded is discrete facts, not narrative prose.

## Other documented failure modes worth designing around

- **Compounding hallucination**: an agent's erroneous assertion, once
  committed to shared dialogue history, gets treated as ground truth by other
  agents within 2-3 turns, and once absorbed into *reflective* memory it
  permanently corrupts the campaign timeline for subsequent slow-planner
  passes. Mitigation stated plainly: physical facts must stay externalized in
  the game engine's own state, never sourced from unverified dialogue
  history — directly validates Chronicle's existing architecture (the C++
  bridge as ground truth, not the LLM's own narration).
- **Reflection distorts over time** — periodically synthesizing raw history into
  higher-level insight (Generative Agents' own mechanism) *increases* factual
  distortion rate over multi-session timelines relative to raw history,
  eroding distinctive traits into generic caricatures. Suggested countermeasure:
  a strict memory schema separating immutable core persona, verifiable
  physical facts (relational entity-state pairs), and subjective social
  impressions explicitly flagged as non-authoritative beliefs — which is,
  again, close to what Chronicle's belief/claim distinction already does.
- **Latency**: a 3-tier reasoning stack (plan-review-revise at the director
  level, NLI-graph checks at the actor level) can introduce multi-second
  delays in an open-world game where the player keeps moving in real time.
  Stated mitigation: the fast layer needs local fallback behavior (ambient
  barks, idle schedules) so it stays responsive while higher tiers reason
  asynchronously, plus state-conditional reconciliation before committing an
  async replan (revalidate preconditions still hold before applying it) —
  the same "menu staleness across the render hop" problem already flagged as
  open question 2 in `docs/decisions/open-questions.md`'s conversation-tier
  section, now with a named general-purpose solution pattern.
- **Control/autonomy trade-off**: too much director intervention makes NPCs
  feel like puppets; too little causes "action entropy" — after ~12-15 turns,
  autonomous agents converge on repetitive platitudes and lose dramatic
  urgency. HAMLET's answer: the supervisory tier is purely observational
  while semantic distance to the goal keeps decreasing, intervening only on
  explicit failure predicates (deadlock, loop detection, timeout) — same
  threshold-triggered pattern as the Advancer above.

## Relevance to Chronicle

Confirms report 54's recommended 3-tier architecture from an almost entirely
independent set of sources, and supplies the missing "how do you actually keep
this from desynchronizing" mechanics report 54 stated as a goal but didn't
detail as concretely: semantic-goal predicates (not imperative commands) as
the interface between tiers, an NLI-graph-style contradiction check before
anything commits to shared state, and folded-fact (not prose) summarization
feeding the slow tier. All three translate directly onto Chronicle's existing
architecture — the C++ bridge is already the "engine owns ground truth"
layer these patterns assume; the belief/claim distinction already separates
verified fact from subjective impression the way the reflection-distortion
countermeasure recommends.
