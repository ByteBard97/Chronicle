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
        # 18 more named NPCs added 2026-08-26, matching the 18 new
        # kNamedCast entries in adapters/skyrim/ChronicleBridge/src/
        # IdentityMap.cpp (same npc_id strings, chosen there first). Plain
        # daytime/market-hours presence windows on the same 0-1000 tick
        # scale already in use above -- not a modeled Skyrim AI package,
        # just enough presence to make each NPC schedulable/encounterable.
        #
        # Carlotta's produce stall in the marketplace, with her daughter
        # Lucia nearby.
        ScheduleBlock(npc_id="carlotta_valentia", location_id="whiterun_marketplace", start_tick=0, end_tick=600),
        ScheduleBlock(npc_id="lucia", location_id="whiterun_marketplace", start_tick=0, end_tick=600),
        # Amren and his wife Saffir, near their house in the Wind District.
        ScheduleBlock(npc_id="amren", location_id="whiterun_marketplace", start_tick=100, end_tick=400),
        ScheduleBlock(npc_id="saffir", location_id="whiterun_marketplace", start_tick=100, end_tick=400),
        # Warmaiden's: Adrianne at the forge, Sigurd assisting.
        ScheduleBlock(npc_id="adrianne_avenicci", location_id="warmaidens_forge", start_tick=0, end_tick=800),
        ScheduleBlock(npc_id="sigurd", location_id="warmaidens_forge", start_tick=0, end_tick=800),
        # The Battle-Born household: Idolaf and his son Lars.
        ScheduleBlock(npc_id="idolaf_battle_born", location_id="battle_born_house", start_tick=0, end_tick=500),
        ScheduleBlock(npc_id="lars_battle_born", location_id="battle_born_house", start_tick=0, end_tick=500),
        # Braith, a child usually seen around the marketplace/streets.
        ScheduleBlock(npc_id="braith", location_id="whiterun_marketplace", start_tick=100, end_tick=500),
        # The Gray-Mane household: Fralia and her daughter Olfina.
        ScheduleBlock(npc_id="fralia_gray_mane", location_id="gray_mane_house", start_tick=0, end_tick=500),
        ScheduleBlock(npc_id="olfina_gray_mane", location_id="gray_mane_house", start_tick=0, end_tick=500),
        # Nazeem, a wealthy resident often seen around the Cloud District.
        ScheduleBlock(npc_id="nazeem", location_id="cloud_district", start_tick=100, end_tick=400),
        # Lillith Maiden-Loom, a weaver near the marketplace.
        ScheduleBlock(npc_id="lillith_maiden_loom", location_id="whiterun_marketplace", start_tick=0, end_tick=600),
        # Brenuin, a beggar seen around the temple steps.
        ScheduleBlock(npc_id="brenuin", location_id="temple_of_kynareth", start_tick=0, end_tick=1000),
        # Anoriath, works at the Drunken Huntsman.
        ScheduleBlock(npc_id="anoriath", location_id="drunken_huntsman", start_tick=0, end_tick=1000),
        # Heimskr, preaching near the Gildergreen.
        ScheduleBlock(npc_id="heimskr", location_id="gildergreen", start_tick=0, end_tick=1000),
        # Olava the Feeble, a fortune-teller near her house by the city wall.
        ScheduleBlock(npc_id="olava_the_feeble", location_id="olava_house", start_tick=100, end_tick=500),
        # Danica Pure-Spring, priestess of the Temple of Kynareth.
        ScheduleBlock(npc_id="danica_pure_spring", location_id="temple_of_kynareth", start_tick=0, end_tick=1000),
    )
