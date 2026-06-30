# AAIF Event Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `tracker-io` foundation plus three skills (`aaif-event-status`, `aaif-create-event`, `aaif-update-event`) that read and write an event's section inside a chapter/series `Event Tracker.docx`.

**Architecture:** A stdlib-only Python package `lib/aaif_meetups/` provides Drive access (`gws_cli.py`), low-level docx-zip/table editing (`office.py`), and an event-aware API + date math (`tracker.py`). Each skill is a thin CLI script that adds `lib/` to `sys.path`, calls the package, and talks to Drive via the `gws` CLI. All docx edits happen in pure Python on `word/document.xml` — no LibreOffice/soffice, no third-party libraries.

**Tech Stack:** Python 3.9 (stdlib only: `zipfile`, `xml.etree.ElementTree`, `copy`, `datetime`, `re`, `argparse`, `subprocess`, `json`), `unittest`, the `gws` CLI for Google Drive.

## Global Constraints

- **Stdlib-only.** No third-party Python deps (no `python-docx`, no `Pillow`). The repo has "no package to build."
- **Pure Python edits.** No `soffice`/LibreOffice anywhere in this plan.
- **Python 3.9**, `ruff` line-length 100, lint select `["F", "E9"]` (bug-focused).
- **Drive via `gws` CLI** only (prereq: `gws-cli-access`), through `lib/aaif_meetups/gws_cli.py`.
- **By-label, never positional.** Detail rows match on label text (`EVENT TITLE`, …); phase tables match on the header `["TASK","OWNER","DUE","STATUS"]`. Never hard-code a table/row index.
- **First argument is `<chapter|series>`** — resolved against `Chapters/` (⇒ in-person) or `Online/` (⇒ online); mode is auto-detected from which parent matched.
- **Drive folder IDs:** Chapters `1IQ1K7aVOKUUkxAcfLuNjdETEnmavvtjx`, Online `1g2vHrqDHfh9wBkDJryJIl8wqXA4J-d4i`.
- **WordprocessingML namespace:** `http://schemas.openxmlformats.org/wordprocessingml/2006/main` (prefix `w`).
- **Tracker structure (verified):** body is an ordered list of `<w:p>` and `<w:tbl>`. The detail block is a 2-col `<w:tbl>` whose first row is `["EVENT TITLE", <value>]`. Each phase table's first row is `["TASK","OWNER","DUE","STATUS"]`. The `DAY OF` phase table's DUE cells hold clock times (`16:00`), not dates.

---

## File Structure

- Create `lib/aaif_meetups/__init__.py` — package marker (empty).
- Create `lib/aaif_meetups/gws_cli.py` — Drive helpers (run gws, list/get/update/copy/create, download/upload).
- Create `lib/aaif_meetups/office.py` — docx zip read/write + table/cell/paragraph primitives.
- Create `lib/aaif_meetups/tracker.py` — event-aware API (`locate_tracker`, `list_events`, `read_event`, `clone_example_section`, `write_event`, `set_field`, `set_due_dates`) + date math.
- Create `lib/aaif_meetups/tests/__init__.py` — empty.
- Create `lib/aaif_meetups/tests/fixtures/event_tracker_irl.docx` — real TemplateCity tracker (downloaded).
- Create `lib/aaif_meetups/tests/fixtures/event_tracker_online.docx` — real TemplateSeries tracker (downloaded).
- Create `lib/aaif_meetups/tests/test_office.py`, `test_tracker.py`.
- Create `skills/aaif-event-status/SKILL.md` + `scripts/event_status.py`.
- Create `skills/aaif-create-event/SKILL.md` + `scripts/create_event.py`.
- Create `skills/aaif-update-event/SKILL.md` + `scripts/update_event.py`.
- Modify `skills/aaif-create-chapter/scripts/create_chapter.py` and `skills/aaif-create-online-series/scripts/create_series.py` — import `gws` from the shared package (drop duplicated helpers).

Run all tests with: `python -m unittest discover -s lib/aaif_meetups/tests -v`

---

## Task 1: Package skeleton + real fixtures

**Files:**
- Create: `lib/aaif_meetups/__init__.py`, `lib/aaif_meetups/tests/__init__.py`
- Create: `lib/aaif_meetups/tests/fixtures/event_tracker_irl.docx`, `event_tracker_online.docx`

**Interfaces:**
- Produces: an importable `aaif_meetups` package (when `lib/` is on `sys.path`) and two real tracker fixtures for offline tests.

- [ ] **Step 1: Create package markers**

```bash
mkdir -p lib/aaif_meetups/tests/fixtures
touch lib/aaif_meetups/__init__.py lib/aaif_meetups/tests/__init__.py
```

- [ ] **Step 2: Download the two real trackers as fixtures**

```bash
IRL=$(gws drive files list --params '{"q":"'\''1PHvEgqnHo0RrsFyA47O9iRJGaKehC8Eg'\'' in parents and name='\''Event Tracker.docx'\''","fields":"files(id)"}' | grep -oE '"id": "[^"]+"' | head -1 | cut -d'"' -f4)
ONLINE_TPL=$(gws drive files list --params '{"q":"'\''1M15wzKvQqd_jQz5cG16NO_YcbWU3EH1j'\'' in parents and name='\''Event Tracker.docx'\''","fields":"files(id)"}' | grep -oE '"id": "[^"]+"' | head -1 | cut -d'"' -f4)
( cd lib/aaif_meetups/tests/fixtures && gws drive files get --params "{\"fileId\":\"$IRL\",\"alt\":\"media\"}" --output event_tracker_irl.docx )
( cd lib/aaif_meetups/tests/fixtures && gws drive files get --params "{\"fileId\":\"$ONLINE_TPL\",\"alt\":\"media\"}" --output event_tracker_online.docx )
```

- [ ] **Step 3: Verify both fixtures open as valid docx zips**

```bash
python3 -c "import zipfile; [print(f, 'word/document.xml' in zipfile.ZipFile('lib/aaif_meetups/tests/fixtures/'+f).namelist()) for f in ('event_tracker_irl.docx','event_tracker_online.docx')]"
```
Expected: both print `True`.

- [ ] **Step 4: Commit**

```bash
git add lib/aaif_meetups
git commit -m "feat(tracker-io): package skeleton + real tracker fixtures"
```

---

## Task 2: `office.py` — docx zip read/write

**Files:**
- Create: `lib/aaif_meetups/office.py`
- Test: `lib/aaif_meetups/tests/test_office.py`

**Interfaces:**
- Produces:
  - `W` (str) — the `{namespace}` prefix, e.g. `"{http://…/main}"`.
  - `read_document(path: str) -> xml.etree.ElementTree.Element` — parse `word/document.xml`, return its root element.
  - `save_document(src_path: str, root: Element, out_path: str) -> None` — rewrite the docx zip at `out_path` copying every entry from `src_path`, replacing `word/document.xml` with the serialized `root`.

- [ ] **Step 1: Write the failing test**

```python
# lib/aaif_meetups/tests/test_office.py
import os, tempfile, unittest
from aaif_meetups import office

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "event_tracker_irl.docx")

class TestDocIO(unittest.TestCase):
    def test_read_returns_body(self):
        root = office.read_document(FIX)
        self.assertIsNotNone(root.find(f"{office.W}body"))

    def test_roundtrip_preserves_content_and_zip(self):
        root = office.read_document(FIX)
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "out.docx")
            office.save_document(FIX, root, out)
            root2 = office.read_document(out)
            # same number of tables survives the round-trip
            n1 = len(list(root.iter(f"{office.W}tbl")))
            n2 = len(list(root2.iter(f"{office.W}tbl")))
            self.assertEqual(n1, n2)
            self.assertGreater(n2, 5)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest lib.aaif_meetups.tests.test_office -v` (from repo root, with `PYTHONPATH=lib`)
Actual command: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_office -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aaif_meetups.office'`.

- [ ] **Step 3: Write minimal implementation**

```python
# lib/aaif_meetups/office.py
"""Stdlib-only OOXML helpers: read/write word/document.xml inside a .docx zip,
and navigate/edit its tables, rows, cells, and paragraph run text."""
import copy
import zipfile
from xml.etree import ElementTree as ET

NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = "{%s}" % NS
ET.register_namespace("w", NS)


def read_document(path):
    with zipfile.ZipFile(path) as z:
        return ET.fromstring(z.read("word/document.xml"))


def save_document(src_path, root, out_path):
    body = ET.tostring(root, encoding="UTF-8", xml_declaration=True)
    with zipfile.ZipFile(src_path) as zin:
        names = zin.namelist()
        data = {n: zin.read(n) for n in names}
    data["word/document.xml"] = body
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zo:
        for n in names:
            zo.writestr(n, data[n])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_office -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/aaif_meetups/office.py lib/aaif_meetups/tests/test_office.py
git commit -m "feat(office): docx document.xml read/save round-trip"
```

---

## Task 3: `office.py` — table/cell/paragraph primitives

**Files:**
- Modify: `lib/aaif_meetups/office.py`
- Test: `lib/aaif_meetups/tests/test_office.py` (add cases)

**Interfaces:**
- Consumes: `W`, `read_document` (Task 2).
- Produces:
  - `tables(root) -> list[Element]` — all `<w:tbl>` in document order.
  - `rows(tbl) -> list[Element]` — its `<w:tr>`.
  - `cells(tr) -> list[Element]` — its `<w:tc>`.
  - `cell_text(tc) -> str` — concatenated, stripped run text of a cell.
  - `set_cell_text(tc, text: str) -> None` — set the cell's text: write `text` into the first `<w:t>` of the first run, blank every other `<w:t>` in the cell (preserves the cell's run/format).
  - `para_text(p) -> str` — concatenated run text of a `<w:p>`.

- [ ] **Step 1: Write the failing test**

```python
# add to test_office.py
class TestTablePrimitives(unittest.TestCase):
    def setUp(self):
        self.root = office.read_document(FIX)

    def test_detail_table_first_row(self):
        # the detail table's first row is ["EVENT TITLE", <value>]
        detail = [t for t in office.tables(self.root)
                  if office.cell_text(office.cells(office.rows(t)[0])[0]) == "EVENT TITLE"]
        self.assertEqual(len(detail), 1)
        first = office.rows(detail[0])[0]
        self.assertEqual(office.cell_text(office.cells(first)[0]), "EVENT TITLE")

    def test_set_cell_text_roundtrips(self):
        detail = next(t for t in office.tables(self.root)
                      if office.cell_text(office.cells(office.rows(t)[0])[0]) == "EVENT TITLE")
        value_cell = office.cells(office.rows(detail)[0])[1]
        office.set_cell_text(value_cell, "New Night · Test Series")
        self.assertEqual(office.cell_text(value_cell), "New Night · Test Series")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_office -v`
Expected: FAIL with `AttributeError: module 'aaif_meetups.office' has no attribute 'tables'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to office.py
def tables(root):
    return list(root.iter(W + "tbl"))


def rows(tbl):
    return tbl.findall(W + "tr")


def cells(tr):
    return tr.findall(W + "tc")


def _texts(el):
    return list(el.iter(W + "t"))


def cell_text(tc):
    return "".join(t.text or "" for t in _texts(tc)).strip()


def para_text(p):
    return "".join(t.text or "" for t in _texts(p)).strip()


def set_cell_text(tc, text):
    ts = _texts(tc)
    if not ts:
        raise ValueError("cell has no run text node to set")
    ts[0].text = text
    # xml:space=preserve guards against trimming
    ts[0].set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    for extra in ts[1:]:
        extra.text = ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_office -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/aaif_meetups/office.py lib/aaif_meetups/tests/test_office.py
git commit -m "feat(office): table/cell/paragraph primitives"
```

---

## Task 4: `tracker.py` — date math (`parse_event_date`, `parse_due`, `restamp`)

**Files:**
- Create: `lib/aaif_meetups/tracker.py`
- Test: `lib/aaif_meetups/tests/test_tracker.py`

**Interfaces:**
- Produces:
  - `parse_event_date(text: str) -> datetime.date` — extract the date from a `DATE & TIME` value like `"Tue · June 24, 2026 · 17:30 — late"`. Raises `ValueError` if none found.
  - `parse_due(token: str, anchor: datetime.date) -> datetime.date | None` — parse a DUE cell like `"May 27"`/`"Jun 3"` choosing the year (anchor.year-1/+0/+1) closest to `anchor`. Returns `None` for clock-time cells (`"16:00"`) or empty/unparsable tokens.
  - `format_due(d: datetime.date) -> str` — `"%b %-d"` style without leading zero, e.g. `"May 27"`.
  - `restamp(due_token: str, old_event: datetime.date, new_event: datetime.date) -> str` — if `due_token` is a date, return it shifted by `(new_event - old_event)`'s effect via offset; if it's a clock time or blank, return it unchanged.

- [ ] **Step 1: Write the failing test**

```python
# lib/aaif_meetups/tests/test_tracker.py
import datetime as dt
import unittest
from aaif_meetups import tracker

class TestDates(unittest.TestCase):
    def test_parse_event_date(self):
        self.assertEqual(
            tracker.parse_event_date("Tue · June 24, 2026 · 17:30 — late"),
            dt.date(2026, 6, 24))

    def test_parse_due_infers_year(self):
        anchor = dt.date(2026, 6, 24)
        self.assertEqual(tracker.parse_due("May 27", anchor), dt.date(2026, 5, 27))
        self.assertEqual(tracker.parse_due("Jun 3", anchor), dt.date(2026, 6, 3))

    def test_parse_due_skips_clock_and_blank(self):
        anchor = dt.date(2026, 6, 24)
        self.assertIsNone(tracker.parse_due("16:00", anchor))
        self.assertIsNone(tracker.parse_due("", anchor))

    def test_restamp_shifts_dates_keeps_clock(self):
        old, new = dt.date(2026, 6, 24), dt.date(2026, 7, 8)  # +14 days
        self.assertEqual(tracker.restamp("May 27", old, new), "Jun 10")
        self.assertEqual(tracker.restamp("16:00", old, new), "16:00")
        self.assertEqual(tracker.restamp("", old, new), "")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aaif_meetups.tracker'`.

- [ ] **Step 3: Write minimal implementation**

```python
# lib/aaif_meetups/tracker.py
"""Event-aware reads/writes over an Event Tracker.docx, plus the shared
date-stamping math. Stdlib-only; pure-Python OOXML editing via office.py."""
import datetime as dt
import re

from aaif_meetups import office

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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add lib/aaif_meetups/tracker.py lib/aaif_meetups/tests/test_tracker.py
git commit -m "feat(tracker): date parsing and restamp math"
```

---

## Task 5: `tracker.py` — event model (`list_events`, `read_event`)

**Files:**
- Modify: `lib/aaif_meetups/tracker.py`
- Test: `lib/aaif_meetups/tests/test_tracker.py` (add cases)

**Interfaces:**
- Consumes: `office.tables/rows/cells/cell_text` (Tasks 2–3), `parse_event_date` (Task 4).
- Produces:
  - `PHASE_HEADER == ["TASK", "OWNER", "DUE", "STATUS"]`.
  - `is_detail_table(tbl) -> bool` — first row first cell == `"EVENT TITLE"`.
  - `is_phase_table(tbl) -> bool` — first row cells == `PHASE_HEADER`.
  - `list_events(root) -> list[dict]` — `[{"title": str, "detail_table": Element, "phase_tables": [Element], "date": date|None}]` in document order. An event = a detail table + every phase table after it until the next detail table.
  - `read_event(root, event) -> dict` — find one event by case-insensitive title substring, or `"next"` (soonest future date), or `"latest"` (max date). Returns `{"title", "details": {label: value}, "phases": [{"tasks": [{"task","owner","due","status"}]}], "date"}`. Raises `LookupError` if not found.

- [ ] **Step 1: Write the failing test**

```python
# add to test_tracker.py
import os
from aaif_meetups import office
FIX = os.path.join(os.path.dirname(__file__), "fixtures", "event_tracker_irl.docx")

class TestEventModel(unittest.TestCase):
    def setUp(self):
        self.root = office.read_document(FIX)

    def test_list_events_finds_the_example(self):
        evs = tracker.list_events(self.root)
        self.assertEqual(len(evs), 1)
        self.assertIn("Agentic AI Night", evs[0]["title"])
        self.assertEqual(len(evs[0]["phase_tables"]), 8)  # 4wk,3wk,2wk,1wk,day-before,day-of,next-day,follow-ups

    def test_read_event_details_and_tasks(self):
        ev = tracker.read_event(self.root, "Agentic AI Night")
        self.assertEqual(ev["details"]["DATE & TIME"], "Tue · June 24, 2026 · 17:30 — late")
        self.assertEqual(ev["date"], dt.date(2026, 6, 24))
        # first phase, first task
        self.assertEqual(ev["phases"][0]["tasks"][0]["status"], "Done")

    def test_read_event_next(self):
        ev = tracker.read_event(self.root, "next")
        self.assertIn("Agentic AI Night", ev["title"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: FAIL with `AttributeError: module 'aaif_meetups.tracker' has no attribute 'list_events'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to tracker.py
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
        future = sorted([e for e in dated if e["date"] >= dt.date.today()],
                        key=lambda e: e["date"])
        return (future or sorted(dated, key=lambda e: e["date"]))[0] if dated else None
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: PASS (all tracker tests).

- [ ] **Step 5: Commit**

```bash
git add lib/aaif_meetups/tracker.py lib/aaif_meetups/tests/test_tracker.py
git commit -m "feat(tracker): event model — list_events, read_event"
```

---

## Task 6: `tracker.py` — writes (`set_field`, `set_due_dates`)

**Files:**
- Modify: `lib/aaif_meetups/tracker.py`
- Test: `lib/aaif_meetups/tests/test_tracker.py` (add cases)

**Interfaces:**
- Consumes: `list_events`, `_select`, `restamp`, `office.set_cell_text` / `cells` / `rows`.
- Produces:
  - `set_field(root, event, label, value) -> None` — set the value cell of the detail row whose label cell == `label`, for the selected event. Raises `LookupError` if event or label missing.
  - `set_due_dates(root, event, new_event_date) -> int` — for the selected event, restamp every phase table DUE cell from the event's current date to `new_event_date`; also update the `DATE & TIME` detail value's date. Returns the count of DUE cells changed.

- [ ] **Step 1: Write the failing test**

```python
# add to test_tracker.py
import tempfile
class TestWrites(unittest.TestCase):
    def setUp(self):
        self.root = office.read_document(FIX)

    def test_set_field(self):
        tracker.set_field(self.root, "Agentic AI Night", "SPEAKER(S)", "Jane Doe (Infra)")
        ev = tracker.read_event(self.root, "Agentic AI Night")
        self.assertEqual(ev["details"]["SPEAKER(S)"], "Jane Doe (Infra)")

    def test_set_due_dates_shifts_two_weeks(self):
        # original 4-weeks-out task due "May 27"; +14 days -> "Jun 10"
        changed = tracker.set_due_dates(self.root, "Agentic AI Night", dt.date(2026, 7, 8))
        self.assertGreater(changed, 0)
        ev = tracker.read_event(self.root, "Agentic AI Night")
        self.assertEqual(ev["phases"][0]["tasks"][0]["due"], "Jun 10")
        # day-of clock times unchanged
        dayof = ev["phases"][5]["tasks"][0]["due"]
        self.assertRegex(dayof, r"^\d{1,2}:\d{2}$")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: FAIL with `AttributeError: ... has no attribute 'set_field'`.

- [ ] **Step 3: Write minimal implementation**

These public writes delegate to **element-level helpers** that act on a detail-table /
phase-table directly (no event re-selection). Task 7 reuses the same helpers on cloned
elements — this is what avoids the "edit the wrong section" ambiguity.

```python
# append to tracker.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/aaif_meetups/tracker.py lib/aaif_meetups/tests/test_tracker.py
git commit -m "feat(tracker): set_field and set_due_dates writes"
```

---

## Task 7: `tracker.py` — clone & append a new event section

**Files:**
- Modify: `lib/aaif_meetups/tracker.py`
- Test: `lib/aaif_meetups/tests/test_tracker.py` (add cases)

**Interfaces:**
- Consumes: `office` (W, tables, rows, cells), `list_events`, `is_detail_table`, `is_phase_table`, `_set_detail`, `_restamp_tables`, `_reset_status`. (Add `import copy` to `tracker.py`'s imports.)
- Produces:
  - `add_event(root, fields: dict, event_date: datetime.date) -> None` — clone the body elements spanning the **first** existing event (the heading paragraph immediately before its detail table, through its last phase table), edit the **cloned elements directly** (set detail fields from `fields`, restamp DUE cells from the example date to `event_date`, reset all STATUS to `"Not started"`), then insert the block just before the body's trailing `<w:sectPr>`. Editing the clone before insertion avoids any title/date selection ambiguity with the original example. `fields` keys are detail labels (`"EVENT TITLE"`, `"DATE & TIME"`, …).

- [ ] **Step 1: Write the failing test**

```python
# add to test_tracker.py
class TestAddEvent(unittest.TestCase):
    def setUp(self):
        self.root = office.read_document(FIX)

    def test_add_event_appends_section(self):
        before = len(tracker.list_events(self.root))
        tracker.add_event(self.root, {
            "EVENT TITLE": "Eval Night · Builder Series",
            "DATE & TIME": "Wed · August 12, 2026 · 18:00 — late",
            "SPEAKER(S)": "TBD",
        }, dt.date(2026, 8, 12))
        evs = tracker.list_events(self.root)
        self.assertEqual(len(evs), before + 1)
        new = tracker.read_event(self.root, "Eval Night")
        self.assertEqual(new["details"]["EVENT TITLE"], "Eval Night · Builder Series")
        # statuses reset
        self.assertTrue(all(t["status"] == "Not started"
                            for ph in new["phases"] for t in ph["tasks"]))
        # dates restamped to the new event date (4-wks-out is ~28 days before Aug 12)
        self.assertNotEqual(new["phases"][0]["tasks"][0]["due"], "May 27")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: FAIL with `AttributeError: ... has no attribute 'add_event'`.

- [ ] **Step 3: Write minimal implementation**

Add `import copy` to the top of `tracker.py`, then append:

```python
# append to tracker.py
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
```

Because the clone is edited *before* insertion, the new section already carries its own
title/date — later title-based reads (`read_event("Eval Night")`) are unambiguous.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: PASS.

- [ ] **Step 5: Validate the written docx still opens (no corruption)**

Add a round-trip assertion to the test: after `add_event`, `save_document` to a temp path and `read_document` it back, asserting the table count increased by 9 (1 detail + 8 phase). Append to `test_add_event_appends_section`:

```python
            import tempfile
            with tempfile.TemporaryDirectory() as dd:
                out = os.path.join(dd, "out.docx")
                office.save_document(FIX, self.root, out)
                reloaded = office.read_document(out)
                self.assertEqual(len(tracker.list_events(reloaded)), before + 1)
```

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: PASS — the appended section survives a save→reload.

- [ ] **Step 6: Commit**

```bash
git add lib/aaif_meetups/tracker.py lib/aaif_meetups/tests/test_tracker.py
git commit -m "feat(tracker): add_event clones and appends a dated section"
```

---

## Task 8: `gws_cli.py` — Drive helpers (extracted, shared)

**Files:**
- Create: `lib/aaif_meetups/gws_cli.py`
- Test: `lib/aaif_meetups/tests/test_gws_cli.py`

**Interfaces:**
- Produces (ported verbatim from `create_chapter.py`'s helpers, made importable):
  - `gws_json(*args, params=None, body=None) -> dict`
  - `gws_download(file_id, out_path) -> None`
  - `gws_upload(file_id, path, mime) -> None`
  - `list_children(folder_id) -> list[dict]`
  - `find_child(folder_id, name) -> dict | None` — first non-trashed child with exact name.
  - `DOCX` mime constant.

- [ ] **Step 1: Write the failing test** (pure-function test only — no Drive calls)

```python
# lib/aaif_meetups/tests/test_gws_cli.py
import unittest
from aaif_meetups import gws

class TestGwsModule(unittest.TestCase):
    def test_exposes_callables_and_mime(self):
        for name in ("gws_json", "gws_download", "gws_upload",
                     "list_children", "find_child"):
            self.assertTrue(callable(getattr(gws, name)), name)
        self.assertIn("wordprocessingml", gws_cli.DOCX)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_gws -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'aaif_meetups.gws'`.

- [ ] **Step 3: Write minimal implementation**

Port the helpers from `skills/aaif-create-chapter/scripts/create_chapter.py` (the `_gws`, `gws_json`, `gws_download`, `gws_upload`, `list_children` functions and the `DOCX`/folder constants), into `lib/aaif_meetups/gws_cli.py`. Add `find_child`:

```python
def find_child(folder_id, name):
    for c in list_children(folder_id):
        if c.get("name") == name:
            return c
    return None
```

Keep `list_children` filtering `trashed=false` (already does). Do NOT change behavior — this is a lift-and-shift so the existing scripts can import it in Task 12.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_gws -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/aaif_meetups/gws_cli.py lib/aaif_meetups/tests/test_gws_cli.py
git commit -m "feat(gws): shared Drive helpers extracted from create_chapter"
```

---

## Task 9: `tracker.py` — `locate_tracker` (Drive resolution)

**Files:**
- Modify: `lib/aaif_meetups/tracker.py`
- Test: `lib/aaif_meetups/tests/test_tracker.py` (add a test that monkeypatches `gws`)

**Interfaces:**
- Consumes: `gws_cli.list_children`, `gws_cli.find_child`.
- Produces:
  - `CHAPTERS_PARENT`, `ONLINE_PARENT` constants (the folder IDs from Global Constraints).
  - `locate_tracker(name) -> {"file_id", "kind", "folder_id", "folder_name"}` — find a folder named `name` (case-insensitive exact) under Chapters/ first, else Online/; `kind` is `"chapter"` or `"series"`. Inside it, find `Event Tracker.docx`. Raises `LookupError` if the folder or the tracker is missing.

- [ ] **Step 1: Write the failing test** (monkeypatch Drive — no network)

```python
# add to test_tracker.py
from aaif_meetups import gws_cli as gws_mod

class TestLocate(unittest.TestCase):
    def test_locate_prefers_chapters_then_online(self):
        calls = {}
        def fake_children(folder_id):
            if folder_id == tracker.CHAPTERS_PARENT:
                return [{"id": "fA", "name": "Berlin",
                         "mimeType": "application/vnd.google-apps.folder"}]
            if folder_id == "fA":
                return [{"id": "tDoc", "name": "Event Tracker.docx"}]
            return []
        orig = gws_mod.list_children
        gws_mod.list_children = fake_children
        try:
            got = tracker.locate_tracker("berlin")
        finally:
            gws_mod.list_children = orig
        self.assertEqual(got["file_id"], "tDoc")
        self.assertEqual(got["kind"], "chapter")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: FAIL with `AttributeError: ... has no attribute 'locate_tracker'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to tracker.py
from aaif_meetups import gws

CHAPTERS_PARENT = "1IQ1K7aVOKUUkxAcfLuNjdETEnmavvtjx"
ONLINE_PARENT = "1g2vHrqDHfh9wBkDJryJIl8wqXA4J-d4i"
FOLDER_MIME = "application/vnd.google-apps.folder"


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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=lib python -m unittest aaif_meetups.tests.test_tracker -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/aaif_meetups/tracker.py lib/aaif_meetups/tests/test_tracker.py
git commit -m "feat(tracker): locate_tracker resolves chapter or series"
```

---

## Task 10: Skill `aaif-event-status` (read-only)

**Files:**
- Create: `skills/aaif-event-status/SKILL.md`
- Create: `skills/aaif-event-status/scripts/event_status.py`

**Interfaces:**
- Consumes: `tracker.locate_tracker`, `gws_cli.gws_download`, `office.read_document`, `tracker.list_events` / `read_event`, `tracker.parse_due`.
- Produces: a CLI `python event_status.py <chapter|series> [event]` that prints overdue / due-soon tasks by owner. Read-only.

- [ ] **Step 1: Write the failing test (core logic, offline)**

```python
# skills/aaif-event-status/scripts/test_event_status.py
import datetime as dt, os, sys, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib")))
sys.path.insert(0, os.path.dirname(__file__))
import event_status

class TestClassify(unittest.TestCase):
    def test_overdue_and_due_soon(self):
        today = dt.date(2026, 6, 10)
        tasks = [
            {"task": "A", "owner": "Org", "due": "Jun 3", "status": "Not started"},   # overdue
            {"task": "B", "owner": "Org", "due": "Jun 12", "status": "Not started"},  # due soon
            {"task": "C", "owner": "Org", "due": "Jun 3", "status": "Done"},          # done -> ignore
            {"task": "D", "owner": "Co", "due": "16:00", "status": "Not started"},    # clock -> ignore
        ]
        anchor = dt.date(2026, 6, 24)
        res = event_status.classify(tasks, anchor, today)
        self.assertEqual([t["task"] for t in res["overdue"]], ["A"])
        self.assertEqual([t["task"] for t in res["due_soon"]], ["B"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest skills.aaif-event-status.scripts.test_event_status -v` — but the hyphen in the path blocks dotted import. Run directly instead:
`python skills/aaif-event-status/scripts/test_event_status.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'event_status'`.

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""Read-only status digest for a chapter/series Event Tracker: overdue and
due-soon tasks grouped by owner. Reads via the gws CLI; pure-Python parsing."""
import argparse, datetime as dt, os, pathlib, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from aaif_meetups import gws_cli, office, tracker  # noqa: E402

DUE_SOON_DAYS = 7


def classify(tasks, anchor, today):
    overdue, due_soon = [], []
    for t in tasks:
        d = tracker.parse_due(t.get("due", ""), anchor)
        if d is None or t.get("status") == "Done":
            continue
        if d < today:
            overdue.append(t)
        elif (d - today).days <= DUE_SOON_DAYS:
            due_soon.append(t)
    return {"overdue": overdue, "due_soon": due_soon}


def _digest(ev, today):
    flat = [t for ph in ev["phases"] for t in ph["tasks"]]
    res = classify(flat, ev["date"] or today, today)
    lines = ["", "== %s ==" % ev["title"],
             "%d overdue, %d due within %d days"
             % (len(res["overdue"]), len(res["due_soon"]), DUE_SOON_DAYS)]
    for label in ("overdue", "due_soon"):
        if res[label]:
            lines.append("  %s:" % label.replace("_", "-"))
            for t in sorted(res[label], key=lambda x: x.get("owner", "")):
                lines.append("    [%s] %s (due %s)" % (t["owner"], t["task"], t["due"]))
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("group", help="chapter or series name")
    ap.add_argument("event", nargs="?", help="optional event title; default all")
    a = ap.parse_args()
    loc = tracker.locate_tracker(a.group)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "tracker.docx")
        gws_cli.gws_download(loc["file_id"], path)
        root = office.read_document(path)
        events = tracker.list_events(root)
        if a.event:
            events = [e for e in events if a.event.lower() in e["title"].lower()]
        today = dt.date.today()
        print("%s (%s) — %d event(s)" % (loc["folder_name"], loc["kind"], len(events)))
        for e in events:
            print(_digest(tracker.read_event(root, e["title"]), today))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python skills/aaif-event-status/scripts/test_event_status.py`
Expected: PASS.

- [ ] **Step 5: Write the SKILL.md**

```markdown
---
name: aaif-event-status
description: Report task status for an AAIF chapter or online series — which event tasks are overdue or due soon, grouped by owner, read from the Event Tracker.docx. Use when asked for the status / health / what's-due of a chapter or series' events.
argument-hint: '<chapter|series> [event]'
---

# AAIF Event Status

Read-only digest of a chapter or online series' `Event Tracker.docx`: for each
event, the **overdue** and **due-soon** (within 7 days) tasks, grouped by owner.
Never writes.

Prereq: the `gws` CLI must be installed and authenticated (`gws-cli-access`).
The first argument resolves under **Chapters/** or **Online/** automatically.

## Run

    python skills/aaif-event-status/scripts/event_status.py "<chapter|series>" ["event"]

Examples:

    python skills/aaif-event-status/scripts/event_status.py "Berlin"
    python skills/aaif-event-status/scripts/event_status.py "Reading Group" "Paper Club"

Status is computed against today's date from each task's DUE cell; clock-time
day-of tasks and `Done` tasks are excluded.
```

- [ ] **Step 6: Commit**

```bash
git add skills/aaif-event-status
git commit -m "feat: aaif-event-status skill (read-only task digest)"
```

---

## Task 11: Skills `aaif-create-event` and `aaif-update-event`

**Files:**
- Create: `skills/aaif-create-event/SKILL.md` + `scripts/create_event.py`
- Create: `skills/aaif-update-event/SKILL.md` + `scripts/update_event.py`
- Test: `skills/aaif-create-event/scripts/test_create_event.py`

**Interfaces:**
- Consumes: `tracker.locate_tracker/add_event/set_field/set_due_dates/read_event/parse_event_date`, `gws_cli.gws_download/gws_upload/DOCX`, `office.read_document/save_document`.
- Produces:
  - `create_event.py <chapter|series> --title T --date "..." [--theme --venue --platform --speakers --luma --capacity --organizer] [--dry-run]` — downloads the tracker, `add_event`, re-uploads. Aborts if an event with the same title already exists.
  - `update_event.py <chapter|series> <event> [--set "LABEL=value" ...] [--date "..."]` — applies field edits; if `--date`, recomputes due dates; prints which downstream assets are now stale.

- [ ] **Step 1: Write the failing test for create_event core (offline, on a fixture copy)**

```python
# skills/aaif-create-event/scripts/test_create_event.py
import datetime as dt, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "lib")))
sys.path.insert(0, os.path.dirname(__file__))
import create_event
from aaif_meetups import office, tracker

FIX = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                   "lib", "aaif_meetups", "tests", "fixtures",
                                   "event_tracker_irl.docx"))

class TestCreateCore(unittest.TestCase):
    def test_apply_adds_event_to_local_docx(self):
        with tempfile.TemporaryDirectory() as d:
            local = os.path.join(d, "t.docx")
            shutil.copy(FIX, local)
            create_event.apply_local(local, {
                "EVENT TITLE": "Eval Night",
                "DATE & TIME": "Wed · August 12, 2026 · 18:00 — late",
            }, dt.date(2026, 8, 12))
            root = office.read_document(local)
            titles = [e["title"] for e in tracker.list_events(root)]
            self.assertIn("Eval Night", titles)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python skills/aaif-create-event/scripts/test_create_event.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'create_event'`.

- [ ] **Step 3: Implement `create_event.py`**

```python
#!/usr/bin/env python3
"""Create a new event section in a chapter/series Event Tracker.docx: clone the
example section, fill details, and stamp all phase due-dates from the event date.
Stdlib-only, pure-Python docx edit; Drive I/O via the gws CLI."""
import argparse, datetime as dt, os, pathlib, sys, tempfile

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
```

- [ ] **Step 4: Run create_event test to verify it passes**

Run: `python skills/aaif-create-event/scripts/test_create_event.py`
Expected: PASS.

- [ ] **Step 5: Implement `update_event.py`**

```python
#!/usr/bin/env python3
"""Apply a targeted change to an existing event in a chapter/series tracker:
edit detail fields and, when the date moves, recompute every phase due-date.
Then report which downstream assets are now stale. Pure-Python docx edit."""
import argparse, os, pathlib, sys, tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from aaif_meetups import gws_cli, office, tracker  # noqa: E402

STALE_ON_DATE = ["square banner", "Luma cover", "announcement post",
                 "carousel", "day-of slides", "attendee reminder"]
STALE_ON_SPEAKER = ["speaker bio", "announcement post", "carousel", "day-of slides"]


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
        stale = set()
        for pair in a.set:
            label, _, value = pair.partition("=")
            tracker.set_field(root, a.event, label.strip(), value.strip())
            if "SPEAKER" in label.upper():
                stale.update(STALE_ON_SPEAKER)
        if a.date:
            tracker.set_field(root, a.event, "DATE & TIME", a.date)
            tracker.set_due_dates(root, a.event, tracker.parse_event_date(a.date))
            stale.update(STALE_ON_DATE)
        office.save_document(path, root, path)
        gws_cli.gws_upload(loc["file_id"], path, gws_cli.DOCX)
    print("Updated %r in %s." % (a.event, loc["folder_name"]))
    if stale:
        print("Now stale — re-run these skills: " + ", ".join(sorted(stale)))


if __name__ == "__main__":
    main()
```

Note: `update_event.py` is exercised through `tracker`'s already-tested `set_field`/`set_due_dates`; no separate unit test beyond those. The stale-asset lists are static strings (no logic to test).

- [ ] **Step 6: Write both SKILL.md files**

`skills/aaif-create-event/SKILL.md`:

```markdown
---
name: aaif-create-event
description: Create a new event in an AAIF chapter or online series by cloning the example section in its Event Tracker.docx and stamping all phase task due-dates from the event date. Use when asked to add/schedule/set up a new event for a chapter or series.
argument-hint: '<chapter|series> --title "..." --date "..."'
---

# AAIF Create Event

Clone the example event section in a chapter/series `Event Tracker.docx`, fill the
detail block, and compute every phase task's DUE date backward from the event date.
Mode is auto-detected: a chapter (under Chapters/) clones the in-person task set; an
online series (under Online/) clones the online set. Aborts if the title already exists.

Prereq: `gws` CLI authenticated (`gws-cli-access`).

## Run

    python skills/aaif-create-event/scripts/create_event.py "<chapter|series>" \
      --title "Eval Night · Builder Series" \
      --date "Wed · August 12, 2026 · 18:00 — late" \
      [--theme "..."] [--venue "..."] [--platform "..."] [--speakers "..."] \
      [--luma "lu.ma/aaif-..."] [--capacity "..."] [--organizer "..."] [--dry-run]

Anything you omit is left as the example's text for you to fill later. Due-dates
keep the template's exact cadence (each task's offset from the event date is preserved).
```

`skills/aaif-update-event/SKILL.md`:

```markdown
---
name: aaif-update-event
description: Apply a change to an existing AAIF event (chapter or series) — edit detail fields like speakers/venue/capacity, or move the date and recompute all task due-dates, then flag which marketing/banner assets are now stale. Use when asked to update/change/edit an event's details or date.
argument-hint: '<chapter|series> <event> [--set "LABEL=value"] [--date "..."]'
---

# AAIF Update Event

Change-driven editor for one event in a chapter/series `Event Tracker.docx`. State the
change; the skill edits the right detail fields. If you move the date, every phase task
DUE date is recomputed (clock-time day-of tasks are left alone). It then reports which
downstream assets (banner, Luma cover, posts, slides) are now stale so you can re-run
those skills — it does not regenerate them.

Prereq: `gws` CLI authenticated (`gws-cli-access`).

## Run

    # add/replace a speaker
    python skills/aaif-update-event/scripts/update_event.py "Berlin" "Agentic AI Night" \
      --set "SPEAKER(S)=Jane Doe (Agent Infra)"

    # move the date (recomputes all due-dates)
    python skills/aaif-update-event/scripts/update_event.py "Berlin" "Agentic AI Night" \
      --date "Wed · July 8, 2026 · 17:30 — late"

Detail labels: EVENT TITLE, DATE & TIME, LOCATION / CITY, VENUE, THEME / SERIES,
FORMAT(S), SPEAKER(S), LUMA URL, CAPACITY / RSVPS, ORGANIZER ON POINT.
```

- [ ] **Step 7: Commit**

```bash
git add skills/aaif-create-event skills/aaif-update-event
git commit -m "feat: aaif-create-event and aaif-update-event skills"
```

---

## Task 12: Refactor existing scripts onto shared `gws_cli.py`

**Files:**
- Modify: `skills/aaif-create-chapter/scripts/create_chapter.py`
- Modify: `skills/aaif-create-online-series/scripts/create_series.py`

**Interfaces:**
- Consumes: `lib/aaif_meetups/gws_cli.py` (Task 8).

- [ ] **Step 1: Add the sys.path shim + import, delete the duplicated helpers in `create_chapter.py`**

Replace the in-file `_gws`, `gws_json`, `gws_download`, `gws_upload`, `list_children`, `create_folder`, `copy_file` definitions with:

```python
import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "lib"))
from aaif_meetups.gws_cli import (  # noqa: E402
    gws_json, gws_download, gws_upload, list_children, DOCX, PPTX, XLSX, FOLDER,
)
```

(Move any constants the script still needs — `PPTX`, `XLSX`, `FOLDER`, `MIME_BY_EXT` — into `gws_cli.py` if not already there, and import them. Keep `create_folder`/`copy_file` in `gws_cli.py` too.)

- [ ] **Step 2: Run the existing local rebrand self-test to prove no regression**

Run: `python skills/aaif-create-chapter/scripts/create_chapter.py --city "Los Angeles" --rebrand-local /tmp/nonexistent 2>&1 | head -1`
Expected: the script imports cleanly (no `ImportError`); it will then report the dir doesn't exist — that's fine, it proves imports resolve.

- [ ] **Step 3: Repeat for `create_series.py`** (same shim + import; delete its duplicated helpers).

- [ ] **Step 4: Run the full test suite**

Run: `PYTHONPATH=lib python -m unittest discover -s lib/aaif_meetups/tests -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add skills/aaif-create-chapter/scripts/create_chapter.py skills/aaif-create-online-series/scripts/create_series.py
git commit -m "refactor: create_chapter/create_series import shared gws helpers"
```

---

## Task 13: End-to-end dry-run validation against real Drive (manual checkpoint)

**Files:** none (verification only).

- [ ] **Step 1: Status on a real chapter (read-only, safe)**

Run: `python skills/aaif-event-status/scripts/event_status.py "San Francisco"`
Expected: prints the chapter, its event(s), and overdue/due-soon tasks without error.

- [ ] **Step 2: create-event dry-run (no write)**

Run: `python skills/aaif-create-event/scripts/create_event.py "San Francisco" --title "ZZZ Test Event" --date "Wed · September 9, 2026 · 18:00 — late" --dry-run`
Expected: prints the resolved tracker + parsed date; no upload.

- [ ] **Step 3: Confirm tests + lint clean**

Run: `PYTHONPATH=lib python -m unittest discover -s lib/aaif_meetups/tests -v && ruff check lib skills`
Expected: tests PASS; ruff reports no `F`/`E9` errors.

- [ ] **Step 4: Final commit (if anything adjusted)**

```bash
git add -A && git commit -m "chore: event-lifecycle e2e dry-run validation" || echo "nothing to commit"
```

---

## Self-Review notes

- **Spec coverage:** `tracker-io` (Tasks 2–9), `create-event` (11), `update-event` (11),
  `event-status` (10), `<chapter|series>` arg + mode auto-detect (9, skills), date rule
  (4, 6), dedup guard (11 Step 3), stale-asset flagging (11 Step 5), shared-lib + de-dup
  of gws helpers (8, 12), fixture/offline tests + `--dry-run`/`apply_local` (throughout).
- **Out of scope (correctly absent):** banner/image generation and any soffice/`.pptx`
  rendering (sub-project #3); chapter/series health (sub-project #4); two-plugin split
  (sub-project #5).
- **Known follow-up:** phase *heading* anchor dates (e.g. "4 WEEKS OUT  May 27 · …") are
  not recomputed in v1 — only the authoritative DUE cells and the DATE & TIME value.
  Acceptable; note for a later enhancement.
