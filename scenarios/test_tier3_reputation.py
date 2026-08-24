"""Scenario-ladder rung T3.5 (Status deference) -- observer-local reputation wiring.

The player becomes Thane (docs/scenario-ladder.md:76). Assert: reputation
rows update for INFORMED NPCs only; uninformed NPCs unchanged -- any global
jump is a bug. The lane-26 pins in force
(docs/work-packets/lane-26-reputation-wiring.md):

  - Reputation rows update exactly when an NPC gains or corroborates a
    belief whose claim kind is registered as reputation-relevant
    (caller-supplied mapping, the mutation_candidates idiom: claim kind ->
    (subject slot, positive, context)).
  - The evidence kind names the ACQUISITION PATH: witness -> "witnessed",
    retell (scripted or encounter-driven) -> "reported", corroborate ->
    "corroborated". Weights come from REPUTATION_WEIGHT_BY_KIND.
  - Subject/positive/context derive from the claim's slots via the
    mapping -- never a global flag. No mapping registered -> zero rows ->
    behavior identical to pre-lane-26.

Fixture: proventus and irileth witness the proclamation at Dragonsreach
(tick 0); proventus then moves to the Bannered Mare and tells hulda
through an ordinary encounter (reported); carlotta is alone at the market
and never learns (the tripwire); irileth's independent testimony later
corroborates proventus's belief (corroborated). The anchor event is a
RumorHeard proclamation -- the same "existing event class as canonical
anchor" pattern lane 23 used for the secret claim.
"""

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import RumorHeard
from chronicle.framelog import FrameLogReader
from chronicle.rules import REPUTATION_ACCUMULATION
from chronicle.schedule import ScheduleBlock

_SEED = "tier3-reputation"
_SAVE = "whiterun-save-1"
_TICKS = 12

_SUBJECT = "player"
_WITNESSES = ("proventus", "irileth")
_HEARER = "hulda"
_UNINFORMED = "carlotta"
_DRAGONSREACH = "dragonsreach"
_BANNERED_MARE = "bannered_mare"
_MARKET = "whiterun_market"

_CLAIM_ID = "claim-thanehood"
_CLAIM_KIND = "status_change"
_CLAIM_SLOTS = {"subject": _SUBJECT, "role": "thane_of_whiterun"}
# The caller-supplied registration: status_change claims are reputation-
# relevant; the subject slot names the observed party; the news is
# positive; the context is civic standing.
_REPUTATION_RELEVANCE = {_CLAIM_KIND: ("subject", True, "civic")}
_CONTEXT = "civic"

_SCHEDULE = (
    ScheduleBlock(npc_id="proventus", location_id=_DRAGONSREACH, start_tick=0, end_tick=4),
    ScheduleBlock(npc_id="proventus", location_id=_BANNERED_MARE, start_tick=4, end_tick=_TICKS),
    ScheduleBlock(npc_id="irileth", location_id=_DRAGONSREACH, start_tick=0, end_tick=4),
    ScheduleBlock(npc_id=_HEARER, location_id=_BANNERED_MARE, start_tick=0, end_tick=_TICKS),
    ScheduleBlock(npc_id=_UNINFORMED, location_id=_MARKET, start_tick=0, end_tick=_TICKS),
)


def _driver(run_id: str, *, reputation_relevance=_REPUTATION_RELEVANCE) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=_SCHEDULE,
        encounter_probability=1.0,
        reputation_relevance=reputation_relevance,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    # Scripted (pre-run/between-phase) writes sit in the writer's buffer
    # until the tick loop's per-tick flush; flush so post-construction
    # assertions read them. After close() the files are closed and already
    # flushed, so the flush is skipped.
    try:
        driver.writer.flush()
    except ValueError:  # flush of closed file -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def _the_proclamation(driver: Driver) -> None:
    """Both witnesses learn of the Thane proclamation first-hand at tick 0."""
    driver.inject_event(
        RumorHeard(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, hearer_id="proventus",
            source_id="jarl_balgruuf", rumor_id="rumor-thanehood",
            content="the player is named Thane of Whiterun",
        ),
        origin={"kind": "scenario", "detail": "test_tier3_reputation"},
    )
    for witness_id in _WITNESSES:
        driver.witness(
            claim_id=_CLAIM_ID,
            belief_id=f"belief-{witness_id}-thane",
            evidence_id=f"evidence-{witness_id}-thane",
            kind=_CLAIM_KIND,
            slots=dict(_CLAIM_SLOTS),
            canonical_event_key=EventKey(_SAVE, 0, 1),
            witness_id=witness_id,
            gamets=0.0,
        )


def test_reputation_updates_for_informed_npcs_only():
    driver = _driver("tier3-reputation")
    _the_proclamation(driver)
    # proventus moves to the Bannered Mare at tick 4 and tells hulda
    # through an ordinary encounter (encounter_probability 1.0, the tell
    # gate's default 1.0 -- a certain telling).
    driver.run(0, _TICKS)
    # irileth's independent first-hand testimony corroborates proventus's
    # belief (rule 7) -- "corroborated" reputation evidence (R11).
    driver.corroborate(
        belief_id="belief-proventus-thane",
        source_belief=driver.belief_of("irileth", _CLAIM_ID),
        evidence_id="evidence-irileth-corroborates-proventus-thane",
        gamets=float(_TICKS),
    )
    driver.close()

    rows = [p for p in _records(driver, "trace") if p.get("record_type") == "reputation_updated"]

    # Every informed NPC has the expected rows, with the evidence kind
    # naming the acquisition path.
    by_observer: dict[str, list[str]] = {}
    for row in rows:
        by_observer.setdefault(row["observer_id"], []).append(row["kind"])
    assert set(by_observer) == {"proventus", "irileth", _HEARER}
    assert by_observer["proventus"] == ["witnessed", "corroborated"]
    assert by_observer["irileth"] == ["witnessed"]
    assert by_observer[_HEARER] == ["reported"]
    for row in rows:
        assert row["subject_id"] == _SUBJECT
        assert row["positive"] is True
        assert row["context"] == _CONTEXT

    # The observer-locality tripwire, per NPC: the uninformed NPC's
    # reputation store is byte-identical to its pre-event state -- she has
    # no rows at all, in the trace or the store.
    assert _UNINFORMED not in by_observer
    assert driver.social.reputation(_UNINFORMED, _SUBJECT, _CONTEXT) is None

    # Each update carries a paired rule_evaluated row naming rule 16.
    rule_rows = [
        p for p in _records(driver, "trace")
        if p.get("record_type") == "rule_evaluated" and p["rule"] == REPUTATION_ACCUMULATION
    ]
    assert len(rule_rows) == len(rows)
    assert {(p["inputs"]["observer_id"], p["inputs"]["kind"]) for p in rule_rows} == {
        (row["observer_id"], row["kind"]) for row in rows
    }
    for rule_row in rule_rows:
        assert rule_row["fired"] is True
        assert rule_row["inputs"]["claim_id"] == _CLAIM_ID
        assert rule_row["inputs"]["subject_id"] == _SUBJECT
        assert set(rule_row["result"]) == {"alpha", "beta", "uncertainty"}

    # The store agrees: hulda's reported row is witness-bucket evidence
    # (weight 0.5), proventus's witnessed+corroborated rows accumulate.
    hulda_rep = driver.social.reputation(_HEARER, _SUBJECT, _CONTEXT)
    assert hulda_rep is not None and hulda_rep.witness_count == 1
    proventus_rep = driver.social.reputation("proventus", _SUBJECT, _CONTEXT)
    assert proventus_rep is not None
    assert proventus_rep.direct_count == 1 and proventus_rep.witness_count == 1


def test_no_mapping_registered_means_zero_rows():
    """The pin's regression half: no reputation_relevance mapping -> behavior identical to pre-lane-26."""
    driver = _driver("tier3-reputation-unmapped", reputation_relevance=None)
    _the_proclamation(driver)
    driver.run(0, _TICKS)
    driver.close()

    trace = _records(driver, "trace")
    # Beliefs still form and spread -- only the reputation wiring is absent.
    assert [p for p in trace if p.get("record_type") == "belief_formed"]
    assert [p for p in trace if p.get("record_type") == "transmitted"]
    assert not [p for p in trace if p.get("record_type") == "reputation_updated"]
    assert not [
        p for p in trace
        if p.get("record_type") == "rule_evaluated" and p["rule"] == REPUTATION_ACCUMULATION
    ]
    assert driver.social.reputation("proventus", _SUBJECT, _CONTEXT) is None
