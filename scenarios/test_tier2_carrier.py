"""Scenario-ladder rungs T2.6 (The carrier) and T2.7 (Kill the carrier).

Tier 2's border rungs: without mobile carriers, co-presence encounters over
single-hold schedules mean every rumor structurally dies at the hold border
(the rung's v0.3 vision-review catch). The multi-hold fixture
(chronicle/fixtures/carrier_schedule.py) makes a Whiterun market crime
reachable from Markarth *only* through a carrier's travel blocks.

Pinned lane-13 decisions in force here (docs/work-packets/lane-13-t2-6-7-carriers.md):

  - NO mutation candidates (the Driver default): with a single witnessed
    story every belief carries identical slots, so lane 12's resolution
    machinery never fires -- both tests assert zero supersession records,
    keeping "the carrier in every Markarth chain" exact.
  - Roads are explicit but otherwise empty: a lone carrier en route is a
    singleton, dropped by npcs_present_at, so no en-route roll records
    exist and the border-holds assertion is exact by construction.
  - encounter_probability=1.0 (T2.2/T1.2 precedent): arrival and belief
    ticks are exact, not distributional.
  - T2.7's relief caravaneer is in the schedule from tick 0 (no mid-run
    insertion mechanic); the kill is injected between successive
    driver.run() ranges (the T2.5 idiom) -- injecting it up front would
    mark the caravaneer deceased before it ever hears the story, since
    death-awareness has no per-tick timestamp.
"""

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied
from chronicle.fixtures.carrier_schedule import (
    CARAVANEER,
    CARAVANEER_DEPARTURE,
    CARAVANEER_MARKARTH_ARRIVAL,
    MARKARTH_CITY,
    MARKARTH_RESIDENTS,
    RELIEF_CARAVANEER,
    RELIEF_DEPARTURE,
    RELIEF_MARKARTH_ARRIVAL,
    RELIEF_MARKET_ARRIVAL,
    ROAD_WHITERUN_MARKARTH,
    WHITERUN_MARKET,
    carrier_schedule,
)
from chronicle.framelog import FrameLogReader
from chronicle.schedule import npcs_present_at

_SEED = "tier2-carrier"
_SAVE = "whiterun-save-1"
_CLAIM_ID = "claim-market-theft"
_CLAIM_SLOTS = {"perpetrator": "unknown", "crime": "theft", "location": WHITERUN_MARKET}

# T2.7's kill: mid-way through the caravaneer's market stay -- after it
# heard the story (tick 0), before its road block starts.
_KILL_TICK = CARAVANEER_DEPARTURE // 2  # tick 24
# T2.6 runs through the caravaneer's first Markarth block; T2.7 through the
# relief caravaneer's arrival block.
_T26_TICKS = CARAVANEER_MARKARTH_ARRIVAL + 2 * 24
_T27_TICKS = RELIEF_MARKARTH_ARRIVAL + 2 * 24


def _driver(run_id: str) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=carrier_schedule(),
        encounter_probability=1.0,
    )


def _witness_the_market_theft(driver: Driver):
    """A public crime in Whiterun, witnessed first-hand by a market resident (the canonical T2.x pattern)."""
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id="belethor",
            perpetrator_id="unknown", crime_type="theft", location_id=WHITERUN_MARKET,
        ),
        origin={"kind": "scenario", "detail": "test_tier2_carrier"},
    )
    theft_event = driver.event_log.lineage(_SAVE, 0)[0]
    return driver.witness(
        claim_id=_CLAIM_ID,
        belief_id="belief-belethor-theft",
        evidence_id="evidence-belethor-theft",
        kind="crime_witnessed",
        slots=dict(_CLAIM_SLOTS),
        canonical_event_key=EventKey(theft_event.save_uuid, theft_event.generation, theft_event.seq),
        witness_id="belethor",
        gamets=0.0,
    )


def _transmissions(driver: Driver) -> list[dict]:
    """Every transmitted record for the claim, as (envelope tick, payload) -- the trace-side view."""
    reader = FrameLogReader(driver.writer.run_dir)
    return [
        (record["tick"], record["payload"])
        for record in reader.records("trace")
        if record["payload"].get("record_type") == "transmitted"
        and record["payload"]["claim_id"] == _CLAIM_ID
    ]


def _chain_belief_ids(driver: Driver, holder_id: str) -> tuple[str, ...]:
    belief = driver.belief_of(holder_id, _CLAIM_ID)
    assert belief is not None, f"{holder_id} holds no belief about {_CLAIM_ID}"
    return tuple(held.id for held, _evidence in driver.chain_for(belief.id))


def test_t26_the_carrier():
    """Ladder T2.6: the rumor crosses the hold border only inside the caravaneer's travel blocks."""
    driver = _driver("scenario-tier2-carrier")
    _witness_the_market_theft(driver)
    driver.run(0, _T26_TICKS)
    driver.close()

    # Opportunity guard (T1.2 precedent): on the raw schedule the caravaneer
    # IS co-present with the Markarth residents at the arrival tick -- a
    # propagation failure cannot masquerade as no-opportunity.
    present_at_arrival = npcs_present_at(driver.schedule, CARAVANEER_MARKARTH_ARRIVAL)
    assert CARAVANEER in present_at_arrival[MARKARTH_CITY]
    assert set(MARKARTH_RESIDENTS) <= set(present_at_arrival[MARKARTH_CITY])

    transmissions = _transmissions(driver)

    # The premise: the caravaneer heard the story at the Whiterun market
    # before departure (the rung's "carrier hears it at the market").
    caravaneer_hearings = [t for t, p in transmissions if p["hearer_id"] == CARAVANEER]
    assert caravaneer_hearings and min(caravaneer_hearings) == 0
    assert min(caravaneer_hearings) < CARAVANEER_DEPARTURE
    caravaneer_belief = driver.belief_of(CARAVANEER, _CLAIM_ID)
    assert caravaneer_belief is not None and caravaneer_belief.first_learned == 0.0

    # Lane-13's critical pinning, asserted: identical content everywhere,
    # so lane 12's resolution machinery never fires.
    reader = FrameLogReader(driver.writer.run_dir)
    assert [r for r in reader.records("trace") if r["payload"].get("record_type") == "supersession"] == []
    # Roads stayed empty: no transmission ever happened on a road block.
    assert [p for _t, p in transmissions if p["location_id"] == ROAD_WHITERUN_MARKARTH] == []

    markarth_transmissions = [(t, p) for t, p in transmissions if p["location_id"] == MARKARTH_CITY]

    # Rung assertion 1: the first Markarth-resident belief exists only at a
    # tick >= the carrier's arrival -- exactly the arrival tick here, and
    # never before it.
    assert markarth_transmissions, "T2.6 requires the story to reach Markarth"
    first_markarth_tick = min(t for t, _p in markarth_transmissions)
    assert first_markarth_tick == CARAVANEER_MARKARTH_ARRIVAL
    assert [r for r in transmissions if r[1]["hearer_id"] in MARKARTH_RESIDENTS and r[0] < CARAVANEER_MARKARTH_ARRIVAL] == []

    # Rung assertion 2: the carrier appears in EVERY Markarth evidence chain.
    caravaneer_belief_id = caravaneer_belief.id
    for resident in MARKARTH_RESIDENTS:
        assert caravaneer_belief_id in _chain_belief_ids(driver, resident), (
            f"{resident}'s chain does not pass through the carrier"
        )

    # Rung assertion 3: no cross-border belief via any non-carrier path --
    # every Markarth transmission's teller is the carrier or a resident the
    # carrier informed (resident-to-resident spread inside Markarth is
    # in-hold propagation, and assertion 2 already pins its provenance).
    for _t, p in markarth_transmissions:
        teller = p["teller_id"]
        assert teller == CARAVANEER or (
            teller in MARKARTH_RESIDENTS and caravaneer_belief_id in _chain_belief_ids(driver, teller)
        ), f"cross-border transmission via non-carrier path: {p}"


def test_t27_kill_the_carrier():
    """Ladder T2.7: kill the carrier before departure and the border holds; the relief carrier restores it."""
    driver = _driver("scenario-tier2-carrier-killed")
    _witness_the_market_theft(driver)

    # The caravaneer hears the story, then dies mid-stay, before departure.
    # The kill is injected BETWEEN run ranges: death-awareness is a set, not
    # a per-tick timestamp, so injecting up front would silence the
    # caravaneer from tick 0 and make the negative assertion vacuous.
    driver.run(0, _KILL_TICK)
    assert driver.belief_of(CARAVANEER, _CLAIM_ID) is not None  # it heard before dying
    driver.inject_event(
        NPCDied(
            tick=_KILL_TICK, save_uuid=_SAVE, generation=0, seq=2,
            gamets=float(_KILL_TICK), wall_ts=float(_KILL_TICK), npc_id=CARAVANEER,
            cause="killed by the player", killer_id="player", location_id=WHITERUN_MARKET,
        ),
        origin={"kind": "scenario", "detail": "test_tier2_carrier"},
    )
    driver.run(_KILL_TICK, _T27_TICKS)
    driver.close()

    # Would-be opportunity guard on the raw schedule (T1.2 precedent): the
    # caravaneer's Markarth block exists and overlaps the residents -- the
    # border holding below is the death mechanism under test, not a fixture
    # where the trip never existed.
    present_at_arrival = npcs_present_at(driver.schedule, CARAVANEER_MARKARTH_ARRIVAL)
    assert CARAVANEER in present_at_arrival[MARKARTH_CITY]
    assert set(MARKARTH_RESIDENTS) <= set(present_at_arrival[MARKARTH_CITY])

    reader = FrameLogReader(driver.writer.run_dir)
    trace = list(reader.records("trace"))
    transmissions = [
        (record["tick"], record["payload"])
        for record in trace
        if record["payload"].get("record_type") == "transmitted"
        and record["payload"]["claim_id"] == _CLAIM_ID
    ]

    # The dead don't tell (T1.2's inter-hold twin): the caravaneer is
    # excluded before any roll at tick >= the kill tick -- no encounter
    # record ever names it, and it never tells.
    assert [
        r for r in trace
        if r["payload"].get("record_type") == "encounter_rolled"
        and r["tick"] >= _KILL_TICK
        and CARAVANEER in (r["payload"]["npc_a"], r["payload"]["npc_b"])
    ] == []
    assert [p for t, p in transmissions if p["teller_id"] == CARAVANEER and t >= _KILL_TICK] == []

    # The negative assertion, scanned across ALL ticks: until the relief
    # caravaneer's arrival, zero beliefs for the claim held by any
    # non-Whiterun NPC -- the border holds.
    assert [
        p for t, p in transmissions
        if p["hearer_id"] in MARKARTH_RESIDENTS and t < RELIEF_MARKARTH_ARRIVAL
    ] == []

    # Positive control: the relief caravaneer was in the schedule from tick
    # 0, heard the story at the market after the kill, and its completed
    # travel block restores propagation on the next cycle.
    relief_hearings = [t for t, p in transmissions if p["hearer_id"] == RELIEF_CARAVANEER]
    assert relief_hearings and min(relief_hearings) == RELIEF_MARKET_ARRIVAL
    assert min(relief_hearings) < RELIEF_DEPARTURE
    markarth_transmissions = [(t, p) for t, p in transmissions if p["location_id"] == MARKARTH_CITY]
    assert markarth_transmissions
    assert min(t for t, _p in markarth_transmissions) == RELIEF_MARKARTH_ARRIVAL
    relief_belief = driver.belief_of(RELIEF_CARAVANEER, _CLAIM_ID)
    assert relief_belief is not None
    for resident in MARKARTH_RESIDENTS:
        assert relief_belief.id in _chain_belief_ids(driver, resident), (
            f"{resident}'s chain does not pass through the relief carrier"
        )
