"""Pull events from Wix-hosted calendar pages for every venue in
config/venues.yaml with platform: wix.

Wix's calendar widget is client-rendered, so this needs a rendering fetch
(firecrawl) rather than a plain requests.get -- see docs/scraping_notes.md.
The rendered markdown lists each day's events as "<time>\n<title> (<city>)"
lines directly under the calendar grid; parsed with a line-pair heuristic
rather than a full HTML parser since Wix's DOM structure for this widget
isn't documented/stable.

Usage:
    python src/connectors/wix_events.py data/raw/wix_events.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from event_schema import make_event  # noqa: E402

VENUES_PATH = ROOT / "config" / "venues.yaml"

TIME_LINE_RE = re.compile(r"^\d{1,2}:\d{2}\s*[AP]M$", re.IGNORECASE)
DATE_HEADER_RE = re.compile(r"^([A-Z][a-z]+)\s*(\d{4})$")  # e.g. "September 2026"
DAY_NUM_RE = re.compile(r"^\d{1,2}$")


def load_venues() -> list[dict]:
    with open(VENUES_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return [v for v in cfg["venues"] if v.get("platform") == "wix"]


def scrape_markdown(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "page.md"
        subprocess.run(
            f'firecrawl scrape "{url}" --only-main-content -o "{out_path}"',
            shell=True,
            check=True,
            capture_output=True,
            timeout=60,
        )
        return out_path.read_text(encoding="utf-8")


def _build_start(year: int, month: int, day: int, time_str: str) -> dict:
    try:
        t = datetime.strptime(time_str.upper().replace(" ", ""), "%I:%M%p")
        dt = datetime(year, month, day, t.hour, t.minute)
        return {"dateTime": dt.isoformat()}
    except ValueError:
        return {"date": f"{year:04d}-{month:02d}-{day:02d}"}


def parse_wix_calendar(markdown: str, venue: dict) -> list[dict]:
    """Walk the day-grid + time/title lines the Wix calendar widget renders
    to markdown. Month/year context comes from the "September 2026"-style
    header that precedes each grid; a running day-of-month counter attaches
    each subsequent time/title pair to the most recent bare day number seen
    (the grid emits day numbers as their own lines, in calendar order)."""
    lines = [l.strip() for l in markdown.splitlines() if l.strip()]

    events = []
    current_month_year: tuple[int, int] | None = None
    current_day: int | None = None
    i = 0
    while i < len(lines):
        line = lines[i]

        m = DATE_HEADER_RE.match(line)
        if m:
            month_name, year = m.group(1), int(m.group(2))
            try:
                month_num = [
                    "january", "february", "march", "april", "may", "june",
                    "july", "august", "september", "october", "november", "december",
                ].index(month_name.lower()) + 1
                current_month_year = (year, month_num)
            except ValueError:
                pass
            i += 1
            continue

        if DAY_NUM_RE.match(line) and current_month_year:
            current_day = int(line)
            i += 1
            continue

        if TIME_LINE_RE.match(line) and current_month_year and current_day and i + 1 < len(lines):
            time_str = line
            title_line = lines[i + 1].replace("\\[", "[").replace("\\]", "]")
            year, month = current_month_year
            start = _build_start(year, month, current_day, time_str)
            events.append(
                make_event(
                    source=f"wix:{venue['slug']}",
                    source_label=venue["name"],
                    title=title_line,
                    start=start,
                    url=venue.get("calendar_url", venue.get("homepage", "")),
                    styles=venue.get("styles", []),
                )
            )
            i += 2
            continue

        i += 1

    return events


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    venues = load_venues()

    all_events = []
    for venue in venues:
        try:
            md = scrape_markdown(venue["calendar_url"])
            events = parse_wix_calendar(md, venue)
            print(f"{venue['slug']}: {len(events)} events", file=sys.stderr)
            all_events.extend(events)
        except Exception as e:
            print(f"{venue['slug']}: FAILED ({e})", file=sys.stderr)

    payload = json.dumps(all_events, indent=2, ensure_ascii=False)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
