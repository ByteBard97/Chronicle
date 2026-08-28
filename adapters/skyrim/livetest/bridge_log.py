"""Reader for ``ChronicleBridge.log`` (and the plain-text logs beside it).

The bridge logs through spdlog, one line per record::

    [2026-08-28 14:12:06.024] [log] [info] [plugin.cpp:237] ChronicleBridge loaded ...

``devbench.log`` and ``skse64.log`` are unstructured, and the file may not
exist yet when a fixture first asks for it, so every entry point tolerates
both: a line that doesn't match keeps its whole text as ``message`` with
``level``/``source`` left ``None``, and a missing file reads as empty.

The reader is stateless with respect to the file -- it re-reads on every call
so a log the game is still appending to is always seen fresh. ``mark()`` /
``since()`` give "what happened after this point" without holding a handle.
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

LEVELS = ("trace", "debug", "info", "warning", "warn", "error", "critical", "off")

_TAIL_LINES = 20

_LINE_RE = re.compile(
    r"^\[(?P<ts>[^\]]+)\]\s+\[[^\]]*\]\s+\[(?P<level>" + "|".join(LEVELS) + r")\]\s+\[(?P<source>[^\]]*)\]\s+(?P<message>.*)$"
)


@dataclass(frozen=True)
class LogLine:
    """One parsed log record. ``level``/``source`` are ``None`` for unstructured lines."""

    ts: str
    level: str | None
    source: str | None
    message: str
    raw: str


def parse_line(raw: str) -> LogLine:
    """Parse one spdlog line, falling back to the whole text as the message."""
    match = _LINE_RE.match(raw)
    if match is None:
        return LogLine(ts="", level=None, source=None, message=raw, raw=raw)
    return LogLine(
        ts=match.group("ts"),
        level=match.group("level").lower(),
        source=match.group("source"),
        message=match.group("message"),
        raw=raw,
    )


class BridgeLog:
    """Grep anchors and wait-for-line over a log file that may not exist yet."""

    def __init__(self, path: Path, *, refresh: Callable[[], None] | None = None) -> None:
        self.path = Path(path)
        #: Optional hook run before every read -- e.g. re-syncing the log from
        #: the machine the game runs on. Every query goes through ``lines()``,
        #: so each ``wait_for`` poll re-syncs too.
        self.refresh = refresh

    def lines(self) -> list[LogLine]:
        """Every non-blank line, re-read from disk. ``[]`` when the file is missing."""
        if self.refresh is not None:
            self.refresh()
        try:
            text = self.path.read_text(encoding="utf-8", errors="replace")
        except (FileNotFoundError, NotADirectoryError, IsADirectoryError, PermissionError):
            return []
        return [parse_line(raw) for raw in (line.rstrip("\r") for line in text.splitlines()) if raw.strip()]

    def mark(self) -> int:
        """The current line count -- pass it to ``since``/``find`` as a "from here on" anchor."""
        return len(self.lines())

    def since(self, mark: int) -> list[LogLine]:
        """Lines appended after ``mark``."""
        return self.lines()[max(mark, 0) :]

    def find(self, substr: str, *, since: int = 0) -> list[LogLine]:
        """Every line whose text contains ``substr`` (matched against the raw line)."""
        return [line for line in self.since(since) if substr in line.raw]

    def contains(self, substr: str, *, since: int = 0) -> bool:
        """Whether any line contains ``substr``."""
        return bool(self.find(substr, since=since))

    def wait_for(self, substr: str, *, timeout_s: float, poll_s: float = 1.0, since: int = 0) -> LogLine:
        """Block until a line containing ``substr`` appears; raise ``TimeoutError`` with the tail."""
        deadline = time.monotonic() + timeout_s
        while True:
            hits = self.find(substr, since=since)
            if hits:
                return hits[0]
            if time.monotonic() >= deadline:
                break
            time.sleep(poll_s)
        raise TimeoutError(self._timeout_message(substr, timeout_s, since))

    def by_level(self, level: str, *, since: int = 0) -> list[LogLine]:
        """Lines at exactly ``level`` (case-insensitive)."""
        wanted = level.strip().lower()
        return [line for line in self.since(since) if line.level == wanted]

    def errors(self, since: int = 0) -> list[LogLine]:
        """``[error]`` (and ``[critical]``) lines."""
        return [line for line in self.since(since) if line.level in ("error", "critical")]

    def warnings(self, since: int = 0) -> list[LogLine]:
        """``[warning]`` lines -- spdlog's short spelling ``[warn]`` counts too."""
        return [line for line in self.since(since) if line.level in ("warning", "warn")]

    def _timeout_message(self, substr: str, timeout_s: float, since: int) -> str:
        tail = self.since(since)[-_TAIL_LINES:]
        rendered = "\n".join(f"  {line.raw}" for line in tail) or "  (no lines)"
        return (
            f"{substr!r} did not appear in {self.path} within {timeout_s}s "
            f"(searching from line {since}). Last {len(tail)} line(s):\n{rendered}"
        )
