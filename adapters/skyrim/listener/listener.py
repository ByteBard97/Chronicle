"""ChronicleBridge listener -- receives ChronicleBridge's outbound POSTs
(adapters/skyrim/contracts/chronicle-bridge.openapi.yaml) and either
writes a rolling JSON snapshot file (/whiterun/positions) or appends a
canonical event to a live run (/whiterun/events,
docs/design/chronicle-bridge-death-extraction.md). Stdlib-only (matches
the throwaway probe's own "http.server is enough" choice) plus pydantic
for schema validation against the generated models.py -- never hand-parse
the body, the whole point of the shared contract is that a malformed
payload is rejected here, not silently misinterpreted.

Not part of chronicle/ -- see this directory's README.md for why, and for
how to regenerate models.py when the contract changes. /whiterun/events
does not import chronicle/ either; it shells out to the same
`python -m chronicle inject` CLI write path a human uses at the console
(chronicle/cli.py), the documented seam boundary, stamped
`--origin-kind adapter` so it's never mislabeled as a console injection.

    uv run --with pydantic python adapters/skyrim/listener/listener.py --shared-secret <token>
    uv run --with pydantic python adapters/skyrim/listener/listener.py --shared-secret <token> --live-run <run_id>

/whiterun/events is unavailable (503) unless --live-run is given -- there
is deliberately no default and no auto-selection of an existing run. Never
point --live-run at a fixture/demo run the M7 release gate or the ladder's
scenario tests depend on (e.g. runs/north-star-01); always a dedicated
live-play run, since injected events are ordinary appends with no undo.

Trust model: this binds 0.0.0.0 because the real topology is a separate
Windows machine on the LAN POSTing in -- it can't be restricted to
loopback. There is no real authentication scheme here (no TLS, no user
accounts) -- `--shared-secret` is a lightweight bearer-token check meant
to stop an accidental/opportunistic LAN neighbor from writing garbage into
the snapshot file, not to withstand a targeted attacker. Do not expose
this port beyond a trusted home LAN.

Read-only exception, /whiterun/hydration (docs/design/chronicle-bridge-
hydration-out.md §3b): this one route DOES import chronicle/ directly
(`chronicle.framelog.FrameLogReader`/`state_at`, `chronicle.social`,
`chronicle.hydration.relationship_rank_for`), unlike every write path in
this file. The house rule above -- "shell out to `python -m chronicle`,
never import chronicle/ directly" -- exists to keep *writes* going
through the CLI's own validation/refusal logic (fork-territory checks,
origin stamping) so this listener can never silently corrupt a run. This
endpoint has no write path at all: it only reconstructs a run's existing
on-disk state (the same `FrameLogReader.state_at()` read `chronicle
sync-check`/`chronicle inspect` already do from inside the CLI process)
and computes a pure function over it. There is nothing for the CLI
boundary to protect here -- a direct import can't corrupt a run it never
writes to -- and shelling out to a fresh `python -m chronicle` subprocess
would still have to pay interpreter startup on top of the same
`state_at()` log replay the direct import already does, buying no safety
in exchange. Write access to a run still goes through the CLI
exclusively -- this exception is scoped to this one GET handler and must
not be used as precedent for adding new write paths that skip the CLI.
"""

import argparse
import json
import secrets
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).parent))
from models import GameEvent, PositionSnapshot

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))
from chronicle.framelog import FrameLogReader, default_runs_dir
from chronicle.hydration import RANK_NO_GRUDGE, relationship_rank_for

# Mirrors adapters/skyrim/ChronicleBridge/src/IdentityMap.cpp's kNamedCast
# table exactly (chronicleNpcId column) -- the same 19-entry set
# chronicle/tests/test_fixtures.py's NAMED_CAST_NPC_IDS already hardcodes
# for its own sync check. Only NPCs in this set have a resolvable in-game
# actor reference `SetRelationshipRank` could ever be called on (design
# doc §3), so /whiterun/hydration filters grudges down to pairs entirely
# within this set. Keep this in sync with IdentityMap.cpp by hand -- there
# is no shared source of truth between C++ and Python for this table.
NAMED_CAST_NPC_IDS = frozenset(
    {
        "ysolda",
        "idolaf_battle_born",
        "saffir",
        "carlotta_valentia",
        "amren",
        "adrianne_avenicci",
        "lars_battle_born",
        "braith",
        "fralia_gray_mane",
        "nazeem",
        "lillith_maiden_loom",
        "brenuin",
        "anoriath",
        "lucia",
        "heimskr",
        "sigurd",
        "olava_the_feeble",
        "danica_pure_spring",
        "olfina_gray_mane",
    }
)

_write_lock = threading.Lock()

# adapters/skyrim/listener/listener.py -> repo root, three parents up.
# `python -m chronicle` needs cwd here to import the chronicle/ package
# (not installed; a plain top-level package, same as every test/CLI
# invocation in this repo already assumes).
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# A snapshot with hundreds of NPCs at ~40 bytes/entry is still well under
# 100KB -- 1MiB is generous headroom, not a real limit on legitimate
# traffic. Anything bigger is either a bug or someone probing the port,
# and must be rejected before `rfile.read()`, not after: reading an
# attacker-declared Content-Length unconditionally is an unbounded
# memory-allocation footgun regardless of how small real payloads are.
_MAX_BODY_BYTES = 1 * 1024 * 1024


def _inject_death_event(event: GameEvent, *, live_run: str) -> tuple[bool, str]:
    """Shell out to ``python -m chronicle inject`` (never import chronicle/ --
    the documented seam boundary, this directory's README.md). Returns
    (ok, message) -- message is stdout on success, stderr on failure, so
    the caller can log/relay chronicle's own reason for a rejection (e.g.
    a historical-tick refusal) rather than swallowing it.
    """
    payload = {
        "event_type": event.event_type.value,
        "gamets": event.gamets,
        "npc_id": event.npc_id,
        "cause": event.cause if event.cause is not None else "unknown",
    }
    if event.killer_id is not None:
        payload["killer_id"] = event.killer_id
    if event.location_id is not None:
        payload["location_id"] = event.location_id

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "chronicle",
            "inject",
            live_run,
            "--event",
            json.dumps(payload),
            "--origin-kind",
            "adapter",
            "--origin-detail",
            "chronicle-bridge death event",
        ],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, result.stderr.strip()
    return True, result.stdout.strip()


def _max_tick(reader: FrameLogReader) -> int | None:
    """The run's current max tick across both streams -- mirrors chronicle/cli.py's own helper of the same name."""
    index = reader.read_index()
    ticks = [int(t) for stream in index["streams"].values() for t in stream["tick_offsets"]]
    return max(ticks) if ticks else None


def _hydration_pairs(live_run: str, last_pushed: dict[tuple[str, str], int]) -> list[dict[str, object]]:
    """Compute changed (holder, target, rank) pairs for the live run's named-cast grudges.

    Reads the run's current on-disk state at its max tick (the same
    FrameLogReader/state_at pattern `chronicle sync-check`/`chronicle
    inspect` use), buckets every grudge whose holder and target are both
    in the named cast via relationship_rank_for(), and returns only the
    pairs whose bucketed rank differs from `last_pushed` -- updating
    `last_pushed` in place as it goes (idempotency, design doc §3b).
    """
    reader = FrameLogReader(default_runs_dir() / live_run)
    max_tick = _max_tick(reader)
    if max_tick is None:
        return []
    state = reader.state_at(max_tick)
    at_gamets = float(max_tick)

    changed: list[dict[str, object]] = []
    for grudge in state.social.grudges():
        if grudge.holder_id not in NAMED_CAST_NPC_IDS or grudge.target_id not in NAMED_CAST_NPC_IDS:
            continue
        rank = relationship_rank_for(grudge, at_gamets=at_gamets)
        key = (grudge.holder_id, grudge.target_id)
        # A pair absent from the cache defaults to rank 0 (no discount),
        # not "unknown" -- 0 is the game's own default relationship rank,
        # so a pair that has always bucketed to 0 must never be reported
        # as a spurious "changed to 0" push on its very first poll.
        if last_pushed.get(key, RANK_NO_GRUDGE) == rank:
            continue
        last_pushed[key] = rank
        changed.append({"holder_id": grudge.holder_id, "target_id": grudge.target_id, "relationship_rank": rank})
    return changed


def _make_handler(snapshot_path: Path, shared_secret: str | None, live_run: str | None) -> type[BaseHTTPRequestHandler]:
    # Idempotency cache (design doc §3b): the last rank pushed for each
    # (holder_id, target_id) pair, so a poll cycle with no state change is
    # a no-op. In-memory only, scoped to this one handler-class closure --
    # it does NOT persist across listener restarts. That is a real, named
    # gap (design doc §3's "Idempotency/staleness" open question): a
    # restarted listener re-announces every currently-nonzero rank (a
    # missing cache entry defaults to comparing against rank 0, see
    # _hydration_pairs) on its first poll after restart, since it has no
    # memory of what a not-yet-built C++ poller previously received. Not
    # solved here.
    last_pushed_rank: dict[tuple[str, str], int] = {}

    class Handler(BaseHTTPRequestHandler):
        def _check_auth(self) -> bool:
            if shared_secret is None:
                return True
            token = self.headers.get("X-Chronicle-Bridge-Token")
            if token is None or not secrets.compare_digest(token, shared_secret):
                self.send_response(401)
                self.end_headers()
                return False
            return True

        def _read_body(self) -> bytes | None:
            """None means a response was already sent (bad/oversized length)."""
            try:
                length = int(self.headers.get("Content-Length", 0))
            except ValueError:
                self.send_response(400)
                self.end_headers()
                return None
            if length <= 0 or length > _MAX_BODY_BYTES:
                self.send_response(413)
                self.end_headers()
                return None
            return self.rfile.read(length)

        def do_POST(self) -> None:
            if self.path == "/whiterun/positions":
                self._handle_positions()
            elif self.path == "/whiterun/events":
                self._handle_events()
            else:
                self.send_response(404)
                self.end_headers()

        def _handle_positions(self) -> None:
            if not self._check_auth():
                return
            raw = self._read_body()
            if raw is None:
                return

            try:
                snapshot = PositionSnapshot.model_validate_json(raw)
            except ValidationError as exc:
                print(f"rejected malformed snapshot: {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            # Atomic-ish write (temp file + rename) so the dashboard's poller
            # never reads a half-written file -- the same torn-record concern
            # docs/frame-log-schema.md's own reader discipline names, applied
            # here even though this file isn't part of the frame log itself.
            with _write_lock:
                tmp_path = snapshot_path.with_suffix(".tmp")
                tmp_path.write_text(json.dumps(snapshot.model_dump(), indent=None))
                tmp_path.replace(snapshot_path)

            self.send_response(204)
            self.end_headers()

        def _handle_events(self) -> None:
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return
            raw = self._read_body()
            if raw is None:
                return

            try:
                event = GameEvent.model_validate_json(raw)
            except ValidationError as exc:
                print(f"rejected malformed event: {exc}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            ok, message = _inject_death_event(event, live_run=live_run)
            if not ok:
                print(f"chronicle inject rejected event: {message}", file=sys.stderr)
                self.send_response(400)
                self.end_headers()
                return

            print(f"[listener] {message}", file=sys.stderr)
            self.send_response(204)
            self.end_headers()

        def do_GET(self) -> None:
            if self.path == "/whiterun/hydration":
                self._handle_hydration()
            else:
                self.send_response(404)
                self.end_headers()

        def _handle_hydration(self) -> None:
            # Same gating convention as /whiterun/events: 503 if no
            # --live-run was given at startup, never a default/auto-selected
            # run (design doc §3b).
            if live_run is None:
                self.send_response(503)
                self.end_headers()
                return
            if not self._check_auth():
                return

            pairs = _hydration_pairs(live_run, last_pushed_rank)
            body = json.dumps(pairs).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            print(f"[listener] {self.address_string()} {format % args}", file=sys.stderr)

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--snapshot-path",
        type=Path,
        default=Path(__file__).parent / "whiterun-positions.json",
        help="Where the rolling snapshot file is written (the dashboard polls this path).",
    )
    parser.add_argument(
        "--shared-secret",
        type=str,
        default=None,
        help="Bearer token ChronicleBridge must send as X-Chronicle-Bridge-Token. "
        "Strongly recommended once this listens on a real LAN interface -- "
        "omitting it accepts POSTs from anyone who can reach the port.",
    )
    parser.add_argument(
        "--live-run",
        type=str,
        default=None,
        help="The run_id /whiterun/events appends detected deaths into, via "
        "'python -m chronicle inject'. No default and no auto-selection of an "
        "existing run -- omitting this makes /whiterun/events return 503. Never "
        "point this at a fixture/demo run the M7 release gate or the ladder's "
        "scenario tests depend on (e.g. runs/north-star-01); always a dedicated "
        "live-play run.",
    )
    args = parser.parse_args()

    if args.shared_secret is None:
        print(
            "[listener] WARNING: running with no --shared-secret -- anyone who can reach "
            "this port on the LAN can write to the snapshot file. Fine for a quick local "
            "test; set --shared-secret before leaving this running on a real network.",
            file=sys.stderr,
        )
    if args.live_run is None:
        print(
            "[listener] /whiterun/events disabled (no --live-run given) -- only "
            "/whiterun/positions is active.",
            file=sys.stderr,
        )

    server = ThreadingHTTPServer(("0.0.0.0", args.port), _make_handler(args.snapshot_path, args.shared_secret, args.live_run))
    print(f"ChronicleBridge listener on :{args.port}, writing {args.snapshot_path}", file=sys.stderr)
    server.serve_forever()


if __name__ == "__main__":
    main()
