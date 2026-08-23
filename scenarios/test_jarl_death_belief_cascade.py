"""Headless scenario: docs/v0.1-spec.md's payoff (see scenarios/README.md).

Seeds the canonical event log with the Jarl of Whiterun's death and the
crime a witness saw, derives beliefs from both, and carries the death
story two retellings onward with one mutation -- proving belief
formation, retelling-with-mutation, and evidence-chain traceability
(ADR-0007) work end to end, headless, with no game running, *queried
through ClaimStore* rather than by holding onto return values by hand
(that queryability is the actual point: the dashboard will query the
same store, not read local variables). Also proves decay (rule 6) and
corroboration (rule 7) in cascade context, not just in isolated unit
tests: a second independent witness corroborates Proventus's belief,
and querying the story's strength after a long, rehearsal-free gap shows
it eroded rather than staying frozen at formation-time confidence. This
is the minimal slice of the north-star scenario (docs/vision.md):
succession/economic/patrol consequences are explicitly out of scope for
v0.1 (spec §3).
"""

import pytest

from chronicle.claims import GIST_DECAY_HALF_LIFE, decay
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied


def test_jarl_death_belief_forms_spreads_and_stays_evidence_traceable():
    # The scenario runs through the driver (chronicle/driver.py): it owns the
    # stores and writes the frame log as derivations happen. Assertions below
    # are unchanged from the pre-driver version of this test.
    driver = Driver(
        run_id="scenario-jarl-death-belief-cascade",
        seed_id="jarl-death",
        save_uuid="whiterun-save-1",
        generation=0,
    )
    driver.inject_event(
        NPCDied(
            tick=100,
            save_uuid="whiterun-save-1",
            generation=0,
            seq=1,
            gamets=1000.0,
            wall_ts=50_000.0,
            npc_id="jarl_balgruuf",
            cause="assassination",
            killer_id=None,
            location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_jarl_death_belief_cascade"},
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=100,
            save_uuid="whiterun-save-1",
            generation=0,
            seq=2,
            gamets=1000.0,
            wall_ts=50_001.0,
            witness_id="proventus",
            perpetrator_id="unknown",
            crime_type="murder",
            location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_jarl_death_belief_cascade"},
    )
    death_event, crime_event = driver.event_log.lineage("whiterun-save-1", 0)
    death_key = (death_event.save_uuid, death_event.generation, death_event.seq)
    crime_key = (crime_event.save_uuid, crime_event.generation, crime_event.seq)

    store = driver  # witness/retell/corroborate go through the driver so the frame log records them

    # Proventus witnessed the crime itself -- rule 14: this seeds suspicion
    # (an "unknown" perpetrator slot), not a named-culprit belief.
    store.witness(
        claim_id="claim-crime",
        belief_id="belief-proventus-crime",
        evidence_id="evidence-proventus-crime",
        kind="crime_witnessed",
        slots={"perpetrator": "unknown", "crime_type": "murder", "location": "dragonsreach"},
        canonical_event_key=crime_key,
        witness_id="proventus",
        gamets=1000.0,
    )

    # Proventus also witnessed the death itself.
    death_claim, proventus_belief, _ = store.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-proventus-death",
        evidence_id="evidence-proventus-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=death_key,
        witness_id="proventus",
        gamets=1000.0,
    )
    assert proventus_belief.confidence > 0.9

    # First retelling, to Hulda at the tavern: the perpetrator slot mutates.
    variant_1, hulda_belief, _ = store.retell(
        claim=death_claim,
        parent_variant=None,
        variant_id="variant-1",
        belief_id="belief-hulda",
        evidence_id="evidence-hulda",
        teller_id="proventus",
        teller_belief=proventus_belief,
        hearer_id="hulda",
        gamets=1050.0,
        mutate_slot="perpetrator",
        mutated_value="the Thalmor",
    )
    assert hulda_belief.confidence < proventus_belief.confidence

    # Second retelling, Hulda to Ysolda: unmutated this time, carries the
    # first mutation forward.
    variant_2, ysolda_belief, _ = store.retell(
        claim=death_claim,
        parent_variant=variant_1,
        variant_id="variant-2",
        belief_id="belief-ysolda",
        evidence_id="evidence-ysolda",
        teller_id="hulda",
        teller_belief=hulda_belief,
        hearer_id="ysolda",
        gamets=1100.0,
    )
    assert ysolda_belief.confidence < hulda_belief.confidence
    assert variant_2.slots["perpetrator"] == "the Thalmor"

    # Query the store the way a dashboard would: "what does Ysolda
    # believe" -- not a variable held from construction time.
    ysolda_beliefs = store.beliefs_of("ysolda")
    assert len(ysolda_beliefs) == 1
    assert ysolda_beliefs[0].id == ysolda_belief.id

    # ADR-0007's "since when, from what evidence, through whom", answered
    # by walking the store, not by hand-chaining local variables: Ysolda
    # <- Hulda's testimony <- Hulda's belief <- Proventus's testimony <-
    # Proventus's belief <- the canonical death event.
    chain = store.chain_for(ysolda_belief.id)
    holders = [belief.holder_id for belief, _ in chain]
    sources = [evidence.source_id for _, evidence in chain]
    assert holders == ["ysolda", "hulda", "proventus"]
    assert sources == ["hulda", "proventus", "proventus"]
    assert chain[-1][1].evidence_type == "witnessed"
    assert store.claim(chain[-1][0].claim_id).canonical_event_key == death_key

    # The story that reached Ysolda names the Thalmor; the canonical claim
    # (and the event it derives from) never said who did it -- the
    # mutation is traceable, not silently baked into the ground truth.
    assert death_claim.slots["perpetrator"] == "unknown"
    assert death_event.killer_id is None

    # Irileth independently witnessed the same death (she was in
    # Dragonsreach too) and corroborates Proventus's belief -- a second,
    # distinct source, not a retelling. Same claim_id as Proventus's death
    # claim: it's the same canonical event, so it's the same Claim record,
    # not a second independent one.
    _, irileth_belief, _ = store.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=death_key,
        witness_id="irileth",
        gamets=1000.0,
    )
    corroborated_proventus, _ = store.corroborate(
        belief_id=proventus_belief.id,
        source_belief=irileth_belief,
        evidence_id="evidence-irileth-corroborates-proventus",
        gamets=1005.0,
    )
    assert corroborated_proventus.confidence > proventus_belief.confidence
    # Rule 7: repetition from the same source doesn't count as further
    # corroboration.
    with pytest.raises(ValueError):
        store.corroborate(
            belief_id=proventus_belief.id,
            source_belief=irileth_belief,
            evidence_id="evidence-irileth-corroborates-proventus-again",
            gamets=1006.0,
        )

    # A long, rehearsal-free gap later (no game running in between --
    # nobody in Whiterun has thought about this in many gist half-lives),
    # the story's strength has eroded rather than staying frozen at
    # formation-time confidence (rule 6, rule 19: computed at query time,
    # not written back into the store). ADR-0010: 1 gamets = 1 game-hour,
    # so this is ~gist-half-life-many game-days -- deliberately far past
    # any decay threshold, not a calibrated duration.
    much_later = 1000.0 + 10 * GIST_DECAY_HALF_LIFE
    decayed_ysolda_belief = decay(store.beliefs_of("ysolda")[0], at_gamets=much_later)
    assert decayed_ysolda_belief.confidence < ysolda_belief.confidence
    assert store.beliefs_of("ysolda")[0].confidence == ysolda_belief.confidence  # store unchanged
    driver.close()
