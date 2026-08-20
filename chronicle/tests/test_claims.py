import pytest

from chronicle.claims import ClaimStore, decay, retell, witness


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


def test_claim_store_rejects_the_same_claim_id_with_different_content():
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

    # Irileth actually saw the killer -- but that disagreement belongs on
    # a Variant (a mutated retelling of her own account), not silently
    # rewriting the shared canonical claim other beliefs already point at.
    with pytest.raises(ValueError):
        store.witness(
            claim_id="c1",
            belief_id="b2",
            evidence_id="e2",
            kind="npc_death",
            slots={"perpetrator": "a Dark Brotherhood assassin", "cause": "assassination", "location": "dragonsreach"},
            canonical_event_key=("s1", 0, 1),
            witness_id="irileth",
            gamets=10.0,
        )


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

    decayed = decay(belief, at_gamets=belief.last_rehearsed + 500.0)

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
