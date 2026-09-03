"""Shared raw-event JSON shape all connectors emit. See ARCHITECTURE.md."""
from __future__ import annotations


def make_event(
    *,
    source: str,
    source_label: str,
    title: str,
    start: dict,
    url: str,
    description: str = "",
    location: str = "",
    end: dict | None = None,
    styles: list[str] | None = None,
    status: str = "confirmed",
) -> dict:
    return {
        "source": source,
        "source_label": source_label,
        "title": title,
        "description": description,
        "location": location,
        "start": start,
        "end": end,
        "url": url,
        "styles": styles or [],
        "status": status,
    }
