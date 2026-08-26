from chronicle.social import form_grudge, form_relationship
from chronicle.vendor_markup import (
    MARKUP_CEILING,
    MARKUP_NO_MARKUP,
    MARKUP_SEVERITY_FLOOR,
    markup_multiplier_for,
)


def _grudge(*, evidentiary_strength: float, emotional_strength: float | None = None, forgiveness_threshold: float = 0.2):
    """Build a grudge with a chosen (approximate) starting severity.

    Mirrors chronicle/tests/test_hydration.py's and test_avoidance.py's
    own `_grudge` helper exactly -- setting emotional_strength ==
    evidentiary_strength gives severity == that value directly, keeping
    boundary tests exact and easy to read.
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


def test_no_grudge_means_no_markup():
    assert markup_multiplier_for(None, at_gamets=0.0) == MARKUP_NO_MARKUP


def test_severity_just_below_floor_is_no_markup():
    grudge = _grudge(evidentiary_strength=MARKUP_SEVERITY_FLOOR - 0.01)
    assert markup_multiplier_for(grudge, at_gamets=0.0) == MARKUP_NO_MARKUP


def test_severity_at_floor_is_no_markup():
    """The floor is the first severity where markup would begin, not
    itself the first marked-up value -- exclusive lower bound, mirroring
    the < comparison in the implementation."""
    grudge = _grudge(evidentiary_strength=MARKUP_SEVERITY_FLOOR)
    assert markup_multiplier_for(grudge, at_gamets=0.0) == MARKUP_NO_MARKUP


def test_severity_just_above_floor_is_marked_up_slightly():
    grudge = _grudge(evidentiary_strength=MARKUP_SEVERITY_FLOOR + 0.01)
    multiplier = markup_multiplier_for(grudge, at_gamets=0.0)
    assert MARKUP_NO_MARKUP < multiplier < MARKUP_CEILING


def test_severity_at_max_is_the_full_ceiling():
    grudge = _grudge(evidentiary_strength=1.0)
    assert markup_multiplier_for(grudge, at_gamets=0.0) == MARKUP_CEILING


def test_curve_is_monotonically_increasing_with_severity():
    low = markup_multiplier_for(_grudge(evidentiary_strength=0.3), at_gamets=0.0)
    mid = markup_multiplier_for(_grudge(evidentiary_strength=0.6), at_gamets=0.0)
    high = markup_multiplier_for(_grudge(evidentiary_strength=0.9), at_gamets=0.0)
    assert low < mid < high


def test_multiplier_is_never_below_one():
    """Never implies a price below vanilla -- see the module's own
    constants comment on why this matters against fBarterBuyMin's real
    1.05 floor, even though enforcing that floor is out of scope here."""
    for evidentiary_strength in (0.0, 0.1, MARKUP_SEVERITY_FLOOR, 0.5, 1.0):
        grudge = _grudge(evidentiary_strength=evidentiary_strength)
        assert markup_multiplier_for(grudge, at_gamets=0.0) >= MARKUP_NO_MARKUP


def test_cooled_grudge_is_no_markup_even_if_severity_still_reads_high():
    """A forgiveness_threshold above the severity band means grudge_cooled
    is already True at severity==0.9 -- cooled means forgiven, and must
    win over a high decayed severity, the same precedent
    chronicle.hydration.relationship_rank_for and chronicle.avoidance.
    is_avoiding both already follow for their own reads of this state."""
    grudge = _grudge(evidentiary_strength=0.9, forgiveness_threshold=0.95)
    assert markup_multiplier_for(grudge, at_gamets=0.0) == MARKUP_NO_MARKUP


def test_grudge_that_decays_below_floor_over_time_reverts_to_no_markup():
    grudge = _grudge(evidentiary_strength=0.9, forgiveness_threshold=0.2)
    assert markup_multiplier_for(grudge, at_gamets=0.0) > MARKUP_NO_MARKUP

    far_future = 10 * max(672.0, 336.0)  # several half-lives out
    assert markup_multiplier_for(grudge, at_gamets=far_future) == MARKUP_NO_MARKUP
