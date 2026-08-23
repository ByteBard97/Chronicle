"""Determinism harness: same seed + same inputs must produce identical logs.

This is the property replay, run comparison, and the first-divergent-roll
finder all stand on (ADR-0009). wall_ts is the only legitimately
nondeterministic field (transaction time, schema-mandated) and is masked.
"""

import json

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.schedule import ScheduleBlock


def _schedule(end_tick: int = 60) -> tuple[ScheduleBlock, ...]:
    return (
        ScheduleBlock(npc_id="irileth", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id="proventus", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
        ScheduleBlock(npc_id="hulda", location_id="bannered_mare", start_tick=0, end_tick=end_tick),
    )


def _run(runs_dir, run_id: str, seed_id: str, *, encounter_probability: float = 0.5) -> None:
    driver = Driver(
        run_id=run_id,
        seed_id=seed_id,
        save_uuid="save-1",
        generation=0,
        schedule=_schedule(),
        encounter_probability=encounter_probability,
        runs_dir=runs_dir,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="bannered_mare",
        ),
        origin={"kind": "scenario", "detail": "test_determinism"},
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
    driver.run(0, 60)
    driver.close()


def _records(path):
    """Parse a JSONL stream, masking transaction time."""
    records = []
    for line in path.read_text().splitlines():
        rec = json.loads(line)
        payload = rec.get("payload", {})
        if isinstance(payload, dict):
            payload.pop("wall_ts", None)
        records.append(rec)
    return records


def test_same_seed_produces_identical_logs(tmp_path):
    _run(tmp_path, "det-a", "determinism-seed")
    _run(tmp_path, "det-b", "determinism-seed")
    for stream in ("events.jsonl", "trace.jsonl"):
        a = _records(tmp_path / "det-a" / stream)
        b = _records(tmp_path / "det-b" / stream)
        assert a == b, f"{stream} diverged between identical runs"


def test_different_seed_diverges(tmp_path):
    """Roll values are keyed by seed_id (ADR-0009): a different seed must
    produce a different trace — at p=0.5 over ~90 pair-rolls, identical
    outcomes by chance are effectively impossible, and the comparison is
    itself deterministic."""
    _run(tmp_path, "det-a", "seed-one")
    _run(tmp_path, "det-b", "seed-two")
    a = _records(tmp_path / "det-a" / "trace.jsonl")
    b = _records(tmp_path / "det-b" / "trace.jsonl")
    assert a != b, "different seeds produced identical traces — keying is broken"
