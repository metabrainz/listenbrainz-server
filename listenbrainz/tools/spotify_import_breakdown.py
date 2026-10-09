#!/usr/bin/env python3
""" Standalone tool to preview a Spotify Extended Streaming History import.

    Given the zip file (or extracted folder) that Spotify provides for the
    "Extended streaming history" privacy download, this prints a breakdown of
    which entries ListenBrainz would import and which it would skip, and why.

    It uses only the Python standard library so it can be downloaded and run
    on its own, without installing ListenBrainz:

        python3 spotify_import_breakdown.py my_spotify_data.zip
        python3 spotify_import_breakdown.py extracted_folder/
        python3 spotify_import_breakdown.py Streaming_History_Audio_2023_1.json --show-skipped 5

    The classification rules mirror the actual importer in
    listenbrainz/background/listens_importer/spotify.py -- keep the two in
    sync when the import rules change.
"""
import argparse
import json
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Keep in sync with listenbrainz/background/listens_importer/spotify.py
SKIP_REASONS = [
    None, "fwdbtn", "backbtn", "clickrow", "clickside", "endplay", "playbtn", "remote", "logout",
    "popup", "trackerror", "unexpected-exit", "unexpected-exit-while-paused", "unknown"
]

# categories, in the order they are reported
IMPORTED = "imported"
NEEDS_LOOKUP = "needs_lookup"
SHORT_PLAY = "short_play"
INCOGNITO = "incognito"
NO_TRACK_LINK = "no_track_link"
INVALID = "invalid"

CATEGORY_LABELS = {
    IMPORTED: "Would be imported",
    NEEDS_LOOKUP: "Imported only if Spotify metadata lookup succeeds (no track/artist name in file)",
    SHORT_PLAY: "Skipped: played under 30 seconds and manually skipped or interrupted",
    INCOGNITO: "Skipped: played in incognito/private session",
    NO_TRACK_LINK: "Skipped: no track link (podcast episodes, videos, audiobooks)",
    INVALID: "Skipped: entry could not be parsed",
}


def matches_import_filter(filename: str) -> bool:
    """ Same file filter the ListenBrainz importer applies inside the zip. """
    name = Path(filename).name.lower()
    return name.endswith(".json") and ("audio" in name or "endsong" in name)


def is_account_data_history(filename: str) -> bool:
    """ Detect files from the *simplified* "Account data" export

        (StreamingHistory_music_0.json etc). Those are a different, reduced
        format that the ListenBrainz importer does not read at all -- a very
        common source of "why did nothing import" confusion.
    """
    name = Path(filename).name.lower()
    return name.endswith(".json") and name.startswith("streaminghistory")


def classify_entry(item) -> tuple[str, str]:
    """ Classify one streaming-history entry.

        Returns (category, detail). The checks and their order mirror
        SpotifyListensImporter (_skip_item, then parse_listen_batch).
    """
    if not isinstance(item, dict):
        return INVALID, "entry is not an object"

    try:
        datetime.strptime(item["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        return INVALID, "missing or malformed 'ts' timestamp"

    if item.get("incognito_mode", False):
        return INCOGNITO, ""

    if (
        item.get("ms_played", 0) < 30000 and
        (
            item.get("skipped", False) or
            ("reason_end" in item and item["reason_end"] in SKIP_REASONS)
        )
    ):
        reason = "skipped flag" if item.get("skipped", False) else f"reason_end={item.get('reason_end')}"
        return SHORT_PLAY, reason

    uri = item.get("spotify_track_uri")
    if not isinstance(uri, str) or len(uri.split(":")) < 3:
        if item.get("spotify_episode_uri"):
            return NO_TRACK_LINK, "podcast episode"
        return NO_TRACK_LINK, "no spotify_track_uri"

    if not item.get("master_metadata_track_name") or not item.get("master_metadata_album_artist_name"):
        return NEEDS_LOOKUP, ""

    return IMPORTED, ""


class Breakdown:
    """ Accumulates per-category counts and example entries. """

    def __init__(self, max_examples: int):
        self.max_examples = max_examples
        self.counts = Counter()
        self.details = Counter()
        self.examples = {}
        self.files_scanned = []
        self.files_ignored = []
        self.account_data_files = []

    def add_entry(self, item) -> None:
        category, detail = classify_entry(item)
        self.counts[category] += 1
        if detail:
            self.details[f"{category}: {detail}"] += 1
        examples = self.examples.setdefault(category, [])
        if category != IMPORTED and len(examples) < self.max_examples:
            examples.append(_describe(item))

    @property
    def total(self) -> int:
        return sum(self.counts.values())


def _describe(item) -> str:
    if not isinstance(item, dict):
        return repr(item)[:80]
    name = item.get("master_metadata_track_name") or item.get("episode_name") or "<no name>"
    artist = item.get("master_metadata_album_artist_name") or item.get("episode_show_name") or "<no artist>"
    return f"{item.get('ts', '<no ts>')}  {artist} - {name} ({item.get('ms_played', '?')} ms)"


def _analyze_stream(fileobj, breakdown: Breakdown) -> None:
    try:
        entries = json.load(fileobj)
    except (json.JSONDecodeError, UnicodeDecodeError):
        breakdown.counts[INVALID] += 1
        breakdown.details[f"{INVALID}: file is not valid JSON"] += 1
        return
    if not isinstance(entries, list):
        entries = [entries]
    for item in entries:
        breakdown.add_entry(item)


def analyze_path(path: Path, breakdown: Breakdown) -> None:
    """ Analyze a zip archive, a directory, or a single .json file. """
    if path.is_dir():
        for child in sorted(path.rglob("*.json")):
            analyze_path(child, breakdown)
        return

    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as zf:
            for name in zf.namelist():
                if matches_import_filter(name):
                    breakdown.files_scanned.append(name)
                    with zf.open(name) as f:
                        _analyze_stream(f, breakdown)
                elif name.lower().endswith(".json"):
                    breakdown.files_ignored.append(name)
                    if is_account_data_history(name):
                        breakdown.account_data_files.append(name)
        return

    # single file: analyze it even if the name would not match the zip filter,
    # so users can inspect one file directly, but still surface the warning
    if is_account_data_history(str(path)):
        breakdown.account_data_files.append(str(path))
        breakdown.files_ignored.append(str(path))
        return
    breakdown.files_scanned.append(str(path))
    with open(path, encoding="utf-8") as f:
        _analyze_stream(f, breakdown)


def print_report(breakdown: Breakdown, show_skipped: int) -> None:
    print(f"Files scanned: {len(breakdown.files_scanned)}")
    for name in breakdown.files_scanned:
        print(f"    {name}")
    if breakdown.files_ignored:
        print(f"Files ignored by the importer: {len(breakdown.files_ignored)}")
        for name in breakdown.files_ignored:
            print(f"    {name}")
    if breakdown.account_data_files:
        print()
        print("WARNING: files like " + Path(breakdown.account_data_files[0]).name + " come from the")
        print("simplified 'Account data' export, which ListenBrainz cannot import. Request the")
        print("'Extended streaming history' from https://www.spotify.com/account/privacy/ instead.")

    total = breakdown.total
    print()
    if total == 0:
        print("No streaming history entries found.")
        return

    print(f"Total entries: {total}")
    for category in (IMPORTED, NEEDS_LOOKUP, SHORT_PLAY, INCOGNITO, NO_TRACK_LINK, INVALID):
        count = breakdown.counts.get(category, 0)
        if count == 0:
            continue
        print(f"    {count:>8}  ({count / total:6.1%})  {CATEGORY_LABELS[category]}")

    detail_lines = [f"    {count:>8}  {detail}" for detail, count in breakdown.details.most_common()]
    if detail_lines:
        print()
        print("Skip reasons in detail:")
        print("\n".join(detail_lines))

    if show_skipped:
        for category in (SHORT_PLAY, INCOGNITO, NO_TRACK_LINK, NEEDS_LOOKUP, INVALID):
            examples = breakdown.examples.get(category)
            if not examples:
                continue
            print()
            print(f"Examples - {CATEGORY_LABELS[category]}:")
            for example in examples[:show_skipped]:
                print(f"    {example}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview which entries of a Spotify Extended Streaming History "
                    "ListenBrainz would import, and why the rest would be skipped."
    )
    parser.add_argument("paths", nargs="+", type=Path,
                        help="Spotify export zip, extracted folder, or individual "
                             "Streaming_History_Audio_*.json files")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="output the breakdown as JSON instead of text")
    parser.add_argument("--show-skipped", type=int, default=0, metavar="N",
                        help="also print up to N example entries per skip category")

    args = parser.parse_args()
    breakdown = Breakdown(max_examples=max(args.show_skipped, 5))

    for path in args.paths:
        if not path.exists():
            print(f"error: {path} does not exist", file=sys.stderr)
            return 1
        analyze_path(path, breakdown)

    if args.as_json:
        print(json.dumps({
            "total": breakdown.total,
            "counts": dict(breakdown.counts),
            "skip_details": dict(breakdown.details),
            "files_scanned": breakdown.files_scanned,
            "files_ignored": breakdown.files_ignored,
            "account_data_files": breakdown.account_data_files,
        }, indent=2))
    else:
        print_report(breakdown, args.show_skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
