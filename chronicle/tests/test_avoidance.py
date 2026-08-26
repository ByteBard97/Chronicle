from chronicle.avoidance import is_avoiding
from chronicle.driver import AVOIDANCE_GRUDGE_THRESHOLD
from chronicle.social import form_grudge, form_relationship


def _grudge(*, evidentiary_strength: float, emotional_strength: float | None = None, forgiveness_threshold: float = 0.2):
    """Build a grudge with a chosen (approximate) starting severity.

    Mirrors chronicle/tests/test_hydration.py's own `_grudge` helper
    exactly -- setting emotional_strength == evidentiary_strength gives
    severity == that value directly, keeping threshold-boundary tests
    exact and easy to read.
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


def test_severity_just_below_threshold_is_not_avoiding():
    grudge = _grudge(evidentiary_strength=AVOIDANCE_GRUDGE_THRESHOLD - 0.01)
    assert is_avoiding(grudge, at_gamets=0.0) is False


def test_severity_at_threshold_is_avoiding():
    grudge = _grudge(evidentiary_strength=AVOIDANCE_GRUDGE_THRESHOLD)
    assert is_avoiding(grudge, at_gamets=0.0) is True


def test_severity_above_threshold_is_avoiding():
    grudge = _grudge(evidentiary_strength=AVOIDANCE_GRUDGE_THRESHOLD + 0.1)
    assert is_avoiding(grudge, at_gamets=0.0) is True


def test_cooled_grudge_is_not_avoiding_even_if_severity_still_reads_high():
    """A forgiveness_threshold above the severity band means grudge_cooled
    is already True at severity==0.9 -- cooled means forgiven, and must
    win over a high decayed severity, the same precedent
    chronicle.hydration.relationship_rank_for follows for its own
    severe-but-cooled case."""
    grudge = _grudge(evidentiary_strength=0.9, forgiveness_threshold=0.95)
    assert is_avoiding(grudge, at_gamets=0.0) is False


def test_grudge_that_decays_below_threshold_over_time_stops_avoiding():
    grudge = _grudge(evidentiary_strength=0.9, forgiveness_threshold=0.2)
    assert is_avoiding(grudge, at_gamets=0.0) is True

    far_future = 10 * max(672.0, 336.0)  # several half-lives out
    assert is_avoiding(grudge, at_gamets=far_future) is False


def test_custom_threshold_overrides_the_driver_default():
    grudge = _grudge(evidentiary_strength=0.3)
    assert is_avoiding(grudge, at_gamets=0.0, threshold=0.5) is False
    assert is_avoiding(grudge, at_gamets=0.0, threshold=0.2) is True


def test_default_threshold_is_the_driver_constant():
    import inspect

    assert inspect.signature(is_avoiding).parameters["threshold"].default == AVOIDANCE_GRUDGE_THRESHOLD
