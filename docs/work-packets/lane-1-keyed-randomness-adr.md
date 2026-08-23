# Lane 1 — Keyed-randomness ADR

**Status:** Ready to start. No dependencies. Deliverable is one new file.
**Effort:** small (a decision document; no code changes).

## Context

Chronicle is a deterministic social-simulation engine for Skyrim (Python,
`chronicle/`). The dashboard build plan requires a **derivation trace** that
records every random roll's value — which is only meaningful if rolls are
*keyed*: reproducible independent of iteration order, so two runs with the
same seed roll identically, and a fork re-sim diverges exactly where inputs
diverge.

Today the codebase has exactly one dice roll:
`chronicle/schedule.py`'s `sample_encounters()` (lines ~73–95) — a
caller-supplied `random.Random` consumed **sequentially**
(`rng.random() < encounter_probability`). Sequential consumption means any
upstream change (an added NPC, a new roll site) silently shifts every
downstream roll. `chronicle/propagate.py` has no randomness today but will
need keyed rolls when Tier 2/3 machinery lands (variant resolution,
tell-decision gating).

## Read first (in order)

1. `docs/scenario-ladder.md` §5 (the open decision this ADR closes) and §1
   (design principles, incl. keyed randomness).
2. `docs/dashboard-build-plan.md` §1 prerequisite 2 and §2 M0.
3. `chronicle/schedule.py` (the roll site) and `chronicle/propagate.py`
   (to confirm what's pure).
4. Any existing ADR in `docs/decisions/` for format (frontmatter:
   `status`/`date`; sections Context / Decision / Consequences).

## Task

Write `docs/decisions/0009-keyed-randomness.md`:

- Decide the keying scheme — the ladder's design principle sketches
  `hash(seed_id, purpose, tick, site, participants)`; evaluate that against
  alternatives (e.g., per-entity substreams à la counter-based PRNGs) and
  pick one. State the hash function, the key components and their order,
  and how new roll sites get `purpose` strings.
- Specify the migration for `sample_encounters()` from sequential
  `random.Random` consumption to keyed rolls (interface change:
  callers pass `seed_id`, not an `rng` instance).
- Consequences must cover: the scenario tests' determinism guarantee
  (`schedule + rng seed always reproduces`), fork re-sim divergence
  semantics, and what the trace records per roll (key components + value).

## Acceptance

- ADR is decision-complete: Lane 4 can implement `schedule.py`'s rework
  from the ADR alone without asking questions.
- Status `accepted` (the coordinator adjudicates disagreements).

## File boundaries

- **Create:** `docs/decisions/0009-keyed-randomness.md` only.
- **Do not touch:** any `.py` file, `docs/ui-spec.md`,
  `docs/scenario-ladder.md`, `docs/ui-doctrines.md` (frozen), other lanes'
  files.

## Conventions

- Do **not** `git commit` — leave the file for the coordinator.
- Note in your final report anything you found in the read-first docs that
  contradicts your decision (that's a finding, not a blocker).
