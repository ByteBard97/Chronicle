from chronicle.claims import CONFIDENCE_DECAY_HALF_LIFE, BeliefInstance
from chronicle.diegetic_evidence import (
    EVIDENCE_CONFIDENCE_THRESHOLD,
    should_reveal_evidence,
)


def _belief(*, confidence: float, last_rehearsed: float = 0.0) -> BeliefInstance:
    """A belief with a chosen starting confidence, mirroring
    chronicle/tests/test_vendor_markup.py's/test_hydration.py's own
    `_grudge` helper's spirit: hand-build the minimal record a threshold
    test needs rather than driving it through witness()/retell()."""
    return BeliefInstance(
        id="belief-test",
        holder_id="holder",
        claim_id="claim-test",
        variant_id=None,
        confidence=confidence,
        verbatim_strength=1.0,
        gist_strength=1.0,
        first_learned=last_rehearsed,
        last_rehearsed=last_rehearsed,
    )


def test_confidence_just_below_threshold_does_not_reveal():
    belief = _belief(confidence=EVIDENCE_CONFIDENCE_THRESHOLD - 0.01)
    assert should_reveal_evidence(belief, at_gamets=0.0) is False


def test_confidence_at_threshold_reveals():
    """The threshold is inclusive -- the first confidence value that
    reveals evidence, not merely the last one that doesn't (the same `>=`
    boundary chronicle.avoidance.is_avoiding uses for its own threshold)."""
    belief = _belief(confidence=EVIDENCE_CONFIDENCE_THRESHOLD)
    assert should_reveal_evidence(belief, at_gamets=0.0) is True


def test_confidence_just_above_threshold_reveals():
    belief = _belief(confidence=EVIDENCE_CONFIDENCE_THRESHOLD + 0.01)
    assert should_reveal_evidence(belief, at_gamets=0.0) is True


def test_belief_that_decays_below_threshold_over_time_stops_revealing():
    """Decay-awareness is the point (design doc §2): a belief whose stored
    confidence was once well above threshold but has since decayed below
    it by a later at_gamets must return False, even though the stored
    record itself never changed."""
    belief = _belief(confidence=0.95)
    assert should_reveal_evidence(belief, at_gamets=0.0) is True

    far_future = 10 * CONFIDENCE_DECAY_HALF_LIFE  # several half-lives out
    assert should_reveal_evidence(belief, at_gamets=far_future) is False


def test_custom_threshold_overrides_the_default():
    belief = _belief(confidence=0.5)
    assert should_reveal_evidence(belief, at_gamets=0.0, threshold=0.4) is True
    assert should_reveal_evidence(belief, at_gamets=0.0, threshold=0.6) is False
