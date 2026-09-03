# Bay Area Dance Events

A public, all-styles Bay Area social dance event search site: salsa,
bachata, swing/lindy hop, west coast swing, Argentine tango, ballroom,
contra, kizomba, zouk, blues, and line dance/country western — aggregated
from Eventbrite, Meetup, Luma, and ~10 individual dance venues/organizer
groups' own calendars.

See `ARCHITECTURE.md` for the connector design (two source families: broad
keyword-search platforms + named-source venue calendars grouped by shared
platform template) and its "legal posture" section for the sourcing rules
this project holds itself to — stricter than a personal-use scraper, since
this is public-facing.

## Why this exists

Built 2026-09-03 after finding that existing Bay Area dance aggregators
(salsavida.com, danceus.org) either only cover salsa/bachata or have thin
non-Latin coverage in this region specifically — see the scoping
conversation for the research behind that call. The wedge is genuine
all-styles coverage, not "do everything better."

## Running it

```
pip install -r requirements.txt
python src/run_all.py          # runs every connector, merges, rebuilds site/events.json
```

Or run pieces individually:

```
python src/connectors/gcal_ical.py data/raw/gcal_ical.json
python src/connectors/wix_events.py data/raw/wix_events.json
python src/connectors/wp_events_calendar.py data/raw/wp_events_calendar.json
python src/connectors/eventbrite.py data/raw/eventbrite.json
python src/connectors/meetup.py data/raw/meetup.json
python src/connectors/luma.py data/raw/luma.json

python src/merge.py data/raw/*.json data/events.json
python src/build_site.py data/events.json site/events.json
```

`site/` is the deployed static frontend — plain HTML/JS, no build step, no
backend, reads `site/events.json` at page load and does all search/filter
client-side.

**View locally**: `python -m http.server 8000` from inside `site/`, then
open `http://localhost:8000` (fetching `events.json` from a `file://` URL is
blocked by the browser, so it must be served, not opened directly).

## Adding a new venue

If it's Google-Calendar-backed (public, no invite needed), Wix Events, or
WordPress "The Events Calendar" plugin, add an entry to `config/venues.yaml`
with the right `platform:` — no new code needed, the matching template
connector picks it up automatically. Otherwise it needs a small script under
`src/connectors/custom/`, same output shape as `src/event_schema.py`.

## Current source status (as of 2026-09-03 build)

| Source | Status |
|---|---|
| NextGen Swing WCS calendar (gcal_ical) | Working — 500+ event feed, single richest source |
| SF Tango With.Us (wp_events_calendar) | Working — itself aggregates many Bay Area tango venues |
| Bayshore Blues (wix) | Working |
| Tip Top Ballroom | Needs custom connector — not a calendar-grid Wix page, static schedule table instead |
| Golden City Dance Collective (Punchpass) | Deferred — schedule widget too irregular to parse reliably in v1 |
| Eventbrite / Meetup (keyword search, all 11 styles) | Working |
| Luma (discover feed, keyword-filtered) | Working but low yield — Luma skews tech events, not dance |
| ~15 other researched venues (Cat's Corner, BAWDC, BACDS, etc.) | Not yet wired in — see `config/venues.yaml`'s bottom comment for the list |

Not yet deployed to a live URL — see TODO for next step.

## Deploying

Not yet decided/wired up. `site/` is a plain static folder (HTML + one JSON
file) — deployable to any static host (GitHub Pages, Netlify, Vercel, etc.)
with zero build step.
