#!/usr/bin/env python3
"""Apply a targeted change to an existing event in a chapter/series tracker:
edit detail fields and, when the date moves, recompute every phase due-date.
Then report which downstream assets are now stale. Pure-Python docx edit."""
import argparse
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from aaif_meetups import gws_cli, office, tracker  # noqa: E402

STALE_ON_DATE = ["square banner", "Luma cover", "announcement post",
                 "carousel", "day-of slides", "attendee reminder"]
STALE_ON_SPEAKER = ["speaker bio", "announcement post", "carousel", "day-of slides"]


def apply_changes(root, event, set_pairs, date_str):
    """Mutate root in place. set_pairs is a list of 'LABEL=VALUE' strings.
    If date_str is given, recompute all due-dates from the *original* date first,
    then write the authoritative new DATE & TIME string. Returns the stale-asset set."""
    stale = set()
    for pair in set_pairs:
        label, _, value = pair.partition("=")
        tracker.set_field(root, event, label.strip(), value.strip())
        if "SPEAKER" in label.upper():
            stale.update(STALE_ON_SPEAKER)
    if date_str:
        # restamp DUE cells using the original date still in the doc, THEN overwrite
        # DATE & TIME with the user's full string (so weekday/time are exactly as given).
        tracker.set_due_dates(root, event, tracker.parse_event_date(date_str))
        tracker.set_field(root, event, "DATE & TIME", date_str)
        stale.update(STALE_ON_DATE)
    return stale


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("group")
    ap.add_argument("event")
    ap.add_argument("--set", action="append", default=[],
                    metavar="LABEL=VALUE", help='e.g. --set "SPEAKER(S)=Jane Doe"')
    ap.add_argument("--date", help="new DATE & TIME value; triggers due-date recompute")
    a = ap.parse_args()

    loc = tracker.locate_tracker(a.group)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "tracker.docx")
        gws_cli.gws_download(loc["file_id"], path)
        root = office.read_document(path)
        stale = apply_changes(root, a.event, a.set, a.date)
        office.save_document(path, root, path)
        gws_cli.gws_upload(loc["file_id"], path, gws_cli.DOCX)
    print("Updated %r in %s." % (a.event, loc["folder_name"]))
    if stale:
        print("Now stale — re-run these skills: " + ", ".join(sorted(stale)))


if __name__ == "__main__":
    main()
