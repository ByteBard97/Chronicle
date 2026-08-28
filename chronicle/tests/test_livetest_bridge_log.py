"""Unit tests for the live-harness ChronicleBridge.log reader (no game needed).

The three sample lines below were copied verbatim out of a real
``ChronicleBridge.log`` produced by the first-boot spike on 2026-08-28, so the
parser is pinned against spdlog's actual layout rather than a guess at it. The
reader also has to survive ``devbench.log`` / ``skse64.log``, which are plain
unstructured lines.
"""

from __future__ import annotations

import dataclasses
import threading
import time

import pytest

from adapters.skyrim.livetest.bridge_log import BridgeLog, LogLine

BANNER = "[2026-08-28 14:12:06.024] [log] [info] [plugin.cpp:237] ChronicleBridge loaded -- spatial streamer + death-event + hydration-poll"
INI_LINE = r"[2026-08-28 14:12:06.024] [log] [info] [Config.cpp:35] ChronicleBridge.ini not found at Z:\home\geoff\Games\ChronicleDev\Stock Game\data\SKSE\Plugins\ChronicleBridge.ini -- using defaults (host=127.0.0.1, port=8765)"
WARNING = "[2026-08-28 14:12:14.031] [log] [warning] [OutboundClient.cpp:618] ChronicleBridge: GET 127.0.0.1:8765/whiterun/vendor-markup returned status 501"

SAMPLE = f"{BANNER}\n{INI_LINE}\n{WARNING}\n"


@pytest.fixture
def log(tmp_path):
    path = tmp_path / "ChronicleBridge.log"
    path.write_text(SAMPLE, encoding="utf-8")
    return BridgeLog(path)


def test_missing_file_reads_as_empty(tmp_path):
    reader = BridgeLog(tmp_path / "nope.log")
    assert reader.lines() == []
    assert reader.mark() == 0
    assert reader.find("anything") == []
    assert reader.contains("anything") is False
    assert reader.errors() == []


def test_path_is_a_public_attribute(tmp_path):
    path = tmp_path / "ChronicleBridge.log"
    assert BridgeLog(path).path == path


def test_refresh_hook_runs_before_every_read(tmp_path):
    """The log may be synced from the machine the game runs on before each query."""
    path = tmp_path / "ChronicleBridge.log"
    calls = {"n": 0}

    def sync():
        calls["n"] += 1
        path.write_text(BANNER + "\n", encoding="utf-8")

    reader = BridgeLog(path, refresh=sync)
    assert calls["n"] == 0
    assert len(reader.lines()) == 1
    assert calls["n"] == 1
    reader.contains("ChronicleBridge")
    reader.mark()
    assert calls["n"] == 3


def test_refresh_hook_runs_on_every_wait_for_poll(tmp_path):
    path = tmp_path / "ChronicleBridge.log"
    path.write_text(BANNER + "\n", encoding="utf-8")
    calls = {"n": 0}

    def sync():
        calls["n"] += 1
        if calls["n"] >= 3:
            path.write_text(BANNER + "\n" + WARNING + "\n", encoding="utf-8")

    reader = BridgeLog(path, refresh=sync)
    line = reader.wait_for("vendor-markup", timeout_s=5.0, poll_s=0.01)
    assert line.raw == WARNING
    assert calls["n"] >= 3


def test_refresh_defaults_to_none(log):
    assert log.refresh is None


def test_parses_the_banner_line(log):
    line = log.lines()[0]
    assert isinstance(line, LogLine)
    assert line.ts == "2026-08-28 14:12:06.024"
    assert line.level == "info"
    assert line.source == "plugin.cpp:237"
    assert line.message == "ChronicleBridge loaded -- spatial streamer + death-event + hydration-poll"
    assert line.raw == BANNER


def test_parses_a_message_containing_windows_paths_and_brackets(log):
    line = log.lines()[1]
    assert line.source == "Config.cpp:35"
    assert line.message.startswith("ChronicleBridge.ini not found at Z:\\home\\geoff")
    assert line.message.endswith("(host=127.0.0.1, port=8765)")


def test_parses_the_warning_line(log):
    line = log.lines()[2]
    assert line.level == "warning"
    assert line.source == "OutboundClient.cpp:618"
    assert "returned status 501" in line.message


def test_log_lines_are_frozen(log):
    with pytest.raises(dataclasses.FrozenInstanceError):
        log.lines()[0].level = "error"  # type: ignore[misc]


def test_non_matching_lines_are_kept_as_raw_messages(tmp_path):
    path = tmp_path / "skse64.log"
    path.write_text(
        "plugin ChronicleBridge.dll (00000001 ChronicleBridge 00000001) loaded correctly (handle 1)\n"
        "[not a real level] still not a match\n",
        encoding="utf-8",
    )
    lines = BridgeLog(path).lines()
    assert len(lines) == 2
    for line in lines:
        assert line.level is None
        assert line.source is None
        assert line.ts == ""
        assert line.message == line.raw


def test_blank_lines_are_dropped_and_crlf_is_stripped(tmp_path):
    path = tmp_path / "ChronicleBridge.log"
    path.write_bytes((BANNER + "\r\n" + "\r\n" + WARNING + "\r\n").encode("utf-8"))
    lines = BridgeLog(path).lines()
    assert [line.raw for line in lines] == [BANNER, WARNING]
    assert lines[0].message.endswith("hydration-poll")


def test_undecodable_bytes_do_not_break_the_reader(tmp_path):
    path = tmp_path / "ChronicleBridge.log"
    path.write_bytes(BANNER.encode("utf-8") + b" \xff\xfe\n")
    assert len(BridgeLog(path).lines()) == 1


def test_find_and_contains(log):
    assert log.contains("returned status 501") is True
    assert log.contains("not in this log") is False
    hits = log.find("ChronicleBridge")
    assert len(hits) == 3
    assert log.find("vendor-markup")[0].level == "warning"


def test_mark_and_since_only_see_new_lines(tmp_path):
    path = tmp_path / "ChronicleBridge.log"
    path.write_text(BANNER + "\n", encoding="utf-8")
    reader = BridgeLog(path)
    mark = reader.mark()
    assert mark == 1
    assert reader.since(mark) == []

    with path.open("a", encoding="utf-8") as handle:
        handle.write(WARNING + "\n")

    fresh = reader.since(mark)
    assert [line.raw for line in fresh] == [WARNING]
    assert reader.mark() == 2
    assert log_texts(reader.find("ChronicleBridge", since=mark)) == [WARNING]
    assert reader.contains("hydration-poll", since=mark) is False
    assert reader.contains("hydration-poll") is True


def log_texts(lines):
    return [line.raw for line in lines]


def test_by_level_errors_and_warnings(tmp_path):
    path = tmp_path / "ChronicleBridge.log"
    error = "[2026-08-28 14:13:00.000] [log] [error] [OutboundClient.cpp:99] ChronicleBridge: POST failed: connection refused"
    warn_short = "[2026-08-28 14:13:01.000] [log] [warn] [Poller.cpp:12] short spelling"
    path.write_text(f"{BANNER}\n{WARNING}\n{error}\n{warn_short}\n", encoding="utf-8")
    reader = BridgeLog(path)

    assert log_texts(reader.by_level("info")) == [BANNER]
    assert log_texts(reader.by_level("INFO")) == [BANNER]
    assert log_texts(reader.errors()) == [error]
    assert log_texts(reader.warnings()) == [WARNING, warn_short]
    assert log_texts(reader.errors(since=3)) == []


def test_wait_for_returns_immediately_when_already_present(log):
    line = log.wait_for("returned status 501", timeout_s=5.0, poll_s=0.01)
    assert line.raw == WARNING


def test_wait_for_sees_a_line_appended_by_another_thread(tmp_path):
    path = tmp_path / "ChronicleBridge.log"
    path.write_text(BANNER + "\n", encoding="utf-8")
    reader = BridgeLog(path)

    def append_later():
        time.sleep(0.15)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(WARNING + "\n")

    writer = threading.Thread(target=append_later)
    writer.start()
    try:
        line = reader.wait_for("vendor-markup", timeout_s=5.0, poll_s=0.02)
    finally:
        writer.join()
    assert line.raw == WARNING
    assert line.level == "warning"


def test_wait_for_respects_since(tmp_path):
    path = tmp_path / "ChronicleBridge.log"
    path.write_text(BANNER + "\n", encoding="utf-8")
    reader = BridgeLog(path)
    with pytest.raises(TimeoutError):
        reader.wait_for("hydration-poll", timeout_s=0.1, poll_s=0.02, since=1)


def test_wait_for_timeout_message_carries_the_tail(tmp_path):
    path = tmp_path / "ChronicleBridge.log"
    path.write_text("\n".join(f"[2026-08-28 14:12:0{i % 10}.000] [log] [info] [p.cpp:1] line {i}" for i in range(40)) + "\n", encoding="utf-8")
    reader = BridgeLog(path)
    with pytest.raises(TimeoutError) as excinfo:
        reader.wait_for("never appears", timeout_s=0.05, poll_s=0.01)
    message = str(excinfo.value)
    assert "never appears" in message
    assert str(reader.path) in message
    assert "line 39" in message
    assert "line 20" in message
    assert "line 19" not in message
