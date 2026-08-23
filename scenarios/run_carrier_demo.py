"""Generate a real demo run into runs/: a market murder carried across a hold border.

Not a test — a runnable demo producer (pytest ignores it: no test_ prefix).
Same idiom as scenarios/run_jarl_death_demo.py, over the T2.6/T2.7 carrier
fixture (chronicle/fixtures/carrier_schedule.py): a crime witnessed at the
Whiterun market at tick 0, then encounter-driven spread — including over the
caravaneers' Whiterun <-> Markarth laps — with mutation candidates registered
so variants emerge en route and supersessions fire (lane 12's machinery).
This is the run the dashboard's mutation/supersession renderers (lanes 16/18)
and its carrier/satellite UI read. Deterministic: fixed seed, same log
(chronicle/tests/test_determinism.py proves the property this script relies on).

    uv run python scenarios/run_carrier_demo.py
"""

import json
from collections import Counter

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied
from chronicle.fixtures.carrier_schedule import (
    CARAVANEER,
    END_TICK,
    MARKARTH_CITY,
    RELIEF_CARAVANEER,
    WHITERUN_MARKET,
    carrier_schedule,
)

RUN_ID = "carrier-mutation-01"
SEED = "carrier-mutation-demo"
SAVE_UUID = "whiterun-save-1"

# The jarl-demo's canonical pattern: a public crime at tick 0, witnessed
# where the carriers begin their lap. The victim is not a cast member (the
# demo keeps every scheduled NPC alive — the T2.6 shape, no kill events).
VICTIM = "whiterun_merchant"
WITNESS = "belethor"  # a Whiterun market regular; co-present with both carriers at tick 0

# The caller-supplies-context seam (T2.2's mapping shape): lore-flavored
# candidate domains a mutation can substitute from, keyed (claim_kind, slot).
# Expect heavy supersession churn — the ruled T2.3 behavior, not a bug.
MUTATION_CANDIDATES = {
    ("npc_death", "perpetrator"): ("the Thalmor", "a bandit chief", "the Silver-Bloods"),
    ("npc_death", "cause"): ("an accident", "a sudden illness"),
    ("npc_death", "location"): ("the plains district", "the stables"),
}

ENCOUNTER_PROBABILITY = 0.35  # the jarl-demo value; the fixture's 1.0 pinning is for exact-tick tests


def main() -> None:
    driver = Driver(
        run_id=RUN_ID,
        seed_id=SEED,
        save_uuid=SAVE_UUID,
        generation=0,
        schedule=carrier_schedule(),
        encounter_probability=ENCOUNTER_PROBABILITY,
        mutation_candidates=MUTATION_CANDIDATES,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=SAVE_UUID, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id=VICTIM,
            cause="assassination", killer_id=None, location_id=WHITERUN_MARKET,
        ),
        origin={"kind": "scenario", "detail": "run_carrier_demo"},
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid=SAVE_UUID, generation=0, seq=2,
            gamets=0.0, wall_ts=1.0, witness_id=WITNESS,
            perpetrator_id="unknown", crime_type="murder",
            location_id=WHITERUN_MARKET,
        ),
        origin={"kind": "scenario", "detail": "run_carrier_demo"},
    )
    driver.witness(
        claim_id="claim-market-murder",
        belief_id=f"belief-{WITNESS}-murder",
        evidence_id=f"evidence-{WITNESS}-murder",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": WHITERUN_MARKET},
        canonical_event_key=EventKey(SAVE_UUID, 0, 1),
        witness_id=WITNESS,
        gamets=0.0,
    )
    driver.run(0, END_TICK)
    driver.close()

    from chronicle.framelog import default_runs_dir

    run_dir = default_runs_dir() / RUN_ID
    for stream, type_field in (("events.jsonl", "event_type"), ("trace.jsonl", "record_type")):
        path = run_dir / stream
        counts: Counter[str] = Counter()
        for line in path.open():
            payload = json.loads(line)["payload"]
            counts[payload.get(type_field) or payload.get("record_type", "?")] += 1
        print(f"{stream}: {sum(counts.values())} records")
        for record_type, count in sorted(counts.items()):
            print(f"  {record_type}: {count}")
    print(f"carriers on the route: {CARAVANEER}, {RELIEF_CARAVANEER} (both kept alive; destination {MARKARTH_CITY})")
    print(f"run written: {run_dir}")


if __name__ == "__main__":
    main()
