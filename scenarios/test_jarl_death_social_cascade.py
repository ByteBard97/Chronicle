"""Headless scenario: layer 4 (social state) derived from layer 3 (belief).

Extends test_jarl_death_belief_cascade.py's cast and events with the
social-state consequences docs/v0.1-spec.md rules 8-10 require: a grudge
forms for an NPC who both believes the Jarl was murdered *and* has an
existing relationship to him (Irileth, his housecarl), but not for an
NPC who heard the same story with no such relationship (Hulda, a tavern
keeper one retelling removed) -- rule 8's conditional gate, proven by
contrast rather than by asserting one grudge exists in isolation. Also
proves rule 10: the accused's reputation moves independently per
observer and per context, not as one global "the Thalmor did it" score.

Rules 15/16 (schedule-driven encounter sampling, the rumor stage
machine) are out of scope here, per chronicle/social.py's module
docstring -- relationships are hand-seeded via
chronicle/fixtures/whiterun_relationships.py, not derived from
schedules.
"""

import pytest

from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied
from chronicle.fixtures.whiterun_relationships import seed_whiterun
from chronicle.social import form_grudge


def test_grudge_and_reputation_form_only_where_a_relationship_exists():
    # The scenario runs through the driver (chronicle/driver.py): it owns the
    # stores and writes the frame log as derivations happen. Assertions below
    # are unchanged from the pre-driver version of this test.
    driver = Driver(
        run_id="scenario-jarl-death-social-cascade",
        seed_id="jarl-death",
        save_uuid="whiterun-save-1",
        generation=0,
    )
    driver.inject_event(
        NPCDied(
            tick=100, save_uuid="whiterun-save-1", generation=0, seq=1,
            gamets=1000.0, wall_ts=50_000.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_jarl_death_social_cascade"},
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=100, save_uuid="whiterun-save-1", generation=0, seq=2,
            gamets=1000.0, wall_ts=50_001.0, witness_id="irileth",
            perpetrator_id="unknown", crime_type="murder", location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_jarl_death_social_cascade"},
    )
    death_event, _ = driver.event_log.lineage("whiterun-save-1", 0)
    death_key = (death_event.save_uuid, death_event.generation, death_event.seq)

    claims = driver  # witness/retell go through the driver so the frame log records them
    social = driver.social
    seed_whiterun(social, gamets=0.0)

    # Irileth witnessed the death herself -- high-confidence belief, and she
    # has a shared_employer relationship to jarl_balgruuf from the fixture.
    death_claim, irileth_belief, _ = claims.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=death_key,
        witness_id="irileth",
        gamets=1000.0,
    )

    # The story reaches Hulda, one retelling removed, naming "the Thalmor" --
    # she has no relationship edge to jarl_balgruuf in the fixture.
    _, hulda_belief, _ = claims.retell(
        claim=death_claim, parent_variant=None, variant_id="variant-1",
        belief_id="belief-hulda", evidence_id="evidence-hulda",
        teller_id="irileth", teller_belief=irileth_belief, hearer_id="hulda",
        gamets=1050.0, mutate_slot="perpetrator", mutated_value="the Thalmor",
    )

    # -- Grudge formation (rule 8): Irileth qualifies, Hulda does not. -----

    irileth_relationship = social.any_relationship("irileth", "jarl_balgruuf")
    irileth_grudge = social.add_grudge(
        form_grudge(
            id="grudge-irileth-thalmor",
            holder_id="irileth",
            victim_id="jarl_balgruuf",
            target_id="the_thalmor",
            grievance_type="murder_of_ally",
            source_belief_id=irileth_belief.id,
            evidentiary_strength=irileth_belief.confidence,
            relationship_to_victim=irileth_relationship,
            gamets=1000.0,
        )
    )
    assert irileth_grudge.holder_id == "irileth"
    assert irileth_grudge.target_id == "the_thalmor"
    assert social.grudge("irileth", "the_thalmor") is irileth_grudge

    hulda_relationship = social.any_relationship("hulda", "jarl_balgruuf")
    assert hulda_relationship is None
    with pytest.raises(ValueError):
        form_grudge(
            id="grudge-hulda-thalmor",
            holder_id="hulda",
            victim_id="jarl_balgruuf",
            target_id="the_thalmor",
            grievance_type="murder_of_ally",
            source_belief_id=hulda_belief.id,
            evidentiary_strength=hulda_belief.confidence,
            relationship_to_victim=hulda_relationship,
            gamets=1050.0,
        )
    assert social.grudge("hulda", "the_thalmor") is None

    # -- Reputation (rule 10): observer-local, not a shared global score. --

    social.update_reputation(
        observer_id="irileth", subject_id="the_thalmor", context="violence",
        kind="witnessed", positive=False, gamets=1000.0,
    )
    social.update_reputation(
        observer_id="hulda", subject_id="the_thalmor", context="violence",
        kind="reported", positive=False, gamets=1050.0,
    )

    irileth_view = social.reputation("irileth", "the_thalmor", "violence")
    hulda_view = social.reputation("hulda", "the_thalmor", "violence")

    # Both observers think worse of the Thalmor, but from independent
    # records -- Irileth's is grounded in a witnessed death, Hulda's in
    # thirdhand testimony, and each observer's assessment can move on its
    # own without touching the other's.
    assert irileth_view.mean < 0.5
    assert hulda_view.mean < 0.5
    assert irileth_view.direct_count == 1
    assert hulda_view.witness_count == 1
    assert irileth_view != hulda_view
    driver.close()
