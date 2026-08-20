---
status: accepted
date: 2026-08-20
---

# 0002: Event-sourced core

## Context

Chronicle's state (beliefs with provenance, rumor content, grudges,
reputation) is exactly the kind of state where *how you got here* matters
as much as the current value — beliefs need an evidence chain, rumors need
a mutation history, grudges need an originating incident. The debug
dashboard's causality timeline and the scenario-based regression suite both
depend on being able to reconstruct that history.

## Decision

All state is derived by folding over an append-only `EventLog`
(`chronicle/events.py`). Nothing in the simulation mutates state directly;
everything happens by appending an event and re-deriving.

## Rationale

- **Provenance for free.** Talk of the Town's belief model (facets with
  value, predecessor, evidence, strength) is naturally an event fold —
  each new belief facet's predecessor link is just "the prior derived
  state." See `docs/research/` for the full citation once filed.
- **Headless testability.** Scenarios seed the log and assert on derived
  state — no running game, no mocked engine calls.
- **Debuggability.** The dashboard's causality timeline is "which events
  produced this belief," which is a log query, not a bespoke feature.
- **Replay.** Any world state is reproducible by replaying the log, which
  makes bug reports and regression scenarios exact rather than approximate.

## Consequences

- Derivation functions must stay pure (log → state), which constrains how
  the LLM tiers can be wired in: LLM output has to become a new event, not
  a direct state mutation, before it's folded in.
- Log size/performance at ~1,000 NPCs over long play sessions needs
  attention eventually (snapshotting or compaction), but is out of scope
  for the initial skeleton.
