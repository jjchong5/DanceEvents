# TODO

Open items, in rough priority order. See `config/venues.yaml`'s bottom
comment block for the full per-venue investigation notes this summarizes.

## High value, worth real effort

- **TangoMango (tangomango.org)** — the single richest untapped source
  found across both research passes: dozens of real Argentine tango events
  per week across the whole NorCal region (SF, East Bay, Peninsula, South
  Bay, Marin, Sacramento, Santa Cruz, Monterey, Sonoma). Blocked because its
  calendar-grid page exposes zero per-event URLs (confirmed via
  `firecrawl scrape --format links`) — every event's detail appears to be a
  JS tooltip/popup, not a real link. This project's shared schema requires
  a `url` per event. Next step: inspect the page's network requests (or try
  `firecrawl interact` to click an event and see what loads) for an AJAX
  endpoint the tooltip pulls from — if one exists with a stable per-event
  ID, that's the real fix, not another markdown-scrape attempt.

## Investigated, deliberately deferred/blocked (don't re-attempt the same way)

- **BAWDC (bawdc.org/schedule)** — reCAPTCHA-gated even through a
  rendering fetch. Would need a different approach entirely (official API
  if one exists, or manual periodic entry) — not a scraping fix.
- **Tip Top Ballroom** — has a real dated schedule, but it's mostly private
  kids/adult lesson bookings, not open social dances, with verbose
  per-entry markup. Lower value than time cost; skip unless the site
  changes to foreground its social-dance events more clearly.
- **Golden City Dance Collective / Punchpass** — the schedule widget's
  rendered markdown is a single day at a time, dense and irregular
  (course cards + instructor avatars interleaved). Would need either a
  different Punchpass endpoint (check for a public JSON API before trying
  HTML again) or per-day fetches multiplied out — meaningfully more work
  than the venue justifies given its output is recurring classes, not
  drop-in socials.

## Not yet attempted this round (ran out of time, not individually diagnosed)

Try these fresh — some may just work with the same `firecrawl scrape
--wait-for 2000 --only-main-content` pattern used for everything else:

- District Zouk, OmniZouk (theomnimovement.org/omnizouk)
- DJ Shivers Bay Area Country Nights (djshiversofficial.com)
- Coastside Country (coastsidecountry.org)
- Arthur Murray Los Gatos — if it works, check whether other Bay Area
  Arthur Murray franchise locations share the same site template (would
  turn one connector into coverage for several locations)
- Bay Area Ballroom & Latin Social
- Bay Area Fusion Calendar
- La Bruja Tango at Berkeley City Club — **check for overlap first**: SF
  Tango With.Us's feed already includes "at La Bruja" events, so this may
  already be covered indirectly. Confirm before spending time on it.
- CCSF Argentine Tango — a community-college course catalog, not an event
  calendar; different shape entirely (semester enrollment, not dated
  events). Lowest priority, may not fit this project's model at all.

## Infrastructure / not source-related

- No automated re-run schedule yet — `src/run_all.py` is manual. If this
  needs to stay fresh without a person re-running it, look at how
  `~/code/calendar`'s mac-mini launchd scheduling works
  (`docs/scheduler_setup_mac_mini.md` there) as a precedent — this repo
  doesn't have its own mac-mini setup yet.
- `data/events.json`/`data/raw/*.json` are gitignored (regenerable), but
  `site/events.json` is committed since it's what the deployed static site
  actually serves — remember to commit it after every `run_all.py`, or the
  live site silently goes stale even though the data pipeline "ran fine."
- No dedupe across sources yet (only within a single connector's own
  output) — see `src/merge.py`'s docstring. If the same real-world event
  starts appearing from two sources (e.g. a venue's own calendar AND an
  Eventbrite listing for the same night), it'll show twice. Not yet
  observed as an actual problem in the live data, but worth watching.
