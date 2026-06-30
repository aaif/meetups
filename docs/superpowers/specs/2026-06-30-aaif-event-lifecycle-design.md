# AAIF Event Lifecycle + `tracker-io` Foundation — Design

**Date:** 2026-06-30
**Status:** Draft for review
**Scope of this spec:** Sub-projects #1 (the `tracker-io` foundation) and #2 (the
three event-lifecycle skills). The other sub-projects (pptx-fill-export, content-skill
enhancement, management/health skills, two-bundle repo split) are out of scope here and
will get their own specs.

---

## 1. Context & goals

The AAIF meetup skills repo migrated the per-folder `SKILLS.md.docx` prompts into 12
versioned skills. The 8 content skills cover *the words & decks*; the 4 ops skills cover
intake and chapter/series creation. The gap: **nothing automates the per-event runbook**
— the `Event Tracker.docx`, which is the actual spine of running an event.

This spec adds that spine:

- a shared **`tracker-io`** layer that reads and writes an event's section inside a
  chapter/series `Event Tracker.docx`, and
- three skills on top of it: **`aaif-create-event`**, **`aaif-update-event`**,
  **`aaif-event-status`**.

It also establishes two repo-wide conventions every later skill inherits: the standard
**`<chapter|series> <event>`** argument pair (the first argument is a chapter *or* an
online series), and **auto-detected online/in-person mode**.

**Implementation note:** every edit in this spec is performed in **pure Python** on the
`.docx` XML — no LibreOffice/`soffice`, no rendering engine. (`soffice` was only ever
floated for a *later* sub-project, #3, to *render* a filled `.pptx` into a posted image;
that render-engine choice — pure-Python `Pillow` composition vs. `python-pptx` + `soffice`
— is deferred to the #3 spec and is out of scope here.)

### Goals
- Create a fully-scaffolded event in the tracker (detail block + all phased task tables
  with computed due-dates) from a few inputs.
- Apply targeted, change-driven edits to an existing event ("add speaker X", "move to
  Jul 8") and recompute due-dates when the event date moves.
- Report task status across a chapter's events (overdue / due-soon / by owner).
- Keep the tracker as `.docx` (per decision #6) and stay **stdlib-only** (repo
  philosophy — no third-party deps, no package to build).

### Non-goals (this spec)
- Generating banners/decks/images, and any `.pptx` rendering (that's the file-aware
  content skills, sub-project #3). The render-engine decision for #3 — pure-Python
  `Pillow` composition vs. `python-pptx` + `soffice` — is explicitly deferred to that spec.
- Migrating to a Sheet (explicitly declined).
- The two-plugin bundle split (sub-project #5).

---

## 2. Source of truth & data model

Each chapter lives in `Chapters/<City>/`; each online series in `Online/<Series>/`. Both
contain one `Event Tracker.docx`. Within a tracker:

- **Preamble** (shared Quickstart + "How to use this tracker") — never touched.
- **Chapter/series identity blocks** (About, Vibes, Organizers, Luma) — never touched.
- **One section per event**, in document order. A section is:
  1. a **heading** paragraph, e.g. `June 24, 2026 · AGENTIC AI NIGHT — LAUNCH SERIES`
  2. a **detail table** with labelled rows: `EVENT TITLE`, `DATE & TIME`,
     `LOCATION / CITY`, `VENUE`, `THEME / SERIES`, `FORMAT(S)`, `SPEAKER(S)`, `LUMA URL`,
     `CAPACITY / RSVPS`, `ORGANIZER ON POINT`
  3. a sequence of **phase tables**, each a `TASK | OWNER | DUE | STATUS` grid, under a
     phase heading: `4 WEEKS OUT`, `3 WEEKS OUT`, `2 WEEKS OUT`, `1 WEEK OUT`,
     `DAY BEFORE`, `DAY OF`, `NEXT DAY`, `FOLLOW-UPS`.

The **online tracker** (`Event Tracker (Online).docx`) has the same shape but a no-venue
task set (platform / join link / tech check / recording / chat-Q&A instead of
venue / A-V / food / door).

**Canonical "example" section.** Every freshly-cloned tracker ships with one filled
example event (the June 24 "Agentic AI Night" block). `create-event` clones *that
section's structure*. Treat it as the template-of-record; do not delete it from the
masters.

---

## 3. Foundation: `tracker-io`

A stdlib-only module that manipulates `Event Tracker.docx` by editing `word/document.xml`
inside the docx zip (the same technique `create_chapter.py` already uses). No
`python-docx`.

**Location:** `lib/aaif_meetups/` at repo root, holding:
- `gws.py` — the Drive helpers currently duplicated in `create_chapter.py` /
  `create_series.py` (list/get/update/copy/create, retry wrapper). De-dups existing code.
- `office.py` — low-level docx helpers: load/save the zip, get/set `document.xml`,
  iterate `<w:tbl>` / `<w:tr>` / run text, deep-copy an element subtree.
- `tracker.py` — the event-aware API below.

Each skill script adds the repo root to `sys.path` via
`Path(__file__).resolve().parents[3]` so imports work from source *and* from an installed
plugin. **Open item for sub-project #5:** the two-plugin split must decide how shared
`lib/` code is packaged into each plugin (vendor a copy, or make it pip-installable). Not
a blocker for #1/#2 (single plugin, `source: "./"`).

### API

```
locate_tracker(chapter_or_series) -> {file_id, kind: "chapter"|"series", folder_id}
    Resolve the folder under Chapters/ or Online/ by name (case-insensitive, exact),
    find its "Event Tracker.docx". kind drives in-person vs online mode downstream.

list_events(doc) -> [{title, heading, date, anchor_element_index}]
    Parse all event sections in document order.

read_event(doc, event) -> {details: {field: value}, phases: [{name, tasks: [...] }]}
    event matches by title (case-insensitive substring), or the literal "next"
    (soonest future DATE & TIME), or "latest".

clone_example_section(doc) -> element subtree
    Deep-copy the heading + detail table + all phase tables of the canonical example
    section. Returns detached XML ready to fill and append.

write_event(doc, fields, due_dates) -> doc
    Fill a cloned section's detail rows + DUE cells + STATUS=Not started, append to the
    body after the last existing event section (before any trailing content).

set_field(doc, event, field, value) -> doc
    Replace the value run of one detail row for one event.

set_due_dates(doc, event, due_dates) -> doc
    Rewrite DUE cells for one event's phase tables from a {task -> date} map.
```

Reads/writes are by **label / header text**, never positional index — mirrors the
`clean-data` / `triage-intake` "by header name" discipline so layout tweaks don't break it.

### Date computation (shared rule)

Offsets are derived from the **example section itself**, not hard-coded, so they track the
template if it changes:

```
for each task in the example:
    offset_days[task] = example_task_DUE - example_EVENT_DATE      # e.g. -28, -21, ... 0, +1
new_due[task] = new_EVENT_DATE + offset_days[task]
```

Weekend handling and exact wording stay as-is (no rounding) for v1 — keep it predictable.
`DATE & TIME` parsing accepts the tracker's own format (`Tue · June 24, 2026 · 17:30 —
late`); a small tolerant parser extracts the date.

---

## 4. Skill: `aaif-create-event`

`argument-hint: '<chapter|series> <event title>'` plus event basics.

**Inputs:** chapter or series name, event title, date (+ time), theme/series, venue *or*
platform, speakers, Luma URL, capacity, organizer-on-point. Anything omitted is left as a
`[bracketed]` placeholder for the organizer to fill.

**Behavior:**
1. `locate_tracker(chapter)` → file + mode (chapter ⇒ in-person, series ⇒ online).
2. Download the tracker; abort if an event section with the same title/date already
   exists (dedup guard).
3. `clone_example_section` → fill detail rows from inputs.
4. Compute due-dates from the event date via the shared rule; set all STATUS to
   `Not started`.
5. Append the section, re-upload via `gws`.
6. Print a summary: created section, computed phase dates, and which fields were left as
   placeholders.

**Mode:** in-person clones the IRL example; online clones the online example (no
venue/A-V/food/door rows; platform/join/tech-check/recording/chat-Q&A instead).

---

## 5. Skill: `aaif-update-event`

`argument-hint: '<chapter|series> <event> — <change in plain language>'`

A **change-driven** editor, not a fixed pipeline. The organizer states the change; the
skill maps it to tracker edits.

**Behavior:**
1. Locate tracker + `read_event` for the named event.
2. Interpret the requested change → one or more field edits:
   - add/replace **speaker** → edit `SPEAKER(S)`
   - change **date/time** → edit `DATE & TIME` **and** `set_due_dates` (recompute every
     phase date from the new date)
   - change **venue / platform / capacity / theme / Luma** → edit that detail row
3. Apply edits via `set_field` / `set_due_dates`, re-upload.
4. **Flag stale downstream assets** (do not regenerate): report which artifacts now
   reference outdated info — e.g. "date changed ⇒ square banner, Luma cover, announcement
   & carousel copy, day-of slides are now stale; re-run those skills." Regeneration is the
   organizer's explicit next step (and lands when sub-project #3 makes those skills
   file-aware).

---

## 6. Skill: `aaif-event-status`

`argument-hint: '<chapter|series> [<event>]'`

**Behavior:**
1. Locate tracker; `list_events` (+ optional single-event filter).
2. For each task across phase tables, classify against **today** using the task's DUE and
   STATUS: `overdue` (DUE < today, STATUS ≠ Done), `due-soon` (DUE within 7 days, not
   Done), `done`, `upcoming`.
3. Output a digest: per event, the overdue and due-soon tasks grouped by OWNER, plus a
   one-line health summary (e.g. "3 overdue, 5 due this week"). Read-only — never writes.

This is the `triage-intake` pattern applied to event tasks.

---

## 7. Shared conventions (repo-wide, established here)

- **Arguments:** every event-scoped skill takes `<chapter|series> <event>` first — the
  first argument resolves against `Chapters/` *or* `Online/`; details flow from the
  tracker. Explicitly-passed values override what's read.
- **Mode auto-detection:** chapter (under `Chapters/`) ⇒ in-person; series (under
  `Online/`) ⇒ online. No manual `--mode` needed; an override flag is allowed but not
  required.
- **Drive access:** via the `gws` CLI (prereq: `gws-cli-access`), through `lib/aaif_meetups/gws.py`.
- **By-label, never positional:** all docx reads/writes match on label/header text.

---

## 8. Risks & open items

1. **docx section cloning in raw OOXML is the hard part.** Deep-copying a heading +
   multiple tables and re-appending must preserve numbering/style refs and not corrupt the
   doc. *Mitigation:* `office.py` clones whole `<w:tbl>`/`<w:p>` elements verbatim
   (no reconstruction); round-trip every generated doc through a load/parse check before
   upload; add fixture-based tests (section 9). If raw-XML proves too brittle in
   implementation, revisit the stdlib-only constraint with the user before adding a dep.
2. **Tolerant date parsing** of the tracker's prose date format — covered by unit tests on
   real strings.
3. **Shared-`lib/` packaging** under the future two-plugin split — flagged for #5; not a
   blocker now.
4. **Existing chapters' example sections** may have drifted from the master. `create-event`
   clones whatever the local tracker's example section is; if a tracker lacks one, fall
   back to the master template's example section.

---

## 9. Testing

Stdlib `unittest`, fixture-driven, no Drive calls in tests:
- Check in a small fixture `Event Tracker.docx` (IRL + online) under
  `lib/aaif_meetups/tests/fixtures/`.
- `tracker-io`: round-trip read → write → read; field edits; due-date math (golden values
  for a known event date); date-parser cases; "next"/"latest" selection.
- Each skill exposes a pure core (compute + docx-transform) separate from the Drive I/O,
  so the core is unit-tested offline (same split as `create_chapter.py`'s
  `--rebrand-local`). A `--dry-run` plans without writing; a `--local <path>` runs the
  transform on a local docx for testing.

---

## 10. Build order (within this spec)

1. `lib/aaif_meetups/`: `gws.py` (extract from existing scripts), `office.py`, `tracker.py` + tests.
2. `aaif-event-status` (read-only — exercises `tracker-io` reads with zero write risk).
3. `aaif-create-event` (clone/fill/date-stamp/append).
4. `aaif-update-event` (field edits + date recompute + stale-asset flagging).
5. Refactor `create_chapter.py` / `create_series.py` to import `lib/aaif_meetups/gws.py`
   (remove the duplicated helpers) — opportunistic cleanup, since we're touching that code.
