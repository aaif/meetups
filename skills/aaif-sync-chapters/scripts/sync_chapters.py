#!/usr/bin/env python3
"""Sync organizer decisions from the AAIF Community Intake Ops sheet into the
AAIF Community Chapters List.

Every intake organizer whose Status is "Accepted" or "Existing (from MLOps)"
must appear in the Organizers column of their city's row on the chapters list;
cities with no row yet get one appended. The intake sheet is only ever READ.

Usage:
  python3 sync_chapters.py            # report + proposed changes, writes nothing
  python3 sync_chapters.py --write    # apply the proposal via one batchUpdate

The report shows: per-city name adds (existing rows), new rows with their
appended row numbers and Luma slugs, unresolved-city rows needing a human,
near-miss city names (never auto-matched), and a "no changes" line when the
sheets are already in sync. --write recomputes the proposal from a fresh read,
applies it atomically, then re-reads and verifies the diff is empty.
"""
import argparse, json, re, subprocess, sys, time, unicodedata, urllib.error, urllib.request

INTAKE_ID = "1cWkjCI5AGK9RX_fs23P5jRA4I2nixgnHuapvwHseZ5o"
INTAKE_TAB = "Organizers"
CHAPTERS_ID = "18_7aHD45-5NhlN6IZKW2QzswZlDHVb8nBSP7rl5-yWg"
CHAPTERS_TAB = "Chapters & Teams"

# Exact dropdown strings — "Existing" alone would miss every MLOps row.
SYNC_STATUSES = ("Accepted", "Existing (from MLOps)")

# Folded city -> Luma slug, for cities whose page doesn't follow the default
# slug rule (same exceptions as aaif-create-chapter).
SLUG_OVERRIDES = {"denver": "colorado"}

# ----------------------------------------------------------------------------
# gws helpers (same retry/JSON pattern as aaif-create-chapter)
# ----------------------------------------------------------------------------
_TRANSIENT = ("timed out", "internalError", "HTTP request failed",
              "Connection", "temporarily", "rateLimit", "userRateLimit",
              "backendError", "503", "500", "502")

def _gws(cmd, retries=5):
    for i in range(max(1, retries)):   # retries<=0 must raise below, not return None
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode == 0:
            return r.stdout
        msg = (r.stderr or "") + (r.stdout or "")
        if i < max(1, retries) - 1 and any(k in msg for k in _TRANSIENT):
            time.sleep(2 * (i + 1))
            continue
        raise RuntimeError("gws failed (%s): %s" % (r.returncode, msg.strip()[:400]))

def gws_json(*args, params=None, body=None):
    cmd = ["gws", *args]
    if params is not None:
        cmd += ["--params", json.dumps(params)]
    if body is not None:
        cmd += ["--json", json.dumps(body)]
    out = _gws(cmd)
    # Split on "\n" only — NOT splitlines(), which also splits on U+2028 and
    # friends INSIDE cell values, corrupting the JSON when rejoined.
    s = "\n".join(l for l in out.split("\n") if "keyring backend" not in l).strip()
    if not s:
        raise RuntimeError("gws produced no JSON output for: %s" % " ".join(args))
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        raise RuntimeError("gws returned non-JSON output for %s: %s" % (" ".join(args), s[:200]))

def get_values(sheet_id, rng):
    res = gws_json("sheets", "spreadsheets", "values", "batchGet",
                   params={"spreadsheetId": sheet_id, "ranges": [rng]})
    return res["valueRanges"][0].get("values", [])

# ----------------------------------------------------------------------------
# Text helpers
# ----------------------------------------------------------------------------
def fold(s):
    """Comparison key: accent-folded, casefolded, whitespace-collapsed.
    Only ever used to COMPARE — written values keep their original UTF-8."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().casefold()

def slugify(city):
    s = unicodedata.normalize("NFKD", city).encode("ascii", "ignore").decode()
    return SLUG_OVERRIDES.get(fold(city), re.sub(r"[^a-z0-9]", "", s.lower()))

def cell(row, i):
    return row[i].strip() if i < len(row) and isinstance(row[i], str) else ""

def header_index(headers, sheet, *names):
    idx = []
    for n in names:
        if n not in headers:
            sys.exit("ABORT: column %r not found on %s — sheet layout changed?" % (n, sheet))
        idx.append(headers.index(n))
    return idx

def luma_status(slug):
    """'live' (200) / 'absent' (404) / 'unknown' (couldn't verify)."""
    req = urllib.request.Request("https://luma.com/aaif-" + slug, method="GET",
                                 headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return "live" if r.status == 200 else "unknown"
    except urllib.error.HTTPError as e:
        return "absent" if e.code == 404 else "unknown"
    except (urllib.error.URLError, TimeoutError):
        return "unknown"

# ----------------------------------------------------------------------------
# Read the two sheets
# ----------------------------------------------------------------------------
def read_intake():
    """Return (entries, unresolved, status_counts, dupes).

    entries    = [{row, name, city, status}]           city resolved, deduped
    unresolved = [{row, name, status, g, h, events, why}]  needs a human
    """
    rows = get_values(INTAKE_ID, "%s!A:U" % INTAKE_TAB)
    if not rows:
        sys.exit("ABORT: intake tab %r came back empty." % INTAKE_TAB)
    i_status, i_name, i_g, i_h, i_events, i_why = header_index(
        rows[0], INTAKE_TAB, "Status", "Full name", "City (Existing)", "City (New)",
        "Run events before?", "Why organize / ties")

    entries, unresolved, dupes = [], [], []
    counts = {s: 0 for s in SYNC_STATUSES}
    seen = set()
    for rownum, row in enumerate(rows[1:], start=2):
        status = cell(row, i_status)
        if status not in SYNC_STATUSES:
            continue
        counts[status] += 1
        name = cell(row, i_name)
        g, h = cell(row, i_g), cell(row, i_h)
        # City resolution: City (New) wins; else City (Existing) unless it's an
        # "Other..." placeholder; else the row needs a human.
        city = h or (g if g and not fold(g).startswith("other") else "")
        if not name or not city:
            unresolved.append({"row": rownum, "name": name, "status": status,
                               "g": g, "h": h,
                               "events": cell(row, i_events), "why": cell(row, i_why)})
            continue
        key = (fold(name), fold(city))
        if key in seen:
            dupes.append({"row": rownum, "name": name, "city": city})
            continue
        seen.add(key)
        entries.append({"row": rownum, "name": name, "city": city, "status": status})
    return entries, unresolved, counts, dupes

def read_chapters():
    """Return (chapters, last_row). chapters = [{row, city, organizers_raw}]."""
    rows = get_values(CHAPTERS_ID, "'%s'!A:D" % CHAPTERS_TAB)
    if not rows:
        sys.exit("ABORT: chapters tab %r came back empty." % CHAPTERS_TAB)
    i_city, i_org = header_index(rows[0], CHAPTERS_TAB, "City", "Organizers")

    chapters, last_row = [], 1
    for rownum, row in enumerate(rows[1:], start=2):
        city = cell(row, i_city)
        if not city:
            continue   # never append into a gap; find the true last City row
        chapters.append({"row": rownum, "city": city, "organizers_raw": cell(row, i_org)})
        last_row = rownum
    return chapters, last_row

# ----------------------------------------------------------------------------
# Diff
# ----------------------------------------------------------------------------
def parse_organizers(raw):
    return [p.strip() for p in raw.split(";") if p.strip()]

def build_proposal(entries, chapters, last_row):
    """Return (adds, new_rows, near_misses).

    adds       = [{row, city, names, new_value}]   merge into an existing B cell
    new_rows   = [{row, city, names, slug}]        append after last_row
    near_misses= [{city, names, candidates}]       no exact row; never written
    """
    by_city = {}          # folded intake city -> {city, names[]}   (intake order)
    for e in entries:
        by_city.setdefault(fold(e["city"]), {"city": e["city"], "names": []})["names"].append(e["name"])

    chap_by_fold = {fold(c["city"]): c for c in chapters}
    adds, new_rows, near_misses = [], [], []
    next_row = last_row + 1
    for fc, grp in by_city.items():
        chap = chap_by_fold.get(fc)
        if chap:
            existing = parse_organizers(chap["organizers_raw"])
            present = {fold(n) for n in existing}
            # Merge, don't overwrite: keep every name already in B (manual
            # entries included), append only the intake names missing from it.
            missing = [n for n in grp["names"] if fold(n) not in present]
            if missing:
                adds.append({"row": chap["row"], "city": chap["city"], "names": missing,
                             "new_value": "; ".join(existing + missing)})
            continue
        cands = [c for c in chapters if fc in fold(c["city"]) or fold(c["city"]) in fc]
        if cands:
            near_misses.append({"city": grp["city"], "names": grp["names"],
                                "candidates": [(c["city"], c["row"]) for c in cands]})
            continue
        new_rows.append({"row": next_row, "city": grp["city"], "names": grp["names"],
                         "slug": slugify(grp["city"])})
        next_row += 1
    return adds, new_rows, near_misses

def annotate_unresolved(unresolved, chapters):
    """Mark unresolved rows already hand-placed on the chapters list, and infer
    a city ONLY when the row's free text explicitly names a chapter city."""
    for u in unresolved:
        u["placed"] = [(c["city"], c["row"]) for c in chapters
                       if fold(u["name"]) in {fold(n) for n in parse_organizers(c["organizers_raw"])}
                       ] if u["name"] else []
        text = fold(u["events"] + " " + u["why"])
        u["inferred"] = [c["city"] for c in chapters
                         if re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(fold(c["city"])), text)]

# ----------------------------------------------------------------------------
# Report
# ----------------------------------------------------------------------------
def print_report(entries, unresolved, counts, dupes, chapters, last_row,
                 adds, new_rows, near_misses):
    qual = " + ".join("%d %s" % (counts[s], s) for s in SYNC_STATUSES)
    print("Intake  : %d qualifying organizers (%s) across %d cities; %d unresolved; %d duplicate row(s)."
          % (len(entries), qual, len({fold(e["city"]) for e in entries}), len(unresolved), len(dupes)))
    print("Chapters: %d city rows (2-%d)." % (len(chapters), last_row))

    if adds:
        print("\nProposed adds to existing rows:")
        for a in adds:
            print("  %s (row %d): + %s" % (a["city"], a["row"], "; ".join(a["names"])))
            print("      B%d -> %r" % (a["row"], a["new_value"]))
    if new_rows:
        print("\nProposed NEW city rows (appended after row %d):" % last_row)
        for n in new_rows:
            status = luma_status(n["slug"])
            note = {"live": "Luma page live",
                    "absent": "Luma page NOT LIVE yet — create it manually; run aaif-create-chapter for the assets",
                    "unknown": "could not verify the Luma page — check it manually"}[status]
            print("  row %d: %s — %s — https://luma.com/aaif-%s (%s)"
                  % (n["row"], n["city"], "; ".join(n["names"]), n["slug"], note))
    if near_misses:
        print("\nNear-miss cities (NOT written — confirm the right row, or fix the intake city):")
        for m in near_misses:
            cand = ", ".join("%r (row %d)" % c for c in m["candidates"])
            print("  intake %r (%s) ~ chapter %s" % (m["city"], "; ".join(m["names"]), cand))
    if unresolved:
        print("\nUnresolved city — needs a human, never written:")
        for u in unresolved:
            print("  intake row %d: %s (%s) — City (Existing)=%r, City (New)=%r"
                  % (u["row"], u["name"] or "(no name)", u["status"], u["g"], u["h"]))
            print("      Run events before?: %r" % u["events"])
            print("      Why organize / ties: %r" % u["why"])
            if u["inferred"]:
                print("      -> free text names %s; fill City (New) on the intake row to sync."
                      % ", ".join(map(repr, u["inferred"])))
            if u["placed"]:
                print("      -> already on the chapters list: %s — no action needed."
                      % ", ".join("%s (row %d)" % p for p in u["placed"]))
    if dupes:
        print("\nDuplicate intake rows (deduped, first occurrence wins):")
        for d in dupes:
            print("  intake row %d: %s / %s" % (d["row"], d["name"], d["city"]))

    if not adds and not new_rows:
        print("\nNo changes needed — the chapters list is in sync with the intake.")

# ----------------------------------------------------------------------------
def compute():
    entries, unresolved, counts, dupes = read_intake()
    chapters, last_row = read_chapters()
    adds, new_rows, near_misses = build_proposal(entries, chapters, last_row)
    annotate_unresolved(unresolved, chapters)
    return entries, unresolved, counts, dupes, chapters, last_row, adds, new_rows, near_misses

def apply_changes(adds, new_rows):
    data = [{"range": "'%s'!B%d" % (CHAPTERS_TAB, a["row"]), "values": [[a["new_value"]]]}
            for a in adds]
    data += [{"range": "'%s'!A%d:D%d" % (CHAPTERS_TAB, n["row"], n["row"]),
              "values": [[n["city"], "; ".join(n["names"]), "",
                          "https://luma.com/aaif-" + n["slug"]]]}
             for n in new_rows]
    # One batchUpdate for everything, so a partial failure can't half-sync the
    # sheet. RAW, not USER_ENTERED: a name starting with = + - @ must stay text,
    # never become a formula.
    gws_json("sheets", "spreadsheets", "values", "batchUpdate",
             params={"spreadsheetId": CHAPTERS_ID},
             body={"valueInputOption": "RAW", "data": data})
    return len(data)

def main():
    ap = argparse.ArgumentParser(description="Sync intake organizer decisions into the chapters list.")
    ap.add_argument("--write", action="store_true",
                    help="apply the proposed changes (default: report only)")
    a = ap.parse_args()

    # --write recomputes from a fresh read here — a stale proposal is never applied.
    state = compute()
    print_report(*state)
    adds, new_rows = state[6], state[7]
    if not a.write or (not adds and not new_rows):
        return

    print("\nApplying %d cell update(s) + %d new row(s) in one batchUpdate..."
          % (len(adds), len(new_rows)))
    n = apply_changes(adds, new_rows)
    print("Wrote %d range(s)." % n)

    print("\nRe-verifying...")
    _, _, _, _, _, _, adds2, new_rows2, _ = compute()
    if adds2 or new_rows2:
        print("VERIFY FAILED — still out of sync after write:")
        for x in adds2:
            print("  row %d %s: + %s" % (x["row"], x["city"], "; ".join(x["names"])))
        for x in new_rows2:
            print("  new row %s: %s" % (x["city"], "; ".join(x["names"])))
        sys.exit(1)
    print("Verified: a fresh run proposes zero changes.")

if __name__ == "__main__":
    main()
