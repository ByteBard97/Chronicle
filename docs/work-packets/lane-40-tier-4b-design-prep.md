# Lane 40 — Tier 4b design prep: avoidance weighting (Track A, design doc)

**Status:** After **lanes 36/37** land (Tier 4a must be real before its
sibling tier is designed against it). This is a **design-doc lane — no
production code**, same shape as lanes 18/33. The Tier-4a design doc
already sketched rule 18 as a preview (T6b) — this lane turns the
preview into a ruled design with the 4a machinery in hand.

**Effort:** small-medium (the preview did the heavy thinking; this is
verification + precision).

## Context

Tier 4b (ladder, `docs/scenario-ladder.md:86-89`): **pairwise encounter
weighting** — 4a changed *who's at the table*; 4b changes *whether
tablemates actually talk*. A grudge above threshold (and not cooled)
makes two NPCs stop encountering each other. Rule 18 fills its registry
stub.

The Tier-4a design's preview (Decision T6b): a per-pair
encounter-probability override — the roll is unchanged (same roll_key,
same purpose; **no new RNG purpose**), only the threshold it's compared
against drops for an avoiding pair. Gated by `grudge_cooled`
(implemented, lane 20).

## Read first (in order)

1. `docs/design/tier-4a-schedule-write-back.md` §4 (T6b preview) — the
   starting point, incl. why 18 stayed out of 4a's rungs (T4a.2's
   byte-identical-threshold requirement).
2. `docs/scenario-ladder.md:86-89` — Tier 4b's rung text.
3. `chronicle/schedule.py` — `sample_encounters`' probability
   parameter (the seam the override threads).
4. `chronicle/social.py` — `grudge_at`/`grudge_cooled` (lane 20),
   the grudge fields.
5. Lane 36's landed overlay machinery (read the committed code — how
   the driver consults overlays per tick; avoidance is a sibling
   per-tick consultation, not a schedule change).
6. `docs/work-packets/reviews/README.md` — governance.

## Questions the doc must answer

1. **The override's exact mechanics** — where the per-pair threshold
   override is computed (driver per tick, from active grudges), its
   data shape, and how it interacts with `encounter_probability` (a
   multiplier? a per-pair replacement? pick one with rationale).
2. **The rung test's exact assertions** — T4b's rung text, made
   precise: which records prove avoidance (declined-encounter rows?
   absence of pairs?), and how the test distinguishes "avoided" from
   "rolled against" (both produce no encounter — the rolled-against
   negative row exists for one, the pair simply never appears for the
   other... or does avoidance emit its own negative row? Decide, with
   the negative-results-first-class doctrine in mind).
3. **Cooling/reheating dynamics** — when a grudge cools below the
   forgiveness floor, avoidance stops (records never deleted); when a
   fresh grievance lands, it resumes. What the trace shows for each
   transition (`rule_evaluated` rows, fired and not).
4. **Rule budget + registry** — rule 18 registration, its real toggle
   (driver-owned), the 17/20 count's headroom.
5. **Interaction with lane 37's roll-identity** — T4a.2's guarantee
   assumed byte-identical thresholds; confirm avoidance can't pollute
   it (the preview's argument, re-verified against the landed 4a code).

## Acceptance

- One markdown deliverable: `docs/design/tier-4b-avoidance.md`.
- file:line citations; recommendations + alternatives; open points at
  the end; findings list.
- Suite untouched-green (no code written).

## File boundaries

**Create:** `docs/design/tier-4b-avoidance.md`

**Do not touch:** everything else.

## Conventions

- Match the Tier-3/4a design docs' voice and structure.
- **Local commits OK** (path-scoped); never push.
- Report format: the doc + a cover note (decided / needs adjudication /
  surprises).
