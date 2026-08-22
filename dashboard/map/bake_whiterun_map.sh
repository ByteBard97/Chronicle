#!/usr/bin/env bash
# Bake the WhiterunWorld top-down map backdrop for the Chronicle dashboard.
#
# Renders real Skyrim geometry (WhiterunWorld worldspace, form ID 0x0001A26F)
# from the user's own game files using fo76utils (MIT,
# https://github.com/fo76utils/fo76utils). Output is Bethesda-derived:
# internal tooling only, never committed or redistributed (gitignored).
#
# Usage: ./bake_whiterun_map.sh <fo76utils_dir> <skyrim_data_dir> [out_dir]
#   <fo76utils_dir>    build tree containing ./render and ./esmdump
#   <skyrim_data_dir>  a Skyrim SE "Data" directory (Skyrim.esm + BSAs;
#                      the 1.6.1170 depot staging dir works fine)
#   [out_dir]          defaults to the directory containing this script
#
# Produces whiterun_topdown_4k.png, whose world->pixel calibration lives in
# whiterun_map.json (committed). If you change -view or the image size,
# regenerate the transform in that file: px = s*x + offsX + W/2,
# py = -s*y + offsY + H/2 (RX=180 top-down; see docs/research/
# 14-isometric-render-foundations.md, Verification section).
set -euo pipefail

FO76UTILS="$1"
DATA="$2"
OUT="${3:-$(cd "$(dirname "$0")" && pwd)}"

"$FO76UTILS/render" "$DATA/Skyrim.esm" "$OUT/whiterun_topdown_4k.png" \
  4096 4096 "$DATA" \
  -w 0x0001A26F \
  -deftxt 0x00000C16 \
  -env textures/cubemaps/chrome_e.dds \
  -light 2.6 70.5288 135 \
  -ltxtres 256 \
  -rq 10 \
  -mip 1 -lmip 1 \
  -view 0.2 180 0 0 -4915 -1229 8192

echo "wrote $OUT/whiterun_topdown_4k.png"
