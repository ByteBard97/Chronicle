#!/usr/bin/env bash
# Deploys SimpleSkyrim's enabled mods as loose files into "Stock Game/Data".
#
# This instance is launched via tools/launch-simpleskyrim-direct.sh, which
# invokes skse64_loader.exe directly and bypasses MO2/usvfs entirely (MO2's
# moshortcut launch was unreliable for this instance -- see
# docs/design/simple-modlist-milestone.md). Without MO2's virtual
# filesystem there is no runtime mod merging, so this script does that
# merge once, up front, by copying mod content into Data directly.
#
# Source of truth for "what's enabled" is MO2's own
# profiles/Default/modlist.txt (+name = enabled, -name = disabled) --
# it already matches what was hand-verified working in the 2026-08-28
# 140s stable run, so there is no second list to keep in sync. Mod
# *content* still lives under mods/<name>/ (an MO2 mod folder is just a
# Data-shaped tree), so mods/ remains the install location; this script
# only decides what gets copied into Data and in what order.
#
# Idempotent and re-runnable: safe to run again after adding/removing a
# mod's files under mods/<name>/ or flipping its +/- in modlist.txt.
# Does NOT remove files for mods that were deployed by a previous run
# and are now disabled -- if you disable a mod, clear Data by hand
# first (or re-clone Stock Game from a clean baseline) before
# redeploying.
#
# MO2 priority semantics: modlist.txt lists highest-priority mods first;
# on a file conflict, the higher (earlier-listed) mod wins. This script
# replicates that by deploying in *reverse* file order, so top-listed
# mods are copied last and overwrite anything below them.

set -euo pipefail

INSTANCE_DIR="/home/geoff/Games/SimpleSkyrim"
MODS_DIR="$INSTANCE_DIR/mods"
GAME_DIR="$INSTANCE_DIR/Stock Game"
DATA_DIR="$GAME_DIR/Data"
MODLIST="$INSTANCE_DIR/profiles/Default/modlist.txt"

if [ ! -f "$MODLIST" ]; then
    echo "modlist.txt not found: $MODLIST" >&2
    exit 1
fi

enabled=()
while IFS= read -r line; do
    line="${line%$'\r'}"  # MO2 writes modlist.txt with CRLF line endings
    case "$line" in
        +*) enabled+=("${line#+}") ;;
    esac
done < "$MODLIST"

if [ "${#enabled[@]}" -eq 0 ]; then
    echo "No enabled (+) mods found in $MODLIST -- nothing to deploy." >&2
    exit 1
fi

echo "Enabled mods (MO2 priority order, top wins):"
printf '  %s\n' "${enabled[@]}"

mkdir -p "$DATA_DIR"

# Reverse the array so the top (highest-priority) mod copies last.
for (( i=${#enabled[@]}-1; i>=0; i-- )); do
    name="${enabled[i]}"
    src="$MODS_DIR/$name"
    if [ ! -d "$src" ]; then
        echo "SKIP (mod folder missing): $name" >&2
        continue
    fi
    echo "Deploying: $name"
    # -a preserves the tree; trailing slash on src copies contents, not
    # the folder itself; meta.ini is MO2 bookkeeping, not a game file.
    # MO2's "Root" convention: a mod's Root/ subfolder deploys to the
    # game's install root (Stock Game/), not Data/ -- SKSE64 ships its
    # loader/dlls this way. Everything else in the mod folder is a
    # normal Data-relative tree.
    if [ -d "$src/Root" ]; then
        rsync -a "$src/Root/" "$GAME_DIR/"
        rsync -a --exclude='meta.ini' --exclude='Root' "$src/" "$DATA_DIR/"
    else
        rsync -a --exclude='meta.ini' "$src/" "$DATA_DIR/"
    fi
done

echo "Done. Deployed ${#enabled[@]} mod(s) into: $DATA_DIR"
