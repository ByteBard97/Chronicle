"""Regression test for tools/chronicle-devbench-runbook.py's seeding recipe.

Locks in a real bug found and fixed on 2026-08-27: id-generation for the
seeded claim/belief/evidence records was originally keyed off
``Driver._auto_ids``, a counter rebased only from existing *grudge* ids
(see that script's ``_resume_driver`` docstring). A bystander seed
(``self_victim=False``) creates a belief but no grudge, so the counter
doesn't advance past it -- a second seed call afterward then reused the
same id suffix and collided on ``claim_id``, raising a real
"second witness disagrees on N slots" error from ``ClaimStore``. Fixed by
keying the id suffix on the injected event's own monotonic ``seq``
instead. This test reproduces the exact failing sequence (a grudge seed,
then a bystander seed, then two more grudge seeds against the same run)
and asserts all four succeed.

The script's filename has a hyphen (matching this project's other
``tools/`` scripts), so it isn't importable as a normal module -- loaded
via ``importlib.util`` from its file path, the same technique this
project's own review process used to verify the fix by hand before this
test existed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_TOOLS_SCRIPT = Path(__file__).resolve().parents[2] / "tools" / "chronicle-devbench-runbook.py"


def _load_devbench_runbook_module():
    spec = importlib.util.spec_from_file_location("chronicle_devbench_runbook", _TOOLS_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def devbench_runbook():
    return _load_devbench_runbook_module()


def _make_fresh_run(run_id: str, runs_dir: Path) -> None:
    from chronicle.driver import Driver

    driver = Driver(run_id=run_id, seed_id="devbench-test-seed", save_uuid="devbench-test-save", generation=0, runs_dir=runs_dir)
    driver.close()


def test_sequential_seed_calls_do_not_collide(devbench_runbook, tmp_path):
    """The exact failing sequence this bug was found with: grudge, bystander, grudge, grudge."""
    run_id = "seed-collision-regression"
    _make_fresh_run(run_id, tmp_path)

    calls = [
        {"witness_id": "npc_a", "perpetrator_id": "npc_b", "self_victim": True, "location_id": "whiterun", "gamets": 10.0},
        {"witness_id": "npc_c", "perpetrator_id": "unknown", "self_victim": False, "location_id": "whiterun", "gamets": 20.0},
        {"witness_id": "npc_d", "perpetrator_id": "the_player", "self_victim": True, "location_id": "warmaidens", "gamets": 30.0},
        {"witness_id": "npc_e", "perpetrator_id": "the_player", "self_victim": True, "location_id": "warmaidens", "gamets": 40.0},
    ]
    for call in calls:
        ok, message = devbench_runbook.seed_crime_witnessed_grudge(
            run_id=run_id,
            runs_dir=str(tmp_path),
            crime_type="theft",
            **call,
        )
        assert ok, f"seeding {call} failed: {message}"


def test_npc_pair_grudge_clears_avoidance_and_markup_thresholds(devbench_runbook, tmp_path):
    """The hydration/avoidance/vendor-markup shape: witness is the victim, so rule 12 fires."""
    from chronicle.driver import AVOIDANCE_GRUDGE_THRESHOLD
    from chronicle.vendor_markup import MARKUP_SEVERITY_FLOOR

    run_id = "npc-pair-grudge"
    _make_fresh_run(run_id, tmp_path)

    ok, message = devbench_runbook.seed_crime_witnessed_grudge(
        run_id=run_id,
        runs_dir=str(tmp_path),
        witness_id="npc_a",
        perpetrator_id="npc_b",
        crime_type="assault",
        self_victim=True,
        location_id="whiterun",
        gamets=10.0,
    )
    assert ok, message

    from chronicle.framelog import FrameLogReader

    state = FrameLogReader(tmp_path / run_id).state_at(10)
    grudge = state.social.grudge("npc_a", "npc_b")
    assert grudge is not None
    assert grudge.severity >= AVOIDANCE_GRUDGE_THRESHOLD
    assert grudge.severity >= MARKUP_SEVERITY_FLOOR


def test_bystander_witness_forms_belief_without_grudge(devbench_runbook, tmp_path):
    """The diegetic-evidence shape: victim_id=None, no grudge cascade, belief clears the threshold."""
    from chronicle.diegetic_evidence import EVIDENCE_CONFIDENCE_THRESHOLD

    run_id = "bystander-belief"
    _make_fresh_run(run_id, tmp_path)

    ok, message = devbench_runbook.seed_crime_witnessed_grudge(
        run_id=run_id,
        runs_dir=str(tmp_path),
        witness_id="npc_c",
        perpetrator_id="unknown",
        crime_type="theft",
        self_victim=False,
        location_id="whiterun",
        gamets=20.0,
    )
    assert ok, message

    from chronicle.framelog import FrameLogReader

    state = FrameLogReader(tmp_path / run_id).state_at(20)
    beliefs = state.claims.beliefs_of("npc_c")
    assert len(beliefs) == 1
    assert beliefs[0].confidence >= EVIDENCE_CONFIDENCE_THRESHOLD
    assert state.social.grudge("npc_c", "unknown") is None
