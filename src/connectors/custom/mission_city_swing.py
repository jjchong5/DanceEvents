"""Mission City Swing (South Bay-oriented WCS club, weekly dances +
practice sessions actually held in SF -- Russian Center of SF / Polish
Club) -- a single "Upcoming Class and Event Schedule" page with several
Date | Event | Details markdown tables (confirmed 2026-09-03). No per-event
URL exists on this static page, so every event links back to the schedule
page itself, same pattern as bacds.py/recurring.py for sources with no
per-event permalink.

Usage:
    python src/connectors/custom/mission_city_swing.py data/raw/custom_mission_city_swing.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from event_schema import make_event  # noqa: E402

SCHEDULE_URL = "https://missioncityswing.com/classes/upcoming-class-and-event-schedule/"
SOURCE_LABEL = "Mission City Swing"

ROW_RE = re.compile(r"^\|\s*([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|$")
LOCATION_RE = re.compile(r"Location:\s*([^<\n]+?)(?:<br>|\n|$)")


def scrape_markdown(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "page.md"
        subprocess.run(
            f'firecrawl scrape "{url}" --wait-for 2000 --only-main-content -o "{out_path}"',
            shell=True,
            check=True,
            capture_output=True,
            timeout=60,
        )
        return out_path.read_text(encoding="utf-8")


def _parse_date(date_str: str) -> str | None:
    date_str = date_str.strip().rstrip(",")
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%b. %d, %Y"):
        try:
            return datetime.strptime(date_str, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def parse_events(markdown: str) -> list[dict]:
    events = []
    for line in markdown.splitlines():
        if not line.strip().startswith("|") or line.strip().startswith("| ---") or line.strip().startswith("| Date"):
            continue
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        date_str, title, details = m.groups()
        iso_date = _parse_date(date_str)
        if not iso_date:
            continue

        loc_match = LOCATION_RE.search(details)
        location = loc_match.group(1).strip() if loc_match else ""

        events.append(
            make_event(
                source="custom:mission_city_swing",
                source_label=SOURCE_LABEL,
                title=title.strip(),
                description=details.replace("<br>", " ").replace("**", ""),
                location=location,
                start={"date": iso_date},
                url=SCHEDULE_URL,
                styles=["west_coast_swing"],
            )
        )
    return events


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None

    try:
        md = scrape_markdown(SCHEDULE_URL)
        events = parse_events(md)
        print(f"mission_city_swing: {len(events)} events", file=sys.stderr)
    except Exception as e:
        print(f"mission_city_swing: FAILED ({e})", file=sys.stderr)
        events = []

    payload = json.dumps(events, indent=2, ensure_ascii=False)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
