"""chronicle/driver.py: the Tier-2 mutation policy (ladder T2.2).

Covers the encounter-driven mutation machinery: determinism under a pinned
seed, the no-mutation paths (probability 0, no candidates registered), the
mutation_applied payload's shape against frame-log schema §4 field-for-field,
record ordering (mutation_applied before transmitted), and replay-exactness
(reader state_at(T) matching the in-memory run on a log containing
mutations -- the proof that readers replay the effect via transmitted and
need no mutation_applied handling of their own).
"""

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.framelog import FrameLogReader, serialize_state
from chronicle.schedule import ScheduleBlock

_SEED = "driver-mutation-test-seed"

_CANDIDATES = {
    ("npc_death", "perpetrator"): ("the Thalmor", "a bandit", "the guard captain"),
    ("npc_death", "cause"): ("an accident", "illness"),
    ("npc_death", "location"): ("the market", "dragonsreach"),
}


def _three_npc_schedule(end_tick: int = 40) -> tuple[ScheduleBlock, ...]:
    return (
        ScheduleBlock(npc_id="irileth", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id="proventus", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
    )


def _run_driver(
    runs_dir,
    run_id: str,
    *,
    mutation_probability: float = 1.0,
    mutation_candidates=None,
    ticks: int = 40,
    keyframe_interval: int = 24,
) -> Driver:
    driver = Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=_three_npc_schedule(end_tick=ticks),
        encounter_probability=1.0,
        mutation_probability=mutation_probability,
        mutation_candidates=mutation_candidates,
        keyframe_interval=keyframe_interval,
        runs_dir=runs_dir,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        ),
        origin={"kind": "scenario", "detail": "test_driver_mutation"},
    )
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
        canonical_event_key=EventKey("save-1", 0, 1),
        witness_id="irileth",
        gamets=0.0,
    )
    driver.run(0, ticks)
    driver.close()
    return driver


def _trace(runs_dir, run_id: str) -> list[dict]:
    return [r["payload"] for r in FrameLogReader(runs_dir / run_id).records("trace")]


def test_mutations_fire_and_the_log_is_byte_for_byte_reproducible(tmp_path):
    _run_driver(tmp_path, "run-mut-a", mutation_candidates=_CANDIDATES)
    _run_driver(tmp_path, "run-mut-b", mutation_candidates=_CANDIDATES)
    for stream in ("events.jsonl", "trace.jsonl"):
        assert (tmp_path / "run-mut-a" / stream).read_bytes() == (tmp_path / "run-mut-b" / stream).read_bytes()
    mutations = [p for p in _trace(tmp_path, "run-mut-a") if p["record_type"] == "mutation_applied"]
    assert mutations  # probability 1.0 with full candidate coverage: every retelling mutates


def test_probability_zero_never_mutates(tmp_path):
    _run_driver(tmp_path, "run-mut-zero", mutation_probability=0.0, mutation_candidates=_CANDIDATES)
    trace = _trace(tmp_path, "run-mut-zero")
    assert [p for p in trace if p["record_type"] == "mutation_applied"] == []
    transmitted = [p for p in trace if p["record_type"] == "transmitted"]
    assert transmitted  # the story still spread -- it just never mutated
    assert all(p["variant"]["mutated_slot"] is None for p in transmitted)


def test_no_candidates_registered_means_no_mutation(tmp_path):
    _run_driver(tmp_path, "run-mut-none", mutation_probability=1.0)
    trace = _trace(tmp_path, "run-mut-none")
    assert [p for p in trace if p["record_type"] == "mutation_applied"] == []
    transmitted = [p for p in trace if p["record_type"] == "transmitted"]
    assert transmitted
    assert all(p["variant"]["mutated_slot"] is None for p in transmitted)


def test_candidates_covering_only_some_slots_mutate_only_those_slots(tmp_path):
    # Only "cause" has a registered domain: a gate-passing roll that picks
    # "perpetrator" or "location" declines silently (no record without a
    # mutation, schema §4). The slot picks are seed-pinned, so under _SEED
    # this run both fires mutations and declines some.
    driver = Driver(
        run_id="run-mut-partial",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=tuple(
            ScheduleBlock(npc_id=n, location_id="bannered_mare", start_tick=0, end_tick=40)
            for n in ("irileth", "proventus", "hulda", "ysolda", "belethor", "nazeem")
        ),
        encounter_probability=1.0,
        mutation_probability=1.0,
        mutation_candidates={("npc_death", "cause"): ("an accident", "illness")},
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        )
    )
    driver.witness(
        claim_id="claim-jarl-death", belief_id="belief-irileth-death", evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
        canonical_event_key=EventKey("save-1", 0, 1), witness_id="irileth", gamets=0.0,
    )
    driver.run(0, 40)
    driver.close()
    trace = _trace(tmp_path, "run-mut-partial")
    mutations = [p for p in trace if p["record_type"] == "mutation_applied"]
    assert mutations
    assert all(p["slot"] == "cause" for p in mutations)
    # Declined mutations leave no trace record, but the retelling itself
    # still happened (unmutated) -- transmitted rows outnumber mutations.
    transmitted = [p for p in trace if p["record_type"] == "transmitted"]
    assert len(transmitted) > len(mutations)


def test_mutation_applied_payload_matches_schema_section_4_field_for_field(tmp_path):
    _run_driver(tmp_path, "run-mut-schema", mutation_probability=1.0, mutation_candidates=_CANDIDATES)
    trace = _trace(tmp_path, "run-mut-schema")
    mutations = [p for p in trace if p["record_type"] == "mutation_applied"]
    assert mutations
    for p in mutations:
        # Exactly the schema §4 field list, plus the value/threshold/outcome
        # the §4 preamble mandates for roll-bearing records.
        assert set(p) == {
            "record_type", "claim_id", "parent_variant_id", "variant_id",
            "slot", "old_value", "new_value", "mutation_id",
            "roll_key", "value", "threshold", "outcome",
        }
        assert set(p["roll_key"]) == {"seed_id", "purpose", "tick", "site", "participants", "draw"}
        assert p["roll_key"]["seed_id"] == _SEED
        assert p["roll_key"]["purpose"] == "mutation.slot"
        assert p["roll_key"]["site"] == p["claim_id"] == "claim-jarl-death"
        assert 0.0 <= p["value"] < p["threshold"] == 1.0  # the gate this roll passed
        assert p["outcome"] == "mutated"
        assert p["slot"] in ("perpetrator", "cause", "location")
        assert p["new_value"] in _CANDIDATES[("npc_death", p["slot"])]
        assert p["new_value"] != p["old_value"]
        assert p["mutation_id"].startswith("mut-")  # seeded id, never a uuid


def test_mutation_applied_precedes_the_transmitted_record_it_evidences(tmp_path):
    _run_driver(tmp_path, "run-mut-order", mutation_probability=1.0, mutation_candidates=_CANDIDATES)
    trace = _trace(tmp_path, "run-mut-order")
    for i, p in enumerate(trace):
        if p["record_type"] != "mutation_applied":
            continue
        following = trace[i + 1]
        assert following["record_type"] == "transmitted"
        assert following["variant"]["variant_id"] == p["variant_id"]
        # The transmitted variant carries the mutation as its effect:
        # mutated_slot set, and the slot's value is the record's new_value.
        assert following["variant"]["mutated_slot"] == p["slot"]
        assert following["variant"]["slots"][p["slot"]] == p["new_value"]


def test_scripted_retell_stays_caller_controlled(tmp_path):
    # driver.retell() with an explicit mutation must not emit a
    # mutation_applied record -- the policy applies to encounter-driven
    # retellings only; scripted mutations are their caller's business.
    driver = Driver(
        run_id="run-mut-scripted", seed_id=_SEED, save_uuid="save-1", generation=0,
        runs_dir=tmp_path, mutation_probability=1.0, mutation_candidates=_CANDIDATES,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        )
    )
    claim, irileth_belief, _ = driver.witness(
        claim_id="claim-jarl-death", belief_id="belief-irileth-death", evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
        canonical_event_key=EventKey("save-1", 0, 1), witness_id="irileth", gamets=0.0,
    )
    driver.retell(
        claim=claim, parent_variant=None,
        variant_id="variant-scripted", belief_id="belief-hulda", evidence_id="evidence-hulda",
        teller_id="irileth", teller_belief=irileth_belief, hearer_id="hulda", gamets=1.0,
        mutate_slot="perpetrator", mutated_value="the Thalmor",
    )
    driver.close()
    trace = _trace(tmp_path, "run-mut-scripted")
    assert [p for p in trace if p["record_type"] == "mutation_applied"] == []
    (transmitted,) = [p for p in trace if p["record_type"] == "transmitted"]
    assert transmitted["variant"]["mutated_slot"] == "perpetrator"


def _state_dict(state, *, tick: int) -> dict:
    """serialize_state minus the schedule key -- schedules are inputs, and the
    keyframe stores blocks effective at the keyframe's tick, not the query's."""
    data = serialize_state(state.claims, state.social, state.schedule, tick=tick)
    del data["schedules"]
    return data


def test_replay_state_at_matches_in_memory_on_a_run_containing_mutations(tmp_path):
    """Reader replay-exactness: state_at(T) replays the mutation's effect via
    the transmitted record's variant (mutated_slot), so a log containing
    mutation_applied records reconstructs with no reader change at all.
    Snapshots the live stores at several ticks (keyframe interval 5, so both
    keyframe-boundary and mid-interval replay are exercised) and asserts the
    log-alone reconstruction matches.
    """
    ticks = 30
    driver = Driver(
        run_id="run-mut-replay",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=_three_npc_schedule(end_tick=ticks),
        encounter_probability=1.0,
        mutation_probability=1.0,
        mutation_candidates=_CANDIDATES,
        keyframe_interval=5,
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        ),
        origin={"kind": "scenario", "detail": "test_driver_mutation"},
    )
    driver.witness(
        claim_id="claim-jarl-death", belief_id="belief-irileth-death", evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
        canonical_event_key=EventKey("save-1", 0, 1), witness_id="irileth", gamets=0.0,
    )
    snapshots = {}
    for tick in range(ticks):
        driver.run(tick, tick + 1)
        snapshots[tick] = _state_dict(driver, tick=tick)
    driver.close()

    reader = FrameLogReader(tmp_path / "run-mut-replay")
    mutations = [r["payload"] for r in reader.records("trace") if r["payload"]["record_type"] == "mutation_applied"]
    assert mutations  # the run under test really does contain mutations
    for tick, expected in snapshots.items():
        reconstructed = reader.state_at(tick)
        assert _state_dict(reconstructed, tick=tick) == expected, f"reconstruction diverged at tick {tick}"
