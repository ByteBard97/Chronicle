"""Scenario-ladder rung T4b.1 (Avoidance) -- pairwise encounter weighting, rule 18.

A strong grudge between a pair (docs/scenario-ladder.md:89). The
lane-40/43 pins in force (docs/design/tier-4b-avoidance.md decisions
W1-W5, docs/work-packets/lane-43-tier-4b-avoidance.md):

  - The override is a per-pair threshold REPLACEMENT
    (`AVOIDANCE_PROBABILITY = 0.0`), not a multiplier -- an avoiding
    pair's `encounter_rolled.threshold` reads 0.0 instead of the run's
    base `encounter_probability`, making "encounters... cease" an
    exact guarantee (W1).
  - No new record type: the lowered `threshold` IS the visible weight
    delta; a same-tick `rule_evaluated` row (rule 18) names the grudge
    and carries base-vs-effective probability in `result` (W2).
  - A **control pair** at the same tavern block, with no grudge, must
    encounter at the ordinary base threshold and produce no rule-18
    row at all -- proving avoidance is per-pair, not location-wide.
  - Cooling is read-time (W3): once decayed severity drops below
    `AVOIDANCE_GRUDGE_THRESHOLD`, the override stops and rule 18's rows
    continue but with `fired: false` -- nothing is deleted, nothing is
    silent.

Fixture: adrianne holds a strong grudge (severity 0.8, self-victim, no
edge needed) against ulfberth; both share the Bannered Mare with an
unrelated control pair, camilla and delphine.
"""

from chronicle.driver import Driver
from chronicle.framelog import FrameLogReader
from chronicle.rules import PAIRWISE_ENCOUNTER_WEIGHTING
from chronicle.schedule import ScheduleBlock

_SEED = "tier4b-avoidance"
_SAVE = "whiterun-save-1"
_TICKS = 10

_HOLDER = "adrianne"
_TARGET = "ulfberth"
_CAMILLA = "camilla"
_DELPHINE = "delphine"
_TAVERN = "bannered_mare"

_SCHEDULE = (
    ScheduleBlock(npc_id=_HOLDER, location_id=_TAVERN, start_tick=0, end_tick=1000),
    ScheduleBlock(npc_id=_TARGET, location_id=_TAVERN, start_tick=0, end_tick=1000),
    ScheduleBlock(npc_id=_CAMILLA, location_id=_TAVERN, start_tick=0, end_tick=1000),
    ScheduleBlock(npc_id=_DELPHINE, location_id=_TAVERN, start_tick=0, end_tick=1000),
)

_ENCOUNTER_PROBABILITY = 1.0


def _driver(run_id: str) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=_SCHEDULE,
        encounter_probability=_ENCOUNTER_PROBABILITY,
    )


def _form_the_grudge(driver: Driver) -> None:
    """A strong, self-victim grudge (O3's ruled bypass, lane 25): severity
    0.5*1.0 (emotional, self-regard is total) + 0.5*0.6 (evidentiary) =
    0.8, comfortably above AVOIDANCE_GRUDGE_THRESHOLD (0.5)."""
    driver.form_grudge(
        id="grudge-adrianne-ulfberth", holder_id=_HOLDER, victim_id=_HOLDER, target_id=_TARGET,
        grievance_type="betrayal", source_belief_id="belief-adrianne-wronged",
        evidentiary_strength=0.6, relationship_to_victim=None, gamets=0.0,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    try:
        driver.writer.flush()
    except ValueError:  # flush of closed file -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def _rolls_for(rolled: list[dict], npc_a: str, npc_b: str) -> list[dict]:
    pair = {npc_a, npc_b}
    return [p for p in rolled if {p["npc_a"], p["npc_b"]} == pair]


def test_t4b1_the_grudged_pair_never_encounters_while_the_control_pair_encounters_normally():
    driver = _driver("tier4b-avoidance")
    _form_the_grudge(driver)
    driver.run(0, _TICKS)
    driver.close()

    trace = _records(driver, "trace")
    rolled = [p for p in trace if p.get("record_type") == "encounter_rolled"]
    avoided = _rolls_for(rolled, _HOLDER, _TARGET)
    control = _rolls_for(rolled, _CAMILLA, _DELPHINE)

    assert len(avoided) == _TICKS  # co-present and rolled every tick
    for row in avoided:
        assert row["threshold"] == 0.0
        assert row["encountered"] is False

    assert len(control) == _TICKS
    for row in control:
        assert row["threshold"] == _ENCOUNTER_PROBABILITY
        assert row["encountered"] is True  # base threshold 1.0: every roll's value is < 1.0

    # The same-tick rule-18 row per avoiding roll, naming the grudge --
    # the visible reason, not a hidden multiplier.
    rule_rows = [
        p for p in trace
        if p.get("record_type") == "rule_evaluated"
        and p["rule"] == PAIRWISE_ENCOUNTER_WEIGHTING
        and {p["inputs"]["npc_a"], p["inputs"]["npc_b"]} == {_HOLDER, _TARGET}
    ]
    assert len(rule_rows) == _TICKS
    for row in rule_rows:
        assert row["fired"] is True
        assert row["inputs"]["grudge_id"] == "grudge-adrianne-ulfberth"
        # Decays negligibly over 10 ticks against 336/672-tick half-lives --
        # comfortably above the threshold throughout, not pinned to the
        # exact tick-0 value of 0.8.
        assert row["inputs"]["severity"] > 0.5
        assert row["inputs"]["threshold"] == 0.5
        assert row["result"]["base_probability"] == 1.0
        assert row["result"]["effective_probability"] == 0.0

    # No rule-18 row at all for the grudge-free control pair (bounded
    # volume: rule 18 only evaluates pairs with a grudge between them).
    control_rule_rows = [
        p for p in trace
        if p.get("record_type") == "rule_evaluated"
        and p["rule"] == PAIRWISE_ENCOUNTER_WEIGHTING
        and {p["inputs"]["npc_a"], p["inputs"]["npc_b"]} == {_CAMILLA, _DELPHINE}
    ]
    assert control_rule_rows == []


def test_t4b1_avoidance_stops_once_the_grudge_cools_below_the_threshold():
    """No behavior-threshold-without-hysteresis violation: cooling isn't a
    special record, just decayed severity read fresh -- proven directly
    by running far enough out that GRUDGE_EMOTIONAL/EVIDENTIARY_HALF_LIFE
    decay has crossed AVOIDANCE_GRUDGE_THRESHOLD (severity(0)=0.8,
    severity(390..410)~0.46-0.47 by the half-life math), without needing
    to simulate every tick in between (grudge_at is a pure function of
    elapsed gamets, not of ticks actually run)."""
    driver = _driver("tier4b-avoidance-cooled")
    _form_the_grudge(driver)
    driver.run(390, 410)
    driver.close()

    trace = _records(driver, "trace")
    rolled = [p for p in trace if p.get("record_type") == "encounter_rolled"]
    cooled_rolls = _rolls_for(rolled, _HOLDER, _TARGET)
    assert len(cooled_rolls) == 20
    for row in cooled_rolls:
        assert row["threshold"] == _ENCOUNTER_PROBABILITY  # no longer overridden
        assert row["encountered"] is True

    rule_rows = [
        p for p in trace
        if p.get("record_type") == "rule_evaluated"
        and p["rule"] == PAIRWISE_ENCOUNTER_WEIGHTING
        and {p["inputs"]["npc_a"], p["inputs"]["npc_b"]} == {_HOLDER, _TARGET}
    ]
    assert len(rule_rows) == 20
    for row in rule_rows:
        # fired:false, not absent -- the cooling grudge stays visible,
        # not silent (doctrine 3), with its current (decayed) severity.
        assert row["fired"] is False
        assert row["result"] is None
        assert 0.0 < row["inputs"]["severity"] < 0.5
    # Not cooled outright (social.grudge_cooled's own, lower floor,
    # forgiveness_threshold=0.2) -- just below the avoidance floor. The
    # grudge is still "live," simply no longer gating behavior.
    assert all(row["inputs"]["severity"] > 0.2 for row in rule_rows)


def test_no_grudges_means_zero_avoidance_rows():
    """The pin's regression half: no grudge at all -> behavior identical to pre-lane-43."""
    driver = _driver("tier4b-avoidance-unmapped")
    driver.run(0, _TICKS)
    driver.close()

    trace = _records(driver, "trace")
    rolled = [p for p in trace if p.get("record_type") == "encounter_rolled"]
    for row in rolled:
        assert row["threshold"] == _ENCOUNTER_PROBABILITY
    assert not [p for p in trace if p.get("record_type") == "rule_evaluated" and p["rule"] == PAIRWISE_ENCOUNTER_WEIGHTING]
