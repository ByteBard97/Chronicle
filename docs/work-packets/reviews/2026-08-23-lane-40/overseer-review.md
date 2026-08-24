# Lane 40 — overseer review and rulings (Tier 4b design doc)

**Date:** 2026-08-23 · **Overseer:** planning agent · **Re:**
`docs/design/tier-4b-avoidance.md` (`0740c1b`)

## Verdict: **accepted.** Precise, consistent with the landed 4a
machinery, and correctly minimal.

The load-bearing decisions all hold: per-pair threshold **replacement**
(not multiplier — consistent with every existing flat tunable);
`AVOIDANCE_PROBABILITY = 0.0` making "cease" exact rather than
probabilistic; the roll untouched (no new RNG purpose — the T6b preview
verified against the landed code); no new record type (the
`encounter_rolled.threshold` delta *is* the visible weight, paired with
a rule row for the reason); cooling as continuous read-time derivation
(the three-stage severity progression is a nice consequence, not new
machinery); W5's forward-looking note (symmetric rule-18 treatment in
any future combined 4a+4b counterfactual) adopted for the future packet.

## Rulings on the open points (coordinator authority, owner-delegated)

- **O1 — `AVOIDANCE_PROBABILITY = 0.0`: accepted.** Hard guarantee;
  the rung's "encounters cease" is absolute, and the rolled-against
  row still exists (negative-first-class).
- **O2 — `AVOIDANCE_GRUDGE_THRESHOLD = 0.5`: accepted.** Placeholder;
  the ordering above `forgiveness_threshold` (0.2) is load-bearing.
- **O3 — bulk `grudges()` accessor: accepted as recommended.** Lane 43
  adds a **public** `grudges()` iterator to `SocialStateStore` rather
  than another `_grudges` private read — explicitly in its packet.
- **O4 — mutual-grudge collapse: accepted.** Asymmetric grudges produce
  symmetric avoidance; documented modeling simplification, no rung
  needs the distinction.

## Dispatch

Lane 43 (T4b.1 avoidance — rule 18, the per-pair override, the rung
with its control pair) packetized and dispatched. Tier 4b completes
Tier 4; next design cycle after it: Tier 5 (roles/vacancy) or the
north-star composition fixture.
