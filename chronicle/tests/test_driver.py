"""chronicle/driver.py: the tick loop and its frame-log emissions."""

import json

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import CrimeWitnessed, EventLog, NPCDied
from chronicle.framelog import FrameLogReader
from chronicle.schedule import ScheduleBlock

_SEED = "driver-test-seed"


def _three_npc_schedule(end_tick: int = 50) -> tuple[ScheduleBlock, ...]:
    return (
        ScheduleBlock(npc_id="irileth", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id="proventus", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
    )


def _death_event(seq: int = 1) -> NPCDied:
    return NPCDied(
        tick=0, save_uuid="save-1", generation=0, seq=seq,
        gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
        cause="assassination", killer_id=None, location_id="bannered_mare",
    )


def _witness_death(driver: Driver):
    return driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "bannered_mare"},
        canonical_event_key=EventKey("save-1", 0, 1),
        witness_id="irileth",
        gamets=0.0,
    )


def _run_driver(runs_dir, run_id: str, *, encounter_probability: float = 1.0, ticks: int = 30) -> Driver:
    driver = Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=_three_npc_schedule(),
        encounter_probability=encounter_probability,
        runs_dir=runs_dir,
    )
    driver.inject_event(_death_event(), origin={"kind": "scenario", "detail": "test_driver"})
    _witness_death(driver)
    driver.run(0, ticks)
    driver.close()
    return driver


def test_driver_run_propagates_the_witnessed_claim_through_encounters(tmp_path):
    driver = _run_driver(tmp_path, "run-1")
    # Irileth witnessed; the other two co-present NPCs must have heard via
    # encounter-driven retellings alone.
    for npc in ("proventus", "hulda"):
        belief = driver.belief_of(npc, "claim-jarl-death")
        assert belief is not None
        chain = driver.chain_for(belief.id)
        assert chain[-1][1].evidence_type == "witnessed"
        assert chain[-1][0].holder_id == "irileth"


def test_driver_run_is_byte_for_byte_reproducible(tmp_path):
    _run_driver(tmp_path, "run-a")
    _run_driver(tmp_path, "run-b")
    for stream in ("events.jsonl", "trace.jsonl"):
        assert (tmp_path / "run-a" / stream).read_bytes() == (tmp_path / "run-b" / stream).read_bytes()


def test_driver_emits_every_roll_including_rolled_against_negatives(tmp_path):
    _run_driver(tmp_path, "run-rolls", encounter_probability=0.5, ticks=30)
    reader = FrameLogReader(tmp_path / "run-rolls")
    rolls = [r["payload"] for r in reader.records("trace") if r["payload"]["record_type"] == "encounter_rolled"]
    assert len(rolls) == 3 * 30  # 3 co-present pairs, every tick, fired or not
    assert any(r["encountered"] for r in rolls)
    assert any(not r["encountered"] for r in rolls)
    for r in rolls:
        # frame-log schema §4: roll-bearing records carry the full key plus
        # value/threshold/outcome.
        assert set(r["roll_key"]) == {"seed_id", "purpose", "tick", "site", "participants", "draw"}
        assert r["roll_key"]["seed_id"] == _SEED
        assert r["roll_key"]["purpose"] == "encounter.co-presence"
        assert 0.0 <= r["value"] < 1.0
        assert r["threshold"] == 0.5
        assert r["outcome"] == ("encountered" if r["encountered"] else "no_encounter")


def test_driver_emits_nothing_salient_once_everyone_is_informed(tmp_path):
    _run_driver(tmp_path, "run-salient")
    reader = FrameLogReader(tmp_path / "run-salient")
    salient = [r["payload"] for r in reader.records("trace") if r["payload"]["record_type"] == "nothing_salient"]
    # By the end of the run all three NPCs hold the claim, so late-tick
    # encounters find nothing to propagate (rule 2's other half).
    assert any(r["reason"] == "both-informed" and r["claim_id"] == "claim-jarl-death" for r in salient)


def test_driver_writes_keyframes_every_k_ticks(tmp_path):
    driver = Driver(
        run_id="run-keyframes",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=_three_npc_schedule(),
        keyframe_interval=7,
        runs_dir=tmp_path,
    )
    driver.run(0, 20)
    driver.close()
    reader = FrameLogReader(tmp_path / "run-keyframes")
    keyframes = reader.read_index()["streams"]["events"]["keyframe_offsets"]
    assert [k["tick"] for k in keyframes] == [6, 13]


def test_injected_event_is_logged_with_its_origin(tmp_path):
    driver = Driver(run_id="run-events", seed_id=_SEED, save_uuid="save-1", generation=0, runs_dir=tmp_path)
    driver.inject_event(_death_event(), origin={"kind": "scenario", "detail": "test_driver"})
    driver.close()
    reader = FrameLogReader(tmp_path / "run-events")
    events = list(reader.records("events"))
    assert len(events) == 1
    record = events[0]
    assert record["seq"] == 1  # the envelope seq IS the Event.seq (schema §2)
    assert record["payload"]["event_type"] == "npc_died"
    assert record["payload"]["origin"] == {"kind": "scenario", "detail": "test_driver"}
    assert record["payload"]["gamets"] == 0.0
    assert record["payload"]["wall_ts"] == 0.0


def test_duplicate_event_injection_is_an_idempotent_no_op(tmp_path):
    driver = Driver(run_id="run-dupes", seed_id=_SEED, save_uuid="save-1", generation=0, runs_dir=tmp_path)
    assert driver.inject_event(_death_event()) is True
    assert driver.inject_event(_death_event()) is False
    driver.close()
    reader = FrameLogReader(tmp_path / "run-dupes")
    assert len(list(reader.records("events"))) == 1


def test_writer_flushes_each_tick_so_a_tailing_reader_sees_records_before_close(tmp_path):
    driver = Driver(
        run_id="run-live",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=_three_npc_schedule(),
        encounter_probability=1.0,
        runs_dir=tmp_path,
    )
    driver.inject_event(_death_event())
    _witness_death(driver)
    driver.run(0, 5)
    # No close() yet -- the liveness contract (schema §1) says a committed
    # record is visible within one tick of emission.
    with open(tmp_path / "run-live" / "trace.jsonl", "rb") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    assert rows  # trace rows from the first 5 ticks are already on disk
    assert (tmp_path / "run-live" / "index.json").exists()
    driver.close()


def test_dead_npcs_neither_tell_nor_are_told_and_generate_no_rolls(tmp_path):
    """Ladder T1.2 machinery: NPCDied excludes the deceased from encounter sampling.

    Hulda (a witness) and whiterun_guard_1 (ignorant) both die at tick 5,
    before their tavern blocks begin; irileth (a second witness, of a
    different theft) and ysolda (ignorant) live and are co-present
    throughout. The dead must neither tell (hulda's story reaches no one)
    nor be told (the guard never learns irileth's story), and no
    encounter_rolled record may name them -- while living propagation
    (irileth -> ysolda) proceeds untouched. A dead NPC's own existing
    beliefs are untouched too: death stops new propagation only.
    """
    driver = Driver(
        run_id="run-dead-excluded",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=(
            ScheduleBlock(npc_id="irileth", location_id="bannered_mare", start_tick=0, end_tick=30),
            ScheduleBlock(npc_id="ysolda", location_id="bannered_mare", start_tick=0, end_tick=30),
            # Hulda and the guard are scheduled at the tavern only AFTER
            # their deaths -- any roll naming them is a resurrection.
            ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=10, end_tick=30),
            ScheduleBlock(npc_id="whiterun_guard_1", location_id="bannered_mare", start_tick=10, end_tick=30),
        ),
        encounter_probability=1.0,
        runs_dir=tmp_path,
    )
    # Two thefts, two witnesses: irileth (living) saw claim A, hulda saw
    # claim B and then died before her tavern block. The guard dies too.
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid="save-1", generation=0, seq=1, gamets=0.0, wall_ts=0.0,
            witness_id="irileth", perpetrator_id="unknown", crime_type="theft", location_id="bannered_mare",
        )
    )
    driver.inject_event(
        CrimeWitnessed(
            tick=0, save_uuid="save-1", generation=0, seq=2, gamets=0.0, wall_ts=1.0,
            witness_id="hulda", perpetrator_id="unknown", crime_type="theft", location_id="the_market",
        )
    )
    for seq, npc_id in ((3, "hulda"), (4, "whiterun_guard_1")):
        driver.inject_event(
            NPCDied(
                tick=5, save_uuid="save-1", generation=0, seq=seq, gamets=5.0, wall_ts=5.0,
                npc_id=npc_id, cause="killed by the player", killer_id="player", location_id="dragonsreach",
            )
        )
    driver.witness(
        claim_id="claim-theft-a", belief_id="belief-irileth-a", evidence_id="evidence-irileth-a",
        kind="crime_witnessed",
        slots={"perpetrator": "unknown", "crime_type": "theft", "location": "bannered_mare"},
        canonical_event_key=EventKey("save-1", 0, 1), witness_id="irileth", gamets=0.0,
    )
    driver.witness(
        claim_id="claim-theft-b", belief_id="belief-hulda-b", evidence_id="evidence-hulda-b",
        kind="crime_witnessed",
        slots={"perpetrator": "unknown", "crime_type": "theft", "location": "the_market"},
        canonical_event_key=EventKey("save-1", 0, 2), witness_id="hulda", gamets=0.0,
    )
    driver.run(0, 30)
    driver.close()

    # Living propagation still works: ysolda learned claim A from irileth.
    assert driver.belief_of("ysolda", "claim-theft-a") is not None
    # The dead hearer stays ignorant: the guard never holds claim A.
    assert driver.belief_of("whiterun_guard_1", "claim-theft-a") is None
    # The dead teller: hulda's claim B reached nobody else...
    for npc in ("irileth", "ysolda", "whiterun_guard_1"):
        assert driver.belief_of(npc, "claim-theft-b") is None
    # ...but her own belief is untouched -- death stops new propagation only.
    assert driver.belief_of("hulda", "claim-theft-b") is not None

    reader = FrameLogReader(tmp_path / "run-dead-excluded")
    trace = [r["payload"] for r in reader.records("trace")]
    # Encounter sampling ran (irileth/ysolda were rolled every tick)...
    rolls = [p for p in trace if p["record_type"] == "encounter_rolled"]
    assert rolls
    # ...but no roll ever named a dead NPC, and no transmission ever
    # involved one as teller or hearer.
    for p in rolls:
        assert "hulda" not in (p["npc_a"], p["npc_b"])
        assert "whiterun_guard_1" not in (p["npc_a"], p["npc_b"])
    transmitted = [p for p in trace if p["record_type"] == "transmitted"]
    assert all(p["teller_id"] not in ("hulda", "whiterun_guard_1") for p in transmitted)
    assert all(p["hearer_id"] not in ("hulda", "whiterun_guard_1") for p in transmitted)


def test_deaths_in_a_prepopulated_event_log_are_honored(tmp_path):
    """Start-from-keyframe path (ladder T1.2): an NPCDied already present in the
    event_log passed to the constructor marks the NPC deceased -- the dead are
    not resurrected by resuming from prior state.
    """
    event_log = EventLog()
    event_log.append(
        CrimeWitnessed(
            tick=0, save_uuid="save-1", generation=0, seq=1, gamets=0.0, wall_ts=0.0,
            witness_id="hulda", perpetrator_id="unknown", crime_type="theft", location_id="the_market",
        )
    )
    event_log.append(
        NPCDied(
            tick=0, save_uuid="save-1", generation=0, seq=2, gamets=0.0, wall_ts=1.0,
            npc_id="hulda", cause="killed by the player", killer_id="player", location_id="the_market",
        )
    )
    driver = Driver(
        run_id="run-prepopulated-death",
        seed_id=_SEED,
        save_uuid="save-1",
        generation=0,
        schedule=(
            ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=10),
            ScheduleBlock(npc_id="ysolda", location_id="bannered_mare", start_tick=0, end_tick=10),
        ),
        encounter_probability=1.0,
        runs_dir=tmp_path,
        event_log=event_log,
    )
    # Hulda witnessed the theft before she died (a scripted derivation --
    # death excludes her from encounters, not from the historical record).
    driver.witness(
        claim_id="claim-theft", belief_id="belief-hulda", evidence_id="evidence-hulda",
        kind="crime_witnessed",
        slots={"perpetrator": "unknown", "crime_type": "theft", "location": "the_market"},
        canonical_event_key=EventKey("save-1", 0, 1), witness_id="hulda", gamets=0.0,
    )
    driver.run(0, 10)
    driver.close()

    # Ysolda was co-present with hulda's block every tick and never heard the
    # story; with hulda excluded, ysolda is a lone present NPC, so no pair
    # was ever rolled at all.
    assert driver.belief_of("ysolda", "claim-theft") is None
    reader = FrameLogReader(tmp_path / "run-prepopulated-death")
    rolls = [r["payload"] for r in reader.records("trace") if r["payload"]["record_type"] == "encounter_rolled"]
    assert rolls == []


def test_driver_works_as_a_context_manager(tmp_path):
    # Every other test calls driver.close() explicitly; nothing exercises
    # __enter__/__exit__ itself, even though it's the documented shape
    # (Driver's docstring shows `with Driver(...) as d:`).
    with Driver(run_id="run-context-manager", seed_id=_SEED, save_uuid="save-1", generation=0, runs_dir=tmp_path) as driver:
        driver.run(0, 1)
    reader = FrameLogReader(tmp_path / "run-context-manager")
    registry = json.loads((tmp_path / "index.json").read_text())
    entry = next(r for r in registry["runs"] if r["run_id"] == "run-context-manager")
    assert entry["status"] == "complete"  # __exit__ called close(), which registers completion
    assert list(reader.records("events")) is not None  # log is readable after the with-block exits
