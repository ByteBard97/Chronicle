"""Session fixture for the live-game suite (docs/design/live-test-harness.md §2.1).

Opt-in: ``CHRONICLE_LIVE=1``. Everything else skips so ``make test`` can
never launch a game by accident. ``CHRONICLE_LIVE_TARGET`` picks where the
game runs (``windows`` default, ``local`` only with ``CHRONICLE_LIVE_LOCAL_OK=1``).
"""

from __future__ import annotations

import os
import secrets
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adapters.skyrim.livetest import harness, targets
from adapters.skyrim.livetest.bridge_log import BridgeLog
from adapters.skyrim.livetest.devbench import DevBench

LIVE = os.environ.get("CHRONICLE_LIVE") == "1"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "live: needs a real Skyrim process (CHRONICLE_LIVE=1)")


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    if LIVE:
        return
    skip = pytest.mark.skip(reason="set CHRONICLE_LIVE=1 to run against a live game")
    for item in items:
        item.add_marker(skip)


@dataclass
class LiveSession:
    db: DevBench
    listener: harness.Listener
    target: targets.Target
    run_id: str
    runs_dir: Path
    scratch: Path
    bridge_log: BridgeLog
    game: harness.Game
    _gamets: float = 0.0
    notes: list[str] = field(default_factory=list)

    @property
    def run_dir(self) -> Path:
        return self.runs_dir / self.run_id

    def next_gamets(self) -> float:
        """``chronicle inject`` refuses a tick below the run's max tick -- keep seeds monotonic."""
        self._gamets += 10.0
        return self._gamets

    def note(self, text: str) -> None:
        self.notes.append(text)
        print(f"[live] {text}")


def _scratch_root() -> Path:
    base = os.environ.get("CHRONICLE_LIVE_SCRATCH") or os.environ.get("TMPDIR") or "/tmp"
    root = Path(base) / "chronicle-live" / time.strftime("%Y%m%d-%H%M%S")
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture(scope="session")
def live_session() -> LiveSession:
    target = targets.select_target()
    harness.preflight(target)
    scratch = _scratch_root()
    run_id = f"live-{scratch.name}"
    runs_dir = scratch / "runs"
    harness.create_empty_run(run_id, runs_dir)

    secret = secrets.token_hex(16)
    listener = harness.Listener(
        run_id=run_id, runs_dir=runs_dir, secret=secret,
        snapshot_path=scratch / "positions.json", log_path=scratch / "listener.log",
    )
    logs_dir = scratch / "game-logs"
    game = harness.Game(target=target, launch_log=scratch / "launch.log", db=DevBench(target.devbench_url))
    session: LiveSession | None = None
    ini_written = False
    try:
        listener.start()
        listener.wait_ready()
        target.write_bridge_ini(harness.bridge_ini_text(host=target.listener_host(), port=listener.port, secret=secret))
        ini_written = True
        game.launch()
        game.wait_devbench()
        game.wait_data_loaded()
        harness.bootstrap(game.db)
        session = LiveSession(
            db=game.db, listener=listener, target=target, run_id=run_id, runs_dir=runs_dir, scratch=scratch,
            bridge_log=BridgeLog(target.bridge_log_path(logs_dir), refresh=lambda: target.sync_logs(logs_dir)),
            game=game,
        )
        session.note(f"session up: target={target.name} run={run_id} scratch={scratch}")
        yield session
    finally:
        game.shutdown()
        listener.stop()
        if ini_written:
            target.restore_bridge_ini()
        artifacts = scratch / "artifacts"
        artifacts.mkdir(exist_ok=True)
        try:
            target.sync_logs(artifacts / "game-logs")
        except Exception as exc:  # noqa: BLE001 -- best-effort evidence collection
            print(f"[live] log sync failed: {exc}")
        for extra in (listener.log_path, game.launch_log):
            if extra.exists():
                shutil.copy2(extra, artifacts / extra.name)
        if (runs_dir / run_id).exists():
            shutil.copytree(runs_dir / run_id, artifacts / run_id, dirs_exist_ok=True)
        print(f"\n[live] artifacts: {artifacts}")
        if session and session.notes:
            print("[live] notes:\n  " + "\n  ".join(session.notes))
