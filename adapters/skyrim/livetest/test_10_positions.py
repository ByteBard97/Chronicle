"""Slice 10: the spatial streamer posts live named-cast positions ~1 Hz that match the engine."""

from __future__ import annotations

import json
import math
import time

import pytest

from adapters.skyrim.livetest.cast import REFS

pytestmark = pytest.mark.live


def _snapshot(session) -> dict:
    return json.loads(session.listener.snapshot_path.read_text())


def test_snapshot_updates_at_about_one_hertz(live_session):
    path = live_session.listener.snapshot_path
    live_session.db.wait_until(path.exists, timeout_s=15, what="first positions snapshot")
    seen: set[float] = set()
    deadline = time.monotonic() + 6
    while time.monotonic() < deadline:
        seen.add(path.stat().st_mtime)
        time.sleep(0.25)
    assert len(seen) >= 3, f"snapshot mtime changed only {len(seen)} times in 6s"


def test_snapshot_contains_named_cast(live_session):
    npcs = _snapshot(live_session)["npcs"]
    ids = {n["id"] for n in npcs}
    named = ids & set(REFS)
    live_session.note(f"positions: {len(npcs)} npcs, {len(named)} named-cast: {sorted(named)}")
    assert len(named) >= 10, f"only {sorted(named)} resolved to named-cast ids"


def test_nazeem_position_matches_engine(live_session):
    ref = live_session.db.ref(REFS["nazeem"])
    assert ref, "Nazeem's reference not loaded"
    ex, ey, _ = ref["position"]
    npc = next((n for n in _snapshot(live_session)["npcs"] if n["id"] == "nazeem"), None)
    assert npc, "nazeem missing from the snapshot"
    dist = math.hypot(npc["x"] - ex, npc["y"] - ey)
    assert dist < 150, f"snapshot ({npc['x']:.0f},{npc['y']:.0f}) vs engine ({ex:.0f},{ey:.0f}): {dist:.0f} units apart"
