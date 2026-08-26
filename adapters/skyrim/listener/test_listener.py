"""Tests for adapters/skyrim/listener/listener.py.

Not under chronicle/tests/ or scenarios/ -- pyproject.toml's testpaths
deliberately don't include this file, the same "adapters/skyrim/ is not
part of chronicle/" boundary this directory's README.md states. Run
explicitly:

    uv run --with pydantic --with pytest pytest adapters/skyrim/listener/test_listener.py

/whiterun/events genuinely exercises the real subprocess call to
`python -m chronicle inject` (no mocking of that boundary) against a real
run built with chronicle.driver.Driver in a tmp CHRONICLE_RUNS_DIR, the
same pattern chronicle/tests/test_agent_debug_cli.py's run_dir fixture
uses -- this is the actual seam being tested, not an implementation
detail to stub out.
"""

from __future__ import annotations

import http.client
import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from listener import NAMED_CAST_NPC_IDS, _make_handler  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from chronicle.driver import Driver  # noqa: E402
from chronicle.events import NPCDied  # noqa: E402
from chronicle.framelog import FrameLogReader  # noqa: E402
from chronicle.schedule import ScheduleBlock  # noqa: E402
from chronicle.tests.test_fixtures import NAMED_CAST_NPC_IDS as _CHRONICLE_NAMED_CAST_NPC_IDS  # noqa: E402

from http.server import ThreadingHTTPServer  # noqa: E402

_SEED = "listener-test-seed"
_RUN = "listener-test-run"
_SAVE_UUID = "save-listener-1"
_TICKS = 10  # max tick is therefore 9


@pytest.fixture()
def live_run(tmp_path, monkeypatch):
    """A small real run in a tmp CHRONICLE_RUNS_DIR -- propagates to the
    listener's subprocess call since subprocess.run inherits os.environ
    by default and monkeypatch.setenv really sets it."""
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=_RUN,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=(ScheduleBlock(npc_id="nazeem", location_id="whiterun_market", start_tick=0, end_tick=50),),
        encounter_probability=0.0,
        runs_dir=tmp_path,
    )
    driver.run(0, _TICKS)
    driver.close()
    return tmp_path / _RUN


@pytest.fixture()
def server_factory(tmp_path):
    """Starts a real listener server on an ephemeral port; yields a (post, run_dir) helper."""
    servers = []

    def start(*, snapshot_path=None, shared_secret=None, live_run=None):
        handler_cls = _make_handler(snapshot_path or (tmp_path / "snap.json"), shared_secret, live_run)
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append(server)

        def post(path: str, body: dict, *, token: str | None = None) -> http.client.HTTPResponse:
            conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
            headers = {"Content-Type": "application/json"}
            if token is not None:
                headers["X-Chronicle-Bridge-Token"] = token
            conn.request("POST", path, body=json.dumps(body), headers=headers)
            resp = conn.getresponse()
            resp.read()
            conn.close()
            return resp

        def get(path: str, *, token: str | None = None) -> tuple[int, bytes]:
            conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
            headers = {}
            if token is not None:
                headers["X-Chronicle-Bridge-Token"] = token
            conn.request("GET", path, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            conn.close()
            return resp.status, data

        post.get = get
        return post

    yield start

    for server in servers:
        server.shutdown()


def test_events_endpoint_returns_503_without_live_run(server_factory):
    post = server_factory(live_run=None)
    resp = post("/whiterun/events", {"event_type": "npc_died", "gamets": 5.0, "npc_id": "nazeem"})
    assert resp.status == 503


def test_events_endpoint_appends_a_real_death_event_via_chronicle_inject(server_factory, live_run):
    post = server_factory(live_run=_RUN)
    resp = post(
        "/whiterun/events",
        {"event_type": "npc_died", "gamets": 8.0, "npc_id": "nazeem", "killer_id": "the_player", "location_id": "whiterun_market"},
    )
    assert resp.status == 204

    reader = FrameLogReader(live_run)
    events = [r for r in reader.records("events") if r["payload"].get("event_type") == "npc_died"]
    assert len(events) == 1
    record = events[0]
    assert record["tick"] == 8
    assert record["payload"]["npc_id"] == "nazeem"
    assert record["payload"]["killer_id"] == "the_player"
    assert record["payload"]["cause"] == "unknown"  # design doc §2, D2 -- fixed until cause detection lands
    assert record["payload"]["origin"] == {"kind": "adapter", "detail": "chronicle-bridge death event"}


def test_events_endpoint_rejects_a_malformed_payload(server_factory, live_run):
    post = server_factory(live_run=_RUN)
    resp = post("/whiterun/events", {"event_type": "npc_died"})  # missing required gamets/npc_id
    assert resp.status == 400
    reader = FrameLogReader(live_run)
    assert not any(r["payload"].get("event_type") == "npc_died" for r in reader.records("events"))


def test_events_endpoint_rejects_an_unknown_event_type(server_factory, live_run):
    post = server_factory(live_run=_RUN)
    resp = post("/whiterun/events", {"event_type": "bogus_event", "gamets": 1.0, "npc_id": "nazeem"})
    assert resp.status == 400


def test_events_endpoint_enforces_the_shared_secret(server_factory, live_run):
    post = server_factory(live_run=_RUN, shared_secret="s3cret")
    unauth = post("/whiterun/events", {"event_type": "npc_died", "gamets": 1.0, "npc_id": "nazeem"})
    assert unauth.status == 401
    authed = post("/whiterun/events", {"event_type": "npc_died", "gamets": 1.0, "npc_id": "nazeem"}, token="s3cret")
    assert authed.status == 204


def test_events_endpoint_surfaces_chronicles_own_rejection_reason(server_factory, live_run):
    """A death at a tick before the run's current max tick is chronicle's own
    fork-territory refusal (chronicle/cli.py) -- the listener must forward
    that as a 400, not swallow it as a generic failure. The fixture run's
    own max tick starts at 0 (no encounters fire with a single idle NPC
    and encounter_probability=0.0), so the first injection establishes a
    real max tick of 8 before the second one lands behind it."""
    post = server_factory(live_run=_RUN)
    first = post("/whiterun/events", {"event_type": "npc_died", "gamets": 8.0, "npc_id": "nazeem"})
    assert first.status == 204
    second = post("/whiterun/events", {"event_type": "npc_died", "gamets": 3.0, "npc_id": "nazeem"})
    assert second.status == 400


def test_positions_endpoint_still_works_after_the_events_route_was_added(server_factory, tmp_path):
    snapshot_path = tmp_path / "positions.json"
    post = server_factory(snapshot_path=snapshot_path)
    resp = post("/whiterun/positions", {"wall_ts": 123.0, "npcs": [{"id": "nazeem", "name": "Nazeem", "x": 1.0, "y": 2.0}]})
    assert resp.status == 204
    assert json.loads(snapshot_path.read_text())["npcs"][0]["name"] == "Nazeem"


_GRUDGE_RUN = "listener-test-grudge-run"


@pytest.fixture()
def grudge_run(tmp_path, monkeypatch):
    """A run with two named-cast NPCs (nazeem, ysolda) and a severe grudge
    between them, for exercising /whiterun/hydration. Both ids are in
    listener.NAMED_CAST_NPC_IDS."""
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=_GRUDGE_RUN,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=(
            ScheduleBlock(npc_id="nazeem", location_id="whiterun_market", start_tick=0, end_tick=1000),
            ScheduleBlock(npc_id="ysolda", location_id="whiterun_market", start_tick=0, end_tick=1000),
        ),
        encounter_probability=0.0,
        runs_dir=tmp_path,
    )
    driver.run(0, 5)
    relationship = driver.form_relationship(
        id="r1", from_id="nazeem", to_id="ysolda",
        basis="colocation", basis_id=None, strength=0.9, gamets=5.0,
    )
    driver.form_grudge(
        id="g1", holder_id="nazeem", victim_id="ysolda", target_id="ysolda",
        grievance_type="theft", source_belief_id="belief-nazeem-ysolda",
        evidentiary_strength=0.9, relationship_to_victim=relationship, gamets=5.0,
        forgiveness_threshold=0.2,
    )
    driver.run(5, 6)
    driver.close()
    return driver, tmp_path


def test_named_cast_mirror_matches_chronicles_own_mirror():
    """listener.py hardcodes its own copy of IdentityMap.cpp's kNamedCast
    (it cannot import chronicle.tests.test_fixtures.NAMED_CAST_NPC_IDS --
    that lives under chronicle/tests/, not a shared importable location).
    Ties the two independently-maintained mirrors together so a future
    edit to one that forgets the other is caught immediately, the same
    discipline test_fixtures.py already applies against IdentityMap.cpp
    itself."""
    assert NAMED_CAST_NPC_IDS == _CHRONICLE_NAMED_CAST_NPC_IDS


def test_hydration_endpoint_returns_empty_array_for_a_sub_threshold_grudge(server_factory, tmp_path, monkeypatch):
    """A grudge that exists but never crosses the mild-band threshold
    (relationship_rank_for -> 0) must be indistinguishable from "no
    grudge rows at all" in the response -- not surfaced as a spurious
    rank-0 change."""
    run_id = "listener-test-subthreshold-run"
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=(
            ScheduleBlock(npc_id="nazeem", location_id="whiterun_market", start_tick=0, end_tick=50),
            ScheduleBlock(npc_id="ysolda", location_id="whiterun_market", start_tick=0, end_tick=50),
        ),
        encounter_probability=0.0,
        runs_dir=tmp_path,
    )
    driver.run(0, 5)
    relationship = driver.form_relationship(
        id="r1", from_id="nazeem", to_id="ysolda",
        basis="colocation", basis_id=None, strength=0.1, gamets=5.0,
    )
    driver.form_grudge(
        id="g1", holder_id="nazeem", victim_id="ysolda", target_id="ysolda",
        grievance_type="theft", source_belief_id="belief-nazeem-ysolda",
        evidentiary_strength=0.1, relationship_to_victim=relationship, gamets=5.0,
        forgiveness_threshold=0.2,
    )
    driver.close()

    post = server_factory(live_run=run_id)
    status, body = post.get("/whiterun/hydration")
    assert status == 200
    assert json.loads(body) == []


def test_hydration_endpoint_returns_503_without_live_run(server_factory):
    post = server_factory(live_run=None)
    status, _ = post.get("/whiterun/hydration")
    assert status == 503


def test_hydration_endpoint_returns_empty_array_with_no_grudges(server_factory, live_run):
    post = server_factory(live_run=_RUN)
    status, body = post.get("/whiterun/hydration")
    assert status == 200
    assert json.loads(body) == []


def test_hydration_endpoint_surfaces_a_severe_grudge_between_named_cast(server_factory, grudge_run):
    _driver, _tmp_path = grudge_run
    post = server_factory(live_run=_GRUDGE_RUN)

    status, body = post.get("/whiterun/hydration")
    assert status == 200
    pairs = json.loads(body)
    assert pairs == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]


def test_hydration_endpoint_is_idempotent_on_a_second_immediate_poll(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    first_status, first_body = post.get("/whiterun/hydration")
    assert first_status == 200
    assert json.loads(first_body) != []

    second_status, second_body = post.get("/whiterun/hydration")
    assert second_status == 200
    assert json.loads(second_body) == []


def test_hydration_endpoint_reverts_toward_zero_once_the_grudge_cools(server_factory, grudge_run):
    _driver, _tmp_path = grudge_run
    post = server_factory(live_run=_GRUDGE_RUN)

    first_status, first_body = post.get("/whiterun/hydration")
    assert first_status == 200
    assert json.loads(first_body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]

    # Advance the run's max tick well past both grudge half-lives
    # (GRUDGE_EMOTIONAL_HALF_LIFE=672, GRUDGE_EVIDENTIARY_HALF_LIFE=336
    # ticks) so the decayed severity has fallen back below the mild
    # threshold by the time of the next poll. Reuses the already-tested
    # /whiterun/events write path (an unrelated NPC's death) purely to
    # push the run's max tick forward -- inject() appends a bare canonical
    # event with no rule processing, so it does not touch the
    # nazeem/ysolda grudge itself.
    death = post("/whiterun/events", {"event_type": "npc_died", "gamets": 2000.0, "npc_id": "brenuin"})
    assert death.status == 204

    third_status, third_body = post.get("/whiterun/hydration")
    assert third_status == 200
    assert json.loads(third_body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": 0}]


def test_hydration_endpoint_does_not_reoffer_a_pair_still_awaiting_ack(server_factory, grudge_run):
    """Two back-to-back polls with no ack in between must return the pair
    only once -- it is in-flight (offered-awaiting-ack), not a duplicate
    offer. Closes the fad0d79 gap: the old cache marked a pair delivered
    the instant it was served, so this exact scenario would previously
    have (wrongly) returned the pair only once for a different reason --
    the new state machine returns it once for the RIGHT reason (it is
    still awaiting an ack), which matters for every other behavior below."""
    post = server_factory(live_run=_GRUDGE_RUN)
    first_status, first_body = post.get("/whiterun/hydration")
    assert first_status == 200
    assert json.loads(first_body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]

    second_status, second_body = post.get("/whiterun/hydration")
    assert second_status == 200
    assert json.loads(second_body) == []


def test_hydration_ack_applied_means_not_reoffered_at_the_same_rank(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/hydration")
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]

    ack = post(
        "/whiterun/hydration/ack",
        [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "applied"}],
    )
    assert ack.status == 204

    status, body = post.get("/whiterun/hydration")
    assert status == 200
    assert json.loads(body) == []


def test_hydration_ack_no_relationship_permanently_skips_the_same_rank(server_factory, grudge_run):
    """A no_relationship ack must never be re-offered again at the SAME
    rank, even once the rank is independently recomputed to the identical
    value on a later poll -- that recomputation is not new information."""
    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/hydration")
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]

    ack = post(
        "/whiterun/hydration/ack",
        [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "no_relationship"}],
    )
    assert ack.status == 204

    # A later poll recomputes the identical rank (-2, nothing in the
    # underlying grudge changed) -- must still not be re-offered.
    status, body = post.get("/whiterun/hydration")
    assert status == 200
    assert json.loads(body) == []


def test_hydration_ack_no_relationship_is_reoffered_once_the_rank_changes(server_factory, grudge_run):
    """The permanent skip is scoped to the exact rank it was recorded
    against -- once the underlying grudge decays to a genuinely different
    rank, the pair must be offered again (a different rank maps to a
    different in-game RELATIONSHIP_LEVEL; the old skip says nothing about
    whether THAT relationship exists)."""
    driver, _tmp_path = grudge_run
    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/hydration")
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]

    ack = post(
        "/whiterun/hydration/ack",
        [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "no_relationship"}],
    )
    assert ack.status == 204

    # Push the run's max tick well past both grudge half-lives so the
    # decayed severity falls back to rank 0 -- a genuinely different rank
    # from the -2 that was permanently skipped.
    death = post("/whiterun/events", {"event_type": "npc_died", "gamets": 2000.0, "npc_id": "brenuin"})
    assert death.status == 204

    status, body = post.get("/whiterun/hydration")
    assert status == 200
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": 0}]


def test_hydration_ack_retry_is_reoffered_on_the_next_poll(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/hydration")
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]

    ack = post(
        "/whiterun/hydration/ack",
        [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "retry"}],
    )
    assert ack.status == 204

    status, body = post.get("/whiterun/hydration")
    assert status == 200
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]


def test_hydration_pair_is_reoffered_after_a_listener_restart(server_factory, grudge_run):
    """Simulates the listener process itself restarting (a fresh
    handler-state closure, as here): the new process has no memory of a
    prior offer at all, so the pair is offered again on its next poll from
    that fresh state -- the "does not persist across restarts" limitation
    the module docstring already names, now carried in the richer per-pair
    state machine instead of a bare rank cache. (Renamed from its original
    "dropped ack never arrives" name -- that's a DIFFERENT scenario, the
    same long-running process never restarting at all, covered by
    test_hydration_pair_is_reoffered_if_its_ack_times_out below.)"""
    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/hydration")
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]

    # No ack ever sent -- simulate the listener restarting (fresh state)
    # by starting a brand-new server against the same run.
    fresh_post = server_factory(live_run=_GRUDGE_RUN)
    status, body = fresh_post.get("/whiterun/hydration")
    assert status == 200
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]


def test_hydration_pair_is_reoffered_if_its_ack_times_out(server_factory, grudge_run, monkeypatch):
    """The gap an ack timeout closes: the SAME long-running listener
    process (no restart), whose ack for a given offer was silently
    dropped (PostHydrationAck is fire-and-forget, per OutboundClient.h --
    a real, expected possibility, not just a hypothetical). Without a
    timeout, this pair would stay "awaiting_ack" forever since its
    computed rank never changes -- listener._AWAITING_ACK_TIMEOUT_SECONDS
    is what makes a dropped ack self-correcting instead of a permanent
    stuck state."""
    import listener as listener_module

    fake_now = [1000.0]
    monkeypatch.setattr(listener_module.time, "monotonic", lambda: fake_now[0])

    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/hydration")
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]

    # No ack sent. Immediately re-polling (still within the timeout
    # window) must NOT re-offer -- this is the ordinary "in-flight,
    # awaiting-ack" no-op case, unaffected by the fix.
    status, body = post.get("/whiterun/hydration")
    assert json.loads(body) == []

    # Advance past the timeout with no ack ever having arrived (still the
    # same server, same in-memory state -- no restart). The pair must be
    # re-offered even though its computed rank hasn't changed.
    fake_now[0] += listener_module._AWAITING_ACK_TIMEOUT_SECONDS + 1.0
    status, body = post.get("/whiterun/hydration")
    assert status == 200
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "relationship_rank": -2}]


def test_hydration_ack_endpoint_returns_503_without_live_run(server_factory):
    post = server_factory(live_run=None)
    resp = post("/whiterun/hydration/ack", [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "applied"}])
    assert resp.status == 503


def test_hydration_ack_endpoint_rejects_a_non_array_body(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    resp = post("/whiterun/hydration/ack", {"holder_id": "nazeem", "target_id": "ysolda", "outcome": "applied"})
    assert resp.status == 400


def test_hydration_ack_endpoint_rejects_an_unknown_outcome(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    resp = post(
        "/whiterun/hydration/ack",
        [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "bogus"}],
    )
    assert resp.status == 400


def test_hydration_ack_endpoint_rejects_a_missing_field(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    resp = post("/whiterun/hydration/ack", [{"holder_id": "nazeem", "outcome": "applied"}])
    assert resp.status == 400


def test_hydration_ack_endpoint_enforces_the_shared_secret(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN, shared_secret="s3cret")
    unauth = post("/whiterun/hydration/ack", [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "applied"}])
    assert unauth.status == 401
    authed = post(
        "/whiterun/hydration/ack",
        [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "applied"}],
        token="s3cret",
    )
    assert authed.status == 204


def test_unknown_path_is_404(server_factory):
    post = server_factory()
    resp = post("/not/a/real/path", {})
    assert resp.status == 404
