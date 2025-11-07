#!/usr/bin/env python3
"""
Export Safari reading list entries into a JSON file the Rust site can read.

Usage:
    uv run python scripts/export_reading_list.py
        --output static/data/reading_list.json
"""

from __future__ import annotations

import argparse
import json
import plistlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote, urlparse

DEFAULT_INPUT = Path("~/Library/Safari/Bookmarks.plist").expanduser()
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "static" / "data" / "reading_list.json"


def extract_reading_list(bookmarks_path: Path) -> List[Dict[str, Any]]:
    if not bookmarks_path.exists():
        raise FileNotFoundError(f"Safari Bookmarks.plist not found at {bookmarks_path}")

    with bookmarks_path.open("rb") as fh:
        plist_data = plistlib.load(fh)

    reading_list = None
    for child in plist_data.get("Children", []):
        if child.get("Title") == "com.apple.ReadingList":
            reading_list = child.get("Children", [])
            break

    if not reading_list:
        return []

    entries: List[Dict[str, Any]] = []
    for entry in reading_list:
        url = entry.get("URLString")
        if not url:
            continue

        title = normalize_title(entry.get("URIDictionary", {}).get("title"), url)
        date_added = entry.get("DateAdded")
        if isinstance(date_added, datetime):
            date_str = date_added.isoformat()
        else:
            date_str = str(date_added) if date_added is not None else ""

        entries.append(
            {
                "title": title,
                "url": url,
                "date_added": date_str,
            }
        )

    return entries


def normalize_title(raw_title: Optional[str], url: str) -> str:
    """Return a human-friendly title, fixing cases where Safari stores only the URL."""
    if raw_title and not raw_title.startswith("http"):
        return raw_title

    parsed = urlparse(url)
    host = parsed.hostname or ""
    if "substack.com" in host:
        derived = derive_substack_title(parsed)
        if derived:
            return derived

    return raw_title or url


def derive_substack_title(parsed) -> Optional[str]:
    """Best-effort title extraction for Substack URLs."""
    segments = [seg for seg in parsed.path.split("/") if seg]
    slug: Optional[str] = None

    if "p" in segments:
        idx = segments.index("p")
        if idx + 1 < len(segments):
            slug = segments[idx + 1]
    elif segments:
        slug = segments[-1]

    if not slug:
        return None

    readable = unquote(slug.split("?")[0]).replace("-", " ").strip().title()
    if not readable:
        return None

    publication = None
    if parsed.hostname and parsed.hostname.endswith(".substack.com"):
        publication = parsed.hostname.replace(".substack.com", "")
    elif "pub" in segments:
        idx = segments.index("pub")
        if idx + 1 < len(segments):
            publication = segments[idx + 1]

    if publication:
        return f"{publication}: {readable}"
    return readable


def write_json(entries: List[Dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(entries, fh, indent=2, ensure_ascii=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Safari reading list to JSON.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help=f"Path to Safari Bookmarks.plist (default: {DEFAULT_INPUT})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Destination JSON file (default: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    entries = extract_reading_list(args.input)
    write_json(entries, args.output)
    print(f"Exported {len(entries)} entries to {args.output}")


if __name__ == "__main__":
    main()
