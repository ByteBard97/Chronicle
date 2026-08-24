"""Scenario-ladder rung T4a.1 (Mourning) -- schedule write-back, rule 17.

Kin dies (docs/scenario-ladder.md:82). The lane-36 pins in force
(docs/design/tier-4a-schedule-write-back.md decisions T1-T7,
docs/work-packets/lane-36-schedule-write-back.md):

  - The trigger is belief acquisition (witness/first-retell/corroborate,
    rule 16's exact call sites) + a kinship edge to the deceased,
    caller-assembled in the driver, never inside the rule (T5).
  - The overlay OVERRIDES ALL of the mourner's own presence for its
    window -- and touches nobody else's (T1/T4): the precondition
    T4a.2's roll-identity guarantee depends on.
  - Restoration is `end_tick` reached, not a separate record (T2) -- the
    base schedule resumes automatically.
  - The latch is log-derived (T6): a schedule_rewrite event already
    naming this (npc, trigger_event_key) blocks a re-fire.
  - `state_at` reconstruction inside the mourning window shows the
    overlay -- the T3 fix to the latent schedule-reconstruction gap,
    asserted directly.

Fixture: jarl_balgruuf dies at tick 0 (witnessed by sven, his kin, and
independently by farkas, unrelated). sven's own base schedule keeps him
at his house with camilla and delphine, who must show no presence change
at all. The mourning destination is the temple.
"""

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.framelog import FrameLogReader
from chronicle.rules import SCHEDULE_WRITE_BACK
from chronicle.schedule import ScheduleBlock

_SEED = "tier4a-mourning"
_SAVE = "whiterun-save-1"
_TICKS = 50
_KEYFRAME_INTERVAL = 10
_MOURNING_DURATION = 20

_DECEASED = "jarl_balgruuf"
_MOURNER = "sven"
_OTHER_WITNESS = "farkas"
_CAMILLA = "camilla"
_DELPHINE = "delphine"
_HOUSE = "sven_house"
_TEMPLE = "temple"

_CLAIM_ID = "claim-balgruuf-death"
_CLAIM_KIND = "npc_death"
_MOURNING_TRIGGERS = {_CLAIM_KIND: "deceased"}

_SCHEDULE = (
    ScheduleBlock(npc_id=_MOURNER, location_id=_HOUSE, start_tick=0, end_tick=_TICKS),
    ScheduleBlock(npc_id=_CAMILLA, location_id=_HOUSE, start_tick=0, end_tick=_TICKS),
    ScheduleBlock(npc_id=_DELPHINE, location_id=_HOUSE, start_tick=0, end_tick=_TICKS),
    ScheduleBlock(npc_id=_OTHER_WITNESS, location_id=_TEMPLE, start_tick=0, end_tick=_TICKS),
)


def _driver(run_id: str) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=_SCHEDULE,
        encounter_probability=1.0,
        mourning_triggers=_MOURNING_TRIGGERS,
        mourning_location=_TEMPLE,
        mourning_duration_ticks=_MOURNING_DURATION,
        keyframe_interval=_KEYFRAME_INTERVAL,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    try:
        driver.writer.flush()
    except ValueError:  # flush of closed file -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def _the_death(driver: Driver) -> None:
    """jarl_balgruuf dies at tick 0; sven (kin) and farkas (unrelated) each witness it first-hand."""
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id=_DECEASED,
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_tier4a_mourning"},
    )
    for witness_id in (_MOURNER, _OTHER_WITNESS):
        driver.witness(
            claim_id=_CLAIM_ID,
            belief_id=f"belief-{witness_id}-balgruuf-death",
            evidence_id=f"evidence-{witness_id}-balgruuf-death",
            kind=_CLAIM_KIND,
            slots={"deceased": _DECEASED, "cause": "assassination", "location": "dragonsreach"},
            canonical_event_key=EventKey(_SAVE, 0, 1),
            witness_id=witness_id,
            gamets=0.0,
        )


def test_t4a1_mourning_inserts_the_overlay_restores_after_and_touches_nobody_else():
    driver = _driver("tier4a-mourning")
    driver.form_relationship(
        id="rel-sven-balgruuf", from_id=_MOURNER, to_id=_DECEASED,
        basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
    )
    _the_death(driver)
    driver.run(0, _TICKS)
    driver.close()

    # The schedule_rewrite event, field-for-field against schema §3:96.
    events = _records(driver, "events")
    rewrites = [p for p in events if p.get("event_type") == "schedule_rewrite"]
    assert len(rewrites) == 1
    rewrite = rewrites[0]
    assert rewrite["npc_id"] == _MOURNER
    assert rewrite["location_id"] == _TEMPLE
    assert rewrite["start_tick"] == 0
    assert rewrite["end_tick"] == _MOURNING_DURATION
    assert rewrite["cause"] == "mourning"
    assert rewrite["trigger_event_key"] == {"save_uuid": _SAVE, "generation": 0, "seq": 1}
    assert rewrite["rule"] == SCHEDULE_WRITE_BACK

    # The paired rule_evaluated row fired, naming rule 17.
    trace = _records(driver, "trace")
    fired_rows = [
        p for p in trace
        if p.get("record_type") == "rule_evaluated" and p["rule"] == SCHEDULE_WRITE_BACK and p["fired"]
    ]
    assert len(fired_rows) == 1
    assert fired_rows[0]["inputs"] == {
        "npc_id": _MOURNER,
        "deceased_id": _DECEASED,
        "kin": True,
        "already_mourning": False,
    }

    # Presence, via the actual encounter_rolled trace -- the mechanical
    # ground truth, not a re-derivation. During the window (tick 5): sven
    # is at the temple (paired with farkas there), NOT at the house.
    rolled = [p for p in trace if p.get("record_type") == "encounter_rolled"]

    def _pairs_at(tick: int, location_id: str) -> set[frozenset[str]]:
        return {
            frozenset((p["npc_a"], p["npc_b"]))
            for p in rolled
            if p["roll_key"]["tick"] == tick and p["location_id"] == location_id
        }

    during = 5
    assert frozenset((_MOURNER, _OTHER_WITNESS)) in _pairs_at(during, _TEMPLE)
    assert not any(_MOURNER in pair for pair in _pairs_at(during, _HOUSE))
    # T4's precondition: camilla and delphine, who never had anything to do
    # with the mourning, are still grouped and rolled at the house exactly
    # as if sven were never there.
    assert frozenset((_CAMILLA, _DELPHINE)) in _pairs_at(during, _HOUSE)

    # After the window (tick 25, past end_tick=20): restored to the house,
    # not the temple -- no separate "restore" record, just end_tick reached.
    after = 25
    assert frozenset((_CAMILLA, _MOURNER)) in _pairs_at(after, _HOUSE) or frozenset(
        (_DELPHINE, _MOURNER)
    ) in _pairs_at(after, _HOUSE)
    assert not any(_MOURNER in pair for pair in _pairs_at(after, _TEMPLE))


def test_t4a1_latch_blocks_a_second_mourning_for_the_same_death():
    """sven corroborating farkas's independent testimony re-runs rule 17's
    hook at the same call site as rule 16 -- the log-derived latch (a
    schedule_rewrite already exists for this npc+trigger) must block it."""
    driver = _driver("tier4a-mourning-latch")
    driver.form_relationship(
        id="rel-sven-balgruuf", from_id=_MOURNER, to_id=_DECEASED,
        basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
    )
    _the_death(driver)
    driver.corroborate(
        belief_id="belief-sven-balgruuf-death",
        source_belief=driver.belief_of(_OTHER_WITNESS, _CLAIM_ID),
        evidence_id="evidence-sven-corroborates-farkas-balgruuf-death",
        gamets=1.0,
    )
    driver.run(2, _TICKS)
    driver.close()

    events = _records(driver, "events")
    assert len([p for p in events if p.get("event_type") == "schedule_rewrite"]) == 1

    trace = _records(driver, "trace")
    rows = [
        p for p in trace
        if p.get("record_type") == "rule_evaluated"
        and p["rule"] == SCHEDULE_WRITE_BACK
        and p["inputs"]["npc_id"] == _MOURNER
    ]
    assert len(rows) == 2
    fired = [r for r in rows if r["fired"]]
    declined = [r for r in rows if not r["fired"]]
    assert len(fired) == 1 and fired[0]["inputs"]["already_mourning"] is False
    assert len(declined) == 1
    assert declined[0]["inputs"] == {
        "npc_id": _MOURNER,
        "deceased_id": _DECEASED,
        "kin": True,
        "already_mourning": True,
    }


def test_t4a1_state_at_inside_the_mourning_window_shows_the_overlay():
    """The T3 fix, asserted directly: reconstruction at a tick past the
    first keyframe (written at tick 9, per keyframe_interval=10) but still
    inside the mourning window shows sven at the temple, not the house;
    reconstruction after the window shows him restored."""
    driver = _driver("tier4a-mourning-reconstruction")
    driver.form_relationship(
        id="rel-sven-balgruuf", from_id=_MOURNER, to_id=_DECEASED,
        basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
    )
    _the_death(driver)
    driver.run(0, _TICKS)
    driver.close()

    reader = FrameLogReader(driver.writer.run_dir)

    inside = reader.state_at(15).schedule
    sven_inside = [b for b in inside if b.npc_id == _MOURNER]
    assert len(sven_inside) == 1
    assert sven_inside[0].location_id == _TEMPLE

    after = reader.state_at(30).schedule
    sven_after = [b for b in after if b.npc_id == _MOURNER]
    assert len(sven_after) == 1
    assert sven_after[0].location_id == _HOUSE


def test_no_mourning_triggers_registered_means_zero_overlays():
    """The pin's regression half: no mapping registered -> zero mourning behavior."""
    driver = Driver(
        run_id="tier4a-mourning-unmapped",
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=_SCHEDULE,
        encounter_probability=1.0,
        keyframe_interval=_KEYFRAME_INTERVAL,
    )
    driver.form_relationship(
        id="rel-sven-balgruuf", from_id=_MOURNER, to_id=_DECEASED,
        basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
    )
    _the_death(driver)
    driver.run(0, _TICKS)
    driver.close()

    events = _records(driver, "events")
    trace = _records(driver, "trace")
    assert not [p for p in events if p.get("event_type") == "schedule_rewrite"]
    assert not [p for p in trace if p.get("record_type") == "rule_evaluated" and p["rule"] == SCHEDULE_WRITE_BACK]
