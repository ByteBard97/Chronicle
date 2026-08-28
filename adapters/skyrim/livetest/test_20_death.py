"""Slice 20: a named-cast death reaches the run's events.jsonl as ``npc_died``."""

from __future__ import annotations

import json
import time

import pytest

from adapters.skyrim.livetest.cast import REFS

pytestmark = pytest.mark.live

VICTIM = "brenuin"  # the beggar -- expendable, and resurrected afterwards


def _npc_died_events(session) -> list[dict]:
    path = session.run_dir / "events.jsonl"
    if not path.exists():
        return []
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [r["payload"] for r in records if r.get("payload", {}).get("event_type") == "npc_died"]


def test_console_kill_produces_npc_died(live_session):
    db = live_session.db
    before = len(_npc_died_events(live_session))
    db.console(f"prid {REFS[VICTIM]}")
    time.sleep(0.5)
    db.console("kill")
    try:
        db.wait_until(lambda: len(_npc_died_events(live_session)) > before, timeout_s=20, what="npc_died in events.jsonl")
    finally:
        db.console(f"prid {REFS[VICTIM]}")
        time.sleep(0.5)
        db.console("resurrect")
    event = _npc_died_events(live_session)[-1]
    live_session.note(f"death: {event}")
    assert event["npc_id"] == VICTIM
    assert event["gamets"] > 0
    assert "POST /whiterun/events" in live_session.listener.log_text()
