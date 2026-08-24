"""chronicle/roles.py: RoleStore's install/holder_of/roles_held_by/vacate (design doc S1)."""

import pytest

from chronicle.roles import Duty, Role, RoleStore

_STEWARD = Role(
    id="steward_of_whiterun",
    title="Steward of Whiterun",
    institution_id="whiterun_court",
    duties=(Duty(name="collect_taxes", lapse_status_kind="duty_lapsed"),),
    holder_id="proventus",
    vacated_at=None,
)


def test_holder_of_reflects_the_installed_holder():
    store = RoleStore()
    store.install(_STEWARD)
    assert store.holder_of("steward_of_whiterun") == "proventus"
    assert store.role("steward_of_whiterun") == _STEWARD


def test_holder_of_is_none_for_an_unknown_role():
    store = RoleStore()
    assert store.holder_of("no_such_role") is None


def test_install_rejects_a_second_install_of_the_same_role_id():
    store = RoleStore()
    store.install(_STEWARD)
    with pytest.raises(ValueError, match="already installed"):
        store.install(_STEWARD)


def test_vacate_clears_the_holder_and_stamps_vacated_at():
    store = RoleStore()
    store.install(_STEWARD)
    updated = store.vacate("steward_of_whiterun", gamets=10.0)
    assert updated.holder_id is None
    assert updated.vacated_at == 10.0
    assert store.holder_of("steward_of_whiterun") is None
    # The stored copy reflects the mutation too -- vacate() isn't a
    # pure function on a detached copy.
    assert store.role("steward_of_whiterun").holder_id is None


def test_roles_held_by_finds_every_role_one_npc_holds():
    store = RoleStore()
    store.install(_STEWARD)
    store.install(
        Role(id="court_wizard", title="Court Wizard", institution_id="whiterun_court",
             duties=(), holder_id="proventus", vacated_at=None)
    )
    store.install(
        Role(id="housecarl", title="Housecarl", institution_id="whiterun_court",
             duties=(), holder_id="irileth", vacated_at=None)
    )
    assert {role.id for role in store.roles_held_by("proventus")} == {"steward_of_whiterun", "court_wizard"}
    assert [role.id for role in store.roles_held_by("irileth")] == ["housecarl"]
    assert store.roles_held_by("nobody") == ()


def test_roles_held_by_excludes_a_role_after_it_is_vacated():
    store = RoleStore()
    store.install(_STEWARD)
    store.vacate("steward_of_whiterun", gamets=5.0)
    assert store.roles_held_by("proventus") == ()


def test_a_vacant_role_can_be_installed_directly():
    store = RoleStore()
    store.install(
        Role(id="jarl_of_whiterun", title="Jarl of Whiterun", institution_id="whiterun_court",
             duties=(), holder_id=None, vacated_at=None)
    )
    assert store.holder_of("jarl_of_whiterun") is None
    assert store.roles_held_by("anyone") == ()
