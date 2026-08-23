# Lane 23 — Tier 3 L-D: tell-decision gate (Track A, sim substrate)

**Status:** Ready to start immediately. L-A landed (`8a83e41` — registry
core, `_evaluate_rule` emission, `disabled_rules`). Design decisions R9
and R10 are ruled and final (design doc §5); O5 is ruled (rule name in
`rule`, sub-reason in the paired `rule_evaluated`'s `inputs`). Lanes
24–26 follow serially after this one (all touch `driver.py`).

**Effort:** medium (gate wiring + rung test).

## Context

T3.4 (frozen, `docs/scenario-ladder.md:75`): two NPCs learn the player's
secret; one is kin-motivated to keep it. Assert: the motivated holder
**never transmits — and the trace shows the tell-decision rule declining
by name each opportunity**; the unmotivated holder transmits on normal
keyed rolls. This lane is also the M4 dashboard dependency:
`transmission_declined` (schema-reserved since M2) gets its producer —
the encounter feed's fourth outcome state finally has real rows.

## Read first (in order)

1. `docs/design/tier-3-rule-registry-and-tell-decision.md` §5 (R9/R10)
   — the ruled design. Deviations come back as findings.
2. `docs/scenario-ladder.md:75` — the frozen rung text.
3. `docs/frame-log-schema.md:121` — `transmission_declined`: `claim_id`,
   `teller_id`, `hearer_id`, `location_id`, `rule` (string),
   `roll_key | null`. The null-roll_key case is exactly the
   deterministic-decline path (R10 stage 1).
4. `chronicle/rules.py` — the lane-19 machinery you're building on
   (`Rule`, `RuleContext`, registration idiom, the StubRule your rule
   replaces). `chronicle/driver.py` — `_propagate_on_encounter`
   (:513-552: resolve → mutation → retell; the gate inserts between the
   first two), `_evaluate_rule`, `_propagating_claims` (:519 — the
   claim-ordinal discriminator).
5. `chronicle/rng.py:44` — `TELL_DECISION` is registered; no new
   purposes.
6. `scenarios/test_tier2_carrier.py` — the newest rung-test idiom.
7. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions (coordinator-set, 2026-08-23)

- **Placement (R9, ruled):** after `teller_and_hearer` resolves a real
  transmission pair, **before** the mutation decision. Nothing else in
  the encounter flow changes — resolution, nothing_salient, and
  re-hearing paths are untouched, and **T2.3's resolution is never
  gated** (a contested hearing is not a telling).
- **Stage 1 — deterministic motive decline:** the driver assembles
  caller-supplied context (the claim's privacy classification — a new
  construction-time mapping in the `mutation_candidates` idiom; the
  teller's relevant social state, caller-looked-up — the T2.3 lesson:
  no social lookups inside claims operations). Motive met → decline
  **always, no roll**: `transmission_declined` with `rule` = the rule
  name and `roll_key = null`.
- **Stage 2 — keyed roll:** purpose `tell.decision`; roll_key members
  per ADR-0009 with `site = location_id`, `participants =
  [teller_id, hearer_id]`, `draw =` the claim's ordinal in the
  `_propagating_claims` loop. Threshold `TELL_PROBABILITY = 1.0` as the
  construction-time default (migration-safe: today every resolved
  transmission happens); fixtures lower it per-run.
- **O5 (ruled):** `rule` carries the rule name exactly; any sub-reason
  (e.g. kin-motive) goes in the paired `rule_evaluated`'s `inputs`.
- **Both outcomes emit `rule_evaluated`** (lane-19 machinery) — "each
  opportunity" is visible even when the tell proceeds.
- **The rule registers as rule 15** replacing the stub; default enabled.
  Behavior at `TELL_PROBABILITY = 1.0` with no privacy mappings is
  identical to today (the 196-test battery is the regression proof).

## Task

1. The tell-decision rule in `chronicle/rules.py` (replacing the
   rule-15 stub): two-stage evaluation per the pins.
2. Driver wiring: the gate in `_propagate_on_encounter`; the
   construction-time privacy/motive mapping; `transmission_declined`
   emission (scripted-wrapper idiom, field-for-field §4:121).
3. `scenarios/test_tier3_tell_decision.py` — the T3.4 rung: two
   informed NPCs, one kin-motivated. Assert: motivated holder has zero
   `transmitted` records and a `transmission_declined` row **naming the
   rule** for every encounter opportunity (scan all ticks); the
   unmotivated holder transmits normally; both decline and proceed
   outcomes emit `rule_evaluated`; the motivated decline carries
   `roll_key: null`.
4. Determinism: same seed → same rolls; no behavior change at defaults
   (the full suite unedited).

## Acceptance

- `uv run pytest -q` green (196 + your new tests), `uv run ruff check .`
  clean.
- `transmission_declined` records match §4:121 field-for-field; the
  deterministic-decline row carries `roll_key: null`.
- The rung's "declining by name each opportunity" assert passes as
  written above.
- No behavior change at defaults; no new RNG purposes; no frozen-doc
  edits (the schema row is already reserved).

## File boundaries

**Create:** `scenarios/test_tier3_tell_decision.py`

**Edit:** `chronicle/rules.py` (the rule), `chronicle/driver.py` (gate +
mapping + emission), `chronicle/propagate.py` (context assembly only —
keep it lookup-pure)

**Do not touch:** frozen/coordinator docs, `chronicle/rng.py`,
`chronicle/social.py` (lane 20's file), other `scenarios/` files,
`dashboard/`, `runs/`

## Conventions

- Match the driver/rules idiom; named constants (`TELL_PROBABILITY`)
  with rule citations.
- **Local commits OK** (path-scoped, explicit adds); never push.
- Existing test assertions immutable; conflicts are findings.
- Report format: delivered, acceptance per criterion with command
  tails, findings list.
