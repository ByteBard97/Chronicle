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


def _make_handler(snapshot_path: Path, shared_secret: str | None, live_run: str | None) -> type[BaseHTTPRequestHandler]:
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
