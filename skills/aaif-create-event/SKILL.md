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

Prereq: the `gws` CLI must be installed and authenticated (`gws-cli-access`).

## Run

    python skills/aaif-create-event/scripts/create_event.py "<chapter|series>" \
      --title "Eval Night · Builder Series" \
      --date "Wed · August 12, 2026 · 18:00 — late" \
      [--theme "..."] [--venue "..."] [--platform "..."] [--speakers "..."] \
      [--luma "lu.ma/aaif-..."] [--capacity "..."] [--organizer "..."] [--dry-run]

Anything you omit is left as the example's text for you to fill later. Due-dates
keep the template's exact cadence (each task's offset from the event date is preserved).
