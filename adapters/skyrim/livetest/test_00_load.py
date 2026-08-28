"""Slice 00: the plugin loaded, configured itself, registered its sinks, and the listener is wired."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.live

REQUIRED_LINES = (
    "ChronicleBridge loaded --",
    "ChronicleBridge.ini loaded from",
    "sharedSecret=set",
    "TESDeathEvent sink registered",
    "MenuOpenCloseEvent (BarterMenu) sink registered",
    "BarterMenu PostCreate vtable-slot swap installed",
)


def test_bridge_startup_lines(live_session):
    log = live_session.bridge_log
    missing = [line for line in REQUIRED_LINES if not log.contains(line)]
    assert not missing, f"missing from ChronicleBridge.log: {missing}\n{log.path}"


def test_bridge_has_no_errors(live_session):
    errors = live_session.bridge_log.errors()
    assert not errors, "\n".join(line.raw for line in errors)


def test_bridge_talks_to_listener(live_session):
    """No non-2xx statuses once the listener was up (it was up before the game launched)."""
    bad = [line.raw for line in live_session.bridge_log.warnings() if "returned status" in line.message or "failed:" in line.message]
    assert not bad, "\n".join(bad)
    status, _ = live_session.listener.get("/whiterun/hydration")
    assert status == 200


def test_devbench_identity(live_session):
    state = live_session.db.state()
    assert state["playerLoaded"] is True
    assert state["exe"] == "SkyrimSE.exe"
    scene = live_session.db.scene()
    assert scene["worldspace"]["editorId"] == "WhiterunWorld", scene
