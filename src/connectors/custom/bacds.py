"""Bay Area Country Dance Society (BACDS) monthly contra/English calendar --
a multi-venue aggregator itself (its own schedule table lists real Bay Area
church-hall/community-center venues by code), so this one connector covers
most of the Bay Area's organized contra and English country dance scene.

Page shape (confirmed 2026-09-03 via firecrawl):
  https://bacds.org/dance-scheduler/calendars/<year>/<month>/  -- one month,
  rendered as a "Schedule of Events" table (DATE(S) | STYLE | LOCATION |
  CALLER(S) | MUSICIANS) followed by a "Dance Venues" legend table (VENUE
  code -> NAME/ADDRESS/CITY). Parsed straight from the rendered markdown
  since there's no JSON API; www.bacds.org has flaky DNS, use bacds.org
  (no www) instead -- confirmed during research.

Usage:
    python src/connectors/custom/bacds.py data/raw/custom_bacds.json [months_ahead]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from event_schema import make_event  # noqa: E402

CALENDAR_URL = "https://bacds.org/dance-scheduler/calendars/{year}/{month:02d}"
MONTHS_AHEAD_DEFAULT = 2

STYLE_TO_TAG = {
    "CONTRA": "contra",
    "ENGLISH": "contra",  # config/styles.yaml only has one contra/english style key
    "SQUARE": "contra",
}


def scrape_markdown(url: str) -> str:
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "page.md"
        subprocess.run(
            f'firecrawl scrape "{url}" --wait-for 2000 --only-main-content -o "{out_path}"',
            shell=True,
            check=True,
            capture_output=True,
            timeout=90,
        )
        return out_path.read_text(encoding="utf-8")


def parse_venues(markdown: str) -> dict[str, dict]:
    venues = {}
    in_venue_table = False
    for line in markdown.splitlines():
        if line.strip().startswith("| VENUE"):
            in_venue_table = True
            continue
        if in_venue_table:
            if not line.strip().startswith("|"):
                break
            if line.strip().startswith("| ---"):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 4:
                code, name, address, city = cells[0], cells[1], cells[2], cells[3]
                venues[code] = {"name": name, "address": address, "city": city}
    return venues


DATE_ROW_RE = re.compile(
    r"^\|\s*September|^\|\s*[A-Z][a-z]+ \d{1,2}", re.IGNORECASE
)
ROW_SPLIT_RE = re.compile(r"^\|\s*([A-Za-z]+[ \xa0]\d{1,2})\s*\|\s*(.+?)\s*\|\s*([A-Z]{2,5})\s*\|")


def parse_events(markdown: str, year: int, month: int, venues: dict[str, dict]) -> list[dict]:
    events = []
    in_schedule = False
    for line in markdown.splitlines():
        if line.strip().startswith("| DATE(S)"):
            in_schedule = True
            continue
        if line.strip().startswith("# Dance Venues"):
            break
        if not in_schedule or not line.strip().startswith("|"):
            continue
        if line.strip().startswith("| ---") or line.strip().startswith("| |"):
            continue

        m = ROW_SPLIT_RE.match(line)
        if not m:
            continue
        date_str, style_field, venue_code = m.groups()

        day_match = re.search(r"(\d{1,2})", date_str)
        if not day_match:
            continue
        day = int(day_match.group(1))
        try:
            event_date = date(year, month, day)
        except ValueError:
            continue

        style_upper = style_field.upper()
        tag = next((v for k, v in STYLE_TO_TAG.items() if k in style_upper), None)
        if not tag:
            continue  # skip BOARDMEETING/WOODSHED/etc non-dance rows

        venue = venues.get(venue_code, {})
        location = ", ".join(filter(None, [venue.get("name"), venue.get("address"), venue.get("city")]))

        events.append(
            make_event(
                source="custom:bacds",
                source_label="Bay Area Country Dance Society (BACDS)",
                title=style_field.split("(")[0].strip().title() + " Dance",
                location=location,
                start={"date": event_date.isoformat()},
                url=CALENDAR_URL.format(year=year, month=month),
                styles=[tag],
            )
        )
    return events


def _next_months(n: int) -> list[tuple[int, int]]:
    today = date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.append((y, m))
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def main() -> None:
    args = sys.argv[1:]
    out_path = Path(args[0]) if args else None
    months_ahead = int(args[1]) if len(args) > 1 else MONTHS_AHEAD_DEFAULT

    all_events = []
    for year, month in _next_months(months_ahead):
        url = CALENDAR_URL.format(year=year, month=month)
        try:
            md = scrape_markdown(url)
            venues = parse_venues(md)
            events = parse_events(md, year, month, venues)
            print(f"bacds {year}-{month:02d}: {len(events)} events", file=sys.stderr)
            all_events.extend(events)
        except Exception as e:
            print(f"bacds {year}-{month:02d}: FAILED ({e})", file=sys.stderr)

    payload = json.dumps(all_events, indent=2, ensure_ascii=False)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
