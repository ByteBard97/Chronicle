from chronicle.claims import ClaimStore
from chronicle.propagate import teller_and_hearer


def test_teller_and_hearer_when_one_holds_a_belief_and_the_other_does_not():
    store = ClaimStore()
    store.witness(
        claim_id="c1", belief_id="b1", evidence_id="e1", kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1), witness_id="proventus", gamets=1000.0,
    )
    assert teller_and_hearer(store, claim_id="c1", npc_a="proventus", npc_b="hulda") == ("proventus", "hulda")
    # Order of the encounter pair shouldn't matter -- the holder is always the teller.
    assert teller_and_hearer(store, claim_id="c1", npc_a="hulda", npc_b="proventus") == ("proventus", "hulda")


def test_teller_and_hearer_is_none_when_neither_holds_a_belief():
    store = ClaimStore()
    assert teller_and_hearer(store, claim_id="c1", npc_a="proventus", npc_b="hulda") is None


def test_teller_and_hearer_is_none_when_both_already_hold_it():
    store = ClaimStore()
    claim, proventus_belief, _ = store.witness(
        claim_id="c1", belief_id="b1", evidence_id="e1", kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=("s1", 0, 1), witness_id="proventus", gamets=1000.0,
    )
    store.retell(
        claim=claim, parent_variant=None, variant_id="v1", belief_id="b2", evidence_id="e2",
        teller_id="proventus", teller_belief=proventus_belief, hearer_id="hulda", gamets=1050.0,
    )
    assert teller_and_hearer(store, claim_id="c1", npc_a="proventus", npc_b="hulda") is None
