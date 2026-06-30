---
name: aaif-create-chapter
description: Create a new AAIF city chapter in the "Chapters" Google Drive by cloning TemplateCity and rebranding all assets. Use when asked to add/launch/set up a new AAIF city, chapter, or location.
argument-hint: '<City Name> [--slug <lumaslug>]'
---

# Create AAIF Chapter

Spin up a new AAIF city "chapter" by cloning the **TemplateCity** folder in the
**Chapters** Google Drive and rebranding every Office file from San Francisco to
the new city. Each chapter folder is the standard template: `Event Tracker.docx`,
`Attendee CRM.xlsx`, and the `Event Name/` + `Banners (...)/` subfolders of `.pptx`
design assets. (The old `SKILLS.md.docx` of paste-into-Claude prompts is retired —
those prompts now live as the `aaif-*` content skills in this repo.)

Prereq: the `gws` CLI must be installed and authenticated (see the user's
`gws-cli-access` memory). All Drive calls go through it.

## What gets replaced (and what does NOT)

The rebrand swaps two tokens and leaves everything else alone. Event-specific
content — dates ("JUNE 24"), speakers ("Maya Chen"), venue, agenda, the SoMa /
"SOUTH OF MARKET" neighbourhood placeholder — is **template content** that
organizers fill per-event later using the `aaif-*` content skills in this repo. Do
not touch it.

| Token in template | Becomes | Notes |
|---|---|---|
| `San Francisco` / `SAN FRANCISCO` | new city, case-matched | contiguous in the clean template |
| `SF` abbreviation (`AAIF · SF`, `SF CHAPTER`, `About the AAIF SF Chapter`, `AAIF SF — Attendee CRM`, doc metadata) | full city name | **UPPER** in all-caps contexts, **Title case** in prose |
| `aaif-sanfrancisco` / `AAIF-SANFRANCISCO` (Luma slug, incl. hyperlink targets) | `aaif-<slug>` / `AAIF-<SLUG>` | see slug rules below |

## Luma slug rules

- Default slug = city lowercased, spaces/accents removed: `New York → newyork`,
  `Mexico City → mexicocity`, `Montréal → montreal`.
- **Exceptions exist** — e.g. **Denver's page lives at `aaif-colorado`**, not
  `aaif-denver`. Always confirm the live page; pass `--slug` to override.
- Live pages resolve at both `https://luma.com/aaif-<slug>` and
  `https://lu.ma/aaif-<slug>`. The design files display the brand form
  `LU.MA / AAIF-<SLUG>`; keep that — only the slug changes.
- The script **cannot create the Luma page** (that's done manually at luma.com).
  It checks whether the page is live and warns if not.

## Procedure

1. **Confirm the city name and slug with the user.** Ask for the exact display
   name (with spaces, e.g. "New York") and whether the Luma page exists / what
   its slug is. If they don't know, the default slug is fine — the script will
   tell you if it's not live.

2. **Dry run first** to surface the slug, Luma status, and any name collision:
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/create_chapter.py \
       --city "New York" --dry-run
   ```
   - If it aborts with "already exists", stop — the chapter is already there.
   - If Luma shows NOT LIVE, tell the user the page needs creating at
     `luma.com/aaif-<slug>` (or that the slug differs — re-run with `--slug`).

3. **Create the chapter:**
   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/create_chapter.py \
       --city "New York"            # add --slug <x> if overriding
   ```
   The script clones TemplateCity → a new `<City>` folder under Chapters, then
   downloads, rebrands, and re-uploads each `.pptx/.docx/.xlsx` in place. It
   prints a tree and flags any file with `!! residual` tokens.

4. **Verify.** Confirm the run printed no `!! residual` flags and report the new
   folder URL to the user. If the Luma page wasn't live, remind them to create it.

## How it works / maintenance

`scripts/create_chapter.py` is the engine. It rebrands at the paragraph level
(concatenate the text runs, transform, write back into the first run) so it is
robust to OOXML run-splitting. The `SF`-abbreviation casing is decided by the
surrounding words. The Drive layer uses `gws` (`files.copy`, `create`, `get`,
`update`).

To validate the engine after any edit, rebrand a throwaway copy of the template
and diff it against an existing chapter (the canonical end-state):
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/create_chapter.py \
    --city "Los Angeles" --rebrand-local /path/to/template-copy
# then compare paragraph text against the real Los Angeles chapter
```

Constants (Chapters parent id, TemplateCity id) live at the top of the script.
The template must stay "clean": `San Francisco` contiguous (no run/paragraph
splits) and the slug normalized to `aaif-sanfrancisco`. If a future template edit
re-introduces a split, the paragraph-level engine still handles it, but the big
stacked title on Carousel slide 2 is intentionally a single adaptive line.
