---
date: 2026-09-06
sources:
  - "Claude deep-research report on angle 3 of notes/gm-agent-harness-research-prompts-2026-09-06.md (owner-run, delivered as 'claude gm prompt3.md')"
topic: "Third independent deep-research pass specifically on multi-agent, multi-timescale architectures for long-horizon reactive storytelling"
status: filed
---

# Multi-timescale agent decomposition — third pass (Claude)

A third independent pass on angle 3 (reports 54 and 55 were the first two).
Strong convergence on the verdict, a different but overlapping set of named
precedents (HAMLET and StoryVerse now confirmed by two of the three passes),
and — most valuable — a direct, sourced **correction** to a claim implicit in
how this research arc has been citing things.

## The correction worth flagging

**ChatRPG / "Static vs. Agentic Game Master AI" (arXiv:2502.19519) — the paper
underlying SENNA, which report 52 named the strongest precedent for angle 1
(pre-written campaign fidelity) — is explicitly confirmed here to NOT be a
multi-timescale design.** Its Narrator/Archivist split is a foreground/
background *labor* division (storytelling vs. memory-keeping), both running
once per player turn, with no campaign-architect/scene-director separation at
all. This doesn't contradict report 52 (that report cited it for module
fidelity, a different axis, not for timescale hierarchy) but it's worth being
precise: **ChatRPG's real contribution is the empirical result that agentic
beats static** (counterbalanced N=12 study, 9 of 14 constructs significant,
strongest effect on Mastery 0.68→2.33 p=0.004), not evidence for the
multi-timescale hypothesis specifically. Don't cite it for both.

## Verdict

Confirms reports 54/55: hierarchical, multi-timescale decomposition is
**well-established, not speculative** — both in the general LLM-agent
literature (plan-then-execute, manager/worker, slow/fast dual-process
designs) and in interactive-narrative work specifically, with fully-realized
non-LLM ancestors (Façade, Left 4 Dead's AI Director) proving the pattern
predates LLMs by two decades.

## Strongest precedent named here: HAMLET

Same system report 55 found, with more architectural precision. Confirmed:
**peer-reviewed at ICLR 2026** (not just a preprint) — the most rigorously
validated candidate in this entire research arc on the "is this real
research" axis.

**Correction (2026-09-06, verified by directly cloning the repo):** the
"open-source, ships code + models, full evaluation suite" claim below is
**false as of this writing**. `github.com/Tsumugii24/HAMLET` contains only a
`README.md` and a poster image — no code, no `requirements.txt` or
`.env.example` despite the README's own Quick Start referencing them, no
working leaderboard link, no releases. The README's MIT license badge has
nothing behind it to license. This is a paper landing page, not a code
release yet, regardless of the "Official code implementation for HAMLET"
tagline. Treat HAMLET as **architecture-only precedent** (the paper itself,
arXiv:2507.15518, is real and citable) — there is currently nothing to run,
study line-by-line, or build on directly. Its own README lists "Upcoming
Features & Contributions," so recheck later.

**Addendum, from directly viewing the paper's ICLR poster (not just the
abstract):** the *research* itself is real and well-evaluated, even though
the code isn't public — worth separating those two facts. Concrete details
worth stealing as design ideas (all primary-source, from the poster):

- Their plot-beat unit ("**Point**," e.g. "The King's Gaffe," "Crime
  Exposed") carries a completion flag and gets decomposed by a **Planner**
  into a chain of finer beats (a "beat chain"); a separate **Narrator Agent**
  independently adjudicates whether physical prop interactions succeed or
  fail against tracked absolute/relative positions — the same
  goal→concrete-steps→grounded-in-real-state pattern found everywhere else
  in this research arc, plus a nice touch: each Point's blueprint entry shows
  per-character relationship-delta arrows directly.
- Character profiles are **Speech Style / Goal / Relationships / Memory** —
  structurally identical to ADR-0011's voice card and SkyrimNet's NPC bios.
  A fifth independent convergence on the same representation shape.
- The **PAD (Perceive And Decide) module** gives each actor a dead-simple
  per-turn three-way choice before acting at all: **Silence / Fast / Slow**.
  A good minimal template for "does this NPC even react right now."
- **Real, measured ablation numbers, not just qualitative argument**: adding
  a Reviewer critique pass to the offline blueprint improved win-rate scores
  by roughly +7 to +12 points across every tested base model (Qwen3-8B,
  GPT-4.1, Gemini-2.5-pro, Claude-4-sonnet) — genuine quantified evidence for
  the "critic gate" pattern reports 54/55 only argued for qualitatively.
- A real evaluation leaderboard exists (HAMLETJudge, a dedicated critic
  model), scoring Character/Narrative/Interaction dimensions across English
  and Chinese for a wide range of frontier and open models — Claude-4-sonnet
  variants score highest in both reasoning and non-reasoning categories.
- **A latency-vs-immersion penalty curve, explicitly modeled** — named
  thresholds ("tolerable," "attention lost") per model plotted against
  response latency in seconds. Chronicle doesn't currently have this framing
  and should: the entire point of the Mac Mini hardware is real-time
  response, and this is a template for quantifying how much latency budget
  actually exists before players disengage, rather than assuming a number.

Offline "campaign architect": actor designer + plot designer + reviewer feed
a director agent that produces a structured narrative blueprint from a
simple topic. Online: planner/transfer/advancer steers per-actor agents,
each with its own adaptive fast/slow reasoning module — a within-turn
timescale split *inside* the fast tier, not just between tiers. Actor
actions changing scene/prop state are broadcast to related actors, updating
what they know — a lightweight shared-state consistency mechanism. **Verify
license before reusing code/weights** (domain is live embodied theater, not
games — the arc→scene→line mapping to a TTRPG GM is a well-supported
inference, not a like-for-like deployment).

## Other genuinely new finds

- **Dramatron** (CHI 2023, Google DeepMind lineage) — the foundational
  hierarchical LLM story generator, and the cleanest possible illustration of
  Chronicle's own "loose premise → gradually filled detail" idea: three
  layers (log line → characters/plot-outline/locations → scene dialogue),
  coherent because each layer's output becomes the next layer's prompt
  (pure prompt chaining, no fine-tuning). Includes a simple, reusable
  repetition-detection safeguard (block-frequency counting, resample on
  loop). Co-creative offline tool, not autonomous/reactive — an idea
  template, not an architecture to run live.
- **Story2Game** (arXiv:2505.03547) — directly relevant given Chronicle
  already has a live C++ game state: generates a story, then annotates every
  action with **preconditions and effects** compiled into executable
  engine-side checks (location/inventory/attribute), supports dynamic
  action generation when a player goes off-script, and does retroactive
  game-logic repair. This is close to a ready-made pattern for binding GM
  narrative intent to Chronicle's own engine-side validation.
- **Microsoft Research's "Player-Driven Emergence"** (IEEE CoG 2024) — a
  fixed-premise, free-NPC-interaction testbed where GPT-4 converts play logs
  into a narrative node-graph and identifies **emergent nodes**: 53 total (43
  unique) player-created narrative beats across 28 players, not in the
  designer's intended graph. Both validates the "loose premise, player fills
  detail" design directly and names the real failure mode to guard against:
  "without human intervention, the generated stories easily devolve into a
  limited set of patterns."
- **A useful counter-intuitive nuance from Memento (§6.3)**: a *fast,
  non-deliberative* planner paired with a strong executor beat a *slow,
  deliberative* planner (70.9% vs. 63.03% accuracy), because the slow planner
  "compress[ed] solutions into a single, convoluted chain of thought" while
  the fast one decomposed cleanly. Design lesson: the campaign-architect
  tier's job is producing a **concise, structured** plan, not a long reasoning
  dump — bigger/slower isn't automatically better for this role.
- **Concrete, measured drift-reduction numbers** from Magnet: a critic that
  gates each proposed action for relevance/consistency against a shared
  world state, reporting 41% fewer annotated errors and 50% fewer
  hallucinations at 100 pages vs. a single-model baseline — a rare case of an
  actual quantified benefit for the "critic gate" pattern also found (without
  numbers) in reports 54/55.
- **Falsifiable Commitment Planning** (arXiv:2607.24167) — the crispest
  one-line framing of the consistency problem found across all three angle-3
  passes: "stable long-horizon agents need plans that know when they are
  wrong," so a fast layer can detect it's "following a plausible but stale
  routine after the active plan has become invalid."
- **Façade and Left 4 Dead's AI Director**, described with real specificity
  (27 authored dramatic beats over thousands of ABL reactive behaviors;
  Build-Up→Sustained-Peak→Peak-Fade→Relax states driven by a continuously
  measured per-survivor "intensity" signal) — confirms the timescale split
  is a decades-old, non-LLM-specific game-AI pattern, not a fad.

## Relevance to Chronicle

A third independent validation of the three-tier hypothesis, with HAMLET now
confirmed by two of three angle-3 passes as the strongest single precedent —
about as much convergent confidence as this kind of research can produce.
The genuinely actionable new pieces: Story2Game's precondition/effect
grounding maps almost directly onto binding a GM's proposed beats to
Chronicle's own live C++ state; the Memento finding argues for keeping the
campaign-architect's output compact and structured rather than assuming a
bigger/slower model produces better arcs; and the emergent-node finding
(Microsoft Research) gives a concrete metric — track how many player-driven
beats fall outside the architect's own graph — for detecting the "devolves
into repetitive patterns" failure mode before it ships.
