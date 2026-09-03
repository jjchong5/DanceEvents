"""Pull events from the WordPress "The Events Calendar" plugin's REST API
for every venue in config/venues.yaml with platform: wp_events_calendar.

The plugin exposes a standard JSON REST endpoint at
<site>/wp-json/tribe/events/v1/events -- much more reliable than HTML
scraping, and any WordPress site using this plugin exposes the same shape,
so this one connector covers every venue on the platform. Several of these
sites sit behind Cloudflare's bot challenge for plain HTTP clients, so this
fetches via `firecrawl scrape` (which renders past the challenge) rather
than urllib -- same reason the wix_events.py connector needs it.

Usage:
    python src/connectors/wp_events_calendar.py data/raw/wp_events_calendar.json
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
from event_schema import make_event  # noqa: E402

VENUES_PATH = ROOT / "config" / "venues.yaml"
API_PATH = "/wp-json/tribe/events/v1/events?per_page=50"
JSON_FENCE_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


def load_venues() -> list[dict]:
    with open(VENUES_PATH, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return [v for v in cfg["venues"] if v.get("platform") == "wp_events_calendar"]


def fetch_json_via_firecrawl(url: str) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "page.md"
        subprocess.run(
            f'firecrawl scrape "{url}" --only-main-content -o "{out_path}"',
            shell=True,
            check=True,
            capture_output=True,
            timeout=60,
        )
        raw = out_path.read_text(encoding="utf-8")

    m = JSON_FENCE_RE.search(raw)
    text = m.group(1) if m else raw
    return json.loads(text)


def _to_start_dict(date_str: str) -> dict:
    # tribe events dates look like "2026-09-02 19:00:00"
    date_part, _, time_part = date_str.partition(" ")
    if time_part and time_part != "00:00:00":
        return {"dateTime": f"{date_part}T{time_part}"}
    return {"date": date_part}


def fetch_venue_events(venue: dict) -> list[dict]:
    base = venue.get("calendar_url", venue.get("homepage", "")).rstrip("/")
    # calendar_url may point at /events/ -- strip any path, use bare origin
    m = re.match(r"(https?://[^/]+)", base)
    origin = m.group(1) if m else base
    data = fetch_json_via_firecrawl(origin + API_PATH)

    events = []
    for ev in data.get("events", []):
        venue_info = ev.get("venue") or {}
        location = ", ".join(
            filter(None, [venue_info.get("venue"), venue_info.get("address"), venue_info.get("city")])
        )
        events.append(
            make_event(
                source=f"wp_events_calendar:{venue['slug']}",
                source_label=venue["name"],
                title=ev.get("title", ""),
                description=re.sub(r"<[^>]+>", "", ev.get("description", "") or ""),
                location=location,
                start=_to_start_dict(ev["start_date"]),
                end=_to_start_dict(ev["end_date"]) if ev.get("end_date") else None,
                url=ev.get("url", venue.get("homepage", "")),
                styles=venue.get("styles", []),
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
