"""Slice 50: a player-directed grudge reaches the bridge's vendor-markup cache.

The barter-price write itself cannot be exercised unattended: ``BarterMenu``
only opens through dialogue, and DevBench's ``menu open`` explicitly cannot
open target-ref menus. That last step is printed as a manual check.
"""

from __future__ import annotations

import json

import pytest

from adapters.skyrim.livetest import seeding

pytestmark = pytest.mark.live

VENDOR = "adrianne_avenicci"
# A distinct vendor for test_bridge_caches_multiplier -- the listener's
# vendor-markup delivery is single-consumer (a "changed since last
# delivered" dedupe, per _vendor_markup_pairs in listener.py), with a
# 60s awaiting-ack timeout before an unacked pair is re-offered.
# test_listener_serves_player_directed_pair's own direct GET consumes
# VENDOR's delivery; ChronicleBridge's C++ poller (which never acks
# vendor-markup by design -- see VendorMarkupCache.cpp's header comment)
# would then see no change for that same pair until that 60s timeout
# expires, well past this test's budget. Using a different holder NPC
# gives each test its own uncontested delivery instead of racing for
# one (2026-08-29).
VENDOR_FOR_BRIDGE_CACHE = "nazeem"
CACHED = f"vendor-markup: cached 1.50x for vendor '{VENDOR}'"
CACHED_FOR_BRIDGE = f"vendor-markup: cached 1.50x for vendor '{VENDOR_FOR_BRIDGE_CACHE}'"


def test_listener_serves_player_directed_pair(live_session):
    seeding.seed_grudge(run_id=live_session.run_id, runs_dir=live_session.runs_dir, holder=VENDOR, target=seeding.PLAYER_ID, gamets=live_session.next_gamets(), crime_type="theft")
    status, body = live_session.listener.get("/whiterun/vendor-markup")
    assert status == 200
    pairs = json.loads(body)
    match = [p for p in pairs if p["holder_id"] == VENDOR and p["target_id"] == seeding.PLAYER_ID]
    assert match, f"listener did not serve the player-directed pair: {pairs}"
    assert match[0]["markup_multiplier"] == pytest.approx(1.5)


def test_bridge_caches_multiplier(live_session):
    seeding.seed_grudge(run_id=live_session.run_id, runs_dir=live_session.runs_dir, holder=VENDOR_FOR_BRIDGE_CACHE, target=seeding.PLAYER_ID, gamets=live_session.next_gamets(), crime_type="theft")
    line = live_session.bridge_log.wait_for(CACHED_FOR_BRIDGE, timeout_s=30)
    live_session.note(f"vendor markup: {line.message}")
    live_session.note(f"MANUAL: talk to {VENDOR_FOR_BRIDGE_CACHE}, open barter, compare displayed price vs gold charged (1.5x expected)")
