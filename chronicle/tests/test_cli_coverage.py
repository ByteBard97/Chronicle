"""chronicle/cli.py: coverage gaps left by test_cli.py/test_agent_debug_cli.py.

vue-tsc/vite build type-check the dashboard's TS; the Python analogue here
is that argparse wiring and error-message branches type-check (mypy-less,
but import cleanly) without ever executing. A coverage pass
(`uv run --with pytest-cov pytest --cov=chronicle --cov-report=term-missing`)
found real, reachable gaps in already-shipped code:

  - `chronicle.cli.main()` -- the actual `python -m chronicle` entry point
    (`chronicle/__main__.py` calls it directly) -- was never once invoked
    by name; every existing test calls the lower-level `run()` and asserts
    on a raised `SystemExit` instead of `main()`'s catch-and-convert
    wrapper.
  - `_npc_known()`'s fallback branches (relationship-subject-only,
    grudge-target-only, schedule-only, raw-record-only NPCs) and the
    matching `inspect` print branches (relationships/grudges "subject to",
    obligation debtor role, reputation "subject to").
  - `_resolve_run_and_subject`/`_resolve_positional_run`/`_resolve_at`'s
    conflict and missing-argument error paths.
  - `inject --event`'s write-path error branches and the registry-fallback
    branch identity lookup.

New fixture data lives in NPCs not touched by test_cli.py's existing
count-based assertions (`the_thalmor`, `jarl_balgruuf`, `proventus` are
already in that fixture but never inspected; `mikael`/`ashvard`/
`fresh_corpse` are new, added only here) so nothing here can make an
existing assertion flap.
"""

from __future__ import annotations

import json

import pytest

from chronicle.cli import main as cli_main
from chronicle.cli import run as cli_run
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.framelog import serialize_state
from chronicle.schedule import ScheduleBlock
from chronicle.social import form_relationship
from chronicle.tests.test_cli import _RUN_ID, _SAVE_UUID, _SEED, _build_run


@pytest.fixture
def run_dir(tmp_path):
    _build_run(tmp_path)
    return tmp_path


def _run_cli(capsys, argv: list[str]) -> tuple[int, str, str]:
    code = cli_run(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# ---------------------------------------------------------------------------
# main(): the actual entry point -- run() raises SystemExit, main() converts
# it. Nothing in test_cli.py/test_agent_debug_cli.py ever calls main().
# ---------------------------------------------------------------------------


def test_main_converts_a_string_systemexit_to_stderr_plus_exit_code_1(tmp_path, capsys):
    code = cli_main(["--runs-dir", str(tmp_path), "inspect", "hulda", "--run", "no-such-run", "--at", "0"])
    captured = capsys.readouterr()
    assert code == 1
    assert "no such run" in captured.err

    # The un-converted form (what every other test in this project checks)
    # really does raise, proving the two entry points differ as described.
    with pytest.raises(SystemExit):
        cli_run(["--runs-dir", str(tmp_path), "inspect", "hulda", "--run", "no-such-run", "--at", "0"])


def test_main_passes_through_argparses_own_int_exit_code(capsys):
    # argparse itself raises SystemExit(2) for a malformed invocation --
    # this exercises main()'s `isinstance(exc.code, int)` branch, distinct
    # from the string-message branch above.
    code = cli_main(["not-a-real-subcommand"])
    assert code == 2


def test_main_returns_zero_on_success(run_dir, capsys):
    code = cli_main(["--runs-dir", str(run_dir), "inspect", "hulda", "--run", _RUN_ID, "--at", "10"])
    assert code == 0


# ---------------------------------------------------------------------------
# _resolve_run_and_subject / _resolve_positional_run / _resolve_at
# ---------------------------------------------------------------------------


def test_inspect_rejects_run_id_given_both_positionally_and_via_flag(run_dir, capsys):
    with pytest.raises(SystemExit, match="either positionally or via --run, not both"):
        cli_run(["--runs-dir", str(run_dir), "inspect", _RUN_ID, "hulda", "--run", _RUN_ID])


def test_inspect_rejects_a_missing_run_id_and_subject(tmp_path, capsys):
    with pytest.raises(SystemExit, match="need a run id and a npc_id"):
        cli_run(["--runs-dir", str(tmp_path), "inspect", "hulda"])


def test_feed_rejects_run_id_given_both_positionally_and_via_flag(run_dir, capsys):
    with pytest.raises(SystemExit, match="either positionally or via --run, not both"):
        cli_run(["--runs-dir", str(run_dir), "feed", _RUN_ID, "--run", _RUN_ID])


def test_feed_rejects_a_missing_run_id(tmp_path, capsys):
    with pytest.raises(SystemExit, match="feed needs a run id"):
        cli_run(["--runs-dir", str(tmp_path), "feed"])


def test_inspect_without_at_on_a_run_with_zero_records_fails_clearly(tmp_path, capsys):
    # A run directory that exists but has never had a record written --
    # _max_tick() has nothing to report, so --at has no default to fall
    # back to.
    Driver(run_id="empty-run", seed_id=_SEED, save_uuid=_SAVE_UUID, generation=0, runs_dir=tmp_path).close()
    with pytest.raises(SystemExit, match="run has no records yet -- pass --at explicitly"):
        cli_run(["--runs-dir", str(tmp_path), "inspect", "hulda", "--run", "empty-run"])


# ---------------------------------------------------------------------------
# _npc_known()'s fallback branches + inspect's "subject to" print paths
# ---------------------------------------------------------------------------


def test_inspect_reports_the_grudge_target_side_for_an_npc_known_only_that_way(run_dir, capsys):
    # the_thalmor is grudge-1's target and nothing else in the fixture: no
    # beliefs, no relationships, not an obligation party -- only reachable
    # via _npc_known()'s grudge-target fallback, and only printed via
    # inspect's "grudges subject to" loop.
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(run_dir), "inspect", "the_thalmor", "--run", _RUN_ID, "--at", "10"])
    assert code == 0
    assert "beliefs (0)" in out
    assert "  (none)" in out  # the empty-beliefs branch
    assert "grudges subject to (1)" in out
    assert "held by hulda: murder" in out


def test_inspect_reports_the_relationship_target_side(run_dir, capsys):
    # jarl_balgruuf is relationship-1's to_id (hulda -> jarl_balgruuf) --
    # exercises the "relationships subject to" print branch specifically,
    # distinct from the "relationships held" branch every other test uses.
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(run_dir), "inspect", "jarl_balgruuf", "--run", _RUN_ID, "--at", "10"])
    assert code == 0
    assert "relationships subject to (1)" in out
    assert "<- hulda basis=colocation" in out


def test_inspect_reports_obligation_debtor_role_and_reputation_subject_side(run_dir, capsys):
    # proventus is obligation-1's debtor and reputation-1's subject --
    # neither the "debtor" role branch nor "reputations subject to" is
    # exercised by any existing test (both only ever inspect the issuer/
    # observer side).
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(run_dir), "inspect", "proventus", "--run", _RUN_ID, "--at", "10"])
    assert code == 0
    assert "[debtor] obligation-1: manage the treasury" in out
    assert "reputations subject to (as subject) (1)" in out
    assert "by hulda in 'stewardship'" in out


def test_inspect_reports_an_npc_known_only_via_a_schedule_block(tmp_path, capsys):
    driver = Driver(
        run_id="schedule-only-run",
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=(ScheduleBlock(npc_id="mikael", location_id="bannered_mare", start_tick=0, end_tick=5),),
        runs_dir=tmp_path,
    )
    driver.run(0, 1)
    # state_at()'s schedule field comes from the nearest keyframe (schema
    # §5), not the driver's live in-memory schedule -- write one so tick 0
    # has a keyframe to reconstruct from (the default keyframe_interval is
    # 24 ticks, too coarse for this 1-tick run to get one automatically).
    driver.writer.write_keyframe(tick=0, state=serialize_state(driver.claims, driver.social, driver.schedule, tick=0))
    driver.close()
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(tmp_path), "inspect", "mikael", "--run", "schedule-only-run", "--at", "0"])
    assert code == 0
    assert "beliefs (0)" in out
    assert "relationships held (0)" in out


def test_inspect_reports_an_npc_known_only_via_a_raw_event_field(tmp_path, capsys):
    driver = Driver(run_id="raw-record-only-run", seed_id=_SEED, save_uuid=_SAVE_UUID, generation=0, runs_dir=tmp_path)
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid=_SAVE_UUID, generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="a_random_bandit",
            cause="killed in a duel", killer_id="a_nameless_assassin", location_id=None,
        ),
    )
    driver.close()
    # a_nameless_assassin never holds a belief, relationship, grudge,
    # obligation, or schedule block -- the *only* record naming them is
    # this event's killer_id field, reached solely by _npc_known()'s
    # final raw-stream scan.
    code, out, _err = _run_cli(
        capsys, ["--runs-dir", str(tmp_path), "inspect", "a_nameless_assassin", "--run", "raw-record-only-run", "--at", "0"]
    )
    assert code == 0
    assert "beliefs (0)" in out


def test_inspect_reports_an_npc_known_only_as_a_relationship_target_with_nothing_else(tmp_path, capsys):
    # Unlike jarl_balgruuf above (already known via obligations_involving
    # before _npc_known() ever reaches the relationship-target fallback),
    # ysolda here has NO other record at all -- isolating the exact
    # fallback branch (social._relationships, r.to_id == npc_id) rather
    # than merely exercising the print path it feeds.
    driver = Driver(run_id="rel-target-only-run", seed_id=_SEED, save_uuid=_SAVE_UUID, generation=0, runs_dir=tmp_path)
    driver.social.add_relationship(
        form_relationship(id="rel-x", from_id="hulda", to_id="ysolda", basis="colocation", basis_id=None, strength=0.3, gamets=0.0)
    )
    driver.writer.write_keyframe(tick=0, state=serialize_state(driver.claims, driver.social, driver.schedule, tick=0))
    driver.close()
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(tmp_path), "inspect", "ysolda", "--run", "rel-target-only-run", "--at", "0"])
    assert code == 0
    assert "relationships subject to (1)" in out


def test_inspect_reports_an_npc_known_only_via_a_reputation_record(tmp_path, capsys):
    # carlotta is only ever a reputation subject -- no beliefs, no
    # relationships/grudges/obligations on either side -- isolating
    # _npc_known()'s final reputation-only fallback branch.
    driver = Driver(run_id="reputation-only-run", seed_id=_SEED, save_uuid=_SAVE_UUID, generation=0, runs_dir=tmp_path)
    driver.social.update_reputation(observer_id="hulda", subject_id="carlotta", context="honesty", kind="witnessed", positive=True, gamets=0.0)
    driver.writer.write_keyframe(tick=0, state=serialize_state(driver.claims, driver.social, driver.schedule, tick=0))
    driver.close()
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(tmp_path), "inspect", "carlotta", "--run", "reputation-only-run", "--at", "0"])
    assert code == 0
    assert "reputations subject to (as subject) (1)" in out


def test_inspect_unknown_npc_is_rejected_even_with_records_in_the_run(run_dir, capsys):
    with pytest.raises(SystemExit, match="unknown npc 'nobody-by-this-name'"):
        cli_run(["--runs-dir", str(run_dir), "inspect", "nobody-by-this-name", "--run", _RUN_ID, "--at", "10"])


# ---------------------------------------------------------------------------
# inject --event: the write path's own error branches
# ---------------------------------------------------------------------------


def test_inject_event_rejects_a_non_object_json_payload(run_dir, capsys):
    code, _out, err = _run_cli(capsys, ["--runs-dir", str(run_dir), "inject", _RUN_ID, "--event", json.dumps([1, 2, 3])])
    assert code == 1
    assert "--event must be a JSON object" in err


def test_inject_event_rejects_a_payload_missing_tick_and_gamets(run_dir, capsys):
    event = {"event_type": "npc_died", "npc_id": "x", "cause": "y", "killer_id": None, "location_id": None}
    code, _out, err = _run_cli(capsys, ["--runs-dir", str(run_dir), "inject", _RUN_ID, "--event", json.dumps(event)])
    assert code == 1
    assert "must carry a tick or gamets" in err


def test_inject_event_rejects_unknown_fields(run_dir, capsys):
    event = {
        "event_type": "npc_died", "tick": 11, "npc_id": "x", "cause": "y",
        "killer_id": None, "location_id": None, "not_a_real_field": True,
    }
    code, _out, err = _run_cli(capsys, ["--runs-dir", str(run_dir), "inject", _RUN_ID, "--event", json.dumps(event)])
    assert code == 1
    assert "unknown field(s) for 'npc_died': not_a_real_field" in err


def test_inject_compose_path_rejects_a_non_object_payload(run_dir, capsys):
    code, _out, err = _run_cli(
        capsys,
        ["--runs-dir", str(run_dir), "inject", "--run", _RUN_ID, "--at", "10", "--type", "npc_died", "--payload", json.dumps([1])],
    )
    assert code == 1
    assert "--payload must be a JSON object" in err


def test_inject_compose_path_rejects_actor_conflicting_with_payload(run_dir, capsys):
    payload = json.dumps({"npc_id": "someone_else", "cause": "unknown", "killer_id": None, "location_id": None})
    code, _out, err = _run_cli(
        capsys,
        [
            "--runs-dir", str(run_dir), "inject", "--run", _RUN_ID, "--at", "10",
            "--type", "npc_died", "--actor", "hulda", "--payload", payload,
        ],
    )
    assert code == 1
    assert "conflicts with payload['npc_id']" in err


# ---------------------------------------------------------------------------
# _branch_identity()'s registry fallback (no records in either stream,
# identity comes from runs/index.json instead of a record envelope).
# ---------------------------------------------------------------------------


def test_inject_event_reads_branch_identity_from_the_registry_when_the_run_has_no_records(tmp_path, capsys):
    driver = Driver(run_id="registry-only-run", seed_id=_SEED, save_uuid=_SAVE_UUID, generation=0, runs_dir=tmp_path)
    driver.close()  # registers runs/index.json; zero records written

    event = {"event_type": "npc_died", "tick": 0, "npc_id": "x", "cause": "y", "killer_id": None, "location_id": None}
    code, out, _err = _run_cli(capsys, ["--runs-dir", str(tmp_path), "inject", "registry-only-run", "--event", json.dumps(event)])
    assert code == 0
    assert "injected npc_died seq=0 tick=0" in out


def test_inject_event_fails_clearly_when_neither_records_nor_registry_can_identify_the_branch(tmp_path, capsys):
    run_dir = tmp_path / "ghost-run"
    run_dir.mkdir()
    (run_dir / "events.jsonl").write_text("")
    (run_dir / "trace.jsonl").write_text("")
    (run_dir / "index.json").write_text(json.dumps({"schema_version": 1, "streams": {"events": {"tick_offsets": {}, "keyframe_offsets": []}, "trace": {"tick_offsets": {}}}}))
    event = {"event_type": "npc_died", "tick": 0, "npc_id": "x", "cause": "y", "killer_id": None, "location_id": None}
    with pytest.raises(SystemExit, match="has no records and no registry entry"):
        cli_run(["--runs-dir", str(tmp_path), "inject", "ghost-run", "--event", json.dumps(event)])
