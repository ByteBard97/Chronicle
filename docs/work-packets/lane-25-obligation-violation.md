# Lane 25 — Tier 3 L-E: obligation violation cascade (Track A, sim substrate)

**Status:** Serial after **lane 24** (driver.py contention, per the
design doc). Everything else unblocked: design R8 ruled, O3 ruled
(`victim_id == holder_id` documented bypass in `form_grudge` —
harm-to-self is rule 8's base case).

**Effort:** small-medium (cascade + bypass + rung test).

## Context

T3.3 (frozen, `docs/scenario-ladder.md:74`): three favors; invoke one
(consumed); refuse one. Assert: refusal fires the violation wiring —
grudge + reputation evidence row for observers present. The substrate
exists (`issue/fulfill/violate_obligation` wrappers emit
`obligation_issued`/`obligation_resolved`); this lane adds the cascade
and the ruled bypass.

## Read first (in order)

1. `docs/design/tier-3-rule-registry-and-tell-decision.md` §4 (R8) and
   the ruled O3 (overseer review, `reviews/2026-08-23-lane-18/`).
2. `docs/scenario-ladder.md:74` — the frozen rung text.
3. `chronicle/social.py` — `form_grudge` (:203-254, the victim-edge
   gate at :225-235 you're adding the ruled bypass to),
   `update_reputation` (:298-353), `REPUTATION_WEIGHT_BY_KIND` (:64-68).
4. `chronicle/driver.py` — the obligation wrappers (:381-434), the
   lane-19 `_evaluate_rule` idiom, `npcs_present_at` usage for the
   caller-supplied presence set.
5. `docs/frame-log-schema.md` §4:124-128 — `grudge_formed`,
   `reputation_updated` shapes (already final; emit field-for-field).
6. `docs/work-packets/reviews/README.md` — governance.

## Pinned implementation decisions (coordinator-set, 2026-08-23)

- **The cascade lives in the existing `violate_obligation` wrapper**,
  after the `obligation_resolved` write, as one rule-14 evaluation
  (one `rule_evaluated` row naming the obligation, grudge id +
  reputation rows in `result`).
- **Grudge:** issuer against debtor, `grievance_type =
  "obligation_violated"`, evidentiary strength from the obligation's
  sanctions/severity (caller-supplied).
- **O3 bypass (ruled):** `form_grudge` gains a documented
  `victim_id == holder_id` path — the gate's raise is skipped for
  self-victim grudges with a comment naming rule 8's harm-to-self base
  case. **No synthetic self-edge rows** — no fake data.
- **Reputation evidence:** one `update_reputation` per **present
  observer** — `obligation.witnesses` ∩ co-located NPCs at the refusal
  tick (caller-supplied presence via `npcs_present_at`) — `subject_id =
  debtor`, `kind = "witnessed"`, `positive = False`. Later hearers get
  `"reported"` rows via ordinary propagation (lane 26's machinery if
  landed, else out of scope here).
- **Rule 14 registers** replacing the stub; default enabled.

## Task

1. `form_grudge` bypass (social.py, per the O3 ruling) + unit test.
2. The rule-14 cascade (rules.py + driver wrapper) per the pins.
3. `scenarios/test_tier3_obligations.py` — the T3.3 rung: three favors
   issued; one fulfilled (consumed, no cascade); one refused with
   observers present. Assert: the refusal produces exactly one
   `obligation_resolved` (violated), one `grudge_formed` (issuer vs
   debtor, `obligation_violated`), and one `reputation_updated` per
   present observer (witnessed, negative) — and **none** for absent
   NPCs; the fulfillment produces no grudge; one `rule_evaluated` row
   names the rule and lists the products.
4. Suite green; no behavior change outside the new cascade.

## Acceptance

- `uv run pytest -q` green (prior count + your new tests), ruff clean.
- `grudge_formed`/`reputation_updated` match §4:124/128 field-for-field.
- The rung asserts pass as written above; the bypass is unit-tested
  (self-victim allowed, missing-edge still raises for third parties).
- No schema/frozen-doc edits; no new RNG purposes.

## File boundaries

**Create:** `scenarios/test_tier3_obligations.py`

**Edit:** `chronicle/social.py` (the bypass only), `chronicle/rules.py`
(rule 14), `chronicle/driver.py` (wrapper cascade)

**Do not touch:** frozen/coordinator docs, `rng.py`, `claims.py`,
other `scenarios/` files, `dashboard/`, `runs/`

## Conventions

- Match the social/driver idiom; rule citations in docstrings.
- **Local commits OK** (path-scoped, explicit adds); never push.
- Existing test assertions immutable; conflicts are findings.
- Report format: delivered, acceptance per criterion with command
  tails, findings list.
