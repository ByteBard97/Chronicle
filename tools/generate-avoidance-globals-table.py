#!/usr/bin/env python3
"""Generates the kAvoidancePairGlobals array body in
adapters/skyrim/ChronicleBridge/src/AvoidanceGlobals.cpp from
tools/chronicle-patcher/out/chronicle-globals.json.

Re-run this whenever IdentityMap.cpp's/IdentityMap.cs's named-cast roster
changes (adds/removes an NPC): that changes the 19-choose-2 pair set, which
means tools/chronicle-patcher/ must be re-run first to regenerate
chronicle-globals.json, and then this script must be re-run to regenerate
AvoidanceGlobals.cpp's table from that new JSON.

Usage:
    python3 tools/generate-avoidance-globals-table.py

Reads:
    tools/chronicle-patcher/out/chronicle-globals.json
Writes (in place, replacing the kAvoidancePairGlobals array literal only):
    adapters/skyrim/ChronicleBridge/src/AvoidanceGlobals.cpp
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
JSON_PATH = REPO_ROOT / "tools" / "chronicle-patcher" / "out" / "chronicle-globals.json"
CPP_PATH = REPO_ROOT / "adapters" / "skyrim" / "ChronicleBridge" / "src" / "AvoidanceGlobals.cpp"

ARRAY_START_RE = re.compile(
    r"constexpr std::array<AvoidancePairEntry, \d+> kAvoidancePairGlobals\{\{\n"
)
ARRAY_END_RE = re.compile(r"[ \t]*\}\};\n")
ARRAY_END = "        }};\n"


def format_entry(entry: dict) -> str:
    npc_a = entry["npcA"]
    npc_b = entry["npcB"]
    if npc_b < npc_a:
        raise ValueError(f"pair ({npc_a}, {npc_b}) is not lexicographically sorted")
    plugin = entry["plugin"]
    local_form_id = int(entry["globalLocalFormId"], 16)
    return f'            {{"{npc_a}", "{npc_b}", "{plugin}", 0x{local_form_id:06x}}},\n'


def main() -> int:
    entries = json.loads(JSON_PATH.read_text())
    entries = sorted(entries, key=lambda e: (e["npcA"], e["npcB"]))

    body = "".join(format_entry(e) for e in entries)
    new_array = (
        f"constexpr std::array<AvoidancePairEntry, {len(entries)}> kAvoidancePairGlobals{{{{\n"
        + body
        + ARRAY_END
    )

    text = CPP_PATH.read_text()
    match = ARRAY_START_RE.search(text)
    if not match:
        print("ERROR: could not find kAvoidancePairGlobals array start in AvoidanceGlobals.cpp", file=sys.stderr)
        return 1
    end_match = ARRAY_END_RE.search(text, match.end())
    if not end_match:
        print("ERROR: could not find kAvoidancePairGlobals array end in AvoidanceGlobals.cpp", file=sys.stderr)
        return 1
    new_text = text[: match.start()] + new_array + text[end_match.end() :]

    CPP_PATH.write_text(new_text)
    print(f"Wrote {len(entries)} entries to {CPP_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
