# Lane 13 — delivery report (T2.6/T2.7 mobile carriers)

**Date:** 2026-08-23 · **Lane agent:** Kimi (Track A) · **Packet:** `docs/work-packets/lane-13-t2-6-7-carriers.md`

**No commit**, per protocol. Suite state at delivery: **185 passed, 0 failed, 0 xfailed**; `uv run ruff check .` clean.

## What was delivered

- **`chronicle/fixtures/carrier_schedule.py`** (new) — the multi-hold cast
  in the `whiterun_schedule.py` idiom: a 3-NPC Whiterun market cast and 3
  Markarth residents who never leave their holds; the **caravaneer**
  (market [0,48) → `road_whiterun_markarth` [48,96) → Markarth [96,144) →
  road home → market, one full lap inside the window); the **relief
  caravaneer** on the same route with blocks from tick 25 (after T2.7's
  kill tick), in the schedule from tick 0 as pinned. The courier's Riften
  circuit is omitted — it serves no assertion (the packet's own
  optionality). All cycle ticks are named constants (24 ticks/day,
  ADR-0010).
- **`scenarios/test_tier2_carrier.py`** (new, 2 tests) — both rungs, in
  the T2.x idiom (seeded, deterministic, `encounter_probability=1.0`,
  trace-scan + `chain_for` assertions).

**T2.6** (`test_t26_the_carrier`): public theft witnessed at the market
tick 0; run through the caravaneer's first Markarth block. Asserts the
rung's three exactly — first Markarth-resident transmission lands **at
tick 96 == the arrival tick** and none before it (envelope ticks +
`location_id`, `_believer_curve` precedent); the caravaneer's belief id is
in **every** Markarth resident's `chain_for` walk; every Markarth-located
transmission's teller is the caravaneer or a resident whose own chain
passes through it. Plus the guards: the T1.2-style opportunity guard on
the raw schedule at the arrival tick; the caravaneer heard at tick 0,
before departure; **zero supersession records** (the lane's critical
pinning — identical content everywhere, lane 12's machinery never fires);
zero road transmissions.

**T2.7** (`test_t27_kill_the_carrier`): same setup; the caravaneer hears
the story, then dies at tick 24 (kill seq=2, T1.2 template), injected
**between** `driver.run(0, 24)` and `driver.run(24, 168)` (see findings
below). Asserts: no `encounter_rolled` record names the caravaneer at any
tick ≥ the kill (the exclusion is pre-roll); no caravaneer-told
transmission at tick ≥ 24; zero Markarth-resident hearings at any tick
before the relief arrival (the rung's "any later tick", scanned across
the whole trace, not the endpoint); the would-be opportunity guard (the
dead caravaneer's Markarth block overlaps the residents on the raw
schedule). Positive control: the relief caravaneer hears at tick 25 ==
its market arrival, Markarth transmissions resume exactly at tick 120 ==
its arrival, and every Markarth chain passes through *its* belief id.

## Acceptance criteria

- `uv run pytest -q`: **185 passed, 0 failed, 0 xfailed** (183 + 2 new).
  Tail: `185 passed in 2.30s`
- `uv run ruff check .`: `All checks passed!`
- T2.6's three + T2.7's negative/positive assertions: green, exact ticks
  (96 / 24 / 25 / 120 pinned from fixture constants).
- **Zero engine changes:** `git diff chronicle/` is empty;
  `git status` shows only the two new files
  (`chronicle/fixtures/carrier_schedule.py`, `scenarios/test_tier2_carrier.py`).
- No new RNG purposes; no frozen-doc edits; no dashboard edits; no runs
  generated (scenario runs land in per-test tmp dirs via conftest).

## Findings

1. **Expected finding — confirmed.** Lane 12's encounter path never
   re-hears: the caravaneer's repeated market days produce
   `nothing_salient`/`"both-informed"` rows only. Neither test depends on
   exposure counts — assertions use `transmitted` records and chain walks
   exclusively.
2. **New (noted, not blocking) — kill timing needs the phased-run idiom.**
   `Driver._deceased` is a set with no per-tick timestamp: injecting
   T2.7's kill *before* `driver.run()` would exclude the caravaneer from
   tick 0 and make the negative assertion vacuous (it would never hear the
   story). The test therefore runs in phases and injects the kill between
   ranges (the T2.5 successive-run idiom the packet cited), and asserts
   the caravaneer held the belief at the kill tick as an anti-vacuity
   guard. Worth one line in the driver docstring someday; no action
   requested.
3. **Pre-implementation review (relayed in-session): no blocking
   findings.** The packet's verified claims all checked out against the
   code (singleton road blocks produce no rolls; content-identical
   propagation can't trigger lane-12 resolution; T1.2/T2.1 idioms as
   cited). The two additions beyond the packet text — the heard-before-
   death anti-vacuity assert and the zero-supersession/zero-road
   regression pins — are guards within the packet's latitude, not
   deviations.

## Awaiting

Coordinator review and integration. Nothing known-open in the lane.
