"""Unit tests for the live-harness DevBench client, with no game and no server.

Every canned response below is copied from the DevBench v1.15.1 API cheat
sheet (request/response shapes read out of that project's source), so these
tests lock in the *real* wire format -- including its traps: a bare JSON array
from ``/api/tools``, a scenario transcript whose HTTP status is 200 while
``ok`` is false, ``inspect refs`` returning ``count:0`` instead of a 404, and
the ``{"error","code"}`` flat error envelope.
"""

from __future__ import annotations

import json
import urllib.error

import pytest

from adapters.skyrim.livetest.devbench import DevBench, DevBenchError, ScenarioFailed

HEALTH = {
    "ok": True,
    "lastLifecycle": "postLoadGame",
    "frame": 12345,
    "lastTaskFrame": 12340,
    "pendingTasks": 0,
    "pid": 4242,
    "port": 8920,
    "exe": "SkyrimSE.exe",
    "vr": False,
}

TOOLS = [
    {"name": "console", "description": "...", "inputSchema": {}, "readOnly": False},
    {"name": "inspect", "description": "...", "inputSchema": {}, "readOnly": True},
]

MODS = {
    "count": 2,
    "lightCount": 1,
    "total": 3,
    "plugins": [{"index": 0, "name": "Skyrim.esm"}, {"index": 5, "name": "ChroniclePatcher.esp"}],
    "lightPlugins": [{"index": 12, "name": "MyMod.esl"}],
}


class FakeClock:
    """Injected monotonic + sleep so retry/poll tests cost no wall time."""

    def __init__(self) -> None:
        self.t = 1000.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.t

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.t += seconds


class FakeOpener:
    """``(method, url, body, timeout) -> (status, bytes)`` with scripted replies."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls: list[dict] = []

    def __call__(self, method, url, body, timeout):
        self.calls.append(
            {
                "method": method,
                "url": url,
                "body": json.loads(body) if body else body,
                "raw_body": body,
                "timeout": timeout,
            }
        )
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        if isinstance(reply, Exception):
            raise reply
        status, payload = reply
        if isinstance(payload, (dict, list)):
            payload = json.dumps(payload).encode("utf-8")
        return status, payload


def make(*replies, clock=None):
    opener = FakeOpener(replies)
    clock = clock or FakeClock()
    db = DevBench(opener=opener, sleep=clock.sleep, monotonic=clock.monotonic)
    return db, opener, clock


# --------------------------------------------------------------------------
# transport + error taxonomy
# --------------------------------------------------------------------------


def test_health_is_a_get_with_no_body():
    db, opener, _ = make((200, HEALTH))
    assert db.health()["frame"] == 12345
    call = opener.calls[0]
    assert call["method"] == "GET"
    assert call["url"] == "http://127.0.0.1:8920/api/health"
    assert call["raw_body"] is None


def test_tools_returns_the_bare_array():
    db, _, _ = make((200, TOOLS))
    tools = db.tools()
    assert isinstance(tools, list)
    assert [t["name"] for t in tools] == ["console", "inspect"]


def test_call_always_posts_a_json_body_even_with_no_args():
    db, opener, _ = make((200, {"ok": True}))
    db.call("menu")
    call = opener.calls[0]
    assert call["method"] == "POST"
    assert call["url"] == "http://127.0.0.1:8920/api/tool/menu"
    assert call["body"] == {}
    assert call["raw_body"] == b"{}"


def test_http_error_message_names_status_and_body_error():
    db, _, _ = make((404, {"error": "unknown tool 'nope'", "code": 404}))
    with pytest.raises(DevBenchError) as excinfo:
        db.call("nope")
    exc = excinfo.value
    assert exc.code == 404
    assert exc.kind == "http"
    assert "HTTP 404" in str(exc)
    assert "unknown tool 'nope'" in str(exc)


def test_400_envelope_without_a_code_key_still_yields_the_status():
    db, _, _ = make((400, {"error": "invalid JSON body: unexpected end of input"}))
    with pytest.raises(DevBenchError) as excinfo:
        db.call("console", action="exec")
    assert excinfo.value.code == 400
    assert "invalid JSON body" in str(excinfo.value)


def test_empty_non_json_error_body_does_not_crash_the_error_path():
    db, _, _ = make((400, b""))
    with pytest.raises(DevBenchError) as excinfo:
        db.call("console")
    assert excinfo.value.code == 400
    assert "HTTP 400" in str(excinfo.value)


def test_unreachable_message_is_distinct():
    db, _, _ = make(urllib.error.URLError("Connection refused"))
    with pytest.raises(DevBenchError) as excinfo:
        db.health()
    exc = excinfo.value
    assert exc.kind == "unreachable"
    assert exc.code is None
    assert "could not reach DevBench" in str(exc)


def test_connection_closed_message_is_distinct():
    import http.client

    db, _, _ = make(http.client.RemoteDisconnected("Remote end closed connection"))
    with pytest.raises(DevBenchError) as excinfo:
        db.health()
    assert excinfo.value.kind == "closed"
    assert "closed without an HTTP response" in str(excinfo.value)


def test_timeout_message_is_distinct():
    db, _, _ = make(TimeoutError("timed out"))
    with pytest.raises(DevBenchError) as excinfo:
        db.health()
    assert excinfo.value.kind == "timeout"
    assert "did not respond within" in str(excinfo.value)


def test_all_four_error_messages_differ():
    import http.client

    messages = set()
    for failure in (
        (500, {"error": "boom", "code": 500}),
        urllib.error.URLError("refused"),
        http.client.RemoteDisconnected("bye"),
        TimeoutError("slow"),
    ):
        db, _, _ = make(failure)
        with pytest.raises(DevBenchError) as excinfo:
            db.health()
        messages.add(str(excinfo.value))
    assert len(messages) == 4


# --------------------------------------------------------------------------
# call_retry
# --------------------------------------------------------------------------


def test_call_retry_retries_a_504_then_succeeds():
    clock = FakeClock()
    db, opener, _ = make(
        (504, {"error": "main-thread task did not run within 5000ms", "code": 504}),
        (504, {"error": "main-thread task did not run within 5000ms", "code": 504}),
        (200, {"playerLoaded": True}),
        clock=clock,
    )
    assert db.call_retry("inspect", kind="state") == {"playerLoaded": True}
    assert len(opener.calls) == 3
    assert clock.slept == [0.5, 1.0]


def test_call_retry_does_not_retry_a_404():
    db, opener, _ = make((404, {"error": "unknown tool", "code": 404}))
    with pytest.raises(DevBenchError):
        db.call_retry("nope")
    assert len(opener.calls) == 1


def test_call_retry_does_not_retry_a_timeout():
    db, opener, _ = make(TimeoutError("slow"))
    with pytest.raises(DevBenchError) as excinfo:
        db.call_retry("inspect", kind="state")
    assert excinfo.value.kind == "timeout"
    assert len(opener.calls) == 1


def test_call_retry_retries_unreachable_and_gives_up_at_the_deadline():
    clock = FakeClock()
    db, opener, _ = make(urllib.error.URLError("refused"), clock=clock)
    with pytest.raises(DevBenchError) as excinfo:
        db.call_retry("inspect", deadline_s=3.0, kind="state")
    assert excinfo.value.kind == "unreachable"
    assert len(opener.calls) > 1
    assert max(clock.slept) <= 4.0


# --------------------------------------------------------------------------
# inspect wrappers
# --------------------------------------------------------------------------


def test_ref_returns_none_when_count_is_zero():
    db, opener, _ = make((200, {"count": 0, "refs": []}))
    assert db.ref("0xDEADBEEF") is None
    assert opener.calls[0]["body"] == {"kind": "refs", "formId": "0xDEADBEEF"}


def test_ref_returns_the_single_ref():
    ref = {"formId": "0x0001A6A2", "formType": "ACHR", "name": "Balgruuf the Greater"}
    db, _, _ = make((200, {"count": 1, "refs": [ref]}))
    assert db.ref("WEBalgruuf") == ref


def test_selected_ref_uses_the_selected_flag():
    db, opener, _ = make((200, {"source": "selected", "count": 1, "refs": [{"formId": "0x14"}]}))
    assert db.selected_ref() == {"formId": "0x14"}
    assert opener.calls[0]["body"] == {"kind": "refs", "selected": True}


def test_refs_omits_none_filters_and_unwraps_the_list():
    db, opener, _ = make((200, {"count": 812, "returned": 2, "truncated": True, "refs": [{"a": 1}, {"b": 2}]}))
    assert db.refs() == [{"a": 1}, {"b": 2}]
    assert opener.calls[0]["body"] == {"kind": "refs", "limit": 100}


def test_refs_passes_form_type_and_radius_when_given():
    db, opener, _ = make((200, {"count": 0, "refs": []}))
    db.refs(form_type="Actor", radius=4096, limit=200)
    assert opener.calls[0]["body"] == {"kind": "refs", "limit": 200, "formType": "Actor", "radius": 4096}


def test_state_scene_player_mods_use_their_kinds():
    for method, kind in (("state", "state"), ("scene", "scene"), ("player", "player"), ("mods", "mods")):
        db, opener, _ = make((200, {"playerLoaded": True}))
        getattr(db, method)()
        assert opener.calls[0]["body"] == {"kind": kind}


# --------------------------------------------------------------------------
# console
# --------------------------------------------------------------------------


def test_console_is_fire_and_forget_exec():
    db, opener, _ = make((200, {"queued": True, "command": "coc WhiterunOrigin", "capturing": False}))
    assert db.console("coc WhiterunOrigin")["queued"] is True
    assert opener.calls[0]["body"] == {"action": "exec", "command": "coc WhiterunOrigin"}


def test_console_capture_rereads_once_when_markers_are_missing():
    clock = FakeClock()
    db, opener, _ = make(
        (200, {"queued": True, "capturing": True}),
        (200, {"markersFound": False, "sawBegin": False, "sawEnd": False, "count": 0, "lines": []}),
        (200, {"markersFound": True, "sawBegin": True, "sawEnd": True, "count": 2, "lines": ["a", "b"]}),
        clock=clock,
    )
    assert db.console_capture("help nonce", settle_s=0.25) == ["a", "b"]
    assert [c["body"]["action"] for c in opener.calls] == ["exec", "read", "read"]
    assert opener.calls[0]["body"]["capture"] is True
    assert clock.slept == [0.25, 0.25]


def test_console_capture_returns_on_the_first_read_when_markers_are_found():
    clock = FakeClock()
    db, opener, _ = make(
        (200, {"queued": True, "capturing": True}),
        (200, {"markersFound": True, "count": 1, "lines": ["350.00"]}),
        clock=clock,
    )
    assert db.console_capture("player.getav health") == ["350.00"]
    assert len(opener.calls) == 2
    assert clock.slept == [0.5]


# --------------------------------------------------------------------------
# papyrus
# --------------------------------------------------------------------------


def test_papyrus_call_shape_and_returned_value():
    db, opener, _ = make((200, {"called": True, "returned": -2, "returnedType": "int"}))
    value = db.papyrus(
        "Actor",
        "GetRelationshipRank",
        self_form="0x0001A684",
        args=[DevBench.form("0x0001A685")],
    )
    assert value == -2
    assert opener.calls[0]["body"] == {
        "action": "call",
        "script": "Actor",
        "function": "GetRelationshipRank",
        "self": {"form": "0x0001A684"},
        "args": [{"form": "0x0001A685"}],
        "timeoutMs": 3000,
    }


def test_papyrus_omits_self_when_no_form_is_given():
    db, opener, _ = make((200, {"called": True, "returned": 0.0, "returnedType": "float"}))
    db.papyrus("Utility", "GetCurrentGameTime", timeout_ms=5000)
    body = opener.calls[0]["body"]
    assert "self" not in body
    assert body["args"] == []
    assert body["timeoutMs"] == 5000


def test_form_helper_is_a_static_method():
    assert DevBench.form("0x14") == {"form": "0x14"}
    db, _, _ = make((200, {}))
    assert db.form("WEBalgruuf") == {"form": "WEBalgruuf"}


def test_papyrus_returns_none_for_a_void_call():
    db, _, _ = make((200, {"called": True}))
    assert db.papyrus("Debug", "Notification", args=["hi"]) is None


# --------------------------------------------------------------------------
# scenario
# --------------------------------------------------------------------------

OK_TRANSCRIPT = {
    "ok": True,
    "aborted": False,
    "stepsRun": 2,
    "elapsedMs": 1200,
    "results": [
        {"index": 0, "kind": "tool", "tool": "console", "ok": True, "result": {}, "elapsedMs": 3},
        {"index": 1, "kind": "waitUntil", "cond": "playerLoaded", "satisfied": True, "elapsedMs": 900},
    ],
}

FAILING_TRANSCRIPT = {
    "ok": False,
    "aborted": True,
    "stepsRun": 4,
    "elapsedMs": 61000,
    "results": [
        {"index": 0, "kind": "tool", "tool": "console", "ok": True, "result": {}, "elapsedMs": 3},
        {"index": 1, "kind": "waitUntil", "cond": "playerLoaded", "satisfied": True, "elapsedMs": 8400},
        {
            "index": 2,
            "kind": "waitFor",
            "topic": "lifecycle",
            "match": {"event": "postLoadGame"},
            "satisfied": False,
            "timedOut": True,
            "elapsedMs": 60000,
        },
        {"index": 3, "kind": "tool", "tool": "game", "ok": False, "errorCode": 404, "error": "unknown save", "elapsedMs": 1},
    ],
}


def test_scenario_posts_action_run_with_the_whole_timeout():
    db, opener, _ = make((200, OK_TRANSCRIPT))
    steps = [{"tool": "console", "args": {"command": "coc WhiterunOrigin"}}, {"waitUntil": "playerLoaded"}]
    assert db.scenario(steps, timeout_s=120.0) == OK_TRANSCRIPT
    call = opener.calls[0]
    assert call["url"].endswith("/api/tool/scenario")
    assert call["body"] == {"action": "run", "steps": steps}
    assert call["timeout"] == 120.0


def test_scenario_raises_on_ok_false_despite_http_200():
    db, _, _ = make((200, FAILING_TRANSCRIPT))
    with pytest.raises(ScenarioFailed) as excinfo:
        db.scenario([{"wait": 10}])
    exc = excinfo.value
    assert exc.transcript == FAILING_TRANSCRIPT
    assert isinstance(exc, DevBenchError)


def test_scenario_failure_names_the_first_failing_step_not_a_satisfied_one():
    """A passing ``waitUntil`` step carries no ``ok`` key at all -- it must not be flagged."""
    db, _, _ = make((200, FAILING_TRANSCRIPT))
    with pytest.raises(ScenarioFailed) as excinfo:
        db.scenario([{"wait": 10}])
    message = str(excinfo.value)
    assert "step 2" in message
    assert "waitFor" in message
    assert "timedOut" in message
    assert "step 1" not in message
    assert "step 3" not in message


def test_scenario_failure_reports_a_failed_tool_step():
    transcript = {
        "ok": False,
        "aborted": True,
        "results": [{"index": 0, "kind": "tool", "tool": "game", "ok": False, "errorCode": 404, "error": "unknown save 'x'"}],
    }
    db, _, _ = make((200, transcript))
    with pytest.raises(ScenarioFailed) as excinfo:
        db.scenario([{"tool": "game", "args": {}}])
    message = str(excinfo.value)
    assert "step 0" in message
    assert "game" in message
    assert "unknown save 'x'" in message
    assert "404" in message


def test_scenario_ok_false_with_no_failing_step_still_raises():
    db, _, _ = make((200, {"ok": False, "aborted": True, "results": []}))
    with pytest.raises(ScenarioFailed):
        db.scenario([{"wait": 1}])


# --------------------------------------------------------------------------
# menu / game
# --------------------------------------------------------------------------


def test_menu_list_and_describe():
    db, opener, _ = make((200, {"openMenus": ["HUD Menu"], "messageBoxOpen": False, "registered": []}))
    assert db.menu_list()["openMenus"] == ["HUD Menu"]
    assert opener.calls[0]["body"] == {"action": "list"}

    db, opener, _ = make((200, {"messageBoxOpen": True, "bodyText": "...", "buttons": ["Yes", "No"], "cancelIndex": 1}))
    assert db.menu_describe()["buttons"] == ["Yes", "No"]
    assert opener.calls[0]["body"] == {"action": "describe"}


def test_menu_accept_by_index_and_by_body():
    db, opener, _ = make((200, {"queued": True, "action": "accept", "index": 0}))
    db.menu_accept(index=0)
    assert opener.calls[0]["body"] == {"action": "accept", "index": 0}

    db, opener, _ = make((200, {"accepted": True, "index": 1}))
    db.menu_accept(match_body="content")
    assert opener.calls[0]["body"] == {"action": "accept", "matchBody": "content"}


def test_menu_accept_requires_exactly_one_selector():
    db, _, _ = make((200, {}))
    with pytest.raises(ValueError):
        db.menu_accept()
    with pytest.raises(ValueError):
        db.menu_accept(index=0, match_body="content")


def test_game_save_load_and_list():
    db, opener, _ = make((200, {"queued": True, "action": "save", "name": "baseline"}))
    db.save("baseline")
    assert opener.calls[0]["body"] == {"action": "save", "name": "baseline"}

    db, opener, _ = make((200, {"queued": True, "action": "load", "name": "baseline"}))
    db.load("baseline")
    assert opener.calls[0]["body"] == {"action": "load", "name": "baseline"}

    db, opener, _ = make((200, {"count": 1, "returned": 1, "saves": [{"name": "Save 37", "mtimeUnix": 1755}]}))
    assert db.list_saves(limit=1)["saves"][0]["name"] == "Save 37"
    assert opener.calls[0]["body"] == {"action": "list", "limit": 1}


# --------------------------------------------------------------------------
# waiting helpers
# --------------------------------------------------------------------------


def test_wait_frames_reports_the_delta_from_two_health_reads():
    clock = FakeClock()
    db, opener, _ = make((200, dict(HEALTH, frame=1000)), (200, dict(HEALTH, frame=1100)), clock=clock)
    ok, delta = db.wait_frames(min_frames=30, within_s=2.0)
    assert (ok, delta) == (True, 100)
    assert clock.slept == [2.0]
    assert all(c["method"] == "GET" for c in opener.calls)


def test_wait_frames_fails_when_the_counter_is_frozen():
    db, _, _ = make((200, dict(HEALTH, frame=1000)), (200, dict(HEALTH, frame=1000)))
    assert db.wait_frames() == (False, 0)


def test_wait_frames_fails_on_an_unresolved_frame_counter():
    db, _, _ = make((200, dict(HEALTH, frame=-1)), (200, dict(HEALTH, frame=-1)))
    ok, _ = db.wait_frames()
    assert ok is False


def test_wait_until_returns_when_the_predicate_passes():
    clock = FakeClock()
    db, _, _ = make((200, {}), clock=clock)
    calls = {"n": 0}

    def predicate():
        calls["n"] += 1
        return calls["n"] >= 3

    db.wait_until(predicate, timeout_s=30.0, poll_s=0.5, what="playerLoaded")
    assert calls["n"] == 3
    assert clock.slept == [0.5, 0.5]


def test_wait_until_treats_a_devbench_error_as_not_yet():
    clock = FakeClock()
    db, _, _ = make((200, {}), clock=clock)
    calls = {"n": 0}

    def predicate():
        calls["n"] += 1
        if calls["n"] < 3:
            raise DevBenchError("504 during a loading screen", code=504)
        return True

    db.wait_until(predicate, timeout_s=30.0, poll_s=1.0, what="scene")
    assert calls["n"] == 3


def test_wait_until_raises_timeout_error_naming_what():
    clock = FakeClock()
    db, _, _ = make((200, {}), clock=clock)
    with pytest.raises(TimeoutError) as excinfo:
        db.wait_until(lambda: False, timeout_s=5.0, poll_s=1.0, what="playerLoaded")
    assert "playerLoaded" in str(excinfo.value)


# --------------------------------------------------------------------------
# FormID composition
# --------------------------------------------------------------------------


def test_compose_form_id_for_a_full_plugin():
    db, opener, _ = make((200, MODS))
    assert db.compose_form_id("ChroniclePatcher.esp", 0x000801) == "0x05000801"
    assert opener.calls[0]["body"] == {"kind": "mods"}


def test_compose_form_id_for_a_light_plugin():
    db, _, _ = make((200, MODS))
    assert db.compose_form_id("MyMod.esl", 0x800) == "0xFE00C800"


def test_compose_form_id_matches_the_plugin_name_case_insensitively():
    db, _, _ = make((200, MODS))
    assert db.compose_form_id("chroniclepatcher.ESP", 1) == "0x05000001"


def test_compose_form_id_masks_out_of_range_local_ids():
    db, _, _ = make((200, MODS))
    assert db.compose_form_id("ChroniclePatcher.esp", 0xAB123456) == "0x05123456"
    db, _, _ = make((200, MODS))
    assert db.compose_form_id("MyMod.esl", 0xABC123) == "0xFE00C123"


def test_compose_form_id_raises_for_an_unloaded_plugin():
    db, _, _ = make((200, MODS))
    with pytest.raises(DevBenchError) as excinfo:
        db.compose_form_id("NotInstalled.esp", 1)
    assert "NotInstalled.esp" in str(excinfo.value)


def test_base_url_trailing_slash_is_normalised():
    opener = FakeOpener([(200, HEALTH)])
    DevBench("http://127.0.0.1:8921/", opener=opener).health()
    assert opener.calls[0]["url"] == "http://127.0.0.1:8921/api/health"
