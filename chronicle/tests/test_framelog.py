"""chronicle/framelog.py: writer/reader contract tests (docs/frame-log-schema.md v1).

Includes the two M0 acceptance proofs from docs/dashboard-build-plan.md §2:
reader reconstruction at arbitrary T matches the in-memory run exactly, and
scanning the streams rebuilds an identical index.json.
"""

import json

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied
from chronicle.framelog import FrameLogReader, FrameLogWriter, serialize_state
from chronicle.schedule import ScheduleBlock

_SEED = "framelog-test-seed"


def _schedule(end_tick: int = 60) -> tuple[ScheduleBlock, ...]:
    return (
        ScheduleBlock(npc_id="irileth", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id="proventus", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id="ysolda", location_id="bannered_mare", start_tick=10, end_tick=end_tick),
    )


def _seed_events_and_claim(driver: Driver) -> None:
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        ),
        origin={"kind": "scenario", "detail": "test_framelog"},
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid="save-1", generation=0, seq=2,
            gamets=0.0, wall_ts=1.0, witness_id="irileth",
            perpetrator_id="unknown", crime_type="murder", location_id="bannered_mare",
        )
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


def _state_dict(state, *, tick: int) -> dict:
    """serialize_state minus the schedule key -- schedules are inputs, and the
    keyframe stores blocks effective at the keyframe's tick, not the query's."""
    data = serialize_state(state.claims, state.social, state.schedule, tick=tick)
    del data["schedules"]
    return data


def test_writer_creates_the_frozen_layout_and_registry(tmp_path):
    with FrameLogWriter(run_id="run-1", seed_id=_SEED, save_uuid="save-1", generation=0, runs_dir=tmp_path):
        pass
    run_dir = tmp_path / "run-1"
    assert (run_dir / "events.jsonl").exists()
    assert (run_dir / "trace.jsonl").exists()
    assert (run_dir / "index.json").exists()
    registry = json.loads((tmp_path / "index.json").read_text())
    assert registry["schema_version"] == 1
    (entry,) = [r for r in registry["runs"] if r["run_id"] == "run-1"]
    assert entry["seed_id"] == _SEED
    assert entry["branches"] == [{"save_uuid": "save-1", "generation": 0}]
    assert entry["streams"] == {"events": "events.jsonl", "trace": "trace.jsonl"}
    assert entry["status"] == "complete"


def test_writer_refuses_to_clobber_an_existing_run_dir(tmp_path):
    import pytest

    with FrameLogWriter(run_id="run-1", seed_id=_SEED, save_uuid="save-1", generation=0, runs_dir=tmp_path):
        pass
    with pytest.raises(FileExistsError):
        FrameLogWriter(run_id="run-1", seed_id=_SEED, save_uuid="save-1", generation=0, runs_dir=tmp_path)


def test_envelope_carries_the_frozen_fields_from_record_one(tmp_path):
    with FrameLogWriter(run_id="run-1", seed_id=_SEED, save_uuid="save-1", generation=2, runs_dir=tmp_path) as writer:
        writer.write_trace(tick=3, payload={"record_type": "nothing_salient", "location_id": "loc", "npc_a": "a", "npc_b": "b", "claim_id": None, "reason": "neither-informed"})
        writer.flush()
    (record,) = [json.loads(line) for line in (tmp_path / "run-1" / "trace.jsonl").read_text().splitlines()]
    # ui-spec §1.1: (schema_version, seed_id, save_uuid, generation, tick,
    # stream, seq, payload) -- the branch key is present from record one.
    assert {*record} == {"schema_version", "seed_id", "save_uuid", "generation", "tick", "stream", "seq", "payload"}
    assert record["schema_version"] == 1
    assert record["seed_id"] == _SEED
    assert record["save_uuid"] == "save-1"
    assert record["generation"] == 2
    assert record["tick"] == 3
    assert record["stream"] == "trace"
    assert record["seq"] == 0


def test_reader_treats_a_non_terminated_tail_as_not_yet_written(tmp_path):
    with FrameLogWriter(run_id="run-1", seed_id=_SEED, save_uuid="save-1", generation=0, runs_dir=tmp_path) as writer:
        for tick in range(3):
            writer.write_trace(tick=tick, payload={"record_type": "nothing_salient", "location_id": "loc", "npc_a": "a", "npc_b": "b", "claim_id": None, "reason": "neither-informed"})
            writer.flush()
    # Simulate a torn write mid-append: half a JSON line at the tail.
    with open(tmp_path / "run-1" / "trace.jsonl", "ab") as f:
        f.write(b'{"schema_version": 1, "tic')
    reader = FrameLogReader(tmp_path / "run-1")
    assert len(list(reader.records("trace"))) == 3  # the torn tail is skipped, not yielded


def test_scanning_the_streams_rebuilds_an_identical_index(tmp_path):
    """M0 acceptance: the sidecar index is pure acceleration (ui-spec §1.1 three-things rule)."""
    driver = Driver(
        run_id="run-indexed",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=_schedule(),
        encounter_probability=0.5,
        keyframe_interval=5,
        runs_dir=tmp_path,
    )
    _seed_events_and_claim(driver)
    driver.run(0, 23)
    driver.close()
    reader = FrameLogReader(tmp_path / "run-indexed")
    assert reader.rebuild_index() == reader.read_index()


def test_reader_reconstruction_at_arbitrary_t_matches_the_in_memory_run(tmp_path):
    """M0 acceptance: nearest keyframe + replayed deltas == the live stores, at every tick.

    Snapshots the in-memory stores after every tick of a run (small keyframe
    interval so keyframe-load, keyframe+replay, and from-scratch replay paths
    are all exercised), then reconstructs each tick from the log alone and
    compares the full derived state.
    """
    driver = Driver(
        run_id="run-replay",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=_schedule(),
        encounter_probability=1.0,
        keyframe_interval=5,
        runs_dir=tmp_path,
    )
    _seed_events_and_claim(driver)
    # A second witness to the same canonical event (never scheduled, so the
    # tick loop can't reach him), and his corroboration of Irileth's belief,
    # before the loop -- replay covers belief_corroborated at tick 0, in the
    # same emission order as the live run.
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-guard2-death",
        evidence_id="evidence-guard2-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
        canonical_event_key=EventKey("save-1", 0, 1),
        witness_id="whiterun_guard_2",
        gamets=0.0,
    )
    driver.corroborate(
        belief_id="belief-irileth-death",
        source_belief=driver.belief_of("whiterun_guard_2", "claim-jarl-death"),
        evidence_id="evidence-guard2-corroborates",
        gamets=0.0,
    )
    snapshots = {}
    for tick in range(37):
        driver.run(tick, tick + 1)
        snapshots[tick] = _state_dict(driver, tick=tick)
    # A scripted mutated retelling after the loop, so replay covers
    # transmitted-with-mutation across a keyframe boundary too.
    irileth_belief = driver.belief_of("irileth", "claim-jarl-death")
    parent_variant = driver.variant(irileth_belief.variant_id) if irileth_belief.variant_id is not None else None
    driver.retell(
        claim=driver.claim("claim-jarl-death"),
        parent_variant=parent_variant,
        variant_id="variant-scripted-1",
        belief_id="belief-scripted-belethor",
        evidence_id="evidence-scripted-belethor",
        teller_id="irileth",
        teller_belief=irileth_belief,
        hearer_id="belethor",
        gamets=38.0,
        mutate_slot="perpetrator",
        mutated_value="the Thalmor",
    )
    snapshots[38] = _state_dict(driver, tick=38)
    driver.close()

    reader = FrameLogReader(tmp_path / "run-replay")
    for tick, expected in snapshots.items():
        reconstructed = reader.state_at(tick)
        assert _state_dict(reconstructed, tick=tick) == expected, f"reconstruction diverged at tick {tick}"


def test_keyframe_round_trips_layer4_social_state(tmp_path):
    """Keyframe state includes relationships/grudges/obligations/reputations (schema §5); loading one rebuilds them."""
    from chronicle.fixtures.whiterun_relationships import seed_whiterun
    from chronicle.social import form_grudge

    driver = Driver(
        run_id="run-social",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=_schedule(),
        keyframe_interval=1,  # keyframe every tick, so social state is captured immediately
        runs_dir=tmp_path,
    )
    seed_whiterun(driver.social, gamets=0.0)
    _seed_events_and_claim(driver)
    irileth_belief = driver.belief_of("irileth", "claim-jarl-death")
    driver.social.add_grudge(
        form_grudge(
            id="grudge-irileth-thalmor",
            holder_id="irileth",
            victim_id="jarl_balgruuf",
            target_id="the_thalmor",
            grievance_type="murder_of_ally",
            source_belief_id=irileth_belief.id,
            evidentiary_strength=irileth_belief.confidence,
            relationship_to_victim=driver.social.any_relationship("irileth", "jarl_balgruuf"),
            gamets=0.0,
        )
    )
    driver.social.update_reputation(
        observer_id="irileth", subject_id="the_thalmor", context="violence",
        kind="witnessed", positive=False, gamets=0.0,
    )
    driver.run(0, 3)
    expected = _state_dict(driver, tick=2)
    driver.close()

    # Tick 2 is exactly a keyframe tick (K=1): this exercises pure keyframe
    # load of the layer-4 records, no replay.
    reconstructed = FrameLogReader(tmp_path / "run-social").state_at(2)
    assert _state_dict(reconstructed, tick=2) == expected


def test_reader_ignores_unknown_trace_record_types(tmp_path):
    """Schema §7: readers skip-and-continue on record types from newer schema versions."""
    with FrameLogWriter(run_id="run-1", seed_id=_SEED, save_uuid="save-1", generation=0, runs_dir=tmp_path) as writer:
        writer.write_trace(tick=0, payload={"record_type": "tier9_unobtainium", "whatever": 1})
        writer.flush()
    state = FrameLogReader(tmp_path / "run-1").state_at(0)
    assert state.claims.beliefs_of("anyone") == ()
