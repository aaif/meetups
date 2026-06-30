#!/usr/bin/env python3
"""Pull the AAIF intake queue (Organizers / Hosts / Speakers) from the
"AAIF Community Intake Ops" sheet and print the rows that need review.

Reads everything by *header name* (never column letter), matching the sheet's
name-based extraction design, so it survives column reordering.

Usage:
    intake.py                 # text digest of rows needing attention
    intake.py --json          # same selection as JSON (for the digest routine)
    intake.py --all           # every row, regardless of status
    intake.py --status New "In progress"   # custom status filter
"""
import argparse, json, subprocess, sys

SHEET_ID = "1cWkjCI5AGK9RX_fs23P5jRA4I2nixgnHuapvwHseZ5o"

# Per-tab: the header names to surface in the digest (resolved by name).
# Name / Email / LinkedIn / City are shown for every tab; these add the
# distinctive, decision-relevant fields per applicant type.
TABS = {
    "Organizers": ["Full name", "Email", "LinkedIn", "City",
                   "Chapter / city wanted", "Technical expertise",
                   "Run events before?", "Why organize / ties"],
    "Hosts":      ["Name", "Email", "LinkedIn", "City", "Company",
                   "Venue name", "Capacity", "Holds 30+?", "A/V available?"],
    "Speakers":   ["Name", "Email", "LinkedIn", "City", "Headline",
                   "Talk title", "Ships in production?", "Past talks / portfolio"],
}

# Rows in these Status states (or blank) are "awaiting review".
DEFAULT_NEEDS_REVIEW = {"", "New", "In progress"}


def fetch(tab):
    """Return (headers, rows) for a tab; rows are padded to len(headers)."""
    params = json.dumps({"spreadsheetId": SHEET_ID,
                         "range": f"{tab}!A1:BB", "majorDimension": "ROWS"})
    out = subprocess.run(["gws", "sheets", "spreadsheets", "values", "get",
                          "--params", params, "--format", "json"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gws error reading {tab}: {out.stderr.strip()}")
    # gws prints a keyring banner line before the JSON; find the JSON start.
    txt = out.stdout
    data = json.loads(txt[txt.index("{"):])
    vals = data.get("values", [])
    if not vals:
        return [], []
    headers = [h.strip() for h in vals[0]]
    rows = [r + [""] * (len(headers) - len(r)) for r in vals[1:]]
    return headers, rows


def col(headers, name):
    return headers.index(name) if name in headers else None


def collect(status_filter, show_all):
    result = {}
    for tab, fields in TABS.items():
        headers, rows = fetch(tab)
        if not headers:
            result[tab] = []
            continue
        si = col(headers, "Status")
        ti = col(headers, "Timestamp")  # real-row marker (always present from the form)
        # A missing marker/status column means a header rename, not an empty
        # queue — fail loudly rather than silently reporting "0 awaiting review".
        if ti is None:
            sys.exit(f"ABORT: tab {tab!r} has no 'Timestamp' column; headers present: {headers}")
        if si is None and not show_all:
            sys.exit(f"ABORT: tab {tab!r} has no 'Status' column to filter on; "
                     f"pass --all or fix the header. Headers present: {headers}")
        picked = []
        for rn, row in enumerate(rows, start=2):  # row 2 = first data row
            if not (row[ti] or "").strip():
                continue  # skip empty trailing rows (no Timestamp)
            status = (row[si].strip() if si is not None else "")
            if not show_all and status not in status_filter:
                continue
            rec = {"row": rn, "status": status or "New"}
            for f in fields:
                ci = col(headers, f)
                rec[f] = (row[ci].strip() if ci is not None else "")
            picked.append(rec)
        result[tab] = picked
    return result


def truncate(s, n=70):
    s = " ".join(s.split())
    return s if len(s) <= n else s[: n - 1] + "…"


def text_digest(data):
    total = sum(len(v) for v in data.values())
    counts = " · ".join(f"{len(v)} {t.lower()}" for t, v in data.items())
    print(f"AAIF intake — {total} awaiting review ({counts})\n")
    for tab, recs in data.items():
        if not recs:
            continue
        print(f"== {tab} ({len(recs)}) ==")
        for r in recs:
            name = r.get("Full name") or r.get("Name") or "(no name)"
            print(f"  • [{r['status']}] {name} — {r.get('Email','')}"
                  f"  {r.get('City','')}  (row {r['row']})")
            for f, v in r.items():
                if f in ("row", "status", "Full name", "Name", "Email", "City"):
                    continue
                if v:
                    print(f"      {f}: {truncate(v)}")
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--status", nargs="*", default=None,
                    help="Status values to include (default: blank/New/In progress)")
    args = ap.parse_args()
    sf = set(args.status) if args.status is not None else DEFAULT_NEEDS_REVIEW
    if args.status is not None:
        sf.add("") if "New" in sf else None
    data = collect(sf, args.all)
    if args.json:
        print(json.dumps(data, indent=1))
    else:
        text_digest(data)


if __name__ == "__main__":
    main()
