"""Generate upcoming instances for venues whose "calendar" is really just a
fixed weekly recurrence with no dated listing at all -- confirmed against
the venue's own site, not guessed (see RECURRING_VENUES' `verified` note per
entry). Covers venues where writing a real scraper would be pointless: there
is no per-date page to scrape, just an "every Wednesday" statement on the
homepage.

Usage:
    python src/connectors/custom/recurring.py data/raw/custom_recurring.json [weeks_ahead]
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from event_schema import make_event  # noqa: E402

WEEKS_AHEAD_DEFAULT = 6

# weekday: 0=Monday .. 6=Sunday
RECURRING_VENUES = [
    {
        "slug": "cats_corner",
        "name": "Cat's Corner (SF Lindy Hop)",
        "title": "Cat's Corner Wednesday Swing Dance Party",
        "weekday": 2,  # Wednesday
        "time": "20:00",
        "location": "435 Broadway, San Francisco",
        "url": "https://www.catscornersf.com/dance-party/",
        "styles": ["swing_lindy"],
        "verified": "2026-09-03: homepage explicitly states 'Swing Dance Classes and Live Music Dance Party on Wednesdays', no dated calendar exists on site.",
    },
    {
        "slug": "sundance_saloon_sun",
        "name": "Sundance Saloon",
        "title": "Sundance Saloon — Sunday Country/Line Dancing",
        "weekday": 6,  # Sunday
        "time": "17:00",
        "location": "550 Barneveld Ave, San Francisco",
        "url": "https://www.sundancesaloon.org",
        "styles": ["line_dance_country"],
        "verified": "2026-09-03: homepage states 'SUNDAYS: 5:00-10:30 pm', LGBTQ+ country-western dance, no dated calendar.",
    },
    {
        "slug": "sundance_saloon_thu",
        "name": "Sundance Saloon",
        "title": "Sundance Saloon — Thursday Country/Line Dancing",
        "weekday": 3,  # Thursday
        "time": "18:30",
        "location": "550 Barneveld Ave, San Francisco",
        "url": "https://www.sundancesaloon.org",
        "styles": ["line_dance_country"],
        "verified": "2026-09-03: homepage states 'THURSDAYS: 6:30-10:30 pm'.",
    },
]


def _next_weekday_on_or_after(start: date, weekday: int) -> date:
    delta = (weekday - start.weekday()) % 7
    return start + timedelta(days=delta)


def generate_events(weeks_ahead: int) -> list[dict]:
    today = date.today()
    events = []
    for venue in RECURRING_VENUES:
        first = _next_weekday_on_or_after(today, venue["weekday"])
        for week in range(weeks_ahead):
            event_date = first + timedelta(weeks=week)
            hour, minute = map(int, venue["time"].split(":"))
            dt = datetime.combine(event_date, datetime.min.time()).replace(hour=hour, minute=minute)
            events.append(
                make_event(
                    source=f"custom:recurring:{venue['slug']}",
                    source_label=venue["name"],
                    title=venue["title"],
                    location=venue["location"],
                    start={"dateTime": dt.isoformat()},
                    url=venue["url"],
                    styles=venue["styles"],
                )
            )
    return events


def main() -> None:
    args = sys.argv[1:]
    out_path = Path(args[0]) if args else None
    weeks_ahead = int(args[1]) if len(args) > 1 else WEEKS_AHEAD_DEFAULT

    events = generate_events(weeks_ahead)
    print(f"recurring: {len(events)} events generated ({len(RECURRING_VENUES)} venues x {weeks_ahead} weeks)", file=sys.stderr)

    payload = json.dumps(events, indent=2, ensure_ascii=False)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
