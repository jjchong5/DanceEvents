"""Copy data/events.json into site/events.json (the frontend's data file) and
stamp a generated_at timestamp so the page can show data freshness.

Usage:
    python src/build_site.py data/events.json site/events.json
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: build_site.py data/events.json site/events.json", file=sys.stderr)
        sys.exit(1)

    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    events = json.loads(src.read_text(encoding="utf-8"))

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(events),
        "events": events,
    }

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(events)} events to {dst}", file=sys.stderr)


if __name__ == "__main__":
    main()
