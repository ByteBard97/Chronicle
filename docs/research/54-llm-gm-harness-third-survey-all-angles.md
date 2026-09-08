---
date: 2026-09-06
sources:
  - "Deep-research report, all three prompts of notes/gm-agent-harness-research-prompts-2026-09-06.md answered in one pass (owner-run, delivered as 'LLM_Game_Master_Harness_Research.md')"
topic: "A third, independent full-scope pass answering all three GM-harness research prompts at once — pre-written campaigns, in-game asset-grounded GMs, and multi-agent/multi-timescale architectures"
status: filed
---

# LLM GM harnesses — third independent full-scope survey

A third deep-research pass, run by the owner, that answers all three prompts of
`notes/gm-agent-harness-research-prompts-2026-09-06.md` in one document rather
than one-per-prompt like the Gemini/Claude passes (reports 52/53). Cross-checked
against those — strong convergence on the shared candidates, several genuinely
new finds per angle, and this is the **first source to substantively answer
angle 3** (multi-timescale architecture), alongside report 55.

## Angle 1 (pre-written campaigns) — what's new here vs. report 52

Names **DungeonsDeep.ai** as the strongest precedent (Claude's pass, report 52,
found it too — independent confirmation), but adds real texture: its own
documentation states a dedicated rules engine "handles to hit calculation,
damage type resolution, critical logic, condition tracking... in code" while
"the AI Game Master narrates the result," with campaign memory held "at the
platform level" rather than a retrieval window. New finding not in report 52:
**no product anywhere ingests an actual copyrighted published module** (Curse
of Strahd, etc.) — every serious "pre-authored" product hand-authors its own
adventures in a platform-native structured format instead, because the D&D 5e
SRD's Creative Commons license covers rules but explicitly excludes published
settings/lore/adventures. Direct relevance for Chronicle: **this problem
doesn't apply** — Skyrim's assets are already licensed to the player, so
anchoring to Skyrim's own quest/NPC data (Chronicle's actual plan) sidesteps
the legal wall entirely.

Also new: harsher, more specific DIY-failure evidence than report 52's
benchmarks — a Hacker News account of a family's *Curse of Strahd* session
collapsing by session 4-5 over an inconsistent "how many maps does the party
own" question, concluding the fix needed is "a world ontology and being able
to CRUD facts against such an ontology" — a plain-language restatement of
exactly what Chronicle's event-sourced belief store already is.

## Angle 2 (in-game asset-grounded GMs) — what's new here vs. report 53

Confirms IntelEngine as the standout (fourth independent confirmation now,
across this report + Gemini + Claude + this session's own SkyrimNet archive
inspection). Adds real mechanistic detail on **CHIM's "Background Life"**
that reports 52/53 only touched lightly: tracked NPCs generate periodic
"inner thoughts" conditioned on last conversation, goals/personality/
relationships, location, recent activity, and area rumors; in Full Mode,
autonomous actions are drawn from an explicit set (`StayAtPlace`, `TravelTo`,
`ReturnHome`, `SpreadRumor`) on a default 5-in-game-day cadence, with hourly
GPS tracking. Documentation is candid: "NPCs make their own choices, so some
of those choices will be strange or unexpected." Also new: **PANGeA** (AIIDE
2024) — procedurally generates level content (setting, key items, NPCs,
dialogue) inside a real Unity turn-based RPG, with a novel LLM validator that
checks free-form player text against game rules to keep generation aligned —
a genuinely citable academic precedent for "grounded generation inside a real
engine," distinct from IntelEngine/CHIM's hobbyist-mod tier.

**Confirms the same gap a fourth time**: "Both systems [IntelEngine, CHIM]
author *episodes*... rather than holding and advancing a *campaign-length arc
with a premise*. There is no evidence... of a slow-tick planner maintaining a
multi-session story spine."

## Angle 3 (multi-timescale architecture) — the new territory

This is the first source in this research arc to seriously answer the
question the owner originally guessed at: does a GM need multiple agents at
different timescales? **Verdict: yes, strongly validated, with concrete named
precedents at every tier**, not just a plausible-sounding idea.

- **IBSEN** (ACL 2024, code+prompts public, `OpenDFM/ibsen`) — the single
  strongest precedent. A director agent holds a plot-objective list, writes
  per-turn scripts toward the current objective, checks completion after every
  turn via an LLM call, and **replans when a human player derails the scene**.
  Documented failure modes, directly actionable: the director sometimes
  "swallows" actor dialogue with narration; actors show a safety-bias tone
  distortion (too positive about negative events); objective-wording fixation
  causes stuck loops (patched with forced completion after 9 turns).
- **DEPS** (NeurIPS 2023) — describe→explain→replan loop for a planner/
  controller split; nearly doubled task performance in Minecraft; a learned
  Selector re-orders sub-goals by predicted completion horizon.
- **DOC / Re3** (Yang et al., ACL 2023, code public) — a Detailed Outliner
  shifts creative burden to planning, a Detailed Controller (FUDGE — a
  lightweight token-level classifier) enforces the draft stays aligned to the
  outline; +22.5% absolute plot coherence over the Re3 baseline.
- **DOME** (2024) — plans only a *rough* outline up front, expands detail
  section-by-section *after* preceding text exists, "adjust[ing] to the
  uncertainty of the previously generated stories" — the closest formal match
  to "loose evolving premise, filled in reactively."
- **Generative Agents** (Park et al., UIST 2023 — the Smallville paper) — the
  canonical binding-memory-layer reference: a memory stream scored by
  relevance/recency/importance, periodic reflection synthesizing observations
  into higher-level insight, and **explicitly multi-timescale planning**
  (daily plans → hourly schedules → 5-15 min actions). Ablation numbers
  quantify why this matters: TrueSkill 29.89 (full architecture) vs. 25.64
  (no reflection/planning) vs. 21.21 (no memory at all). Worth flagging: this
  is the same lineage Chronicle's own dashboard v1 design already drew on
  (Smallville-style JSON-snapshot + replay per prior project decisions).
- **Voyager** (MIT-licensed, code public) — automatic curriculum + skill
  library as the template for the slowest "campaign architect" tier.
- A 2026 hierarchical web-agent evaluation supplies a genuinely important
  caution: **replanning in natural language degrades goal-alignment** (60.6%
  → 56.1% after a replan) via "over-elaboration drift," while structured
  (PDDL-style) plans degrade differently but more predictably — a concrete
  argument for representing Chronicle's campaign arc as structured data, not
  prose, if it needs to be revised mid-flight.

## Recommended architecture (as given in the source report)

1. **Campaign Architect** (macro, slow tick on in-game days) — holds the
   premise as a *structured* arc object (not prose, per the replanning-drift
   finding), revises scoped sub-arcs rather than wholesale replans.
2. **Scene Director** (meso, per-scene tick) — IBSEN-style objective list with
   per-turn completion checks, explicit abandon/advance policy, hard
   narration/dialogue channel separation.
3. **Existing NPC interaction layer** (micro, fast tick) — the renderer,
   extended with a SkyrimNet-style eligibility-checked action library.
4. **Chronicle's own social store promoted to the single canonical world
   state** — the LLM never owns the ledger; an independent validator checks
   claimed state changes against it.

## Relevance to Chronicle

A fourth independent confirmation of the same gap (report 51 → 52/53 → this
report): nobody combines a persistent evolving premise, real asset grounding,
and an open license. New this time: actual concrete, citable, license-clean
architecture precedent (IBSEN, DOC, Voyager, Generative Agents — all public
code/prompts) for the specific layer that's missing. This is no longer "does
the gap exist" territory — it's "here is what to build it out of."
