---
name: aaif-update-event
description: Apply a change to an existing AAIF event (chapter or series) — edit detail fields like speakers/venue/capacity, or move the date and recompute all task due-dates, then flag which marketing/banner assets are now stale. Use when asked to update/change/edit an event's details or date.
argument-hint: '<chapter|series> <event> [--set "LABEL=value"] [--date "..."]'
---

# AAIF Update Event

Change-driven editor for one event in a chapter/series `Event Tracker.docx`. State the
change; the script edits the right detail fields. If you move the date, every phase task
DUE date is recomputed (clock-time day-of tasks are left alone). It reports which
downstream assets (banner, Luma cover, posts, slides) are now stale so you can re-run
those skills — it does not regenerate them.

**You (the agent) drive Google Drive via the `gws` CLI; the Python script only does the
deterministic docx edit on a local file.** Prereq: `gws` installed and authenticated
(`gws-cli-access`).

## Steps

1. **Locate + download the tracker** (Chapters parent `1IQ1K7aVOKUUkxAcfLuNjdETEnmavvtjx`,
   Online parent `1g2vHrqDHfh9wBkDJryJIl8wqXA4J-d4i`; see `aaif-event-status` for the
   `gws drive files list` queries):

   ```
   gws drive files get --params '{"fileId":"<DOC_ID>","alt":"media"}' --output tracker.docx
   ```

2. **Apply the change (deterministic, local):**

   ```
   # add/replace a speaker
   python skills/aaif-update-event/scripts/update_event.py tracker.docx "Agentic AI Night" \
     --set "SPEAKER(S)=Jane Doe (Agent Infra)"

   # move the date (recomputes all due-dates from the original date)
   python skills/aaif-update-event/scripts/update_event.py tracker.docx "Agentic AI Night" \
     --date "Wed · July 8, 2026 · 17:30 — late"
   ```
   The event argument matches a case-insensitive title substring, or `next` / `latest`.
   Detail labels: EVENT TITLE, DATE & TIME, LOCATION / CITY, VENUE, THEME / SERIES,
   FORMAT(S), SPEAKER(S), LUMA URL, CAPACITY / RSVPS, ORGANIZER ON POINT.

3. **Upload it back:**

   ```
   gws drive files update --params '{"fileId":"<DOC_ID>"}' --upload tracker.docx \
     --upload-content-type application/vnd.openxmlformats-officedocument.wordprocessingml.document
   ```

The script prints the stale-asset list in step 2 — surface that so the organizer knows
which content/banner skills to re-run.
