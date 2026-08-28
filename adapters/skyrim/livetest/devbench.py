"""Thin DevBench (v1.15.1) REST client for the live-game test harness.

Stdlib only (``urllib``), matching this project's empty ``dependencies``. The
error taxonomy is the same four distinct messages
``tools/chronicle-devbench-runbook.py`` raises (HTTP error / unreachable /
connection accepted-then-closed / timeout), plus a machine-readable ``kind``
so retry logic can tell "the game is still coming up" from "it timed out".

Two DevBench facts shape most of this module. **HTTP 200 does not mean a
scenario passed** -- ``ScenarioHandler`` returns a transcript instead of
throwing, so ``scenario()`` checks ``body["ok"]`` and each ``results[]`` entry
itself. And **504 is routine, not fatal** -- every main-thread-marshalled tool
504s during a loading screen or while a modal is open, so ``call_retry``
retries it.

The HTTP transport is injected (``opener``) so the whole surface is unit
testable with canned responses and no game running; ``sleep``/``monotonic``
are injected for the same reason.
"""

from __future__ import annotations

import http.client
import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from typing import Any

DEFAULT_BASE_URL = "http://127.0.0.1:8920"

#: ``(method, url, body_bytes | None, timeout) -> (status, body_bytes)``.
Opener = Callable[[str, str, bytes | None, float], tuple[int, bytes]]

_RETRYABLE_STATUS = 504
_LIGHT_PLUGIN_BASE = 0xFE000000


class DevBenchError(Exception):
    """A DevBench call failed in a way the caller should see a clear message for."""

    def __init__(self, message: str, *, code: int | None = None, kind: str = "http") -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        #: One of ``http``, ``unreachable``, ``closed``, ``timeout``, ``client``, ``scenario``.
        self.kind = kind


class ScenarioFailed(DevBenchError):
    """A ``scenario run`` came back HTTP 200 with ``ok:false``; ``transcript`` is the body."""

    def __init__(self, message: str, *, transcript: dict) -> None:
        super().__init__(message, code=None, kind="scenario")
        self.transcript = transcript


def _urllib_opener(method: str, url: str, body: bytes | None, timeout: float) -> tuple[int, bytes]:
    """Default transport: HTTP errors come back as a status, everything else raises."""
    request = urllib.request.Request(url, data=body, method=method)
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return int(response.status), response.read()
    except urllib.error.HTTPError as exc:
        return int(exc.code), exc.read()


def _step_failed(step: dict) -> bool:
    """A scenario step failed. Note a satisfied ``waitUntil`` carries no ``ok`` key at all."""
    if "ok" in step and not step["ok"]:
        return True
    if "satisfied" in step and not step["satisfied"]:
        return True
    return bool(step.get("timedOut"))


def _describe_step(step: dict) -> str:
    parts = [f"step {step.get('index')}", f"kind={step.get('kind')}"]
    if step.get("tool"):
        parts.append(f"tool={step['tool']}")
    if step.get("cond"):
        parts.append(f"cond={step['cond']}")
    if step.get("timedOut"):
        parts.append("timedOut")
    if step.get("errorCode"):
        parts.append(f"errorCode={step['errorCode']}")
    if step.get("error"):
        parts.append(f"error={step['error']}")
    return ", ".join(parts)


def _first_ref(body: Any) -> dict | None:
    body = body or {}
    refs = body.get("refs") or []
    return refs[0] if body.get("count") and refs else None


def _scenario_message(body: dict) -> str:
    results = body.get("results") if isinstance(body, dict) else None
    for step in results or []:
        if isinstance(step, dict) and _step_failed(step):
            return f"DevBench scenario failed at {_describe_step(step)}"
    return f"DevBench scenario reported ok=false with no failing step (aborted={body.get('aborted')})"


class DevBench:
    """The harness's only channel to the running game."""

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
        *,
        opener: Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._opener: Opener = opener or _urllib_opener
        self._sleep = sleep
        self._now = monotonic

    # -- transport ---------------------------------------------------------

    def _request(self, method: str, path: str, body: Any = None, *, timeout: float | None = None) -> Any:
        url = f"{self.base_url}{path}"
        payload = json.dumps(body).encode("utf-8") if body is not None else None
        budget = self.timeout if timeout is None else timeout
        try:
            status, raw = self._opener(method, url, payload, budget)
        except urllib.error.URLError as exc:
            raise DevBenchError(
                f"could not reach DevBench at {self.base_url} ({exc.reason}) -- "
                "is Skyrim running with the devbench SKSE plugin loaded? "
                "(DevBench is in-process; it does not exist until Skyrim does.)",
                kind="unreachable",
            ) from exc
        except (ConnectionError, http.client.HTTPException) as exc:
            raise DevBenchError(
                f"a connection to {self.base_url} was accepted but closed without an HTTP "
                f"response ({exc!r}) for {method} {path} -- something is listening on that "
                "port but isn't DevBench (a stale SSH port-forward with nothing on the far "
                "end is a common cause), or DevBench crashed mid-response.",
                kind="closed",
            ) from exc
        except TimeoutError as exc:
            raise DevBenchError(
                f"DevBench at {self.base_url} did not respond within {budget}s for {method} {path} -- "
                "the main thread may be busy (a long load, a stuck menu); GET /api/health "
                "answers even then, so try health() to distinguish busy from hung.",
                kind="timeout",
            ) from exc

        ok = 200 <= status < 300
        decoded = self._decode(raw, method, path, strict=ok)
        if ok:
            return decoded
        message = decoded.get("error") if isinstance(decoded, dict) else None
        if not message:
            message = raw.decode("utf-8", errors="replace").strip() or "(empty response body)"
        raise DevBenchError(f"DevBench returned HTTP {status} for {method} {path}: {message}", code=status, kind="http")

    @staticmethod
    def _decode(raw: bytes, method: str, path: str, *, strict: bool) -> Any:
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            if strict:
                raise DevBenchError(f"DevBench's response to {method} {path} was not valid JSON: {raw!r}") from exc
            return None

    def _post_tool(self, name: str, args: dict) -> Any:
        return self._request("POST", f"/api/tool/{name}", args)

    # -- core surface ------------------------------------------------------

    def health(self) -> dict:
        """``GET /api/health`` -- answered off the main thread, so it works while wedged."""
        return self._request("GET", "/api/health")

    def tools(self) -> list[dict]:
        """``GET /api/tools`` -- a bare JSON array, not an object."""
        return self._request("GET", "/api/tools")

    def call(self, name: str, **args: Any) -> Any:
        """``POST /api/tool/<name>``; always sends a JSON body (``{}`` minimum)."""
        return self._post_tool(name, args)

    def call_retry(self, name: str, *, deadline_s: float = 30.0, **args: Any) -> Any:
        """``call`` retrying only 504s and an unreachable server, 0.5s doubling to 4s."""
        deadline = self._now() + deadline_s
        delay = 0.5
        while True:
            try:
                return self._post_tool(name, args)
            except DevBenchError as exc:
                retryable = exc.code == _RETRYABLE_STATUS or exc.kind == "unreachable"
                if not retryable or self._now() >= deadline:
                    raise
                self._sleep(delay)
                delay = min(delay * 2, 4.0)

    # -- inspect -----------------------------------------------------------

    def _inspect(self, kind: str, **args: Any) -> Any:
        return self._post_tool("inspect", {"kind": kind, **args})

    def state(self) -> dict:
        """``inspect kind=state`` -- carries ``playerLoaded`` and instance identity."""
        return self._inspect("state")

    def scene(self) -> dict:
        """``inspect kind=scene`` -- cell/worldspace/position, or just ``playerLoaded:false``."""
        return self._inspect("scene")

    def player(self) -> dict:
        """``inspect kind=player``."""
        return self._inspect("player")

    def mods(self) -> dict:
        """``inspect kind=mods`` -- load order; 503 before data is loaded."""
        return self._inspect("mods")

    def refs(self, form_type: str | None = None, radius: float | None = None, limit: int = 100) -> list[dict]:
        """``inspect kind=refs`` enumerate over the loaded grid; unset filters are omitted."""
        args: dict[str, Any] = {"limit": limit}
        if form_type is not None:
            args["formType"] = form_type
        if radius is not None:
            args["radius"] = radius
        body = self._inspect("refs", **args)
        return list((body or {}).get("refs") or [])

    def ref(self, form: str) -> dict | None:
        """One ref by full hex FormID or EditorID. ``None`` when unresolved (``count:0``, not a 404)."""
        return _first_ref(self._inspect("refs", formId=form))

    def selected_ref(self) -> dict | None:
        """The console/crosshair ref (whatever ``prid`` last selected)."""
        return _first_ref(self._inspect("refs", selected=True))

    # -- console -----------------------------------------------------------

    def console(self, command: str) -> dict:
        """Fire-and-forget ``console exec``; returns ``{"queued":true,...}`` immediately."""
        return self._post_tool("console", {"action": "exec", "command": command})

    def console_capture(self, command: str, *, settle_s: float = 0.5) -> list[str]:
        """Run ``command`` with output capture and return the fenced lines. Diagnostics only.

        **Stale-window caveat.** ``exec`` returns before the console has drained,
        and ``read`` slices the *last* begin marker in the accumulated
        scrollback (DevBench ``ConsoleLogCapture.cpp:19``). Reading too early
        therefore returns the *previous* capture window with
        ``markersFound:true`` -- silently stale data, indistinguishable from
        fresh. No wrapping makes an arbitrary console command self-identifying,
        so this only mitigates: wait ``settle_s``, read, and re-read once after
        another ``settle_s`` if the markers haven't landed. Never assert on the
        result -- use ``papyrus()``, which has no marker race.
        """
        self._post_tool("console", {"action": "exec", "command": command, "capture": True})
        self._sleep(settle_s)
        body = self._post_tool("console", {"action": "read"}) or {}
        if not body.get("markersFound"):
            self._sleep(settle_s)
            body = self._post_tool("console", {"action": "read"}) or {}
        return list(body.get("lines") or [])

    # -- papyrus -----------------------------------------------------------

    @staticmethod
    def form(x: str) -> dict:
        """Wrap a FormID/EditorID for a Papyrus form argument or ``self``."""
        return {"form": x}

    def papyrus(
        self,
        script: str,
        function: str,
        *,
        self_form: str | None = None,
        args: Sequence[Any] = (),
        timeout_ms: int = 3000,
    ) -> Any:
        """The assertion primitive: a typed, synchronous Papyrus call. Returns ``body["returned"]``.

        Pass forms as ``DevBench.form("0x14")``. Omitted trailing optionals are
        padded with type-neutral defaults by DevBench, not Papyrus defaults, so
        always pass every argument you care about.
        """
        payload: dict[str, Any] = {
            "action": "call",
            "script": script,
            "function": function,
            "args": list(args),
            "timeoutMs": timeout_ms,
        }
        if self_form is not None:
            payload["self"] = {"form": self_form}
        body = self._post_tool("papyrus", payload) or {}
        return body.get("returned")

    # -- scenario ----------------------------------------------------------

    def scenario(self, steps: list[dict], *, timeout_s: float = 300.0) -> dict:
        """Run a synchronous scenario; raise ``ScenarioFailed`` unless ``body["ok"]``.

        The run blocks the HTTP request for its whole duration, so ``timeout_s``
        is used as the per-request timeout as well.
        """
        body = self._request("POST", "/api/tool/scenario", {"action": "run", "steps": list(steps)}, timeout=timeout_s)
        if not isinstance(body, dict):
            raise ScenarioFailed(f"DevBench scenario returned an unexpected body: {body!r}", transcript={})
        if not body.get("ok"):
            raise ScenarioFailed(_scenario_message(body), transcript=body)
        return body

    # -- menu --------------------------------------------------------------

    def menu_list(self) -> dict:
        """``menu list`` -- no main-thread marshalling, so it works when everything else 504s."""
        return self._post_tool("menu", {"action": "list"})

    def menu_describe(self) -> dict:
        """``menu describe`` -- body text and buttons of the open MessageBoxMenu."""
        return self._post_tool("menu", {"action": "describe"})

    def menu_accept(self, *, index: int | None = None, match_body: str | None = None) -> dict:
        """Accept a modal by button index or by matching its body text (preferred)."""
        if (index is None) == (match_body is None):
            raise ValueError("menu_accept() takes exactly one of index= or match_body=")
        args: dict[str, Any] = {"action": "accept"}
        if index is not None:
            args["index"] = index
        else:
            args["matchBody"] = match_body
        return self._post_tool("menu", args)

    # -- game --------------------------------------------------------------

    def save(self, name: str) -> dict:
        """``game save`` (never raw console save -- that deadlocks the engine). Fire-and-forget."""
        return self._post_tool("game", {"action": "save", "name": name})

    def load(self, name: str) -> dict:
        """``game load`` by save *stem*, no ``.ess``. Fire-and-forget; watch the lifecycle."""
        return self._post_tool("game", {"action": "load", "name": name})

    def list_saves(self, **kw: Any) -> dict:
        """``game list`` -- pure file I/O, works at the main menu. ``saves[]`` are objects."""
        return self._post_tool("game", {"action": "list", **kw})

    # -- waiting -----------------------------------------------------------

    def wait_frames(self, *, min_frames: int = 30, within_s: float = 2.0) -> tuple[bool, int]:
        """Is the game actually simulating? Two ``/api/health`` reads ``within_s`` apart.

        An unresolved frame counter (``-1``, e.g. no Address Library) is a
        failure, not a delta.
        """
        before = (self.health() or {}).get("frame", -1)
        self._sleep(within_s)
        after = (self.health() or {}).get("frame", -1)
        if not isinstance(before, int) or not isinstance(after, int) or before < 0 or after < 0:
            return False, 0
        delta = after - before
        return delta >= min_frames, delta

    def wait_until(
        self,
        predicate: Callable[[], bool],
        *,
        timeout_s: float,
        poll_s: float = 1.0,
        what: str = "",
    ) -> None:
        """Poll ``predicate`` until true. A ``DevBenchError`` from it means "not yet"."""
        deadline = self._now() + timeout_s
        while True:
            try:
                if predicate():
                    return
            except DevBenchError:
                pass
            if self._now() >= deadline:
                raise TimeoutError(f"timed out after {timeout_s}s waiting for {what or 'a condition'}")
            self._sleep(poll_s)

    # -- FormID composition ------------------------------------------------

    def compose_form_id(self, plugin_name: str, local_id: int) -> str:
        """Compose a runtime FormID from a plugin-local one; DevBench does no such lookup itself.

        Full plugin: ``(index << 24) | (local & 0xFFFFFF)``. Light (ESL/FE):
        ``0xFE000000 | (index << 12) | (local & 0xFFF)``. Self-check the result
        once per session against an EditorID lookup -- a wrong composition
        silently resolves the wrong form.
        """
        body = self.mods() or {}
        needle = plugin_name.strip().lower()
        for entry in body.get("plugins") or []:
            if str(entry.get("name", "")).strip().lower() == needle:
                return "0x%08X" % ((int(entry["index"]) << 24) | (local_id & 0x00FFFFFF))
        for entry in body.get("lightPlugins") or []:
            if str(entry.get("name", "")).strip().lower() == needle:
                return "0x%08X" % (_LIGHT_PLUGIN_BASE | (int(entry["index"]) << 12) | (local_id & 0x00000FFF))
        raise DevBenchError(
            f"plugin {plugin_name!r} is not in the load order "
            f"({body.get('count')} full + {body.get('lightCount')} light plugins loaded) -- "
            "cannot compose a runtime FormID for it",
            kind="client",
        )
