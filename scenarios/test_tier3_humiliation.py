"""Scenario-ladder rung T3.2 (Humiliation) -- rule 12 (grudge creation) end to end.

docs/scenario-ladder.md:73, verbatim:

    T3.2 Humiliation. Public brawl loss, 6 witnesses. Assert: grudge
    created, emotional > evidentiary strength; witnesses hold beliefs;
    grudge decays slower than the rumor (now assertable -- grudge decay
    exists as of this tier).

This is the only ladder-named test exercising rule 12 (GRUDGE_CREATION,
chronicle/driver.py's suffer_harm). Rule 12's gate/latch mechanics
(fires once, then non-fires on already_exists; disabled suppresses
entirely) already have focused unit coverage in
chronicle/tests/test_rules.py (test_grudge_creation_rule_fires_once_
then_latches, test_disabling_grudge_creation_suppresses_it) -- this test
does not repeat that; it drives the full T3.2 scenario shape instead:
one humiliated NPC, 6 independent witnesses to the same public event,
and the decay-rate comparison rule 13's grudge_at() makes assertable.

Fixture shape, deliberately explicit: 7 named NPCs total. _LOSER is the
one humiliated in the brawl and is NOT one of the "6 witnesses" the
ladder names -- the ladder's 6 witnesses are onlookers, distinct from
the person the humiliation happened to. All 7 (loser + 6 onlookers)
witness the same public event and each get their own first-hand belief
on the one shared claim (chronicle/claims.py's shared-claim invariant:
one canonical_event_key -> one claim_id, a second witness reuses that
claim_id rather than minting a new claim). The loser's own belief about
their own humiliation becomes suffer_harm's source_belief_id -- the
grudge is derived from a belief, not from the event directly.

CrimeWitnessed is reused with crime_type="public_humiliation" (the same
idiom test_tier3_accumulation.py uses with crime_type="theft" -- the
event's crime_type is a plain caller-supplied string, no enum
validation on the class).
"""

import pytest

from chronicle.claims import CONFIDENCE_DECAY_HALF_LIFE, EventKey, decay
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed
from chronicle.framelog import FrameLogReader
from chronicle.schedule import ScheduleBlock
from chronicle.social import GRUDGE_EMOTIONAL_HALF_LIFE, GRUDGE_EVIDENTIARY_HALF_LIFE, grudge_at

_SEED = "tier3-humiliation"
_SAVE = "whiterun-save-1"

_LOSER = "uthgerd"  # publicly humiliated -- the grudge's holder_id AND victim_id (O3 self-victim bypass)
_BULLY = "nazeem"  # who humiliated them -- the grudge's target_id
_WITNESSES = ("adrianne", "ulfberth", "hulda", "saadia", "mikael", "carlotta")  # the ladder's "6 witnesses"
_SQUARE = "whiterun_plains_district"

_HUMILIATION_KIND = "public_humiliation"
_EVENT_KEY = EventKey(_SAVE, 0, 1)
_GAMETS = 0.0

# T3.2's evidentiary_strength is caller-supplied, never derived (the T2.3
# lesson, restated for rule 12 in suffer_harm's docstring). Picked well
# inside (0.3, 0.6) so "emotional (1.0, the O3 bypass) > evidentiary"
# isn't a coincidence of numbers that happen to be close.
_EVIDENTIARY_STRENGTH = 0.4


def _driver(run_id: str) -> Driver:
    cast = (_LOSER, _BULLY, *_WITNESSES)
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=tuple(
            ScheduleBlock(npc_id=npc, location_id=_SQUARE, start_tick=0, end_tick=1) for npc in cast
        ),
        encounter_probability=0.0,  # scripted witnessing only -- no tick-loop propagation needed here
    )


def _witness_humiliation(driver: Driver, *, witness_id: str, belief_id: str) -> None:
    """One onlooker's (or the loser's own) first-hand belief about the one shared public event.

    Does NOT inject the canonical event -- EventLog.append() is idempotent
    on (save_uuid, generation, seq), so a second inject_event() call for
    the same event key would silently no-op anyway. The event is injected
    exactly once by the caller, before any witness() calls.
    """
    driver.witness(
        claim_id="claim-humiliation-uthgerd",
        belief_id=belief_id,
        evidence_id=f"evidence-{belief_id}",
        kind=_HUMILIATION_KIND,
        slots={"perpetrator": _BULLY, "victim": _LOSER, "location": _SQUARE},
        canonical_event_key=_EVENT_KEY,
        witness_id=witness_id,
        gamets=_GAMETS,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    try:
        driver.writer.flush()
    except ValueError:  # already closed -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def test_t32_public_humiliation_grudge_witnesses_and_slower_decay():
    driver = _driver("scenario-tier3-humiliation")

    # One canonical event -- the brawl loss -- injected once. witness_id on
    # the canonical CrimeWitnessed record is the loser: the humiliation
    # happened to them and they observed it too, same as any first-hand
    # witness of an event that targets them. The 6 onlookers' witnessing is
    # captured below, entirely through driver.witness() calls against this
    # one event/claim -- CrimeWitnessed itself carries only one witness_id.
    driver.inject_event(
        CrimeWitnessed(
            tick=int(_GAMETS), save_uuid=_SAVE, generation=0, seq=1,
            gamets=_GAMETS, wall_ts=0.0, witness_id=_LOSER,
            perpetrator_id=_BULLY, crime_type=_HUMILIATION_KIND, location_id=_SQUARE,
        ),
        origin={"kind": "scenario", "detail": "test_tier3_humiliation"},
    )

    # The loser witnesses their own humiliation first-hand (this belief
    # becomes suffer_harm's source_belief_id), and the 6 onlookers each
    # independently witness the same public event -- one shared claim,
    # 7 distinct beliefs.
    _witness_humiliation(driver, witness_id=_LOSER, belief_id="belief-uthgerd-own-humiliation")
    for npc in _WITNESSES:
        _witness_humiliation(driver, witness_id=npc, belief_id=f"belief-{npc}-humiliation")

    # -- 6 witnesses hold beliefs on the humiliation claim --
    claim_id = "claim-humiliation-uthgerd"
    for npc in _WITNESSES:
        belief = driver.claims.belief_of(npc, claim_id)
        assert belief is not None
        assert belief.claim_id == claim_id
    loser_belief = driver.claims.belief_of(_LOSER, claim_id)
    assert loser_belief is not None

    belief_formed_rows = [p for p in _records(driver, "trace") if p.get("record_type") == "belief_formed" and p.get("claim_id") == claim_id]
    assert len(belief_formed_rows) == 7  # loser + 6 onlookers, one shared claim, no orphans
    assert {row["holder_id"] for row in belief_formed_rows} == {_LOSER, *_WITNESSES}

    # -- grudge created, emotional > evidentiary strength --
    grudge = driver.suffer_harm(
        holder_id=_LOSER,
        target_id=_BULLY,
        grievance_type="humiliation",
        source_belief_id=loser_belief.id,
        evidentiary_strength=_EVIDENTIARY_STRENGTH,
        gamets=_GAMETS,
    )
    assert grudge is not None
    assert driver.social.grudge(_LOSER, _BULLY) is grudge
    assert grudge.holder_id == _LOSER and grudge.target_id == _BULLY
    # O3 self-victim bypass (chronicle/social.py's form_grudge): holder_id
    # == victim_id has no relationship edge to read emotional strength
    # from, so self-regard is total.
    assert grudge.emotional_strength == 1.0
    assert grudge.evidentiary_strength == _EVIDENTIARY_STRENGTH
    assert grudge.emotional_strength > grudge.evidentiary_strength  # T3.2's assertion shape

    # grudge_formed trace record (docs/frame-log-schema.md:127) -- neither
    # of lane 2's chronicle/tests/test_rules.py rule-12 tests asserts this
    # payload (they filter to rule_evaluated rows only). source_belief_id
    # here is the check that "a grudge is derived from a belief, not from
    # the event directly" (chronicle/social.py's form_grudge docstring)
    # actually holds for this fixture, not just asserted in prose.
    grudge_formed_rows = [p for p in _records(driver, "trace") if p.get("record_type") == "grudge_formed" and p.get("id") == grudge.id]
    assert len(grudge_formed_rows) == 1
    row = grudge_formed_rows[0]
    assert set(row) == {
        "record_type", "id", "holder_id", "target_id", "source_belief_id",
        "grievance_type", "severity", "emotional_strength", "evidentiary_strength",
        "last_rehearsed", "forgiveness_threshold",
    }
    assert row["holder_id"] == _LOSER
    assert row["target_id"] == _BULLY
    assert row["source_belief_id"] == loser_belief.id
    assert row["grievance_type"] == "humiliation"
    assert row["emotional_strength"] == 1.0
    assert row["evidentiary_strength"] == _EVIDENTIARY_STRENGTH

    driver.close()

    # -- grudge decays slower than the rumor --
    #
    # Rule 13's half-lives (chronicle/social.py) are ordered, by construction,
    # slower than rule 6's belief-confidence half-life (chronicle/claims.py):
    #   GRUDGE_EMOTIONAL_HALF_LIFE   = 672 ticks (~28 game-days)
    #   GRUDGE_EVIDENTIARY_HALF_LIFE = 336 ticks (~14 game-days)
    #   CONFIDENCE_DECAY_HALF_LIFE   = 168 ticks (~7 game-days)
    # so severity's decay (a weighted blend of the two grudge half-lives)
    # is slower than confidence's decay at every elapsed time > 0. All
    # three are placeholder tunables (docs/decisions/open-questions.md);
    # only their *ordering* is load-bearing, so the expected retained
    # fractions below are recomputed from the actual imported constants
    # -- never pinned decimals that would fight a later retune -- at a
    # concrete, non-boundary elapsed of 336 ticks (14 game-days): two
    # evidentiary half-lives, one confidence half-life doubled.
    assert GRUDGE_EMOTIONAL_HALF_LIFE > GRUDGE_EVIDENTIARY_HALF_LIFE > CONFIDENCE_DECAY_HALF_LIFE
    later_gamets = _GAMETS + 336.0
    elapsed = later_gamets - _GAMETS

    decayed_grudge = grudge_at(grudge, later_gamets)
    grudge_retained = decayed_grudge.severity / grudge.severity

    a_witness = _WITNESSES[0]
    witness_belief = driver.claims.belief_of(a_witness, claim_id)
    decayed_witness_belief = decay(witness_belief, later_gamets)
    rumor_retained = decayed_witness_belief.confidence / witness_belief.confidence

    expected_emotional = 0.5 ** (elapsed / GRUDGE_EMOTIONAL_HALF_LIFE)
    expected_evidentiary = _EVIDENTIARY_STRENGTH * 0.5 ** (elapsed / GRUDGE_EVIDENTIARY_HALF_LIFE)
    expected_severity = min(1.0, 0.5 * expected_emotional + 0.5 * expected_evidentiary)
    expected_grudge_retained = expected_severity / grudge.severity
    expected_rumor_retained = 0.5 ** (elapsed / CONFIDENCE_DECAY_HALF_LIFE)  # confidence decay is a pure fraction of itself

    assert grudge_retained == pytest.approx(expected_grudge_retained)
    assert rumor_retained == pytest.approx(expected_rumor_retained)
    assert grudge_retained > rumor_retained
