"""Bucketing Chronicle's social state into Skyrim's relationship-rank scale.

docs/design/chronicle-bridge-hydration-out.md is the design doc this
module implements the Python-only first cut of (§3b). The "Out" direction
of the ChronicleBridge seam (sim state -> game) needs to map Chronicle's
continuous `Grudge.severity` (a Beta-mean-adjacent [0, 1] float, decayed
at read time by `chronicle.social.grudge_at`) onto Skyrim's native
`Actor.SetRelationshipRank` scale, which is a small integer band
(roughly -4..4; this module only ever produces 0, -1, or -2 for now).

Headless, no adapter dependency -- same "chronicle/ never imports
adapter-specific concerns" boundary `chronicle/sync.py` follows (see that
module's docstring). Nothing here knows about listener.py, HTTP, or
ChronicleBridge; it is pure arithmetic over `chronicle.social` types.

Reputation is explicitly deferred for this first cut (design doc §3b):
`relationship_rank_for` takes only a `Grudge | None`, not a `Reputation`.
The design doc allows folding `Reputation`'s Beta-mean in "only if you
find a clean way to combine the two signals -- otherwise grudge alone...
reputation deferred, and say so explicitly rather than inventing a
combination formula." No clean combination was found here, so this is
grudge-only; combining the two signals is future work, not silently
dropped.
"""

from __future__ import annotations

from chronicle.social import Grudge, grudge_at, grudge_cooled

# Placeholder bucketing bands (design doc §2/§3b) -- not load-bearing
# precision, same tunable-not-derived status as every other constant in
# chronicle/social.py (GRUDGE_EMOTIONAL_WEIGHT et al.). Keyed on decayed
# severity (chronicle.social.grudge_at's output), not stored severity --
# a grudge that has cooled since it was last rehearsed must bucket back
# toward 0, not stay pinned at whatever its stored severity once was.
RANK_NO_GRUDGE = 0
RANK_MILD_GRUDGE = -1
RANK_SEVERE_GRUDGE = -2

MILD_SEVERITY_THRESHOLD = 0.2
SEVERE_SEVERITY_THRESHOLD = 0.5


def relationship_rank_for(grudge: Grudge | None, *, at_gamets: float) -> int:
    """Bucket a grudge's decayed severity into Skyrim's relationship-rank scale.

    Grudge-only for this first cut (see module docstring) -- Reputation
    is deferred, not combined in.

    - `grudge is None` -> 0 (no grudge, no discount).
    - decayed severity < 0.2 -> 0.
    - 0.2 <= decayed severity <= 0.5 -> -1.
    - decayed severity > 0.5 AND the grudge has not cooled
      (`chronicle.social.grudge_cooled`) -> -2.
    - decayed severity > 0.5 but the grudge HAS cooled (its own
      forgiveness_threshold is set above 0.5, an unusual but legal
      configuration) -> 0, not -2 or -1. `grudge_cooled`'s own docstring
      says a cooled grudge "no longer gates behavior rules... it is never
      deleted" -- cooled means forgiven, and this function has no band
      between "forgiven" and "mild," so cooled buckets all the way back
      to no discount rather than inventing an intermediate penalty.

    Decay-awareness is the point: this buckets `grudge_at(grudge,
    at_gamets).severity`, the decayed value, never the grudge's stored
    `severity` field directly -- a grudge that was once severe but has
    since cooled reports a low decayed severity here and buckets
    accordingly, per docs/design/chronicle-bridge-hydration-out.md §3b's
    explicit "decay-awareness" requirement.
    """
    if grudge is None:
        return RANK_NO_GRUDGE

    decayed_severity = grudge_at(grudge, at_gamets).severity

    if decayed_severity < MILD_SEVERITY_THRESHOLD:
        return RANK_NO_GRUDGE
    if decayed_severity <= SEVERE_SEVERITY_THRESHOLD:
        return RANK_MILD_GRUDGE
    if grudge_cooled(grudge, at_gamets):
        return RANK_NO_GRUDGE
    return RANK_SEVERE_GRUDGE
