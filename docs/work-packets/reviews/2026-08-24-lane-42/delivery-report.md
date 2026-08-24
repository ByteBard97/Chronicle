# Lane 42 delivery report — mourning demo run producer

**Delivered:** `18611a3` — `scenarios/run_mourning_demo.py`. Same
producer idiom as lanes 17/29 (`run_carrier_demo.py`,
`run_tier3_demo.py`), exercising rule 17 on a real, watchable run.

## Acceptance, per criterion

- **The run exists with the smoke facts, CLI-verified.** ✓ —
  `runs/mourning-demo-01/` generated (local-only, `.gitignore:18`, same
  as every prior demo run). The producer's own smoke check passes
  (`smoke: OK`), and independently re-verified via the CLI:

  ```
  $ uv run python scenarios/run_mourning_demo.py | tail -3
  schedule_rewrite events: [('sven', 'temple_of_kynareth', 0, 72), ('erik', 'temple_of_kynareth', 0, 72)]
  smoke: OK
  run written: .../runs/mourning-demo-01
  ```

  - **`schedule_rewrite` events, field-for-field**: two events (one per
    mourner), both `location_id="temple_of_kynareth"`,
    `start_tick=0`, `end_tick=72` (the driver's default
    `MOURNING_DURATION_TICKS`).
  - **Encounters move to the temple during the window**:
    `feed --npc sven --from-tick 70` shows `encounter_rolled` rows at
    `temple_of_kynareth` through tick 71, switching to `sven_house` at
    exactly tick 72 — restoration is exact, not approximate.
  - **The priest is informed and the chain shows the reroute path**:
    `trace claim-balgruuf-death` shows `belief_formed` for sven/erik at
    tick 0 (the witness), then a `transmitted` row at tick 0
    (`teller_id: erik, hearer_id: priest, location_id:
    temple_of_kynareth`) — a belief the priest could only have gotten
    via the reroute, since the priest's own schedule never covers the
    house. The chain continues past restoration: `transmitted` at tick
    72 (`erik -> hilde`, at `sven_house` — the carrier arriving exactly
    as the household is restored) and at tick 84 (`hilde -> carlotta ->
    ysolda`, at `whiterun_market`) — the reroute's downstream effect on
    who eventually hears the news, watchable in one run.
- **Determinism verified.** ✓ — two independent regenerations into
  fresh `mktemp -d` `CHRONICLE_RUNS_DIR`s, diffed with `payload.wall_ts`
  masked (the harness's rule): `events.jsonl` 9==9, `trace.jsonl`
  1322==1322, byte-identical.
- **`uv run pytest -q` green, ruff clean.** ✓ — 218 passed (unchanged —
  no test files touched), ruff clean.

## What was built

One cast, `END_TICK=144` (six game-days): jarl_balgruuf dies at tick 0;
sven and erik (both kin, per two `form_relationship` calls) each
witness it first-hand and each independently trigger rule 17 — the
vision's "his household mourns on their calendars, not in a bark"
(`docs/vision-v2.2.md:21`) realized as two separate `schedule_rewrite`
events rather than one, since rule 17's trigger is per-holder belief
acquisition (design doc T5), not a household-level event. Both reroute
to `temple_of_kynareth` for the full 72-tick window and inform the
priest there. `hilde`, an ordinary carrier with no stake in the death
(the T2.6 mobile-carrier pattern), is scheduled to arrive at the house
at exactly tick 72 and the market at tick 84 — she can only pick up the
news from the household once they're actually home again, so her own
arrival timing makes restoration's narrative consequence ("the reroute
mattered, then life resumes and news travels normally") observable
without a second driver run.

## Findings

1. **The `deceased`-naming slot convention (F3/O1 from the Tier-4a
   design doc) is used exactly as documented** — the fixture's
   `npc_death` claim carries an explicit `"deceased"` slot, and
   `mourning_triggers = {"npc_death": "deceased"}` points at it. No
   surprises; confirms the convention is workable for a richer,
   multi-mourner fixture, not just the two-NPC rung tests.
2. **The producer's own smoke check is deliberately narrower than a
   full CLI walkthrough** (it only checks event counts and
   `belief_of` presence) — I verified the richer claims (exact
   restoration tick, the specific transmission chain) by hand via the
   CLI for this report rather than hard-coding them into the script
   itself, matching lanes 17/29's precedent of keeping the producer's
   own assertions to coarse smoke facts and doing the detailed
   walkthrough in the delivery report.
3. **No engine changes** — `git diff chronicle/` for this lane is
   empty; the run relies entirely on the landed lane-36 mechanism and
   already-existing driver constructor parameters
   (`mourning_triggers`/`mourning_location`).
