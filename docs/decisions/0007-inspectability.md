---
status: accepted
date: 2026-08-20
---

# 0007: Inspectability

## Context

`docs/research/08-social-sim-literature-v2.md` names unclear ownership of
truth and poor legibility as recurring causes of failure across the
shipped and prototype social-sim systems it surveyed — not missing math,
missing explanations. Its worked example is the standard this ADR adopts:

```text
Mara refused Petyr because:
- Petyr owes Mara a favor from 12 April.
- Mara believes Petyr spread the warehouse rumor.
- The belief came from Leni, whose reliability Mara rates low.
- Two independent witnesses strengthened the gist but not the details.
- Refusing publicly would impose high face threat on Petyr.
- Mara has a grudge with emotional strength 0.71 and evidentiary strength 0.44.
```

`docs/vision.md` already commits to the debug dashboard (map + rumor
overlay, social graph inspector, **causality timeline**, injection
console) as a first-class deliverable, not an afterthought. That
commitment is unenforceable unless the schema itself can answer these
questions — a dashboard bolted onto opaque state can only show numbers,
not explanations.

## Decision

**Every derived social outcome must be explainable via evidence-chain
drill-down.** Concretely: for any belief, rumor, grudge, obligation
status, or reputation value Chronicle produces, it must be possible to
answer, from stored state alone (no re-simulation, no guessing):

- **Who** holds this belief/grudge/obligation, and who else is affected?
- **From what evidence** — direct observation, testimony, inference?
- **Through whom** — the source chain, including any intermediaries?
- **Since when** — first-learned and last-rehearsed timestamps?
- **Why has it changed** — the predecessor link to whatever it mutated
  from, and what mutation rule fired?

This constrains the schema (`docs/decisions/0006-data-ownership-layers.md`)
directly: `BeliefInstance`, `Evidence`, `Grudge`, and `Obligation` records
all carry the provenance fields (`predecessor_id`, `source_id`,
`evidence_type`, timestamps) needed to answer this, not because the
schema happened to include them, but because this ADR requires them.

**This is also the dashboard's core query.** The causality timeline in
`dashboard/README.md` is this drill-down, rendered — not a separate
feature to design later. Any `chronicle/` change that would make a social
outcome inexplicable (e.g., a derivation that isn't a pure function of
stored evidence) is a regression against this ADR, not just against
ADR-0006.

## Rationale

- Cheaper to build in from the schema than retrofit: the fields this
  requires (predecessor links, source chains, typed evidence) are exactly
  what event-sourcing (ADR-0002) and the five-layer model (ADR-0006)
  already produce as a byproduct — this ADR mostly requires *not throwing
  that information away* during derivation, rather than adding new
  machinery.
- Debuggability and tunability both depend on it: without drill-down,
  diagnosing "why did this NPC behave that way" during development means
  re-reading simulation code, not reading data — the same cost this
  project is trying to avoid by being event-sourced in the first place.
- It's a stronger, more specific version of the general "tooling as a
  first-class artifact" principle already in `docs/vision.md` — this ADR
  exists so that principle has a concrete, checkable definition rather
  than staying aspirational.

## Consequences

- Any derivation function in `chronicle/` that can't cite its inputs
  (an LLM call that outputs a belief update with no evidence record
  backing it, for example) violates this ADR — the hybrid-tier
  architecture's existing rule ("LLM output becomes a new event before
  being folded in," `docs/architecture.md`) already prevents this in
  principle; this ADR makes it a named, checkable requirement instead of
  an implicit one.
- The regression scenario suite (`scenarios/`) should include at least one
  scenario per belief/rumor/grudge/obligation kind that asserts the
  drill-down is answerable, not just that the final state value is
  correct — asserting *why* alongside *what*.
- `dashboard/`'s causality-timeline view can be built directly against
  layers 2-4 of ADR-0006's schema once they exist; no separate
  explanation-generation system is needed.
