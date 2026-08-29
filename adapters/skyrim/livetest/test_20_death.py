"""Slice 20: a named-cast death reaches the run's events.jsonl as ``npc_died``."""

from __future__ import annotations

import json

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
    ref = REFS[VICTIM]
    # Three prior live attempts at console-driven kill (prid+kill,
    # <ref>.kill, <ref>.setessential 0 + <ref>.kill) all failed identically
    # -- no npc_died, no error, no echo. Research confirmed DevBench's
    # console exec really does call the game's own RE::Console::
    # ExecuteCommand, so this isn't a DevBench dispatch bug. Switched to
    # Papyrus's Actor.Kill()/IsDead()/GetActorValue -- the harness's own
    # documented "reliable assertion primitive" with no marker/queue race
    # -- both to kill more reliably and to get a direct read on whether
    # the actor actually dies at all (isolating "kill didn't land" from
    # "it died but ChronicleBridge's identity resolution silently dropped
    # the event") (2026-08-29).
    ref_info = db.ref(ref)
    live_session.note(f"ref lookup: {ref_info}")
    health_before = db.papyrus("Actor", "GetActorValue", self_form=ref, args=["Health"])
    live_session.note(f"health before: {health_before}")
    db.papyrus("Actor", "Kill", self_form=ref)
    try:
        db.wait_until(lambda: len(_npc_died_events(live_session)) > before, timeout_s=20, what="npc_died in events.jsonl")
    finally:
        is_dead = db.papyrus("Actor", "IsDead", self_form=ref)
        health_after = db.papyrus("Actor", "GetActorValue", self_form=ref, args=["Health"])
        live_session.note(f"IsDead={is_dead} health_after={health_after}")
        db.papyrus("Actor", "Resurrect", self_form=ref, args=[True])
    event = _npc_died_events(live_session)[-1]
    live_session.note(f"death: {event}")
    assert event["npc_id"] == VICTIM
    assert event["gamets"] > 0
    assert "POST /whiterun/events" in live_session.listener.log_text()
