"""Slice 60: a well-evidenced belief spawns the authored evidence item at the believer, persistently."""

from __future__ import annotations

import time

import pytest

from adapters.skyrim.livetest import seeding
from adapters.skyrim.livetest.cast import EVIDENCE_ITEM_NAME, REFS

pytestmark = pytest.mark.live

HOLDER = "nazeem"
SPAWNED = f"evidence: spawned evidence object at '{HOLDER}''s position"


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


def test_evidence_object_exists_near_holder(live_session, spawned):
    db = live_session.db
    _go_to_holder(db)
    found = _evidence_refs(db)
    assert found, f"no '{EVIDENCE_ITEM_NAME}' MISC ref within 2000 units of {HOLDER}"
    live_session.note(f"evidence ref: {found[0]['formId']} at {found[0]['position']}")


def test_evidence_survives_cell_detach(live_session, spawned):
    db = live_session.db
    db.console("coc RiverwoodSleepingGiantInn")
    db.wait_until(lambda: db.scene().get("cell", {}).get("editorId") == "RiverwoodSleepingGiantInn", timeout_s=90, what="arrive in Riverwood")
    time.sleep(5)
    db.console("coc WhiterunOrigin")
    db.wait_until(lambda: db.scene().get("worldspace", {}).get("editorId") == "WhiterunWorld", timeout_s=90, what="return to Whiterun")
    _go_to_holder(db)
    assert _evidence_refs(db), "evidence object gone after cell detach/attach"


def test_evidence_survives_save_and_load(live_session, spawned):
    db = live_session.db
    db.scenario([
        {"tool": "game", "args": {"action": "save", "name": "chronicle-live-evidence"}},
        {"waitFor": "saveGame", "timeoutMs": 60000},
        {"tool": "game", "args": {"action": "load", "name": "chronicle-live-evidence"}},
        {"waitFor": "postLoadGame", "timeoutMs": 120000},
        {"waitUntil": "playerLoaded", "timeoutMs": 60000},
    ], timeout_s=300)
    _go_to_holder(db)
    assert _evidence_refs(db), "evidence object gone after save/load -- forced persistence did not hold"
