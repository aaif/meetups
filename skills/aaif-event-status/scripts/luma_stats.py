#!/usr/bin/env python3
"""Read-only Luma registration stats for tracker events: guest counts by status
(going / pending / waitlist / invited / declined / checked-in), registration
state, and the event URL. Never writes anything, on Luma or locally.

Targets come from a tracker.docx (each event's LUMA URL field, as written back
by aaif-create-event's luma_push) or directly via --url / --event-id.
"""
import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from aaif_meetups import luma, office, tracker  # noqa: E402

COUNT_KEYS = ("approved", "pending_approval", "waitlist", "invited", "declined", "checked_in")


def print_stats(live, label=None):
    counts = live.get("guest_counts") or {}
    going = (counts.get("approved") or {}).get("guests", 0)
    print("== %s ==" % (label or live.get("name", "?")))
    print("  %s  ·  starts %s (%s)" % (live.get("url", "?"),
                                       live.get("start_at", "?"), live.get("timezone", "?")))
    print("  registration: %s  ·  waitlist: %s"
          % ("OPEN" if live.get("registration_open") else "closed",
             live.get("waitlist_status", "?")))
    print("  going: %d   %s" % (going, "   ".join(
        "%s: %d" % (k.replace("_", "-"), (counts.get(k) or {}).get("guests", 0))
        for k in COUNT_KEYS if k != "approved")))


def stats_for_tracker(docx, event_filter):
    root = office.read_document(docx)
    refs = tracker.list_events(root)
    if event_filter:
        refs = [e for e in refs if event_filter.lower() in e["title"].lower()]
    shown = 0
    for ref in refs:
        view = tracker.view_event(ref)
        cell = (view["details"].get("LUMA URL") or "").strip()
        if not cell:
            print("== %s ==\n  (no event page in LUMA URL — not pushed to Luma yet)"
                  % view["title"])
            continue
        # Event pages may use aaif- slugs, so the entity lookup — not the slug —
        # decides whether the cell holds an event page or the calendar link.
        try:
            live = luma.get_event(luma.resolve_event_id(cell))
        except luma.NotAnEventUrl:
            print("== %s ==\n  (LUMA URL doesn't point to an event page — not pushed "
                  "to Luma yet)" % view["title"])
            continue
        except luma.LumaError as e:
            print("== %s ==\n  !! %s" % (view["title"], e))
            continue
        print_stats(live, label=view["title"])
        shown += 1
    if not refs:
        print("No matching events in %s." % docx)
    return shown


def main():
    ap = argparse.ArgumentParser(description="Read-only Luma guest stats for AAIF events")
    ap.add_argument("docx", nargs="?", help="tracker.docx already downloaded via gws")
    ap.add_argument("event", nargs="?", help="optional event title filter; default all")
    ap.add_argument("--url", help="a luma.com event URL to check directly")
    ap.add_argument("--event-id", help="an evt- id to check directly")
    a = ap.parse_args()

    if not luma.available():
        # Not connected: the task digest still works; just no registration numbers.
        print("Luma is not connected (no API key) — skipping registration stats. "
              "Read the numbers off the event page manually, or set up the key "
              "(see aaif-create-event's SKILL.md).")
        return
    if a.event_id:
        print_stats(luma.get_event(a.event_id))
    elif a.url:
        print_stats(luma.get_event(luma.resolve_event_id(a.url)))
    elif a.docx:
        stats_for_tracker(a.docx, a.event)
    else:
        ap.error("pass a tracker.docx, --url, or --event-id")


if __name__ == "__main__":
    main()
