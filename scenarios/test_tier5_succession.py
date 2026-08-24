"""Scenario-ladder rung T5.2 (Succession) + T5.3 (No orphaned references) -- rule 19.

The successor resolves from relationship/faction state; varying the
prior-relationship fixture while holding the seed produces a different
successor (docs/scenario-ladder.md, Tier 5). The lane-44/48 pins in
force (docs/design/tier-5-roles-and-vacancy.md decisions S5/S6,
docs/work-packets/lane-48-succession.md):

  - Deterministic ranking (S5): candidates are NPCs holding a
    relationship edge whose basis_id matches the vacant role's
    institution_id, ranked by strength descending, ties broken by
    lower npc_id lexicographically. No roll, no new RNG purpose.
  - Zero qualifying candidates -> stays vacant (a real outcome, not an
    error).
  - The counterfactual is fixture-carried, not seed-carried (S5): same
    seed_id, one relationship strength swapped, a different successor
    -- exactly, not probabilistically.
  - T5.3 holds by construction (S2/O1's ruled narrow reading):
    `roles.holder_of()` is the only place to ask who holds a role;
    layer-4 records (relationships/grudges/obligations) are unchanged
    and still name NPCs directly.
"""

from chronicle.driver import Driver
from chronicle.events import NPCDied, StatusChanged
from chronicle.framelog import FrameLogReader
from chronicle.roles import Duty, Role
from chronicle.rules import ROLE_VACANCY_SUCCESSION
from chronicle.schedule import ScheduleBlock

_SEED = "tier5-succession"
_SAVE = "whiterun-save-1"
_TICKS = 5

_STEWARD_ROLE = "steward_of_whiterun"
_INSTITUTION = "whiterun_court"
_STEWARD = "erik_the_steward"
_CANDIDATE_STRONG = "irileth"
_CANDIDATE_WEAK = "proventus"

_SCHEDULE = (ScheduleBlock(npc_id=_CANDIDATE_STRONG, location_id="dragonsreach", start_tick=0, end_tick=_TICKS),)


def _steward_role() -> Role:
    return Role(
        id=_STEWARD_ROLE, title="Steward of Whiterun", institution_id=_INSTITUTION,
        duties=(Duty(name="collect_taxes", lapse_status_kind="duty_lapsed"),), holder_id=_STEWARD, vacated_at=None,
    )


def _driver(run_id: str) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=_SCHEDULE,
        encounter_probability=1.0,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    try:
        driver.writer.flush()
    except ValueError:  # flush of closed file -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def _kill_the_steward(driver: Driver) -> None:
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id=_STEWARD,
            cause="illness", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_tier5_succession"},
    )


def test_t5_2_the_higher_strength_candidate_succeeds():
    driver = _driver("tier5-succession")
    driver.roles.install(_steward_role())
    driver.form_relationship(
        id="rel-irileth-court", from_id=_CANDIDATE_STRONG, to_id=_STEWARD,
        basis="shared_employer", basis_id=_INSTITUTION, strength=0.95, gamets=0.0,
    )
    driver.form_relationship(
        id="rel-proventus-court", from_id=_CANDIDATE_WEAK, to_id=_STEWARD,
        basis="shared_employer", basis_id=_INSTITUTION, strength=0.85, gamets=0.0,
    )
    _kill_the_steward(driver)

    assert driver.roles.holder_of(_STEWARD_ROLE) == _CANDIDATE_STRONG
    role = driver.roles.role(_STEWARD_ROLE)
    assert role.vacated_at is None  # succeeded, not left vacant

    # The role_appointed status_changed event, field-for-field.
    appointed = [e for e in driver.event_log.lineage(_SAVE, 0) if isinstance(e, StatusChanged) and e.status_kind == "role_appointed"]
    assert len(appointed) == 1
    assert appointed[0].npc_id == _CANDIDATE_STRONG
    assert appointed[0].detail == _STEWARD_ROLE

    driver.close()
    trace = _records(driver, "trace")
    rows = [p for p in trace if p.get("record_type") == "rule_evaluated" and p["rule"] == ROLE_VACANCY_SUCCESSION]
    assert len(rows) == 1
    assert rows[0]["fired"] is True
    assert rows[0]["inputs"]["successor_id"] == _CANDIDATE_STRONG
    assert rows[0]["inputs"]["candidate_count"] == 2


def test_t5_2_the_counterfactual_is_fixture_carried_not_seed_carried():
    """Same seed_id both times; only which fixture edge has the higher
    strength changes -- exactly the stronger determinism claim T5.2 asks for."""
    a = _driver("tier5-succession-a")
    a.roles.install(_steward_role())
    a.form_relationship(id="rel-irileth", from_id=_CANDIDATE_STRONG, to_id=_STEWARD, basis="shared_employer", basis_id=_INSTITUTION, strength=0.95, gamets=0.0)
    a.form_relationship(id="rel-proventus", from_id=_CANDIDATE_WEAK, to_id=_STEWARD, basis="shared_employer", basis_id=_INSTITUTION, strength=0.85, gamets=0.0)
    _kill_the_steward(a)
    a.close()

    b = _driver("tier5-succession-b")
    b.roles.install(_steward_role())
    # The one line swapped: proventus now outranks irileth.
    b.form_relationship(id="rel-irileth", from_id=_CANDIDATE_STRONG, to_id=_STEWARD, basis="shared_employer", basis_id=_INSTITUTION, strength=0.60, gamets=0.0)
    b.form_relationship(id="rel-proventus", from_id=_CANDIDATE_WEAK, to_id=_STEWARD, basis="shared_employer", basis_id=_INSTITUTION, strength=0.97, gamets=0.0)
    _kill_the_steward(b)
    b.close()

    assert a.roles.holder_of(_STEWARD_ROLE) == _CANDIDATE_STRONG
    assert b.roles.holder_of(_STEWARD_ROLE) == _CANDIDATE_WEAK


def test_t5_2_a_tie_breaks_lexicographically_by_lower_npc_id():
    driver = _driver("tier5-succession-tie")
    driver.roles.install(_steward_role())
    driver.form_relationship(id="rel-beatrice", from_id="beatrice", to_id=_STEWARD, basis="faction", basis_id=_INSTITUTION, strength=0.7, gamets=0.0)
    driver.form_relationship(id="rel-aldric", from_id="aldric", to_id=_STEWARD, basis="faction", basis_id=_INSTITUTION, strength=0.7, gamets=0.0)
    _kill_the_steward(driver)
    assert driver.roles.holder_of(_STEWARD_ROLE) == "aldric"  # "aldric" < "beatrice"


def test_t5_2_zero_qualifying_candidates_leaves_the_role_vacant():
    driver = _driver("tier5-succession-vacant")
    driver.roles.install(_steward_role())
    _kill_the_steward(driver)

    assert driver.roles.holder_of(_STEWARD_ROLE) is None
    role = driver.roles.role(_STEWARD_ROLE)
    assert role.vacated_at == 0.0  # stayed vacant, not silently re-held

    driver.close()
    trace = _records(driver, "trace")
    rows = [p for p in trace if p.get("record_type") == "rule_evaluated" and p["rule"] == ROLE_VACANCY_SUCCESSION]
    assert len(rows) == 1
    assert rows[0]["fired"] is False
    assert rows[0]["inputs"]["candidate_count"] == 0
    assert rows[0]["inputs"]["successor_id"] is None


def test_t5_3_holder_of_is_the_only_reference_and_layer_four_records_are_unchanged():
    """No orphaned references, by construction (S2/O1's ruled narrow
    reading): nothing but Role.holder_id (via holder_of()) says who
    holds the role, and the pre-existing relationship edges naming the
    old and new holder directly are untouched by succession."""
    driver = _driver("tier5-succession-t53")
    driver.roles.install(_steward_role())
    irileth_edge = driver.form_relationship(
        id="rel-irileth-court", from_id=_CANDIDATE_STRONG, to_id=_STEWARD,
        basis="shared_employer", basis_id=_INSTITUTION, strength=0.95, gamets=0.0,
    )
    _kill_the_steward(driver)

    assert driver.roles.holder_of(_STEWARD_ROLE) == _CANDIDATE_STRONG
    # The relationship edge that made irileth a candidate is untouched --
    # succession doesn't rewrite layer-4 records, it only mutates the
    # Role itself.
    assert driver.social.relationship(_CANDIDATE_STRONG, _STEWARD, "shared_employer") == irileth_edge
    # The dead former holder's own name still appears in that edge's
    # to_id -- succession doesn't retroactively scrub or re-point it.
    assert driver.social.relationship(_CANDIDATE_STRONG, _STEWARD, "shared_employer").to_id == _STEWARD
