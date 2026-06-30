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

Prereq: the `gws` CLI must be installed and authenticated (`gws-cli-access`).

## Run

    # add/replace a speaker
    python skills/aaif-update-event/scripts/update_event.py "Berlin" "Agentic AI Night" \
      --set "SPEAKER(S)=Jane Doe (Agent Infra)"

    # move the date (recomputes all due-dates)
    python skills/aaif-update-event/scripts/update_event.py "Berlin" "Agentic AI Night" \
      --date "Wed · July 8, 2026 · 17:30 — late"

Detail labels: EVENT TITLE, DATE & TIME, LOCATION / CITY, VENUE, THEME / SERIES,
FORMAT(S), SPEAKER(S), LUMA URL, CAPACITY / RSVPS, ORGANIZER ON POINT.
