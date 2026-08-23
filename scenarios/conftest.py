"""Scenario-suite wiring for the frame log.

Every scenario runs through chronicle.driver.Driver, which writes a frame
log per run (docs/frame-log-schema.md). The runs directory is overridable
via CHRONICLE_RUNS_DIR -- the one env var shared by pytest and the
dashboard (ui-spec §1.2) -- so this fixture points it at a per-test tmp
dir: scenario runs exercise the same env-var contract the dashboard reads,
without polluting the repo's real runs/ directory.
"""

import pytest


@pytest.fixture(autouse=True)
def _runs_dir_per_test(tmp_path, monkeypatch):
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path / "runs"))
    return tmp_path / "runs"
