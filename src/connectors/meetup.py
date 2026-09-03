"""Scrape Meetup's public event search page, one query per dance style
(config/styles.yaml's search_terms), same ld+json extraction pattern as
~/code/calendar/src/meetup.py. See that repo's CLAUDE.md and this project's
ARCHITECTURE.md for the scraping risk tradeoff this accepts.

Usage:
    python src/connectors/meetup.py data/raw/meetup.json
"""
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from event_schema import make_event  # noqa: E402

STYLES_PATH = ROOT / "config" / "styles.yaml"
LOCATION = "us--ca--San Francisco"
FIND_URL = "https://www.meetup.com/find/?keywords={query}&location={location}"

LD_JSON_RE = re.compile(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', re.DOTALL)


def load_styles() -> dict:
    with open(STYLES_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_search(query: str, timeout: int = 15) -> str:
    url = FIND_URL.format(query=urllib.parse.quote(query), location=urllib.parse.quote(LOCATION))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (danceevents-agent)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _first_name(value) -> str:
    if isinstance(value, list):
        value = value[0] if value else {}
    if isinstance(value, dict):
        return value.get("name", "")
    return ""


def parse_events(page_html: str, style_key: str) -> list[dict]:
    events = []
    for block in LD_JSON_RE.findall(page_html):
        try:
            data = json.loads(block)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for e in items:
            if not isinstance(e, dict) or e.get("@type") != "Event":
                continue
            location_str = _first_name(e.get("location"))
            events.append(
                make_event(
                    source="meetup",
                    source_label="Meetup",
                    title=e.get("name", "(no title)"),
                    description=e.get("description", ""),
                    location=location_str,
                    start={"dateTime": e.get("startDate")} if e.get("startDate") else {"date": ""},
                    url=e.get("url", ""),
                    styles=[style_key],
                )
            )
    return events


def fetch_all_events(styles_cfg: dict) -> list[dict]:
    events = []
    seen = set()
    for style_key, style in styles_cfg.items():
        for term in style.get("search_terms", []):
            html = fetch_search(term)
            for e in parse_events(html, style_key):
                if e["url"] in seen:
                    continue
                seen.add(e["url"])
                events.append(e)
    return events


def main() -> None:
    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    styles_cfg = load_styles()
    events = fetch_all_events(styles_cfg)
    print(f"meetup: {len(events)} events", file=sys.stderr)

    payload = json.dumps(events, indent=2, ensure_ascii=False)
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    main()
