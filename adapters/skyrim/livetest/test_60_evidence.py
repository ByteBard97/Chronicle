"""Slice 60: a well-evidenced belief spawns the authored evidence item at the believer, persistently."""

from __future__ import annotations

import time

import pytest

from adapters.skyrim.livetest import seeding
from adapters.skyrim.livetest.cast import EVIDENCE_ITEM_NAME, REFS

pytestmark = pytest.mark.live

HOLDER = "nazeem"
SPAWNED = f"evidence: spawned evidence object at '{HOLDER}''s position"
SAVE_NAME = "chronicle-live-evidence"


def _evidence_refs(db) -> list[dict]:
    return [r for r in db.refs(form_type="MISC", radius=2000, limit=200) if r.get("base", {}).get("name") == EVIDENCE_ITEM_NAME]


def _go_to_holder(db) -> None:
    db.console(f"player.moveto {REFS[HOLDER]}")
    time.sleep(3)
    db.call_retry("inspect", deadline_s=30, kind="state")


@pytest.fixture(scope="module")
def spawned(live_session):
    log = live_session.bridge_log
    seeding.seed_belief(run_id=live_session.run_id, runs_dir=live_session.runs_dir, holder=HOLDER, gamets=live_session.next_gamets())
    line = log.wait_for(SPAWNED, timeout_s=30)
    live_session.note(f"evidence: {line.message}")
    return line


@pytest.fixture(scope="module")
def evidence_form_id(live_session, spawned) -> str:
    """Capture the spawned evidence ref's FormID once, right after spawn.

    The evidence object is a fixed-position ref; ``HOLDER`` (nazeem) is a
    living NPC who keeps following his normal AI routine. A ``radius``
    search only enumerates "loaded refs in the grid" (DevBench's own
    README wording) around wherever the player currently is -- fine right
    after spawn, while nazeem is still near it, but a false negative in
    any later test after he's wandered off and the player teleports to
    his *new* position instead. Persistence tests must look up this exact
    FormID (``db.ref()``, a live-form resolve, not a loaded-grid
    enumeration) instead of re-searching by radius (2026-08-29).
    """
    db = live_session.db
    _go_to_holder(db)
    found = _evidence_refs(db)
    assert found, f"no '{EVIDENCE_ITEM_NAME}' MISC ref within 2000 units of {HOLDER}"
    live_session.note(f"evidence ref: {found[0]['formId']} at {found[0]['position']}")
    return found[0]["formId"]


def test_evidence_object_exists_near_holder(evidence_form_id):
    assert evidence_form_id


def test_evidence_survives_cell_detach(live_session, evidence_form_id):
    db = live_session.db
    db.console("coc RiverwoodSleepingGiantInn")
    db.wait_until(lambda: db.scene().get("cell", {}).get("editorId") == "RiverwoodSleepingGiantInn", timeout_s=90, what="arrive in Riverwood")
    time.sleep(5)
    db.console("coc WhiterunOrigin")
    db.wait_until(lambda: db.scene().get("worldspace", {}).get("editorId") == "WhiterunWorld", timeout_s=90, what="return to Whiterun")
    assert db.ref(evidence_form_id), "evidence object gone after cell detach/attach"


def test_evidence_survives_save_and_load(live_session, evidence_form_id):
    db = live_session.db
    # Same save/load-race + load-no-op issues found in test_30_hydration.py
    # apply here identically (both go through the same DevBench game
    # tool/native BGSSaveLoadManager path) -- see that file's comments and
    # GOALS.md for the still-open `load` bug. Split + list_saves() poll
    # applied here for consistency even though `load` itself may still
    # silently no-op (2026-08-29).
    db.scenario([
        {"tool": "game", "args": {"action": "save", "name": SAVE_NAME}},
        {"waitFor": "saveGame", "timeoutMs": 60000},
    ], timeout_s=90)
    db.wait_until(
        lambda: any(SAVE_NAME in str(s) for s in (db.list_saves().get("saves") or [])),
        timeout_s=30,
        what=f"save '{SAVE_NAME}' visible in list_saves()",
    )
    db.scenario([
        {"tool": "game", "args": {"action": "loadLast"}},
        {"waitFor": "postLoadGame", "timeoutMs": 120000},
        {"waitUntil": "playerLoaded", "timeoutMs": 60000},
    ], timeout_s=200)
    assert db.ref(evidence_form_id), "evidence object gone after save/load -- forced persistence did not hold"
