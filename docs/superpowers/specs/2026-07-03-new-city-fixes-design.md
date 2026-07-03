# new-city-fixes — design

Branch: `new-city-fixes`. Three parts.

## Part A — `aaif-backup` skill
A new ops skill that snapshots critical AAIF data to local, versioned files.

- **Files:** `skills/aaif-backup/SKILL.md`, `skills/aaif-backup/scripts/backup.py`.
- **Default (no arg):** back up the AAIF Community Intake Ops sheet
  (`1cWkjCI5AGK9RX_fs23P5jRA4I2nixgnHuapvwHseZ5o`), exported Sheet → `.xlsx`.
- **Optional arg:** back up any file — a Drive fileId (native Docs/Sheets/Slides
  exported to `.docx/.xlsx/.pptx`, already-binary files via `alt=media`) or a local
  path (copied).
- **Versioned snapshots, gitignored:** each run writes an immutable
  `backups/<slug>/<UTC-timestamp>.<ext>` under the repo. Never overwrites, so the
  folder is a full version history. `backups/` is added to `.gitignore` so binary
  snapshots never enter the published plugin repo; a tracked `backups/README.md`
  documents the folder and the manual restore path (re-upload the `.xlsx` via `gws`).
- The agent drives `gws`; `backup.py` does the deterministic export/copy + naming.
  Restore is documented, not automated (YAGNI).

## Part B — intake schema edits (dictated verbatim)
Match the sheet's renamed city columns: role tabs now show **City (Existing)** (col G,
submitted dropdown) and **City (New)** (col H, resolved "Other" city). The physical
source column in Form Responses stays **"Resolved City"** — never renamed.

- `skills/aaif-clean-data/scripts/clean.py` — (a) flag message text → "City (New)";
  (b) provenance color constants (VIOLET/AMBER/GREEN, col indices, COLOR_FORMULAS);
  (c) `_conditional_formats()` + `install_colors()`; (d) call `install_colors()` at the
  end of `install_flags()`; (e) `install-colors` subcommand; (f) docstring entry.
- `skills/aaif-clean-data/SKILL.md` — reword resolved-city step (source at CF, shown as
  City (New); City (Existing) = submitted dropdown; City (New) holds net-new only);
  add `install-colors` as a 4th maintenance mode.
- `skills/aaif-triage-intake/scripts/intake.py` — split `"City"` into
  `"City (Existing)", "City (New)"` in each `TABS` entry; digest header shows
  `City (New)` else `City (Existing)`; update the skip-set.

Rules: keep bright-red error rule at top priority (city colors sit below it);
`install_colors` idempotent (matches its own rules by formula); scripts import cleanly.

## Part C — colors + flowchart in the sheet + repo docs
On the Intake Ops **"How to use"** tab (first page, where colors are defined):

- **New colors** in the legend: 🟪 Violet = `Existing (from MLOps)` (prior organizer,
  whole row). New **CITY COLORS** note: 🟨 Amber on *City (New)* = net-new resolved
  city; 🟩 light-green on *City (Existing)* = a real submitted city.
- **HELPER COLUMNS** update: *Resolved City* now surfaces as *City (New)*; *City
  (Existing)* = submitted dropdown.
- **ORGANIZER REVIEW FLOW** (text/cell flowchart):

  ```
  Form submission → New
     └ Review LinkedIn: credible organizer?  — no → Denied
          │ yes
          ▼  Tentative (vetted, not yet accepted)
          ├ Prior organizer, existing chapter (MLOps) → Violet → Accepted (existing MLOps)
          ├ Existing city, net-new → City (Existing) → intro chapter champs → interview → Accepted (after interview)
          └ New city / new chapter → City (New) → interview → Accepted (after interview)
     On final Accept (either) → grant: chapter Drive folder + local-champs channel + guidelines (confirm read & understood)
  ```

- Mirror the color + flow summary into `aaif-triage-intake/SKILL.md`'s Status-model
  section so repo docs match the sheet.

## Commits
1. Part B edits + repo doc/flow updates (`clean.py`, `clean-data/SKILL.md`,
   `intake.py`, `triage-intake/SKILL.md`).
2. `aaif-backup` skill (+ `.gitignore`, `backups/README.md`).

Part C is a live Drive write to the sheet, done after the code lands.
