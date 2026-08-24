"""Scenario-ladder rung T3.3 (Favor ledger) -- the obligation violation cascade.

Three favors; invoke one (consumed); refuse one (docs/scenario-ladder.md:74).
The lane-25 pins in force (docs/work-packets/lane-25-obligation-violation.md):

  - The cascade lives in the existing violate_obligation wrapper, after the
    obligation_resolved write, as ONE rule-14 evaluation (one
    rule_evaluated row naming the obligation, grudge id + reputation rows
    in result).
  - Grudge: issuer against debtor, grievance_type "obligation_violated",
    caller-supplied evidentiary strength. The issuer is the wronged party,
    so this is form_grudge's ruled O3 self-victim bypass -- no synthetic
    self-edge, emotional strength 1.0.
  - Reputation: one witnessed, negative row per PRESENT observer --
    obligation.witnesses intersected with caller-supplied co-located
    presence (npcs_present_at) -- subject the debtor, context the action.
    Absent witnesses and present non-witnesses get nothing.
  - The cascade fires only when the caller supplies
    violation_evidentiary_strength; a plain violation stays exactly the
    pre-lane-25 behavior.

Fixture: adrianne holds three favors over ulfberth. One is fulfilled
(consumed -- no cascade), one is refused in front of proventus and hulda;
carlotta is a named witness but across town, and olfrid is present but
not a witness. The third favor stays active.
"""

from chronicle.driver import Driver
from chronicle.framelog import FrameLogReader
from chronicle.rules import OBLIGATION_LIFECYCLE
from chronicle.schedule import ScheduleBlock, npcs_present_at

_SEED = "tier3-obligations"
_SAVE = "whiterun-save-1"
_TICKS = 8

_ISSUER = "adrianne"
_DEBTOR = "ulfberth"
_PRESENT_WITNESSES = ("proventus", "hulda")
_ABSENT_WITNESS = "carlotta"  # a named witness, across town at the refusal
_NONWITNESS = "olfrid"  # co-located at the refusal, but not a witness
_WARMAIDENS = "warmaidens"
_MARKET = "whiterun_market"

_ACTION = "return the borrowed steel"
_EVIDENTIARY_STRENGTH = 0.6  # caller-supplied, from the favor's sanctions

_SCHEDULE = (
    ScheduleBlock(npc_id=_ISSUER, location_id=_WARMAIDENS, start_tick=0, end_tick=_TICKS),
    ScheduleBlock(npc_id=_DEBTOR, location_id=_WARMAIDENS, start_tick=0, end_tick=_TICKS),
    *(ScheduleBlock(npc_id=npc, location_id=_WARMAIDENS, start_tick=0, end_tick=_TICKS) for npc in _PRESENT_WITNESSES),
    ScheduleBlock(npc_id=_NONWITNESS, location_id=_WARMAIDENS, start_tick=0, end_tick=_TICKS),
    ScheduleBlock(npc_id=_ABSENT_WITNESS, location_id=_MARKET, start_tick=0, end_tick=_TICKS),
)


def _driver(run_id: str) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=_SCHEDULE,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    # Scripted (pre-run) writes sit in the writer's buffer until the tick
    # loop's per-tick flush; flush so post-construction assertions read
    # them. After close() the files are closed and already flushed, so the
    # flush is skipped.
    try:
        driver.writer.flush()
    except ValueError:  # flush of closed file -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def test_refusal_fires_grudge_and_reputation_for_present_observers():
    driver = _driver("tier3-obligations")

    # Three favors issued at tick 0; the refused one names its witnesses.
    for n in (1, 2, 3):
        driver.issue_obligation(
            id=f"obl-favor-{n}",
            issuer_id=_ISSUER,
            debtor_id=_DEBTOR,
            beneficiary_id=None,
            action=_ACTION,
            condition=None,
            gamets=0.0,
            witnesses=((*_PRESENT_WITNESSES, _ABSENT_WITNESS) if n == 2 else ()),
        )

    # Invoke one: fulfilled (consumed) -- no cascade, no grudge.
    driver.fulfill_obligation("obl-favor-1", gamets=1.0)

    # Refuse one, in front of whoever is actually at warmaiden's.
    present = npcs_present_at(driver.schedule, 2)[_WARMAIDENS]
    driver.violate_obligation(
        "obl-favor-2",
        gamets=2.0,
        violation_evidentiary_strength=_EVIDENTIARY_STRENGTH,
        present_npc_ids=present,
    )
    driver.close()

    # Exactly one violation resolution, and the fulfillment alongside it.
    resolutions = [p for p in _records(driver, "trace") if p.get("record_type") == "obligation_resolved"]
    assert [(p["obligation_id"], p["status"]) for p in resolutions] == [
        ("obl-favor-1", "fulfilled"),
        ("obl-favor-2", "violated"),
    ]

    # Exactly one grudge: issuer against debtor, the violation grievance --
    # and the fulfillment produced none.
    grudges = [p for p in _records(driver, "trace") if p.get("record_type") == "grudge_formed"]
    assert len(grudges) == 1
    (grudge,) = grudges
    assert grudge["holder_id"] == _ISSUER
    assert grudge["target_id"] == _DEBTOR
    assert grudge["grievance_type"] == "obligation_violated"
    assert grudge["evidentiary_strength"] == _EVIDENTIARY_STRENGTH
    assert grudge["emotional_strength"] == 1.0  # the O3 self-victim bypass

    # One reputation row per PRESENT observer -- witnessed, negative,
    # subject the debtor -- and none for the absent witness or the
    # co-located non-witness.
    rows = [p for p in _records(driver, "trace") if p.get("record_type") == "reputation_updated"]
    assert {p["observer_id"] for p in rows} == set(_PRESENT_WITNESSES)
    for row in rows:
        assert row["subject_id"] == _DEBTOR
        assert row["kind"] == "witnessed"
        assert row["positive"] is False
        assert row["context"] == _ACTION
    assert _ABSENT_WITNESS not in {p["observer_id"] for p in rows}
    assert _NONWITNESS not in {p["observer_id"] for p in rows}

    # One rule-14 evaluation naming the obligation, listing the products.
    rule_rows = [
        p for p in _records(driver, "trace")
        if p.get("record_type") == "rule_evaluated" and p["rule"] == OBLIGATION_LIFECYCLE
    ]
    assert len(rule_rows) == 1
    (rule_row,) = rule_rows
    assert rule_row["fired"] is True
    assert rule_row["inputs"]["obligation_id"] == "obl-favor-2"
    assert rule_row["result"]["grudge_id"] == grudge["id"]
    assert rule_row["result"]["reputation_observer_ids"] == list(_PRESENT_WITNESSES)

    # Store state agrees: the grudge exists; the absent witness holds no
    # reputation row for the debtor.
    assert driver.social.grudge(_ISSUER, _DEBTOR) is not None
    assert driver.social.reputation(_ABSENT_WITNESS, _DEBTOR, _ACTION) is None
    assert driver.social.reputation(_NONWITNESS, _DEBTOR, _ACTION) is None


def test_violation_without_cascade_parameters_is_the_pre_lane25_behavior():
    """A plain violation (no caller-supplied severity) resolves without the cascade."""
    driver = _driver("tier3-obligations-plain")
    driver.issue_obligation(
        id="obl-favor-plain",
        issuer_id=_ISSUER,
        debtor_id=_DEBTOR,
        beneficiary_id=None,
        action=_ACTION,
        condition=None,
        gamets=0.0,
        witnesses=_PRESENT_WITNESSES,
    )
    driver.violate_obligation("obl-favor-plain", gamets=1.0, excuse="the war dried up business")
    driver.close()

    trace = _records(driver, "trace")
    assert [p["status"] for p in trace if p.get("record_type") == "obligation_resolved"] == ["violated"]
    assert not [p for p in trace if p.get("record_type") == "grudge_formed"]
    assert not [p for p in trace if p.get("record_type") == "reputation_updated"]
    assert not [p for p in trace if p.get("record_type") == "rule_evaluated" and p["rule"] == OBLIGATION_LIFECYCLE]
    assert driver.social.grudge(_ISSUER, _DEBTOR) is None
