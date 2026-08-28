"""Unit tests for the live harness's Skyrim.ini key assertion."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from adapters.skyrim.livetest.ini import (
    UNATTENDED_KEYS,
    assert_keys,
    assert_keys_in_file,
)


def test_updates_existing_key_and_preserves_everything_else():
    text = "[General]\nsLanguage=ENGLISH\nbAlwaysActive=0\n\n[Display]\nfGamma=1.0\n"
    new, changes = assert_keys(text, {"General": {"bAlwaysActive": "1"}})
    assert new == "[General]\nsLanguage=ENGLISH\nbAlwaysActive=1\n\n[Display]\nfGamma=1.0\n"
    assert changes == ["[General] bAlwaysActive: '0' -> '1'"]


def test_appends_missing_key_inside_its_section_not_after_blank_lines():
    text = "[General]\nsLanguage=ENGLISH\n\n[Display]\nfGamma=1.0\n"
    new, _ = assert_keys(text, {"General": {"bFreebiesSeen": "1"}})
    assert new == "[General]\nsLanguage=ENGLISH\nbFreebiesSeen=1\n\n[Display]\nfGamma=1.0\n"


def test_appends_missing_section_at_end():
    text = "[General]\nsLanguage=ENGLISH\n"
    new, changes = assert_keys(text, {"Bethesda.net": {"bEnablePlatform": "0"}})
    assert new == "[General]\nsLanguage=ENGLISH\n\n[Bethesda.net]\nbEnablePlatform=0"
    assert changes == ["[Bethesda.net] bEnablePlatform=0 (added, new section)"]


def test_no_change_is_idempotent():
    text = "[General]\nbAlwaysActive=1\n"
    new, changes = assert_keys(text, {"General": {"bAlwaysActive": "1"}})
    assert new == text and changes == []


def test_crlf_and_case_insensitive_keys_and_empty_values():
    text = "[general]\r\nSINTROSEQUENCE=BGS_Logo.bik\r\n"
    new, changes = assert_keys(text, {"General": {"sIntroSequence": ""}})
    assert new == "[general]\r\nsIntroSequence=\r\n"
    assert changes == ["[General] sIntroSequence: 'BGS_Logo.bik' -> ''"]


def test_file_round_trip_and_defaults(tmp_path):
    path = tmp_path / "skyrim.ini"
    path.write_text("[General]\nsLanguage=ENGLISH\n")
    changes = assert_keys_in_file(path)
    assert len(changes) == sum(len(v) for v in UNATTENDED_KEYS.values())
    assert assert_keys_in_file(path) == []
    text = path.read_text()
    assert "[Bethesda.net]\nbEnablePlatform=0" in text and "bFreebiesSeen=1" in text
