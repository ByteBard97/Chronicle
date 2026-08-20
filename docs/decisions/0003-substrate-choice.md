---
status: DRAFT
date: 2026-08-20
---

# 0003: Build against Skyrim directly, or prototype elsewhere first?

## Status

**DRAFT — open.** Do not treat this as decided. Pending research findings;
see `docs/research/00-index.md` and `docs/decisions/open-questions.md`.

## The tension

**Case for prototyping elsewhere (RimWorld, or from scratch in 2D):** a
prior analysis argued that Skyrim's engine constraints, mod-installation
friction, and the difficulty of iterating on simulation logic against a
live game make it a poor *laboratory*. The claim: "Skyrim is the
destination, not the laboratory" — validate the belief/rumor/grudge model
somewhere cheap to iterate on, then port the proven design to Skyrim once
it's a rendering/integration problem rather than a design problem.

**Case for targeting Skyrim directly (the current working plan):**

- The external-service architecture (`0001`) means most of the engine's
  constraints don't apply — Chronicle isn't fighting Papyrus's execution
  model for its actual simulation logic, only for the thin adapter seam.
- Mantella and CHIM (and other AI-NPC mods) already provide a maintained
  presentation layer — dialogue rendering, TTS, LLM plumbing — that a
  from-scratch or RimWorld prototype would have to build or fake anyway.
  Building against Skyrim means that layer is free.
- A prototype's validity is itself uncertain: dynamics that work in a toy
  2D world (encounter rates, social graph density, schedule-driven contact
  patterns) may not transfer, making the "prove it elsewhere first" step
  partially wasted work.

## What would resolve this

Findings from `docs/research/` on:
- How much real integration surface exists in Skyrim's modding ecosystem
  right now (event hooks, injection points) — if it's rich and stable, the
  "engine fights you" premise weakens.
- Whether any existing mod's extension API is solid enough to build against
  without forking, which would substantially lower the cost of targeting
  Skyrim directly.

## Decision

_Not yet made._ Update this ADR (status → accepted, with a rationale
section) only after proposing the change and getting explicit approval —
do not resolve unilaterally.
