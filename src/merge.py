"""Merge every connector's raw output (data/raw/*.json) into one deduped
data/events.json.

Dedupe key: (title, start-date, source) is too loose across sources sharing
the same event (e.g. a venue appearing both via its own calendar AND an
Eventbrite listing) -- but cross-source identity for the same real-world
event isn't reliably inferable from title text alone, so this only dedupes
exact repeats *within* a single connector's own output (same title + same
start), which happens when a connector's source itself lists near-duplicates.
Cross-source duplicates are left as-is for v1; the frontend can group by
title+date client-side later if this turns out to matter in practice.

Usage:
    python src/merge.py data/raw/*.json > data/events.json
    python src/merge.py data/raw/*.json data/events.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_events(paths: list[Path]) -> list[dict]:
    events = []
    for p in paths:
        if not p.exists():
            print(f"skip (missing): {p}", file=sys.stderr)
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"skip (bad json): {p} ({e})", file=sys.stderr)
            continue
        events.extend(data)
    return events


def dedupe(events: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for e in events:
        start = e.get("start", {})
        key = (e.get("source"), e.get("title"), start.get("dateTime") or start.get("date"))
        if key in seen:
            continue
        seen.add(key)
        out.append(e)
    return out


def event_sort_key(e: dict) -> str:
    start = e.get("start", {})
    return start.get("dateTime") or start.get("date") or "9999"


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("usage: merge.py data/raw/*.json [out.json]", file=sys.stderr)
        sys.exit(1)

    # last arg is the output path only if it doesn't exist as an input glob
    # match already collected -- simplest: treat any arg ending .json that
    # isn't under data/raw/ as the output path.
    raw_paths = [Path(a) for a in args if "raw" in Path(a).parts]
    out_arg = next((a for a in args if "raw" not in Path(a).parts), None)

    events = load_events(raw_paths)
    events = dedupe(events)
    events.sort(key=event_sort_key)

    print(f"{len(events)} events after dedupe (from {len(raw_paths)} source files)", file=sys.stderr)

    payload = json.dumps(events, indent=2, ensure_ascii=False)
    if out_arg:
        Path(out_arg).parent.mkdir(parents=True, exist_ok=True)
        Path(out_arg).write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
