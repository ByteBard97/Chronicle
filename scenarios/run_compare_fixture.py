"""Lane 38 test fixture: two real, same-`seed_id` runs for the dashboard's
§3.9 run-comparison tool (`dashboard/src/derived/runCompare.ts`).

Not a test -- a runnable demo producer (pytest ignores it: no test_ prefix),
matching the precedent of `run_jarl_death_demo.py`/`run_carrier_demo.py`/
`run_mourning_demo.py`. `runs/whiterun-jarl-01` and `runs/carrier-mutation-01`
have DIFFERENT seed_ids (confirmed), so they can't stand in for this lane's
"two runs, same seed_id, differing config" pair -- this script builds one.

Divergence mechanism: both runs share `SEED_ID`, `save_uuid`/`generation`,
and an identical schedule (same NPCs, same sites, same ticks) -- so every
`encounter_rolled` record's `roll_key` (seed_id, purpose, tick, site,
sorted participants, draw) is identical between the two runs, and
`chronicle.rng.roll()` is a pure function of that key -- so the recorded
`value` for a given key is byte-identical in both runs too. What differs is
`encounter_probability` (0.85 in run A, 0.15 in run B): the `threshold`
each `encounter_rolled` record compares that same `value` against, and
therefore (for any roll whose `value` falls between the two thresholds)
`encountered` itself. This is a controlled, deterministic way to produce
real same-seed_id runs whose `encounter_rolled` streams disagree on
`threshold`/`encountered` (never on `value`, never on `roll_key`) at
several ticks -- exactly the shape `findFirstDivergentRoll` is looking for,
without hand-editing JSONL.

    uv run python scenarios/run_compare_fixture.py
"""

from chronicle.driver import Driver
from chronicle.schedule import ScheduleBlock

SEED_ID = "compare-fixture-demo"
SAVE_UUID = "compare-fixture-save"
TICKS = 24

RUN_A = "compare-fixture-a"
RUN_B = "compare-fixture-b"

_MARKET = "market"
_TAVERN = "bannered_mare"  # a real dashboard/map/whiterun_map.json location id, unlike a made-up "tavern"

# Five NPCs, two sites, all present the whole run -- plenty of co-present
# pairs each tick so `encounter_probability`'s effect on `threshold`/
# `encountered` actually shows up repeatedly, not just once.
_SCHEDULE = (
    ScheduleBlock(npc_id="adrianne", location_id=_MARKET, start_tick=0, end_tick=TICKS),
    ScheduleBlock(npc_id="ulfberth", location_id=_MARKET, start_tick=0, end_tick=TICKS),
    ScheduleBlock(npc_id="belethor", location_id=_MARKET, start_tick=0, end_tick=TICKS),
    ScheduleBlock(npc_id="camilla", location_id=_TAVERN, start_tick=0, end_tick=TICKS),
    ScheduleBlock(npc_id="sven", location_id=_TAVERN, start_tick=0, end_tick=TICKS),
)


def _build(run_id: str, *, encounter_probability: float) -> Driver:
    driver = Driver(
        run_id=run_id,
        seed_id=SEED_ID,
        save_uuid=SAVE_UUID,
        generation=0,
        schedule=_SCHEDULE,
        encounter_probability=encounter_probability,
    )
    driver.run(0, TICKS)
    driver.close()
    return driver


def main() -> None:
    _build(RUN_A, encounter_probability=0.85)
    _build(RUN_B, encounter_probability=0.15)

    from chronicle.framelog import default_runs_dir

    for run_id in (RUN_A, RUN_B):
        run_dir = default_runs_dir() / run_id
        for stream in ("events.jsonl", "trace.jsonl"):
            path = run_dir / stream
            n = sum(1 for _ in path.open()) if path.exists() else 0
            print(f"{run_id}/{stream}: {n} records")


if __name__ == "__main__":
    main()
