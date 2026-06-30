"""Event-aware reads/writes over an Event Tracker.docx, plus the shared
date-stamping math. Stdlib-only; pure-Python OOXML editing via office.py."""
import copy
import datetime as dt
import re

from aaif_meetups import gws_cli, office

CHAPTERS_PARENT = "1IQ1K7aVOKUUkxAcfLuNjdETEnmavvtjx"
ONLINE_PARENT = "1g2vHrqDHfh9wBkDJryJIl8wqXA4J-d4i"
FOLDER_MIME = "application/vnd.google-apps.folder"

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


PHASE_HEADER = ["TASK", "OWNER", "DUE", "STATUS"]


def _row_cells_text(tbl, row_index):
    rs = office.rows(tbl)
    if not rs:
        return []
    return [office.cell_text(c) for c in office.cells(rs[row_index])]


def is_detail_table(tbl):
    cells0 = _row_cells_text(tbl, 0)
    return bool(cells0) and cells0[0] == "EVENT TITLE"


def is_phase_table(tbl):
    return _row_cells_text(tbl, 0) == PHASE_HEADER


def list_events(root):
    events, current = [], None
    for tbl in office.tables(root):
        if is_detail_table(tbl):
            details = {}
            for r in office.rows(tbl):
                cs = office.cells(r)
                if len(cs) >= 2:
                    details[office.cell_text(cs[0])] = office.cell_text(cs[1])
            title = details.get("EVENT TITLE", "")
            try:
                date = parse_event_date(details.get("DATE & TIME", ""))
            except ValueError:
                date = None
            current = {"title": title, "detail_table": tbl,
                       "phase_tables": [], "date": date}
            events.append(current)
        elif is_phase_table(tbl) and current is not None:
            current["phase_tables"].append(tbl)
    return events


def _select(events, event):
    key = (event or "").strip().lower()
    dated = [e for e in events if e["date"]]
    if key == "next":
        if not dated:
            return None
        future = sorted([e for e in dated if e["date"] >= dt.date.today()],
                        key=lambda e: e["date"])
        return (future or sorted(dated, key=lambda e: e["date"]))[0]
    if key == "latest":
        return max(dated, key=lambda e: e["date"]) if dated else None
    for e in events:
        if key in e["title"].lower():
            return e
    return None


def read_event(root, event):
    events = list_events(root)
    e = _select(events, event)
    if e is None:
        raise LookupError("no event matching %r" % event)
    details = {}
    for r in office.rows(e["detail_table"]):
        cs = office.cells(r)
        if len(cs) >= 2:
            details[office.cell_text(cs[0])] = office.cell_text(cs[1])
    phases = []
    for pt in e["phase_tables"]:
        tasks = []
        for r in office.rows(pt)[1:]:
            cs = [office.cell_text(c) for c in office.cells(r)]
            cs += [""] * (4 - len(cs))
            tasks.append({"task": cs[0], "owner": cs[1], "due": cs[2], "status": cs[3]})
        phases.append({"tasks": tasks})
    return {"title": e["title"], "details": details, "phases": phases, "date": e["date"]}


def _selected_or_raise(root, event):
    e = _select(list_events(root), event)
    if e is None:
        raise LookupError("no event matching %r" % event)
    return e


def _set_detail(detail_tbl, label, value):
    """Set the value cell of the row whose label cell == label. Returns bool found."""
    for r in office.rows(detail_tbl):
        cs = office.cells(r)
        if len(cs) >= 2 and office.cell_text(cs[0]) == label:
            office.set_cell_text(cs[1], value)
            return True
    return False


def _restamp_tables(detail_tbl, phase_tbls, old_date, new_date):
    """Shift every phase DUE cell by (new-old); sync the DATE & TIME value's date.
    Returns the count of DUE cells changed."""
    changed = 0
    for pt in phase_tbls:
        for r in office.rows(pt)[1:]:
            cs = office.cells(r)
            if len(cs) >= 3:
                cur = office.cell_text(cs[2])
                nv = restamp(cur, old_date, new_date)
                if nv != cur:
                    office.set_cell_text(cs[2], nv)
                    changed += 1
    for r in office.rows(detail_tbl):
        cs = office.cells(r)
        if len(cs) >= 2 and office.cell_text(cs[0]) == "DATE & TIME":
            txt = office.cell_text(cs[1])
            txt = _DATE_RE.sub(new_date.strftime("%B ") + str(new_date.day), txt, count=1)
            txt = _YEAR_RE.sub(str(new_date.year), txt, count=1)
            office.set_cell_text(cs[1], txt)
    return changed


def _reset_status(phase_tbls):
    for pt in phase_tbls:
        for r in office.rows(pt)[1:]:
            cs = office.cells(r)
            if len(cs) >= 4:
                office.set_cell_text(cs[3], "Not started")


def set_field(root, event, label, value):
    e = _selected_or_raise(root, event)
    if not _set_detail(e["detail_table"], label, value):
        raise LookupError("no detail row labelled %r" % label)


def set_due_dates(root, event, new_event_date):
    e = _selected_or_raise(root, event)
    if e["date"] is None:
        raise ValueError("event has no parseable current date; cannot restamp")
    return _restamp_tables(e["detail_table"], e["phase_tables"], e["date"], new_event_date)


def _body(root):
    return root.find(office.W + "body")


def add_event(root, fields, event_date):
    events = list_events(root)
    if not events:
        raise LookupError("tracker has no example event section to clone")
    example = events[0]
    old_date = example["date"]
    body = _body(root)
    kids = list(body)
    # span: the paragraph immediately before the detail table .. the last phase table
    detail_idx = kids.index(example["detail_table"])
    start = detail_idx - 1 if detail_idx > 0 and kids[detail_idx - 1].tag == office.W + "p" else detail_idx
    last = example["phase_tables"][-1] if example["phase_tables"] else example["detail_table"]
    end = kids.index(last)
    block = [copy.deepcopy(kids[i]) for i in range(start, end + 1)]
    # edit the CLONED elements directly (no re-selection against the original)
    new_detail = next(el for el in block
                      if el.tag == office.W + "tbl" and is_detail_table(el))
    new_phases = [el for el in block
                  if el.tag == office.W + "tbl" and is_phase_table(el)]
    for label, value in fields.items():
        _set_detail(new_detail, label, value)
    if old_date is not None:
        _restamp_tables(new_detail, new_phases, old_date, event_date)
    _reset_status(new_phases)
    # insert before trailing sectPr if present, else at end
    sectpr = body.find(office.W + "sectPr")
    insert_at = kids.index(sectpr) if sectpr is not None else len(kids)
    for offset, el in enumerate(block):
        body.insert(insert_at + offset, el)


def _find_folder(parent, name):
    key = name.strip().lower()
    for c in gws_cli.list_children(parent):
        if c.get("mimeType") == FOLDER_MIME and c.get("name", "").lower() == key:
            return c
    return None


def locate_tracker(name):
    for parent, kind in ((CHAPTERS_PARENT, "chapter"), (ONLINE_PARENT, "series")):
        folder = _find_folder(parent, name)
        if folder:
            doc = gws_cli.find_child(folder["id"], "Event Tracker.docx")
            if not doc:
                raise LookupError("%r has no Event Tracker.docx" % name)
            return {"file_id": doc["id"], "kind": kind,
                    "folder_id": folder["id"], "folder_name": folder["name"]}
    raise LookupError("no chapter or series named %r" % name)
