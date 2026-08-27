#!/usr/bin/env python3
"""Drive parts of ``docs/design/chronicle-bridge-verification-runbook.md`` through
DevBench's REST API instead of the owner typing console commands by hand.

**UNVERIFIED against a live game.** This script was written and reviewed
against real source (DevBench's own README, ``chronicle/cli.py``, and this
repo's listener) but has never been run against an actual DevBench+Skyrim
session -- no Skyrim process was running when this was written, and
launching one is explicitly out of scope for whatever wrote this. Everything
below is "should work per the documented contract," not "has been observed
to work." Treat every printed result as something to read and judge, not
something this script has already judged for you.

## What this does and does not automate

Per the runbook's corrections table, the four write paths split into two
kinds:

- **Avoidance** needs only console commands (``prid``, ``set ... to ...``,
  ``getglobalvalue``, ``EvaluatePackage``) -- this script drives all of
  those through DevBench's ``console`` tool and prints the raw captured
  output for you to read. Fully automatable today.
- **Hydration, vendor markup, and diegetic evidence** all need a
  precondition seeded into the live run's frame log: a real ``Grudge``
  (hydration and vendor markup) or a well-evidenced ``BeliefInstance``
  (evidence). Earlier revisions of this script (and of the runbook)
  believed this was flatly impossible via ``chronicle inject`` because
  ``grudge_formed``/``belief_formed`` are TRACE-stream *derived* records
  (docs/frame-log-schema.md §4, tier 0/3), not one of the three
  events-stream kinds ``--event`` accepts (``npc_died``,
  ``crime_witnessed``, ``rumor_heard``), and there is genuinely no
  listener-side seed hook (``/whiterun/hydration``, ``/whiterun/vendor-
  markup``, and ``/whiterun/evidence`` all compute their poll responses
  from ``FrameLogReader.state_at()`` -- straight from the frame log).
  **That diagnosis was correct but incomplete: it's not that no recipe
  exists, it's that no ONE-STEP `chronicle inject --event` recipe
  exists.** A real, verified two-step recipe does (2026-08-27 session,
  proven end-to-end against a fresh scratch run, not theorized):

  1. **Inject a real ``crime_witnessed`` event** via the CLI's already-
     working ``--event`` write path, with the witness AS the victim
     (``victim_id == witness_id``) -- this is genuinely accepted today,
     confirmed by running it. Example:

         $ uv run python -m chronicle inject <run> --event \\
             '{"event_type": "crime_witnessed", "tick": 10, \\
               "witness_id": "adrianne_avenicci", "perpetrator_id": "nazeem", \\
               "crime_type": "assault", "victim_id": "adrianne_avenicci", \\
               "location_id": "whiterun_marketplace"}'
         injected crime_witnessed seq=0 tick=10 into run <run> (origin console: chronicle inject)

  2. **Derive the belief + grudge from that event** by reattaching a real
     ``chronicle.driver.Driver`` to the same run (replaying its current
     claims/social/roles state via ``FrameLogReader.state_at()``, then
     temporarily swapping in the reattached ``FrameLogWriter`` so
     ``Driver.__init__`` doesn't try to create a second run directory) and
     calling ``Driver.crime_witnessed()`` with the SAME ``witness_id``/
     ``perpetrator_id``/``victim_id``/canonical-event-key as step 1. This
     is exactly ``chronicle/driver.py``'s own documented cascade -- rule
     12 (``suffer_harm``) fires because ``victim_id == witness_id``,
     producing a real ``Grudge(holder_id=witness_id, target_id=perpetrator_id,
     severity=1.0)`` -- verified well above every consumer's threshold
     (``AVOIDANCE_GRUDGE_THRESHOLD=0.5``, ``MARKUP_SEVERITY_FLOOR=0.2``) --
     alongside a ``BeliefInstance`` at ``WITNESS_CONFIDENCE=0.95``, well
     above diegetic evidence's ``EVIDENCE_CONFIDENCE_THRESHOLD=0.6``. This
     step is NOT a `chronicle inject` CLI call -- there is no CLI
     subcommand for it today -- it is a real, if small, Python driver of
     ``chronicle``'s own public simulation API (`_seed_via_crime_witnessed`
     below), the same technique ``chronicle/cli.py``'s own
     ``_open_appending_writer`` already establishes for reattaching to an
     existing run, and the same derivation every test/scenario script in
     ``chronicle/tests/`` and ``scenarios/`` already calls -- nothing here
     hand-fabricates a trace record with no source event; the source
     event from step 1 is real and step 2 derives from it exactly as a
     live tick loop would.

     **A real caveat this session found the hard way**: a freshly resumed
     ``Driver``'s auto-id counter (``self._auto_ids``) starts at 1
     regardless of the run's history. Seeding twice against the same run
     without correcting for this mints a colliding grudge id, which
     silently clobbers an unrelated pair's entry in
     ``SocialStateStore``'s id-keyed dict (`add_grudge` only rejects a
     colliding id for the SAME (holder, target) pair; a different pair
     reusing an old id overwrites the old grudge in place, invisibly,
     until you go looking for it). `_resume_driver` below rebases the
     counter off every existing ``grudge-{harm,violation}-auto-<n>`` id
     already in the run before seeding anything new -- do not skip this
     if you ever reimplement the pattern elsewhere.

  Diegetic evidence needs only step 1's belief, so its recipe uses a
  bystander witness (``victim_id=None`` or a third party) to skip the
  grudge cascade entirely -- see `cmd_evidence` below.

  The ``hydration``, ``vendor-markup``, and ``evidence`` subcommands below
  now perform both steps for real (when ``--run`` is given), print the
  actual CLI response from step 1 and the actual derived Grudge/
  BeliefInstance from step 2, and only fall back to an explanation if
  ``--run`` is omitted.

## DevBench's real API shape (verified against the source, not paraphrased)

Source: ``https://github.com/alandtse/devbench`` README, fetched directly
via ``gh api repos/alandtse/devbench/readme`` (2026-08-27), cross-checked
against ``docs/research/25-devbench-skse-mcp-verification.md``'s earlier,
independently-sourced pass. Quotes below are verbatim from that README.

- Base URL: ``http://127.0.0.1:8920`` for Skyrim SE/AE (``8921`` for VR),
  loopback-only by hardcoded design ("Bind address is fixed to
  ``127.0.0.1``"; there is no config knob to widen it).
- ``GET /api/health`` -- "the one endpoint answered off the main thread (no
  ``RunAndWait``) -- a fast, always-returning liveness + identity probe":
  ``{ ok, lastLifecycle, frame, lastTaskFrame, pendingTasks, pid, port, exe,
  vr }``. This is the right reachability probe precisely because it answers
  even when the main thread is busy -- a tool call would ``504`` in that
  case, which looks identical to "not running" unless you check health
  first.
- ``GET /api/tools`` -- the full tool registry as JSON Schema (also the MCP
  ``inputSchema`` for each tool). Not fetched here (no live instance to ask)
  -- the ``probe`` subcommand below calls it once against a real instance
  so its exact shape can be confirmed empirically instead of guessed.
- ``POST /api/tool/<name>`` -- call a tool. Body is the tool's ``args``
  object directly (confirmed from the README's own worked example:
  ``POST /api/tool/scenario`` with body ``{"steps": [...]}"``, no envelope
  wrapper). Response is whatever that tool returns, JSON.
- ``console`` tool: ``{"action": "exec", "command": "...", "capture":
  true}`` queues the command on the main thread, fencing it between marker
  commands when ``capture=true``; a separate ``{"action": "read"}`` call
  "slices ConsoleLog's buffer between the markers and returns
  ``{markersFound, lines: [...]}``". The README does not spell out whether
  ``read`` needs a marker handle echoed back from the ``exec`` response or
  reads implicitly-latest markers -- this script tries the exec response's
  fields first (if any) and falls back to a bare ``{"action": "read"}``,
  and prints whatever comes back verbatim rather than asserting a shape.
- ``inspect`` tool: ``{"kind": "refs", "selected": true}`` after a
  console ``prid <formid>`` resolves the currently-selected reference to
  ``{formId, formType, name, editorId, base, position}``.
- No endpoint here is used to launch Skyrim or install mods -- DevBench is
  in-process and does not exist until Skyrim is already running with it
  loaded (confirmed in the research doc's §5); that setup remains the
  owner's own manual step per the runbook's §0.

## Usage

    uv run python tools/chronicle-devbench-runbook.py health
    uv run python tools/chronicle-devbench-runbook.py probe
    uv run python tools/chronicle-devbench-runbook.py hydration --npc-a 14a684 --npc-b 14a685
    uv run python tools/chronicle-devbench-runbook.py avoidance --pair nazeem_ysolda \\
        --npc-a 14a6a4 --npc-b 14a69a
    uv run python tools/chronicle-devbench-runbook.py vendor-markup --run <run_id> \\
        --vendor-formid 14a67c
    uv run python tools/chronicle-devbench-runbook.py evidence --run <run_id> --holder nazeem

Every subcommand is independently runnable (per this task's own instruction
not to build one monolithic unattended script) -- the owner still has to
look at the screen (NPCs moving apart, a barter price, a spawned item);
this tool's job is eliminating the typing, not the observation.
"""

from __future__ import annotations

import argparse
import http.client
import itertools
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from unittest.mock import patch

# `chronicle` lives at the repo root, one directory up from this file
# (tools/chronicle-devbench-runbook.py) -- sys.path[0] is this script's own
# directory when run directly (`python tools/chronicle-devbench-runbook.py`),
# which does NOT include the repo root, so `import chronicle...` would fail
# without this. Inserted before the chronicle imports below.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import chronicle.driver as _chronicle_driver_module
from chronicle.claims import EventKey
from chronicle.cli import (
    _branch_identity,
    _max_tick,
    _open_appending_writer,
    _reader_for,
)
from chronicle.driver import Driver
from chronicle.framelog import FrameLogReader

DEFAULT_DEVBENCH_URL = "http://127.0.0.1:8920"
DEFAULT_LISTENER_URL = "http://127.0.0.1:8765"

# Skyrim.esm's usual runtime prefix once loaded (it is conventionally the
# base master, load-order index 00) -- only a default; a real load order
# can differ, so every ref-taking flag below accepts an override.
_DEFAULT_REFIDS = {
    "nazeem": "0001a6a4",
    "ysolda": "0001a69a",
    "adrianne_avenicci": "0001a67c",
    "fralia_gray_mane": "0001a684",
    "olfina_gray_mane": "0001a685",
}

_AVOIDANCE_PAIRS = {
    "nazeem_ysolda": ("nazeem", "ysolda"),
    "carlotta_valentia_saffir": ("carlotta_valentia", "saffir"),
    "amren_brenuin": ("amren", "brenuin"),
    "fralia_gray_mane_idolaf_battle_born": ("fralia_gray_mane", "idolaf_battle_born"),
}


class DevBenchError(RuntimeError):
    """A DevBench call failed in a way the caller should see a clear message for."""


class DevBenchClient:
    """Thin wrapper over DevBench's REST surface (stdlib only -- no ``requests`` dependency

    in this project, per ``pyproject.toml``'s empty ``dependencies``)."""

    def __init__(self, base_url: str, *, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DevBenchError(f"DevBench returned HTTP {exc.code} for {method} {path}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise DevBenchError(
                f"could not reach DevBench at {self.base_url} ({exc.reason}) -- "
                "is Skyrim running with the devbench SKSE plugin loaded? "
                "(DevBench is in-process; it does not exist until Skyrim does.)"
            ) from exc
        except (ConnectionError, http.client.HTTPException) as exc:
            # E.g. RemoteDisconnected: a TCP port answered (something IS listening --
            # commonly a stale SSH -L port-forward left over from a prior session,
            # per docs/research/25-devbench-skse-mcp-verification.md's LAN-reachability
            # notes) but closed the connection instead of speaking HTTP -- a distinct
            # failure mode from "nothing is listening at all" (that one raises
            # urllib.error.URLError, handled above).
            raise DevBenchError(
                f"a connection to {self.base_url} was accepted but closed without an HTTP "
                f"response ({exc!r}) for {method} {path} -- something is listening on that "
                "port but isn't DevBench (a stale SSH port-forward with nothing on the far "
                "end is a common cause), or DevBench crashed mid-response."
            ) from exc
        except TimeoutError as exc:
            raise DevBenchError(
                f"DevBench at {self.base_url} did not respond within {self.timeout}s for {method} {path} -- "
                "the main thread may be busy (a long load, a stuck menu); GET /api/health "
                "answers even then, so try `probe`/`health` to distinguish busy from hung."
            ) from exc
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise DevBenchError(f"DevBench's response to {method} {path} was not valid JSON: {raw!r}") from exc

    def health(self) -> Any:
        return self._request("GET", "/api/health")

    def tools(self) -> Any:
        return self._request("GET", "/api/tools")

    def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        return self._request("POST", f"/api/tool/{name}", args)

    def console_exec_capture(self, command: str) -> dict[str, Any]:
        """Run one console command with output capture, per the README's exec/read pair.

        The README documents ``action='exec'`` (queues the command, fences it
        between markers when ``capture=true``) and a separate ``action='read'``
        that "slices ConsoleLog's buffer between the markers." It does not say
        whether ``read`` needs a marker handle from the ``exec`` response --
        this method passes through any such field if the exec response has
        one, otherwise issues a bare read. Both raw responses are returned
        so the caller can print them verbatim rather than this script
        guessing at a schema it hasn't seen live.
        """
        exec_result = self.call_tool("console", {"action": "exec", "command": command, "capture": True})
        read_args: dict[str, Any] = {"action": "read"}
        if isinstance(exec_result, dict):
            for key in ("marker", "markerId", "handle", "id"):
                if key in exec_result:
                    read_args[key] = exec_result[key]
        read_result = self.call_tool("console", read_args)
        return {"command": command, "exec": exec_result, "read": read_result}


def _print_console_result(result: dict[str, Any]) -> None:
    print(f"  > {result['command']}")
    read = result.get("read")
    lines = read.get("lines") if isinstance(read, dict) else None
    if isinstance(lines, list):
        for line in lines:
            print(f"    {line}")
    else:
        print(f"    (raw exec response) {result.get('exec')!r}")
        print(f"    (raw read response) {result.get('read')!r}")


def _resolve_refid(name_or_id: str) -> str:
    return _DEFAULT_REFIDS.get(name_or_id, name_or_id)


# ---------------------------------------------------------------------------
# chronicle inject shell-out (write path only; see module docstring for why
# grudge_formed/belief_formed cannot go through this today)
# ---------------------------------------------------------------------------


def run_chronicle_inject(run_id: str, event_json: str, *, runs_dir: str | None = None) -> tuple[int, str, str]:
    """Shell out to ``python -m chronicle inject <run_id> --event '<json>'`` (step 1 of the seeding recipe).

    Matches this project's own convention of shelling out to the tested CLI
    for the events-stream write itself, rather than reimplementing it here.
    """
    cmd = [sys.executable, "-m", "chronicle"]
    if runs_dir is not None:
        cmd += ["--runs-dir", runs_dir]
    cmd += ["inject", run_id, "--event", event_json]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# The verified two-step seeding recipe (2026-08-27): a real crime_witnessed
# event (step 1, via the CLI above) plus a real Driver-mediated derivation
# (step 2, below) -- see the module docstring's "What this does and does
# not automate" section for the full explanation of why this is real and
# not a fabricated shortcut.
# ---------------------------------------------------------------------------


def _resume_driver(run_id: str, runs_dir: Path) -> Driver:
    """Reattach a real ``Driver`` to an existing run, replaying its current state first.

    Mirrors ``chronicle/cli.py``'s own ``_open_appending_writer``/
    ``_branch_identity`` reattachment pattern (imported directly from
    there, not reimplemented) -- the one thing ``Driver.__init__`` can't do
    on its own is attach to an ALREADY-EXISTING run directory
    (``FrameLogWriter.__init__`` is create-only, append-only logs). This
    works around that by hydrating ``Driver``'s pre-populated-store
    constructor arguments from ``FrameLogReader.state_at()`` (the same
    "start-from-keyframe" shape the fork milestone already documents) and
    monkeypatching ``chronicle.driver``'s ``FrameLogWriter`` reference for
    just the one call that constructs it, swapping in the already-reattached
    writer instead of letting ``Driver.__init__`` try to create a new run.

    Also rebases ``driver._auto_ids`` off the highest existing
    ``grudge-{harm,violation}-auto-<n>`` id already in the run -- see the
    module docstring's caveat: skipping this risks a colliding auto-id on a
    second seeding call against the same run, which silently clobbers an
    unrelated grudge in ``SocialStateStore``'s id-keyed dict.
    """
    run_dir = runs_dir / run_id
    reader = _reader_for(run_id, runs_dir=runs_dir)
    seed_id, save_uuid, generation = _branch_identity(reader, runs_dir, run_id)
    max_tick = _max_tick(reader)
    state = reader.state_at(max_tick) if max_tick is not None else None
    reattached_writer = _open_appending_writer(run_dir, seed_id=seed_id, save_uuid=save_uuid, generation=generation)

    def _fake_writer_factory(*, run_id: str, seed_id: str, save_uuid: str, generation: int, runs_dir: Path | None = None):
        return reattached_writer

    with patch.object(_chronicle_driver_module, "FrameLogWriter", _fake_writer_factory):
        driver = _chronicle_driver_module.Driver(
            run_id=run_id,
            seed_id=seed_id,
            save_uuid=save_uuid,
            generation=generation,
            runs_dir=runs_dir,
            event_log=state.event_log if state is not None else None,
            claims=state.claims if state is not None else None,
            social=state.social if state is not None else None,
            roles=state.roles if state is not None else None,
        )
    existing_auto_ns = [
        int(m.group(1))
        for grudge in driver.social.grudges()
        if (m := re.match(r"^grudge-(?:harm|violation)-auto-(\d+)$", grudge.id))
    ]
    driver._auto_ids = itertools.count(max(existing_auto_ns, default=0) + 1)
    return driver


def _close_resumed_driver(driver: Driver) -> None:
    """Flush and release the reattached writer WITHOUT ``Driver.close()``.

    ``Driver.close()`` re-registers the run as "complete" and rewrites its
    registry entry -- wrong for a one-shot mid-session seed against a run a
    live listener is still tailing. Matches ``chronicle/cli.py``'s own
    ``_inject_write``'s cleanup exactly.
    """
    driver.writer.flush()
    for handle in driver.writer._files.values():
        handle.close()
    driver.writer._closed = True


def seed_crime_witnessed_grudge(
    *,
    run_id: str,
    runs_dir: str | None,
    witness_id: str,
    perpetrator_id: str,
    crime_type: str,
    self_victim: bool,
    location_id: str | None,
    gamets: float = 0.0,
) -> tuple[bool, str]:
    """The full, real, two-step seeding recipe. Returns (ok, message) for the caller to print.

    ``self_victim=True`` -> ``victim_id = witness_id``, so
    ``Driver.crime_witnessed()``'s rule-12 cascade fires and mints a real
    ``Grudge(holder_id=witness_id, target_id=perpetrator_id)``. This is the
    hydration/vendor-markup recipe (``target_id="the_player"`` for vendor
    markup, another named-cast NPC for hydration/avoidance).

    ``self_victim=False`` -> ``victim_id = None`` (bystander witness): forms
    a belief with no grudge at all -- the diegetic-evidence recipe, which
    only needs ``BeliefInstance.confidence`` (fixed at
    ``chronicle.claims.WITNESS_CONFIDENCE = 0.95`` for any fresh witness()
    call, regardless of victim_id).
    """
    runs_path = Path(runs_dir) if runs_dir is not None else Path("runs")
    victim_id = witness_id if self_victim else None
    event = {
        "event_type": "crime_witnessed",
        "gamets": gamets,
        "tick": int(gamets),
        "witness_id": witness_id,
        "perpetrator_id": perpetrator_id,
        "crime_type": crime_type,
        "victim_id": victim_id,
        "location_id": location_id,
    }

    print(f"\nStep 1/2: python -m chronicle inject {run_id} --event '{json.dumps(event)}'")
    returncode, stdout, stderr = run_chronicle_inject(run_id, json.dumps(event), runs_dir=runs_dir)
    if stdout:
        print(f"  stdout: {stdout.strip()}")
    if stderr:
        print(f"  stderr: {stderr.strip()}")
    if returncode != 0:
        return False, "step 1 (event injection) failed -- see stderr above; step 2 was not attempted."

    # The CLI prints "injected crime_witnessed seq=<n> tick=<t> into run ...";
    # pull the real seq back out rather than guessing it, since a run with
    # prior events won't start at seq 0.
    seq_match = re.search(r"seq=(\d+)", stdout)
    if seq_match is None:
        return False, f"step 1 succeeded but its seq could not be parsed from stdout: {stdout!r}"
    seq = int(seq_match.group(1))

    print("Step 2/2: reattaching a Driver and deriving the belief/grudge from that event...")
    try:
        driver = _resume_driver(run_id, runs_path)
        _seed_id, save_uuid, generation = _branch_identity(
            _reader_for(run_id, runs_dir=runs_path), runs_path, run_id
        )
        # Use step 1's own event seq (unique and monotonic per run) for the
        # id suffix, NOT driver._auto_ids -- that counter is rebased off
        # existing GRUDGE ids only (see _resume_driver's docstring), so a
        # bystander seed (self_victim=False, no grudge created) never
        # advances it. A second seed call after a bystander seed would then
        # reuse the same claim/belief/evidence id suffix as the bystander
        # call, colliding on claim_id and raising a real "second witness
        # disagrees on N slots" error from ClaimStore -- reproduced and
        # confirmed while verifying this script. seq has no such gap: the
        # CLI increments it on every injected event regardless of what the
        # derivation step does with it.
        _claim, belief, _evidence, grudge = driver.crime_witnessed(
            claim_id=f"claim-devbench-{seq}",
            belief_id=f"belief-devbench-{seq}",
            evidence_id=f"evidence-devbench-{seq}",
            witness_id=witness_id,
            perpetrator_id=perpetrator_id,
            crime_type=crime_type,
            victim_id=victim_id,
            canonical_event_key=EventKey(save_uuid, generation, seq),
            location_id=location_id,
            gamets=gamets,
        )
        _close_resumed_driver(driver)
    except Exception as exc:  # noqa: BLE001 -- surface any failure to the operator, don't swallow it
        return False, f"step 2 (derivation) raised {exc!r} -- the event from step 1 was written, but no belief/grudge was derived from it."

    lines = [
        "step 2 succeeded -- derived state (re-read independently from the frame log below):",
        f"  belief: id={belief.id} holder_id={belief.holder_id} confidence={belief.confidence}",
    ]
    if grudge is not None:
        lines.append(
            f"  grudge: id={grudge.id} holder_id={grudge.holder_id} target_id={grudge.target_id} "
            f"severity={grudge.severity}"
        )
    else:
        lines.append("  grudge: none (bystander witness -- victim_id was not witness_id, as intended for evidence-only seeding)")

    # Independent re-read, exactly what the listener's state_at() call does --
    # proves the write actually landed, not just that this process's own
    # in-memory driver thinks it did.
    reader = FrameLogReader(runs_path / run_id)
    state = reader.state_at(int(gamets))
    reread_belief = next((b for b in state.claims.beliefs_of(witness_id) if b.id == belief.id), None)
    reread_grudge = state.social.grudge(witness_id, perpetrator_id) if grudge is not None else None
    lines.append(
        f"  independent re-read (fresh FrameLogReader.state_at({int(gamets)})): "
        f"belief found={reread_belief is not None}, grudge found={reread_grudge is not None if grudge is not None else 'n/a'}"
    )
    return True, "\n".join(lines)


_INJECT_GAP_MESSAGE = (
    "\n(pass --run <run_id> to actually run the verified two-step seeding recipe: a real "
    "`chronicle inject --event` crime_witnessed write, then a Driver-mediated derivation of "
    "the belief/grudge from it -- see this script's module docstring for the full recipe and "
    "why it's real, not a fabricated shortcut.)"
)


# ---------------------------------------------------------------------------
# health / probe
# ---------------------------------------------------------------------------


def cmd_health(args: argparse.Namespace) -> int:
    client = DevBenchClient(args.devbench_url)
    try:
        health = client.health()
    except DevBenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(health, indent=2))
    return 0


def cmd_probe(args: argparse.Namespace) -> int:
    """Fetch the real tool schema from a live instance -- resolves this script's
    own documented uncertainty about console's exec/read handshake."""
    client = DevBenchClient(args.devbench_url)
    try:
        tools = client.tools()
    except DevBenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(tools, indent=2))
    return 0


# ---------------------------------------------------------------------------
# hydration
# ---------------------------------------------------------------------------


def cmd_hydration(args: argparse.Namespace) -> int:
    client = DevBenchClient(args.devbench_url)
    try:
        client.health()
    except DevBenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    npc_a = _resolve_refid(args.npc_a)
    npc_b = _resolve_refid(args.npc_b)

    print(f"Hydration check: reading relationship rank between {args.npc_a} ({npc_a}) "
          f"and {args.npc_b} ({args.npc_b} -> {npc_b}).")
    print("This is an NPC<->NPC write (HydrationPoller.cpp), not NPC<->player -- see the "
          "runbook's correction #5.")
    if args.run is not None:
        ok, message = seed_crime_witnessed_grudge(
            run_id=args.run,
            runs_dir=args.runs_dir,
            witness_id=args.npc_a,
            perpetrator_id=args.npc_b,
            crime_type="assault",
            self_victim=True,
            location_id="whiterun",
        )
        print(message)
        if not ok:
            print("(seeding failed -- see message above; proceeding to read the rank anyway)")
    else:
        print(_INJECT_GAP_MESSAGE)
    print("\nProceeding to read the current rank regardless (useful even unseeded, e.g. to "
          "confirm a baseline before some other seeding path runs):")
    try:
        r1 = client.console_exec_capture(f"prid {npc_a}")
        r2 = client.console_exec_capture(f"getrelationshiprank {npc_b}")
    except DevBenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    _print_console_result(r1)
    _print_console_result(r2)
    print(
        "\nRead the rank above. Wait ~8s for HydrationPoller's poll/ack, then re-run this "
        "same command and compare. If the log line 'no existing BGSRelationship for (...) "
        "-- skipping' appears in ChronicleBridge.log, this pair has no vanilla relationship "
        "record -- try a different pair (runbook §3). After a save/reload, re-run again: "
        "if the rank reverted, AddChange() did not persist the write -- report that as a "
        "real finding, not a script bug."
    )
    return 0


# ---------------------------------------------------------------------------
# avoidance
# ---------------------------------------------------------------------------


def cmd_avoidance(args: argparse.Namespace) -> int:
    if args.pair not in _AVOIDANCE_PAIRS:
        known = ", ".join(sorted(_AVOIDANCE_PAIRS))
        print(f"error: unknown --pair {args.pair!r} -- only these 4 have real FormIDs wired "
              f"into AvoidanceGlobals.cpp: {known}", file=sys.stderr)
        return 1
    npc_a_id, npc_b_id = _AVOIDANCE_PAIRS[args.pair]
    global_name = f"ChronicleAvoidingPair_{args.pair}"

    npc_a = _resolve_refid(args.npc_a) if args.npc_a else _DEFAULT_REFIDS.get(npc_a_id)
    npc_b = _resolve_refid(args.npc_b) if args.npc_b else _DEFAULT_REFIDS.get(npc_b_id)
    if npc_a is None or npc_b is None:
        print(f"error: no default refid known for {npc_a_id!r}/{npc_b_id!r} -- pass "
              "--npc-a/--npc-b explicitly", file=sys.stderr)
        return 1

    client = DevBenchClient(args.devbench_url)
    try:
        client.health()

        print(f"Reading current value of global {global_name!r} -- if this errors or reads "
              "as undefined, ChroniclePatcher.esp likely isn't installed/load-ordered "
              "(runbook's deployment-gap section), which looks identical to 'avoidance "
              "doesn't work' if you don't check this first.")
        r = client.console_exec_capture(f"getglobalvalue {global_name}")
        _print_console_result(r)

        print(f"\nSetting {global_name} to 1.")
        r = client.console_exec_capture(f"set {global_name} to 1")
        _print_console_result(r)

        print(f"\nSelecting {npc_a_id} ({npc_a}) and forcing an AI package re-evaluation.")
        r = client.console_exec_capture(f"prid {npc_a}")
        _print_console_result(r)
        r = client.console_exec_capture("EvaluatePackage")
        _print_console_result(r)

        print(f"\nSelecting {npc_b_id} ({npc_b}) and forcing an AI package re-evaluation.")
        r = client.console_exec_capture(f"prid {npc_b}")
        _print_console_result(r)
        r = client.console_exec_capture("EvaluatePackage")
        _print_console_result(r)
    except DevBenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        "\nNow watch the two NPCs in-game over 3-5 minutes (`GetDistance`/`GetCurrentPackage` "
        "via this script's console passthrough, or just watch them move) -- EvaluatePackage "
        "is 'nudge the AI to reconsider now,' not a guaranteed instant switch, especially "
        "mid-travel (runbook §6). If nothing changes, check whether either NPC is mid-quest-"
        "package first."
    )
    return 0


# ---------------------------------------------------------------------------
# vendor-markup / evidence: now seeded via the verified two-step recipe
# (seed_crime_witnessed_grudge, above) when --run is given.
# ---------------------------------------------------------------------------


def cmd_vendor_markup(args: argparse.Namespace) -> int:
    vendor_id = _resolve_refid(args.vendor_formid or "adrianne_avenicci")
    client = DevBenchClient(args.devbench_url)
    try:
        client.health()
        print(f"Resolving vendor ref {vendor_id} (default: Adrianne Avenicci, Warmaidens forge).")
        r = client.console_exec_capture(f"prid {vendor_id}")
        _print_console_result(r)
        r = client.call_tool("inspect", {"kind": "refs", "selected": True})
        print(f"  inspect kind=refs selected=true -> {json.dumps(r)}")
    except DevBenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.run is not None:
        ok, message = seed_crime_witnessed_grudge(
            run_id=args.run,
            runs_dir=args.runs_dir,
            witness_id="adrianne_avenicci",
            perpetrator_id="the_player",
            crime_type="theft",
            self_victim=True,
            location_id="warmaidens",
        )
        print(message)
        if not ok:
            print("error: seeding failed", file=sys.stderr)
            return 1
    else:
        print(_INJECT_GAP_MESSAGE)
    print(
        "\nGive the poller (8s interval, VendorMarkupCache.cpp) time to pick up the seeded "
        "grudge before opening the barter menu. Then: give the player gold, open the barter "
        "menu with this vendor, and compare the displayed price against actual gold "
        "deducted on purchase (VendorPriceHook.h's own 'UNVERIFIED CAVEAT'). Iron Dagger "
        "FormID 0001397E if you want a cheap known-price item. If the multiplier never "
        "appears, close and reopen the barter menu once before concluding it's broken "
        "(runbook §4's ordering caveat)."
    )
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    holder_id = args.holder or "nazeem"
    holder = _resolve_refid(args.holder) if args.holder else None
    client = DevBenchClient(args.devbench_url)
    try:
        client.health()
        if holder is not None:
            print(f"Resolving holder ref {holder}.")
            r = client.console_exec_capture(f"prid {holder}")
            _print_console_result(r)
            r = client.call_tool("inspect", {"kind": "refs", "selected": True})
            print(f"  inspect kind=refs selected=true -> {json.dumps(r)}")
    except DevBenchError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.run is not None:
        # self_victim=False: a bystander witness, no grudge cascade -- this
        # path only needs the BeliefInstance (fixed confidence 0.95,
        # regardless of victim_id), not a Grudge.
        ok, message = seed_crime_witnessed_grudge(
            run_id=args.run,
            runs_dir=args.runs_dir,
            witness_id=holder_id,
            perpetrator_id="unknown",
            crime_type="theft",
            self_victim=False,
            location_id="whiterun",
        )
        print(message)
        if not ok:
            print("error: seeding failed", file=sys.stderr)
            return 1
    else:
        print(_INJECT_GAP_MESSAGE)
    print(
        "\nWait ~8s for EvidencePoller's poll, then go find the holder NPC and look for a "
        "spawned Gold001 near their feet -- do not manually PlaceAtMe anything (runbook §5, "
        "correction #2). The persistence check that matters: hard-save, fast-travel far "
        "enough for the cell to unload, travel back, confirm the item is still there."
    )
    return 0


# ---------------------------------------------------------------------------
# listener reachability (used by the preflight, and standalone)
# ---------------------------------------------------------------------------


def cmd_check_listener(args: argparse.Namespace) -> int:
    req = urllib.request.Request(f"{args.listener_url.rstrip('/')}/whiterun/hydration")
    if args.shared_secret is not None:
        req.add_header("X-Chronicle-Bridge-Token", args.shared_secret)
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as exc:
        print(
            f"error: could not reach the Chronicle listener at {args.listener_url} ({exc.reason}) -- "
            "is it running? (adapters/skyrim/listener/listener.py --shared-secret <token> "
            "--live-run <run_id>)",
            file=sys.stderr,
        )
        return 1
    if status == 503:
        print(
            f"listener at {args.listener_url} is reachable but returned 503 -- it was likely "
            "started without --live-run (or --live-run points at the wrong run)."
        )
        return 1
    if status == 401:
        print(
            f"listener at {args.listener_url} is reachable but rejected the request (401) -- "
            "pass the correct --shared-secret.",
            file=sys.stderr,
        )
        return 1
    print(f"listener at {args.listener_url} is reachable: HTTP {status}\n{body}")
    return 0


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chronicle-devbench-runbook",
        description="Drive ChronicleBridge's in-game verification runbook through DevBench's REST API. "
        "UNVERIFIED against a live game -- see this file's module docstring.",
    )
    parser.add_argument("--devbench-url", default=DEFAULT_DEVBENCH_URL, help=f"default: {DEFAULT_DEVBENCH_URL}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_health = sub.add_parser("health", help="GET /api/health -- confirm DevBench is reachable")
    p_health.set_defaults(func=cmd_health)

    p_probe = sub.add_parser("probe", help="GET /api/tools -- dump the real tool schemas from a live instance")
    p_probe.set_defaults(func=cmd_probe)

    p_hydration = sub.add_parser("hydration", help="run/read the hydration NPC<->NPC relationship-rank check")
    p_hydration.add_argument("--npc-a", default="fralia_gray_mane", help="name (looked up) or raw refid")
    p_hydration.add_argument("--npc-b", default="olfina_gray_mane", help="name (looked up) or raw refid")
    p_hydration.add_argument("--run", default=None, help="a run id -- if given, actually attempts `chronicle inject`")
    p_hydration.add_argument("--runs-dir", default=None, help="passed through to `chronicle --runs-dir`")
    p_hydration.set_defaults(func=cmd_hydration)

    p_avoidance = sub.add_parser("avoidance", help="set the avoidance global and nudge both NPCs' packages")
    p_avoidance.add_argument(
        "--pair", default="nazeem_ysolda", choices=sorted(_AVOIDANCE_PAIRS), help="one of the 4 wired pairs"
    )
    p_avoidance.add_argument("--npc-a", default=None, help="override the first NPC's refid")
    p_avoidance.add_argument("--npc-b", default=None, help="override the second NPC's refid")
    p_avoidance.set_defaults(func=cmd_avoidance)

    p_vendor = sub.add_parser(
        "vendor-markup", help="resolve the vendor ref and report the chronicle-inject seeding gap"
    )
    p_vendor.add_argument("--vendor-formid", default=None, help="default: adrianne_avenicci's default refid")
    p_vendor.add_argument("--run", default=None, help="a run id -- if given, actually attempts `chronicle inject`")
    p_vendor.add_argument("--runs-dir", default=None, help="passed through to `chronicle --runs-dir`")
    p_vendor.set_defaults(func=cmd_vendor_markup)

    p_evidence = sub.add_parser(
        "evidence", help="resolve the holder ref (optional) and report the chronicle-inject seeding gap"
    )
    p_evidence.add_argument("--holder", default=None, help="a named-cast NPC id or raw refid")
    p_evidence.add_argument("--run", default=None, help="a run id -- if given, actually attempts `chronicle inject`")
    p_evidence.add_argument("--runs-dir", default=None, help="passed through to `chronicle --runs-dir`")
    p_evidence.set_defaults(func=cmd_evidence)

    p_listener = sub.add_parser("check-listener", help="confirm the Chronicle listener is reachable and configured")
    p_listener.add_argument("--listener-url", default=DEFAULT_LISTENER_URL, help=f"default: {DEFAULT_LISTENER_URL}")
    p_listener.add_argument("--shared-secret", default=None, help="the listener's --shared-secret, if it has one")
    p_listener.set_defaults(func=cmd_check_listener)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
