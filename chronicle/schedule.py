"""NPC schedules and encounter sampling -- docs/v0.1-spec.md rules 2 and 15.

Rule 2: rumor propagation requires a sampled encounter (shared location +
schedule overlap) -- never a global broadcast.
Rule 15: encounter sampling draws from NPC schedules -- no "everyone
within N ticks" shortcut.

This module supplies the primitive both rules name: presence is computed
from each NPC's own timetable (npcs_present_at), and whether a
co-present pair actually has an encounter this tick is a probabilistic
roll (sample_encounters), not a certainty. It does not decide what
happens *because of* an encounter -- that's chronicle.claims.retell()'s
job; this module only answers "who could plausibly have talked to whom,
right now."

v0.1 hand-seeds schedules for the known Whiterun cast (see
chronicle/fixtures/whiterun_schedule.py), the same stand-in status
chronicle/social.py's fixture uses for relationships: real,
data-driven NPC schedules are a math-tier concern (docs/architecture.md),
but the sampling mechanics here don't change shape when that data source
changes -- only the caller supplying ScheduleBlocks does.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from chronicle import rng as _rng

# Placeholder tunable, same status as claims.py's decay/retell constants --
# not derived from any source report, set empirically once the math tier
# calibrates it against a scenario.
ENCOUNTER_PROBABILITY = 0.5


@dataclass(frozen=True)
class ScheduleBlock:
    """One NPC's presence at one location for a half-open tick range [start_tick, end_tick)."""

    npc_id: str
    location_id: str
    start_tick: int
    end_tick: int

    def __post_init__(self) -> None:
        if self.end_tick <= self.start_tick:
            raise ValueError(f"end_tick ({self.end_tick}) must be after start_tick ({self.start_tick})")

    def covers(self, tick: int) -> bool:
        return self.start_tick <= tick < self.end_tick


def effective_schedule_at(
    base: Sequence[ScheduleBlock],
    overlays: Sequence[ScheduleBlock],
    tick: int,
) -> tuple[ScheduleBlock, ...]:
    """The schedule blocks in effect at one tick (Tier 4a, ladder T4a.1): social-state write-back.

    Base blocks covering ``tick``, except any NPC with an overlay covering
    ``tick`` has ALL of their base presence at this tick replaced by the
    overlay -- total override, not merge (an NPC can't be at two places at
    once). Overlays are ordinary ``ScheduleBlock``s (an inserted mourning
    block is structurally identical to a base one -- Tier 4a's write-back
    needs no new shape); restoration is automatic once ``tick`` moves past
    an overlay's ``end_tick`` and the base blocks apply again unmodified,
    which is why there is no separate "restore" step anywhere.

    This is the ONE place presence-with-overlays is computed (design doc
    T1/T3): both the live driver's tick loop and ``framelog.state_at``'s
    reconstruction call this, so the two can't drift apart. It is also
    why the T4a.2 roll-identity guarantee holds automatically --
    ``sample_encounters`` below rolls each pair independently of who else
    is present, so overriding one NPC's presence here never touches any
    roll that doesn't name them.
    """
    overridden = {overlay.npc_id for overlay in overlays if overlay.covers(tick)}
    return tuple(block for block in base if block.covers(tick) and block.npc_id not in overridden) + tuple(
        overlay for overlay in overlays if overlay.covers(tick)
    )


def npcs_present_at(schedule: Sequence[ScheduleBlock], tick: int) -> dict[str, tuple[str, ...]]:
    """Group NPCs by location for one tick, from whichever schedule blocks cover it.

    Only locations with 2+ present NPCs are returned -- a lone NPC can't
    have an encounter. This is computed strictly from each NPC's own
    ScheduleBlocks; there is no "everyone within N ticks of each other"
    shortcut here (rule 15) -- two NPCs whose blocks don't both cover
    this exact tick are never grouped, no matter how close their
    schedules run.
    """
    by_location: dict[str, list[str]] = {}
    for block in schedule:
        if block.covers(tick):
            by_location.setdefault(block.location_id, []).append(block.npc_id)
    return {location: tuple(npcs) for location, npcs in by_location.items() if len(npcs) >= 2}


@dataclass(frozen=True)
class EncounterRoll:
    """The outcome of one keyed co-presence roll for one NPC pair at one tick.

    Negative results are first-class (ui-doctrines D7, frame-log schema §4):
    encountered=False is a rolled-against row, not an absence -- the driver
    emits every roll to the trace, not just the ones that fired.
    """

    location_id: str
    npc_a: str
    npc_b: str
    roll_key: Mapping[str, object]
    value: float
    threshold: float
    encountered: bool


def sample_encounters(
    present_by_location: Mapping[str, tuple[str, ...]],
    *,
    seed_id: str,
    tick: int,
    encounter_probability: float = ENCOUNTER_PROBABILITY,
    pair_thresholds: Mapping[frozenset[str], float] | None = None,
) -> tuple[EncounterRoll, ...]:
    """Roll which co-present NPC pairs actually encounter each other this tick.

    Returns one EncounterRoll per co-present pair -- co-presence alone is
    not an encounter (rule 2: a sampled encounter, never a certainty or a
    global broadcast), and the rolled-against rows (encountered=False) are
    returned alongside the fired ones so the caller can log them (frame-log
    schema §4's encounter_rolled record). Pairs within a location are
    ordered deterministically (sorted).

    Each pair's roll is keyed (ADR-0009): a pure function of
    (seed_id, "encounter.co-presence", tick, location_id, (npc_a, npc_b),
    draw=0), with no sequential stream state -- an added NPC, a reordered
    iteration, or a fork re-sim cannot shift any other pair's roll.
    seed_id is caller-supplied (the run's statistical identity, carried by
    the frame-log envelope from record one), the same explicit-dependency
    discipline as gamets on decay()/retell() elsewhere in this codebase.

    ``pair_thresholds`` is Tier 4b's avoidance seam (design doc
    tier-4b-avoidance.md, decision W1): a per-pair threshold
    REPLACEMENT, keyed by the unordered pair (``frozenset``, since a
    grudge is directional but the roll's threshold is about the pair,
    not who holds it against whom). A pair present in the mapping
    compares its roll against that value instead of
    ``encounter_probability``; every other pair is unaffected --
    migration-safe by construction (no mapping, byte-identical to
    today). The roll ``value`` itself never changes either way -- only
    what it's compared against.
    """
    # T4a.2's roll-identity guarantee (design doc T4) depends on this loop
    # rolling each pair independently of the rest of ``present_by_location``
    # -- a pair's roll never reads who else is present at this location, so
    # effective_schedule_at()'s overlay override (Tier 4a) can change who's
    # in this dict without perturbing any roll for a pair it doesn't name.
    # A future refactor that rolls once per site (rather than per pair)
    # would break this silently -- keep the independence.
    rolls: list[EncounterRoll] = []
    for location_id, npc_ids in present_by_location.items():
        ordered = sorted(npc_ids)
        for i, npc_a in enumerate(ordered):
            for npc_b in ordered[i + 1 :]:
                value = _rng.roll(
                    seed_id=seed_id,
                    purpose=_rng.ENCOUNTER_CO_PRESENCE,
                    tick=tick,
                    site=location_id,
                    participants=(npc_a, npc_b),
                    draw=0,
                )
                threshold = (
                    pair_thresholds.get(frozenset((npc_a, npc_b)), encounter_probability)
                    if pair_thresholds is not None
                    else encounter_probability
                )
                rolls.append(
                    EncounterRoll(
                        location_id=location_id,
                        npc_a=npc_a,
                        npc_b=npc_b,
                        roll_key=_rng.roll_key(
                            seed_id=seed_id,
                            purpose=_rng.ENCOUNTER_CO_PRESENCE,
                            tick=tick,
                            site=location_id,
                            participants=(npc_a, npc_b),
                            draw=0,
                        ),
                        value=value,
                        threshold=threshold,
                        encountered=value < threshold,
                    )
                )
    return tuple(rolls)
