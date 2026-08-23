"""Scenario-ladder rung T3.1 (Serial theft) -- accumulation-threshold escalation.

Four thefts against the same merchant (docs/scenario-ladder.md:72). The
lane-24 pins in force (docs/work-packets/lane-24-accumulation-threshold.md):

  - The accumulator is DERIVED (R4): count of the merchant's beliefs whose
    claim kind is registered and whose victim slot names the merchant. The
    kind registration is caller-supplied (accumulation_thresholds), the
    mutation_candidates idiom.
  - The latch (R5) is store-derived: once the escalation-warning belief
    exists, no recount can re-fire -- theft five fires nothing.
  - The escalation materializes as an EVENT first (R6); the warning claim
    is witnessed off its canonical key by the merchant themselves, and
    propagates to the peer merchant only through Tier-1/2 encounters.
  - Evaluation happens exactly where a matching belief forms, never
    per-tick -- the "counter stuck at 3-of-4" rows are rule_evaluated
    (fired=false), visible not silent.

Fixture: two merchants co-present at the market; four scripted thefts the
merchant witnesses first-hand (gamets 0-3), then the tick loop runs, then
a fifth theft after the run proves the latch across phases.
"""

from chronicle.claims import EventKey
from chronicle.driver import ESCALATION_WARNING_CLAIM_KIND, Driver
from chronicle.events import CrimeWitnessed
from chronicle.framelog import FrameLogReader
from chronicle.rules import ACCUMULATION_THRESHOLD
from chronicle.schedule import ScheduleBlock

_SEED = "tier3-accumulation"
_SAVE = "whiterun-save-1"
_TICKS = 48  # two game-days (ADR-0010)

_MERCHANT = "belethor"
_PEER = "carlotta"  # the peer merchant: informed only via encounters
_THIEF = "a pickpocket"
_MARKET = "whiterun_market"

_THEFT_KIND = "theft"
# The caller-supplied registration: theft claims accumulate, the victim
# slot names the aggrieved party, four strikes trigger the escalation.
_ACCUMULATION_THRESHOLDS = {_THEFT_KIND: ("victim", 4)}
_THRESHOLD = 4


def _driver(run_id: str) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=(
            ScheduleBlock(npc_id=_MERCHANT, location_id=_MARKET, start_tick=0, end_tick=_TICKS),
            ScheduleBlock(npc_id=_PEER, location_id=_MARKET, start_tick=0, end_tick=_TICKS),
        ),
        encounter_probability=1.0,
        accumulation_thresholds=_ACCUMULATION_THRESHOLDS,
    )


def _theft(driver: Driver, n: int, *, gamets: float, seq: int | None = None) -> None:
    """The nth theft against the merchant, witnessed first-hand by them.

    seq defaults to n, but the engine's escalation event takes the next
    branch seq when it fires (theft four's escalation is seq 5), so the
    fifth theft must skip past it.
    """
    event_seq = seq if seq is not None else n
    driver.inject_event(
        CrimeWitnessed(
            tick=int(gamets), save_uuid=_SAVE, generation=0, seq=event_seq,
            gamets=gamets, wall_ts=0.0, witness_id=_MERCHANT,
            perpetrator_id=_THIEF, crime_type="theft", location_id=_MARKET,
        ),
        origin={"kind": "scenario", "detail": "test_tier3_accumulation"},
    )
    driver.witness(
        claim_id=f"claim-theft-{n}",
        belief_id=f"belief-merchant-theft-{n}",
        evidence_id=f"evidence-merchant-theft-{n}",
        kind=_THEFT_KIND,
        slots={"perpetrator": _THIEF, "victim": _MERCHANT, "location": _MARKET},
        canonical_event_key=EventKey(_SAVE, 0, event_seq),
        witness_id=_MERCHANT,
        gamets=gamets,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    # Scripted (pre-run/between-phase) writes sit in the writer's buffer
    # until the tick loop's per-tick flush; flush so mid-construction
    # assertions read them. After close() the files are closed and already
    # flushed, so the flush is skipped.
    try:
        driver.writer.flush()
    except ValueError:  # flush of closed file -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def _escalation_events(driver: Driver) -> list[dict]:
    return [p for p in _records(driver, "events") if p.get("event_type") == "escalation_warning"]


def _threshold_crossings(driver: Driver) -> list[dict]:
    return [p for p in _records(driver, "trace") if p.get("record_type") == "threshold_crossed"]


def _rule11_rows(driver: Driver) -> list[dict]:
    return [
        p
        for p in _records(driver, "trace")
        if p.get("record_type") == "rule_evaluated" and p.get("rule") == ACCUMULATION_THRESHOLD
    ]


def test_t31_serial_theft_escalates_exactly_once_and_only_via_encounters():
    driver = _driver("scenario-tier3-accumulation")

    # Below threshold: three thefts, annoyance only -- the counter is
    # visible in the trace (fired=false rows), nothing escalates.
    for n in (1, 2, 3):
        _theft(driver, n, gamets=float(n - 1))
    assert not _escalation_events(driver)
    assert not _threshold_crossings(driver)
    below = _rule11_rows(driver)
    assert [row["inputs"]["count"] for row in below] == [1, 2, 3]
    assert all(not row["fired"] for row in below)  # a counter stuck at 3-of-4, visible

    # At threshold: exactly one escalation, event-first.
    _theft(driver, 4, gamets=3.0)
    events = _escalation_events(driver)
    crossings = _threshold_crossings(driver)
    assert len(events) == 1
    assert len(crossings) == 1
    assert set(events[0]) == {"gamets", "wall_ts", "origin", "event_type", "holder_id", "grievance_kind", "count", "threshold"}
    assert events[0]["holder_id"] == _MERCHANT
    assert events[0]["grievance_kind"] == _THEFT_KIND
    assert events[0]["count"] == _THRESHOLD
    assert events[0]["threshold"] == _THRESHOLD
    assert events[0]["origin"] is None  # engine-internal
    crossing = crossings[0]
    assert set(crossing) == {"record_type", "rule", "accumulator", "threshold", "produced"}
    assert crossing["rule"] == ACCUMULATION_THRESHOLD
    assert crossing["accumulator"]["holder_id"] == _MERCHANT
    assert crossing["accumulator"]["count"] == _THRESHOLD
    assert len(crossing["accumulator"]["belief_ids"]) == _THRESHOLD
    assert crossing["threshold"] == _THRESHOLD

    # The warning claim hangs off the event's canonical key -- no orphan.
    warning_claim_id = crossing["produced"]["claim_id"]
    event_key = crossing["produced"]["event_key"]
    warning_claim = driver.claims.claim(warning_claim_id)
    assert warning_claim.kind == ESCALATION_WARNING_CLAIM_KIND
    assert warning_claim.canonical_event_key == EventKey(_SAVE, 0, 4 + 1)  # the escalation took the next seq
    assert (event_key["save_uuid"], event_key["generation"], event_key["seq"]) == (_SAVE, 0, 5)
    merchant_warning = driver.claims.belief_of(_MERCHANT, warning_claim_id)
    assert merchant_warning is not None

    # Propagation is encounters-only: the peer holds nothing until the tick
    # loop runs; then a transmitted record carries it, never a broadcast.
    assert driver.claims.belief_of(_PEER, warning_claim_id) is None
    driver.run(4, _TICKS // 2)

    # Theft five, between run phases (the T2.7 idiom -- no writing after
    # close): the latch holds, nothing new fires. seq 6: the escalation
    # event took seq 5 when theft four fired.
    _theft(driver, 5, gamets=float(_TICKS // 2), seq=6)
    assert len(_escalation_events(driver)) == 1
    assert len(_threshold_crossings(driver)) == 1
    latched_row = _rule11_rows(driver)[-1]
    assert latched_row["inputs"]["count"] == 5
    assert latched_row["inputs"]["latched"] is True
    assert not latched_row["fired"]

    driver.run(_TICKS // 2 + 1, _TICKS)
    driver.close()
    peer_warning = driver.claims.belief_of(_PEER, warning_claim_id)
    assert peer_warning is not None
    warning_transmissions = [
        p
        for p in _records(driver, "trace")
        if p.get("record_type") == "transmitted" and p["claim_id"] == warning_claim_id
    ]
    assert warning_transmissions
    assert all(p["teller_id"] in (_MERCHANT, _PEER) for p in warning_transmissions)


def test_t31_reconstruction_parity_no_double_fire_on_replay():
    """state_at over the firing tick: the latch is log-derived state, so
    replay rebuilds exactly one escalation and cannot re-fire it."""
    driver = _driver("scenario-tier3-accumulation-replay")
    for n in (1, 2, 3, 4):
        _theft(driver, n, gamets=float(n - 1))
    driver.run(4, _TICKS)
    driver.close()

    reader = FrameLogReader(driver.writer.run_dir)
    state = reader.state_at(_TICKS - 1)
    escalation_claims = [
        belief
        for belief in state.claims.beliefs_of(_MERCHANT)
        if state.claims.claim(belief.claim_id).kind == ESCALATION_WARNING_CLAIM_KIND
    ]
    assert len(escalation_claims) == 1
    # The reconstructed peer learned it too (replay re-executes the
    # encounter-driven transmitted records).
    assert state.claims.belief_of(_PEER, escalation_claims[0].claim_id) is not None
