"""Run every connector, merge, and rebuild the site's data file. The single
command a scheduled job (or a manual re-run) should call.

Usage:
    python src/run_all.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYTHON = sys.executable

CONNECTORS = [
    "src/connectors/gcal_ical.py",
    "src/connectors/wix_events.py",
    "src/connectors/wp_events_calendar.py",
    "src/connectors/eventbrite.py",
    "src/connectors/meetup.py",
    "src/connectors/luma.py",
]


def run(cmd: list[str]) -> None:
    print(f"$ {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=False, cwd=ROOT)


def main() -> None:
    for connector in CONNECTORS:
        out_name = Path(connector).stem + ".json"
        run([PYTHON, connector, f"data/raw/{out_name}"])

    run([PYTHON, "src/merge.py", *[f"data/raw/{Path(c).stem}.json" for c in CONNECTORS], "data/events.json"])
    run([PYTHON, "src/build_site.py", "data/events.json", "site/events.json"])


if __name__ == "__main__":
    main()
