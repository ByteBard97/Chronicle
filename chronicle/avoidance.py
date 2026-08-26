"""Exposing rule 18's already-computed avoidance-pair state, read-only.

docs/design/chronicle-bridge-avoidance-out.md is the design doc this
module implements the Python-only first cut of (a fourth ChronicleBridge
slice, mirroring docs/design/chronicle-bridge-hydration-out.md's own
precedent almost exactly in shape). Rule 18
(`chronicle.driver.Driver`'s `PairwiseEncounterWeightingRule` --
`_grudge_severities`/`_avoidance_thresholds`/`_evaluate_avoidance`)
already computes, every tick, exactly which NPC pairs should be avoiding
each other, and uses that state *inside the headless sim* to suppress
encounter sampling between them. This module does not change that
mechanism at all -- it is a pure, read-only re-derivation of the same
condition `_avoidance_thresholds` already implements, so a live game can
also express avoidance visibly (a future C++ slice, not this one).

Why a new module rather than adding this to `chronicle/hydration.py`:
hydration.py's whole job is *bucketing* a continuous decayed severity
into Skyrim's integer relationship-rank scale (0/-1/-2) -- a mapping with
placeholder bands and a documented "reputation deferred" scope note.
Avoidance is a different shape of question entirely: a plain boolean gate
("is this pair avoiding right now"), with no bucketing, no rank scale,
and no reputation-combination question to defer. Reusing hydration.py's
docstring/scope would misdescribe what's here. Same "chronicle/ never
imports adapter-specific concerns" boundary as every other module in this
package (see hydration.py's and sync.py's own docstrings) -- headless, no
adapter dependency, pure arithmetic over `chronicle.social`/
`chronicle.driver` types.

`is_avoiding` deliberately reuses `chronicle.driver.AVOIDANCE_GRUDGE_THRESHOLD`
as its default threshold and `chronicle.social.grudge_at`/`grudge_cooled`
for its logic -- the exact same
`severity >= threshold and not grudge_cooled(...)` condition
`Driver._avoidance_thresholds` already implements, imported and reused,
never duplicated as a second copy of the same rule.
"""

from __future__ import annotations

from chronicle.driver import AVOIDANCE_GRUDGE_THRESHOLD
from chronicle.social import Grudge, grudge_at, grudge_cooled


def is_avoiding(grudge: Grudge, *, at_gamets: float, threshold: float = AVOIDANCE_GRUDGE_THRESHOLD) -> bool:
    """Whether this grudge currently puts its holder/target pair into avoidance.

    Exactly rule 18's own `_avoidance_thresholds` condition: the grudge's
    decayed severity (`chronicle.social.grudge_at`, evaluated at
    `at_gamets`, never the grudge's stored `severity` field directly) has
    cleared `threshold` AND the grudge has not cooled
    (`chronicle.social.grudge_cooled`) -- a cooled grudge no longer gates
    behavior rules per `grudge_cooled`'s own docstring, even if its
    decayed severity happens to still read above `threshold` (the same
    "cooled means forgiven, not a leftover penalty" precedent
    `chronicle.hydration.relationship_rank_for` already follows for the
    rank-bucketing side of this same rule).

    `threshold` defaults to `chronicle.driver.AVOIDANCE_GRUDGE_THRESHOLD`
    -- the one place this constant is defined; this module never
    hardcodes a second copy of it.
    """
    decayed_severity = grudge_at(grudge, at_gamets).severity
    return decayed_severity >= threshold and not grudge_cooled(grudge, at_gamets)
