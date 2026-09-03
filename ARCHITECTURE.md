# Architecture

Bay Area, all-styles social dance event aggregator. Public-facing (unlike the
personal `~/code/calendar` repo this borrows patterns from), so it holds
itself to a stricter sourcing bar: prefer official/public feeds over HTML
scraping wherever one exists, and never scrape a page that itself says access
is by request/invite only.

## Raw event shape

Every connector in `src/connectors/` emits a JSON list of events in this
shape (same spirit as `~/code/calendar`'s shape, trimmed to what this project
needs):

```json
{
  "source": "nextgen_swing_gcal",
  "source_label": "NextGen Swing Dance Club (Bay Area WCS calendar)",
  "title": "...",
  "description": "...",
  "location": "...",
  "start": {"dateTime": "2026-09-05T19:00:00-07:00"} | {"date": "2026-09-05"},
  "end": {...} | null,
  "url": "https://...",
  "styles": ["west_coast_swing"],
  "status": "confirmed" | "cancelled"
}
```

`styles` is a list (never a single pick) drawn from `config/styles.yaml` —
an event can be tagged with more than one style (e.g. a "Salsa/Bachata"
night). Connectors that can't determine style from the source (e.g. a
keyword-search connector already scoped to one query) hardcode it; template
connectors that pull a whole venue's calendar tag from the venue's known
style(s) in `config/venues.yaml`, falling back to a title/description
keyword match against `config/styles.yaml` when a venue covers multiple
styles itself.

## Two source families

**1. Broad discovery (keyword search across general platforms)** —
Eventbrite, Meetup, Luma, Facebook: same approach as `~/code/calendar`'s
connectors, but with search terms widened to ALL partner dance styles, not
just salsa/bachata (`config/styles.yaml` drives the query terms, one file,
not duplicated across sources — see that repo's CLAUDE.md for why keyword
duplication caused bugs before).

**2. Named-source (specific venues/dance groups' own calendars)** — ~25
individual Bay Area dance venues/organizer groups researched 2026-09-03
(`config/venues.yaml`), each pulling from its *own* calendar rather than a
generic search. These cluster onto a handful of shared platforms, so one
template connector serves many venues instead of one bespoke scraper per
site:

| Template | Connector | Venues (config/venues.yaml `platform:`) |
|---|---|---|
| Public Google Calendar iCal feed | `src/connectors/gcal_ical.py` | `platform: gcal_ical` |
| Wix Events calendar page | `src/connectors/wix_events.py` | `platform: wix` |
| WordPress "The Events Calendar" plugin | `src/connectors/wp_events_calendar.py` | `platform: wp_events_calendar` |
| Punchpass class schedule | `src/connectors/punchpass.py` | `platform: punchpass` |
| Custom/one-off (no shared template) | `src/connectors/custom/<slug>.py` | `platform: custom` |

A venue with `platform: gcal_ical`/`wix`/`wp_events_calendar`/`punchpass`
needs only a config entry (URL/calendar-ID) in `venues.yaml` — no new code.
A `custom` venue gets its own small script under `src/connectors/custom/`,
following the same output shape.

**Why iCal feed over scraping where available**: a *public* Google Calendar
iCal feed (`calendar.google.com/calendar/ical/<id>/public/basic.ics`) is a
standard, intended-for-programmatic-consumption export — not a ToS gray
area the way HTML scraping is. Prefer it whenever a venue's calendar is
Google-Calendar-backed and the calendar is confirmed public (verify the
`.ics` URL actually returns events before wiring a venue in — some venues'
calendars are invite-only, e.g. Bay Area Zouk's, confirmed 2026-09-03; those
get `platform: custom` or are dropped, not force-fit into this template).

## Merge + build

```
python src/connectors/*.py -> data/raw/<source>.json   (each connector run standalone)
python src/merge.py data/raw/*.json -> data/events.json  (dedupe, tag styles, one file)
python src/build_site.py data/events.json -> site/events.json  (frontend's data file)
```

`site/` is a static frontend (no backend) that reads `site/events.json` at
load time and does all search/filter client-side. Deployed as a static host
(see README for current deploy target). No live database; a fresh
`events.json` is only as current as the last scrape run.

## Legal posture (different from ~/code/calendar — read before adding sources)

This project is public-facing, which is a materially different risk profile
than personal-use scraping:
- Prefer official feeds (iCal, RSS) over HTML scraping whenever one exists.
- Never add a source whose access is explicitly gated/by-request (confirmed
  invite-only sources are excluded, not scraped around).
- Attribute every event's original source + link back to it (both a courtesy
  and a way to keep this a discovery layer, not a redistribution product).
- Keep scrape volume/frequency low (see `docs/scheduling.md` once written) —
  this mirrors `~/code/calendar`'s existing throttling conventions.
- If any source operator asks to be removed, remove them immediately, no
  argument.
