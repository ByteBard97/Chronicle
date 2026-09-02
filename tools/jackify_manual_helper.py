#!/usr/bin/env python3
"""Helper for Jackify/Wabbajack manual-download workflows on Linux.

This does NOT automate Nexus downloads (that would violate Nexus ToS and risk
an account ban). It extracts the modlist, builds a structured task list, opens
browser tabs in polite batches, and watches the download folder so you can click
through the manual downloads efficiently.
"""

from __future__ import annotations

import argparse
import configparser
import csv
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

JACKIFY_DATA_DIR = Path.home() / "Jackify"
DOWNLOADED_MODLISTS_DIR = JACKIFY_DATA_DIR / "downloaded_mod_lists"
MODLIST_DOWNLOADS_DIR = Path.home() / "Games" / "Modlist_Downloads"
WATCH_DIR = Path.home() / "Downloads"
STEAM_LIBRARY = Path("/mnt/games/SteamLibrary")
SKYRIM_DIR = (
    STEAM_LIBRARY
    / "steamapps"
    / "common"
    / "Skyrim Special Edition"
)

GAME_DOMAINS = {
    "SkyrimSpecialEdition": "skyrimspecialedition",
    "SkyrimSE": "skyrimspecialedition",
}


@dataclass(frozen=True)
class Archive:
    name: str
    size: int
    hash_b64: str
    downloader: str
    meta: dict[str, str]
    state: dict

    @property
    def nexus_url(self) -> str | None:
        """Return a Nexus file-page URL if this is a Nexus download."""
        if self.source_label != "Nexus":
            return None
        game = self.state.get("GameName", "SkyrimSpecialEdition")
        domain = GAME_DOMAINS.get(game, game.lower())
        mod_id = self.state.get("ModID")
        file_id = self.state.get("FileID")
        if mod_id is None or file_id is None:
            return None
        return f"https://www.nexusmods.com/{domain}/mods/{mod_id}?tab=files&file_id={file_id}"

    @property
    def direct_url(self) -> str | None:
        """Return a direct URL for non-Nexus downloads when available."""
        if self.source_label == "HTTP":
            return self.state.get("Url")
        return None

    @property
    def source_label(self) -> str:
        base = self.downloader.split(",")[0].strip()
        if base == "NexusDownloader":
            return "Nexus"
        if base == "GameFileSourceDownloader":
            return "GameFile"
        if base == "HttpDownloader":
            return "HTTP"
        if "GoogleDrive" in base:
            return "GoogleDrive"
        if "WabbajackCDN" in base:
            return "WabbajackCDN"
        return base.split(".")[-1]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["source"] = self.source_label
        d["nexus_url"] = self.nexus_url
        d["direct_url"] = self.direct_url
        return d


def _parse_meta(meta_text: str) -> dict[str, str]:
    cfg = configparser.ConfigParser()
    try:
        cfg.read_string(meta_text)
    except configparser.Error:
        return {}
    result: dict[str, str] = {}
    if "General" in cfg:
        result.update(cfg["General"])
    return result


def _archive_from_json(obj: dict) -> Archive:
    state = obj.get("State", {})
    downloader = state.get("$type", "Unknown")
    return Archive(
        name=obj["Name"],
        size=int(obj.get("Size", 0)),
        hash_b64=obj.get("Hash", ""),
        downloader=downloader,
        meta=_parse_meta(obj.get("Meta", "")),
        state=state,
    )


def find_wabbajack_file() -> Path | None:
    if not DOWNLOADED_MODLISTS_DIR.exists():
        return None
    files = sorted(DOWNLOADED_MODLISTS_DIR.glob("*.wabbajack"))
    return files[0] if files else None


def load_modlist(wabbajack_path: Path | None = None, cache_dir: Path | None = None) -> dict:
    """Load the modlist JSON from inside a .wabbajack archive, with local caching."""
    wabbajack_path = wabbajack_path or find_wabbajack_file()
    if wabbajack_path is None or not wabbajack_path.exists():
        raise FileNotFoundError(
            f"No .wabbajack file found in {DOWNLOADED_MODLISTS_DIR}. "
            "Pass --wabbajack explicitly."
        )

    cache_dir = cache_dir or (JACKIFY_DATA_DIR / "modlist-json-cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / f"{wabbajack_path.name}.modlist.json"

    if cache_file.exists() and cache_file.stat().st_mtime >= wabbajack_path.stat().st_mtime:
        with cache_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    with zipfile.ZipFile(wabbajack_path, "r") as zf:
        try:
            info = zf.getinfo("modlist")
        except KeyError:
            raise RuntimeError("This .wabbajack archive does not contain a 'modlist' member.")
        raw = zf.read(info)

    data = json.loads(raw.decode("utf-8"))
    with cache_file.open("w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def iter_archives(data: dict) -> Iterable[Archive]:
    for obj in data.get("Archives", []):
        yield _archive_from_json(obj)


def already_downloaded(name: str) -> bool:
    """Check whether the expected archive filename is already in Modlist_Downloads."""
    target = MODLIST_DOWNLOADS_DIR / name
    return target.exists()


def _build_game_file_lookup() -> dict[str, Path]:
    """Map sanitized modlist names to actual on-disk paths.

    The modlist stores game-file paths with '/' replaced by '_', e.g.
      Data_Skyrim - Sounds.bsa  -> Data/Skyrim - Sounds.bsa
      Data_Video_BGS_Logo.bik   -> Data/Video/BGS_Logo.bik
      Skyrim_SkyrimPrefs.ini    -> Skyrim/SkyrimPrefs.ini
    """
    lookup: dict[str, Path] = {}
    if not SKYRIM_DIR.exists():
        return lookup
    for path in SKYRIM_DIR.rglob("*"):
        if path.is_file():
            rel = path.relative_to(SKYRIM_DIR).as_posix()
            key = rel.replace("/", "_")
            lookup[key] = path
    return lookup


_GAME_FILE_LOOKUP: dict[str, Path] | None = None


def resolve_game_file(name: str) -> Path | None:
    """Return the actual on-disk path for a GameFileSource modlist name."""
    global _GAME_FILE_LOOKUP
    if _GAME_FILE_LOOKUP is None:
        _GAME_FILE_LOOKUP = _build_game_file_lookup()
    # Try direct lookup first.
    if name in _GAME_FILE_LOOKUP:
        return _GAME_FILE_LOOKUP[name]
    # Fall back to case-insensitive match.
    name_lower = name.lower()
    for key, path in _GAME_FILE_LOOKUP.items():
        if key.lower() == name_lower:
            return path
    return None


def game_file_path(name: str) -> Path:
    """Best-effort expected path for display when the file is missing."""
    resolved = resolve_game_file(name)
    if resolved:
        return resolved
    # Fallback to the slash-to-underscore reconstruction.
    return SKYRIM_DIR / name.replace("_", "/")


def cmd_report(args: argparse.Namespace) -> int:
    data = load_modlist(args.wabbajack)
    archives = list(iter_archives(data))

    total = len(archives)
    by_source: dict[str, int] = {}
    pending_nexus = []
    pending_other = []
    missing_game_files = []
    already_have = 0

    for arc in archives:
        by_source[arc.source_label] = by_source.get(arc.source_label, 0) + 1
        if arc.source_label == "Nexus":
            if already_downloaded(arc.name):
                already_have += 1
            else:
                pending_nexus.append(arc)
        elif arc.source_label == "GameFile":
            path = resolve_game_file(arc.name)
            if path is None:
                missing_game_files.append((arc.name, game_file_path(arc.name)))
        else:
            if not already_downloaded(arc.name):
                pending_other.append(arc)

    print(f"Modlist: {data.get('Name')} v{data.get('Version')} by {data.get('Author')}")
    print(f"Game type: {data.get('GameType')}")
    print(f"Total archives: {total}")
    print("\nBy source:")
    for source, count in sorted(by_source.items(), key=lambda x: -x[1]):
        print(f"  {source:16} {count:5}")

    print(f"\nNexus archives already present:     {already_have}")
    print(f"Nexus archives still pending:       {len(pending_nexus)}")
    print(f"Non-Nexus archives still pending:   {len(pending_other)}")

    if missing_game_files:
        print(f"\nMissing game files ({len(missing_game_files)}):")
        for name, path in missing_game_files:
            print(f"  {name}")
            print(f"      expected at: {path}")
    else:
        print("\nAll required game files are present.")

    if pending_other:
        print("\nOther pending downloads:")
        for arc in pending_other:
            url = arc.direct_url or arc.nexus_url or "(no URL)"
            print(f"  [{arc.source_label}] {arc.name}\n      {url}")

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "source", "name", "size", "nexus_url", "direct_url", "present"
            ])
            for arc in archives:
                writer.writerow([
                    arc.source_label,
                    arc.name,
                    arc.size,
                    arc.nexus_url or "",
                    arc.direct_url or "",
                    "yes" if already_downloaded(arc.name) else "no",
                ])
        print(f"\nWrote full report to: {out}")

    return 0


def cmd_urls(args: argparse.Namespace) -> int:
    data = load_modlist(args.wabbajack)
    rows = []
    for arc in iter_archives(data):
        if arc.source_label != "Nexus":
            continue
        if already_downloaded(arc.name) and not args.all:
            continue
        url = arc.nexus_url
        if url:
            rows.append({
                "name": arc.name,
                "size": arc.size,
                "url": url,
            })

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "size", "url"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} Nexus URLs to: {out}")
    return 0


def cmd_open_batch(args: argparse.Namespace) -> int:
    """Open a batch of Nexus file pages in the default browser."""
    data = load_modlist(args.wabbajack)
    pending = [
        arc for arc in iter_archives(data)
        if arc.source_label == "Nexus"
        and arc.nexus_url
        and not already_downloaded(arc.name)
    ]

    start = args.offset
    end = min(start + args.count, len(pending))
    batch = pending[start:end]

    if not batch:
        print("No pending Nexus downloads in that range.")
        return 0

    print(f"Opening {len(batch)} tabs ({start}..{end - 1} of {len(pending)} pending)...")
    for i, arc in enumerate(batch):
        url = arc.nexus_url
        assert url is not None
        print(f"  [{start + i}] {arc.name}")
        subprocess.run(["xdg-open", url], check=False)
        if i < len(batch) - 1:
            time.sleep(args.delay)

    print(f"\nNext batch starts at offset {end}. Run:")
    print(f"  python3 {Path(__file__).name} open-batch --offset {end} --count {args.count}")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """Watch the download folder and report matching expected files."""
    data = load_modlist(args.wabbajack)
    expected_names = {
        arc.name for arc in iter_archives(data)
        if not already_downloaded(arc.name)
    }

    watch_dir = Path(args.watch_dir)
    if not watch_dir.exists():
        print(f"Watch directory does not exist: {watch_dir}")
        return 1

    print(f"Watching {watch_dir} for {len(expected_names)} expected files...")
    print("Press Ctrl+C to stop.")
    known: set[Path] = set()
    try:
        while True:
            current = {p for p in watch_dir.iterdir() if p.is_file()}
            new = current - known
            for p in new:
                if p.name in expected_names:
                    size = p.stat().st_size
                    print(f"[MATCH] {p.name} ({size} bytes)")
                    if args.move:
                        dest = MODLIST_DOWNLOADS_DIR / p.name
                        MODLIST_DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(p), str(dest))
                        print(f"        moved to {dest}")
                elif args.verbose:
                    print(f"[skip]  {p.name}")
            known = current
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def cmd_check_game(args: argparse.Namespace) -> int:
    data = load_modlist(args.wabbajack)
    missing = []
    for arc in iter_archives(data):
        if arc.source_label != "GameFile":
            continue
        path = resolve_game_file(arc.name)
        if path is None:
            missing.append((arc.name, game_file_path(arc.name)))

    if missing:
        print(f"Missing {len(missing)} game files:")
        for name, path in missing:
            print(f"  {name}")
            print(f"      {path}")
        print("\nFix: launch Skyrim SE once through Steam so Anniversary Edition /")
        print("Creation Club content downloads. If still missing, verify game files.")
        return 1
    print("All required game files are present.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Helper for Jackify manual downloads on Linux."
    )
    parser.add_argument(
        "--wabbajack",
        type=Path,
        default=None,
        help="Path to the .wabbajack modlist (auto-detected by default).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_report = sub.add_parser("report", help="Print a summary of pending downloads.")
    p_report.add_argument("-o", "--output", help="Write full CSV report to this path.")

    p_urls = sub.add_parser("urls", help="Write a CSV of Nexus download URLs.")
    p_urls.add_argument("-o", "--output", default="apostasy_nexus_urls.csv")
    p_urls.add_argument("--all", action="store_true", help="Include already-present files.")

    p_open = sub.add_parser("open-batch", help="Open a batch of Nexus pages in the browser.")
    p_open.add_argument("--offset", type=int, default=0, help="Start index into pending list.")
    p_open.add_argument("--count", type=int, default=10, help="How many tabs to open.")
    p_open.add_argument("--delay", type=float, default=1.5, help="Seconds between tab opens.")

    p_watch = sub.add_parser("watch", help="Watch Downloads for expected mod files.")
    p_watch.add_argument("--watch-dir", type=Path, default=WATCH_DIR)
    p_watch.add_argument("--interval", type=float, default=2.0)
    p_watch.add_argument("--move", action="store_true", help="Move matches to Modlist_Downloads.")
    p_watch.add_argument("-v", "--verbose", action="store_true")

    p_check = sub.add_parser("check-game", help="Check required Skyrim game files.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return globals()[f"cmd_{args.command.replace('-', '_')}"](args)


if __name__ == "__main__":
    sys.exit(main())
