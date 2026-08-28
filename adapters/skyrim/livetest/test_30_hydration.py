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
    db.scenario([
        {"tool": "game", "args": {"action": "save", "name": "chronicle-live-hydration"}},
        {"waitFor": "saveGame", "timeoutMs": 60000},
        {"tool": "game", "args": {"action": "load", "name": "chronicle-live-hydration"}},
        {"waitFor": "postLoadGame", "timeoutMs": 120000},
        {"waitUntil": "playerLoaded", "timeoutMs": 60000},
    ], timeout_s=300)
    after = _rank(db, holder, target)
    assert after == EXPECTED_RANK, f"rank reverted to {after} after reload -- AddChange() was not sufficient to persist"
