#!/usr/bin/env bash
# Twin of launch-ngvo-skse.sh, pointed at the new minimal ChronicleDev
# instance instead of NGVO. Same moshortcut://SKSE mechanism (MO2's
# native way to launch a named customExecutables entry without its
# window, still through MO2's virtual filesystem). See that script's
# header comments for the fuller rationale (why not Steam's -applaunch,
# why not gamescope).
#
# Uses a fresh, arbitrary Proton prefix (compatdata/4190904830) --
# picked as NGVO's id (4190904829) + 1, has no real Steam appmanifest
# behind it (same as NGVO's own non-Steam-shortcut setup), created on
# first run by Proton itself. Isolated from NGVO's own prefix -- this
# instance never shares Wine state with it.

set -euo pipefail

STEAM_ROOT="/home/geoff/.local/share/Steam"
COMPATDATA="$STEAM_ROOT/steamapps/compatdata/4190904830"
PROTON="$STEAM_ROOT/compatibilitytools.d/GE-Proton10-14/proton"
CHRONICLEDEV_DIR="/home/geoff/Games/ChronicleDev"

export DISPLAY="${DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/run/user/1000/gdm/Xauthority}"
export STEAM_COMPAT_MOUNTS="/mnt/games/SteamLibrary:/home/geoff/Games/Modlist_Downloads"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT"
export STEAM_COMPAT_DATA_PATH="$COMPATDATA"
export __GL_THREADED_OPTIMIZATIONS=0

exec "$PROTON" waitforexitandrun \
    "$CHRONICLEDEV_DIR/ModOrganizer.exe" 'moshortcut://SKSE'
