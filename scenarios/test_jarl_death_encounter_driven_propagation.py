"""Headless scenario: rumor propagation driven by sampled encounters (rules 2, 15).

The two earlier Jarl-death scenarios hand-scripted every retelling
(store.retell(teller_id="proventus", hearer_id="hulda", ...)) -- correct
for proving mutation/decay/evidence-chain mechanics, but rule 2 requires
propagation to come from a *sampled encounter*, and rule 15 requires
that sampling to come from real NPC schedules, not a hand-picked
teller/hearer pair. This scenario drives the same story outward purely
through chronicle.schedule + chronicle.propagate, driven by the driver's
tick loop (chronicle/driver.py): nobody in this test decides who talks to
whom -- the schedule fixture and the run's keyed rolls (ADR-0009) do.

Encounter probability is fixed at 1.0 for this scenario (every co-present
qualifying pair encounters) so the outcome is deterministic and
assertable; sample_encounters' actual probabilistic behavior (not every
co-presence is an encounter) is unit-tested in test_schedule.py.

The scenario also proves the "never a global broadcast" half of rule 2
by contrast: Belethor, a Whiterun merchant with no schedule block at all
in the fixture, never receives the belief -- there is no code path here
that could reach him, unlike a global-broadcast model where everyone
eventually hears everything.
"""

from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied
from chronicle.fixtures.whiterun_schedule import whiterun_schedule


def test_rumor_reaches_the_tavern_purely_through_scheduled_encounters():
    # The scenario runs through the driver (chronicle/driver.py): the tick
    # loop below is the driver's, and it writes the frame log as it runs.
    # Assertions below are unchanged from the pre-driver version of this
    # test. Encounter probability stays pinned at 1.0 (every co-present
    # qualifying pair encounters), so the outcome is deterministic and
    # assertable regardless of how the rolls are keyed.
    driver = Driver(
        run_id="scenario-jarl-death-encounter-driven",
        seed_id="jarl-death-encounters",
        save_uuid="whiterun-save-1",
        generation=0,
        schedule=whiterun_schedule(),
        encounter_probability=1.0,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="whiterun-save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_jarl_death_encounter_driven_propagation"},
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid="whiterun-save-1", generation=0, seq=2,
            gamets=0.0, wall_ts=1.0, witness_id="irileth",
            perpetrator_id="unknown", crime_type="murder", location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_jarl_death_encounter_driven_propagation"},
    )
    death_event, _ = driver.event_log.lineage("whiterun-save-1", 0)
    death_key = (death_event.save_uuid, death_event.generation, death_event.seq)

    claims = driver  # witness goes through the driver so the frame log records it
    death_claim, _, _ = claims.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=death_key,
        witness_id="irileth",
        gamets=0.0,
    )

    # The math tier's tick loop: the driver advances every tick, asks the
    # schedule who's co-present, samples which pairs actually encounter
    # (keyed rolls per ADR-0009), and for each encounter that has anything
    # to propagate, retells it. Nothing here hand-picks proventus/hulda/etc.
    # -- only the fixture's schedule and the keyed rolls decide who talks
    # to whom.
    driver.run(0, 400)

    # The story reached the tavern regulars, through nobody's hand but the
    # schedule's -- proving rule 2's "sampled encounter" mechanism actually
    # closes the loop from schedule to belief, not just in isolated unit tests.
    assert claims.belief_of("proventus", death_claim.id) is not None
    assert claims.belief_of("hulda", death_claim.id) is not None
    assert claims.belief_of("ysolda", death_claim.id) is not None
    # It also reached the guard who happened to share Dragonsreach with the
    # witnesses -- schedule-driven spread isn't limited to named principals.
    assert claims.belief_of("whiterun_guard_1", death_claim.id) is not None

    # Rule 2's other half: never a global broadcast. Belethor has no
    # schedule block in the fixture at all, so there is no encounter he
    # could ever appear in -- and, unlike a global-broadcast model, he
    # never hears the story.
    assert claims.belief_of("belethor", death_claim.id) is None

    # Evidence chain traceability (ADR-0007) survives encounter-driven
    # propagation exactly as it does hand-scripted propagation: walking
    # back from a schedule-reached belief still resolves to the witness.
    hulda_belief = claims.belief_of("hulda", death_claim.id)
    chain = claims.chain_for(hulda_belief.id)
    assert chain[-1][1].evidence_type == "witnessed"
    assert chain[-1][0].holder_id == "irileth"
    driver.close()
