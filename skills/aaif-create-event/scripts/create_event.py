#!/usr/bin/env python3
"""Deterministic, local-file event creator: clone the example section in an
Event Tracker.docx, fill details, and stamp all phase due-dates from the event date.
Operates on a docx the agent has ALREADY downloaded via the gws CLI — this script
never touches Drive. Pure-Python docx edit."""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from aaif_meetups import office, tracker  # noqa: E402

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
    ap = argparse.ArgumentParser(description="Add an event to a local Event Tracker.docx")
    ap.add_argument("docx", help="path to a tracker.docx already downloaded via gws")
    ap.add_argument("--title", required=True)
    ap.add_argument("--date", required=True, help='e.g. "Wed · August 12, 2026 · 18:00 — late"')
    for f in ("theme", "venue", "platform", "speakers", "luma", "capacity",
              "organizer", "location"):
        ap.add_argument("--" + f)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    event_date = tracker.parse_event_date(a.date)
    fields = _fields_from_args(a)
    root = office.read_document(a.docx)
    if any(a.title.lower() in e["title"].lower() for e in tracker.list_events(root)):
        sys.exit("ABORT: an event titled %r already exists in %s." % (a.title, a.docx))
    print("Event: %s  date: %s  (fields set: %s)"
          % (a.title, event_date, ", ".join(sorted(fields)) or "title/date only"))
    if a.dry_run:
        print("[dry-run] would clone the example section and stamp dates; no write.")
        return
    apply_local(a.docx, fields, event_date)
    print("Done. New event section added to %s and due-dates stamped." % a.docx)


if __name__ == "__main__":
    main()
