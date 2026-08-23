"""chronicle/framelog.py: writer/reader contract tests (docs/frame-log-schema.md v1).

Includes the two M0 acceptance proofs from docs/dashboard-build-plan.md §2:
reader reconstruction at arbitrary T matches the in-memory run exactly, and
scanning the streams rebuilds an identical index.json.
"""

import json

from chronicle.claims import ClaimStore, EventKey
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, NPCDied
from chronicle.framelog import (
    FrameLogReader,
    FrameLogWriter,
    load_state,
    serialize_state,
)
from chronicle.schedule import ScheduleBlock
from chronicle.social import SocialStateStore

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


def test_social_mutations_reconstruct_at_inter_keyframe_ticks(tmp_path):
    """Schema §4's five social trace records: layer-4 state reconstructs at
    arbitrary T, not just at keyframe granularity.

    Scripts relationship/grudge/obligation/reputation activity through the
    driver's wrappers at ticks between keyframes (K=5), snapshots the live
    stores each tick, and asserts the log-alone reconstruction matches --
    including ticks before the first keyframe, where replayed trace records
    are the only source of layer-4 state.
    """
    driver = Driver(
        run_id="run-social-replay",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        keyframe_interval=5,
        runs_dir=tmp_path,
    )
    _seed_events_and_claim(driver)
    irileth_belief = driver.belief_of("irileth", "claim-jarl-death")

    def scripted(tick: int) -> None:
        # Mutations for tick t are applied before run(t, t+1), so a keyframe
        # due at tick t captures them -- the same emission-order discipline
        # test_reader_reconstruction_at_arbitrary_t uses.
        gamets = float(tick)
        if tick == 0:
            driver.form_relationship(
                id="rel-irileth-balgruuf", from_id="irileth", to_id="jarl_balgruuf",
                basis="shared_employer", basis_id="whiterun_court", strength=0.95, gamets=gamets,
            )
            driver.form_grudge(
                id="grudge-irileth-thalmor", holder_id="irileth", victim_id="jarl_balgruuf",
                target_id="the_thalmor", grievance_type="murder_of_ally",
                source_belief_id=irileth_belief.id, evidentiary_strength=irileth_belief.confidence,
                relationship_to_victim=driver.social.any_relationship("irileth", "jarl_balgruuf"),
                gamets=gamets,
            )
            driver.update_reputation(
                observer_id="irileth", subject_id="the_thalmor", context="violence",
                kind="witnessed", positive=False, gamets=gamets,
            )
            driver.issue_obligation(
                id="obl-proventus-investigate", issuer_id="irileth", debtor_id="proventus",
                beneficiary_id=None, action="investigate the jarl's murder", condition=None,
                gamets=gamets, deadline=10.0, witnesses=("hulda",),
            )
        elif tick == 1:
            driver.update_reputation(
                observer_id="hulda", subject_id="the_thalmor", context="violence",
                kind="reported", positive=False, gamets=gamets,
            )
        elif tick == 2:
            driver.form_relationship(
                id="rel-hulda-ysolda", from_id="hulda", to_id="ysolda",
                basis="colocation", basis_id="bannered_mare", strength=0.5, gamets=gamets,
            )
        elif tick == 3:
            driver.issue_obligation(
                id="obl-ysolda-compensation", issuer_id="hulda", debtor_id="ysolda",
                beneficiary_id=None, action="pay 100 septims", condition="by the deadline",
                gamets=gamets, deadline=6.0,
            )
        elif tick == 6:
            # Resolutions land after the keyframe at tick 4, so replay must
            # re-execute them on keyframe-loaded obligations.
            driver.fulfill_obligation("obl-proventus-investigate", gamets=gamets)
        elif tick == 7:
            driver.violate_obligation("obl-ysolda-compensation", gamets=gamets, excuse="the war dried up business")
        elif tick == 8:
            # A second update folding into a reputation the tick-4 keyframe
            # already captured -- replay resumes from the stored record.
            driver.update_reputation(
                observer_id="irileth", subject_id="the_thalmor", context="violence",
                kind="reported", positive=False, gamets=gamets,
            )

    snapshots = {}
    for tick in range(12):
        scripted(tick)
        driver.run(tick, tick + 1)
        snapshots[tick] = _state_dict(driver, tick=tick)
    driver.close()

    reader = FrameLogReader(tmp_path / "run-social-replay")
    for tick, expected in snapshots.items():
        reconstructed = reader.state_at(tick)
        assert _state_dict(reconstructed, tick=tick) == expected, f"reconstruction diverged at tick {tick}"

    # Explicitly: layer-4 state is visible before the first keyframe (tick
    # 4) -- the pre-fix gap this test guards.
    early = reader.state_at(2)
    assert early.social.grudge("irileth", "the_thalmor") is not None
    assert early.social.reputation("hulda", "the_thalmor", "violence").witness_count == 1
    # Obligation resolutions replayed through the store's resolve paths.
    resolved = reader.state_at(8)
    statuses = {o.id: o.status for o in resolved.social.obligations_involving("proventus")}
    statuses.update({o.id: o.status for o in resolved.social.obligations_involving("ysolda")})
    assert statuses["obl-proventus-investigate"] == "fulfilled"
    assert statuses["obl-ysolda-compensation"] == "violated"


def test_distinct_source_counting_survives_a_keyframe_boundary(tmp_path):
    """Schema §5's rumor_sources key: a holder re-hearing the same
    claim/variant from multiple sources across a keyframe boundary keeps an
    exact distinct_source_count (rule 7), and post-keyframe hearings resume
    counting from the serialized source set, not a re-derivation.
    """
    driver = Driver(
        run_id="run-rumor-sources",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        keyframe_interval=2,
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        )
    )
    # Three independent witnesses to the same event (identical claim content,
    # one shared claim_id), so three distinct tellers can reach Hulda.
    tellers = {}
    for npc in ("irileth", "proventus", "ysolda"):
        _, tellers[npc], _ = driver.witness(
            claim_id="claim-jarl-death",
            belief_id=f"belief-{npc}-death",
            evidence_id=f"evidence-{npc}-death",
            kind="npc_death",
            slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
            canonical_event_key=EventKey("save-1", 0, 1),
            witness_id=npc,
            gamets=0.0,
        )

    def tell(teller: str, tick: int, n: int) -> None:
        # Every telling reuses variant-shared's id, so all of them land on
        # the same (hulda, claim, variant) rumor key -- the re-hearing case
        # _rumor_sources exists to count (rule 7's distinct-source spirit).
        driver.retell(
            claim=driver.claim("claim-jarl-death"),
            parent_variant=None,
            variant_id="variant-shared",
            belief_id=f"belief-hulda-{n}",
            evidence_id=f"evidence-hulda-{n}",
            teller_id=teller,
            teller_belief=tellers[teller],
            hearer_id="hulda",
            gamets=float(tick),
        )

    snapshots = {}
    tell("irileth", 0, 1)  # Hulda's first hearing: distinct_source_count 1
    driver.run(0, 1)
    snapshots[0] = _state_dict(driver, tick=0)
    tell("proventus", 1, 2)  # a second, distinct source before the keyframe
    driver.run(1, 2)  # keyframe at tick 1 carries rumor_sources {irileth, proventus}
    snapshots[1] = _state_dict(driver, tick=1)
    tell("proventus", 2, 3)  # repetition from a known source: exposure only
    driver.run(2, 3)
    snapshots[2] = _state_dict(driver, tick=2)
    tell("ysolda", 3, 4)  # a third distinct source after the keyframe
    driver.run(3, 4)
    snapshots[3] = _state_dict(driver, tick=3)
    driver.close()

    reader = FrameLogReader(tmp_path / "run-rumor-sources")
    for tick, expected in snapshots.items():
        reconstructed = reader.state_at(tick)
        assert _state_dict(reconstructed, tick=tick) == expected, f"reconstruction diverged at tick {tick}"

    # The keyframe boundary fell between tick 1 and tick 2: the replayed
    # tick-2 hearing must not count proventus as a new source, and the
    # tick-3 hearing must count ysolda as one.
    after_keyframe = reader.state_at(2).claims.rumor_state("hulda", "claim-jarl-death", "variant-shared")
    assert (after_keyframe.exposure_count, after_keyframe.distinct_source_count) == (3, 2)
    third_source = reader.state_at(3).claims.rumor_state("hulda", "claim-jarl-death", "variant-shared")
    assert (third_source.exposure_count, third_source.distinct_source_count) == (4, 3)


def test_load_state_rederives_rumor_sources_when_a_keyframe_omits_them():
    """Schema §7: pre-amendment v1 logs carry no rumor_sources key; readers
    fall back to the grounding-evidence derivation and stay readable."""
    claims = ClaimStore()
    claims.witness(
        claim_id="claim-jarl-death", belief_id="belief-irileth", evidence_id="evidence-irileth",
        kind="npc_death", slots={"perpetrator": "unknown"},
        canonical_event_key=EventKey("save-1", 0, 1), witness_id="irileth", gamets=0.0,
    )
    claims.retell(
        claim=claims.claim("claim-jarl-death"), parent_variant=None, variant_id="variant-1",
        belief_id="belief-hulda", evidence_id="evidence-hulda", teller_id="irileth",
        teller_belief=claims.belief_of("irileth", "claim-jarl-death"), hearer_id="hulda", gamets=1.0,
    )
    state = serialize_state(claims, SocialStateStore(), (), tick=1)
    del state["rumor_sources"]  # simulate a pre-amendment v1 keyframe
    rebuilt = ClaimStore()
    load_state(rebuilt, SocialStateStore(), state)
    assert rebuilt._rumor_sources == claims._rumor_sources


def test_canonical_event_after_a_keyframe_never_collides_on_seq(tmp_path):
    """Schema §2: keyframes carry the highest canonical-event seq written so
    far and do not consume seq numbers -- a canonical event appended after a
    keyframe keeps its own seq, and the stream's seq is monotonic
    non-decreasing with file order the true order.
    """
    driver = Driver(
        run_id="run-keyframe-seq",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        keyframe_interval=1,
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        )
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid="save-1", generation=0, seq=2,
            gamets=0.0, wall_ts=1.0, witness_id="irileth",
            perpetrator_id="unknown", crime_type="murder", location_id="bannered_mare",
        )
    )
    driver.run(0, 1)  # keyframe at tick 0
    # This event's seq is exactly the number the superseded
    # high-water-increment scheme would have burned on the keyframe above.
    driver.inject_event(
        NPCDied(
            tick=1, save_uuid="save-1", generation=0, seq=3,
            gamets=1.0, wall_ts=2.0, npc_id="proventus",
            cause="old_age", killer_id=None, location_id=None,
        )
    )
    driver.witness(
        claim_id="claim-proventus-death",
        belief_id="belief-hulda-proventus",
        evidence_id="evidence-hulda-proventus",
        kind="npc_death",
        slots={"perpetrator": None, "cause": "old_age", "location": None},
        canonical_event_key=EventKey("save-1", 0, 3),
        witness_id="hulda",
        gamets=1.0,
    )
    driver.run(1, 2)  # keyframe at tick 1
    driver.close()

    reader = FrameLogReader(tmp_path / "run-keyframe-seq")
    records = list(reader.records("events"))
    canonical = [r for r in records if "event_type" in r["payload"]]
    keyframes = [r for r in records if r["payload"].get("record_type") == "keyframe"]
    assert [r["seq"] for r in canonical] == [1, 2, 3]  # strictly increasing, undisturbed by keyframes
    assert [r["seq"] for r in keyframes] == [2, 3]  # highest canonical seq so far; no seq consumed
    assert [r["seq"] for r in records] == sorted(r["seq"] for r in records)  # monotonic non-decreasing
    assert reader.rebuild_index() == reader.read_index()
    # Reader behavior: the post-keyframe event's derivation is visible.
    assert reader.state_at(1).claims.belief_of("hulda", "claim-proventus-death") is not None
