#!/usr/bin/env bash
# Restarts the ChronicleBridge listener, picking up code/model changes
# without the classic footgun: a plain `pkill -f listener.py` run in the
# same command that starts the replacement can match the new process's own
# command line and kill it immediately after launch (hit for real during
# development -- see git history). This script kills only PIDs that exist
# *before* it starts anything new.
#
# Usage: adapters/skyrim/listener/restart_listener.sh <shared-secret> [port]

set -euo pipefail

SECRET="${1:?usage: restart_listener.sh <shared-secret> [port]}"
PORT="${2:-8765}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/tmp/chronicle-listener.log"

OLD_PIDS="$(pgrep -f "adapters/skyrim/listener/listener.py" || true)"
if [[ -n "$OLD_PIDS" ]]; then
    echo "Stopping existing listener PID(s): $OLD_PIDS"
    kill $OLD_PIDS
    sleep 1
fi

cd "$SCRIPT_DIR/../../.."
nohup uv run --with pydantic python adapters/skyrim/listener/listener.py \
    --shared-secret "$SECRET" --port "$PORT" > "$LOG_FILE" 2>&1 &
disown

sleep 1
echo "Listener restarted (PID $!), logging to $LOG_FILE"
tail -3 "$LOG_FILE"
