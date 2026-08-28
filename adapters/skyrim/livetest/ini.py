"""Minimal, order-preserving INI key assertion for Skyrim's ini files.

``configparser`` is deliberately not used: Skyrim inis have duplicate keys,
no-value keys (``sIntroSequence=``), CRLF endings and comments that must
survive untouched. This edits in place: existing keys are updated, missing
keys are appended to their section, missing sections are appended.
"""

from __future__ import annotations

from pathlib import Path

# Keys that keep an unattended 1.6.1170 launch from stalling on a modal
# (docs/design/live-test-harness.md §2.5): no AE upsell / Creation Club
# platform, no mod-manager menu, no Bethesda.net login prompt, no intro video.
UNATTENDED_KEYS: dict[str, dict[str, str]] = {
    "Bethesda.net": {"bEnablePlatform": "0"},
    "General": {
        "bModManagerMenuEnabled": "0",
        "bFreebiesSeen": "1",
        "bAutoSkipMainMenuLogin": "1",
        "sIntroSequence": "",
        "bAlwaysActive": "1",
    },
}


def assert_keys(text: str, wanted: dict[str, dict[str, str]]) -> tuple[str, list[str]]:
    """Return (new_text, changes). Section names compare case-insensitively; keys too."""
    newline = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(newline) if text else []
    changes: list[str] = []

    def section_bounds(name: str) -> tuple[int, int] | None:
        start = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                if start is not None:
                    return start, i
                if stripped[1:-1].lower() == name.lower():
                    start = i
        return (start, len(lines)) if start is not None else None

    for section, keys in wanted.items():
        bounds = section_bounds(section)
        if bounds is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append(f"[{section}]")
            for key, value in keys.items():
                lines.append(f"{key}={value}")
                changes.append(f"[{section}] {key}={value} (added, new section)")
            continue
        start, end = bounds
        for key, value in keys.items():
            found = False
            for i in range(start + 1, end):
                raw = lines[i]
                if "=" in raw and not raw.lstrip().startswith((";", "#")):
                    k, _, v = raw.partition("=")
                    if k.strip().lower() == key.lower():
                        found = True
                        if v.strip() != value:
                            lines[i] = f"{key}={value}"
                            changes.append(f"[{section}] {key}: {v.strip()!r} -> {value!r}")
                        break
            if not found:
                insert_at = end
                while insert_at > start + 1 and not lines[insert_at - 1].strip():
                    insert_at -= 1
                lines.insert(insert_at, f"{key}={value}")
                changes.append(f"[{section}] {key}={value} (added)")
                end += 1
    return newline.join(lines), changes


def assert_keys_in_file(path: Path, wanted: dict[str, dict[str, str]] = UNATTENDED_KEYS) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    new_text, changes = assert_keys(text, wanted)
    if changes:
        path.write_text(new_text, encoding="utf-8")
    return changes
