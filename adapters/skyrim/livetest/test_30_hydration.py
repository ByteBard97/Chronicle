"""Slice 30: a Chronicle grudge becomes a vanilla relationship rank, and survives save/load.

Nobody has confirmed which named-cast pairs have an authored ``BGSRelationship``
(the poller only mutates an existing record). So this sweeps the candidate
pairs until one applies; if none does, that negative is the finding.
"""

from __future__ import annotations

import pytest

from adapters.skyrim.livetest import seeding
from adapters.skyrim.livetest.cast import HYDRATION_CANDIDATES, REFS

pytestmark = pytest.mark.live

APPLIED = "ChronicleBridge hydration: set relationship("
SKIPPED = "ChronicleBridge hydration: no existing BGSRelationship for ("
EXPECTED_RANK = -2  # severity 1.0 -> RANK_SEVERE -> kFoe -> Papyrus rank -2
SAVE_NAME = "chronicle-live-hydration"


def _rank(db, holder: str, target: str) -> int:
    return int(db.papyrus("Actor", "GetRelationshipRank", self_form=REFS[holder], args=[db.form(REFS[target])]))


@pytest.fixture(scope="module")
def applied_pair(live_session):
    """Seed candidates until the bridge reports an applied write. Also seeds avoidance (slice 40)."""
    db, log = live_session.db, live_session.bridge_log
    outcomes: list[str] = []
    for holder, target in HYDRATION_CANDIDATES:
        before = _rank(db, holder, target)
        mark = log.mark()
        seeding.seed_grudge(run_id=live_session.run_id, runs_dir=live_session.runs_dir, holder=holder, target=target, gamets=live_session.next_gamets())
        line = log.wait_for(f"({holder}, {target})", timeout_s=30, since=mark)
        if APPLIED in line.raw:
            live_session.note(f"hydration: applied on ({holder}, {target}), rank before={before}")
            return holder, target, before
        outcomes.append(line.message)
        live_session.note(f"hydration: {line.message}")
    pytest.fail("no candidate pair has an authored vanilla BGSRelationship -- record this in the runbook:\n  " + "\n  ".join(outcomes))


def test_rank_written_in_game(live_session, applied_pair):
    holder, target, before = applied_pair
    after = _rank(live_session.db, holder, target)
    assert after == EXPECTED_RANK, f"rank {before} -> {after}, expected {EXPECTED_RANK}"


def test_rank_survives_save_and_load(live_session, applied_pair):
    holder, target, _ = applied_pair
    db = live_session.db
    # First live attempt: game action=save's own queue-log line isn't
    # evidence of a completed save (research confirmed it fires before the
    # engine's real BGSSaveLoadManager::Save call even runs) -- ruled that
    # out live: no open menu, no blocking state, save+waitFor(saveGame)
    # both succeeded, and the .ess file appeared on disk with the exact
    # right name immediately after. The very next scenario step (load)
    # still failed with a 404 "not found" -- a genuine race between the
    # saveGame lifecycle event firing and the file actually being visible/
    # flushed on disk (plausibly slower under Wine/Proton I/O). Fixed by
    # splitting into two scenario calls and polling list_saves() (pure
    # file I/O per its own docstring) until the file is actually visible
    # before ever asking to load it (2026-08-29).
    db.scenario([
        {"tool": "game", "args": {"action": "save", "name": SAVE_NAME}},
        {"waitFor": "saveGame", "timeoutMs": 60000},
    ], timeout_s=90)
    db.wait_until(
        lambda: any(SAVE_NAME in str(s) for s in (db.list_saves().get("saves") or [])),
        timeout_s=30,
        what=f"save '{SAVE_NAME}' visible in list_saves()",
    )
    # `load action=load name=X` silently no-ops (no error, but no reload
    # either) when X isn't yet reflected in BGSSaveLoadManager's own
    # internal save-list cache -- a raw filesystem listing (list_saves())
    # being non-stale doesn't mean that cache is. Research tied this to a
    # DevBench-fixed bug in the same family (github issue #42, quicksave
    # names going stale against that cache) -- `loadLast` is documented to
    # work reliably regardless of session/cache freshness, and the save
    # just written above is definitionally the most recent one, so this
    # sidesteps the by-name lookup entirely instead of guessing at a delay
    # (2026-08-29).
    db.scenario([
        {"tool": "game", "args": {"action": "loadLast"}},
        {"waitFor": "postLoadGame", "timeoutMs": 120000},
        {"waitUntil": "playerLoaded", "timeoutMs": 60000},
    ], timeout_s=200)
    after = _rank(db, holder, target)
    assert after == EXPECTED_RANK, f"rank reverted to {after} after reload -- AddChange() was not sufficient to persist"
