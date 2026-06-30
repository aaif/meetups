#!/usr/bin/env python3
"""Create a new event section in a chapter/series Event Tracker.docx: clone the
example section, fill details, and stamp all phase due-dates from the event date.
Stdlib-only, pure-Python docx edit; Drive I/O via the gws CLI."""
import argparse
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from aaif_meetups import gws_cli, office, tracker  # noqa: E402

# CLI flag -> detail label
FIELD_MAP = {"title": "EVENT TITLE", "date": "DATE & TIME", "theme": "THEME / SERIES",
             "venue": "VENUE", "platform": "VENUE", "speakers": "SPEAKER(S)",
             "luma": "LUMA URL", "capacity": "CAPACITY / RSVPS",
             "organizer": "ORGANIZER ON POINT", "location": "LOCATION / CITY"}


def apply_local(path, fields, event_date):
    root = office.read_document(path)
    tracker.add_event(root, fields, event_date)
    office.save_document(path, root, path)


def _fields_from_args(a):
    fields = {}
    for flag, label in FIELD_MAP.items():
        val = getattr(a, flag, None)
        if val:
            fields[label] = val
    return fields


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("group", help="chapter or series name")
    ap.add_argument("--title", required=True)
    ap.add_argument("--date", required=True, help='e.g. "Wed · August 12, 2026 · 18:00 — late"')
    for f in ("theme", "venue", "platform", "speakers", "luma", "capacity",
              "organizer", "location"):
        ap.add_argument("--" + f)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    event_date = tracker.parse_event_date(a.date)
    fields = _fields_from_args(a)
    loc = tracker.locate_tracker(a.group)
    print("Tracker: %s (%s)  event: %s  date: %s"
          % (loc["folder_name"], loc["kind"], a.title, event_date))
    if a.dry_run:
        print("[dry-run] would clone the example section and stamp dates; no write.")
        return
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "tracker.docx")
        gws_cli.gws_download(loc["file_id"], path)
        root = office.read_document(path)
        if any(a.title.lower() in e["title"].lower() for e in tracker.list_events(root)):
            sys.exit("ABORT: an event titled %r already exists in this tracker." % a.title)
        tracker.add_event(root, fields, event_date)
        office.save_document(path, root, path)
        gws_cli.gws_upload(loc["file_id"], path, gws_cli.DOCX)
    print("Done. New event section added and due-dates stamped.")


if __name__ == "__main__":
    main()
