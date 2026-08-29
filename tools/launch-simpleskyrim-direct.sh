#!/usr/bin/env bash
# Launches SimpleSkyrim by invoking skse64_loader.exe directly via Proton,
# bypassing Mod Organizer 2 / usvfs entirely.
#
# Why not moshortcut://SKSE like tools/launch-chronicledev-skse.sh: MO2's
# named-shortcut launch was unreliable for this instance during initial
# bring-up on 2026-08-28 -- the MO2 process would sometimes silently die
# before spawning anything, with no crash log and no diagnosed root
# cause. This direct-loader path launched cleanly every time it was
# tried that session (proven: 140s stable run in Whiterun with the full
# target mod stack active and ChronicleBridge's HTTP loop confirmed
# live end-to-end). See docs/design/simple-modlist-milestone.md.
#
# Because this bypasses MO2's virtual filesystem, SimpleSkyrim's mods
# are deployed as loose files directly into "Stock Game/Data" -- see
# tools/deploy-simpleskyrim-loose.sh, which is this instance's actual
# install mechanism. MO2's own mods/ folder and profiles/Default/
# modlist.txt are NOT used to manage this instance; they're kept around
# only as an artifact of the original hardlink-clone from ChronicleDev.
#
# Own Proton prefix (compatdata/4190904831), isolated from every other
# instance's Wine state.

set -euo pipefail

STEAM_ROOT="/home/geoff/.local/share/Steam"
COMPATDATA="$STEAM_ROOT/steamapps/compatdata/4190904831"
PROTON="$STEAM_ROOT/compatibilitytools.d/GE-Proton10-14/proton"
SIMPLESKYRIM_DIR="/home/geoff/Games/SimpleSkyrim/Stock Game"

mkdir -p "$COMPATDATA"

export DISPLAY="${DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/run/user/1000/gdm/Xauthority}"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT"
export STEAM_COMPAT_DATA_PATH="$COMPATDATA"
export STEAM_COMPAT_MOUNTS="/mnt/games/SteamLibrary"

cd "$SIMPLESKYRIM_DIR"
exec "$PROTON" waitforexitandrun "$(pwd)/skse64_loader.exe"
