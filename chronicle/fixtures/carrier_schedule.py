"""Hand-seeded multi-hold carrier schedule for ladder rungs T2.6/T2.7.

Same stand-in status as whiterun_schedule.py: real NPC schedules are a
math-tier data concern (docs/architecture.md), not derived here. This
fixture exists to make information crossing a hold border *mechanical*:
ordinary NPCs whose schedule blocks span holds are bridge nodes by
construction (docs/scenario-ladder.md §T2.6, v0.4 -- the vision-review
catch: co-presence encounters over single-hold schedules mean every rumor
structurally dies at the hold border).

Geometry (1 tick = 1 game-hour, 24/day -- ADR-0010):

  - A small Whiterun market cast that never leaves the market.
  - Markarth residents who never leave Markarth.
  - The caravaneer: two game-days at the Whiterun market, then an explicit
    road block (the rung's road decision), then two days in Markarth --
    a multi-day cycle, one full lap of which is what T2.6 exercises.
  - The relief caravaneer on the same route, whose blocks begin only after
    T2.7's kill tick -- T2.7's positive control. It is in the schedule
    from tick 0 (Driver.schedule is fixed at construction; there is no
    mid-run NPC insertion mechanic).

Roads are explicit but otherwise empty (the rung's v0.1 scoping): a lone
carrier on a road block is a singleton at that location, npcs_present_at
drops it, and no en-route roll records exist -- so the border-holds
assertion is exact by construction. The road-leak positive case (two
travelers meeting en route) is the later fixture the rung text reserves.
"""

from __future__ import annotations

from chronicle.schedule import ScheduleBlock

TICKS_PER_DAY = 24  # ADR-0010: 1 tick = 1 gamets = 1 game-hour, 24/day.

WHITERUN_MARKET = "whiterun_market"
MARKARTH_CITY = "markarth_city"
ROAD_WHITERUN_MARKARTH = "road_whiterun_markarth"

WHITERUN_CAST = ("belethor", "carlotta", "ysolda")
MARKARTH_RESIDENTS = ("markarth_resident_1", "markarth_resident_2", "markarth_resident_3")
CARAVANEER = "caravaneer"
RELIEF_CARAVANEER = "relief_caravaneer"

# The caravaneer's cycle ticks: two days at the market, two on the road,
# two in Markarth, then the road home. T2.6's arrival assertions pin
# CARAVANEER_MARKARTH_ARRIVAL exactly (encounter_probability is pinned to
# 1.0, so the first Markarth transmission lands on the arrival tick).
CARAVANEER_DEPARTURE = 2 * TICKS_PER_DAY  # tick 48: leaves the market
CARAVANEER_MARKARTH_ARRIVAL = 4 * TICKS_PER_DAY  # tick 96: road block completes
CARAVANEER_MARKARTH_DEPARTURE = 6 * TICKS_PER_DAY  # tick 144

# The relief caravaneer's blocks begin after T2.7's kill tick (the test
# kills the caravaneer mid-way through its market stay, before departure).
RELIEF_MARKET_ARRIVAL = 25
RELIEF_DEPARTURE = 3 * TICKS_PER_DAY  # tick 72
RELIEF_MARKARTH_ARRIVAL = 5 * TICKS_PER_DAY  # tick 120
RELIEF_MARKARTH_DEPARTURE = 7 * TICKS_PER_DAY  # tick 168

# Static cast blocks span the whole run window.
END_TICK = 10 * TICKS_PER_DAY  # tick 240


def carrier_schedule() -> tuple[ScheduleBlock, ...]:
    """The multi-hold cast's schedule blocks (fixture data only -- zero engine changes, per the rung's v0.4 flag)."""
    blocks = [
        *(ScheduleBlock(npc_id=npc, location_id=WHITERUN_MARKET, start_tick=0, end_tick=END_TICK) for npc in WHITERUN_CAST),
        *(ScheduleBlock(npc_id=npc, location_id=MARKARTH_CITY, start_tick=0, end_tick=END_TICK) for npc in MARKARTH_RESIDENTS),
        # The caravaneer's Whiterun <-> Markarth lap.
        ScheduleBlock(npc_id=CARAVANEER, location_id=WHITERUN_MARKET, start_tick=0, end_tick=CARAVANEER_DEPARTURE),
        ScheduleBlock(npc_id=CARAVANEER, location_id=ROAD_WHITERUN_MARKARTH, start_tick=CARAVANEER_DEPARTURE, end_tick=CARAVANEER_MARKARTH_ARRIVAL),
        ScheduleBlock(npc_id=CARAVANEER, location_id=MARKARTH_CITY, start_tick=CARAVANEER_MARKARTH_ARRIVAL, end_tick=CARAVANEER_MARKARTH_DEPARTURE),
        ScheduleBlock(npc_id=CARAVANEER, location_id=ROAD_WHITERUN_MARKARTH, start_tick=CARAVANEER_MARKARTH_DEPARTURE, end_tick=8 * TICKS_PER_DAY),
        ScheduleBlock(npc_id=CARAVANEER, location_id=WHITERUN_MARKET, start_tick=8 * TICKS_PER_DAY, end_tick=END_TICK),
        # T2.7's positive control: same route, blocks beginning after the kill tick.
        ScheduleBlock(npc_id=RELIEF_CARAVANEER, location_id=WHITERUN_MARKET, start_tick=RELIEF_MARKET_ARRIVAL, end_tick=RELIEF_DEPARTURE),
        ScheduleBlock(npc_id=RELIEF_CARAVANEER, location_id=ROAD_WHITERUN_MARKARTH, start_tick=RELIEF_DEPARTURE, end_tick=RELIEF_MARKARTH_ARRIVAL),
        ScheduleBlock(npc_id=RELIEF_CARAVANEER, location_id=MARKARTH_CITY, start_tick=RELIEF_MARKARTH_ARRIVAL, end_tick=RELIEF_MARKARTH_DEPARTURE),
    ]
    return tuple(blocks)
