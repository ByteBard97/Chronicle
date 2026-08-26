"""A pure grudge-severity -> vendor price-markup multiplier.

docs/design/chronicle-bridge-vendor-markup-out.md is the design doc this
module implements the Python-only first cut of (a fifth ChronicleBridge
slice, mirroring `docs/design/chronicle-bridge-hydration-out.md`'s and
`docs/design/chronicle-bridge-avoidance-out.md`'s own precedent). The
design doc's own §1 poses an open question ("decide at implementation
time") on whether this belongs in `chronicle/hydration.py` or a new
module -- resolved here the same way `chronicle/avoidance.py`'s own
docstring resolved the identical question for itself (see that module's
"Why a new module rather than adding this to `chronicle/hydration.py`"
paragraph): check whether hydration.py's own scope/docstring already
covers this kind of question cleanly. It does not, for the same reason
avoidance didn't -- hydration.py's whole job is *bucketing* a continuous
decayed severity into Skyrim's small INTEGER relationship-rank scale
(0/-1/-2), a fundamentally discrete mapping. This slice's output is a
continuous float multiplier with no rank/bucket concept at all -- reusing
hydration.py's docstring would misdescribe what's here just as badly as
it would have for avoidance's boolean-gate question. A third, independent
new module is the honest fit, same as avoidance.py was for its own
differently-shaped question.

Same "chronicle/ never imports adapter-specific concerns" boundary as
every other module in this package (see hydration.py's/avoidance.py's/
sync.py's own docstrings) -- headless, no adapter dependency, pure
arithmetic over `chronicle.social` types.

`markup_multiplier_for` reuses `chronicle.social.grudge_at`'s decayed
severity and `chronicle.social.grudge_cooled` for its "cooled means no
markup" rule -- the exact same "a cooled grudge no longer gates behavior,
per `grudge_cooled`'s own docstring" precedent
`chronicle.hydration.relationship_rank_for` (hydration.py:79-80) and
`chronicle.avoidance.is_avoiding` (avoidance.py:51-55) both already
follow for their own reads of this same `Grudge` state. This module does
not reinvent that reasoning -- see those two docstrings for the fuller
argument; the short version is that `grudge_cooled`'s own docstring says
a cooled grudge "no longer gates behavior rules... it is never deleted,"
so every read of `Grudge` state in this codebase treats "cooled" as
"back to baseline," never as a leftover, decaying penalty.
"""

from __future__ import annotations

from chronicle.social import Grudge, grudge_at, grudge_cooled

# Placeholder band/curve (design doc §1) -- not load-bearing precision,
# the same tunable-not-derived status as every other constant in this
# codebase (chronicle/social.py's GRUDGE_EMOTIONAL_WEIGHT/half-lives,
# chronicle/hydration.py's MILD_SEVERITY_THRESHOLD/SEVERE_SEVERITY_
# THRESHOLD, chronicle/driver.py's AVOIDANCE_GRUDGE_THRESHOLD).
#
# MARKUP_SEVERITY_FLOOR mirrors chronicle/hydration.py's own
# MILD_SEVERITY_THRESHOLD (0.2, hydration.py:40) -- the same "a grudge
# this mild doesn't matter yet" cutoff already established for reading
# this exact Grudge.severity scale a second way (hydration's rank bucket)
# and a third way (avoidance's boolean gate, which reuses
# AVOIDANCE_GRUDGE_THRESHOLD=0.5 instead -- a stricter threshold, because
# avoidance is a much bigger behavioral claim than a price nudge). A price
# markup is a small, low-stakes signal compared to either of those, so
# starting the curve at hydration's lower 0.2 floor rather than
# avoidance's 0.5 is deliberate, not an oversight.
#
# MARKUP_CEILING is the design doc's own suggested placeholder (§0/§1:
# "a placeholder ceiling around 1.5, respecting fBarterBuyMin's existing
# 1.05 floor as a documented real constraint, not a number to silently
# violate"). `fBarterBuyMin`'s default of 1.05 (docs/research/
# 16-skyrim-economy-mods.md) is a real Skyrim game-setting floor on the
# price a vendor already buys/sells at -- this module does not enforce
# that floor itself (the design doc is explicit that's "the eventual
# game-side consumer's job," §0), but the curve below is designed so it
# can NEVER imply a price below vanilla: the multiplier's own floor is
# 1.0 (no discount, never < 1.0), so a future consumer that simply
# multiplies a vanilla price by this value can never produce a price
# lower than fBarterBuyMin already guarantees. 1.5 as a ceiling ("50%
# over vanilla price") is comfortably inside a plausible in-game range
# for "this merchant really doesn't like you" without needing real
# playtesting data to justify a precise number yet.
MARKUP_NO_MARKUP = 1.0
MARKUP_SEVERITY_FLOOR = 0.2
MARKUP_CEILING = 1.5


def markup_multiplier_for(grudge: Grudge | None, *, at_gamets: float) -> float:
    """A grudge holder's price markup multiplier toward its target.

    - `grudge is None` -> `1.0` (no markup) -- there is no grudge to read
      a severity from, so this returns the plain no-op multiplier rather
      than raising, mirroring `relationship_rank_for`'s and
      `is_avoiding`'s own `grudge is None`/no-grudge handling.
    - decayed severity (`chronicle.social.grudge_at(grudge,
      at_gamets).severity` -- the decayed value, never the grudge's
      stored `severity` field directly, same decay-awareness discipline
      as `relationship_rank_for`) below `MARKUP_SEVERITY_FLOOR` (0.2) ->
      `1.0`.
    - the grudge HAS cooled (`chronicle.social.grudge_cooled`) -> `1.0`,
      regardless of decayed severity -- the same "cooled means forgiven,
      not a leftover penalty" precedent `relationship_rank_for` and
      `is_avoiding` both already follow (see module docstring). Checked
      unconditionally, not only above the floor, so a grudge whose
      `forgiveness_threshold` happens to be configured unusually high
      (the same edge case `relationship_rank_for`'s own docstring names)
      still buckets to no-markup once cooled, exactly like the other two
      readers of this state.
    - otherwise, a continuous linear ramp from `1.0` at
      `MARKUP_SEVERITY_FLOOR` up to `MARKUP_CEILING` (1.5) at a decayed
      severity of `1.0` (the top of `Grudge.severity`'s own `[0, 1]`
      range, `chronicle/social.py`'s `_require_unit_interval`). This is
      deliberately continuous, not banded like `relationship_rank_for`'s
      discrete ranks -- a price multiplier has no natural "step" the way
      Skyrim's integer relationship-rank scale does, so a smooth ramp is
      the more honest shape for this particular output, not an arbitrary
      stylistic choice.

    Never returns a value below 1.0 -- see the module-level constants'
    comment on why that matters against `fBarterBuyMin`'s real 1.05
    floor, even though enforcing that floor itself is out of scope here
    (design doc §0).
    """
    if grudge is None:
        return MARKUP_NO_MARKUP

    decayed_severity = grudge_at(grudge, at_gamets).severity

    if grudge_cooled(grudge, at_gamets):
        return MARKUP_NO_MARKUP
    if decayed_severity < MARKUP_SEVERITY_FLOOR:
        return MARKUP_NO_MARKUP

    fraction = (decayed_severity - MARKUP_SEVERITY_FLOOR) / (1.0 - MARKUP_SEVERITY_FLOOR)
    return MARKUP_NO_MARKUP + fraction * (MARKUP_CEILING - MARKUP_NO_MARKUP)
