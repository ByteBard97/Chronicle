# Lane 19 — delivery report (rule-registry core)

Worker: Kimi (Track A). Packet: `docs/work-packets/lane-19-rule-registry-core.md`.
Committed path-scoped as `8a83e41` (local; not pushed).

## Delivered

- **`chronicle/rules.py`** (new): the 19 §8 names as constants (slugified
  leading tokens; the §8 table stays the vocabulary); `Rule` protocol,
  `RuleContext`/`RuleResult`; `RecordedRule` (wrapper rules — behavior
  stays at the call site, `evaluate()` records the handed outcome);
  `BeliefDecayRule`/`RumorStageRule`/`DormancyReactivationRule` (read-path
  wrappers over `claims.decay`/`stage_at`); `StubRule` (11–19, never
  enabled, `evaluate()` raises); `RuleRegistry` (register/get/enabled,
  unknown `disabled_rules` names raise).
- **`chronicle/driver.py`**: `disabled_rules: Collection[str] = ()` ctor
  arg; `self.rules = RuleRegistry(...)`; `_evaluate_rule` emission helper
  (schema §4:122 field-for-field: `rule`, `inputs`, `fired`, `result`).
  Hooks: `witness` (rules 1 + 4), `retell` (5), `corroborate` (3),
  `resolve` (8), `_run_tick` (6 — one row per tick that had pairs to
  roll; disabling stops the sweep entirely), `_propagate_on_encounter`'s
  mutation decision (7 — evaluation row precedes `mutation_applied`;
  disabling skips the decision, so retellings proceed unmutated).
- **`chronicle/tests/test_rules.py`** (new, 6 tests): 19-names/stub
  contract; unknown-name raise; fired-or-not emission with exact §4:122
  fields on a real run; disabled mutation-policy emits nothing *and* runs
  nothing; disabled encounter-sampling stops the sweep; read-path rules
  compute off-log without emitting.

## Acceptance

- `uv run pytest -q`: **196 passed, 0 failed** (190 pre-existing,
  **unedited** — the no-behavior-change criterion holds with the wiring
  live). `uv run ruff check .`: clean.
- `rule_evaluated` matches §4:122 field-for-field (asserted in tests).
- Replay tolerance: `rule_evaluated` rows carry no store mutation and hit
  the reader's skip path (`framelog.py:768-769`); verified directly —
  `state_at` reconstructs correctly over a run containing them.
- No new RNG purposes; no schema/frozen-doc edits; boundaries respected
  (`claims.py`, `social.py`, `rng.py`, `scenarios/` untouched).

## Findings / judgment calls (flagged, all reversible)

1. **What "toggleable" suspends (the R2 consequence, stated openly).**
   Wrapper rules never owned behavior, so disabling rules 1/3/4/5/8
   suspends *instrumentation* only; the store mechanics are untouched.
   Rules 6 and 7 are the two driver-owned discrete steps, so those get
   real behavioral toggles (sweep stops / mutations stop). True
   behavioral toggles for rules 1–5/8 would require the refactoring R2
   ruled out. This asymmetry is documented in the `rules.py` module
   docstring; if the coordinator wants different semantics, it's a
   driver-side change.
2. **Rule 6's evaluation granularity:** one `rule_evaluated` per *tick
   with pairs* (the `sample_encounters` call), not per roll — per-roll
   would double the largest record class for zero information, since
   `encounter_rolled` already instruments each pair (value/threshold/
   outcome). Volume: +≤240 rows/run, flat. Ticks with zero co-present
   pairs emit nothing (empty world, not a stuck counter).
3. **Rule 4's `pre_existing` flag is driver-scoped** (claims already seen
   by this driver's `witness()`), because `ClaimStore`'s by-event index is
   private and `claims.py` is out of bounds. Sufficient for the wrapper's
   instrumentation; a store-level accessor would be a claims.py change for
   a later lane if a consumer needs it.
4. **Rule 3's wrapper covers the scripted `corroborate()` path only.**
   The encounter path performs no corroboration (lane-12 ruling), and
   re-hearing corroboration inside `claims.retell()` isn't separately
   instrumented — flagged so L-lanes know where rule 3's rows come from.
5. **Volume note for the ui-spec §1.1 figure:** this lane adds
   `rule_evaluated` rows to every run (witness/retell/corroborate/resolve
   + per-tick sweep). On the carrier-demo shape that's roughly +10–15%
   trace rows. Feeds the same owner-review backlog item as the
   supersession-churn finding.
