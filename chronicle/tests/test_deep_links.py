"""Proof that scenarios/conftest.py's deep-link mechanism actually surfaces a
dashboard URL on a failing scenario assertion (docs/dashboard-build-plan.md
§2 M1 acceptance: "a deliberately-failed scenario assertion's output
contains a correctly-formed deep link").

This runs an isolated pytest process (subprocess, not the in-process
`pytester` plugin -- keeping this lane's dependency footprint at "no new
dependency without naming it," and `pytester` needs a `pytest_plugins`
declaration in a *root* conftest.py, which is outside this lane's file
boundary) against a scratch copy of the real scenarios/conftest.py plus a
one-off failing test, then greps its captured output for the URL.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from chronicle.claims import EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCENARIOS_CONFTEST = _REPO_ROOT / "scenarios" / "conftest.py"

_FAILING_TEST_TEMPLATE = '''
def test_deliberately_fails_with_deep_link_context(deep_link):
    deep_link.set(run="{run_id}", t=42, sel="npc:jarl_balgruuf", view="inspector")
    assert 1 == 2, "deliberate failure to prove the deep link lands in the output"
'''


def test_a_deliberately_failed_scenario_assertion_emits_a_correct_deep_link(tmp_path):
    # Build an actual frame log first -- ui-spec §1.2's "a pytest-emitted
    # deep link is therefore resolvable by construction" means the run_id
    # the link names must correspond to a real runs/<run_id>/ directory,
    # not just a string. This is the run a T0 scenario assertion would
    # have written before failing.
    runs_dir = tmp_path / "runs"
    run_id = "deeplink-demo-run"
    driver = Driver(run_id=run_id, seed_id="deeplink-demo-seed", save_uuid="deeplink-save-1", generation=0, runs_dir=runs_dir)
    driver.inject_event(
        NPCDied(
            tick=0, save_uuid="deeplink-save-1", generation=0, seq=1,
            gamets=0.0, wall_ts=0.0, npc_id="jarl_balgruuf",
            cause="assassination", killer_id=None, location_id="dragonsreach",
        ),
        origin={"kind": "scenario", "detail": "test_deep_links"},
    )
    driver.witness(
        claim_id="claim-jarl-death", belief_id="belief-1", evidence_id="evidence-1",
        kind="npc_death", slots={"perpetrator": "unknown", "cause": "assassination", "location": "dragonsreach"},
        canonical_event_key=EventKey("deeplink-save-1", 0, 1), witness_id="irileth", gamets=0.0,
    )
    driver.close()
    assert (runs_dir / run_id).exists()  # the log this run_id's deep link would resolve to

    scratch = tmp_path / "scenarios"
    scratch.mkdir()
    shutil.copy(_SCENARIOS_CONFTEST, scratch / "conftest.py")
    (scratch / "test_fail.py").write_text(_FAILING_TEST_TEMPLATE.format(run_id=run_id), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "test_fail.py", "-q"],
        cwd=scratch,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode != 0  # the test genuinely failed
    output = result.stdout + result.stderr
    assert "dashboard deep link" in output
    assert f"run={run_id}" in output
    assert "t=42" in output
    # sel's ":" is percent-encoded by urlencode -- "npc%3Ajarl_balgruuf".
    assert "sel=npc%3Ajarl_balgruuf" in output
    assert "view=inspector" in output
    assert "http://localhost:5173/?" in output
    # "Resolvable by construction" (ui-spec §1.2): the run_id the emitted
    # link names is a real run directory, not just a string this test made
    # up -- the dashboard, pointed at runs_dir, would actually find it.
    assert (runs_dir / run_id / "events.jsonl").exists()


def test_a_passing_scenario_assertion_emits_no_deep_link_noise(tmp_path):
    scratch = tmp_path / "scenarios"
    scratch.mkdir()
    shutil.copy(_SCENARIOS_CONFTEST, scratch / "conftest.py")
    (scratch / "test_pass.py").write_text(
        '''
def test_passes_after_registering_deep_link_context(deep_link):
    deep_link.set(run="deeplink-demo-run", t=1)
    assert 1 == 1
''',
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "test_pass.py", "-q"],
        cwd=scratch,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0
    assert "dashboard deep link" not in (result.stdout + result.stderr)


def test_a_failure_with_no_deep_link_context_registered_is_unaffected(tmp_path):
    scratch = tmp_path / "scenarios"
    scratch.mkdir()
    shutil.copy(_SCENARIOS_CONFTEST, scratch / "conftest.py")
    (scratch / "test_fail_no_context.py").write_text(
        '''
def test_fails_without_ever_calling_deep_link_set(deep_link):
    assert False
''',
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "test_fail_no_context.py", "-q"],
        cwd=scratch,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode != 0
    assert "dashboard deep link" not in (result.stdout + result.stderr)
