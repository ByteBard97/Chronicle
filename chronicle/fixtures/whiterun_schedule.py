"""Hand-seeded schedule blocks for v0.1's Whiterun cast.

Same stand-in status as whiterun_relationships.py: real NPC schedules are
a math-tier data concern (docs/architecture.md), not derived here. Only
the tick ranges the v0.1 scenario suite actually exercises are seeded --
this is not an attempt at a complete Whiterun daily routine.
"""

from __future__ import annotations

from chronicle.schedule import ScheduleBlock


def whiterun_schedule() -> tuple[ScheduleBlock, ...]:
    """Blocks covering the tick range test_jarl_death_social_cascade.py and
    its scenario siblings run in -- Dragonsreach around the Jarl's death,
    then the Bannered Mare tavern afterward, where the story travels next.
    """
    return (
        ScheduleBlock(npc_id="jarl_balgruuf", location_id="dragonsreach", start_tick=0, end_tick=200),
        ScheduleBlock(npc_id="proventus", location_id="dragonsreach", start_tick=0, end_tick=200),
        ScheduleBlock(npc_id="irileth", location_id="dragonsreach", start_tick=0, end_tick=200),
        ScheduleBlock(npc_id="whiterun_guard_1", location_id="dragonsreach", start_tick=50, end_tick=150),
        # After the court disperses, Proventus and Irileth head to the tavern,
        # where Hulda and Ysolda are already present -- schedule overlap that
        # makes an encounter between the witnesses and the tavern regulars
        # plausible, without asserting it's certain (chronicle.schedule
        # samples that).
        ScheduleBlock(npc_id="proventus", location_id="bannered_mare", start_tick=200, end_tick=400),
        ScheduleBlock(npc_id="irileth", location_id="bannered_mare", start_tick=250, end_tick=350),
        ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=1000),
        ScheduleBlock(npc_id="ysolda", location_id="bannered_mare", start_tick=200, end_tick=300),
    )
