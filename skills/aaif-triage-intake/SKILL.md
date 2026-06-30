---
name: aaif-triage-intake
description: Triage new AAIF community intake submissions (organizers, hosts/venues, speakers) from the Intake Ops sheet — summarize who's awaiting review, assess fit, and draft next-step outreach. Use when asked to review/triage new applicants, check the intake queue, or produce an intake digest.
argument-hint: "[organizers|hosts|speakers]"
---

# Triage AAIF Intake

Review the people who applied through the **"AAIF Community — Get Involved"** form
and decide what happens next. The form feeds the **AAIF Community Intake Ops**
sheet (id `1cWkjCI5AGK9RX_fs23P5jRA4I2nixgnHuapvwHseZ5o`), which auto-routes each
submission to the **Organizers**, **Hosts**, or **Speakers** tab. Submissions
land automatically; this skill is the human review loop on top of them.

Prereq: the `gws` CLI must be installed and authenticated (see the user's
`gws-cli-access` memory). See the user's `aaif-intake-ops-sheet` memory for the
sheet's structure.

## Status model (drives the queue and the sheet's cell colors)

The five Status values (dropdown on column A, matched exactly by the sheet's
whole-row colors): `New` (blue) → `In progress` (orange) → `Accepted` (green) /
`Denied` (maroon); `Inactive` (gray). A **blank** Status cell is treated as `New`.
Two overrides beat the status color: a **data error** (missing/invalid email or
broken LinkedIn) paints the row bright red, and an **SLA breach** — a `New`/blank
row older than 1 week (of a 2-week response SLA) — paints it pink. Acting on a row
(moving it off `New`) clears the pink. Each role tab also has `Reviewed by`,
`Reviewed at`, `Decision notes`, and a `Chapter` assignment.

## Procedure

1. **Pull the queue.** Rows needing attention = Status blank / `New` / `In progress`:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/intake.py
   ```
   Add `--json` for structured data, `--all` for every row, or
   `--status Accepted` to filter explicitly. If the user named one type
   (`organizers` / `hosts` / `speakers`), focus there but pull all so counts are right.

2. **Assess fit per applicant**, using these signals (don't over-weight any one):
   - **Organizer** — real ties to a local AI community, has run events before,
     a concrete programming idea, and a city. Watch for a `City` of "Other" with a
     non-obvious location (it's in their text) → note the actual city.
   - **Host** — capacity ≥ 30 (`Holds 30+?`), A/V + wifi, a real company/venue,
     and ideally `Recurring support?`. Logistics gaps are follow-ups, not denials.
   - **Speaker** — talk relevance to AAIF (agents/MCP/infra/applied AI), ships in
     production, and evidence (`Past talks / portfolio`). A thin abstract is a
     follow-up for specifics.

3. **Produce the triage digest** — grouped by tab, and for each applicant give a
   one-line recommendation: **Accept**, **Follow up** (what to ask), or **Pass**
   (why). Lead with the strongest candidates. Keep it skimmable.

4. **Draft outreach where it helps** — don't just judge, move it forward:
   - Speakers worth pursuing → use the **`aaif-speaker-invite`** skill for the DM.
   - An accepted organizer for a city that has **no chapter yet** → suggest running
     **`aaif-create-chapter`** for that city.

5. **Write back only if asked.** Default is read-only. If the user wants to record
   decisions, set `Status` / `Reviewed by` / `Reviewed at` / `Decision notes`
   (and `Chapter`) via `gws sheets spreadsheets values batchUpdate`
   (`valueInputOption: USER_ENTERED`). Resolve the target cell by the row number
   from step 1 and the column's header name — never assume a fixed column letter.

## Digest mode (for automation)

`intake.py --json` is the data source for a future scheduled digest routine
(delivery channel TBD with the user). The same selection logic powers both the
interactive triage and the unattended digest, so they never drift.

## Notes

- The sheet is read by **header name**, not column letter — robust to the form or
  sheet gaining/reordering columns. Keep that property in any edits here.
- `Other:` responses to "What brings you here?" match no tab and won't appear in
  any queue. If counts look short, check `Form Responses` for unrouted rows.
