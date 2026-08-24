"""Generate the mourning demo run into runs/: rule 17's write-back, watchable.

Not a test — a runnable demo producer (pytest ignores it: no test_
prefix). Same idiom as scenarios/run_tier3_demo.py (lane 29), but
exercising Tier 4a: a kin dies, the household reroutes to the temple,
and the death rumor travels through the *changed* co-presence graph —
the T4a.2 narrative as a demo, richer than the rung tests'
(scenarios/test_tier4a_mourning.py, test_tier4a_counterfactual.py)
minimal fixtures. Needed because today only those rung tests' tmp dirs
produce `schedule_rewrite` events; the schedule-diff view (lane 41)
needs a real run on disk to build against (docs/work-packets/lane-42-mourning-demo-run.md).

One cast:

  - jarl_balgruuf dies at tick 0; his household -- sven and erik, both
    kin -- each witness it first-hand and each independently trigger
    rule 17 (docs/vision-v2.2.md:21's "his household mourns on their
    calendars," now two schedule_rewrite events, not one);
  - both reroute to the temple for the full mourning window (the
    driver's default MOURNING_DURATION_TICKS, 72 ticks / 3 game-days)
    and tell the priest there -- a belief the priest could only have
    gotten via the reroute, since the priest never visits their house;
  - hilde, an ordinary carrier (the T2.6 pattern) with no stake in the
    death, visits the house right as the household is restored (tick
    72) and then moves on to the market -- carrying the news onward to
    the market crowd (ysolda, carlotta) only *after* restoration,
    because before tick 72 there was nobody home for her to hear it
    from.

Deterministic: fixed seed, fixed wall_ts, same log
(chronicle/tests/test_determinism.py proves the property this script
relies on).

    uv run python scenarios/run_mourning_demo.py
"""

import json
from collections import Counter

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.framelog import default_runs_dir
from chronicle.schedule import ScheduleBlock

RUN_ID = "mourning-demo-01"
SEED = "mourning-demo"
SAVE_UUID = "whiterun-save-1"
END_TICK = 144  # six game-days (ADR-0010) -- spans mourning, restoration, and onward spread

DECEASED = "jarl_balgruuf"
MOURNER_1 = "sven"
MOURNER_2 = "erik"
PRIEST = "priest"
CARRIER = "hilde"
MARKET_NPC_1 = "ysolda"
MARKET_NPC_2 = "carlotta"

HOUSE = "sven_house"
TEMPLE = "temple_of_kynareth"
MARKET = "whiterun_market"

CLAIM_ID = "claim-balgruuf-death"
CLAIM_KIND = "npc_death"
MOURNING_TRIGGERS = {CLAIM_KIND: "deceased"}

# The carrier's cycle: home right as the household is restored (tick 72,
# MOURNING_DURATION_TICKS' default), then the market for the rest of the run.
CARRIER_HOME_ARRIVAL = 72
CARRIER_MARKET_ARRIVAL = 84

SCHEDULE = (
    ScheduleBlock(npc_id=MOURNER_1, location_id=HOUSE, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=MOURNER_2, location_id=HOUSE, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=PRIEST, location_id=TEMPLE, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=CARRIER, location_id=HOUSE, start_tick=CARRIER_HOME_ARRIVAL, end_tick=CARRIER_MARKET_ARRIVAL),
    ScheduleBlock(npc_id=CARRIER, location_id=MARKET, start_tick=CARRIER_MARKET_ARRIVAL, end_tick=END_TICK),
    ScheduleBlock(npc_id=MARKET_NPC_1, location_id=MARKET, start_tick=0, end_tick=END_TICK),
    ScheduleBlock(npc_id=MARKET_NPC_2, location_id=MARKET, start_tick=0, end_tick=END_TICK),
)


def _scripted_setup(driver: Driver) -> None:
    """All pre-run scripted writes; the tick loop then carries the rumor."""
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=SAVE_UUID, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id=DECEASED,
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "run_mourning_demo"},
    )
    for mourner_id in (MOURNER_1, MOURNER_2):
        driver.form_relationship(
            id=f"rel-{mourner_id}-balgruuf", from_id=mourner_id, to_id=DECEASED,
            basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
        )
    for witness_id in (MOURNER_1, MOURNER_2):
        driver.witness(
            claim_id=CLAIM_ID,
            belief_id=f"belief-{witness_id}-balgruuf-death",
            evidence_id=f"evidence-{witness_id}-balgruuf-death",
            kind=CLAIM_KIND,
            slots={"deceased": DECEASED, "cause": "assassination", "location": "dragonsreach"},
            canonical_event_key=EventKey(SAVE_UUID, 0, 1),
            witness_id=witness_id,
            gamets=0.0,
        )


def main() -> None:
    driver = Driver(
        run_id=RUN_ID,
        seed_id=SEED,
        save_uuid=SAVE_UUID,
        generation=0,
        schedule=SCHEDULE,
        encounter_probability=1.0,  # every co-presence is a guaranteed encounter -- a watchable demo, not a rolled one
        mourning_triggers=MOURNING_TRIGGERS,
        mourning_location=TEMPLE,
    )
    _scripted_setup(driver)
    driver.run(0, END_TICK)
    driver.close()

    run_dir = default_runs_dir() / RUN_ID
    counts: Counter[str] = Counter()
    for stream, type_field in (("events.jsonl", "event_type"), ("trace.jsonl", "record_type")):
        for line in (run_dir / stream).open():
            payload = json.loads(line)["payload"]
            record_type = payload.get(type_field) or payload.get("record_type", "?")
            counts[f"{stream}:{record_type}"] += 1
    for key, count in sorted(counts.items()):
        print(f"{key}: {count}")

    rewrites = []
    for line in (run_dir / "events.jsonl").open():
        payload = json.loads(line)["payload"]
        if payload.get("event_type") == "schedule_rewrite":
            rewrites.append(payload)
    print(f"schedule_rewrite events: {[(r['npc_id'], r['location_id'], r['start_tick'], r['end_tick']) for r in rewrites]}")

    # The lane's smoke facts: one schedule_rewrite per mourner, the priest
    # and (eventually) the market crowd informed, restoration observable.
    missing = []
    if counts["events.jsonl:schedule_rewrite"] != 2:
        missing.append("schedule_rewrite (expected 2, one per mourner)")
    priest_informed = driver.belief_of(PRIEST, CLAIM_ID) is not None
    market_informed = driver.belief_of(MARKET_NPC_1, CLAIM_ID) is not None or driver.belief_of(MARKET_NPC_2, CLAIM_ID) is not None
    if not priest_informed:
        missing.append("priest never informed")
    if not market_informed:
        missing.append("market crowd never informed (carrier path)")
    print(f"smoke: {'OK' if not missing else f'MISSING {missing}'}")
    print(f"run written: {run_dir}")


if __name__ == "__main__":
    main()
