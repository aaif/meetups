---
name: aaif-create-event
description: Create a new event in an AAIF chapter or online series by cloning the example section in its Event Tracker.docx and stamping all phase task due-dates from the event date. Use when asked to add/schedule/set up a new event for a chapter or series.
argument-hint: '<chapter|series> --title "..." --date "..."'
---

# AAIF Create Event

Add a new event to a chapter/series `Event Tracker.docx`: clone the example event
section, fill the detail block, and compute every phase task's DUE date backward from
the event date (the template's exact cadence is preserved per task). Mode is implicit —
a chapter clones the in-person task set, an online series the online set, because you
download whichever tracker the folder holds.

**You (the agent) drive Google Drive via the `gws` CLI; the Python script only does the
deterministic docx edit on a local file.** Prereq: `gws` installed and authenticated
(`gws-cli-access`).

## Steps

1. **Locate the tracker.** Chapters parent `1IQ1K7aVOKUUkxAcfLuNjdETEnmavvtjx`, Online
   parent `1g2vHrqDHfh9wBkDJryJIl8wqXA4J-d4i`. Find the named folder, then its
   `Event Tracker.docx` id (see `aaif-event-status` for the exact `gws drive files list`
   queries).

2. **Download it:**

   ```
   gws drive files get --params '{"fileId":"<DOC_ID>","alt":"media"}' --output tracker.docx
   ```

3. **Add the event (deterministic, local).** Aborts if the title already exists:

   ```
   # in-person (chapter) tracker
   python skills/aaif-create-event/scripts/create_event.py tracker.docx \
     --title "Eval Night · Builder Series" \
     --date "Wed · August 12, 2026 · 18:00 — late" \
     [--theme ...] [--venue ...] [--location ...] [--speakers ...] \
     [--luma ...] [--capacity ...] [--organizer ...] [--dry-run]

   # online (series) tracker — use --platform / --join, NOT --venue / --location
   python skills/aaif-create-event/scripts/create_event.py tracker.docx \
     --title "..." --date "..." [--platform "Zoom Webinar"] [--join "lu.ma/..."] ...
   ```
   Flags must match the tracker's labels: a chapter tracker has `VENUE` /
   `LOCATION / CITY`; a series tracker has `PLATFORM` / `STREAM / JOIN LINK`. Passing
   a flag whose label doesn't exist in that tracker **aborts loudly** (it is not
   silently dropped). Omitted fields keep the example's text for the organizer to
   fill later. Note: `--luma` sets the displayed URL text only; the clickable Luma
   link target (per chapter/series) is not rewritten here — set it on the Luma page.

4. **Upload it back:**

   ```
   gws drive files update --params '{"fileId":"<DOC_ID>"}' --upload tracker.docx \
     --upload-content-type application/vnd.openxmlformats-officedocument.wordprocessingml.document
   ```

Use `--dry-run` in step 3 first if you want to preview without modifying the local file.
