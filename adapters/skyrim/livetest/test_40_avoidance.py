"""Slice 40: the same grudge flips the pair's patcher-authored gating global to 1."""

from __future__ import annotations

import time

import pytest

from adapters.skyrim.livetest import seeding
from adapters.skyrim.livetest.cast import REFS

pytestmark = pytest.mark.live

PAIR = ("fralia_gray_mane", "olfina_gray_mane")  # first hydration candidate: already seeded by slice 30


def _global_value(db, entry: seeding.AvoidanceGlobal) -> float:
    form_id = db.compose_form_id(entry.plugin, entry.local_form_id)
    return float(db.papyrus("GlobalVariable", "GetValue", self_form=form_id))


def _distance(db, a: str, b: str) -> float:
    return float(db.papyrus("ObjectReference", "GetDistance", self_form=REFS[a], args=[db.form(REFS[b])]))


def test_global_set_and_packages_reevaluated(live_session):
    db, log = live_session.db, live_session.bridge_log
    entry = seeding.avoidance_global(*PAIR)
    if not log.contains(f"avoidance: set {entry.editor_id} = 1"):
        seeding.seed_grudge(run_id=live_session.run_id, runs_dir=live_session.runs_dir, holder=PAIR[0], target=PAIR[1], gamets=live_session.next_gamets())
        log.wait_for(f"avoidance: set {entry.editor_id} = 1", timeout_s=30)
    assert _global_value(db, entry) == 1.0
    d0 = _distance(db, *PAIR)
    time.sleep(30)
    d1 = _distance(db, *PAIR)
    live_session.note(f"avoidance: {entry.editor_id}=1; distance {d0:.0f} -> {d1:.0f} over 30s (informational)")
