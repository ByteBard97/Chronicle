---
status: proposed
date: 2026-08-22
---

# 0009: Keyed randomness for reproducible, fork-safe rolls

## Context

The dashboard's derivation trace (docs/ui-spec.md §1.1) records every random
roll's value so that replay, run comparison, and the first-divergent-roll
finder (ui-spec §3.9) work. That is only meaningful if rolls are **keyed**:
each roll's value must be a pure function of its context, independent of how
many rolls happened before it.

Today the codebase has exactly one dice roll —
`chronicle/schedule.py`'s `sample_encounters()` consumes a caller-supplied
`random.Random` **sequentially** (`rng.random() < encounter_probability`).
Sequential consumption means any upstream change — an added NPC, a new roll
site, a reordered iteration — silently shifts every downstream roll, and a
fork re-sim (ui-spec §3.1: re-simulate from tick T with an injected event)
cannot diverge exactly at the injected difference; it diverges everywhere
after the first shifted draw. Tier 2/3 machinery (variant resolution,
tell-decision gating) will add roll sites in `propagate.py`; the scheme must
cover them without redesign.

The scenario ladder (§1 design principles, §5) sketches the shape:
`hash(seed_id, purpose, tick, site, participants)`. This ADR makes it
concrete.

## Decision

**Every random draw is derived from an explicit key; no sequential stream
state exists anywhere in the sim.**

1. **Roll function.** A new module `chronicle/rng.py` provides:

   ```
   roll(seed_id, purpose, tick, **key_parts) -> float   # uniform [0, 1)
   ```

   Implementation: SHA-256 over a canonical serialization
   `seed_id | purpose | tick | part1=value1 | part2=value2 | …`
   (parts sorted by name; lists serialized sorted and comma-joined), first
   8 bytes as uint64, divided by 2⁶⁴. SHA-256 truncation is statistically
   adequate for simulation rolls and needs no dependency.

2. **Purposes are a registry.** Each roll site gets a dotted purpose string
   defined once in `chronicle/rng.py` (e.g. `ENCOUNTER_SAMPLE =
   "encounter.sample"`; later `mutation.slot`, `tell.decision`). No ad-hoc
   purpose strings at call sites.

3. **Interface migration.** `sample_encounters()` takes `seed_id: str`
   instead of `rng: random.Random`; its per-pair roll key is
   `purpose=ENCOUNTER_SAMPLE, tick=tick, location=location_id,
   pair=(npc_a, npc_b)` (pair order-normalized). Callers (driver, scenario
   tests) pass the run's `seed_id` — which the frame-log envelope already
   carries from record one.

4. **Trace records carry the key.** Each roll emitted to the derivation
   trace records `(purpose, tick, key_parts, value)` (and the threshold
   where one exists), so the merge-scan first-divergent-roll finder compares
   values for identical keys across runs.

## Alternatives considered

- **Sequential `random.Random` (status quo).** Rejected: fragile to any
  upstream change; fork divergence is unanalyzable.
- **Per-entity substreams** (`Random(hash(seed, npc_id))`). Stable to other
  entities being added, but encounter rolls are pairwise and per-tick — a
  per-entity stream still shifts when that entity's own roll count changes.
  Rejected.
- **Counter-based PRNG (Philox/Threefry).** The principled choice for
  large-scale keyed randomness, but it adds a dependency or a nontrivial
  implementation; SHA-256 truncation is sufficient at our roll volumes
  (≤10⁶ rolls/run). Rejected as unnecessary today; the `chronicle/rng.py`
  seam allows swapping the primitive later without changing call sites.

## Consequences

- Replay is exact: same `seed_id` + same inputs ⇒ same keys ⇒ same values.
- Fork divergence is analyzable: two generations differ exactly at keys
  whose inputs differ; T4a.2's counterfactual assertion and ui-spec §3.9's
  merge-scan finder both reduce to comparing values for equal keys.
- Scenario tests keep their determinism guarantee, now via keying rather
  than stream order — stronger, and robust to fixture growth.
- Cost: one SHA-256 per roll — negligible at 10⁵–10⁶ rolls per run.
- `chronicle/rng.py` is the single choke point: statistical quality,
  serialization canonicalization, and future primitive swaps live there
  alone.
