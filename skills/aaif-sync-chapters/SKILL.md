---
name: aaif-sync-chapters
description: Sync accepted/existing organizers from the Intake Ops sheet into the Chapters List — merge names into each city's Organizers column and add rows for net-new cities. Reports & proposes by default; only writes on explicit approval. Use when asked to sync organizers/chapters or push intake decisions to the chapters list.
argument-hint: "[--write]"
---

# Sync Intake Organizers → Chapters List

Push organizer decisions from the **AAIF Community Intake Ops** sheet
(id `1cWkjCI5AGK9RX_fs23P5jRA4I2nixgnHuapvwHseZ5o`, tab `Organizers`) into the
**AAIF Community Chapters List** (id `18_7aHD45-5NhlN6IZKW2QzswZlDHVb8nBSP7rl5-yWg`,
tab `Chapters & Teams`): every organizer whose Status is **`Accepted`** or
**`Existing (from MLOps)`** must appear in their city row's **Organizers** column,
and cities with no row yet get one appended. The intake sheet is only ever **read**;
all writes go to the chapters list. Idempotent — a second run right after a sync
proposes zero changes.

Prereq: the `gws` CLI must be installed and authenticated (see the user's
`gws-cli-access` memory).

## The flow: report → approve → write

1. **Report (default, read-only):**
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/sync_chapters.py
   ```
   Shows per-city adds to existing rows (with the exact new B value), proposed
   new city rows (appended row number + Luma slug + whether the page is live),
   near-miss city names, unresolved-city rows, and deduped duplicates. Ends with
   a "No changes needed" line when the sheets are already in sync.

2. **Show the user the proposal** and get explicit approval. Never skip to write.

3. **Write (on approval only):**
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/sync_chapters.py --write
   ```
   Recomputes the proposal from a **fresh read** (a stale proposal is never
   applied), applies everything in **one** `values batchUpdate` (a partial
   failure can't half-sync the sheet), then re-reads and verifies a fresh run
   proposes zero changes (exits non-zero otherwise).

## Sync rules (what the engine does)

- **Status filter is exact-string**: `Accepted` and `Existing (from MLOps)` only.
  (Matching a prefix like `Existing` once missed all 23 MLOps rows.)
- **City resolution per intake row**: `City (New)` wins if non-empty; else
  `City (Existing)` unless it's an `Other…` placeholder; else the row is
  **unresolved** — reported with its free-text answers quoted (and an inferred
  city when the text explicitly names a chapter city), **never written**. The fix
  is to fill `City (New)` on the intake row (see `aaif-clean-data`), then re-run.
- **Merge, don't overwrite**: existing `B` is parsed on `;`, intake names are
  appended only if missing (compared case-, whitespace- and accent-insensitively);
  names already in `B` but absent from intake are left alone (manual entries live
  there). Written values keep original UTF-8 (`Médéric Hurier` stays accented).
- **Near-miss cities** (e.g. intake `Delhi` vs row `Delhi NCR`) are reported, not
  auto-matched — confirm the right row or fix the intake city, never create a
  near-duplicate row.
- **Column C (`Previous MLOps Organizers`) is read-only history — never modified.**
  Its spellings can differ from intake (e.g. "Adam Lite" vs "Adam Liter"); intake
  wins for column B. San Francisco people are **not** mirrored into the Silicon
  Valley row — B follows the intake city; C is where the legacy duplication lives.
- **New city rows** are appended after the last non-empty City row (not at the
  grid bottom): City in A, names joined `"; "` in B, C empty, and
  `https://luma.com/aaif-SLUG` in D (slug = city lowercased, spaces/accents
  removed; same exceptions as `aaif-create-chapter`, e.g. Denver → `aaif-colorado`).
  The report says whether the Luma page is live — page creation is manual, and a
  net-new city still needs its Drive folder/assets: run **`aaif-create-chapter`**
  for it as the follow-up.
- Duplicate intake rows for the same person+city are deduped (first wins, reported).

## Verify

After any run (and after editing the engine):

- The report's intake counts should match a manual count of the sheet's Status
  column; a delta means status strings drifted.
- After `--write`, the built-in re-verify must print
  "Verified: a fresh run proposes zero changes."
- Spot-check one touched row in the sheet: B merged correctly, C and D untouched,
  and the version history shows a single edit for the whole sync.
- Unit tests for the pure merge/slug/near-miss logic:
  ```bash
  python3 ${CLAUDE_SKILL_DIR}/scripts/test_sync_chapters.py
  ```

## Notes

- Both tabs are read by **header name** (`Status`, `Full name`, `City (Existing)`,
  `City (New)`, `Run events before?`, `Why organize / ties`, `City`, `Organizers`),
  never by fixed column letter — the script aborts loudly if a header disappears.
- Quote the tab name in any manual A1 ranges (`'Chapters & Teams'!B11`) — it
  contains `&` and spaces.
- Unresolved rows already hand-placed on the chapters list are flagged
  "no action needed" so they don't nag every run.
