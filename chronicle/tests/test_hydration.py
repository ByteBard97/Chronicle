from chronicle.hydration import relationship_rank_for
from chronicle.social import form_grudge, form_relationship


def _grudge(*, evidentiary_strength: float, emotional_strength: float | None = None, forgiveness_threshold: float = 0.2):
    """Build a grudge with a chosen (approximate) starting severity.

    form_grudge derives severity as 0.5*emotional + 0.5*evidentiary from a
    relationship's strength and the given evidentiary_strength -- setting
    both to the same value gives severity == that value directly, which
    keeps the band-boundary tests exact and easy to read.
    """
    emotional = evidentiary_strength if emotional_strength is None else emotional_strength
    relationship = form_relationship(
        id="r-test", from_id="holder", to_id="victim",
        basis="colocation", basis_id=None, strength=emotional, gamets=0.0,
    )
    return form_grudge(
        id="g-test", holder_id="holder", victim_id="victim", target_id="target",
        grievance_type="theft", source_belief_id="belief-1",
        evidentiary_strength=evidentiary_strength, relationship_to_victim=relationship,
        gamets=0.0, forgiveness_threshold=forgiveness_threshold,
    )


def test_no_grudge_means_no_discount():
    assert relationship_rank_for(None, at_gamets=0.0) == 0


def test_severity_just_below_mild_threshold_is_no_discount():
    grudge = _grudge(evidentiary_strength=0.19)
    assert relationship_rank_for(grudge, at_gamets=0.0) == 0


def test_severity_at_mild_threshold_is_mild():
    grudge = _grudge(evidentiary_strength=0.2)
    assert relationship_rank_for(grudge, at_gamets=0.0) == -1


def test_severity_just_above_mild_threshold_is_mild():
    grudge = _grudge(evidentiary_strength=0.21)
    assert relationship_rank_for(grudge, at_gamets=0.0) == -1


def test_severity_at_severe_threshold_is_still_mild():
    grudge = _grudge(evidentiary_strength=0.5)
    assert relationship_rank_for(grudge, at_gamets=0.0) == -1


def test_severity_just_above_severe_threshold_is_severe_when_not_cooled():
    grudge = _grudge(evidentiary_strength=0.51)
    assert relationship_rank_for(grudge, at_gamets=0.0) == -2


def test_grudge_that_has_cooled_returns_to_no_discount():
    """The decay-awareness the design doc calls out explicitly: a grudge
    that WAS severe but has since decayed below its forgiveness threshold
    must bucket toward 0, not stay pinned at its stored severity."""
    grudge = _grudge(evidentiary_strength=0.9, forgiveness_threshold=0.2)
    # Immediately, it's well into the severe band.
    assert relationship_rank_for(grudge, at_gamets=0.0) == -2

    # Far enough in the future that both emotional and evidentiary
    # strength have decayed well past the forgiveness threshold.
    far_future = 10 * max(672.0, 336.0)  # several half-lives out
    assert relationship_rank_for(grudge, at_gamets=far_future) == 0


def test_severe_but_already_cooled_grudge_is_no_discount_not_severe_or_mild():
    """A grudge with a forgiveness_threshold above 0.5 is cooled while its
    decayed severity is still in the severe band -- grudge_cooled means
    forgiven (per its own docstring), so this must bucket all the way to
    0, not -2 (the "not cooled" branch) or -1 (an invented in-between)."""
    grudge = _grudge(evidentiary_strength=0.9, forgiveness_threshold=0.95)
    assert relationship_rank_for(grudge, at_gamets=0.0) == 0


def test_grudge_docstring_states_reputation_is_deferred():
    import chronicle.hydration as hydration_module

    assert "reputation" in hydration_module.__doc__.lower()
    assert "deferred" in hydration_module.__doc__.lower()
