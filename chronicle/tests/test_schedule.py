import pytest

from chronicle.schedule import (
    ScheduleBlock,
    effective_schedule_at,
    npcs_present_at,
    sample_encounters,
)


def test_schedule_block_rejects_an_end_tick_at_or_before_start_tick():
    with pytest.raises(ValueError, match="must be after start_tick"):
        ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=10, end_tick=10)


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


def test_sample_encounters_is_deterministic_for_a_seed_id():
    present = {"bannered_mare": ("hulda", "proventus", "ysolda")}
    first = sample_encounters(present, seed_id="seed-a", tick=7)
    second = sample_encounters(present, seed_id="seed-a", tick=7)
    assert first == second


def test_sample_encounters_rolls_are_keyed_not_sequential():
    # ADR-0009's load-bearing property: a pair's roll is a pure function of
    # its key, so adding another co-present NPC cannot shift it -- unlike a
    # sequential rng stream, where one more pair upstream moves every
    # downstream roll.
    pair_only = sample_encounters({"bannered_mare": ("hulda", "proventus")}, seed_id="seed-a", tick=7)
    with_third = sample_encounters({"bannered_mare": ("hulda", "proventus", "ysolda")}, seed_id="seed-a", tick=7)
    assert pair_only[0].npc_a == "hulda" and pair_only[0].npc_b == "proventus"
    assert with_third[0].value == pair_only[0].value
    assert with_third[0].encountered == pair_only[0].encountered
    # ...and a different tick or seed is a different roll.
    other_tick = sample_encounters({"bannered_mare": ("hulda", "proventus")}, seed_id="seed-a", tick=8)
    other_seed = sample_encounters({"bannered_mare": ("hulda", "proventus")}, seed_id="seed-b", tick=7)
    assert other_tick[0].value != pair_only[0].value
    assert other_seed[0].value != pair_only[0].value


def test_sample_encounters_is_not_a_certainty_or_a_global_broadcast():
    present = {"bannered_mare": ("hulda", "proventus")}
    # Probability 0: co-presence alone never produces an encounter.
    assert [r.encountered for r in sample_encounters(present, seed_id="seed-a", tick=1, encounter_probability=0.0)] == [False]
    # Probability 1: every co-present pair does, deterministically.
    encounters = sample_encounters(present, seed_id="seed-a", tick=1, encounter_probability=1.0)
    assert [(r.location_id, r.npc_a, r.npc_b) for r in encounters if r.encountered] == [("bannered_mare", "hulda", "proventus")]


def test_sample_encounters_pair_thresholds_overrides_only_the_named_pair():
    # Tier 4b (design doc W1): a pair present in pair_thresholds compares
    # against that value instead of encounter_probability; the roll's
    # value is unaffected either way, only what it's compared against.
    present = {"bannered_mare": ("hulda", "proventus", "ysolda")}
    baseline = sample_encounters(present, seed_id="seed-a", tick=1, encounter_probability=1.0)
    overridden = sample_encounters(
        present, seed_id="seed-a", tick=1, encounter_probability=1.0,
        pair_thresholds={frozenset(("hulda", "proventus")): 0.0},
    )
    by_pair_baseline = {(r.npc_a, r.npc_b): r for r in baseline}
    by_pair_overridden = {(r.npc_a, r.npc_b): r for r in overridden}
    # The named pair: threshold overridden, never encounters (roll value
    # in [0,1) is never < 0.0); its own roll value is untouched.
    named = by_pair_overridden[("hulda", "proventus")]
    assert named.threshold == 0.0
    assert named.encountered is False
    assert named.value == by_pair_baseline[("hulda", "proventus")].value
    # Every other pair: untouched, byte-identical to the no-override run.
    for key in (("hulda", "ysolda"), ("proventus", "ysolda")):
        assert by_pair_overridden[key] == by_pair_baseline[key]


def test_sample_encounters_orders_pairs_deterministically_within_a_location():
    present = {"bannered_mare": ("ysolda", "hulda")}
    encounters = sample_encounters(present, seed_id="seed-a", tick=1, encounter_probability=1.0)
    assert [(r.npc_a, r.npc_b) for r in encounters] == [("hulda", "ysolda")]  # sorted, not insertion order


def test_effective_schedule_at_overrides_only_the_overlay_npcs_own_presence():
    # Tier 4a (design doc T1/T4): base has sven + camilla at the house; an
    # active overlay sends sven to the temple. Camilla's base block is
    # untouched -- present unmodified, no merge with the overlay's site.
    base = (
        ScheduleBlock(npc_id="sven", location_id="house", start_tick=0, end_tick=100),
        ScheduleBlock(npc_id="camilla", location_id="house", start_tick=0, end_tick=100),
    )
    overlay = (ScheduleBlock(npc_id="sven", location_id="temple", start_tick=10, end_tick=30),)
    effective = effective_schedule_at(base, overlay, tick=15)
    assert set(effective) == {
        ScheduleBlock(npc_id="camilla", location_id="house", start_tick=0, end_tick=100),
        ScheduleBlock(npc_id="sven", location_id="temple", start_tick=10, end_tick=30),
    }


def test_effective_schedule_at_restores_the_base_once_the_overlay_ends():
    base = (ScheduleBlock(npc_id="sven", location_id="house", start_tick=0, end_tick=100),)
    overlay = (ScheduleBlock(npc_id="sven", location_id="temple", start_tick=10, end_tick=30),)
    assert effective_schedule_at(base, overlay, tick=9) == base
    assert effective_schedule_at(base, overlay, tick=30) == base  # end_tick exclusive: restored already
    assert effective_schedule_at(base, overlay, tick=15) == (
        ScheduleBlock(npc_id="sven", location_id="temple", start_tick=10, end_tick=30),
    )


def test_effective_schedule_at_with_no_overlays_is_the_base_unfiltered_by_nothing_extra():
    base = (ScheduleBlock(npc_id="sven", location_id="house", start_tick=0, end_tick=100),)
    assert effective_schedule_at(base, (), tick=50) == base
    assert effective_schedule_at(base, (), tick=200) == ()  # outside the base block too


def test_sample_encounters_rolls_each_pair_independently_across_multiple_npcs():
    present = {"bannered_mare": ("hulda", "proventus", "ysolda")}
    rolls = sample_encounters(present, seed_id="seed-a", tick=1, encounter_probability=1.0)
    assert {(r.location_id, r.npc_a, r.npc_b) for r in rolls if r.encountered} == {
        ("bannered_mare", "hulda", "proventus"),
        ("bannered_mare", "hulda", "ysolda"),
        ("bannered_mare", "proventus", "ysolda"),
    }
    # Each pair's roll carries its own key (frame-log schema §4's
    # encounter_rolled record): distinct participants, distinct keys.
    keys = [tuple(r.roll_key["participants"]) for r in rolls]
    assert len(set(keys)) == 3
