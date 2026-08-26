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
from listener import _make_handler  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from chronicle.driver import Driver  # noqa: E402
from chronicle.events import NPCDied  # noqa: E402
from chronicle.framelog import FrameLogReader  # noqa: E402
from chronicle.schedule import ScheduleBlock  # noqa: E402

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


def test_unknown_path_is_404(server_factory):
    post = server_factory()
    resp = post("/not/a/real/path", {})
    assert resp.status == 404
