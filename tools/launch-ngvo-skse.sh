#!/usr/bin/env bash
# UNTESTED in this corrected form (2026-08-25) -- the quoted variant
# (`moshortcut://"SKSE"`) was run repeatedly and reliably reached MO2,
# but MO2's own log (Games/NGVO/logs/mo_interface.log) proved it always
# failed: `Executable '"SKSE"' does not exist in instance 'Portable'.`
# MO2 takes the argument literally; the real customExecutables title is
# `SKSE`, no quotes. This file has the fix but has not yet been run
# successfully end to end -- verify before trusting it.
#
# Launches NGVO's SKSE target directly, bypassing Steam's GUI and its
# `-applaunch` state machine entirely (that mechanism proved unreliable --
# it silently no-ops or throws "Game configuration unavailable" depending
# on internal client state that's opaque from the outside, and killing a
# hung launch's `reaper` process wedges it further). This runs the exact
# Proton invocation Steam itself builds for the NGVO non-Steam shortcut
# (captured from a working run's own process tree), so it's scriptable
# without Steam being involved in the launch decision at all.
#
# NOTE: does NOT wrap the launch in gamescope. gamescope was tried as a
# fix for a known NVIDIA+Proton+DXVK alt-tab freeze, but this desktop
# runs a pure X11 session (no Wayland) and the installed gamescope build
# (ppa:samoilov-lex/gamescope) only supports nesting inside a Wayland
# compositor or falling back to a headless/pipewire-only output -- it
# always chose headless here regardless of DISPLAY/XAUTHORITY, so nothing
# ever appeared on screen. gamescope is a dead end on this system;
# don't retry it here. The alt-tab freeze itself is still uncharacterized:
# it reproduces on any focus loss, `__GL_THREADED_OPTIMIZATIONS=0` alone
# did not fix it, and nobody has yet established whether game *logic*
# halts or only the display does (a coordinate diff across
# whiterun-positions.json snapshots taken before/during a freeze would
# answer this -- not yet done).
#
# moshortcut://SKSE is Mod Organizer 2's native mechanism for launching a
# named customExecutables entry (Tools > Executables in the MO2 GUI)
# without showing its window at all -- still runs through MO2's virtual
# filesystem/mod list, just skips the "select target, click Run" step.
# No quotes around the title -- MO2 matches it literally.

set -euo pipefail

STEAM_ROOT="/home/geoff/.local/share/Steam"
COMPATDATA="$STEAM_ROOT/steamapps/compatdata/4190904829"
PROTON="$STEAM_ROOT/compatibilitytools.d/GE-Proton10-14/proton"
NGVO_DIR="/home/geoff/Games/NGVO"

export DISPLAY="${DISPLAY:-:1}"
export XAUTHORITY="${XAUTHORITY:-/run/user/1000/gdm/Xauthority}"
export STEAM_COMPAT_MOUNTS="/mnt/games/SteamLibrary:/home/geoff/Games/Modlist_Downloads"
export STEAM_COMPAT_CLIENT_INSTALL_PATH="$STEAM_ROOT"
export STEAM_COMPAT_DATA_PATH="$COMPATDATA"
export __GL_THREADED_OPTIMIZATIONS=0

exec "$PROTON" waitforexitandrun \
    "$NGVO_DIR/ModOrganizer.exe" 'moshortcut://SKSE'
