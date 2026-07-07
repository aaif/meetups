#!/usr/bin/env python3
"""Unit tests for the pure logic in sync_chapters.py (no network/gws)."""
import sys, os
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_chapters
from sync_chapters import fold, slugify, parse_organizers, build_proposal

def chap(row, city, orgs):
    return {"row": row, "city": city, "organizers_raw": orgs}

def entry(row, name, city):
    return {"row": row, "name": name, "city": city, "status": "Accepted"}

fails = 0
def check(label, got, want):
    global fails
    ok = got == want
    fails += 0 if ok else 1
    print("%s %s" % ("ok  " if ok else "FAIL", label))
    if not ok:
        print("      got : %r\n      want: %r" % (got, want))

# --- fold: case, whitespace, accents (compare folded, write original) --------
check("fold trims/collapses/casefolds", fold("  Chandana  Srinivasa "), "chandana srinivasa")
check("fold strips accents", fold("Médéric Hurier"), fold("Mederic HURIER"))

# --- slugify: default rule + the Denver exception -----------------------------
check("slug default", slugify("New York"), "newyork")
check("slug accents", slugify("Montréal"), "montreal")
check("slug Denver override", slugify("Denver"), "colorado")

# --- parse_organizers ----------------------------------------------------------
check("parse B", parse_organizers(" Gleb Lukicov;  Alex Jones ; "), ["Gleb Lukicov", "Alex Jones"])
check("parse empty B", parse_organizers(""), [])

CHAPTERS = [chap(2, "Boston", "Kranthi Manchikanti"),
            chap(3, "Delhi NCR", ""),
            chap(4, "San Francisco", "Rahul Parundekar"),
            chap(5, "Silicon Valley", "")]

# --- merge, don't overwrite: dupe detection is case/space/accent-insensitive ---
adds, new_rows, near = build_proposal(
    [entry(2, "kranthi  manchikanti", "Boston"),      # already present (case/space)
     entry(3, "New Person", "Boston")],
    CHAPTERS, 5)
check("merge appends only missing", adds,
      [{"row": 2, "city": "Boston", "names": ["New Person"],
        "new_value": "Kranthi Manchikanti; New Person"}])
check("merge creates no rows", (new_rows, near), ([], []))

# --- city match is case-insensitive; manual B entries are kept -----------------
adds, _, _ = build_proposal([entry(2, "Ana Ruiz", "  boston ")], CHAPTERS, 5)
check("city matched folded, existing name kept", adds[0]["new_value"],
      "Kranthi Manchikanti; Ana Ruiz")

# --- near-miss reported, never written -----------------------------------------
adds, new_rows, near = build_proposal([entry(2, "Kritika Parmar", "Delhi")], CHAPTERS, 5)
check("near-miss no write", (adds, new_rows), ([], []))
check("near-miss candidates", near,
      [{"city": "Delhi", "names": ["Kritika Parmar"],
        "candidates": [("Delhi NCR", 3)]}])

# --- SF is NOT mirrored into Silicon Valley -------------------------------------
adds, new_rows, near = build_proposal([entry(2, "Leo Walker", "San Francisco")], CHAPTERS, 5)
check("SF row only, SV untouched", [a["row"] for a in adds], [4])

# --- new rows append after last non-empty row, in intake order ------------------
adds, new_rows, _ = build_proposal(
    [entry(2, "Imran Bagwan", "Pune"), entry(3, "Someone Else", "Pune"),
     entry(4, "Jaime Vélez", "Montréal")],
    CHAPTERS, 5)
check("new rows numbered from last+1",
      [(n["row"], n["city"], n["names"], n["slug"]) for n in new_rows],
      [(6, "Pune", ["Imran Bagwan", "Someone Else"], "pune"),
       (7, "Montréal", ["Jaime Vélez"], "montreal")])

# --- empty B everywhere (first-ever run) ----------------------------------------
adds, _, _ = build_proposal([entry(2, "A B", "Delhi NCR")],
                            [chap(2, "Delhi NCR", "")], 2)
check("empty B populated", adds[0]["new_value"], "A B")

# --- apply_changes: exact ranges, column order, RAW (gws mocked, no network) -----
with mock.patch.object(sync_chapters, "gws_json") as gj:
    n = sync_chapters.apply_changes(
        [{"row": 2, "city": "Boston", "names": ["New Person"],
          "new_value": "Kranthi Manchikanti; New Person"}],
        [{"row": 6, "city": "Pune", "names": ["Imran Bagwan"], "slug": "pune"}])
    body = gj.call_args.kwargs["body"]
check("apply_changes writes both changes", n, 2)
check("apply_changes uses RAW (no formula injection)", body["valueInputOption"], "RAW")
check("apply_changes ranges and column order", body["data"],
      [{"range": "'%s'!B2" % sync_chapters.CHAPTERS_TAB,
        "values": [["Kranthi Manchikanti; New Person"]]},
       {"range": "'%s'!A6:D6" % sync_chapters.CHAPTERS_TAB,
        "values": [["Pune", "Imran Bagwan", "", "https://luma.com/aaif-pune"]]}])

# --- gws_json survives U+2028 inside JSON string values (the splitlines() bug) ---
raw = '{"a": "line1\u2028line2"}\n'
with mock.patch.object(sync_chapters.subprocess, "run",
                       return_value=mock.Mock(returncode=0, stdout=raw)):
    check("gws_json keeps U+2028 inside values", sync_chapters.gws_json("sheets", "get"),
          {"a": "line1\u2028line2"})

print()
sys.exit("FAIL: %d test(s) failed" % fails if fails else None)
