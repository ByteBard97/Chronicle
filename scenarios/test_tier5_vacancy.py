"""Scenario-ladder rung T5.1 (Vacancy) -- the role model, objective vacancy, duty lapse.

A steward is killed (docs/scenario-ladder.md, Tier 5). The lane-44/47
pins in force (docs/design/tier-5-roles-and-vacancy.md decisions
S1-S4, docs/work-packets/lane-47-role-model-vacancy.md):

  - Vacancy is objective (S3): detected at inject_event's NPCDied
    branch, the instant the holder dies -- not gated on anyone's
    belief. `holder_of()` is the one place to ask who currently holds
    a role; nothing mirrors it elsewhere (O1's ruled design rule).
  - Duty lapse reuses status_changed (S4): one event per duty, anchored
    on the former holder (a dead NPC can still be a canonical anchor,
    same precedent as escalation_warning/schedule_rewrite). No
    auto-witness -- propagation is ordinary, scripted like any other
    canonical event.
  - Rule 19 was a stub as of this lane's original writing; lane 48
    landed it (succession) afterward -- vacancy now evaluates it on
    every vacancy (fired:false here, no court relationships seeded in
    this fixture) rather than producing no row at all.
  - Vacancy replays from the event log alone, not a keyframe
    dependency -- a driver resumed over a pre-populated event_log with
    the role reinstalled fresh already shows the vacancy at __init__.
"""

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied, StatusChanged
from chronicle.framelog import FrameLogReader
from chronicle.roles import Duty, Role, RoleStore
from chronicle.rules import ROLE_VACANCY_SUCCESSION
from chronicle.schedule import ScheduleBlock

_SEED = "tier5-vacancy"
_SAVE = "whiterun-save-1"
_TICKS = 10

_STEWARD_ROLE = "steward_of_whiterun"
_PROVENTUS = "proventus"  # the steward, dies
_IRILETH = "irileth"  # witnesses the death and the lapse
_CARLOTTA = "carlotta"  # hears the lapse claim via an ordinary encounter

_COLLECT_TAXES = Duty(name="collect_taxes", lapse_status_kind="duty_lapsed")
_MANAGE_HOUSEHOLD = Duty(name="manage_household", lapse_status_kind="duty_lapsed")

_SCHEDULE = (
    ScheduleBlock(npc_id=_IRILETH, location_id="dragonsreach", start_tick=0, end_tick=_TICKS),
    ScheduleBlock(npc_id=_CARLOTTA, location_id="dragonsreach", start_tick=0, end_tick=_TICKS),
)


def _steward_role(*, holder_id: str | None = _PROVENTUS) -> Role:
    return Role(
        id=_STEWARD_ROLE, title="Steward of Whiterun", institution_id="whiterun_court",
        duties=(_COLLECT_TAXES, _MANAGE_HOUSEHOLD), holder_id=holder_id, vacated_at=None,
    )


def _driver(run_id: str, *, roles: RoleStore | None = None, event_log=None) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=_SCHEDULE,
        encounter_probability=1.0,
        roles=roles,
        event_log=event_log,
    )


def _records(driver: Driver, stream: str) -> list[dict]:
    try:
        driver.writer.flush()
    except ValueError:  # flush of closed file -- close() already flushed
        pass
    reader = FrameLogReader(driver.writer.run_dir)
    return [record["payload"] for record in reader.records(stream)]


def test_t5_1_death_vacates_the_role_and_lapses_every_duty():
    driver = _driver("tier5-vacancy")
    driver.roles.install(_steward_role())
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id=_PROVENTUS,
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_tier5_vacancy"},
    )

    # Vacancy is immediate -- no tick loop, no belief, needed.
    assert driver.roles.holder_of(_STEWARD_ROLE) is None
    role = driver.roles.role(_STEWARD_ROLE)
    assert role is not None
    assert role.vacated_at == 0.0
    assert driver.roles.roles_held_by(_PROVENTUS) == ()

    # One status_changed lapse event per duty, anchored on the dead
    # holder, no rule_evaluated row at all (rule 19 stays a stub).
    lapse_events = [e for e in driver.event_log.lineage(_SAVE, 0) if isinstance(e, StatusChanged)]
    assert len(lapse_events) == 2
    assert {e.detail for e in lapse_events} == {"collect_taxes", "manage_household"}
    for e in lapse_events:
        assert e.npc_id == _PROVENTUS
        assert e.status_kind == "duty_lapsed"
        assert e.location_id is None

    driver.close()
    events = _records(driver, "events")
    lapse_payloads = [p for p in events if p.get("event_type") == "status_changed"]
    assert len(lapse_payloads) == 2
    for payload in lapse_payloads:
        assert payload["npc_id"] == _PROVENTUS
        assert payload["status_kind"] == "duty_lapsed"

    # Lane 48 (rule 19 real): succession now evaluates on every vacancy --
    # this fixture seeds no court relationships, so it fires false, not
    # absent. Mechanical update to this pre-existing assertion, flagged
    # in lane 48's delivery report (this file is otherwise lane 47's).
    trace = _records(driver, "trace")
    succession_rows = [p for p in trace if p.get("record_type") == "rule_evaluated" and p["rule"] == ROLE_VACANCY_SUCCESSION]
    assert len(succession_rows) == 1
    assert succession_rows[0]["fired"] is False
    assert succession_rows[0]["inputs"]["has_candidate"] is False


def test_t5_1_the_lapse_propagates_through_ordinary_encounter_machinery():
    driver = _driver("tier5-vacancy-propagates")
    driver.roles.install(_steward_role())
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id=_PROVENTUS,
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_tier5_vacancy"},
    )
    tax_lapse = next(
        e for e in driver.event_log.lineage(_SAVE, 0)
        if isinstance(e, StatusChanged) and e.detail == "collect_taxes"
    )
    # No auto-witness (S4): the scenario scripts irileth noticing, the
    # same caller-scripted witness() call any canonical event gets.
    driver.witness(
        claim_id="claim-tax-collection-lapsed",
        belief_id="belief-irileth-tax-lapse",
        evidence_id="evidence-irileth-tax-lapse",
        kind="duty_lapsed",
        slots={"duty": "collect_taxes", "role": _STEWARD_ROLE},
        canonical_event_key=EventKey(tax_lapse.save_uuid, tax_lapse.generation, tax_lapse.seq),
        witness_id=_IRILETH,
        gamets=0.0,
    )
    driver.run(0, _TICKS)
    driver.close()

    trace = _records(driver, "trace")
    transmitted = [
        p for p in trace
        if p.get("record_type") == "transmitted" and p["claim_id"] == "claim-tax-collection-lapsed"
    ]
    assert transmitted
    assert transmitted[0]["hearer_id"] == _CARLOTTA
    assert driver.belief_of(_CARLOTTA, "claim-tax-collection-lapsed") is not None


def test_t5_1_vacancy_replays_from_a_pre_populated_event_log_not_a_keyframe():
    """The T3 acceptance line: no keyframe/state_at dependency -- a driver
    resumed over the same event_log, with the role reinstalled fresh at
    its pre-death state, shows the vacancy immediately at __init__ (the
    same start-from-keyframe-safe pattern _deceased/_schedule_overlays
    already prove)."""
    original = _driver("tier5-vacancy-original")
    original.roles.install(_steward_role())
    original.inject_event(
        NPCDied(
            tick=5, save_uuid=_SAVE, generation=0, seq=1,
            gamets=5.0, wall_ts=0.0, npc_id=_PROVENTUS,
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
    )
    original.close()
    lapses_before_resume = [e for e in original.event_log.lineage(_SAVE, 0) if isinstance(e, StatusChanged)]
    assert len(lapses_before_resume) == 2  # the original run's own cascade

    resumed_roles = RoleStore()
    resumed_roles.install(_steward_role())  # freshly installed, still HELD -- pre-death state
    resumed = _driver("tier5-vacancy-resumed", roles=resumed_roles, event_log=original.event_log)

    assert resumed.roles.holder_of(_STEWARD_ROLE) is None
    assert resumed.roles.role(_STEWARD_ROLE).vacated_at == 5.0
    # No re-cascade: __init__'s bootstrap only derives Role state (S3),
    # it never re-injects lapse events -- the event_log (shared with
    # `original`) still carries exactly the two from the original run.
    resumed_lapses = [e for e in resumed.event_log.lineage(_SAVE, 0) if isinstance(e, StatusChanged)]
    assert resumed_lapses == lapses_before_resume
    resumed.close()


def test_no_installed_role_means_no_vacancy_behavior():
    """The pin's regression half: a death with no role installed changes nothing new."""
    driver = _driver("tier5-vacancy-unmapped")
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id=_PROVENTUS,
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
    )
    driver.run(0, _TICKS)
    driver.close()

    events = _records(driver, "events")
    assert not [p for p in events if p.get("event_type") == "status_changed"]
    assert driver.roles.roles_held_by(_PROVENTUS) == ()
