"""chronicle/rules.py + driver wiring: the Tier-3 rule registry core (lane 19, L-A).

Covers the packet's contract: every evaluation of an enabled rule emits a
rule_evaluated record with the schema §4:122 fields (fired or not); a
disabled rule emits nothing and doesn't run; all 19 §8 names are
registered (1-10 enabled, 11-19 disabled stubs); and a real scenario-style
run shows rule_evaluated rows in its trace with zero edits to the existing
suite (the unedited battery itself is the migration regression proof).
"""

from __future__ import annotations

import pytest

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied
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


def test_registry_lists_all_nineteen_ladder_rules_with_stubs_disabled():
    registry = RuleRegistry()
    names = registry.names()
    assert len(names) == 19  # §8's table, all names present (O4: the registry lists 19; the budget counts 17)
    enabled = {name for name in names if registry.enabled(name)}
    assert len(enabled) == 16  # rules 1-10 plus 15 (lane 23), 11 (lane 24), 14 (lane 25), 16 (lane 26), 17 (lane 36), 18 (lane 43)
    # Unlanded rules are disabled stubs (R12); rules 15, 11, 14, 16, 17,
    # and 18 were the first stubs replaced by live rules
    # (lanes 23/24/25/26/36/43), so the stub assertions now use rule 12
    # (grudge-creation).
    assert TELL_DECISION_POLICY in names
    assert registry.enabled(TELL_DECISION_POLICY)
    assert registry.enabled(ACCUMULATION_THRESHOLD)
    assert not registry.enabled(GRUDGE_CREATION)
    with pytest.raises(NotImplementedError, match="registered stub"):
        registry.get(GRUDGE_CREATION).evaluate(RuleContext(tick=0, gamets=0.0, inputs={}))


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
