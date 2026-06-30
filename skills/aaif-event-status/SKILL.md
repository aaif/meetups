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
