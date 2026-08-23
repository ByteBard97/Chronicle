"""Scenario-ladder rung T3.4 (Secret with stakes) -- the tell-decision gate.

Two NPCs learn the player's secret; one is kin-motivated to keep it
(docs/scenario-ladder.md:75). The lane-23 pins in force
(docs/work-packets/lane-23-tell-decision.md):

  - The gate (rule 15) sits in the encounter path after teller_and_hearer
    resolves, before mutation; scripted witness paths are scenario-author
    control and are NOT gated (both holders here learn first-hand at tick
    0 -- a scripted retell from the motivated holder would be the author
    violating the motivation, not the sim).
  - Stage 1 is deterministic: the kin-motivated holder declines ALWAYS,
    no roll -- transmission_declined carries the rule name (O5: sub-reason
    in the paired rule_evaluated's inputs) and roll_key null.
  - Stage 2 is the keyed tell.decision roll against tell_probability
    (default 1.0: every unmotivated tell proceeds).

Fixture geometry: two locations, so the motivated holder's opportunities
repeat every tick (his listener never learns) while the unmotivated
holder's single tell lands at tick 0 -- "declining by name each
opportunity" is asserted against the full encounter scan, not a sample.
"""

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed
from chronicle.framelog import FrameLogReader
from chronicle.rules import TELL_DECISION_POLICY
from chronicle.schedule import ScheduleBlock

_SEED = "tier3-tell-decision"
_SAVE = "whiterun-save-1"
_TICKS = 48  # two game-days (ADR-0010)

_CLAIM_ID = "claim-player-secret"
_CLAIM_KIND = "player_secret"
_CLAIM_SLOTS = {"subject": "player", "secret": "the Dragonborn's night-time visit to the tomb"}

# The two informed holders and their respective would-be hearers.
KIN_KEEPER = "kin_keeper"  # kin to the player -- motivated to keep the secret
TAVERN_GOSSIP = "tavern_gossip"  # no motive -- transmits on normal keyed rolls
TAVERN_LISTENER = "tavern_listener"  # co-present with the kin keeper; must never learn
MARKET_LISTENER = "market_listener"  # co-present with the gossip; learns at tick 0
_TAVERN = "bannered_mare"
_MARKET = "whiterun_market"

# The privacy classification (construction-time, mutation_candidates idiom):
# this claim kind is private, and its "subject" slot names who it's about.
_CLAIM_PRIVACY = {_CLAIM_KIND: "subject"}


def _driver(run_id: str) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=(
            ScheduleBlock(npc_id=KIN_KEEPER, location_id=_TAVERN, start_tick=0, end_tick=_TICKS),
            ScheduleBlock(npc_id=TAVERN_LISTENER, location_id=_TAVERN, start_tick=0, end_tick=_TICKS),
            ScheduleBlock(npc_id=TAVERN_GOSSIP, location_id=_MARKET, start_tick=0, end_tick=_TICKS),
            ScheduleBlock(npc_id=MARKET_LISTENER, location_id=_MARKET, start_tick=0, end_tick=_TICKS),
        ),
        encounter_probability=1.0,
        claim_privacy=_CLAIM_PRIVACY,
    )


def _the_secret_gets_out(driver: Driver) -> None:
    """Both holders witness the secret first-hand at tick 0 (the rung's 'two NPCs learn')."""
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id=KIN_KEEPER,
            perpetrator_id="player", crime_type="trespass", location_id="the_tomb",
        ),
        origin={"kind": "scenario", "detail": "test_tier3_tell_decision"},
    )
    for witness_id in (KIN_KEEPER, TAVERN_GOSSIP):
        driver.witness(
            claim_id=_CLAIM_ID,
            belief_id=f"belief-{witness_id}-secret",
            evidence_id=f"evidence-{witness_id}-secret",
            kind=_CLAIM_KIND,
            slots=dict(_CLAIM_SLOTS),
            canonical_event_key=EventKey(_SAVE, 0, 1),
            witness_id=witness_id,
            gamets=0.0,
        )
    # The motive: the keeper is kin to the secret's subject (rule 15 stage 1
    # reads this caller-looked-up edge, driver-side -- never inside claims).
    driver.form_relationship(
        id="rel-keeper-player", from_id=KIN_KEEPER, to_id="player",
        basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
    )


def _trace(driver: Driver) -> list[tuple[int, dict]]:
    reader = FrameLogReader(driver.writer.run_dir)
    return [(record["tick"], record["payload"]) for record in reader.records("trace")]


def test_t34_motivated_holder_never_transmits_and_declines_by_name_each_opportunity():
    driver = _driver("scenario-tier3-tell-decision")
    _the_secret_gets_out(driver)
    driver.run(0, _TICKS)
    driver.close()

    trace = _trace(driver)
    transmitted = [p for _t, p in trace if p.get("record_type") == "transmitted"]
    declined = [p for _t, p in trace if p.get("record_type") == "transmission_declined"]
    encounters = [p for _t, p in trace if p.get("record_type") == "encounter_rolled"]
    gate_evals = [
        p for _t, p in trace
        if p.get("record_type") == "rule_evaluated" and p.get("rule") == TELL_DECISION_POLICY
    ]

    # The motivated holder: zero transmissions, ever (scan all ticks).
    assert not [p for p in transmitted if p["teller_id"] == KIN_KEEPER]
    assert driver.claims.belief_of(TAVERN_LISTENER, _CLAIM_ID) is None

    # Every co-presence encounter between the keeper and his listener --
    # and exactly those -- produced a decline naming the rule.
    opportunities = [
        p for p in encounters
        if p["encountered"] and {p["npc_a"], p["npc_b"]} == {KIN_KEEPER, TAVERN_LISTENER}
    ]
    assert len(opportunities) == _TICKS  # p=1.0, co-present every tick: no-opportunity can't masquerade
    assert len(declined) == len(opportunities)
    for row in declined:
        assert set(row) == {"record_type", "claim_id", "teller_id", "hearer_id", "location_id", "rule", "roll_key"}
        assert row["rule"] == TELL_DECISION_POLICY  # declining BY NAME
        assert row["claim_id"] == _CLAIM_ID
        assert row["teller_id"] == KIN_KEEPER
        assert row["hearer_id"] == TAVERN_LISTENER
        assert row["location_id"] == _TAVERN
        assert row["roll_key"] is None  # the deterministic-decline case (R10 stage 1)

    # The unmotivated holder transmits on the normal keyed roll (threshold
    # 1.0: proceeds), once -- then both-informed closes the market pair.
    gossip_tells = [p for p in transmitted if p["teller_id"] == TAVERN_GOSSIP]
    assert len(gossip_tells) == 1
    assert gossip_tells[0]["hearer_id"] == MARKET_LISTENER
    assert driver.claims.belief_of(MARKET_LISTENER, _CLAIM_ID) is not None

    # Both outcomes emit rule_evaluated (R3: "each opportunity" is visible
    # even when the tell proceeds): one per decline (fired) + one for the
    # gossip's proceeded tell (not fired).
    assert len([p for p in gate_evals if p["fired"]]) == len(declined)
    assert len([p for p in gate_evals if not p["fired"]]) == 1
    # O5: the sub-reason lives in the evaluation's inputs, not the rule name.
    assert all(p["inputs"]["motive"] == "kin-motive" for p in gate_evals if p["fired"])
    proceeded = next(p for p in gate_evals if not p["fired"])
    assert proceeded["inputs"]["motive"] is None
    assert proceeded["inputs"]["roll_value"] is not None


def test_t34_stage2_roll_decline_carries_its_roll_key():
    """The stage-2 twin: with tell_probability below 1.0, roll-declines name
    the rule and carry the tell.decision roll_key (schema §4:121's non-null
    case) -- the stage-1 rows above carry null."""
    driver = Driver(
        run_id="scenario-tier3-tell-decision-roll",
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=(
            ScheduleBlock(npc_id=TAVERN_GOSSIP, location_id=_TAVERN, start_tick=0, end_tick=_TICKS),
            ScheduleBlock(npc_id=TAVERN_LISTENER, location_id=_TAVERN, start_tick=0, end_tick=_TICKS),
        ),
        encounter_probability=1.0,
        tell_probability=0.0,  # every stage-2 roll declines
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id=TAVERN_GOSSIP,
            perpetrator_id="player", crime_type="trespass", location_id="the_tomb",
        ),
        origin={"kind": "scenario", "detail": "test_tier3_tell_decision"},
    )
    driver.witness(
        claim_id=_CLAIM_ID,
        belief_id="belief-gossip-secret",
        evidence_id="evidence-gossip-secret",
        kind=_CLAIM_KIND,
        slots=dict(_CLAIM_SLOTS),
        canonical_event_key=EventKey(_SAVE, 0, 1),
        witness_id=TAVERN_GOSSIP,
        gamets=0.0,
    )
    # No claim_privacy mapping and no kinship edge: the gossip is
    # unmotivated, so stage 1 never fires -- only the roll decides.
    driver.run(0, _TICKS)
    driver.close()

    trace = _trace(driver)
    declined = [p for _t, p in trace if p.get("record_type") == "transmission_declined"]
    assert len(declined) == _TICKS  # the listener never learns; every tick is an opportunity
    for row in declined:
        assert set(row) == {"record_type", "claim_id", "teller_id", "hearer_id", "location_id", "rule", "roll_key"}
        assert row["rule"] == TELL_DECISION_POLICY
        assert row["roll_key"] is not None
        assert row["roll_key"]["purpose"] == "tell.decision"
        assert row["roll_key"]["draw"] == 0  # the claim's ordinal in the propagating list
    assert driver.claims.belief_of(TAVERN_LISTENER, _CLAIM_ID) is None
