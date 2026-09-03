"""Scrape Eventbrite's public location/category pages, one query per dance
style (config/styles.yaml's search_terms), and emit events in this project's
shared raw event shape (src/event_schema.py).

Adapted from ~/code/calendar/src/eventbrite.py's approach: no API path
exists (Eventbrite shut down public event search in Dec 2019/Feb 2020), so
this scrapes eventbrite.com/d/<location>/<query>/ pages directly via their
embedded ld+json Event blocks -- no HTML parsing needed. See that repo's
CLAUDE.md and this project's ARCHITECTURE.md ("legal posture") for the
scraping risk tradeoff this accepts; kept throttled (small page count per
style, same spirit as the calendar repo).

Usage:
    python src/connectors/eventbrite.py data/raw/eventbrite.json
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from event_schema import make_event  # noqa: E402

STYLES_PATH = ROOT / "config" / "styles.yaml"
LOCATION_SLUG = "ca--san-francisco"
BASE_URL = "https://www.eventbrite.com/d/{location}/{query}/"
PAGE_URL = "https://www.eventbrite.com/d/{location}/{query}/?page={page}"
DEFAULT_MAX_PAGES = 2

LD_JSON_RE = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)


def load_styles() -> dict:
    with open(STYLES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_page(query: str, page: int, timeout: int = 15) -> str:
    slug = query.replace(" ", "-")
    url = (
        BASE_URL.format(location=LOCATION_SLUG, query=slug)
        if page == 1
        else PAGE_URL.format(location=LOCATION_SLUG, query=slug, page=page)
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (danceevents-agent)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_events(page_html: str, style_key: str) -> list[dict]:
    events = []
    for block in LD_JSON_RE.findall(page_html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or "itemListElement" not in data:
            continue
        for item in data["itemListElement"]:
            e = item.get("item", {})
            if e.get("@type") != "Event":
                continue
            address = e.get("location", {}).get("address", {})
            place_name = e.get("location", {}).get("name", "")
            locality = address.get("addressLocality", "")
            location_str = ", ".join(p for p in (place_name, locality) if p)

            events.append(
                make_event(
                    source="eventbrite",
                    source_label="Eventbrite",
                    title=e.get("name", "(no title)"),
                    description=e.get("description", ""),
                    location=location_str,
                    start={"date": e.get("startDate", "")},
                    url=e.get("url", ""),
                    styles=[style_key],
                )
            )
    return events


def fetch_all_events(styles_cfg: dict, max_pages: int = DEFAULT_MAX_PAGES) -> list[dict]:
    events = []
    seen = set()

    for style_key, style in styles_cfg.items():
        for term in style.get("search_terms", []):
            for page in range(1, max_pages + 1):
                html = fetch_page(term, page)
                page_events = parse_events(html, style_key)
                if not page_events:
                    break
                for e in page_events:
                    if e["url"] in seen:
                        continue
                    seen.add(e["url"])
                    events.append(e)

    return events


def main() -> None:
    args = sys.argv[1:]
    max_pages = DEFAULT_MAX_PAGES
    out_path = None
    if args:
        out_path = Path(args[0])
    if len(args) > 1:
        max_pages = int(args[1])

    styles_cfg = load_styles()
    events = fetch_all_events(styles_cfg, max_pages=max_pages)
    print(f"eventbrite: {len(events)} events", file=sys.stderr)

    payload = json.dumps(events, indent=2, ensure_ascii=False)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
