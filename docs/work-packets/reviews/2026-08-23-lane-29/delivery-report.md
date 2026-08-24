# Lane 29 delivery report — Tier-3-rich demo run

**Attribution note:** `scenarios/run_tier3_demo.py`'s scenario design,
cast, and Tier-3 opt-in wiring are Kimi's (written before running out of
session usage mid-lane, with the script uncommitted and no run yet
generated). Claude picked this up during a coordinator-outage
investigation, diagnosed and fixed the one bug blocking it, generated
and verified the run, and files this report. Nothing about the
scenario's design was changed — only the tick loop's start boundary.

## What was wrong

Running the script as left on disk crashed immediately:

```
ValueError: a retelling cannot precede the teller's last rehearsal of it
  chronicle/driver.py:933 (_propagate_on_encounter -> retell)
  chronicle/claims.py:348 (the guard)
```

`_scripted_setup()` stamps beliefs with `gamets` values up to `3.0` (the
fourth theft, `n=4`, `gamets=float(n-1)`) — all *before* `driver.run()`
begins. `driver.run(0, END_TICK)` then starts its tick loop at
`gamets=0.0`, which is *behind* `belief-merchant-theft-4`'s
`last_rehearsed=3.0` — the very first tick's automatic encounter
propagation (belethor + carlotta, both scheduled at the market from
tick 0) tries to retell that belief and hits the guard.

## The fix

One change: the tick loop now starts at `LOOP_START_TICK = 4` (one past
the highest `gamets` any `_scripted_setup` call uses), not `0`:

```python
LOOP_START_TICK = 4
...
driver.run(LOOP_START_TICK, END_TICK)
```

Considered and rejected: flattening all of `_scripted_setup`'s `gamets`
values to `0.0` (matching lane 17's simpler precedent) — rejected
because the obligation-violation cascade's `present_npc_ids` is
deliberately computed as `npcs_present_at(SCHEDULE, 2)[WARMAIDENS]`,
i.e. "whoever has arrived by tick 2" (the courtier moves from
Dragonsreach to Warmaiden's exactly at tick 2 per the schedule) —
flattening the violation's own `gamets` to `0.0` while keeping that
tick-2 presence computation would have created a real inconsistency
between when the violation is recorded as happening and who it claims
witnessed it. Shifting the loop's start instead preserves every
scripted timestamp exactly as designed.

No engine file touched; the fix is entirely within
`scenarios/run_tier3_demo.py`, matching the packet's "no engine changes"
requirement.

## Acceptance, verified by Claude

- **`runs/tier3-demo-01/` generated, all required record types present**
  (script's own smoke check + independent CLI/grep spot-checks):
  ```
  trace.jsonl:rule_evaluated: 165 (fired: true=126 false=39)
  trace.jsonl:threshold_crossed: 1
  trace.jsonl:transmission_declined: 44
  trace.jsonl:reputation_updated: 5
  trace.jsonl:grudge_formed: 1
  events.jsonl:escalation_warning: 1
  smoke: OK
  ```
  Negative `rule_evaluated` rows present (39 `fired: false`) — the diff
  panel's stuck-counter case.
- **Each rung spot-checked directly against the log**, not just counted:
  - `chronicle trace tier3-demo-01 claim-theft-4`: belief formed at
    tick 3 (the fourth theft), escalation fires — matches the script's
    intent exactly.
  - `chronicle inspect tier3-demo-01 hulda`: one belief
    (`claim-player-secret`), and `transmission_declined` rows at ticks
    4/5/6/... all `teller_id: hulda, hearer_id: olfrid` — the
    kin-motivated decline firing repeatedly, as scripted.
  - `grudge_formed`: `source_belief_id: obl-favor-2` — the Lane 25-ruled
    convention (a grievance sourced from an obligation, not a belief)
    confirmed present in real data for the first time.
  - `reputation_updated`: both the Thane proclamation (proventus/irileth,
    `positive: true`) and the obligation violation (proventus,
    `positive: false`) rows present.
- **Determinism**: regenerated twice into separate `CHRONICLE_RUNS_DIR`s
  — `trace.jsonl` byte-identical; `events.jsonl` identical modulo
  `wall_ts`.
- `uv run pytest -q`: 205 passed (unchanged — this lane adds no tests,
  per its own packet). `uv run ruff check .`: clean.
- No engine/fixture-test edits; no schema edits — confirmed via
  `git diff` scope (only `scenarios/run_tier3_demo.py` changed).

## Findings

1. **CLI `feed` command doesn't surface `transmission_declined` rows**
   (`chronicle/cli.py`'s `_FEED_RECORD_TYPES` whitelist predates lane
   23) — same root-cause family as lane 17's finding 1 (the `trace`
   command's supersession filter under-reporting). Both point at the
   same backlog item: a `cli.py` hygiene lane to bring its record-type
   whitelists current with Tier 2/3. Verified via direct `trace.jsonl`
   grep instead for this report.
2. `LOOP_START_TICK`'s value (4) is a manually-verified constant tied to
   the specific gamets values `_scripted_setup` happens to use today —
   if a future edit to that function raises the max gamets it stamps,
   this constant needs bumping too. Documented inline; not automated
   (would require walking the scripted calls programmatically, out of
   scope for a one-line fix).

## Command tails

```
$ uv run python scenarios/run_tier3_demo.py
events.jsonl:crime_witnessed: 5
events.jsonl:escalation_warning: 1
events.jsonl:keyframe: 2
events.jsonl:rumor_heard: 1
trace.jsonl:belief_formed: 9
trace.jsonl:encounter_rolled: 308
trace.jsonl:grudge_formed: 1
trace.jsonl:nothing_salient: 2098
trace.jsonl:obligation_issued: 2
trace.jsonl:obligation_resolved: 2
trace.jsonl:relationship_formed: 1
trace.jsonl:reputation_updated: 5
trace.jsonl:rule_evaluated: 165
trace.jsonl:threshold_crossed: 1
trace.jsonl:transmission_declined: 44
trace.jsonl:transmitted: 14
rule_evaluated fired: true=126 false=39
smoke: OK
run written: /home/geoff/projects/Chronicle/runs/tier3-demo-01

$ uv run pytest -q
........................................................................ [ 35%]
........................................................................ [ 70%]
.............................................................          [100%]
205 passed in 2.34s

$ uv run ruff check .
All checks passed!
```
