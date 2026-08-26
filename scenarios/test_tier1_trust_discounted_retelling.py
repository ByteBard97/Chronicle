"""Rule 20: trust-discounted retelling (docs/design/trust-discounted-retelling.md).

Ruled mechanism: retell()/resolve() take an optional trust float; when the
driver's tick loop propagates a claim through an encounter, it looks up
``relationship(hearer_id, teller_id, basis)`` -- direction matters, trust is
the HEARER's regard for the TELLER -- over the qualifying bases
{kinship, faction, shared_employer} (max strength across bases),
**excluding colocation** (a hand-seeded fixture constant nothing ever
updates, tracking no real signal). No qualifying edge at all -> the
no-relationship default, trust=0.5.

All of this rung's fixtures run through Driver.run() (the tick loop), since
that's the only place the lookup fires (docs/design/trust-discounted-
retelling.md §1's caller-supplies-context pattern) -- a scripted
driver.retell()/driver.resolve() call never gets an automatic lookup, only
whatever trust its caller explicitly passes.
"""

import pytest

from chronicle.claims import RETELL_CONFIDENCE_DECAY, TRUST_FLOOR, WITNESS_CONFIDENCE
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed
from chronicle.framelog import FrameLogReader
from chronicle.schedule import ScheduleBlock

_SAVE = "whiterun-save-1"
ORIGIN = {"kind": "scenario", "detail": "test_tier1_trust_discounted_retelling"}


def _driver(run_id: str) -> Driver:
    schedule = (
        ScheduleBlock(npc_id="irileth", location_id="bannered_mare", start_tick=0, end_tick=24),
        ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=24),
    )
    return Driver(
        run_id=run_id,
        seed_id="tier1-trust-discount",
        save_uuid=_SAVE,
        generation=0,
        schedule=schedule,
        encounter_probability=1.0,
    )


def _witness_the_theft(driver: Driver):
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id="irileth",
            perpetrator_id="unknown", crime_type="theft", location_id="bannered_mare",
        ),
        origin=ORIGIN,
    )
    theft_event = driver.event_log.lineage(_SAVE, 0)[0]
    theft_key = (theft_event.save_uuid, theft_event.generation, theft_event.seq)
    claim, _, _ = driver.witness(
        claim_id="claim-theft",
        belief_id="belief-irileth-theft",
        evidence_id="evidence-irileth-theft",
        kind="crime_witnessed",
        slots={"perpetrator": "unknown", "crime_type": "theft", "location": "bannered_mare"},
        canonical_event_key=theft_key,
        witness_id="irileth",
        gamets=0.0,
    )
    return claim


def test_kinship_relationship_gives_the_trust_weighted_formula_not_flat_08():
    """hulda (hearer) has a real kinship tie to irileth (teller): confidence reflects it, not flat 0.8."""
    driver = _driver("trust-kinship")
    driver.form_relationship(
        id="rel-hulda-irileth-kin", from_id="hulda", to_id="irileth",
        basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
    )
    claim = _witness_the_theft(driver)
    driver.run(0, 24)

    hulda_belief = driver.belief_of("hulda", claim.id)
    assert hulda_belief is not None
    expected_decay = RETELL_CONFIDENCE_DECAY * (TRUST_FLOOR + (1 - TRUST_FLOOR) * 0.9)
    assert hulda_belief.confidence == pytest.approx(WITNESS_CONFIDENCE * expected_decay)
    # And it is NOT the flat pre-rule-20 value -- the discount is real.
    assert hulda_belief.confidence != pytest.approx(WITNESS_CONFIDENCE * RETELL_CONFIDENCE_DECAY)

    # Replay parity: the trust value must be re-executable from the trace
    # alone (schema §4's trust_applied field), not just correct in the live
    # store -- post-keyframe reconstruction must land on the exact same
    # trust-discounted confidence.
    driver.close()
    reader = FrameLogReader(driver.writer.run_dir)
    rebuilt = reader.state_at(24).claims.belief_of("hulda", claim.id)
    assert rebuilt == hulda_belief


def test_no_relationship_gets_the_no_relationship_default_trust_of_half():
    """No edge at all between hulda and irileth: trust=0.5, the ruled no-relationship default."""
    driver = _driver("trust-no-relationship")
    claim = _witness_the_theft(driver)
    driver.run(0, 24)

    hulda_belief = driver.belief_of("hulda", claim.id)
    assert hulda_belief is not None
    expected_decay = RETELL_CONFIDENCE_DECAY * (TRUST_FLOOR + (1 - TRUST_FLOOR) * 0.5)
    assert hulda_belief.confidence == pytest.approx(WITNESS_CONFIDENCE * expected_decay)
    driver.close()


def test_colocation_only_relationship_is_excluded_falls_through_to_default():
    """The design doc's ruled basis filter: a colocation edge does NOT count, despite existing."""
    driver = _driver("trust-colocation-excluded")
    # A strong colocation edge -- if it counted, this would raise confidence
    # well above the no-relationship default. It must not: colocation is
    # excluded from the basis filter, so this falls through to trust=0.5
    # exactly as if no edge existed at all.
    driver.form_relationship(
        id="rel-hulda-irileth-coloc", from_id="hulda", to_id="irileth",
        basis="colocation", basis_id="bannered_mare", strength=0.95, gamets=0.0,
    )
    claim = _witness_the_theft(driver)
    driver.run(0, 24)

    hulda_belief = driver.belief_of("hulda", claim.id)
    assert hulda_belief is not None
    expected_decay = RETELL_CONFIDENCE_DECAY * (TRUST_FLOOR + (1 - TRUST_FLOOR) * 0.5)
    assert hulda_belief.confidence == pytest.approx(WITNESS_CONFIDENCE * expected_decay)
    driver.close()


def test_max_strength_wins_when_multiple_qualifying_bases_exist():
    """Both kinship (weak) and faction (strong) edges exist: the MAX strength across qualifying bases wins."""
    driver = _driver("trust-max-across-bases")
    driver.form_relationship(
        id="rel-hulda-irileth-kin", from_id="hulda", to_id="irileth",
        basis="kinship", basis_id=None, strength=0.2, gamets=0.0,
    )
    driver.form_relationship(
        id="rel-hulda-irileth-faction", from_id="hulda", to_id="irileth",
        basis="faction", basis_id="whiterun_guard", strength=0.85, gamets=0.0,
    )
    claim = _witness_the_theft(driver)
    driver.run(0, 24)

    hulda_belief = driver.belief_of("hulda", claim.id)
    assert hulda_belief is not None
    expected_decay = RETELL_CONFIDENCE_DECAY * (TRUST_FLOOR + (1 - TRUST_FLOOR) * 0.85)
    assert hulda_belief.confidence == pytest.approx(WITNESS_CONFIDENCE * expected_decay)
    driver.close()


def test_cross_faction_rumor_still_crosses_at_reduced_not_zero_confidence():
    """The design doc's named risk: trust-discounting must weaken, never block, cross-faction propagation.

    hulda and irileth belong to different factions and share no positive
    relationship edge at all -- structurally the same as the no-relationship
    case, which is exactly the point: the discount lands at a reduced but
    strictly positive confidence, never zero, so the rumor graph doesn't
    silently partition along faction lines.
    """
    driver = _driver("trust-cross-faction")
    driver.form_relationship(
        id="rel-hulda-guild", from_id="hulda", to_id="thieves_guild_placeholder",
        basis="faction", basis_id="thieves_guild", strength=0.7, gamets=0.0,
    )
    driver.form_relationship(
        id="rel-irileth-court", from_id="irileth", to_id="jarl_balgruuf",
        basis="shared_employer", basis_id="whiterun_court", strength=0.95, gamets=0.0,
    )
    claim = _witness_the_theft(driver)
    driver.run(0, 24)

    hulda_belief = driver.belief_of("hulda", claim.id)
    assert hulda_belief is not None
    # Reduced (below the flat/undiscounted ceiling) but strictly positive --
    # the story crossed the faction boundary, just at a weaker signal.
    assert 0.0 < hulda_belief.confidence < WITNESS_CONFIDENCE * RETELL_CONFIDENCE_DECAY
    driver.close()


def test_disabling_the_rule_reproduces_the_flat_08_regardless_of_relationships():
    """Rule 20 disabled: the driver never looks up a relationship at all, trust=None, flat 0.8 exactly."""
    from chronicle.rules import TRUST_DISCOUNTED_RETELLING

    driver = Driver(
        run_id="trust-disabled",
        seed_id="tier1-trust-discount-disabled",
        save_uuid=_SAVE,
        generation=0,
        schedule=(
            ScheduleBlock(npc_id="irileth", location_id="bannered_mare", start_tick=0, end_tick=24),
            ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=24),
        ),
        encounter_probability=1.0,
        disabled_rules=(TRUST_DISCOUNTED_RETELLING,),
    )
    driver.form_relationship(
        id="rel-hulda-irileth-kin", from_id="hulda", to_id="irileth",
        basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
    )
    claim = _witness_the_theft(driver)
    driver.run(0, 24)

    hulda_belief = driver.belief_of("hulda", claim.id)
    assert hulda_belief is not None
    assert hulda_belief.confidence == WITNESS_CONFIDENCE * RETELL_CONFIDENCE_DECAY
    driver.close()
