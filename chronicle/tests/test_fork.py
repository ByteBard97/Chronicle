"""chronicle/fork.py + the ``chronicle fork`` CLI subcommand (docs/design/fork-on-disk-support.md).

Copy-forward, not cross-run reference (the design doc's §1 ruling): a fork
creates a brand-new run directory whose events.jsonl/trace.jsonl open with a
verbatim copy of the parent's records up to the fork tick, then a Driver at
generation = parent_generation + 1 continues from there. These tests build a
small real Driver run fixture, fork it partway through, and assert: the
copied prefix matches the parent's own records exactly, the parent's own
files are provably untouched, the new run's generation is parent + 1, and
injecting a new event into the forked Driver produces a real divergent
continuation the parent's log never sees.
"""

from __future__ import annotations

import json

import pytest

from chronicle.claims import EventKey
from chronicle.cli import main
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.fork import fork_run
from chronicle.framelog import STREAM_FILES, FrameLogReader
from chronicle.schedule import ScheduleBlock

_SEED = "fork-test-seed"
_RUN = "fork-parent-run"
_SAVE_UUID = "save-fork-1"
_GENERATION = 0
_TICKS = 20
_FORK_TICK = 8


def _build_parent(tmp_path, *, run_id: str = _RUN) -> None:
    driver = Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=_GENERATION,
        schedule=(
            ScheduleBlock(npc_id="irileth", location_id="dragonsreach", start_tick=0, end_tick=_TICKS),
            ScheduleBlock(npc_id="proventus", location_id="dragonsreach", start_tick=0, end_tick=_TICKS),
        ),
        encounter_probability=1.0,
        keyframe_interval=5,
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE_UUID, generation=_GENERATION, seq=0,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_fork"},
    )
    driver.witness(
        claim_id="claim-jarl-death",
        belief_id="belief-irileth-death",
        evidence_id="evidence-irileth-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=EventKey(_SAVE_UUID, _GENERATION, 0),
        witness_id="irileth",
        gamets=0.0,
    )
    driver.run(0, _TICKS)
    driver.close()


def _stream_records(run_dir, stream: str) -> list[dict]:
    return list(FrameLogReader(run_dir).records(stream))


def _read_bytes(run_dir) -> dict[str, bytes]:
    return {filename: (run_dir / filename).read_bytes() for filename in STREAM_FILES.values()}


def test_fork_copies_parent_prefix_verbatim(tmp_path):
    _build_parent(tmp_path)
    parent_dir = tmp_path / _RUN
    parent_reader = FrameLogReader(parent_dir)
    parent_events_prefix = list(parent_reader.records("events", upto_tick=_FORK_TICK))
    parent_trace_prefix = list(parent_reader.records("trace", upto_tick=_FORK_TICK))
    assert parent_events_prefix, "fixture should have produced at least one events-stream record by the fork tick"

    driver = fork_run(_RUN, at_tick=_FORK_TICK, new_run_id="fork-child", runs_dir=tmp_path)
    try:
        assert driver.generation == _GENERATION + 1
        assert driver.save_uuid == _SAVE_UUID
    finally:
        driver.close()

    child_dir = tmp_path / "fork-child"
    child_events = _stream_records(child_dir, "events")
    child_trace = _stream_records(child_dir, "trace")
    assert child_events == parent_events_prefix
    assert child_trace == parent_trace_prefix


def test_fork_leaves_parent_files_byte_for_byte_untouched(tmp_path):
    _build_parent(tmp_path)
    parent_dir = tmp_path / _RUN
    before = _read_bytes(parent_dir)

    driver = fork_run(_RUN, at_tick=_FORK_TICK, new_run_id="fork-child", runs_dir=tmp_path)
    driver.inject_event(
        NPCDied(
            tick=_FORK_TICK, save_uuid=_SAVE_UUID, generation=driver.generation, seq=0,
            gamets=float(_FORK_TICK), wall_ts=0.0, npc_id="proventus",
            cause="poison", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_fork divergence"},
    )
    driver.run(_FORK_TICK, _FORK_TICK + 3)
    driver.close()

    after = _read_bytes(parent_dir)
    assert after == before


def test_fork_registers_the_new_run_at_generation_plus_one(tmp_path):
    _build_parent(tmp_path)
    driver = fork_run(_RUN, at_tick=_FORK_TICK, new_run_id="fork-child", runs_dir=tmp_path)
    driver.close()

    registry = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    entries = {entry["run_id"]: entry for entry in registry["runs"]}
    assert "fork-child" in entries
    branch = entries["fork-child"]["branches"][0]
    assert branch["save_uuid"] == _SAVE_UUID
    assert branch["generation"] == _GENERATION + 1
    assert entries["fork-child"]["status"] == "complete"
    # The parent's own registry entry is untouched by the fork.
    assert entries[_RUN]["branches"][0]["generation"] == _GENERATION


def test_branch_identity_reports_the_forks_own_generation_not_the_parents(tmp_path):
    """Regression: chronicle inject/sync-check both resolve a run's identity via
    cli._branch_identity(), which used to read the FIRST record's envelope --
    correct before forking existed, wrong now that a fork's copied prefix is
    deliberately stamped with the PARENT's generation (fork.py's own
    docstring: "they really happened under that branch"). A forked run's
    first record is one of those copied ones, so the old record-first order
    silently reported the parent's generation for the fork itself. The
    registry (written from the Driver's own generation, always correct) must
    win; record envelopes are a fallback for a run with no registry entry."""
    from chronicle.cli import _branch_identity
    from chronicle.framelog import FrameLogReader

    _build_parent(tmp_path)
    driver = fork_run(_RUN, at_tick=_FORK_TICK, new_run_id="fork-child", runs_dir=tmp_path)
    driver.close()

    reader = FrameLogReader(tmp_path / "fork-child")
    # The fork's copy-forward prefix is nonempty (docs/design/fork-on-disk-
    # support.md's whole point) so this assertion actually exercises the
    # bug: the first record really is stamped at the parent's generation.
    first_record_generation = next(reader.records("events"), None) or next(reader.records("trace"))
    assert first_record_generation["generation"] == _GENERATION  # the parent's, by design (copy-forward)

    _seed_id, save_uuid, generation = _branch_identity(reader, tmp_path, "fork-child")
    assert generation == _GENERATION + 1  # the fork's OWN generation, from the registry
    assert save_uuid == _SAVE_UUID


def test_fork_injecting_a_new_event_diverges_from_the_parent(tmp_path):
    _build_parent(tmp_path)
    driver = fork_run(_RUN, at_tick=_FORK_TICK, new_run_id="fork-child", runs_dir=tmp_path)
    driver.inject_event(
        NPCDied(
            tick=_FORK_TICK, save_uuid=_SAVE_UUID, generation=driver.generation, seq=0,
            gamets=float(_FORK_TICK), wall_ts=0.0, npc_id="proventus",
            cause="poison", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_fork divergence"},
    )
    driver.run(_FORK_TICK, _FORK_TICK + 5)
    driver.close()

    child_reader = FrameLogReader(tmp_path / "fork-child")
    child_events = list(child_reader.records("events"))
    assert any(r["payload"].get("event_type") == "npc_died" and r["payload"].get("npc_id") == "proventus" for r in child_events)

    parent_reader = FrameLogReader(tmp_path / _RUN)
    parent_events = list(parent_reader.records("events"))
    assert not any(r["payload"].get("event_type") == "npc_died" and r["payload"].get("npc_id") == "proventus" for r in parent_events)

    # The forked Driver's own state reflects both the inherited death
    # (jarl_balgruuf, injected before the fork tick in the parent) and the
    # new divergent one (proventus, injected only after the fork).
    assert "jarl_balgruuf" in driver._deceased
    assert "proventus" in driver._deceased


def test_fork_rejects_a_tick_beyond_the_parents_max_tick(tmp_path):
    _build_parent(tmp_path)
    with pytest.raises(ValueError):
        fork_run(_RUN, at_tick=10_000, new_run_id="fork-too-far", runs_dir=tmp_path)


def test_fork_rejects_an_unknown_parent_run(tmp_path):
    with pytest.raises(FileNotFoundError):
        fork_run("no-such-run", at_tick=0, new_run_id="fork-child", runs_dir=tmp_path)


def test_fork_rejects_a_new_run_id_that_already_exists(tmp_path):
    _build_parent(tmp_path)
    driver = fork_run(_RUN, at_tick=_FORK_TICK, new_run_id="fork-child", runs_dir=tmp_path)
    driver.close()
    with pytest.raises(FileExistsError):
        fork_run(_RUN, at_tick=_FORK_TICK, new_run_id="fork-child", runs_dir=tmp_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_cli_fork_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    _build_parent(tmp_path)

    rc = main(["fork", _RUN, "--at-tick", str(_FORK_TICK), "--new-run-id", "fork-cli-child"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "fork-cli-child" in out
    assert f"generation {_GENERATION + 1}" in out

    registry = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    entries = {entry["run_id"]: entry for entry in registry["runs"]}
    assert entries["fork-cli-child"]["branches"][0]["generation"] == _GENERATION + 1
    assert entries["fork-cli-child"]["status"] == "complete"


def test_cli_fork_auto_generates_a_new_run_id_when_omitted(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    _build_parent(tmp_path)

    rc = main(["fork", _RUN, "--at-tick", str(_FORK_TICK)])
    assert rc == 0
    expected_run_id = f"{_RUN}-fork-{_FORK_TICK}"
    assert (tmp_path / expected_run_id).exists()


def test_cli_fork_unknown_run_exits_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    rc = main(["fork", "no-such-run", "--at-tick", "0"])
    assert rc == 1
    assert "no such run" in capsys.readouterr().err


def test_cli_fork_at_tick_beyond_max_exits_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    _build_parent(tmp_path)
    rc = main(["fork", _RUN, "--at-tick", "10000"])
    assert rc == 1
    assert "beyond" in capsys.readouterr().err


def test_cli_fork_existing_new_run_id_exits_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    _build_parent(tmp_path)
    rc = main(["fork", _RUN, "--at-tick", str(_FORK_TICK), "--new-run-id", "fork-cli-child"])
    assert rc == 0
    rc = main(["fork", _RUN, "--at-tick", str(_FORK_TICK), "--new-run-id", "fork-cli-child"])
    assert rc == 1
    assert "already exists" in capsys.readouterr().err
