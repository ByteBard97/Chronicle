"""Where the game runs: the local Proton instance, or the owner's Windows machine over SSH.

The harness only needs a handful of operations from a target; everything
game-facing still goes through DevBench. ``CHRONICLE_LIVE_TARGET`` selects
``local`` (Proton instance on this box -- only when the owner says the
machine is free) or ``windows`` (default: SSH to the build/test machine).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from .ini import assert_keys_in_file

REPO_ROOT = Path(__file__).resolve().parents[3]


class Target(Protocol):
    name: str
    devbench_url: str

    def preflight(self) -> list[str]: ...
    def listener_host(self) -> str: ...
    def write_bridge_ini(self, text: str) -> None: ...
    def restore_bridge_ini(self) -> None: ...
    def launch(self, log: Path) -> None: ...
    def game_running(self) -> bool: ...
    def kill_game(self) -> None: ...
    def sync_logs(self, dest: Path) -> None: ...
    def bridge_log_path(self, dest: Path) -> Path: ...
    def close(self) -> None: ...


def _run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False, **kw)


# --- local Proton instance -------------------------------------------------


@dataclass
class LocalProtonTarget:
    name: str = "local"
    devbench_url: str = "http://127.0.0.1:8920"
    instance: Path = Path.home() / "Games" / "ChronicleDev"
    launch_script: Path = REPO_ROOT / "tools" / "launch-chronicledev-skse.sh"
    prefix_docs: Path = (
        Path.home()
        / ".local/share/Steam/steamapps/compatdata/4190904830/pfx/drive_c/users/steamuser/Documents/My Games/Skyrim Special Edition"
    )
    proc: subprocess.Popen | None = None
    _ini_backup: Path | None = None

    @property
    def plugin_dir(self) -> Path:
        return self.instance / "mods" / "ChronicleBridge" / "SKSE" / "Plugins"

    @property
    def ini_path(self) -> Path:
        return self.plugin_dir / "ChronicleBridge.ini"

    def preflight(self) -> list[str]:
        problems = []
        if os.environ.get("CHRONICLE_LIVE_LOCAL_OK") != "1":
            problems.append("local target needs CHRONICLE_LIVE_LOCAL_OK=1 -- the owner said not to launch Skyrim on this box (memory 2026-08-28)")
        for label, path in (
            ("launch script", self.launch_script),
            ("ChronicleBridge.dll", self.plugin_dir / "ChronicleBridge.dll"),
            ("ChroniclePatcher.esp", self.instance / "mods" / "ChroniclePatcherOutput" / "ChroniclePatcher.esp"),
            ("devbench.dll", self.instance / "mods" / "devbench" / "SKSE" / "Plugins" / "devbench.dll"),
        ):
            if not path.exists():
                problems.append(f"{label} missing: {path}")
        modlist = self.instance / "profiles" / "Default" / "modlist.txt"
        if modlist.exists() and any(line.strip() == "+EngineFixes" for line in modlist.read_text().splitlines()):
            problems.append("EngineFixes enabled in modlist.txt -- hangs SKSE plugin load without its preloader")
        if self.game_running():
            problems.append("SkyrimSE.exe already running")
        return problems

    def listener_host(self) -> str:
        return "127.0.0.1"

    def write_bridge_ini(self, text: str) -> None:
        if self.ini_path.exists():
            self._ini_backup = self.ini_path.with_suffix(".ini.livetest-backup")
            shutil.copy2(self.ini_path, self._ini_backup)
        self.ini_path.write_text(text)

    def restore_bridge_ini(self) -> None:
        if self._ini_backup and self._ini_backup.exists():
            shutil.move(self._ini_backup, self.ini_path)
        elif self.ini_path.exists():
            self.ini_path.unlink()

    def launch(self, log: Path) -> None:
        changes = assert_keys_in_file(self.instance / "profiles" / "Default" / "skyrim.ini")
        log.open("ab").write(f"[livetest] skyrim.ini: {changes or 'no changes'}\n".encode())
        self.proc = subprocess.Popen([str(self.launch_script)], cwd=REPO_ROOT, stdout=log.open("ab"), stderr=subprocess.STDOUT)

    def game_running(self) -> bool:
        return _run(["pgrep", "-f", r"SkyrimSE\.exe"]).returncode == 0

    def kill_game(self) -> None:
        for pattern in (r"SkyrimSE\.exe", r"ModOrganizer\.exe"):
            _run(["pkill", "-9", "-f", pattern])
        if self.proc and self.proc.poll() is None:
            try:
                self.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.proc.kill()

    def sync_logs(self, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        skse = self.prefix_docs / "SKSE"
        if skse.exists():
            for src in skse.iterdir():
                if src.is_file():
                    shutil.copy2(src, dest / src.name)

    def bridge_log_path(self, dest: Path) -> Path:
        return dest / "ChronicleBridge.log"

    def close(self) -> None:
        pass


# --- remote Windows machine over SSH ---------------------------------------


@dataclass
class RemoteWindowsTarget:
    """Game on the owner's Windows box; DevBench reached through an SSH local forward.

    Launch mechanism: ``launch_command`` is run through ``ssh`` and must start
    the game in the interactive desktop session (an SSH-spawned process lands
    in session 0 with no desktop). The concrete command is set from the
    machine inventory (``docs/design/live-test-harness.md`` §2.6) -- a
    scheduled task run with ``schtasks /run`` is the usual answer.
    """

    host: str = os.environ.get("CHRONICLE_WIN_HOST", "geoff@192.168.0.211")
    name: str = "windows"
    devbench_url: str = "http://127.0.0.1:8920"
    launch_command: str = os.environ.get("CHRONICLE_WIN_LAUNCH", "schtasks /run /tn ChronicleLiveLaunch")
    instance_win: str = os.environ.get("CHRONICLE_WIN_INSTANCE", r"C:\ChronicleDev")  # mirrored portable MO2 instance
    plugin_dir_win: str = os.environ.get("CHRONICLE_WIN_PLUGIN_DIR", r"C:\ChronicleDev\mods\ChronicleBridge\SKSE\Plugins")
    skse_log_dir_win: str = os.environ.get(
        "CHRONICLE_WIN_SKSE_LOGS", r"C:\Users\geoff\Documents\My Games\Skyrim Special Edition\SKSE"
    )
    skyrim_ini_win: str = os.environ.get("CHRONICLE_WIN_SKYRIM_INI", r"C:\ChronicleDev\profiles\Default\skyrim.ini")
    linux_lan_ip: str = os.environ.get("CHRONICLE_LINUX_LAN_IP", "")  # auto-detected in preflight when empty
    tunnel: subprocess.Popen | None = None
    _had_ini: bool | None = None
    _ini_win: str = field(default="", init=False)

    def ssh(self, command: str, timeout: float = 60) -> subprocess.CompletedProcess:
        return _run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", self.host, command], timeout=timeout)

    def _detect_lan_ip(self) -> str:
        """The source address this box uses to reach the Windows host (the bridge POSTs back to it)."""
        host_only = self.host.split("@", 1)[-1]
        out = _run(["ip", "-4", "route", "get", host_only]).stdout
        parts = out.split()
        return parts[parts.index("src") + 1] if "src" in parts else ""

    def preflight(self) -> list[str]:
        problems = []
        if not self.linux_lan_ip:
            self.linux_lan_ip = self._detect_lan_ip()
        if not self.linux_lan_ip:
            problems.append("could not detect this box's LAN IP; set CHRONICLE_LINUX_LAN_IP")
        probe = self.ssh("hostname")
        if probe.returncode != 0:
            problems.append(f"ssh {self.host} failed: {probe.stderr.strip()}")
            return problems
        for label, path in (
            ("ChronicleBridge.dll", f"{self.plugin_dir_win}\\ChronicleBridge.dll"),
            ("ModOrganizer.exe", f"{self.instance_win}\\ModOrganizer.exe"),
            ("Stock Game SkyrimSE.exe", f"{self.instance_win}\\Stock Game\\SkyrimSE.exe"),
            ("devbench.dll", f"{self.instance_win}\\mods\\devbench\\SKSE\\Plugins\\devbench.dll"),
            ("Skyrim.ini", self.skyrim_ini_win),
        ):
            if "True" not in self.ssh(f'Test-Path "{path}"').stdout:
                problems.append(f"{label} not at {path} on {self.host}")
        task = self.ssh("(Get-ScheduledTask -TaskName ChronicleLiveLaunch -ErrorAction SilentlyContinue).State")
        if not task.stdout.strip():
            problems.append("scheduled task ChronicleLiveLaunch missing on the Windows box (docs/design/live-test-harness.md §2.6)")
        if self.game_running():
            problems.append("SkyrimSE.exe already running on the Windows box")
        return problems

    def listener_host(self) -> str:
        return self.linux_lan_ip

    def write_bridge_ini(self, text: str) -> None:
        self._ini_win = f"{self.plugin_dir_win}\\ChronicleBridge.ini"
        self._had_ini = "True" in self.ssh(f'Test-Path "{self._ini_win}"').stdout
        if self._had_ini:
            self.ssh(f'Copy-Item "{self._ini_win}" "{self._ini_win}.livetest-backup" -Force')
        local = Path(os.environ.get("TMPDIR", "/tmp")) / "ChronicleBridge.livetest.ini"
        local.write_text(text)
        _run(["scp", "-q", str(local), f"{self.host}:{self._ini_win}"])

    def restore_bridge_ini(self) -> None:
        if not self._ini_win:
            return
        if self._had_ini:
            self.ssh(f'Move-Item "{self._ini_win}.livetest-backup" "{self._ini_win}" -Force')
        else:
            self.ssh(f'Remove-Item "{self._ini_win}" -Force -ErrorAction SilentlyContinue')

    def assert_skyrim_ini(self, log: Path) -> None:
        """Re-assert the unattended keys in the Windows profile's Skyrim.ini before every launch."""
        if not self.skyrim_ini_win:
            log.open("ab").write(b"[livetest] CHRONICLE_WIN_SKYRIM_INI unset -- skyrim.ini not asserted\n")
            return
        local = Path(os.environ.get("TMPDIR", "/tmp")) / "skyrim.livetest.ini"
        _run(["scp", "-q", f"{self.host}:{self.skyrim_ini_win}", str(local)])
        changes = assert_keys_in_file(local)
        if changes:
            _run(["scp", "-q", str(local), f"{self.host}:{self.skyrim_ini_win}"])
        log.open("ab").write(f"[livetest] skyrim.ini: {changes or 'no changes'}\n".encode())

    def launch(self, log: Path) -> None:
        self.assert_skyrim_ini(log)
        result = self.ssh(self.launch_command)
        log.open("ab").write((result.stdout + result.stderr).encode())
        if result.returncode != 0:
            raise RuntimeError(f"remote launch failed ({result.returncode}): {result.stderr.strip()}")
        self.tunnel = subprocess.Popen(
            ["ssh", "-o", "BatchMode=yes", "-o", "ExitOnForwardFailure=yes", "-N", "-L", "8920:127.0.0.1:8920", self.host]
        )
        time.sleep(2)

    def game_running(self) -> bool:
        out = self.ssh("Get-Process SkyrimSE -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id").stdout
        return out.strip() != ""

    def kill_game(self) -> None:
        self.ssh("Stop-Process -Name SkyrimSE,ModOrganizer -Force -ErrorAction SilentlyContinue")

    def sync_logs(self, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        _run(["scp", "-q", f"{self.host}:{self.skse_log_dir_win}\\*.log", str(dest)])

    def bridge_log_path(self, dest: Path) -> Path:
        return dest / "ChronicleBridge.log"

    def close(self) -> None:
        if self.tunnel and self.tunnel.poll() is None:
            self.tunnel.terminate()


def select_target() -> Target:
    which = os.environ.get("CHRONICLE_LIVE_TARGET", "windows")
    if which == "local":
        return LocalProtonTarget()
    if which == "windows":
        return RemoteWindowsTarget()
    raise ValueError(f"unknown CHRONICLE_LIVE_TARGET={which!r} (local|windows)")
