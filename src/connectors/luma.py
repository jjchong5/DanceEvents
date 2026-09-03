"""Pull events from Luma's public discover feed (api.luma.com/discover/
get-paginated-events, no auth needed -- see ~/code/calendar/src/luma.py's
module docstring for how this was found) and keep only ones matching a
dance-style keyword in the title, tagged with every style they match.

Luma has no keyword-search endpoint (unlike Eventbrite/Meetup), so unlike
this project's other broad-discovery connectors this pulls the general
firehose and filters client-side by config/styles.yaml's `keywords` lists
against the title (the discover feed doesn't return descriptions) plus a
Bay Area home-area location filter, same spirit as the calendar repo's
luma_home_area_keywords approach.

Usage:
    python src/connectors/luma.py data/raw/luma.json [max_events]
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from event_schema import make_event  # noqa: E402

STYLES_PATH = ROOT / "config" / "styles.yaml"
DISCOVER_URL = "https://api.luma.com/discover/get-paginated-events"
EVENT_URL = "https://lu.ma/{slug}"
PAGE_SIZE = 50
DEFAULT_MAX_EVENTS = 400

HOME_AREA_KEYWORDS = [
    "san francisco", "sf", "bay area", "oakland", "berkeley", "mountain view",
    "san jose", "walnut creek", "richmond", "sausalito", "stanford", "antioch",
    "cupertino", "sunnyvale", "palo alto", "redwood city", "san mateo",
    "half moon bay", "daly city",
]


def load_styles() -> dict:
    with open(STYLES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_page(cursor: str | None, timeout: int = 15) -> dict:
    url = f"{DISCOVER_URL}?pagination_limit={PAGE_SIZE}"
    if cursor:
        url += f"&pagination_cursor={cursor}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (danceevents-agent)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def fetch_raw_entries(max_events: int) -> list[dict]:
    entries: list[dict] = []
    cursor = None
    while len(entries) < max_events:
        page = fetch_page(cursor)
        page_entries = page.get("entries", [])
        if not page_entries:
            break
        entries.extend(page_entries)
        if not page.get("has_more"):
            break
        cursor = page.get("next_cursor")
        if not cursor:
            break
    return entries[:max_events]


def _in_home_area(text: str) -> bool:
    text = (text or "").lower()
    return any(kw in text for kw in HOME_AREA_KEYWORDS)


def _matched_styles(title: str, styles_cfg: dict) -> list[str]:
    text = title.lower()
    return [key for key, style in styles_cfg.items() if any(kw in text for kw in style["keywords"])]


def fetch_all_events(styles_cfg: dict, max_events: int = DEFAULT_MAX_EVENTS) -> list[dict]:
    entries = fetch_raw_entries(max_events)

    events = []
    seen = set()
    for entry in entries:
        event = entry.get("event", {})
        if not event:
            continue
        title = event.get("name", "")
        matched = _matched_styles(title, styles_cfg)
        if not matched:
            continue

        geo = event.get("geo_address_info") or {}
        city_state = geo.get("city_state", "")
        if city_state and not _in_home_area(city_state):
            continue

        slug = event.get("url", "")
        url = EVENT_URL.format(slug=slug) if slug else ""
        if not url or url in seen:
            continue
        seen.add(url)

        events.append(
            make_event(
                source="luma",
                source_label="Luma (discover)",
                title=title,
                location=geo.get("full_address") or city_state,
                start={"dateTime": event.get("start_at", "")},
                url=url,
                styles=matched,
                status="cancelled" if event.get("visibility") == "cancelled" else "confirmed",
            )
        )

    return events


def main() -> None:
    args = sys.argv[1:]
    out_path = Path(args[0]) if args else None
    max_events = int(args[1]) if len(args) > 1 else DEFAULT_MAX_EVENTS

    styles_cfg = load_styles()
    events = fetch_all_events(styles_cfg, max_events=max_events)
    print(f"luma: {len(events)} events", file=sys.stderr)

    payload = json.dumps(events, indent=2, ensure_ascii=False)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
