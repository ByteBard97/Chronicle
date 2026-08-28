"""Bring up and tear down a live ChronicleBridge session on a target machine.

Design: ``docs/design/live-test-harness.md`` §2.1 / §2.3 / §2.5. Everything
game-facing goes through DevBench (``devbench.py``); where the game runs is
a ``targets.Target``. Never X11, never keystrokes -- under Wine neither
reaches the game, and touching the window can pause the simulation.
"""

from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .devbench import DevBench, DevBenchError
from .targets import Target

REPO_ROOT = Path(__file__).resolve().parents[3]
LISTENER_SCRIPT = REPO_ROOT / "adapters" / "skyrim" / "listener" / "listener.py"
GLOBALS_JSON = REPO_ROOT / "tools" / "chronicle-patcher" / "out" / "chronicle-globals.json"

LISTENER_PORT = 8765
BOOTSTRAP_CELL = "WhiterunOrigin"

AE_UPSELL_MARKER = "Anniversary Edition"
# Modal bodies the harness may answer on its own (substring, button to press).
SAFE_MODALS: tuple[tuple[str, str], ...] = (
    ("load order has changed", "Ok"),
    ("relies on content that is no longer present", "Yes"),
    ("This save relies on content", "Yes"),
)


class PreflightError(RuntimeError):
    pass


class UnsafeModal(RuntimeError):
    pass


def _port_listening(port: int) -> bool:
    out = subprocess.run(["ss", "-ltn"], capture_output=True, text=True, check=False).stdout
    return any(line.split()[3].endswith(f":{port}") for line in out.splitlines()[1:] if line.split())


def preflight(target: Target) -> None:
    """Fail fast, before anything is launched, with the fix in the message."""
    problems: list[str] = []
    for label, path in (("listener", LISTENER_SCRIPT), ("avoidance globals JSON", GLOBALS_JSON)):
        if not path.exists():
            problems.append(f"{label} missing: {path}")
    if _port_listening(LISTENER_PORT):
        problems.append(f"something is already listening on :{LISTENER_PORT} -- a stale listener; stop it")
    if _port_listening(8920):
        problems.append("something is already listening on :8920 -- a DevBench/tunnel from another session; stop it")
    problems.extend(target.preflight())
    if problems:
        raise PreflightError(f"live preflight failed (target={target.name}):\n  - " + "\n  - ".join(problems))


# --- listener (always on this box) -----------------------------------------


@dataclass
class Listener:
    run_id: str
    runs_dir: Path
    secret: str
    snapshot_path: Path
    log_path: Path
    port: int = LISTENER_PORT
    proc: subprocess.Popen | None = None

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> None:
        env = dict(os.environ, CHRONICLE_RUNS_DIR=str(self.runs_dir))
        cmd = [
            "uv", "run", "--with", "pydantic", "python", str(LISTENER_SCRIPT),
            "--live-run", self.run_id, "--shared-secret", self.secret,
            "--port", str(self.port), "--snapshot-path", str(self.snapshot_path),
        ]
        self.proc = subprocess.Popen(cmd, cwd=REPO_ROOT, env=env, stdout=subprocess.DEVNULL, stderr=self.log_path.open("ab"))

    def get(self, path: str) -> tuple[int, bytes]:
        import urllib.error
        import urllib.request

        req = urllib.request.Request(self.url + path, headers={"X-Chronicle-Bridge-Token": self.secret})
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status, resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def wait_ready(self, timeout_s: float = 30.0) -> None:
        deadline = time.monotonic() + timeout_s
        last = "no response"
        while time.monotonic() < deadline:
            if self.proc is not None and self.proc.poll() is not None:
                raise RuntimeError(f"listener exited early (rc={self.proc.returncode}); see {self.log_path}")
            try:
                status, body = self.get("/whiterun/hydration")
                if status == 200:
                    return
                last = f"HTTP {status}: {body[:200]!r}"
            except OSError as exc:
                last = repr(exc)
            time.sleep(0.5)
        raise TimeoutError(f"listener not ready after {timeout_s}s ({last}); see {self.log_path}")

    def stop(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.send_signal(signal.SIGINT)
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def log_text(self) -> str:
        return self.log_path.read_text(errors="replace") if self.log_path.exists() else ""


def create_empty_run(run_id: str, runs_dir: Path) -> None:
    """The only empty-run recipe in the repo (chronicle/tests/test_devbench_runbook_seeding.py)."""
    from chronicle.driver import Driver

    Driver(run_id=run_id, seed_id="livetest", save_uuid=f"livetest-{run_id}", generation=0, runs_dir=runs_dir).close()


def bridge_ini_text(*, host: str, port: int, secret: str, log_level: str = "debug") -> str:
    return f"[General]\nHost={host}\nPort={port}\nSharedSecret={secret}\nLogLevel={log_level}\n"


# --- game -------------------------------------------------------------------


@dataclass
class Game:
    target: Target
    launch_log: Path
    db: DevBench

    def launch(self) -> None:
        self.target.launch(self.launch_log)

    def wait_devbench(self, timeout_s: float = 120.0) -> dict:
        deadline = time.monotonic() + timeout_s
        last = "unreachable"
        while time.monotonic() < deadline:
            try:
                health = self.db.health()
                if health.get("ok"):
                    return health
                last = repr(health)
            except DevBenchError as exc:
                last = str(exc)
            if not self.target.game_running() and time.monotonic() - deadline > -timeout_s + 30:
                raise RuntimeError(f"game process not running on {self.target.name} 30s after launch; see {self.launch_log}")
            time.sleep(2)
        raise TimeoutError(f"DevBench not reachable after {timeout_s}s ({last})")

    def wait_data_loaded(self, timeout_s: float = 120.0) -> None:
        self.db.wait_until(
            lambda: self.db.health().get("lastLifecycle") == "dataLoaded",
            timeout_s=timeout_s, poll_s=2.0, what="lastLifecycle == dataLoaded",
        )

    def shutdown(self, timeout_s: float = 30.0) -> None:
        if self.target.game_running():
            try:
                self.db.console("qqq")
            except DevBenchError:
                pass
            deadline = time.monotonic() + timeout_s
            while self.target.game_running() and time.monotonic() < deadline:
                time.sleep(2)
        self.target.kill_game()
        self.target.close()


# --- modals + bootstrap -----------------------------------------------------


def dismiss_modals(db: DevBench) -> list[str]:
    """Answer known-safe message boxes; refuse anything else (design §2.3)."""
    dismissed: list[str] = []
    for _ in range(5):
        if not db.menu_list().get("messageBoxOpen"):
            return dismissed
        try:
            box = db.call_retry("menu", deadline_s=10, action="describe")
        except DevBenchError:
            return dismissed  # main thread busy; caller polls again
        body = box.get("bodyText", "")
        buttons = box.get("buttons", [])
        if AE_UPSELL_MARKER in body:
            raise UnsafeModal(
                "the Anniversary Edition upsell MessageBox is open -- it must be suppressed at the "
                "config level before running the live suite (docs/design/live-test-harness.md §2.5)"
            )
        for marker, button in SAFE_MODALS:
            if marker.lower() in body.lower() and button in buttons:
                db.menu_accept(index=buttons.index(button))
                dismissed.append(body)
                time.sleep(1.0)
                break
        else:
            raise UnsafeModal(f"unexpected MessageBox {buttons!r}: {body!r}")
    return dismissed


def bootstrap(db: DevBench, *, cell: str = BOOTSTRAP_CELL, timeout_s: float = 180.0) -> None:
    """From the main menu into a loaded Whiterun via ``coc`` -- retried once (§2.1 step 6)."""
    dismiss_modals(db)
    db.console(f"coc {cell}")
    deadline = time.monotonic() + timeout_s
    retried = False
    while time.monotonic() < deadline:
        time.sleep(3)
        try:
            dismiss_modals(db)
            if db.state().get("playerLoaded"):
                break
        except DevBenchError:
            pass  # 504 during the load screen is expected
        if not retried and time.monotonic() > deadline - timeout_s / 2:
            db.console(f"coc {cell}")
            retried = True
    else:
        raise TimeoutError(f"player not loaded {timeout_s}s after coc {cell}")
    db.wait_until(lambda: "HUD Menu" in db.menu_list().get("openMenus", []), timeout_s=30, what="HUD Menu open")
    dismiss_modals(db)
    ok, frames = db.wait_frames(min_frames=30, within_s=2.0)
    if not ok:
        raise RuntimeError(f"game is not simulating (only {frames} frames in 2s) -- a modal, the console, or window focus is pausing it")
