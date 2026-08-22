import random

from chronicle.schedule import ScheduleBlock, npcs_present_at, sample_encounters


def test_npcs_present_at_groups_by_location_for_a_covered_tick():
    schedule = (
        ScheduleBlock(npc_id="proventus", location_id="dragonsreach", start_tick=0, end_tick=200),
        ScheduleBlock(npc_id="irileth", location_id="dragonsreach", start_tick=0, end_tick=200),
        ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=1000),
    )
    present = npcs_present_at(schedule, tick=100)
    assert present == {"dragonsreach": ("proventus", "irileth")}


def test_npcs_present_at_excludes_locations_with_only_one_npc():
    schedule = (ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=1000),)
    assert npcs_present_at(schedule, tick=100) == {}


def test_npcs_present_at_respects_half_open_tick_range():
    schedule = (ScheduleBlock(npc_id="proventus", location_id="dragonsreach", start_tick=0, end_tick=200),)
    # A single NPC never produces a location entry regardless of tick, but
    # this still proves the boundary is honored via a second co-present NPC.
    schedule_with_pair = schedule + (
        ScheduleBlock(npc_id="irileth", location_id="dragonsreach", start_tick=0, end_tick=200),
    )
    assert npcs_present_at(schedule_with_pair, tick=199) != {}
    assert npcs_present_at(schedule_with_pair, tick=200) == {}  # end_tick is exclusive


def test_npcs_present_at_never_groups_npcs_whose_blocks_dont_both_cover_the_tick():
    # Two NPCs at the same location, but their schedules don't overlap --
    # rule 15: no "everyone within N ticks" shortcut should group them.
    schedule = (
        ScheduleBlock(npc_id="proventus", location_id="bannered_mare", start_tick=0, end_tick=100),
        ScheduleBlock(npc_id="ysolda", location_id="bannered_mare", start_tick=200, end_tick=300),
    )
    assert npcs_present_at(schedule, tick=50) == {}
    assert npcs_present_at(schedule, tick=250) == {}


def test_sample_encounters_is_deterministic_for_a_seeded_rng():
    present = {"bannered_mare": ("hulda", "proventus", "ysolda")}
    first = sample_encounters(present, rng=random.Random(42))
    second = sample_encounters(present, rng=random.Random(42))
    assert first == second


def test_sample_encounters_is_not_a_certainty_or_a_global_broadcast():
    present = {"bannered_mare": ("hulda", "proventus")}
    # Probability 0: co-presence alone never produces an encounter.
    assert sample_encounters(present, rng=random.Random(1), encounter_probability=0.0) == ()
    # Probability 1: every co-present pair does, deterministically.
    encounters = sample_encounters(present, rng=random.Random(1), encounter_probability=1.0)
    assert encounters == (("bannered_mare", "hulda", "proventus"),)


def test_sample_encounters_orders_pairs_deterministically_within_a_location():
    present = {"bannered_mare": ("ysolda", "hulda")}
    encounters = sample_encounters(present, rng=random.Random(1), encounter_probability=1.0)
    assert encounters == (("bannered_mare", "hulda", "ysolda"),)  # sorted, not insertion order


def test_sample_encounters_rolls_each_pair_independently_across_multiple_npcs():
    present = {"bannered_mare": ("hulda", "proventus", "ysolda")}
    encounters = sample_encounters(present, rng=random.Random(1), encounter_probability=1.0)
    assert set(encounters) == {
        ("bannered_mare", "hulda", "proventus"),
        ("bannered_mare", "hulda", "ysolda"),
        ("bannered_mare", "proventus", "ysolda"),
    }
