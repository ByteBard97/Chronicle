---
status: accepted
date: 2026-08-20
---

# 0006: Data ownership layers

## Context

Chronicle needs a schema for beliefs, rumors, grudges, obligations, and
reputation across ~1,000 NPCs. Left unstructured, it's easy to collapse
these into one "relationship score" or one mutable NPC-knowledge blob —
`docs/research/08-social-sim-literature-v2.md` identifies this as the
single most common failure pattern across every shipped and prototype
social-sim system it surveyed: unclear ownership of truth.

That report (and, less formally, report 02) also identifies the scale
trap: a naive design that maintains or updates a complete pairwise
relationship matrix over ~1,000 NPCs is computing 999,000 ordered pairs.
Socialog's measured per-tick cost — roughly 15-25ms at 50 characters,
degrading to ~600ms at 450 — shows this becomes the bottleneck before
rendering or pathfinding does. City of Gangsters (~1,200 NPCs, a sparse
directed graph, no complete matrix) is the closest shipped precedent at
Chronicle's scale.

## Decision

**Five ownership layers, only the first of which is objective:**

1. **Canonical event log** — append-only, what objectively happened.
   Already implemented: `chronicle/events.py`'s `EventLog`
   (`docs/decisions/0002-event-sourcing.md`).
2. **Claim and variant store** — typed claims derived from events, plus
   mutated variants. Canonical claims never mutate in place; a mutation
   creates a new variant linked to its predecessor (same provenance
   discipline event-sourcing already establishes at the log level).
3. **Subjective belief store** — per-NPC `BeliefInstance` records:
   confidence, verbatim/gist strength, evidence, source, timestamps. This
   is where "what Mara believes" diverges from "what actually happened."
4. **Social state store** — sparse relationships, grudges, obligations,
   trust, reputation. Edges exist only where acquaintance, witnessed
   interaction, shared group membership, or institutional relevance
   creates them — never a dense matrix.
5. **Narrative/query layer** — story sifters, quest hooks, explanation
   views, the dashboard (`dashboard/README.md`).

**The sparse-graph rule is load-bearing, not an optimization to add
later**: layer 4 must never be implemented as, or backed by, a complete
N×N structure. Candidate generation (who could plausibly know/care about
X) comes from location, faction, kinship, workplace, existing
relationships, and recent encounters — never "all NPCs."

**Reputation is observer-local, never a global score**: `Reputation`
records are keyed `(observer, subject, context)` with Beta-distribution
`(alpha, beta)` counts and recency decay, not one number per NPC. An NPC
can be a reliable witness about tavern gossip, unreliable about finance,
and certified as a guild official simultaneously — collapsing this into
one score is the specific bug this rule prevents.

Recommended record shapes (from report 08 §§5.11, 6.10):

```text
Claim(id, kind, slots, canonical_event_id, truth_status)
BeliefInstance(holder_id, claim_id, variant_id, confidence, uncertainty,
                verbatim_strength, gist_strength, source_summary,
                first_learned, last_rehearsed)
Evidence(id, belief_id, evidence_type, source_id, predecessor_id,
         location_id, timestamp, strength)
RumorState(npc_id, claim_variant_id, stage, last_heard, last_told,
           exposure_count, distinct_source_count)

Obligation(id, issuer, debtor, beneficiary, action, condition, deadline,
           status, witnesses, sanctions, excuse, created_at, fulfilled_at, violated_at)
Grudge(holder, target, source_event_id, severity, grievance_type,
       emotional_strength, evidentiary_strength, last_rehearsed, forgiveness_threshold)
Reputation(observer, subject, context, beta_alpha, beta_beta,
           direct_count, witness_count, certified_count, uncertainty, last_updated)
```

Obligations, grudges, and reputation stay three separate record kinds —
never merged into one relationship score, per the same failure pattern
this ADR opens with.

## Rationale

- Matches Chronicle's existing event-sourcing discipline (ADR-0002):
  layer 1 is the log; layers 2-4 are progressively more derived, more
  observer-relative views over it, computed lazily rather than eagerly
  maintained.
- The sparse-graph rule is the only documented fix for the scale trap
  every shipped/prototype system in report 08 hit in some form; adopting
  it from the schema stage avoids a costly later rewrite.
- Keeping obligations/grudges/reputation separate is cheap now and
  expensive to retrofit — merging them is the natural shortcut under
  deadline pressure, so this ADR exists partly to make that shortcut
  visibly wrong later.

## Consequences

- `chronicle/`'s belief and social-state modules (not yet built) must be
  designed against these five layers from the start — this is the schema
  work that precedes any tier-1 (math) simulation logic.
- Every layer above the event log needs a lazy/cached derivation strategy,
  not an eager one — the performance budget in report 08 §8.7 (full
  evaluation for the active scene, eligibility-only for nearby NPCs,
  scheduled batch for offscreen NPCs, no global computation for
  reputation) should inform `chronicle/`'s tick loop once it exists.
- This ADR and `docs/decisions/0007-inspectability.md` are companions:
  layers 2-3 in particular exist specifically so that the inspectability
  requirement (evidence chains, provenance) is answerable from the
  schema, not bolted on afterward.
