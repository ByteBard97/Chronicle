"""chronicle/rules.py + driver wiring: the Tier-3 rule registry core (lane 19, L-A).

Covers the packet's contract: every evaluation of an enabled rule emits a
rule_evaluated record with the schema §4:122 fields (fired or not); a
disabled rule emits nothing and doesn't run; all 20 §8 names are
registered (1-10 enabled, 11-19 disabled stubs); and a real scenario-style
run shows rule_evaluated rows in its trace with zero edits to the existing
suite (the unedited battery itself is the migration regression proof).
"""

from __future__ import annotations

import pytest

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied
from chronicle.framelog import FrameLogReader
from chronicle.rules import (
    ACCUMULATION_THRESHOLD,
    DORMANCY_REACTIVATION,
    ENCOUNTER_SAMPLING,
    GRUDGE_CREATION,
    MUTATION_POLICY,
    TELL_DECISION_POLICY,
    WITNESS_CREATES_BELIEF,
    RuleContext,
    RuleRegistry,
)
from chronicle.schedule import ScheduleBlock

_SEED = "rules-core-seed"
_SAVE = "save-1"
_CAST = ("irileth", "proventus", "hulda")
_TICKS = 60

# The schema §4:122 rule_evaluated row, field-for-field.
_RULE_EVALUATED_FIELDS = {"record_type", "rule", "inputs", "fired", "result"}

_MUTATION_CANDIDATES = {
    ("npc_death", "perpetrator"): ("the Thalmor", "a bandit chief"),
    ("npc_death", "cause"): ("an accident",),
    ("npc_death", "location"): ("the market",),
}


def _driver(run_id: str, tmp_path, **kwargs: object) -> Driver:
    return Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE,
        generation=0,
        schedule=tuple(
            ScheduleBlock(npc_id=npc, location_id="bannered_mare", start_tick=0, end_tick=_TICKS)
            for npc in _CAST
        ),
        runs_dir=tmp_path,
        **kwargs,  # type: ignore[arg-type]
    )


def _witness_death(driver: Driver) -> None:
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        ),
        origin={"kind": "scenario", "detail": "test_rules"},
    )
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
        canonical_event_key=EventKey(_SAVE, 0, 1),
        witness_id="irileth",
        gamets=0.0,
    )


def _rule_rows(tmp_path, run_id: str) -> list[dict]:
    reader = FrameLogReader(tmp_path / run_id)
    return [r["payload"] for r in reader.records("trace") if r["payload"].get("record_type") == "rule_evaluated"]


def test_registry_lists_all_twenty_ladder_rules_with_no_stubs_remaining():
    registry = RuleRegistry()
    names = registry.names()
    assert len(names) == 20  # §8's table, all names present (O4: the registry lists 20; the budget counts 18)
    enabled = {name for name in names if registry.enabled(name)}
    # No stubs remain (rule 12, grudge-creation, was the last one): every
    # registered rule is enabled by default.
    assert len(enabled) == 20
    assert TELL_DECISION_POLICY in names
    assert registry.enabled(TELL_DECISION_POLICY)
    assert registry.enabled(ACCUMULATION_THRESHOLD)
    assert registry.enabled(GRUDGE_CREATION)


def test_grudge_creation_rule_fires_once_then_latches(tmp_path):
    """Rule 12: fires (creates a grudge) the first time, then non-fires (already_exists) for a repeat trigger on the same pair."""
    driver = _driver("rules-grudge-creation-run", tmp_path, encounter_probability=0.0)
    grudge = driver.suffer_harm(
        holder_id="irileth",
        target_id="proventus",
        grievance_type="humiliation",
        source_belief_id="belief-humiliation-irileth",
        evidentiary_strength=0.6,
        gamets=1.0,
    )
    assert grudge is not None
    assert grudge.holder_id == "irileth" and grudge.target_id == "proventus"
    assert grudge.emotional_strength == 1.0  # O3 self-victim bypass: no edge, total self-regard
    assert grudge.emotional_strength > grudge.evidentiary_strength  # T3.2's assertion shape

    repeat = driver.suffer_harm(
        holder_id="irileth",
        target_id="proventus",
        grievance_type="humiliation",
        source_belief_id="belief-humiliation-irileth-2",
        evidentiary_strength=0.9,
        gamets=2.0,
    )
    assert repeat is grudge  # latched: the existing grudge, unchanged, no second grudge minted
    driver.close()

    rows = _rule_rows(tmp_path, "rules-grudge-creation-run")
    grudge_rows = [r for r in rows if r["rule"] == GRUDGE_CREATION]
    assert len(grudge_rows) == 2
    assert grudge_rows[0]["fired"] and grudge_rows[0]["inputs"]["already_exists"] is False
    assert not grudge_rows[1]["fired"] and grudge_rows[1]["inputs"]["already_exists"] is True


def test_crime_witnessed_bystander_forms_belief_without_grudge(tmp_path):
    """docs/design/chronicle-bridge-crime-witness-out.md §1/§6, bystander row: victim_id
    differs from (or is None vs.) witness_id -- belief via witness(), no grudge."""
    driver = _driver("rules-crime-witnessed-bystander-run", tmp_path, encounter_probability=0.0)
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id="irileth",
            perpetrator_id="proventus", crime_type="assault",
            victim_id="hulda", location_id="bannered_mare",
        ),
        origin={"kind": "scenario", "detail": "test_rules"},
    )
    claim, belief, _evidence, grudge = driver.crime_witnessed(
        claim_id="claim-assault-1",
        belief_id="belief-irileth-assault",
        evidence_id="evidence-irileth-assault",
        witness_id="irileth",
        perpetrator_id="proventus",
        crime_type="assault",
        victim_id="hulda",
        canonical_event_key=EventKey(_SAVE, 0, 1),
        location_id="bannered_mare",
        gamets=0.0,
    )
    assert grudge is None
    assert belief.holder_id == "irileth"
    assert claim.kind == "assault"
    assert driver.social.grudge("irileth", "proventus") is None
    driver.close()


def test_crime_witnessed_self_victim_forms_belief_and_grudge(tmp_path):
    """docs/design/chronicle-bridge-crime-witness-out.md §1/§6, self-victim row: victim_id
    == witness_id -- belief via witness() AND a grudge via suffer_harm()/rule 12."""
    driver = _driver("rules-crime-witnessed-self-victim-run", tmp_path, encounter_probability=0.0)
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid=_SAVE, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, witness_id="irileth",
            perpetrator_id="proventus", crime_type="assault",
            victim_id="irileth", location_id="bannered_mare",
        ),
        origin={"kind": "scenario", "detail": "test_rules"},
    )
    _claim, belief, _evidence, grudge = driver.crime_witnessed(
        claim_id="claim-assault-2",
        belief_id="belief-irileth-assault-2",
        evidence_id="evidence-irileth-assault-2",
        witness_id="irileth",
        perpetrator_id="proventus",
        crime_type="assault",
        victim_id="irileth",
        canonical_event_key=EventKey(_SAVE, 0, 1),
        location_id="bannered_mare",
        gamets=0.0,
    )
    assert grudge is not None
    assert grudge.holder_id == "irileth" and grudge.target_id == "proventus"
    assert grudge.source_belief_id == belief.id
    assert driver.social.grudge("irileth", "proventus") is grudge
    driver.close()


def test_disabling_grudge_creation_suppresses_it(tmp_path):
    driver = _driver("rules-grudge-creation-disabled-run", tmp_path, encounter_probability=0.0, disabled_rules={GRUDGE_CREATION})
    grudge = driver.suffer_harm(
        holder_id="irileth",
        target_id="proventus",
        grievance_type="humiliation",
        source_belief_id="belief-humiliation-irileth",
        evidentiary_strength=0.6,
        gamets=1.0,
    )
    assert grudge is None
    driver.close()
    rows = _rule_rows(tmp_path, "rules-grudge-creation-disabled-run")
    assert not [r for r in rows if r["rule"] == GRUDGE_CREATION]


def test_unknown_disabled_rule_name_raises():
    with pytest.raises(ValueError, match="unregistered rules"):
        RuleRegistry(disabled=("not-a-rule",))


def test_every_evaluation_emits_rule_evaluated_fired_or_not(tmp_path):
    """A scenario-style run: rule_evaluated rows carry the schema fields exactly, both fired values present."""
    driver = _driver("rules-core-run", tmp_path, encounter_probability=0.35, mutation_candidates=_MUTATION_CANDIDATES)
    _witness_death(driver)
    driver.run(0, _TICKS)
    driver.close()

    rows = _rule_rows(tmp_path, "rules-core-run")
    assert rows, "an enabled-rule run must emit rule_evaluated rows"
    for row in rows:
        assert set(row) == _RULE_EVALUATED_FIELDS
        assert isinstance(row["inputs"], dict)
        assert isinstance(row["fired"], bool)
    # The contract's two halves, both visible in one run: evaluations that
    # fired and evaluations that didn't (rolled-against encounters /
    # declined mutation gates), neither silent.
    assert any(row["fired"] for row in rows)
    assert any(not row["fired"] for row in rows)
    # The witness wrapper emitted rules 1 and 4 at tick 0.
    assert any(row["rule"] == WITNESS_CREATES_BELIEF for row in rows)


def test_a_disabled_rule_emits_nothing_and_does_not_run(tmp_path):
    """Mutation policy toggled off at construction: no mutation decisions, no rows, no mutations."""
    driver = _driver(
        "rules-disabled-run", tmp_path,
        encounter_probability=1.0, mutation_candidates=_MUTATION_CANDIDATES,
        disabled_rules={MUTATION_POLICY},
    )
    _witness_death(driver)
    driver.run(0, _TICKS)
    driver.close()

    reader = FrameLogReader(tmp_path / "rules-disabled-run")
    trace = [r["payload"] for r in reader.records("trace")]
    assert not [p for p in trace if p.get("record_type") == "mutation_applied"]
    assert not [p for p in trace if p.get("record_type") == "rule_evaluated" and p.get("rule") == MUTATION_POLICY]
    # Other rules still evaluate: the run is instrumented, just not this rule.
    assert [p for p in trace if p.get("record_type") == "rule_evaluated"]


def test_disabling_encounter_sampling_stops_the_sweep(tmp_path):
    """Rule 6 toggled off: the sampler doesn't run -- no rolls, no encounter rows, no propagation."""
    driver = _driver("rules-no-encounters-run", tmp_path, encounter_probability=1.0, disabled_rules={ENCOUNTER_SAMPLING})
    _witness_death(driver)
    driver.run(0, _TICKS)
    driver.close()

    reader = FrameLogReader(tmp_path / "rules-no-encounters-run")
    trace = [r["payload"] for r in reader.records("trace")]
    assert not [p for p in trace if p.get("record_type") == "encounter_rolled"]
    assert not [p for p in trace if p.get("record_type") == "transmitted"]
    assert not [p for p in trace if p.get("record_type") == "rule_evaluated" and p.get("rule") == ENCOUNTER_SAMPLING]


def test_read_path_rules_compute_for_offlog_consumers_without_emitting(tmp_path):
    """Rules 2/9/10 wrap the pure derivations (decay/stage_at); the run loop never evaluates them."""
    driver = _driver("rules-read-path-run", tmp_path, encounter_probability=1.0)
    _witness_death(driver)
    driver.run(0, _TICKS)
    driver.close()

    belief = driver.claims.belief_of("irileth", "claim-jarl-death")
    assert belief is not None
    rumor = driver.claims.rumor_state("irileth", "claim-jarl-death", belief.variant_id)
    assert rumor is not None
    registry = driver.rules
    ctx = RuleContext(tick=_TICKS, gamets=float(_TICKS), inputs={"belief": belief, "rumor": rumor, "at_gamets": float(_TICKS)})
    decay_result = registry.get("belief-decay").evaluate(ctx)
    assert decay_result.fired and decay_result.result["confidence"] < belief.confidence  # type: ignore[index]
    stage_result = registry.get("rumor-stage-transitions").evaluate(ctx)
    # irileth witnessed at tick 0 and may have retold during the run --
    # either live stage, never dormant at 60 ticks.
    assert stage_result.result["stage"] in ("heard", "repeated")  # type: ignore[index]
    dormancy = registry.get(DORMANCY_REACTIVATION).evaluate(ctx)
    assert not dormancy.fired  # 60 ticks in, the rumor is nowhere near dormant
    # ...and none of that touched the log.
    assert not [r for r in _rule_rows(tmp_path, "rules-read-path-run") if r["rule"] in {"belief-decay", "rumor-stage-transitions", DORMANCY_REACTIVATION}]
