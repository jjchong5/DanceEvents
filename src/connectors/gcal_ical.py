"""Pull events from public Google Calendar iCal feeds for every venue in
config/venues.yaml with platform: gcal_ical.

A *public* Google Calendar's iCal export (calendar.google.com/calendar/ical/
<id>/public/basic.ics) is a standard, intended-for-programmatic-consumption
feed -- not an HTML-scraping gray area. Only venues confirmed public (see
venues.yaml's confirmed_active) are wired in here; an invite-only calendar
(e.g. Bay Area Zouk, confirmed 2026-09-03) is excluded from venues.yaml
entirely rather than worked around.

Usage:
    python src/connectors/gcal_ical.py data/raw/gcal_ical.json
"""
from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml
from icalendar import Calendar

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from event_schema import make_event  # noqa: E402

VENUES_PATH = ROOT / "config" / "venues.yaml"
ICAL_URL = "https://calendar.google.com/calendar/ical/{cal_id}/public/basic.ics"
LOOKAHEAD_DAYS = 60  # skip events further out than this and everything in the past


def load_venues() -> list[dict]:
    with open(VENUES_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return [v for v in cfg["venues"] if v.get("platform") == "gcal_ical"]


def _to_start_dict(dt) -> dict:
    if isinstance(dt, datetime):
        return {"dateTime": dt.isoformat()}
    return {"date": dt.isoformat()}


def fetch_venue_events(venue: dict) -> list[dict]:
    cal_id = venue["gcal_id"]
    url = ICAL_URL.format(cal_id=urllib.parse.quote(cal_id, safe="@"))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read()

    cal = Calendar.from_ical(raw)
    today = date.today()
    cutoff = today + timedelta(days=LOOKAHEAD_DAYS)

    events = []
    for component in cal.walk("VEVENT"):
        dtstart = component.get("dtstart")
        if dtstart is None:
            continue
        start_val = dtstart.dt
        start_date = start_val.date() if isinstance(start_val, datetime) else start_val
        if start_date < today or start_date > cutoff:
            continue

        dtend = component.get("dtend")
        end_dict = None
        if dtend is not None:
            end_dict = _to_start_dict(dtend.dt)

        status = str(component.get("status", "CONFIRMED")).lower()
        events.append(
            make_event(
                source=f"gcal_ical:{venue['slug']}",
                source_label=venue["name"],
                title=str(component.get("summary", "")),
                description=str(component.get("description", "")),
                location=str(component.get("location", "")),
                start=_to_start_dict(start_val),
                end=end_dict,
                url=str(component.get("url") or venue.get("homepage", "")),
                styles=venue.get("styles", []),
                status="cancelled" if status == "cancelled" else "confirmed",
            )
        )
    return events


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    venues = load_venues()

    all_events = []
    for venue in venues:
        try:
            events = fetch_venue_events(venue)
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
