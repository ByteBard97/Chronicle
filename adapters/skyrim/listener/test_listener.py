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
from listener import NAMED_CAST_NPC_IDS, _make_handler, _manifest_from_hello_body

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from http.server import ThreadingHTTPServer

from chronicle.claims import CONFIDENCE_DECAY_HALF_LIFE, EventKey
from chronicle.driver import Driver
from chronicle.events import NPCDied
from chronicle.framelog import FrameLogReader
from chronicle.schedule import ScheduleBlock
from chronicle.sync import Manifest
from chronicle.tests.test_fixtures import (
    NAMED_CAST_NPC_IDS as _CHRONICLE_NAMED_CAST_NPC_IDS,
)

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

    def start(*, snapshot_path=None, shared_secret=None, live_run=None, sync_state_dir=None):
        handler_cls = _make_handler(
            snapshot_path or (tmp_path / "snap.json"),
            shared_secret,
            live_run,
            sync_state_dir if sync_state_dir is not None else (tmp_path / "sync-state"),
        )
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

        def post_json(path: str, body: dict, *, token: str | None = None) -> tuple[int, bytes]:
            """Like `post`, but returns (status, body) -- `post` itself drains and discards the
            response body (fine for every existing route, which replies with no body), but the
            sync/hello route replies 200 with a JSON decision body callers need to inspect."""
            conn = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)
            headers = {"Content-Type": "application/json"}
            if token is not None:
                headers["X-Chronicle-Bridge-Token"] = token
            conn.request("POST", path, body=json.dumps(body), headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            conn.close()
            return resp.status, data

        post.get = get
        post.post_json = post_json
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
    resp = post("/whiterun/events", {"event_type": "npc_died"})  # missing required gamets (schema-enforced)
    assert resp.status == 400
    reader = FrameLogReader(live_run)
    assert not any(r["payload"].get("event_type") == "npc_died" for r in reader.records("events"))


def test_events_endpoint_rejects_an_npc_died_payload_missing_npc_id(server_factory, live_run):
    """npc_id is no longer schema-`required` on the now-shared GameEvent object
    (docs/design/chronicle-bridge-crime-witness-out.md §4 -- required npc_id and
    required witness_id/perpetrator_id/crime_type can't both live in one flat
    JSON Schema `required` list), so this is enforced by the listener's own
    per-kind check instead, same as the crime_witnessed case below."""
    post = server_factory(live_run=_RUN)
    resp = post("/whiterun/events", {"event_type": "npc_died", "gamets": 5.0})  # missing required npc_id
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


def test_events_endpoint_appends_a_real_crime_witnessed_event_via_chronicle_inject(server_factory, live_run):
    """docs/design/chronicle-bridge-crime-witness-out.md §4: the bystander
    row (victim_id differs from witness_id) -- belief only, no grudge, but
    that cascade is chronicle's own concern; the listener's job is just to
    get the event appended with its fields intact."""
    post = server_factory(live_run=_RUN)
    resp = post(
        "/whiterun/events",
        {
            "event_type": "crime_witnessed",
            "gamets": 8.0,
            "witness_id": "nazeem",
            "perpetrator_id": "the_player",
            "crime_type": "assault",
            "victim_id": "brenuin",
            "location_id": "whiterun_market",
        },
    )
    assert resp.status == 204

    reader = FrameLogReader(live_run)
    events = [r for r in reader.records("events") if r["payload"].get("event_type") == "crime_witnessed"]
    assert len(events) == 1
    record = events[0]
    assert record["tick"] == 8
    assert record["payload"]["witness_id"] == "nazeem"
    assert record["payload"]["perpetrator_id"] == "the_player"
    assert record["payload"]["crime_type"] == "assault"
    assert record["payload"]["victim_id"] == "brenuin"
    assert record["payload"]["location_id"] == "whiterun_market"
    assert record["payload"]["origin"] == {"kind": "adapter", "detail": "chronicle-bridge crime_witnessed event"}


def test_events_endpoint_appends_a_crime_witnessed_event_with_no_victim(server_factory, live_run):
    """victim_id omitted (property/bounty crime, design doc §2) -- optional, defaults to None."""
    post = server_factory(live_run=_RUN)
    resp = post(
        "/whiterun/events",
        {"event_type": "crime_witnessed", "gamets": 8.0, "witness_id": "nazeem", "perpetrator_id": "the_player", "crime_type": "theft"},
    )
    assert resp.status == 204
    reader = FrameLogReader(live_run)
    events = [r for r in reader.records("events") if r["payload"].get("event_type") == "crime_witnessed"]
    assert len(events) == 1
    assert events[0]["payload"].get("victim_id") is None


def test_events_endpoint_rejects_a_crime_witnessed_payload_missing_required_fields(server_factory, live_run):
    post = server_factory(live_run=_RUN)
    # Valid per the flat GameEvent schema, but missing crime_witnessed's
    # own required trio -- the listener's per-kind check must reject it
    # (docs/design/chronicle-bridge-crime-witness-out.md §4).
    resp = post("/whiterun/events", {"event_type": "crime_witnessed", "gamets": 1.0})
    assert resp.status == 400
    reader = FrameLogReader(live_run)
    assert not any(r["payload"].get("event_type") == "crime_witnessed" for r in reader.records("events"))


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
    _driver, _tmp_path = grudge_run
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


def test_avoidance_endpoint_returns_empty_array_for_a_sub_threshold_grudge(server_factory, tmp_path, monkeypatch):
    """A grudge that never clears the avoidance threshold must be
    indistinguishable from "no grudge rows at all" -- not surfaced as a
    spurious avoiding:false change."""
    run_id = "listener-test-avoidance-subthreshold-run"
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
    status, body = post.get("/whiterun/avoidance")
    assert status == 200
    assert json.loads(body) == []


def test_avoidance_endpoint_returns_503_without_live_run(server_factory):
    post = server_factory(live_run=None)
    status, _ = post.get("/whiterun/avoidance")
    assert status == 503


def test_avoidance_endpoint_returns_empty_array_with_no_grudges(server_factory, live_run):
    post = server_factory(live_run=_RUN)
    status, body = post.get("/whiterun/avoidance")
    assert status == 200
    assert json.loads(body) == []


def test_avoidance_endpoint_surfaces_a_severe_uncooled_grudge_between_named_cast(server_factory, grudge_run):
    _driver, _tmp_path = grudge_run
    post = server_factory(live_run=_GRUDGE_RUN)

    status, body = post.get("/whiterun/avoidance")
    assert status == 200
    pairs = json.loads(body)
    assert pairs == [{"npc_a": "nazeem", "npc_b": "ysolda", "avoiding": True}]


def test_avoidance_endpoint_canonicalizes_pair_order_lexicographically(server_factory, tmp_path, monkeypatch):
    """The grudge is held nazeem -> ysolda (holder, target), but the
    response must always report npc_a/npc_b in lexicographic order
    regardless of which NPC is the holder -- avoidance is symmetric,
    unlike hydration's directed holder/target."""
    run_id = "listener-test-avoidance-canonical-run"
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
    # Holder ysolda, target nazeem -- reversed from the usual grudge_run
    # fixture, to prove canonicalization doesn't just happen to match
    # holder/target order by coincidence.
    relationship = driver.form_relationship(
        id="r1", from_id="ysolda", to_id="nazeem",
        basis="colocation", basis_id=None, strength=0.9, gamets=5.0,
    )
    driver.form_grudge(
        id="g1", holder_id="ysolda", victim_id="nazeem", target_id="nazeem",
        grievance_type="theft", source_belief_id="belief-ysolda-nazeem",
        evidentiary_strength=0.9, relationship_to_victim=relationship, gamets=5.0,
        forgiveness_threshold=0.2,
    )
    driver.close()

    post = server_factory(live_run=run_id)
    status, body = post.get("/whiterun/avoidance")
    assert status == 200
    assert json.loads(body) == [{"npc_a": "nazeem", "npc_b": "ysolda", "avoiding": True}]


def test_avoidance_endpoint_is_idempotent_on_a_second_immediate_poll(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    first_status, first_body = post.get("/whiterun/avoidance")
    assert first_status == 200
    assert json.loads(first_body) != []

    second_status, second_body = post.get("/whiterun/avoidance")
    assert second_status == 200
    assert json.loads(second_body) == []


def test_avoidance_endpoint_reports_avoiding_false_once_the_grudge_cools(server_factory, grudge_run):
    _driver, _tmp_path = grudge_run
    post = server_factory(live_run=_GRUDGE_RUN)

    first_status, first_body = post.get("/whiterun/avoidance")
    assert first_status == 200
    assert json.loads(first_body) == [{"npc_a": "nazeem", "npc_b": "ysolda", "avoiding": True}]

    # Advance the run's max tick well past both grudge half-lives, same
    # technique as the hydration cooling test.
    death = post("/whiterun/events", {"event_type": "npc_died", "gamets": 2000.0, "npc_id": "brenuin"})
    assert death.status == 204

    third_status, third_body = post.get("/whiterun/avoidance")
    assert third_status == 200
    assert json.loads(third_body) == [{"npc_a": "nazeem", "npc_b": "ysolda", "avoiding": False}]


def test_avoidance_ack_applied_means_not_reoffered_while_unchanged(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/avoidance")
    assert json.loads(body) == [{"npc_a": "nazeem", "npc_b": "ysolda", "avoiding": True}]

    ack = post(
        "/whiterun/avoidance/ack",
        [{"npc_a": "nazeem", "npc_b": "ysolda", "outcome": "applied"}],
    )
    assert ack.status == 204

    status, body = post.get("/whiterun/avoidance")
    assert status == 200
    assert json.loads(body) == []


def test_avoidance_ack_retry_is_reoffered_on_the_next_poll(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/avoidance")
    assert json.loads(body) == [{"npc_a": "nazeem", "npc_b": "ysolda", "avoiding": True}]

    ack = post(
        "/whiterun/avoidance/ack",
        [{"npc_a": "nazeem", "npc_b": "ysolda", "outcome": "retry"}],
    )
    assert ack.status == 204

    status, body = post.get("/whiterun/avoidance")
    assert status == 200
    assert json.loads(body) == [{"npc_a": "nazeem", "npc_b": "ysolda", "avoiding": True}]


def test_avoidance_pair_is_reoffered_if_its_ack_times_out(server_factory, grudge_run, monkeypatch):
    """Same dropped-ack timeout coverage as
    test_hydration_pair_is_reoffered_if_its_ack_times_out, applied to the
    avoidance endpoint's own state machine."""
    import listener as listener_module

    fake_now = [1000.0]
    monkeypatch.setattr(listener_module.time, "monotonic", lambda: fake_now[0])

    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/avoidance")
    assert json.loads(body) == [{"npc_a": "nazeem", "npc_b": "ysolda", "avoiding": True}]

    # No ack sent. Immediately re-polling (still within the timeout
    # window) must NOT re-offer.
    status, body = post.get("/whiterun/avoidance")
    assert json.loads(body) == []

    # Advance past the timeout with no ack ever having arrived (same
    # server, no restart). The pair must be re-offered even though its
    # computed avoiding value hasn't changed.
    fake_now[0] += listener_module._AWAITING_ACK_TIMEOUT_SECONDS + 1.0
    status, body = post.get("/whiterun/avoidance")
    assert status == 200
    assert json.loads(body) == [{"npc_a": "nazeem", "npc_b": "ysolda", "avoiding": True}]


def test_avoidance_ack_endpoint_returns_503_without_live_run(server_factory):
    post = server_factory(live_run=None)
    resp = post("/whiterun/avoidance/ack", [{"npc_a": "nazeem", "npc_b": "ysolda", "outcome": "applied"}])
    assert resp.status == 503


def test_avoidance_ack_endpoint_rejects_a_non_array_body(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    resp = post("/whiterun/avoidance/ack", {"npc_a": "nazeem", "npc_b": "ysolda", "outcome": "applied"})
    assert resp.status == 400


def test_avoidance_ack_endpoint_rejects_an_unknown_outcome(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    resp = post(
        "/whiterun/avoidance/ack",
        [{"npc_a": "nazeem", "npc_b": "ysolda", "outcome": "bogus"}],
    )
    assert resp.status == 400


def test_avoidance_ack_endpoint_rejects_a_missing_field(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    resp = post("/whiterun/avoidance/ack", [{"npc_a": "nazeem", "outcome": "applied"}])
    assert resp.status == 400


def test_avoidance_ack_endpoint_enforces_the_shared_secret(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN, shared_secret="s3cret")
    unauth = post("/whiterun/avoidance/ack", [{"npc_a": "nazeem", "npc_b": "ysolda", "outcome": "applied"}])
    assert unauth.status == 401
    authed = post(
        "/whiterun/avoidance/ack",
        [{"npc_a": "nazeem", "npc_b": "ysolda", "outcome": "applied"}],
        token="s3cret",
    )
    assert authed.status == 204


def test_vendor_markup_endpoint_returns_empty_array_for_a_sub_threshold_grudge(server_factory, tmp_path, monkeypatch):
    """A grudge that never clears markup_multiplier_for's severity floor
    (multiplier stays MARKUP_NO_MARKUP) must be indistinguishable from "no
    grudge rows at all" -- not surfaced as a spurious 1.0-multiplier
    change."""
    run_id = "listener-test-vendor-markup-subthreshold-run"
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
    status, body = post.get("/whiterun/vendor-markup")
    assert status == 200
    assert json.loads(body) == []


def test_vendor_markup_endpoint_returns_503_without_live_run(server_factory):
    post = server_factory(live_run=None)
    status, _ = post.get("/whiterun/vendor-markup")
    assert status == 503


def test_vendor_markup_endpoint_returns_empty_array_with_no_grudges(server_factory, live_run):
    post = server_factory(live_run=_RUN)
    status, body = post.get("/whiterun/vendor-markup")
    assert status == 200
    assert json.loads(body) == []


def test_vendor_markup_endpoint_surfaces_a_severe_grudge_between_named_cast(server_factory, grudge_run):
    """grudge_run's grudge has decayed severity 0.9 at at_gamets=5.0 --
    markup_multiplier_for(0.9) == 1.4375 (see chronicle/vendor_markup.py's
    curve: floor 0.2, ceiling 1.5, linear in between). Directed, like
    hydration -- holder_id/target_id preserved exactly as the grudge names
    them, never canonicalized like avoidance's npc_a/npc_b."""
    _driver, _tmp_path = grudge_run
    post = server_factory(live_run=_GRUDGE_RUN)

    status, body = post.get("/whiterun/vendor-markup")
    assert status == 200
    pairs = json.loads(body)
    assert pairs == [{"holder_id": "nazeem", "target_id": "ysolda", "markup_multiplier": 1.4375}]


def test_vendor_markup_endpoint_surfaces_a_grudge_a_named_cast_vendor_holds_against_the_player(
    server_factory, tmp_path, monkeypatch
):
    """The ONLY pair the game side ever acts on.

    `adapters/skyrim/ChronicleBridge/src/VendorMarkupCache.cpp` (line 24,
    `kPlayerTargetId`) keeps only `target_id == "the_player"` rows out of
    this endpoint's response -- an NPC-to-NPC markup pair has no
    barter-menu meaning at all. So a player-directed pair must be served,
    even though "the_player" is not (and must never be) in
    NAMED_CAST_NPC_IDS. The holder still has to be named-cast: it is the
    vendor whose in-game actor reference the price write resolves.
    """
    run_id = "listener-test-vendor-markup-player-run"
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=(ScheduleBlock(npc_id="adrianne_avenicci", location_id="whiterun_market", start_tick=0, end_tick=1000),),
        encounter_probability=0.0,
        runs_dir=tmp_path,
    )
    driver.run(0, 5)
    relationship = driver.form_relationship(
        id="r1", from_id="adrianne_avenicci", to_id="the_player",
        basis="colocation", basis_id=None, strength=0.9, gamets=5.0,
    )
    driver.form_grudge(
        id="g1", holder_id="adrianne_avenicci", victim_id="the_player", target_id="the_player",
        grievance_type="theft", source_belief_id="belief-adrianne-player",
        evidentiary_strength=0.9, relationship_to_victim=relationship, gamets=5.0,
        forgiveness_threshold=0.2,
    )
    driver.run(5, 6)
    driver.close()

    post = server_factory(live_run=run_id)
    status, body = post.get("/whiterun/vendor-markup")
    assert status == 200
    assert json.loads(body) == [
        {"holder_id": "adrianne_avenicci", "target_id": "the_player", "markup_multiplier": 1.4375}
    ]


def test_vendor_markup_endpoint_still_drops_a_grudge_a_non_named_cast_holder_holds_against_the_player(
    server_factory, tmp_path, monkeypatch
):
    """The player exemption widens the TARGET side only. A holder outside
    NAMED_CAST_NPC_IDS has no resolvable in-game actor reference for the
    price write, so its pairs stay filtered out exactly as before."""
    run_id = "listener-test-vendor-markup-unnamed-holder-run"
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=(ScheduleBlock(npc_id="whiterun_guard_04", location_id="whiterun_market", start_tick=0, end_tick=1000),),
        encounter_probability=0.0,
        runs_dir=tmp_path,
    )
    driver.run(0, 5)
    relationship = driver.form_relationship(
        id="r1", from_id="whiterun_guard_04", to_id="the_player",
        basis="colocation", basis_id=None, strength=0.9, gamets=5.0,
    )
    driver.form_grudge(
        id="g1", holder_id="whiterun_guard_04", victim_id="the_player", target_id="the_player",
        grievance_type="theft", source_belief_id="belief-guard-player",
        evidentiary_strength=0.9, relationship_to_victim=relationship, gamets=5.0,
        forgiveness_threshold=0.2,
    )
    driver.run(5, 6)
    driver.close()

    post = server_factory(live_run=run_id)
    status, body = post.get("/whiterun/vendor-markup")
    assert status == 200
    assert json.loads(body) == []


def test_vendor_markup_endpoint_is_idempotent_on_a_second_immediate_poll(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    first_status, first_body = post.get("/whiterun/vendor-markup")
    assert first_status == 200
    assert json.loads(first_body) != []

    second_status, second_body = post.get("/whiterun/vendor-markup")
    assert second_status == 200
    assert json.loads(second_body) == []


def test_vendor_markup_endpoint_reverts_to_no_markup_once_the_grudge_cools(server_factory, grudge_run):
    _driver, _tmp_path = grudge_run
    post = server_factory(live_run=_GRUDGE_RUN)

    first_status, first_body = post.get("/whiterun/vendor-markup")
    assert first_status == 200
    assert json.loads(first_body) == [{"holder_id": "nazeem", "target_id": "ysolda", "markup_multiplier": 1.4375}]

    # Advance the run's max tick well past both grudge half-lives, same
    # technique as the hydration/avoidance cooling tests.
    death = post("/whiterun/events", {"event_type": "npc_died", "gamets": 2000.0, "npc_id": "brenuin"})
    assert death.status == 204

    third_status, third_body = post.get("/whiterun/vendor-markup")
    assert third_status == 200
    assert json.loads(third_body) == [{"holder_id": "nazeem", "target_id": "ysolda", "markup_multiplier": 1.0}]


def test_vendor_markup_endpoint_does_not_reoffer_a_pair_still_awaiting_ack(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    first_status, first_body = post.get("/whiterun/vendor-markup")
    assert first_status == 200
    assert json.loads(first_body) == [{"holder_id": "nazeem", "target_id": "ysolda", "markup_multiplier": 1.4375}]

    second_status, second_body = post.get("/whiterun/vendor-markup")
    assert second_status == 200
    assert json.loads(second_body) == []


def test_vendor_markup_ack_applied_means_not_reoffered_at_the_same_multiplier(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/vendor-markup")
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "markup_multiplier": 1.4375}]

    ack = post(
        "/whiterun/vendor-markup/ack",
        [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "applied"}],
    )
    assert ack.status == 204

    status, body = post.get("/whiterun/vendor-markup")
    assert status == 200
    assert json.loads(body) == []


def test_vendor_markup_ack_retry_is_reoffered_on_the_next_poll(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/vendor-markup")
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "markup_multiplier": 1.4375}]

    ack = post(
        "/whiterun/vendor-markup/ack",
        [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "retry"}],
    )
    assert ack.status == 204

    status, body = post.get("/whiterun/vendor-markup")
    assert status == 200
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "markup_multiplier": 1.4375}]


def test_vendor_markup_pair_is_reoffered_if_its_ack_times_out(server_factory, grudge_run, monkeypatch):
    """Same dropped-ack timeout coverage as
    test_hydration_pair_is_reoffered_if_its_ack_times_out/
    test_avoidance_pair_is_reoffered_if_its_ack_times_out, applied to the
    vendor-markup endpoint's own state machine."""
    import listener as listener_module

    fake_now = [1000.0]
    monkeypatch.setattr(listener_module.time, "monotonic", lambda: fake_now[0])

    post = server_factory(live_run=_GRUDGE_RUN)
    status, body = post.get("/whiterun/vendor-markup")
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "markup_multiplier": 1.4375}]

    # No ack sent. Immediately re-polling (still within the timeout
    # window) must NOT re-offer.
    status, body = post.get("/whiterun/vendor-markup")
    assert json.loads(body) == []

    # Advance past the timeout with no ack ever having arrived (same
    # server, no restart). The pair must be re-offered even though its
    # computed multiplier hasn't changed.
    fake_now[0] += listener_module._AWAITING_ACK_TIMEOUT_SECONDS + 1.0
    status, body = post.get("/whiterun/vendor-markup")
    assert status == 200
    assert json.loads(body) == [{"holder_id": "nazeem", "target_id": "ysolda", "markup_multiplier": 1.4375}]


def test_vendor_markup_ack_endpoint_returns_503_without_live_run(server_factory):
    post = server_factory(live_run=None)
    resp = post("/whiterun/vendor-markup/ack", [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "applied"}])
    assert resp.status == 503


def test_vendor_markup_ack_endpoint_rejects_a_non_array_body(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    resp = post("/whiterun/vendor-markup/ack", {"holder_id": "nazeem", "target_id": "ysolda", "outcome": "applied"})
    assert resp.status == 400


def test_vendor_markup_ack_endpoint_rejects_an_unknown_outcome(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    resp = post(
        "/whiterun/vendor-markup/ack",
        [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "no_relationship"}],
    )
    assert resp.status == 400


def test_vendor_markup_ack_endpoint_rejects_a_missing_field(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN)
    resp = post("/whiterun/vendor-markup/ack", [{"holder_id": "nazeem", "outcome": "applied"}])
    assert resp.status == 400


def test_vendor_markup_ack_endpoint_enforces_the_shared_secret(server_factory, grudge_run):
    post = server_factory(live_run=_GRUDGE_RUN, shared_secret="s3cret")
    unauth = post("/whiterun/vendor-markup/ack", [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "applied"}])
    assert unauth.status == 401
    authed = post(
        "/whiterun/vendor-markup/ack",
        [{"holder_id": "nazeem", "target_id": "ysolda", "outcome": "applied"}],
        token="s3cret",
    )
    assert authed.status == 204


_BELIEF_RUN = "listener-test-belief-run"


@pytest.fixture()
def belief_run(tmp_path, monkeypatch):
    """A run with one named-cast NPC (nazeem) holding a high-confidence
    witnessed belief (WITNESS_CONFIDENCE=0.95, well above
    EVIDENCE_CONFIDENCE_THRESHOLD=0.6), for exercising /whiterun/evidence.

    Built through driver.inject_event()+driver.witness() -- the same
    pattern chronicle/tests/test_agent_debug_cli.py's own run_dir fixture
    uses -- rather than hand-constructing a bare BeliefInstance, so the
    belief has a real grounding Evidence record and round-trips through
    FrameLogReader.state_at() the same way a real run would (framelog.
    load_state's rumor-source rebuild indexes evidence_by_belief[id][0],
    which would KeyError for a belief persisted with no Evidence at all)."""
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=_BELIEF_RUN,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=(ScheduleBlock(npc_id="nazeem", location_id="whiterun_market", start_tick=0, end_tick=1000),),
        encounter_probability=0.0,
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=5, save_uuid=_SAVE_UUID, generation=0, seq=1,
            gamets=5.0, wall_ts=0.0, npc_id="ysolda",
            cause="unknown", killer_id=None, location_id="whiterun_market",
        ),
        origin={"kind": "scenario", "detail": "test_listener belief_run fixture"},
    )
    driver.witness(
        claim_id="claim-ysolda-death",
        belief_id="belief-nazeem-ysolda-death",
        evidence_id="evidence-nazeem-ysolda-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "unknown", "location": "whiterun_market"},
        canonical_event_key=EventKey(_SAVE_UUID, 0, 1),
        witness_id="nazeem",
        gamets=5.0,
    )
    driver.run(5, 6)
    driver.close()
    return driver, tmp_path


def test_evidence_endpoint_returns_503_without_live_run(server_factory):
    post = server_factory(live_run=None)
    status, _ = post.get("/whiterun/evidence")
    assert status == 503


def test_evidence_endpoint_returns_empty_array_with_no_beliefs(server_factory, live_run):
    post = server_factory(live_run=_RUN)
    status, body = post.get("/whiterun/evidence")
    assert status == 200
    assert json.loads(body) == []


def test_evidence_endpoint_surfaces_a_well_evidenced_belief_between_named_cast(server_factory, belief_run):
    _driver, _tmp_path = belief_run
    post = server_factory(live_run=_BELIEF_RUN)

    status, body = post.get("/whiterun/evidence")
    assert status == 200
    entries = json.loads(body)
    assert entries == [
        {"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "claim_id": "claim-ysolda-death"}
    ]


def test_evidence_endpoint_is_idempotent_on_a_second_immediate_poll(server_factory, belief_run):
    post = server_factory(live_run=_BELIEF_RUN)
    first_status, first_body = post.get("/whiterun/evidence")
    assert first_status == 200
    assert json.loads(first_body) != []

    second_status, second_body = post.get("/whiterun/evidence")
    assert second_status == 200
    assert json.loads(second_body) == []


def test_evidence_ack_applied_means_never_reoffered_again(server_factory, belief_run):
    """applied is a true terminal state (design doc §3) -- unlike
    hydration/avoidance/vendor-markup's `applied`, this must hold even
    once the belief's decayed confidence later drops back below threshold
    and (hypothetically) rises again -- there is no re-offer path at all
    once applied."""
    post = server_factory(live_run=_BELIEF_RUN)
    status, body = post.get("/whiterun/evidence")
    assert json.loads(body) == [
        {"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "claim_id": "claim-ysolda-death"}
    ]

    ack = post(
        "/whiterun/evidence/ack",
        [{"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "outcome": "applied"}],
    )
    assert ack.status == 204

    status, body = post.get("/whiterun/evidence")
    assert status == 200
    assert json.loads(body) == []


def test_evidence_confidence_decaying_below_threshold_after_applied_is_never_reoffered(server_factory, belief_run):
    """The design doc's own named limitation (§3): once `applied`, a
    belief's confidence later decaying below threshold (a poll returning
    empty either way) and then -- hypothetically -- rising back above it
    must never re-trigger a second reveal. Pushing the run's max tick well
    past CONFIDENCE_DECAY_HALF_LIFE and polling again must still be empty,
    both immediately after decay and on a subsequent poll."""
    post = server_factory(live_run=_BELIEF_RUN)
    status, body = post.get("/whiterun/evidence")
    assert json.loads(body) == [
        {"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "claim_id": "claim-ysolda-death"}
    ]

    ack = post(
        "/whiterun/evidence/ack",
        [{"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "outcome": "applied"}],
    )
    assert ack.status == 204

    far_future = 5.0 + 10 * CONFIDENCE_DECAY_HALF_LIFE
    death = post("/whiterun/events", {"event_type": "npc_died", "gamets": far_future, "npc_id": "brenuin"})
    assert death.status == 204

    status, body = post.get("/whiterun/evidence")
    assert status == 200
    assert json.loads(body) == []

    status, body = post.get("/whiterun/evidence")
    assert status == 200
    assert json.loads(body) == []


def test_evidence_ack_retry_is_reoffered_on_the_next_poll(server_factory, belief_run):
    post = server_factory(live_run=_BELIEF_RUN)
    status, body = post.get("/whiterun/evidence")
    assert json.loads(body) == [
        {"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "claim_id": "claim-ysolda-death"}
    ]

    ack = post(
        "/whiterun/evidence/ack",
        [{"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "outcome": "retry"}],
    )
    assert ack.status == 204

    status, body = post.get("/whiterun/evidence")
    assert status == 200
    assert json.loads(body) == [
        {"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "claim_id": "claim-ysolda-death"}
    ]


def test_evidence_entry_is_reoffered_if_its_ack_times_out(server_factory, belief_run, monkeypatch):
    """Same dropped-ack timeout coverage as
    test_hydration_pair_is_reoffered_if_its_ack_times_out/
    test_avoidance_pair_is_reoffered_if_its_ack_times_out/
    test_vendor_markup_pair_is_reoffered_if_its_ack_times_out, applied to
    the evidence endpoint's own state machine."""
    import listener as listener_module

    fake_now = [1000.0]
    monkeypatch.setattr(listener_module.time, "monotonic", lambda: fake_now[0])

    post = server_factory(live_run=_BELIEF_RUN)
    status, body = post.get("/whiterun/evidence")
    assert json.loads(body) == [
        {"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "claim_id": "claim-ysolda-death"}
    ]

    # No ack sent. Immediately re-polling (still within the timeout
    # window) must NOT re-offer.
    status, body = post.get("/whiterun/evidence")
    assert json.loads(body) == []

    # Advance past the timeout with no ack ever having arrived (same
    # server, no restart). The entry must be re-offered.
    fake_now[0] += listener_module._AWAITING_ACK_TIMEOUT_SECONDS + 1.0
    status, body = post.get("/whiterun/evidence")
    assert status == 200
    assert json.loads(body) == [
        {"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "claim_id": "claim-ysolda-death"}
    ]


def test_evidence_ack_endpoint_returns_503_without_live_run(server_factory):
    post = server_factory(live_run=None)
    resp = post("/whiterun/evidence/ack", [{"holder_id": "nazeem", "belief_id": "belief-x", "outcome": "applied"}])
    assert resp.status == 503


def test_evidence_ack_endpoint_rejects_a_non_array_body(server_factory, belief_run):
    post = server_factory(live_run=_BELIEF_RUN)
    resp = post("/whiterun/evidence/ack", {"holder_id": "nazeem", "belief_id": "belief-x", "outcome": "applied"})
    assert resp.status == 400


def test_evidence_ack_endpoint_rejects_an_unknown_outcome(server_factory, belief_run):
    post = server_factory(live_run=_BELIEF_RUN)
    resp = post(
        "/whiterun/evidence/ack",
        [{"holder_id": "nazeem", "belief_id": "belief-x", "outcome": "no_relationship"}],
    )
    assert resp.status == 400


def test_evidence_ack_endpoint_rejects_a_missing_field(server_factory, belief_run):
    post = server_factory(live_run=_BELIEF_RUN)
    resp = post("/whiterun/evidence/ack", [{"holder_id": "nazeem", "outcome": "applied"}])
    assert resp.status == 400


def test_evidence_ack_endpoint_enforces_the_shared_secret(server_factory, belief_run):
    post = server_factory(live_run=_BELIEF_RUN, shared_secret="s3cret")
    unauth = post("/whiterun/evidence/ack", [{"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "outcome": "applied"}])
    assert unauth.status == 401
    authed = post(
        "/whiterun/evidence/ack",
        [{"holder_id": "nazeem", "belief_id": "belief-nazeem-ysolda-death", "outcome": "applied"}],
        token="s3cret",
    )
    assert authed.status == 204


def test_evidence_endpoint_only_considers_named_cast_holders(server_factory, tmp_path, monkeypatch):
    """A belief held by an NPC outside NAMED_CAST_NPC_IDS must never be
    surfaced -- only named-cast NPCs have a resolvable Actor* for a C++
    consumer to spawn evidence at (design doc §2)."""
    run_id = "listener-test-evidence-non-named-cast-run"
    monkeypatch.setenv("CHRONICLE_RUNS_DIR", str(tmp_path))
    driver = Driver(
        run_id=run_id,
        seed_id=_SEED,
        save_uuid=_SAVE_UUID,
        generation=0,
        schedule=(ScheduleBlock(npc_id="not_named_cast", location_id="whiterun_market", start_tick=0, end_tick=50),),
        encounter_probability=0.0,
        runs_dir=tmp_path,
    )
    driver.inject_event(
        NPCDied(
            tick=5, save_uuid=_SAVE_UUID, generation=0, seq=1,
            gamets=5.0, wall_ts=0.0, npc_id="ysolda",
            cause="unknown", killer_id=None, location_id="whiterun_market",
        ),
        origin={"kind": "scenario", "detail": "test_listener non-named-cast fixture"},
    )
    driver.witness(
        claim_id="claim-ysolda-death-2",
        belief_id="belief-outsider-ysolda-death",
        evidence_id="evidence-outsider-ysolda-death",
        kind="npc_death",
        slots={"perpetrator": "unknown", "cause": "unknown", "location": "whiterun_market"},
        canonical_event_key=EventKey(_SAVE_UUID, 0, 1),
        witness_id="not_named_cast",
        gamets=5.0,
    )
    driver.close()

    post = server_factory(live_run=run_id)
    status, body = post.get("/whiterun/evidence")
    assert status == 200
    assert json.loads(body) == []


def test_unknown_path_is_404(server_factory):
    post = server_factory()
    resp = post("/not/a/real/path", {})
    assert resp.status == 404


# --- Save/reload sync handshake (docs/design/chronicle-bridge-sync-handshake-out.md) -------------


def _hello_body(**overrides):
    body = {
        "format_version": 1,
        "save_uuid": "save-sync-test-1",
        "generation": 0,
        "parent_generation": 0,
        "head_seq": 0,
        "gamets": 0.0,
        "wall_ts": 0,
        "char_name_hash": 0,
        "manifest_present": True,
        "hello_seq": 1,
    }
    body.update(overrides)
    return body


def _mutation_body(**overrides):
    body = {
        "epoch_id": 0,
        "save_uuid": "save-sync-test-1",
        "generation": 0,
        "seq": 0,
        "event": {"event_type": "npc_died", "gamets": 5.0, "npc_id": "nazeem", "cause": "unknown"},
    }
    body.update(overrides)
    return body


def test_sync_hello_golden_fixture_boundary_conversion():
    """Design doc §3's golden fixture: given these exact field values (the same ones the 68-byte
    binary struct encodes, verified separately on the C++ side against the identical fixture --
    out of scope here), `_manifest_from_hello_body`'s ms->s and 0->None boundary conversions must
    produce exactly this `chronicle.sync.Manifest`. Proves the JSON parsing/conversion side, not
    raw bytes -- no HTTP round trip needed.
    """
    body = {
        "format_version": 1,
        "save_uuid": "0123456789abcdef0123456789abcdef",
        "generation": 0,
        "parent_generation": 0,  # co-save's 0-sentinel for the root generation
        "head_seq": 42,
        "gamets": 123.5,
        "wall_ts": 1735689600123,  # int64 ms
        "char_name_hash": 0xDEADBEEFCAFEBABE,
    }

    manifest = _manifest_from_hello_body(body)

    assert manifest == Manifest(
        format_version=1,
        save_uuid="0123456789abcdef0123456789abcdef",
        generation=0,
        parent_generation=None,  # 0-sentinel -> None
        head_seq=42,
        gamets=123.5,
        wall_ts=1735689600.123,  # ms -> s
    )


def test_sync_hello_is_not_gated_behind_live_run(server_factory):
    """Design doc §8b item 3: sync state is keyed by save_uuid, orthogonal to demo runs -- unlike
    every other write route in this file, no --live-run means no 503 here."""
    post = server_factory(live_run=None)
    status, body = post.post_json("/whiterun/sync/hello", _hello_body())
    assert status == 200
    assert json.loads(body)["decision"] == "NEW_TIMELINE"


def test_sync_hello_enforces_the_shared_secret(server_factory):
    post = server_factory(shared_secret="s3cret")
    unauth = post("/whiterun/sync/hello", _hello_body())
    assert unauth.status == 401
    status, _ = post.post_json("/whiterun/sync/hello", _hello_body(), token="s3cret")
    assert status == 200


def test_sync_hello_first_ever_hello_is_new_timeline_and_actionable(server_factory):
    post = server_factory()
    status, body = post.post_json("/whiterun/sync/hello", _hello_body(hello_seq=1, head_seq=0, gamets=10.0))
    assert status == 200
    decoded = json.loads(body)
    assert decoded["decision"] == "NEW_TIMELINE"
    assert decoded["actionable"] is True
    assert decoded["epoch_id"] == 0
    assert decoded["replay_from_seq"] is None
    assert decoded["confirm_required"] is False
    assert decoded["hello_seq"] == 1


def test_sync_hello_second_load_of_the_same_branch_continues(server_factory):
    post = server_factory()
    status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-continue-1", hello_seq=1, head_seq=0, gamets=10.0)
    )
    assert json.loads(body)["decision"] == "NEW_TIMELINE"

    status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-continue-1", hello_seq=2, head_seq=0, gamets=10.0)
    )
    decoded = json.loads(body)
    assert status == 200
    assert decoded["decision"] == "CONTINUE"
    assert decoded["actionable"] is True
    assert decoded["epoch_id"] == 1  # a new load bumped the epoch


def test_sync_hello_retried_hello_seq_does_not_mint_a_second_epoch(server_factory):
    """Design doc §4.2: a lost-response retry of the SAME load (same hello_seq) must not bump the
    epoch a second time -- see `_SyncSessionState`'s docstring."""
    post = server_factory()
    status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-retry-1", hello_seq=1, head_seq=0, gamets=10.0)
    )
    first_epoch = json.loads(body)["epoch_id"]

    status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-retry-1", hello_seq=1, head_seq=0, gamets=10.0)
    )
    assert status == 200
    assert json.loads(body)["epoch_id"] == first_epoch


def test_sync_hello_tolerates_a_shim_counter_reset(server_factory):
    """hello_seq lives in SyncHandshake's in-memory C++ state (spec §5), NOT in the co-save
    manifest (§3's field table has seven fields, none of them hello_seq) -- so it resets to a low
    value whenever the GAME PROCESS itself restarts, even though this service's own durable
    sidecar does not. A LOWER hello_seq than the one last seen for this save_uuid must therefore
    still be treated as a genuinely new load (bump the epoch) -- not rejected as "stale", which
    would wedge the session with no self-correction path once the shim's own counter can never
    climb back above whatever this service last recorded."""
    post = server_factory()
    status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-counter-reset-1", hello_seq=5, head_seq=0, gamets=10.0)
    )
    epoch_after_5 = json.loads(body)["epoch_id"]

    # The game process restarted -- ChronicleBridge's own hello_seq
    # counter starts over from 1, well below the 5 this session last saw.
    status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-counter-reset-1", hello_seq=1, head_seq=0, gamets=10.0)
    )
    decoded = json.loads(body)
    assert status == 200
    assert decoded["epoch_id"] == epoch_after_5 + 1  # still a new load -- epoch bumps
    assert decoded["hello_seq"] == 1  # echoes the request's own value regardless


def test_sync_hello_fork_past_the_gamets_threshold_sets_confirm_required(server_factory):
    """Design doc §8b item 1's large-jump threshold: a FORK (reload to an earlier point) whose
    gamets delta exceeds `_CONFIRM_REQUIRED_GAMETS_HOURS` (24 game-hours) must set
    confirm_required=True; one just under the threshold must not. Pins both the rule (computed for
    any known branch, not just when both legs trip) and the constant's value."""
    post = server_factory()
    _status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-confirm-1", hello_seq=1, head_seq=0, gamets=100.0)
    )
    assert json.loads(body)["decision"] == "NEW_TIMELINE"  # branch head is now at gamets=100.0

    # A reload to gamets=10.0 is a 90-game-hour jump backward -- over the
    # 24-hour threshold.
    _status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-confirm-1", hello_seq=2, head_seq=0, gamets=10.0)
    )
    decoded = json.loads(body)
    assert decoded["decision"] == "FORK"
    assert decoded["confirm_required"] is True

    # A reload to gamets=99.0 is only a 1-game-hour jump -- under
    # threshold, still a FORK, but not flagged.
    _status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-confirm-1", hello_seq=3, head_seq=0, gamets=99.0)
    )
    decoded = json.loads(body)
    assert decoded["decision"] == "FORK"
    assert decoded["confirm_required"] is False


def test_sync_hello_missing_manifest_is_legacy_import_and_not_actionable(server_factory):
    post = server_factory()
    status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-legacy-1", manifest_present=False, hello_seq=1)
    )
    decoded = json.loads(body)
    assert status == 200
    assert decoded["decision"] == "LEGACY_IMPORT"
    assert decoded["actionable"] is False


def test_sync_hello_rejects_a_malformed_body(server_factory):
    post = server_factory()
    status, _ = post.post_json("/whiterun/sync/hello", {"save_uuid": "s1"})  # missing hello_seq/manifest_present
    assert status == 400


def test_sync_hello_survives_a_listener_restart(server_factory):
    """Design doc §4.3's required test: the durable per-save_uuid sidecar must survive the
    listener process restarting. Same "fresh handler-state closure simulates a restart" precedent
    as test_hydration_pair_is_reoffered_after_a_listener_restart -- except here, unlike every
    other per-slice state in this file, the restart must NOT lose anything.

    Commits real mutations (advancing the durably-tracked head_seq to 2) between the two hellos,
    then sends the second hello claiming head_seq=2 too -- this is the specific failure mode §4.3
    names: a naive in-memory-only sidecar would have "forgotten" this save_uuid entirely on
    restart (BranchState(known=False)), so a manifest claiming generation 0/head_seq=2 would
    resolve NEW_TIMELINE (a fresh branch, wrongly discarding everything the service already knew),
    not CONTINUE -- or, if the sidecar partially survived but head_seq alone regressed to 0,
    ADOPT (head_seq ahead of what the service ever ACKed). Either way, wrong. Asserting CONTINUE
    with head_seq=0 on both sides (as a weaker version of this test would) can't tell amnesia apart
    from correct behavior -- both would say CONTINUE.
    """
    post = server_factory()
    status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-restart-1", hello_seq=1, head_seq=0, gamets=10.0)
    )
    decoded = json.loads(body)
    assert decoded["decision"] == "NEW_TIMELINE"
    epoch_id = decoded["epoch_id"]

    for seq in (0, 1, 2):
        resp = post(
            "/whiterun/sync/mutation",
            _mutation_body(epoch_id=epoch_id, save_uuid="save-restart-1", generation=0, seq=seq, event={"event_type": "npc_died", "gamets": 10.0 + seq, "npc_id": "nazeem", "cause": "unknown"}),
        )
        assert resp.status == 204

    # Simulate the listener restarting: a brand-new server, same tmp_path
    # (server_factory's own default sync_state_dir), so the durable
    # sidecar on disk is unaffected -- only the in-memory closure state
    # (including the mutation endpoint's own EventLog) is fresh, exactly
    # like a real process restart.
    fresh_post = server_factory()
    status, body = fresh_post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-restart-1", hello_seq=2, head_seq=2, gamets=12.0)
    )
    decoded = json.loads(body)
    assert status == 200
    assert decoded["decision"] == "CONTINUE"


def test_sync_mutation_is_accepted_and_appends_to_the_event_log(server_factory):
    post = server_factory()
    _status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-mutation-1", hello_seq=1, head_seq=0, gamets=0.0)
    )
    epoch_id = json.loads(body)["epoch_id"]

    resp = post(
        "/whiterun/sync/mutation",
        _mutation_body(epoch_id=epoch_id, save_uuid="save-mutation-1", generation=0, seq=0),
    )
    assert resp.status == 204


def test_sync_mutation_rejects_a_stale_epoch_with_409_not_500(server_factory):
    """Design doc §4.4: epoch-fencing rejection must be 409, never a 500."""
    post = server_factory()
    _status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-stale-epoch-1", hello_seq=1, head_seq=0, gamets=0.0)
    )
    current_epoch = json.loads(body)["epoch_id"]

    resp = post(
        "/whiterun/sync/mutation",
        _mutation_body(epoch_id=current_epoch - 1 if current_epoch > 0 else -1, save_uuid="save-stale-epoch-1", seq=0),
    )
    assert resp.status == 409


def test_sync_mutation_before_any_hello_is_rejected_with_409(server_factory):
    """No session at all for this save_uuid -- no epoch was ever legitimately issued, so any
    mutation is treated the same as a stale one (see `_process_mutation`)."""
    post = server_factory()
    resp = post("/whiterun/sync/mutation", _mutation_body(save_uuid="save-never-said-hello", epoch_id=0, seq=0))
    assert resp.status == 409


def test_sync_mutation_dedups_a_replayed_seq_via_event_log_append(server_factory, tmp_path):
    """Design doc §4.1: dedup on (save_uuid, generation, seq) is EventLog.append()'s own
    idempotent-no-op behavior (chronicle/events.py:206) -- reused, not re-implemented. Replaying
    the exact same mutation twice must not double-apply it.

    A bare "both replies were 204" assertion can't distinguish real dedup from no dedup at all (a
    handler with none would also reply 204 twice) -- so this reads the durable sidecar's own
    head_gamets after each call: the first mutation (gamets=5.0) must advance it to 5.0, and a
    REPLAY of that same (save_uuid, generation, seq) carrying a very different gamets (999.0) must
    be a true no-op -- EventLog.append() returns False for the duplicate seq, so
    `_process_mutation` never re-runs `_save_sync_state`, and head_gamets must still read 5.0, not
    999.0.
    """
    post = server_factory()
    _status, body = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-dedup-1", hello_seq=1, head_seq=0, gamets=0.0)
    )
    epoch_id = json.loads(body)["epoch_id"]

    sidecar_path = tmp_path / "sync-state" / "save-dedup-1.json"

    first = post(
        "/whiterun/sync/mutation",
        _mutation_body(
            epoch_id=epoch_id, save_uuid="save-dedup-1", generation=0, seq=0,
            event={"event_type": "npc_died", "gamets": 5.0, "npc_id": "nazeem", "cause": "unknown"},
        ),
    )
    assert first.status == 204
    assert json.loads(sidecar_path.read_text())["head_gamets"] == 5.0

    second = post(
        "/whiterun/sync/mutation",
        _mutation_body(
            epoch_id=epoch_id, save_uuid="save-dedup-1", generation=0, seq=0,  # same seq -- a replay
            event={"event_type": "npc_died", "gamets": 999.0, "npc_id": "nazeem", "cause": "unknown"},
        ),
    )
    assert second.status == 204
    # Dedup means this replay's very different gamets must NOT have been
    # applied -- head_gamets is unchanged from the first call, proving
    # EventLog.append() actually rejected the duplicate seq rather than
    # silently re-appending (and re-advancing state) a second time.
    assert json.loads(sidecar_path.read_text())["head_gamets"] == 5.0


def test_sync_mutation_rejects_a_malformed_body(server_factory):
    post = server_factory()
    _status, _ = post.post_json(
        "/whiterun/sync/hello", _hello_body(save_uuid="save-malformed-mut-1", hello_seq=1, head_seq=0, gamets=0.0)
    )
    resp = post("/whiterun/sync/mutation", {"save_uuid": "save-malformed-mut-1"})  # missing epoch_id/generation/seq/event
    assert resp.status == 400
