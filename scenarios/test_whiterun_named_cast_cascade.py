"""Scenario: the Braith/Lucia marketplace incident, run over the REAL grown
Whiterun cast (chronicle/fixtures/whiterun_schedule.py,
chronicle/fixtures/whiterun_relationships.py) -- not a bespoke fixture that
happens to reuse the same names.

This is the missing proof that the 2026-08-26 fixture-growth pass (6 -> 19
named NPCs) actually composes: everything below is driven through
whiterun_schedule()/seed_whiterun_via_driver(), the same functions any
other caller of the grown fixture would use.

Narrative: Braith publicly humiliates Lucia (Carlotta's daughter) at the
Whiterun marketplace. Three NPCs who share a schedule block there --
Lucia herself, her mother Carlotta, and the weaver Lillith Maiden-Loom --
witness it first-hand (rule 1, WITNESS_CREATES_BELIEF; rule 4, the
shared-claim invariant, implicitly: one canonical_event_key, one claim,
three independent beliefs). Lucia's own humiliation gives her a grudge
against Braith (rule 12, GRUDGE_CREATION, Driver.suffer_harm's self-victim
bypass -- the same O3 pattern test_tier3_humiliation.py demonstrates).

The story then travels by two scripted retellings (rule 5,
TESTIMONY_TRANSFER) that deliberately exercise rule 20 (trust-discounted
retelling) on BOTH sides of its no-relationship default: Carlotta tells
Saffir, who has no seeded relationship edge to Carlotta at all (trust
falls back to the no-relationship default), and Saffir then tells her own
husband Amren, who DOES have a seeded kinship edge to her
(chronicle/fixtures/whiterun_relationships.py's rel-amren-saffir, strength
0.9) -- so the second hop keeps a real, larger share of confidence than
the first. Finally the tick loop runs (rule 6, ENCOUNTER_SAMPLING) so the
remaining un-informed marketplace regular -- Braith herself -- can pick up
the story the ordinary encounter-driven way, proving rules 5/6 aren't just
scripted idioms but actually fire together over this cast. A late
grudge_at() check (rule 13, GRUDGE_DECAY) closes the loop, same
decay-rate-ordering idiom as test_tier3_humiliation.py.
"""

import pytest

from chronicle.claims import (
    CONFIDENCE_DECAY_HALF_LIFE,
    RETELL_CONFIDENCE_DECAY,
    TRUST_FLOOR,
    EventKey,
    decay,
)
from chronicle.driver import NO_RELATIONSHIP_TRUST, TRUST_RELATIONSHIP_BASES, Driver
from chronicle.events import CrimeWitnessed
from chronicle.fixtures.whiterun_relationships import seed_whiterun_via_driver
from chronicle.fixtures.whiterun_schedule import whiterun_schedule
from chronicle.framelog import FrameLogReader
from chronicle.social import (
    GRUDGE_EMOTIONAL_HALF_LIFE,
    GRUDGE_EVIDENTIARY_HALF_LIFE,
    grudge_at,
)

_SEED = "whiterun-named-cast-cascade"
_SAVE = "whiterun-save-1"
_MARKET = "whiterun_marketplace"

_BULLY = "braith"
_VICTIM = "lucia"  # Carlotta's daughter -- the marketplace fixture's own kinship edge
_MOTHER = "carlotta_valentia"
_HUSBAND = "amren"
_WIFE = "saffir"
_WEAVER = "lillith_maiden_loom"

_INCIDENT_KIND = "public_humiliation"
_CLAIM_ID = "claim-braith-humiliates-lucia"
_GAMETS = 150.0  # inside every marketplace regular's overlapping schedule block (100-400/500/600)
_EVENT_KEY = EventKey(_SAVE, 0, 1)


def _driver(run_id: str) -> Driver:
    # The REAL grown fixture schedule, unmodified -- not a hand-rolled
    # parallel cast. encounter_probability=1.0 so the later tick-loop phase
    # deterministically exercises rule 6 rather than leaving it to chance.
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=whiterun_schedule(),
        encounter_probability=1.0,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    try:
        driver.writer.flush()
    except ValueError:  # already closed -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def _trust(driver: Driver, *, hearer_id: str, teller_id: str) -> float:
    """The same lookup Driver._trust_for_retelling makes (rule 20): hearer's
    regard for teller, max strength over the qualifying bases, or the
    no-relationship default. Reproduced here (over the public
    driver.social.relationship() accessor) so the scripted retells below
    can pass trust the same way the encounter-driven path computes it,
    without reaching into the driver's private method."""
    strengths = [
        rel.strength
        for basis in TRUST_RELATIONSHIP_BASES
        if (rel := driver.social.relationship(hearer_id, teller_id, basis)) is not None
    ]
    return max(strengths) if strengths else NO_RELATIONSHIP_TRUST


def _effective_decay(trust: float) -> float:
    return RETELL_CONFIDENCE_DECAY * (TRUST_FLOOR + (1 - TRUST_FLOOR) * trust)


def _witness(driver: Driver, *, witness_id: str, belief_id: str):
    return driver.witness(
        claim_id=_CLAIM_ID,
        belief_id=belief_id,
        evidence_id=f"evidence-{belief_id}",
        kind=_INCIDENT_KIND,
        slots={"perpetrator": _BULLY, "victim": _VICTIM, "location": _MARKET},
        canonical_event_key=_EVENT_KEY,
        witness_id=witness_id,
        gamets=_GAMETS,
    )


def test_braith_humiliates_lucia_cascades_through_the_grown_marketplace_cast():
    driver = _driver("scenario-whiterun-named-cast-cascade")

    # Every relationship edge the grown fixture seeds, through the driver
    # so formation lands in the frame log (relationship_formed, schema §4).
    seed_whiterun_via_driver(driver, gamets=0.0)

    driver.inject_event(
        CrimeWitnessed(
            tick=int(_GAMETS), save_uuid=_SAVE, generation=0, seq=1,
            gamets=_GAMETS, wall_ts=0.0, witness_id=_VICTIM,
            perpetrator_id=_BULLY, crime_type=_INCIDENT_KIND, location_id=_MARKET,
        ),
        origin={"kind": "scenario", "detail": "test_whiterun_named_cast_cascade"},
    )

    # -- rule 1 + rule 4: three independent first-hand witnesses, one claim --
    _, lucia_belief, _ = _witness(driver, witness_id=_VICTIM, belief_id="belief-lucia-own-humiliation")
    _, carlotta_belief, _ = _witness(driver, witness_id=_MOTHER, belief_id="belief-carlotta-witnessed")
    _witness(driver, witness_id=_WEAVER, belief_id="belief-lillith-witnessed")

    for npc in (_VICTIM, _MOTHER, _WEAVER):
        belief = driver.claims.belief_of(npc, _CLAIM_ID)
        assert belief is not None
        assert belief.claim_id == _CLAIM_ID

    belief_formed_rows = [
        p for p in _records(driver, "trace") if p.get("record_type") == "belief_formed" and p.get("claim_id") == _CLAIM_ID
    ]
    assert len(belief_formed_rows) == 3
    assert {row["holder_id"] for row in belief_formed_rows} == {_VICTIM, _MOTHER, _WEAVER}

    # -- rule 12: Lucia's grudge against Braith, the self-victim (O3) bypass --
    evidentiary_strength = 0.4
    grudge = driver.suffer_harm(
        holder_id=_VICTIM,
        target_id=_BULLY,
        grievance_type="humiliation",
        source_belief_id=lucia_belief.id,
        evidentiary_strength=evidentiary_strength,
        gamets=_GAMETS,
    )
    assert grudge is not None
    assert driver.social.grudge(_VICTIM, _BULLY) is grudge
    assert grudge.emotional_strength == 1.0  # no relationship edge to draw from -- total self-regard
    assert grudge.evidentiary_strength == evidentiary_strength
    assert grudge.emotional_strength > grudge.evidentiary_strength  # T3.2's assertion shape

    claim = driver.claims.claim(_CLAIM_ID)

    # -- rule 5 + rule 20: Carlotta -> Saffir, no seeded relationship edge --
    trust_saffir = _trust(driver, hearer_id=_WIFE, teller_id=_MOTHER)
    assert trust_saffir == NO_RELATIONSHIP_TRUST  # no carlotta<->saffir edge anywhere in the fixture
    variant_to_saffir, saffir_belief, _ = driver.retell(
        claim=claim, parent_variant=None, variant_id="variant-carlotta-to-saffir",
        belief_id="belief-saffir-heard", evidence_id="evidence-saffir-heard",
        teller_id=_MOTHER, teller_belief=carlotta_belief, hearer_id=_WIFE,
        gamets=_GAMETS + 10.0, trust=trust_saffir,
    )

    # -- rule 5 + rule 20: Saffir -> Amren, the fixture's real amren<->saffir kinship edge --
    trust_amren = _trust(driver, hearer_id=_HUSBAND, teller_id=_WIFE)
    assert trust_amren == pytest.approx(0.9)  # rel-amren-saffir's seeded strength (whiterun_relationships.py)
    _, amren_belief, _ = driver.retell(
        claim=claim, parent_variant=variant_to_saffir, variant_id="variant-saffir-to-amren",
        belief_id="belief-amren-heard", evidence_id="evidence-amren-heard",
        teller_id=_WIFE, teller_belief=saffir_belief, hearer_id=_HUSBAND,
        gamets=_GAMETS + 20.0, trust=trust_amren,
    )

    # -- rule 20's contrast, made concrete: the kin-trust hop keeps a
    # strictly larger share of confidence than the no-relationship hop.
    # Both still fall short of the pre-rule-20 flat 0.8 (that value is only
    # reached at trust=1.0, which nothing in this cast has) -- rule 20
    # discounts every real retelling here, just by different amounts. --
    saffir_retention = saffir_belief.confidence / carlotta_belief.confidence
    amren_retention = amren_belief.confidence / saffir_belief.confidence
    assert saffir_retention == pytest.approx(_effective_decay(trust_saffir))
    assert amren_retention == pytest.approx(_effective_decay(trust_amren))
    assert saffir_retention < amren_retention < RETELL_CONFIDENCE_DECAY
    assert amren_retention > saffir_retention  # rule 20 has a REAL effect on this cast, not just on paper
    assert carlotta_belief.confidence * saffir_retention == pytest.approx(saffir_belief.confidence)

    scripted_transmissions = {
        p["hearer_id"]: p
        for p in _records(driver, "trace")
        if p.get("record_type") == "transmitted" and p.get("claim_id") == _CLAIM_ID and p.get("hearer_id") in (_WIFE, _HUSBAND)
    }
    assert scripted_transmissions[_WIFE]["trust_applied"] == pytest.approx(NO_RELATIONSHIP_TRUST)
    assert scripted_transmissions[_HUSBAND]["trust_applied"] == pytest.approx(0.9)

    # -- rules 5/6 together: run the tick loop so the one remaining
    # un-informed marketplace regular -- Braith herself -- can pick up the
    # story the ordinary encounter-driven way (real ENCOUNTER_SAMPLING
    # rolls, not a scripted witness()/retell() call). --
    driver.run(int(_GAMETS) + 21, 500)
    driver.close()

    encounter_transmissions = [
        p
        for p in _records(driver, "trace")
        if p.get("record_type") == "transmitted" and p.get("claim_id") == _CLAIM_ID and p.get("location_id") == _MARKET
    ]
    assert encounter_transmissions  # rule 6's encounter sampling actually carried the story further
    assert any(p["fired"] for p in _records(driver, "trace") if p.get("record_type") == "rule_evaluated" and p.get("rule") == "encounter-sampling")
    braith_belief = driver.claims.belief_of(_BULLY, _CLAIM_ID)
    assert braith_belief is not None  # the bully herself hears what the marketplace is saying

    # -- rule 13: Lucia's grudge decays, at a later gamets, per the ordered half-lives --
    later_gamets = _GAMETS + GRUDGE_EVIDENTIARY_HALF_LIFE
    elapsed = later_gamets - _GAMETS
    decayed_grudge = grudge_at(grudge, later_gamets)
    grudge_retained = decayed_grudge.severity / grudge.severity

    decayed_lucia_belief = decay(lucia_belief, later_gamets)
    rumor_retained = decayed_lucia_belief.confidence / lucia_belief.confidence

    expected_emotional = 0.5 ** (elapsed / GRUDGE_EMOTIONAL_HALF_LIFE)
    expected_evidentiary = evidentiary_strength * 0.5 ** (elapsed / GRUDGE_EVIDENTIARY_HALF_LIFE)
    expected_severity = min(1.0, 0.5 * expected_emotional + 0.5 * expected_evidentiary)
    expected_grudge_retained = expected_severity / grudge.severity
    expected_rumor_retained = 0.5 ** (elapsed / CONFIDENCE_DECAY_HALF_LIFE)

    assert grudge_retained == pytest.approx(expected_grudge_retained)
    assert rumor_retained == pytest.approx(expected_rumor_retained)
    assert grudge_retained > rumor_retained  # the grudge outlives the rumor, same ordering as T3.2
