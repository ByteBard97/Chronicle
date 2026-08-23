"""chronicle/rng.py: the keyed-roll choke point (ADR-0009)."""

import pytest

from chronicle import rng


def test_roll_is_deterministic_for_an_identical_key():
    key = {"seed_id": "seed", "purpose": rng.ENCOUNTER_CO_PRESENCE, "tick": 5, "site": "bannered_mare", "participants": ("hulda", "ysolda"), "draw": 0}
    assert rng.roll(**key) == rng.roll(**key)


def test_roll_is_in_unit_interval():
    for tick in range(200):
        value = rng.roll(seed_id="seed", purpose=rng.ENCOUNTER_CO_PRESENCE, tick=tick, site="loc", participants=("a", "b"), draw=0)
        assert 0.0 <= value < 1.0


def test_roll_participants_are_order_normalized():
    forward = rng.roll(seed_id="s", purpose=rng.ENCOUNTER_CO_PRESENCE, tick=1, site="loc", participants=("a", "b"), draw=0)
    reversed_ = rng.roll(seed_id="s", purpose=rng.ENCOUNTER_CO_PRESENCE, tick=1, site="loc", participants=("b", "a"), draw=0)
    assert forward == reversed_


def test_roll_value_changes_with_any_key_member():
    base = {"seed_id": "s", "purpose": rng.ENCOUNTER_CO_PRESENCE, "tick": 1, "site": "loc", "participants": ("a", "b"), "draw": 0}
    base_value = rng.roll(**base)
    for override in (
        {"seed_id": "other"},
        {"purpose": rng.TELL_DECISION},
        {"tick": 2},
        {"site": "other"},
        {"participants": ("a", "c")},
        {"draw": 1},
    ):
        assert rng.roll(**{**base, **override}) != base_value


def test_roll_rejects_unregistered_purposes():
    with pytest.raises(ValueError):
        rng.roll(seed_id="s", purpose="ad.hoc.nonsense", tick=1, site="loc", participants=("a",), draw=0)


def test_roll_key_serializes_participants_sorted():
    key = rng.roll_key(seed_id="s", purpose=rng.ENCOUNTER_CO_PRESENCE, tick=1, site="loc", participants=("b", "a"), draw=0)
    assert key == {
        "seed_id": "s",
        "purpose": "encounter.co-presence",
        "tick": 1,
        "site": "loc",
        "participants": ["a", "b"],
        "draw": 0,
    }
