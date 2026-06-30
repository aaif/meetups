"""Event-aware reads/writes over an Event Tracker.docx, plus the shared
date-stamping math. Stdlib-only; pure-Python OOXML editing via office.py."""
import datetime as dt
import re

_MONTHS = {m: i for i, m in enumerate(
    ["", "jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"])}
_DATE_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})", re.I)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_CLOCK_RE = re.compile(r"^\s*\d{1,2}:\d{2}\s*$")


def parse_event_date(text):
    m = _DATE_RE.search(text)
    if not m:
        raise ValueError("no month/day in event date: %r" % text)
    month, day = _MONTHS[m.group(1)[:3].lower()], int(m.group(2))
    ym = _YEAR_RE.search(text)
    year = int(ym.group(1)) if ym else dt.date.today().year
    return dt.date(year, month, day)


def parse_due(token, anchor):
    if token is None or _CLOCK_RE.match(token or "") or not (token or "").strip():
        return None
    m = _DATE_RE.search(token)
    if not m:
        return None
    month, day = _MONTHS[m.group(1)[:3].lower()], int(m.group(2))
    best = None
    for year in (anchor.year - 1, anchor.year, anchor.year + 1):
        try:
            cand = dt.date(year, month, day)
        except ValueError:
            continue
        if best is None or abs((cand - anchor).days) < abs((best - anchor).days):
            best = cand
    return best


def format_due(d):
    return "%s %d" % (d.strftime("%b"), d.day)


def restamp(due_token, old_event, new_event):
    parsed = parse_due(due_token, old_event)
    if parsed is None:
        return due_token
    return format_due(parsed + (new_event - old_event))
