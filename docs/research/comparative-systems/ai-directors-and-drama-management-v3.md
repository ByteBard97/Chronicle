---
date: 2026-08-23
sources:
  - "compass_artifact_wf-ef66dda3-ea45-52a6-940b-06f69d293976_text_markdown.md"
topic: "AI drama managers / director architectures — third independent pass"
status: filed
---

# AI Directors and Drama Management, v3

Third independent pass on the same ground as
[ai-directors-and-drama-management.md](ai-directors-and-drama-management.md)
and
[ai-directors-and-drama-management-v2.md](ai-directors-and-drama-management-v2.md).
Companion to
[21-skyrim-quest-injection-machinery-v3.md](../21-skyrim-quest-injection-machinery-v3.md),
which covers this same report's Skyrim-specific half. This pass is the
most quantitatively rigorous of the three on the LLM-narrator-drift
question — it cites specific 2024–2026 papers with hard adherence/
conflict-rate numbers rather than general claims — and adds one entirely
new, load-bearing lesson (Sid Meier's rubber-banding) absent from both
prior passes.

## What's genuinely new here (not in the first two passes)

- **[RISK — new, load-bearing] Perceived fairness is not the same thing
  as statistical fairness — Sid Meier's own account of *Civilization*'s
  combat-odds backlash.** Meier recounts that players couldn't accept
  losing a 3-to-1 battle roughly a quarter of the time, "past certain
  odds, people expected to win no matter what" — so *Civilization
  Revolution* deliberately tweaked the underlying math to make the
  player win more often than the "fair" odds would produce.
  **Conversely**, *Civ 3*'s *fair*, fixed-random-seed combat resolution
  made players feel cheated when a reloaded battle replayed identically
  — a genuinely fair system read as rigged. **Direct implication for any
  future Chronicle GM/director layer: budget for tuning to player
  *expectation*, not just to correct probability.** A grudge-driven
  reprisal that is statistically well-calibrated against tracked belief
  intensity can still read as unfair if it violates what the player
  expected going in — this is a distinct failure mode from the
  "invisible decisive variable" problem already filed in the first pass,
  and needs its own tuning pass, not just legibility.
- **[BUILD-ON] Storylet casting is named explicitly as "your highest-value
  transfer"** — sharper actionable framing than the first pass's generic
  KoDP/Wildermyth coverage. The concrete instruction: treat every GM
  intervention as a King-of-Dragon-Pass-style storylet — a
  precondition-gated situation with **role slots** — and cast the
  *actual* sifted entities (the real grudge-holder, the real target, the
  real faction) into those roles. This is what makes generated content
  read as authored, and it's the mechanism that directly fixes Radiant
  hollowness (the same "provenance for free" thesis from reports 15/17/19,
  now stated as a concrete storylet-role-casting recipe rather than a
  general principle).
- **[BUILD-ON] Robertson & Young's "Finding Schrödinger's Gun" gives a
  formal answer to *which kind* of intervention is more believable when
  a player's action threatens a planned arc.** Revising the *world's*
  possibilities (retroactively establishing that a hidden option existed)
  is empirically more believable than overriding or silently failing the
  *player's* choice. This sharpens the Mimesis/mediation finding already
  filed in the second pass — it's not just "accommodate over intervene,"
  it's specifically "if you must reframe, reframe the world's prior
  state, never the player's just-taken action."
- **[RISK — quantified, new] Hard numbers on LLM-narrator drift from a
  named 2026 benchmark, sharper than anything filed so far.** *NCP-Bench*
  (Ma et al., arXiv 2608.08160) frames interactive narrative as a
  long-horizon constraint-satisfaction problem (Invariant/Ordering/
  Achievement constraints) and stress-tests narrators with an adversarial
  player. Its results, verbatim: **"GPT-5.2 has the highest average
  interaction length (32.92 turns), but its survival rate is only 42%
  after 20 turns. Fact conflicts are the most frequent failure mode,
  occurring in 40%–68% of runs across models."** Across all models tested,
  **fewer than 14% of narrative commitments are satisfied**, and only
  ~3.5% of interactions reach 100 turns without an explicit conflict.
  Root cause named precisely: "LLMs lack explicit state-tracking
  mechanisms; they must implicitly reconstruct world state from the
  dialogue history at each turn, leading to drift," and models "yield
  rather than maintain established facts" under adversarial pressure.
  This is the single most citable piece of evidence yet filed for why
  Chronicle's symbolic-sim-as-truth architecture is necessary rather than
  merely prudent, should an LLM-narrated GM layer ever be built.
- **[BUILD-ON] Three named 2024–2026 systems solving exactly this
  problem, each a closer analog to Chronicle's own architecture than
  anything filed before:**
  - **Orchestrated Reality / WorldLines** (Huang, Li, Fang; arXiv
    2606.16014) formalizes an LLM game world as a Parameterized-Action
    POMDP where state is "a tree of canonical JSON entities" owned by a
    single orchestrating agent; the LLM only *observes* a narrative
    projection and *proposes* changes through a **Plan–Diff–Validate–Apply**
    pipeline that "commits schema-validated, content-hashed JSON deltas."
    Its own diagnosis of the field: current systems suffer "unvalidated
    writes: the model can assert any world change, so state silently
    drifts," whereas a validation guard (schema ∧ permission ∧ rule)
    "prevents prose from silently mutating state." Explicitly
    work-in-progress — even its own authors note un-schematized details
    still drift (an NPC's missing finger "swapping between left and right
    hand across a 24-turn session").
  - **Neuro-symbolic TSL automata** (Rothkopf, Zeng & Santolucito;
    arXiv 2402.16905, AAAI 2025) synthesize a correct-by-construction
    automaton from Temporal Stream Logic that decides which prompt
    modifier the LLM receives each turn, so long-horizon constraints are
    enforced by the automaton, not the model — "the automaton serves as
    the memory of the generative agent rather than the LLM itself."
    Hard number: **"our approach using TSL achieves at least 96%
    adherence, whereas the pure LLM-based approach demonstrates as low as
    14.67% adherence"** (75 games × 20 turns), with the neuro-symbolic
    agent making **zero arithmetic errors** vs. 33.67% for the pure LLM.
  - **Slice of Life** (Treanor, Samuel & Nelson; FDG 2024/2025) is the
    closest published analog to Chronicle's own committed design: it
    pairs the Ensemble/ESP social simulation (a deterministic,
    symbolically-represented "social record"; character actions chosen by
    summing weighted first-order-logic social considerations) with an LLM
    used **only for surface-text realization**. Its stated principle, near-
    verbatim Chronicle's own doctrine: "keeping the simulation state
    deterministic and free from influence by the LLM in order to maintain
    authorial control," and "the dialogue does not feed back into the
    symbolic simulation state." Its cautionary finding matters too: an
    over-engineered prompt granting the LLM more latitude *reintroduced*
    hallucination (a character "invented that it is Tuesday") — a
    reminder that the validation boundary must stay tight even when it
    seems safe to loosen.
  - **Function-calling as a hard validity gate** (Gallotta, Liapis &
    Yannakakis, IEEE CoG 2024, system *LLMaker*): the LLM emits function
    calls into a constraint-enforcing back-end rather than free-form
    artifacts. Result: function calling **never produced an invalid
    (parser/domain-failing) output**, while baseline free-form prompting
    "never complete[d] a test case without failing." This is the concrete
    mechanism (not just the principle) for letting a future Chronicle GM
    *act* on the sim — spawn a quest, trigger a faction move — without
    the LLM layer ever being capable of writing an illegal world state.
- **[DESIGN-INPUT] A concrete four-stage build sequence for a future GM
  layer, useful as a starting draft if that layer is ever scoped.** (1)
  Build the intervention layer as prerequisite-gated, entity-cast
  storylets with **no LLM at all** — benchmark: playtesters can
  unprompted explain *why* an event happened. (2) Add one legible,
  decaying pacing signal with *published self-limits* (what the director
  will never do) — benchmark/red-flag: if players discover a suppression
  exploit or report "the world feels out to get me," the causal anchor is
  too hidden. (3) Introduce an LLM GM as a **one-way, validated author**
  only — reads sifted state, writes surface text, never mutates
  belief/grudge/faction state except through a schema∧permission∧rule
  validator; benchmark: run an NCP-Bench-style adversarial stress test on
  your own content and count fact-conflicts per 20 turns. (4) Only after
  1–3 feel solid, add PaSSAGE-style player-type weighting, driven by
  *observed behavior* rather than a hidden inferred vector.

## Not repeated here

Façade's beat manager, the four-stage universal pipeline, Left 4 Dead's
pacing FSM and RimWorld's wealth-exploit, Shadows of Doubt's
provenance-anchored case generator, PaSSAGE's segment-limited results,
DODM's Anchorhead transfer failure, Mimesis/mediation's
accommodate-over-intervene doctrine, Daggerfall's Template v1.11 format,
and AI Dungeon/Hidden Door's consumer-record failures are already filed
across
[the first](ai-directors-and-drama-management.md) and
[second](ai-directors-and-drama-management-v2.md) passes and substantially
overlap this report's coverage of the same ground — not re-filed here.

## Caveats

- The 2026 papers (NCP-Bench, Orchestrated Reality) cite near-future
  model names (GPT-5.2, DeepSeek-V3.2) consistent with their stated
  dates; treat the architectural claims (validated writes,
  constraint-satisfaction framing) as robust regardless of which model
  generation is tested, but treat the specific percentages as tied to
  those model generations, not as durable constants.
- Orchestrated Reality is explicitly work-in-progress with no reported
  effect sizes — cite its architecture, not results.
- RimWorld's raid-cadence and wealth/combat-point figures are drawn from
  the community RimWorld Wiki, not a developer spec — well-corroborated
  but unofficial (same caveat as the first pass, restated here since this
  report repeats those figures independently).
