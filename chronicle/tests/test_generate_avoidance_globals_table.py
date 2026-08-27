"""Tests for tools/generate-avoidance-globals-table.py.

This script does real regex-bounded surgery on a live C++ source file
(AvoidanceGlobals.cpp) and was previously untested -- unlike the C#
AvoidancePatchBuilder it complements, which has its own dotnet test suite.
Loaded via importlib.util since its filename has hyphens, matching the
technique test_devbench_runbook_seeding.py already established for
tools/chronicle-devbench-runbook.py.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "tools" / "generate-avoidance-globals-table.py"


@pytest.fixture(scope="module")
def gen_module():
    spec = importlib.util.spec_from_file_location("generate_avoidance_globals_table", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_format_entry_hex_and_field_order(gen_module):
    entry = {"npcA": "amren", "npcB": "brenuin", "plugin": "ChroniclePatcher.esp", "globalLocalFormId": "0008d8"}
    line = gen_module.format_entry(entry)
    assert line == '            {"amren", "brenuin", "ChroniclePatcher.esp", 0x0008d8},\n'


def test_format_entry_rejects_unsorted_pair(gen_module):
    entry = {"npcA": "brenuin", "npcB": "amren", "plugin": "ChroniclePatcher.esp", "globalLocalFormId": "0008d8"}
    with pytest.raises(ValueError, match="not lexicographically sorted"):
        gen_module.format_entry(entry)


def test_render_array_sorts_and_sizes_correctly(gen_module):
    # Each entry is already sorted WITHIN its own pair (format_entry's own
    # requirement); render_array's job under test is sorting ACROSS pairs
    # -- fed here in reverse order to prove it actually sorts rather than
    # preserving input order.
    entries = [
        {"npcA": "sigurd", "npcB": "ysolda", "plugin": "ChroniclePatcher.esp", "globalLocalFormId": "00082a"},
        {"npcA": "amren", "npcB": "brenuin", "plugin": "ChroniclePatcher.esp", "globalLocalFormId": "0008d8"},
    ]
    array_text = gen_module.render_array(entries)
    assert "std::array<AvoidancePairEntry, 2>" in array_text
    amren_pos = array_text.index("amren")
    sigurd_pos = array_text.index("sigurd")
    assert amren_pos < sigurd_pos


def test_apply_replacement_replaces_only_the_array_body(gen_module):
    original = (
        "namespace ChronicleBridge {\n"
        "    namespace {\n"
        "        // some comment\n"
        "        constexpr std::array<AvoidancePairEntry, 1> kAvoidancePairGlobals{{\n"
        '            {"a", "b", "ChroniclePatcher.esp", 0x000001},\n'
        "        }};\n"
        "    }\n"
        "    // unrelated trailing code, must survive untouched\n"
        "    std::optional<FormRef> ResolveAvoidancePairGlobal(...) { ... }\n"
        "}\n"
    )
    new_array = (
        "constexpr std::array<AvoidancePairEntry, 2> kAvoidancePairGlobals{{\n"
        '            {"c", "d", "ChroniclePatcher.esp", 0x000002},\n'
        '            {"e", "f", "ChroniclePatcher.esp", 0x000003},\n'
        "        }};\n"
    )

    result = gen_module.apply_replacement(original, new_array)

    assert "std::array<AvoidancePairEntry, 2>" in result
    assert '"c", "d"' in result
    assert '"e", "f"' in result
    assert '"a", "b"' not in result
    # Everything outside the array literal must be byte-identical.
    assert "// unrelated trailing code, must survive untouched" in result
    assert "ResolveAvoidancePairGlobal" in result
    assert result.startswith("namespace ChronicleBridge {\n    namespace {\n        // some comment\n")
    assert result.endswith("}\n")


def test_apply_replacement_raises_if_array_start_marker_missing(gen_module):
    text_without_array = "namespace ChronicleBridge {\n    // no array here at all\n}\n"
    with pytest.raises(ValueError, match="could not find kAvoidancePairGlobals array start"):
        gen_module.apply_replacement(text_without_array, "irrelevant")


def test_apply_replacement_raises_if_array_end_marker_missing(gen_module):
    # A start marker with no closing `}};` -- e.g. a truncated/corrupted file.
    text_without_end = (
        "constexpr std::array<AvoidancePairEntry, 1> kAvoidancePairGlobals{{\n"
        '            {"a", "b", "ChroniclePatcher.esp", 0x000001},\n'
    )
    with pytest.raises(ValueError, match="could not find kAvoidancePairGlobals array end"):
        gen_module.apply_replacement(text_without_end, "irrelevant")
