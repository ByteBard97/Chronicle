"""A pure belief-confidence -> "should a diegetic evidence object appear" gate.

docs/design/chronicle-bridge-diegetic-evidence-out.md is the design doc
this module implements the Python-only first cut of (a seventh
ChronicleBridge slice, mirroring `docs/design/chronicle-bridge-hydration-
out.md`'s, `chronicle-bridge-avoidance-out.md`'s, and `chronicle-bridge-
vendor-markup-out.md`'s own precedent). Same "chronicle/ never imports
adapter-specific concerns" boundary as every other module in this package
(see hydration.py's/avoidance.py's/vendor_markup.py's own docstrings) --
headless, no adapter dependency, pure arithmetic over `chronicle.claims`
types.

Why a new module rather than adding this to `chronicle/hydration.py`,
`chronicle/avoidance.py`, or `chronicle/vendor_markup.py` (design doc §2):
this reads a `BeliefInstance`, not a `Grudge` -- a different store
(`chronicle.claims.ClaimStore`, not `chronicle.social.SocialStateStore`)
entirely -- and produces a plain boolean gate over a different decayed
scalar (`BeliefInstance.confidence`, via `chronicle.claims.decay()`, not
`Grudge.severity` via `chronicle.social.grudge_at`). Reusing any of the
other three modules' scope would misdescribe what's here, the same
argument each of their own docstrings already makes for not reusing each
other.

The design doc's §1 walks through, in detail, why this reads
`BeliefInstance.confidence` (decayed via the existing public
`chronicle.claims.decay()`) rather than a raw sum of `Evidence.strength`:
`Evidence.strength` is set once at creation and never decays, and
`resolve()`'s own T2.3 strength-tiebreak sum is explicitly, by its own
docstring, a one-off snapshot, not a maintained or decayable quantity --
whereas `confidence` is exactly the decaying, already-aggregated "how
well-evidenced is this belief" scalar chronicle already maintains
(`corroborate()`, rule 7, already combines multiple `Evidence` records'
contribution into it via a noisy-or update). This module reads that
value; `Evidence` records themselves are not read here at all.

Unlike `Grudge`, a `BeliefInstance` has no `_cooled`-equivalent
forgiveness concept, so `should_reveal_evidence` has no second condition
to check beyond the decayed threshold -- deliberately simpler in shape
than `relationship_rank_for`/`is_avoiding`/`markup_multiplier_for`, all of
which also check a cooldown.
"""

from __future__ import annotations

from chronicle.claims import BeliefInstance, decay

# Placeholder threshold (design doc §2, "e.g. 0.6") -- not load-bearing
# precision, same tunable-not-derived status as every other constant in
# this codebase (chronicle/hydration.py's MILD_SEVERITY_THRESHOLD/
# SEVERE_SEVERITY_THRESHOLD, chronicle/vendor_markup.py's
# MARKUP_SEVERITY_FLOOR, chronicle/driver.py's AVOIDANCE_GRUDGE_THRESHOLD).
EVIDENCE_CONFIDENCE_THRESHOLD = 0.6


def should_reveal_evidence(belief: BeliefInstance, *, at_gamets: float, threshold: float = EVIDENCE_CONFIDENCE_THRESHOLD) -> bool:
    """Whether this belief is well-enough evidenced to reveal a diegetic object.

    Decays `belief` via `chronicle.claims.decay(belief, at_gamets)` --
    never the belief's stored `confidence` field directly, same decay-
    awareness discipline `relationship_rank_for`/`is_avoiding`/
    `markup_multiplier_for` each already follow for their own reads of
    `Grudge.severity` -- and returns whether the decayed `confidence` has
    cleared `threshold`. A belief whose stored confidence was once high
    but has since decayed below `threshold` by `at_gamets` returns False,
    even though nothing about the stored record itself has changed.

    `threshold` defaults to `EVIDENCE_CONFIDENCE_THRESHOLD`, the one place
    this constant is defined; this module never hardcodes a second copy of
    it. Uses `>=`, the same boundary operator `chronicle.avoidance.
    is_avoiding` uses for its own threshold comparison -- the threshold
    itself is the first confidence value that reveals evidence, not merely
    the last one that doesn't.
    """
    decayed = decay(belief, at_gamets)
    return decayed.confidence >= threshold
