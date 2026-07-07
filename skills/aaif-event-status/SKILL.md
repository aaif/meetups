---
name: aaif-event-status
description: Report task status for an AAIF chapter or online series — which event tasks are overdue or due soon, grouped by owner, read from the Event Tracker.docx — plus read-only Luma registration stats (going/waitlist/checked-in counts) for pushed events. Use when asked for the status / health / what's-due / RSVP numbers of a chapter or series' events.
argument-hint: '<chapter|series> [event]'
---

# AAIF Event Status

Read-only digest of a chapter or online series' `Event Tracker.docx`: for each event,
the **overdue** and **due-soon** (within 7 days) tasks, grouped by owner.

**You (the agent) drive Google Drive via the `gws` CLI; the Python script only does the
deterministic parsing of a local file.** Prereq: `gws` installed and authenticated
(`gws-cli-access`).

## Steps

1. **Locate the tracker.** A chapter lives under the **Chapters** folder
   (`1IQ1K7aVOKUUkxAcfLuNjdETEnmavvtjx`); an online series under **Online**
   (`1g2vHrqDHfh9wBkDJryJIl8wqXA4J-d4i`). Find the folder, then its `Event Tracker.docx`:

   ```
   gws drive files list --params '{"q":"name = '\''<NAME>'\'' and '\''1IQ1K7aVOKUUkxAcfLuNjdETEnmavvtjx'\'' in parents and trashed=false","fields":"files(id,name)"}'
   # then, with the folder id:
   gws drive files list --params '{"q":"'\''<FOLDER_ID>'\'' in parents and name = '\''Event Tracker.docx'\'' and trashed=false","fields":"files(id)"}'
   ```
   If not found under Chapters, try the Online parent. (Mode is implicit: whichever
   folder it lived in.)

2. **Download it** to a temp path:

   ```
   gws drive files get --params '{"fileId":"<DOC_ID>","alt":"media"}' --output tracker.docx
   ```

3. **Run the digest** (read-only, local):

   ```
   python3 ${CLAUDE_SKILL_DIR}/scripts/event_status.py tracker.docx ["event"]
   ```

Status is computed against today from each task's DUE cell; clock-time day-of tasks and
`Done` tasks are excluded. Nothing is written back — this skill only reads.

## Luma registration stats (read-only)

For events whose tracker LUMA URL holds their event page (written by
`aaif-create-event`'s Luma push), pull the live guest counts — going, pending,
waitlist, invited, declined, checked-in — plus registration state:

```
python3 ${CLAUDE_SKILL_DIR}/scripts/luma_stats.py tracker.docx ["event"]
python3 ${CLAUDE_SKILL_DIR}/scripts/luma_stats.py --url https://luma.com/EVENT_SLUG
```

The script detects whether Luma is connected (that calendar's API key in
`LUMA_API_KEY` or keychain item `luma-api-key`; see `aaif-create-event` for
setup); when it isn't, it skips the stats with a note — the task digest above
still works, and the user can read the numbers off the event page manually.
This is strictly read-only —
it never writes to Luma, the tracker, or any sheet, and Luma data is never fed
back into the Intake Ops sheet. Use the numbers for the day-of slides
(`aaif-dayof-slides`) and the recap post (`aaif-recap-post`).
