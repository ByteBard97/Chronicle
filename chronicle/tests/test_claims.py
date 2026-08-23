from dataclasses import replace

import pytest

from chronicle.claims import (
    GIST_DECAY_HALF_LIFE,
    RUMOR_DORMANT_AFTER,
    RUMOR_FORGOTTEN_GIST_THRESHOLD,
    BeliefInstance,
    ClaimStore,
    decay,
    hear,
    hear_again,
    retell,
    stage_at,
    tell,
    witness,
)


def test_witness_creates_high_confidence_belief_with_witnessed_evidence():
    claim, belief, evidence = witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )

    assert claim.canonical_event_key == ("s1", 0, 1)
    assert belief.holder_id == "proventus"
    assert belief.confidence > 0.9
    assert evidence.evidence_type == "witnessed"
    assert evidence.source_id == "proventus"


def test_retelling_mutates_exactly_one_slot_and_decays_confidence():
    claim, witness_belief, _ = witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )

    variant, hulda_belief, evidence = retell(
        claim=claim,
        parent_variant=None,
        variant_id="v1",
        belief_id="b2",
        evidence_id="e2",
        teller_id="proventus",
        teller_belief=witness_belief,
        hearer_id="hulda",
        gamets=12.0,
        mutate_slot="perpetrator",
        mutated_value="the Thalmor",
    )

    # Exactly the mutated slot changed; the others carried through unmutated.
    assert variant.slots["perpetrator"] == "the Thalmor"
    assert variant.slots["cause"] == claim.slots["cause"]
    assert variant.slots["location"] == claim.slots["location"]
    assert variant.mutated_slot == "perpetrator"

    assert hulda_belief.confidence < witness_belief.confidence
    assert evidence.evidence_type == "reported"
    assert evidence.source_id == "proventus"

    # A second retelling mutates from the variant, not the original claim.
    variant2, ysolda_belief, _ = retell(
        claim=claim,
        parent_variant=variant,
        variant_id="v2",
        belief_id="b3",
        evidence_id="e3",
        teller_id="hulda",
        teller_belief=hulda_belief,
        hearer_id="ysolda",
        gamets=14.0,
    )
    assert variant2.parent_variant_id == "v1"
    assert variant2.slots["perpetrator"] == "the Thalmor"
    assert ysolda_belief.confidence < hulda_belief.confidence


def test_retelling_an_unknown_slot_raises_rather_than_adding_one():
    claim, witness_belief, _ = witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )

    with pytest.raises(ValueError):
        retell(
            claim=claim,
            parent_variant=None,
            variant_id="v1",
            belief_id="b2",
            evidence_id="e2",
            teller_id="proventus",
            teller_belief=witness_belief,
            hearer_id="hulda",
            gamets=12.0,
            mutate_slot="motive",
            mutated_value="greed",
        )


def test_retell_rejects_a_teller_belief_from_a_different_claim_or_variant():
    claim, _, _ = witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )
    _, other_belief, _ = witness(
        claim_id="c2",
        belief_id="b9",
        evidence_id="e9",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "illness", "location": None},
        canonical_event_key=("s1", 0, 2),
        witness_id="irileth",
        gamets=10.0,
    )

    with pytest.raises(ValueError):
        retell(
            claim=claim,
            parent_variant=None,
            variant_id="v1",
            belief_id="b2",
            evidence_id="e2",
            teller_id="irileth",
            teller_belief=other_belief,  # holds other_claim, not claim
            hearer_id="hulda",
            gamets=12.0,
        )


def test_retell_rejects_gamets_earlier_than_the_tellers_last_rehearsal():
    claim, witness_belief, _ = witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )

    with pytest.raises(ValueError):
        retell(
            claim=claim,
            parent_variant=None,
            variant_id="v1",
            belief_id="b2",
            evidence_id="e2",
            teller_id="proventus",
            teller_belief=witness_belief,
            hearer_id="hulda",
            gamets=5.0,  # before the witness even learned it
        )


def test_retell_rejects_a_no_op_mutation():
    claim, witness_belief, _ = witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )

    with pytest.raises(ValueError):
        retell(
            claim=claim,
            parent_variant=None,
            variant_id="v1",
            belief_id="b2",
            evidence_id="e2",
            teller_id="proventus",
            teller_belief=witness_belief,
            hearer_id="hulda",
            gamets=12.0,
            mutate_slot="perpetrator",
            mutated_value="unknown",  # same as the current value
        )


def test_evidence_chain_is_traceable_back_to_the_canonical_event():
    claim, witness_belief, witness_evidence = witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": None},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )
    _, hulda_belief, report_evidence = retell(
        claim=claim,
        parent_variant=None,
        variant_id="v1",
        belief_id="b2",
        evidence_id="e2",
        teller_id="proventus",
        teller_belief=witness_belief,
        hearer_id="hulda",
        gamets=12.0,
    )

    # "Since when, from what evidence, through whom" (ADR-0007), walked by hand:
    assert report_evidence.belief_id == hulda_belief.id
    assert report_evidence.source_id == witness_belief.holder_id
    assert witness_evidence.belief_id == witness_belief.id
    assert claim.canonical_event_key == ("s1", 0, 1)


def test_claim_store_answers_beliefs_of_and_chain_for_by_query():
    store = ClaimStore()
    claim, proventus_belief, _ = store.witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )
    _, hulda_belief, _ = store.retell(
        claim=claim,
        parent_variant=None,
        variant_id="v1",
        belief_id="b2",
        evidence_id="e2",
        teller_id="proventus",
        teller_belief=proventus_belief,
        hearer_id="hulda",
        gamets=12.0,
        mutate_slot="perpetrator",
        mutated_value="the Thalmor",
    )

    assert store.beliefs_of("hulda") == (hulda_belief,)
    assert store.beliefs_of("nobody") == ()

    chain = store.chain_for(hulda_belief.id)
    assert [belief.holder_id for belief, _ in chain] == ["hulda", "proventus"]
    assert [evidence.evidence_type for _, evidence in chain] == ["reported", "witnessed"]
    assert store.claim(claim.id) is claim


def test_claim_store_rejects_a_second_independent_claim_for_the_same_event():
    store = ClaimStore()
    store.witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )

    with pytest.raises(ValueError):
        store.witness(
            claim_id="c2",  # a different claim_id for the *same* event
            belief_id="b2",
            evidence_id="e2",
            kind="npc_death",
            slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
            canonical_event_key=("s1", 0, 1),
            witness_id="irileth",
            gamets=10.0,
        )

    # Reusing the same claim_id for the same event is the correct pattern.
    _, irileth_belief, _ = store.witness(
        claim_id="c1",
        belief_id="b3",
        evidence_id="e3",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="irileth",
        gamets=10.0,
    )
    assert irileth_belief.claim_id == "c1"


def test_disagreeing_second_witness_produces_a_variant_never_rewrites_claim():
    store = ClaimStore()
    claim, _, _ = store.witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )

    # Irileth actually saw the killer -- that disagreement belongs on a
    # Variant of the one shared Claim (ladder T0.4), never a silent rewrite
    # of the canonical claim other beliefs already point at.
    _, irileth_belief, _ = store.witness(
        claim_id="c1",
        belief_id="b2",
        evidence_id="e2",
        kind="npc_death",
        slots={"perpetrator": "a Dark Brotherhood assassin", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="irileth",
        gamets=10.0,
    )
    assert irileth_belief.claim_id == "c1"  # never a second Claim
    variant = store.variant(irileth_belief.variant_id)
    assert variant.claim_id == "c1"
    assert variant.parent_variant_id is None  # roots at the claim by design
    assert variant.mutated_slot == "perpetrator"
    assert variant.slots["perpetrator"] == "a Dark Brotherhood assassin"
    assert store.claim("c1").slots["perpetrator"] == "unknown"  # canonical telling stands
    assert claim.slots["perpetrator"] == "unknown"


def test_decay_erodes_confidence_and_verbatim_faster_than_gist():
    _, belief, _ = witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )

    # One gist half-life elapsed -- long enough that all three strengths have
    # visibly moved, since gist is the slowest of the three to decay (rule 5).
    decayed = decay(belief, at_gamets=belief.last_rehearsed + GIST_DECAY_HALF_LIFE)

    assert decayed.confidence < belief.confidence
    assert decayed.verbatim_strength < belief.verbatim_strength
    assert decayed.gist_strength < belief.gist_strength
    # Verbatim decays faster than gist over the same elapsed time (rule 5).
    assert decayed.verbatim_strength < decayed.gist_strength

    # decay() is a read-time computation -- it doesn't touch last_rehearsed
    # or the original belief object (rule 19: lazy, not eagerly maintained).
    assert decayed.last_rehearsed == belief.last_rehearsed
    assert decay(belief, at_gamets=belief.last_rehearsed) is belief


def test_corroborate_raises_confidence_via_a_distinct_source_but_not_a_repeat():
    store = ClaimStore()
    _, proventus_belief, _ = store.witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )
    _, hulda_belief, _ = store.witness(
        claim_id="c1",
        belief_id="b2",
        evidence_id="e2",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="hulda",
        gamets=10.0,
    )
    _, irileth_belief, _ = store.witness(
        claim_id="c1",
        belief_id="b3",
        evidence_id="e3",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="irileth",
        gamets=10.0,
    )

    updated, evidence = store.corroborate(
        belief_id="b1",
        source_belief=hulda_belief,
        evidence_id="corrob-1",
        gamets=15.0,
    )
    assert updated.confidence > proventus_belief.confidence
    assert evidence.evidence_type == "corroborated"
    assert evidence.predecessor_belief_id == "b2"
    assert len(store.evidence_for("b1")) == 2

    # A second, distinct source raises confidence further.
    updated_again, _ = store.corroborate(
        belief_id="b1",
        source_belief=irileth_belief,
        evidence_id="corrob-2",
        gamets=16.0,
    )
    assert updated_again.confidence > updated.confidence

    # The same source corroborating again is rejected -- repetition isn't
    # a new distinct source (rule 7).
    with pytest.raises(ValueError):
        store.corroborate(
            belief_id="b1",
            source_belief=hulda_belief,
            evidence_id="corrob-3",
            gamets=17.0,
        )

    # chain_for still walks the *original* grounding evidence, not the
    # corroborating ones.
    chain = store.chain_for("b1")
    assert len(chain) == 1
    assert chain[0][1].evidence_type == "witnessed"


def test_corroborate_decays_both_beliefs_before_combining():
    store = ClaimStore()
    _, proventus_belief, _ = store.witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )
    _, hulda_belief, _ = store.witness(
        claim_id="c1",
        belief_id="b2",
        evidence_id="e2",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="hulda",
        gamets=10.0,
    )

    # Nobody has thought about this in 5000 gamets -- corroboration at that
    # remove should reflect eroded, not original, confidence.
    updated, evidence = store.corroborate(
        belief_id="b1",
        source_belief=hulda_belief,
        evidence_id="corrob-1",
        gamets=5010.0,
    )
    naive_combined = 1 - (1 - proventus_belief.confidence) * (1 - hulda_belief.confidence)
    assert updated.confidence < naive_combined
    assert evidence.strength == hulda_belief.confidence  # recorded as given, not decayed


def test_corroborate_rejects_self_corroboration_and_stale_source_belief():
    store = ClaimStore()
    _, proventus_belief, _ = store.witness(
        claim_id="c1",
        belief_id="b1",
        evidence_id="e1",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="proventus",
        gamets=10.0,
    )
    _, hulda_belief, _ = store.witness(
        claim_id="c1",
        belief_id="b2",
        evidence_id="e2",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1),
        witness_id="hulda",
        gamets=10.0,
    )

    with pytest.raises(ValueError):
        store.corroborate(belief_id="b1", source_belief=proventus_belief, evidence_id="corrob-x", gamets=15.0)

    updated_hulda, _ = store.corroborate(
        belief_id="b2", source_belief=proventus_belief, evidence_id="corrob-y", gamets=15.0
    )
    assert updated_hulda.id == "b2"

    # hulda_belief is now stale -- store.corroborate replaced "b2" with updated_hulda.
    with pytest.raises(ValueError):
        store.corroborate(belief_id="b1", source_belief=hulda_belief, evidence_id="corrob-z", gamets=20.0)


def _belief(**overrides: object) -> BeliefInstance:
    defaults: dict[str, object] = {
        "id": "b1", "holder_id": "hulda", "claim_id": "c1", "variant_id": None,
        "confidence": 0.9, "verbatim_strength": 0.9, "gist_strength": 0.9,
        "first_learned": 1000.0, "last_rehearsed": 1000.0,
    }
    defaults.update(overrides)
    return BeliefInstance(**defaults)  # type: ignore[arg-type]


def test_hear_starts_at_heard_stage_with_one_exposure():
    rumor = hear(npc_id="hulda", claim_id="c1", variant_id=None, gamets=1000.0)
    assert rumor.stage == "heard"
    assert rumor.exposure_count == 1
    assert rumor.distinct_source_count == 1
    assert rumor.last_told is None


def test_hear_again_from_new_source_grows_distinct_count_but_same_source_does_not():
    rumor = hear(npc_id="hulda", claim_id="c1", variant_id=None, gamets=1000.0)

    from_new_source = hear_again(rumor, is_new_source=True, gamets=1010.0)
    assert from_new_source.exposure_count == 2
    assert from_new_source.distinct_source_count == 2

    from_same_source_again = hear_again(from_new_source, is_new_source=False, gamets=1020.0)
    assert from_same_source_again.exposure_count == 3
    assert from_same_source_again.distinct_source_count == 2  # unchanged -- rule 7's spirit


def test_tell_advances_stage_to_repeated_and_records_last_told():
    rumor = hear(npc_id="proventus", claim_id="c1", variant_id=None, gamets=1000.0)
    told = tell(rumor, gamets=1050.0)
    assert told.stage == "repeated"
    assert told.last_told == 1050.0
    # Immutability: the original record is untouched.
    assert rumor.stage == "heard"


def test_stage_at_stays_heard_or_repeated_while_active():
    rumor = tell(hear(npc_id="proventus", claim_id="c1", variant_id=None, gamets=1000.0), gamets=1050.0)
    belief = _belief(first_learned=1000.0, last_rehearsed=1050.0, gist_strength=0.9)
    assert stage_at(rumor, belief, at_gamets=1060.0) == "repeated"


def test_stage_at_derives_dormant_after_long_inactivity():
    rumor = hear(npc_id="hulda", claim_id="c1", variant_id=None, gamets=1000.0)
    # A gist_strength high enough that decay alone won't cross the
    # forgotten threshold within this window -- isolates the dormancy
    # check from the forgotten check.
    belief = _belief(first_learned=1000.0, last_rehearsed=1000.0, gist_strength=0.9)
    much_later = 1000.0 + RUMOR_DORMANT_AFTER + 1.0
    assert stage_at(rumor, belief, at_gamets=much_later) == "dormant"


def test_stage_at_derives_forgotten_once_gist_strength_decays_below_threshold():
    rumor = hear(npc_id="hulda", claim_id="c1", variant_id=None, gamets=1000.0)
    belief = _belief(first_learned=1000.0, last_rehearsed=1000.0, gist_strength=RUMOR_FORGOTTEN_GIST_THRESHOLD * 2)
    # Forgotten is a property of the belief's decay, checked before dormancy --
    # a story can be "forgotten" well before RUMOR_DORMANT_AFTER elapses if
    # nobody ever rehearsed it and gist_strength started low.
    from chronicle.claims import GIST_DECAY_HALF_LIFE

    far_future = 1000.0 + GIST_DECAY_HALF_LIFE * 20
    assert far_future - 1000.0 < RUMOR_DORMANT_AFTER * 100  # sanity: not relying on absurd magnitudes
    assert stage_at(rumor, belief, at_gamets=far_future) == "forgotten"


def test_claimstore_witness_records_rumor_state_at_heard():
    store = ClaimStore()
    store.witness(
        claim_id="c1", belief_id="b1", evidence_id="e1", kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1), witness_id="proventus", gamets=1000.0,
    )
    rumor = store.rumor_state("proventus", "c1", None)
    assert rumor is not None
    assert rumor.stage == "heard"
    assert rumor.exposure_count == 1


def test_claimstore_retell_records_hearer_heard_and_teller_repeated():
    store = ClaimStore()
    claim, proventus_belief, _ = store.witness(
        claim_id="c1", belief_id="b1", evidence_id="e1", kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1), witness_id="proventus", gamets=1000.0,
    )
    store.retell(
        claim=claim, parent_variant=None, variant_id="v1", belief_id="b2", evidence_id="e2",
        teller_id="proventus", teller_belief=proventus_belief, hearer_id="hulda",
        gamets=1050.0, mutate_slot="perpetrator", mutated_value="the Thalmor",
    )

    hulda_rumor = store.rumor_state("hulda", "c1", "v1")
    assert hulda_rumor is not None
    assert hulda_rumor.stage == "heard"

    proventus_rumor = store.rumor_state("proventus", "c1", None)
    assert proventus_rumor is not None
    assert proventus_rumor.stage == "repeated"
    assert proventus_rumor.last_told == 1050.0


def test_retell_rejects_a_teller_belief_with_out_of_range_confidence():
    # BeliefInstance has no __post_init__ validation of its own -- retell()
    # is the only thing standing between a hand-constructed, out-of-range
    # belief and a confidence value that's meaningless downstream.
    store = ClaimStore()
    claim, proventus_belief, _ = store.witness(
        claim_id="c1", belief_id="b1", evidence_id="e1", kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1), witness_id="proventus", gamets=1000.0,
    )
    bad_belief = replace(proventus_belief, confidence=1.5)
    with pytest.raises(ValueError, match="confidence"):
        store.retell(
            claim=claim, parent_variant=None, variant_id="v1", belief_id="b2", evidence_id="e2",
            teller_id="proventus", teller_belief=bad_belief, hearer_id="hulda", gamets=1050.0,
        )


def test_corroborate_rejects_a_source_belief_about_a_different_claim():
    store = ClaimStore()
    _claim1, belief1, _ = store.witness(
        claim_id="c1", belief_id="b1", evidence_id="e1", kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1), witness_id="proventus", gamets=0.0,
    )
    _claim2, belief2, _ = store.witness(
        claim_id="c2", belief_id="b2", evidence_id="e2", kind="crime_witnessed",
        slots={"perpetrator": "unknown", "crime_type": "theft", "location": "market"},
        canonical_event_key=("s1", 0, 2), witness_id="hulda", gamets=0.0,
    )
    with pytest.raises(ValueError, match="same claim"):
        store.corroborate(belief_id=belief1.id, source_belief=belief2, evidence_id="e3", gamets=10.0)


def test_corroborate_rejects_gamets_preceding_either_beliefs_last_rehearsal():
    store = ClaimStore()
    _claim, belief1, _ = store.witness(
        claim_id="c1", belief_id="b1", evidence_id="e1", kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1), witness_id="proventus", gamets=100.0,
    )
    _claim2, belief2, _ = store.witness(
        claim_id="c1", belief_id="b2", evidence_id="e2", kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1), witness_id="hulda", gamets=100.0,
    )
    with pytest.raises(ValueError, match="precede"):
        store.corroborate(belief_id=belief1.id, source_belief=belief2, evidence_id="e3", gamets=50.0)
