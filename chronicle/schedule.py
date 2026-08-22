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

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

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


def sample_encounters(
    present_by_location: Mapping[str, tuple[str, ...]],
    *,
    rng: random.Random,
    encounter_probability: float = ENCOUNTER_PROBABILITY,
) -> tuple[tuple[str, str, str], ...]:
    """Roll which co-present NPC pairs actually encounter each other this tick.

    Returns (location_id, npc_a, npc_b) triples, one per pair that rolled
    an actual encounter -- co-presence alone is not an encounter (rule 2:
    a sampled encounter, never a certainty or a global broadcast). Pairs
    within a location are ordered deterministically (sorted) so the same
    schedule + rng seed always reproduces the same result, which is what
    makes this testable/replayable rather than a hidden random shortcut.

    rng is caller-supplied rather than a module-level random instance --
    the same explicit-dependency discipline as gamets on decay()/retell()
    elsewhere in this codebase, so a scenario can seed it for a
    reproducible run.
    """
    encounters: list[tuple[str, str, str]] = []
    for location_id, npc_ids in present_by_location.items():
        ordered = sorted(npc_ids)
        for i, npc_a in enumerate(ordered):
            for npc_b in ordered[i + 1 :]:
                if rng.random() < encounter_probability:
                    encounters.append((location_id, npc_a, npc_b))
    return tuple(encounters)
