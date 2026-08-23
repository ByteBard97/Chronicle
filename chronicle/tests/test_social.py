import pytest

from chronicle.social import (
    GRUDGE_EMOTIONAL_HALF_LIFE,
    GRUDGE_EVIDENTIARY_HALF_LIFE,
    Reputation,
    SocialStateStore,
    _resolve_obligation,
    form_grudge,
    form_relationship,
    grudge_at,
    grudge_cooled,
    issue_obligation,
    update_reputation,
)


def test_relationship_rejects_arbitrary_basis():
    with pytest.raises(ValueError):
        form_relationship(
            id="r1",
            from_id="proventus",
            to_id="jarl_balgruuf",
            basis="arbitrary",
            basis_id=None,
            strength=0.8,
            gamets=0.0,
        )


def test_relationship_accepts_allowed_bases():
    rel = form_relationship(
        id="r1",
        from_id="irileth",
        to_id="jarl_balgruuf",
        basis="shared_employer",
        basis_id="whiterun_court",
        strength=0.9,
        gamets=0.0,
    )
    assert rel.basis == "shared_employer"
    assert rel.strength == 0.9


def test_store_rejects_duplicate_relationship_for_same_triple():
    store = SocialStateStore()
    rel = form_relationship(
        id="r1", from_id="irileth", to_id="jarl_balgruuf",
        basis="shared_employer", basis_id="whiterun_court", strength=0.9, gamets=0.0,
    )
    store.add_relationship(rel)

    duplicate = form_relationship(
        id="r2", from_id="irileth", to_id="jarl_balgruuf",
        basis="shared_employer", basis_id="whiterun_court", strength=0.5, gamets=1.0,
    )
    with pytest.raises(ValueError):
        store.add_relationship(duplicate)


def test_grudge_requires_existing_relationship_to_victim():
    with pytest.raises(ValueError):
        form_grudge(
            id="g1",
            holder_id="a_random_farmer",
            victim_id="jarl_balgruuf",
            target_id="the_thalmor",
            grievance_type="murder_of_ally",
            source_belief_id="belief-farmer-death",
            evidentiary_strength=0.9,
            relationship_to_victim=None,
            gamets=1000.0,
        )


def test_grudge_rejects_relationship_pointing_the_wrong_way():
    # A relationship jarl_balgruuf -> irileth does not establish that
    # irileth cares about jarl_balgruuf for grudge purposes -- form_grudge
    # needs holder_id -> victim_id specifically, not any edge touching both.
    backwards = form_relationship(
        id="r1", from_id="jarl_balgruuf", to_id="irileth",
        basis="shared_employer", basis_id="whiterun_court", strength=0.9, gamets=0.0,
    )
    with pytest.raises(ValueError):
        form_grudge(
            id="g1",
            holder_id="irileth",
            victim_id="jarl_balgruuf",
            target_id="the_thalmor",
            grievance_type="murder_of_ally",
            source_belief_id="belief-irileth-death",
            evidentiary_strength=0.9,
            relationship_to_victim=backwards,
            gamets=1000.0,
        )


def test_grudge_severity_scales_with_closeness_and_evidence():
    close_relationship = form_relationship(
        id="r1", from_id="irileth", to_id="jarl_balgruuf",
        basis="shared_employer", basis_id="whiterun_court", strength=0.9, gamets=0.0,
    )
    distant_relationship = form_relationship(
        id="r2", from_id="a_guard", to_id="jarl_balgruuf",
        basis="faction", basis_id="whiterun_guard", strength=0.3, gamets=0.0,
    )

    close_grudge = form_grudge(
        id="g1", holder_id="irileth", victim_id="jarl_balgruuf", target_id="the_thalmor",
        grievance_type="murder_of_ally", source_belief_id="belief-irileth-death",
        evidentiary_strength=0.9, relationship_to_victim=close_relationship, gamets=1000.0,
    )
    distant_grudge = form_grudge(
        id="g2", holder_id="a_guard", victim_id="jarl_balgruuf", target_id="the_thalmor",
        grievance_type="murder_of_ally", source_belief_id="belief-guard-death",
        evidentiary_strength=0.9, relationship_to_victim=distant_relationship, gamets=1000.0,
    )

    # Same evidentiary strength, but irileth's closer relationship to the
    # victim produces a more severe grudge than the guard's distant one --
    # rule 9: severity scales with closeness + evidence, not a flat penalty.
    assert close_grudge.severity > distant_grudge.severity
    assert close_grudge.emotional_strength == 0.9
    assert distant_grudge.emotional_strength == 0.3


def test_store_grudge_lookup_by_holder_and_target():
    store = SocialStateStore()
    relationship = form_relationship(
        id="r1", from_id="irileth", to_id="jarl_balgruuf",
        basis="shared_employer", basis_id="whiterun_court", strength=0.9, gamets=0.0,
    )
    grudge = form_grudge(
        id="g1", holder_id="irileth", victim_id="jarl_balgruuf", target_id="the_thalmor",
        grievance_type="murder_of_ally", source_belief_id="belief-irileth-death",
        evidentiary_strength=0.9, relationship_to_victim=relationship, gamets=1000.0,
    )
    store.add_grudge(grudge)

    assert store.grudge("irileth", "the_thalmor") is grudge
    assert store.grudge("irileth", "someone_else") is None
    assert store.grudges_of("irileth") == (grudge,)


def test_reputation_is_keyed_per_observer_subject_context():
    store = SocialStateStore()
    store.update_reputation(
        observer_id="proventus", subject_id="the_thalmor", context="violence",
        kind="witnessed", positive=False, gamets=1000.0,
    )
    store.update_reputation(
        observer_id="proventus", subject_id="the_thalmor", context="commerce",
        kind="reported", positive=True, gamets=1000.0,
    )

    violence_rep = store.reputation("proventus", "the_thalmor", "violence")
    commerce_rep = store.reputation("proventus", "the_thalmor", "commerce")

    # Same observer, same subject, different context -- independent records,
    # not one collapsed score (rule 10).
    assert violence_rep.mean < 0.5  # a negative, witnessed observation
    assert commerce_rep.mean > 0.5  # a positive, reported observation
    assert violence_rep != commerce_rep


def test_reputation_witnessed_outweighs_reported():
    witnessed = update_reputation(
        None, observer_id="proventus", subject_id="the_thalmor", context="violence",
        kind="witnessed", positive=False, gamets=1000.0,
    )
    reported = update_reputation(
        None, observer_id="proventus", subject_id="the_thalmor", context="violence",
        kind="reported", positive=False, gamets=1000.0,
    )
    # A witnessed negative act should move the estimate further from neutral
    # than secondhand testimony of the same polarity.
    assert witnessed.mean < reported.mean
    assert witnessed.direct_count == 1
    assert witnessed.witness_count == 0
    assert reported.witness_count == 1


def test_reputation_uncertainty_shrinks_as_evidence_accumulates():
    store = SocialStateStore()
    first = store.update_reputation(
        observer_id="proventus", subject_id="the_thalmor", context="violence",
        kind="witnessed", positive=False, gamets=1000.0,
    )
    second = store.update_reputation(
        observer_id="proventus", subject_id="the_thalmor", context="violence",
        kind="reported", positive=False, gamets=1050.0,
    )
    assert second.uncertainty < first.uncertainty


def test_obligation_lifecycle_fulfill():
    store = SocialStateStore()
    obligation = issue_obligation(
        id="obl-1", issuer_id="proventus", debtor_id="a_guard_captain",
        beneficiary_id="jarl_balgruuf", action="avenge_murder",
        condition="perpetrator identified", gamets=1000.0,
    )
    store.add_obligation(obligation)
    assert obligation.status == "active"

    fulfilled = store.fulfill_obligation("obl-1", gamets=2000.0)
    assert fulfilled.status == "fulfilled"
    assert fulfilled.fulfilled_at == 2000.0
    # Immutability: the original record is untouched.
    assert obligation.status == "active"


def test_obligation_cannot_be_resolved_twice():
    store = SocialStateStore()
    obligation = issue_obligation(
        id="obl-1", issuer_id="proventus", debtor_id="a_guard_captain",
        beneficiary_id="jarl_balgruuf", action="avenge_murder",
        condition="perpetrator identified", gamets=1000.0,
    )
    store.add_obligation(obligation)
    store.fulfill_obligation("obl-1", gamets=2000.0)

    with pytest.raises(ValueError):
        store.violate_obligation("obl-1", gamets=3000.0)


def test_obligation_involving_finds_issuer_debtor_and_beneficiary():
    store = SocialStateStore()
    obligation = issue_obligation(
        id="obl-1", issuer_id="proventus", debtor_id="a_guard_captain",
        beneficiary_id="jarl_balgruuf", action="avenge_murder",
        condition="perpetrator identified", gamets=1000.0,
    )
    store.add_obligation(obligation)

    assert store.obligations_involving("proventus") == (obligation,)
    assert store.obligations_involving("a_guard_captain") == (obligation,)
    assert store.obligations_involving("jarl_balgruuf") == (obligation,)
    assert store.active_obligations_of("a_guard_captain") == (obligation,)
    assert store.active_obligations_of("proventus") == ()


def test_reputation_rejects_non_positive_alpha_or_beta():
    # A Beta distribution's parameters must be positive -- 0 or negative
    # isn't a valid prior/posterior, regardless of how it was reached.
    with pytest.raises(ValueError, match="alpha/beta must be positive"):
        Reputation(
            observer_id="hulda", subject_id="proventus", context="stewardship",
            alpha=0.0, beta=1.0, direct_count=0, witness_count=0, certified_count=0,
            uncertainty=0.5, last_updated=0.0,
        )


def test_reputation_rejects_an_uncertainty_outside_the_unit_interval():
    with pytest.raises(ValueError, match="uncertainty"):
        Reputation(
            observer_id="hulda", subject_id="proventus", context="stewardship",
            alpha=1.0, beta=1.0, direct_count=0, witness_count=0, certified_count=0,
            uncertainty=1.5, last_updated=0.0,
        )


def test_update_reputation_rejects_an_unknown_kind():
    with pytest.raises(ValueError, match="kind must be one of"):
        update_reputation(None, observer_id="hulda", subject_id="proventus", context="stewardship", kind="hearsay", positive=True, gamets=0.0)


def test_resolve_obligation_rejects_an_unsupported_status():
    # Only fulfill_obligation()/violate_obligation() call this with a fixed
    # literal ("fulfilled"/"violated") -- this guard is otherwise
    # unreachable through the public API, but it's real code, so it gets
    # a real test rather than staying untested dead weight.
    obligation = issue_obligation(
        id="obl-1", issuer_id="jarl_balgruuf", debtor_id="proventus", beneficiary_id=None,
        action="manage the treasury", condition=None, gamets=0.0,
    )
    with pytest.raises(ValueError, match="unsupported resolution status"):
        _resolve_obligation(obligation, status="cancelled", gamets=1.0)


def test_add_grudge_rejects_a_second_grudge_for_the_same_holder_target_pair():
    store = SocialStateStore()
    rel = form_relationship(id="rel-1", from_id="hulda", to_id="jarl_balgruuf", basis="colocation", basis_id=None, strength=0.6, gamets=0.0)
    grudge = form_grudge(
        id="grudge-1", holder_id="hulda", victim_id="jarl_balgruuf", target_id="the_thalmor",
        grievance_type="murder", source_belief_id="belief-hulda", evidentiary_strength=0.4,
        relationship_to_victim=rel, gamets=5.0,
    )
    store.add_grudge(grudge)
    second = form_grudge(
        id="grudge-2", holder_id="hulda", victim_id="jarl_balgruuf", target_id="the_thalmor",
        grievance_type="murder", source_belief_id="belief-hulda", evidentiary_strength=0.9,
        relationship_to_victim=rel, gamets=6.0,
    )
    with pytest.raises(ValueError, match="a grudge already exists"):
        store.add_grudge(second)


def test_relationship_lookup_returns_none_when_no_edge_matches():
    store = SocialStateStore()
    store.add_relationship(
        form_relationship(id="r1", from_id="hulda", to_id="jarl_balgruuf", basis="colocation", basis_id=None, strength=0.6, gamets=0.0)
    )
    assert store.relationship(from_id="hulda", to_id="jarl_balgruuf", basis="colocation") is not None
    assert store.relationship(from_id="hulda", to_id="jarl_balgruuf", basis="kinship") is None
    assert store.relationship(from_id="proventus", to_id="jarl_balgruuf", basis="colocation") is None


def test_form_grudge_rejects_a_missing_relationship_to_the_victim():
    with pytest.raises(ValueError, match="no relationship edge"):
        form_grudge(
            id="grudge-1", holder_id="hulda", victim_id="jarl_balgruuf", target_id="the_thalmor",
            grievance_type="murder", source_belief_id="belief-hulda", evidentiary_strength=0.4,
            relationship_to_victim=None, gamets=5.0,
        )


# ---------------------------------------------------------------------------
# grudge decay (rule 13 -- lane 20, the missing twin of belief decay)
# ---------------------------------------------------------------------------


def _grudge(last_rehearsed: float = 0.0):
    rel = form_relationship(
        id="rel-1", from_id="hulda", to_id="jarl_balgruuf",
        basis="kinship", basis_id=None, strength=0.9, gamets=0.0,
    )
    return form_grudge(
        id="grudge-1", holder_id="hulda", victim_id="jarl_balgruuf", target_id="the_thalmor",
        grievance_type="murder", source_belief_id="belief-hulda", evidentiary_strength=0.9,
        relationship_to_victim=rel, gamets=last_rehearsed,
    )


def test_grudge_at_decays_both_strengths_emotional_slower_than_evidentiary():
    from chronicle.claims import _decay

    grudge = _grudge()
    aged = grudge_at(grudge, 336.0)
    assert aged.emotional_strength == pytest.approx(_decay(0.9, 336.0, GRUDGE_EMOTIONAL_HALF_LIFE))
    assert aged.evidentiary_strength == pytest.approx(_decay(0.9, 336.0, GRUDGE_EVIDENTIARY_HALF_LIFE))
    assert aged.emotional_strength < grudge.emotional_strength
    assert aged.evidentiary_strength < grudge.evidentiary_strength
    # The constants-ordering assert: the feeling outlives the facts.
    assert aged.emotional_strength > aged.evidentiary_strength


def test_grudge_decays_slower_than_belief_confidence_over_the_same_window():
    """T3.2's 'grudge decays slower than the rumor' at the constants level."""
    from chronicle.claims import CONFIDENCE_DECAY_HALF_LIFE, _decay

    grudge = _grudge()
    elapsed = 168.0
    aged = grudge_at(grudge, elapsed)
    decayed_confidence = _decay(0.9, elapsed, CONFIDENCE_DECAY_HALF_LIFE)
    assert aged.emotional_strength > decayed_confidence
    assert aged.evidentiary_strength > decayed_confidence


def test_grudge_cooled_flips_at_the_forgiveness_threshold_crossing():
    # severity(0) = 0.9, forgiveness_threshold = 0.2; with the ruled
    # half-lives the decayed severity crosses 0.2 at ~1060 ticks elapsed.
    grudge = _grudge()
    assert not grudge_cooled(grudge, 0.0)
    assert not grudge_cooled(grudge, 1050.0)
    assert grudge_cooled(grudge, 1070.0)
    # A cooled grudge is never deleted -- the record and its decayed view stand.
    assert grudge_at(grudge, 1070.0).severity < grudge.forgiveness_threshold


def test_grudge_at_never_mutates_its_input():
    grudge = _grudge()
    aged = grudge_at(grudge, 1000.0)
    assert aged is not grudge
    assert grudge.emotional_strength == 0.9
    assert grudge.evidentiary_strength == 0.9
    assert grudge.severity == pytest.approx(0.9)
    assert grudge.last_rehearsed == 0.0
