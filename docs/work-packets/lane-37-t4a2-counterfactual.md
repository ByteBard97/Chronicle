# Lane 37 — Tier 4a L-H: T4a.2 counterfactual (Track A, scenario test)

**Status:** After **lane 36** lands (needs rule 17 live + the toggle).
Pure scenario-test lane — no production-code changes expected; if one
surfaces, it's a finding.

**Effort:** medium.

## Context

T4a.2 (frozen, `docs/scenario-ladder.md:84`): Run A (with reroute) vs.
Run B (fixture-frozen), same seed, keyed randomness. Assert: the rumor
reaches the priest before the market in A and the reverse in B — and
**every roll outside the mourner's changed sites is identical across
runs**. The design (accepted): Run B is Run A with
`disabled_rules=("schedule-write-back",)` (T7), and the roll-identity
assertion is per-pair byte-identical `encounter_rolled` rows (T4's
exact wording).

## Read first

1. `docs/design/tier-4a-schedule-write-back.md` §2 (T4) and §5 (T7) —
   the assertion's exact meaning.
2. Lane 36's landed implementation (rules/driver) — read the committed
   code.
3. `scenarios/test_tier4a_mourning.py` (lane 36) — the fixture to reuse
   (its base schedule needs a priest-site and a market-site with the
   right topology for the narrative assert).
4. `docs/ui-spec.md:120` (the §3.9 merge-scan tool is the dashboard
   twin of this assertion — share one definition of "outside the
   mourner's changed sites"; design doc F4).

## Task

1. `scenarios/test_tier4a_counterfactual.py`: the two-driver harness
   (identical construction; B disables rule 17).
2. **Roll-identity assertion (primary):** for every `encounter_rolled`
   record whose participants exclude the mourner, the A and B records
   (same tick/location/participants) are byte-identical in
   `value`/`threshold`/`encountered` — a merge-scan over both traces,
   with the scan's "outside the mourner's pairs" predicate named and
   documented (F4: this exact predicate is the one the dashboard's
   §3.9 tool will reuse).
3. **Narrative assertion (companion):** the rumor reaches the
   priest-site before the market-site in A; the reverse (or no
   priest-site arrival) in B.
4. The shared-fixture discipline: one fixture, one config flag — no
   hand-authored second schedule.

## Acceptance

- `uv run pytest -q` green (lane-36 count + your new test), ruff clean.
- Both assertions pass as written; the identity scan is a reusable
  helper (the §3.9 tool's semantics, noted in its docstring).
- No production-code changes (any need = finding).

## File boundaries

**Create:** `scenarios/test_tier4a_counterfactual.py` (only)

**Do not touch:** everything else.

## Conventions

- **Local commits OK** (path-scoped); never push.
- File a delivery report on disk: delivered, acceptance with command
  tails, findings list.
