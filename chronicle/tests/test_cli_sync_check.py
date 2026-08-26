"""chronicle/cli.py: the ``sync-check`` subcommand (docs/design/chronicle-sync-cli-integration.md).

Wires ``chronicle.sync.resolve()`` to a real run's on-disk state.
CONTINUE always applies itself (nothing to write). FORK/ADOPT are
computed and reported (exit 3) but NOT applied unless ``--apply`` is
given, in which case they call ``chronicle.fork.fork_run()``
(docs/design/fork-on-disk-support.md) for real. Runs are built with the
real Driver in a tmp CHRONICLE_RUNS_DIR, the same pattern as
chronicle/tests/test_agent_debug_cli.py's ``run_dir`` fixture.
"""

from __future__ import annotations

import json

import pytest

from chronicle.cli import main
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.schedule import ScheduleBlock

_SEED = "sync-check-seed"
_RUN = "sync-check-run"
_SAVE_UUID = "save-sync-check-1"
_GENERATION = 0
_TICKS = 10  # driver.run(0, _TICKS) -> max tick is _TICKS - 1 == 9


@pytest.fixture()
def run_dir(tmp_path, monkeypatch):
    """A small real Driver run with two injected canonical events (seq=0, seq=1) -- head_seq is therefore 1."""
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=_RUN,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=_GENERATION,
        schedule=(ScheduleBlock(npc_id="irileth", location_id="dragonsreach", start_tick=0, end_tick=_TICKS),),
        encounter_probability=1.0,
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE_UUID, generation=_GENERATION, seq=0,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_cli_sync_check"},
    )
    driver.inject_event(
        NPCDied(
            tick=1, save_uuid=_SAVE_UUID, generation=_GENERATION, seq=1,
            gamets=1.0, wall_ts=0.0, npc_id="proventus",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_cli_sync_check"},
    )
    driver.run(0, _TICKS)
    driver.close()
    return tmp_path / _RUN


def _manifest(**overrides: object) -> str:
    base = {
        "format_version": 1,
        "save_uuid": _SAVE_UUID,
        "generation": _GENERATION,
        "parent_generation": None,
        "head_seq": 1,
        "gamets": float(_TICKS - 1),  # matches the run's max tick/gamets
        "wall_ts": 1000.0,
    }
    base.update(overrides)
    return json.dumps(base)


# ---------------------------------------------------------------------------
# CONTINUE
# ---------------------------------------------------------------------------


def test_sync_check_continue_matches_the_runs_state(run_dir, capsys):
    rc = main(["sync-check", _RUN, "--manifest", _manifest()])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    result = json.loads(captured.out)
    assert result["decision"] == "CONTINUE"
    assert result["branch_generation"] == _GENERATION
    assert result["replay_from_seq"] is None


def test_sync_check_continue_reports_a_replay_gap_when_the_run_is_ahead(run_dir, capsys):
    # The run's head_seq is 1 (two injected events); a manifest that only
    # ever ACKed seq 0 should come back CONTINUE with replay_from_seq
    # pointing past its last ACKed seq (i.e. 1).
    rc = main(["sync-check", _RUN, "--manifest", _manifest(head_seq=0)])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    result = json.loads(captured.out)
    assert result["decision"] == "CONTINUE"
    assert result["replay_from_seq"] == 1


# ---------------------------------------------------------------------------
# FORK / ADOPT -- computed but not actionable
# ---------------------------------------------------------------------------


def test_sync_check_fork_on_stale_gamets_is_reported_but_not_applied(run_dir, capsys):
    # Same save_uuid/generation, but the manifest's in-game clock is behind
    # the run's head gamets -- FORK territory.
    rc = main(["sync-check", _RUN, "--manifest", _manifest(gamets=0.0)])
    captured = capsys.readouterr()
    assert rc == 3
    result = json.loads(captured.out)
    assert result["decision"] == "FORK"
    assert "fork-on-disk" in captured.err
    assert "fork-on-disk" not in captured.out  # the limitation message is on stderr, not mixed into the JSON


def test_sync_check_adopt_on_unknown_generation_is_reported_but_not_applied(run_dir, capsys):
    rc = main(["sync-check", _RUN, "--manifest", _manifest(generation=99)])
    captured = capsys.readouterr()
    assert rc == 3
    result = json.loads(captured.out)
    assert result["decision"] == "ADOPT"
    assert result["branch_generation"] == 99
    assert "fork-on-disk" in captured.err


# ---------------------------------------------------------------------------
# FORK / ADOPT with --apply -- actually forks (chronicle.fork.fork_run)
# ---------------------------------------------------------------------------


def test_sync_check_apply_forks_a_stale_gamets_manifest(run_dir, tmp_path, capsys):
    # fork_at_gamets on a stale-gamets FORK is the manifest's own gamets
    # (chronicle/sync.py's resolve()) -- here 0.0, so fork_run() forks at
    # tick 0, the run's very first tick.
    rc = main(["sync-check", _RUN, "--manifest", _manifest(gamets=0.0), "--apply"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    result = json.loads(captured.out)
    assert result["decision"] == "FORK"
    assert "applied FORK" in captured.err

    new_run_id = f"{_RUN}-fork-0"
    assert (tmp_path / new_run_id).exists()
    registry = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    entries = {entry["run_id"]: entry for entry in registry["runs"]}
    assert entries[new_run_id]["branches"][0]["generation"] == _GENERATION + 1
    # The parent's own registry entry and generation are untouched.
    assert entries[_RUN]["branches"][0]["generation"] == _GENERATION


def test_sync_check_apply_respects_new_run_id(run_dir, tmp_path, capsys):
    rc = main(["sync-check", _RUN, "--manifest", _manifest(gamets=0.0), "--apply", "--new-run-id", "my-fork"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert (tmp_path / "my-fork").exists()


def test_sync_check_apply_on_continue_is_a_no_op_since_continue_already_applied_itself(run_dir, capsys):
    # --apply only changes FORK/ADOPT handling; CONTINUE's behavior (and
    # exit code) is identical with or without the flag.
    rc = main(["sync-check", _RUN, "--manifest", _manifest(), "--apply"])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    assert json.loads(captured.out)["decision"] == "CONTINUE"


# ---------------------------------------------------------------------------
# LEGACY_IMPORT -- report-only
# ---------------------------------------------------------------------------


def test_sync_check_legacy_import_on_a_future_format_version(run_dir, capsys):
    rc = main(["sync-check", _RUN, "--manifest", _manifest(format_version=2)])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    result = json.loads(captured.out)
    assert result["decision"] == "LEGACY_IMPORT"
    assert "format_version" in captured.err
    assert "no new" in captured.err


def test_sync_check_legacy_import_gate_runs_before_field_validation(run_dir, capsys):
    """A future-version manifest carrying a field this build doesn't recognize yet (the realistic
    trigger -- a newer shim added a field) must still route to LEGACY_IMPORT, not 'unknown field(s)'
    -- ADR-0005's tolerant-read rule: no field on a too-new manifest gets interpreted at all."""
    manifest = json.loads(_manifest(format_version=2))
    manifest["char_name_hash"] = "deadbeef"  # a hypothetical newer-shim addition
    rc = main(["sync-check", _RUN, "--manifest", json.dumps(manifest)])
    captured = capsys.readouterr()
    assert rc == 0, captured.err
    result = json.loads(captured.out)
    assert result["decision"] == "LEGACY_IMPORT"
    assert "unknown field" not in captured.err


# ---------------------------------------------------------------------------
# save_uuid mismatch -- refuse, don't classify against the wrong run
# ---------------------------------------------------------------------------


def test_sync_check_refuses_a_manifest_for_a_different_save_uuid(run_dir, capsys):
    rc = main(["sync-check", _RUN, "--manifest", _manifest(save_uuid="some-other-save")])
    captured = capsys.readouterr()
    assert rc == 1
    assert "does not match" in captured.err
    assert captured.out == ""  # never a confident decision against the wrong run's state


# ---------------------------------------------------------------------------
# malformed / missing --manifest
# ---------------------------------------------------------------------------


def test_sync_check_rejects_invalid_json(run_dir, capsys):
    rc = main(["sync-check", _RUN, "--manifest", "{not json"])
    captured = capsys.readouterr()
    assert rc == 1
    assert "not valid JSON" in captured.err


def test_sync_check_rejects_missing_fields(run_dir, capsys):
    incomplete = json.dumps({"format_version": 1, "save_uuid": _SAVE_UUID, "generation": 0})
    rc = main(["sync-check", _RUN, "--manifest", incomplete])
    captured = capsys.readouterr()
    assert rc == 1
    assert "missing required field" in captured.err
    assert "head_seq" in captured.err


def test_sync_check_rejects_unknown_fields(run_dir, capsys):
    extra = json.loads(_manifest())
    extra["char_name_hash"] = "deadbeef"
    rc = main(["sync-check", _RUN, "--manifest", json.dumps(extra)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "unknown field" in captured.err


def test_sync_check_rejects_wrong_field_type(run_dir, capsys):
    bad = json.loads(_manifest())
    bad["head_seq"] = "not-an-int"
    rc = main(["sync-check", _RUN, "--manifest", json.dumps(bad)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "head_seq" in captured.err


def test_sync_check_unknown_run_exits_nonzero(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    rc = main(["sync-check", "no-such-run", "--manifest", _manifest()])
    captured = capsys.readouterr()
    assert rc != 0
    assert "no such run" in captured.err
