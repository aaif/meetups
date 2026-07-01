# AAIF Meetups Toolkit

Agent Skills for running **AAIF (Agentic AI Foundation)** in‑person and online
meetups — from writing the LinkedIn announcement to spinning up a brand‑new city
chapter or online event series.

Packaged as a **Claude Code plugin** (and a one‑plugin marketplace) so any
organizer can install the whole toolkit in two commands. The skills are plain
[Agent Skills](https://code.claude.com/docs/en/skills) (`SKILL.md` files), so they
also work in claude.ai and the Claude Agent SDK — see [Using in other tools](#using-in-other-tools).

---

## Install (Claude Code)

```bash
/plugin marketplace add aaif/meetups
/plugin install aaif-meetups@aaif
```

`marketplace add aaif/meetups` reads `.claude-plugin/marketplace.json` from this
repo; `@aaif` is the marketplace name. After installing, the skills auto‑activate
when you describe a matching task (e.g. “draft the announcement post for our July
meetup”), or invoke one explicitly with `/aaif-meetups:<skill>`.

---

## What's inside

### ✍️ Content skills — no setup required
Pure writing skills. They take the event details you give them and produce copy.

| Skill | What it writes |
|---|---|
| `aaif-announcement-post` | LinkedIn launch post for when RSVPs open |
| `aaif-carousel-copy` | 6‑slide LinkedIn carousel announcing a meetup |
| `aaif-luma-description` | Luma event‑page description |
| `aaif-speaker-invite` | Warm speaker‑invite DM / email |
| `aaif-speaker-bio` | 60–80 word speaker bio + one‑liner |
| `aaif-dayof-slides` | Slide text for the “Day of Event” deck |
| `aaif-attendee-reminder` | Pre‑event reminder to people who RSVP'd |
| `aaif-recap-post` | Post‑event LinkedIn recap (within 48h) |

> **Attendee legal defaults.** The attendee‑facing skills (`aaif-announcement-post`,
> `aaif-luma-description`, `aaif-attendee-reminder`) append two standing links by
> default — the [Code of Conduct](https://events.linuxfoundation.org/about/code-of-conduct/)
> and [Privacy Policy](https://www.linuxfoundation.org/legal/privacy-policy).
> Running your own chapter? Swap these URLs in each skill's `SKILL.md`.

### 🛠️ Ops skills — need Google Workspace access
These drive Google Drive / Sheets through the `gws` CLI (see below).

| Skill | What it does | Touches |
|---|---|---|
| `aaif-create-chapter` | Clone the **TemplateCity** folder and rebrand every asset for a new city | Google Drive |
| `aaif-create-online-series` | Clone the **TemplateSeries** folder under **Online/** and rebrand it for a new online series | Google Drive |
| `aaif-triage-intake` | Summarize who's awaiting review in the Community Intake sheet + draft outreach | Google Sheets |
| `aaif-clean-data` | Normalize/flag data quality in the Intake sheet (LinkedIn, casing, City=Other…) | Google Sheets |

> **Heads up — these ship with AAIF's own IDs.** The ops skills reference AAIF's
> Google resources (the Chapters Drive, the Intake Ops spreadsheet ID, Luma slug
> conventions). To run your own chapter, fork and edit the constants at the top of
> each skill's `scripts/*.py` and the IDs in its `SKILL.md`.

---

## Google Workspace access (for the ops skills)

The ops skills read and write Google Drive/Sheets. Pick **one** of these ways to
give your agent access. The bundled scripts call the **`gws` CLI** out of the box;
the connector and MCP options are alternatives if you'd rather have Claude do the
Drive/Sheets work through tools (you then follow the skill steps interactively
instead of running the script).

### Option A — `gws` CLI  *(what the scripts use)*
The **`gws` CLI** (a Google Workspace command‑line tool) is what the scripts call.
Install it, then authenticate with one of:

- **Interactive OAuth:** `gws auth login`
- **Credentials file:** set `GOOGLE_WORKSPACE_CLI_CREDENTIALS_FILE=/path/to/oauth_credentials.json`
- **Pre‑obtained token:** set `GOOGLE_WORKSPACE_CLI_TOKEN=<access_token>`
- **Client app:** set `GOOGLE_WORKSPACE_CLI_CLIENT_ID` and `GOOGLE_WORKSPACE_CLI_CLIENT_SECRET`, then `gws auth login`

On your Google Cloud project, enable the **Sheets**, **Docs**, **Slides**,
**Drive**, and **Forms** APIs.

**OAuth scopes.** Grant **read-write** scopes for anything you write to —
read-only access passes the verify step below but then fails on the first write
(form responses are read-only by nature, hence the `.readonly` scope). The
bundled scripts use only the Sheets and Drive scopes; the Docs, Slides, and Forms
scopes are for operating on those assets directly — the chapter/series source docs
and decks, and the intake form (e.g. via Claude's Google connector or an MCP
server):

- `https://www.googleapis.com/auth/spreadsheets` — read/write the intake sheet *(scripts)*
- `https://www.googleapis.com/auth/drive` — copy, create, and update Drive files,
  incl. chapter/series asset clones *(scripts)*
- `https://www.googleapis.com/auth/documents` — read/edit chapter/series Docs
- `https://www.googleapis.com/auth/presentations` — read/edit day-of / series Slides
- `https://www.googleapis.com/auth/forms.body` — read/edit the intake form
- `https://www.googleapis.com/auth/forms.responses.readonly` — read form responses

Verify with:

```bash
gws sheets spreadsheets get --params '{"spreadsheetId":"<your-sheet-id>"}'
```

### Option B — Claude's Google Drive connector
claude.ai and Claude Code can connect Google Drive/Sheets natively via
**Connectors** (Settings → Connectors → Google Drive). Best when you want Claude to
pull event details from Drive docs or read a sheet conversationally. To use it with
the ops skills, run the skill's steps and let Claude operate the connected tools
rather than invoking the `gws` script.

### Option C — Google Workspace MCP server
Run a Google Workspace **MCP server** and register it with Claude Code:

```bash
claude mcp add google-workspace -- <command to start the server>
# or add it to .mcp.json in your project
```

Claude then reads/writes Sheets and Drive through MCP tools. As with the connector,
follow the skill instructions interactively (the scripts themselves assume `gws`).

---

## Using in other tools

These skills are portable `SKILL.md` files, but not every tool consumes a Claude
Code *plugin*:

- **Claude Code** — install as the plugin above (native).
- **claude.ai / Claude Agent SDK** — zip a skill folder (the dir containing
  `SKILL.md`) and upload it as a Skill.
- **Cursor** — Cursor uses its own `.cursor/rules/*.mdc` format and does **not**
  consume Claude Code plugins. You can copy a `SKILL.md`'s instructions into a
  Cursor rule, but it won't run the bundled scripts the same way.

The portable unit is the `SKILL.md`; the *plugin/marketplace* packaging is
Claude‑Code‑specific.

---

## Repo layout

The repo root is **both** the marketplace and the single plugin — the marketplace
entry's `source` is `"./"`, so there's no extra `plugins/<name>/` nesting.

```
meetups/
├── .claude-plugin/
│   ├── marketplace.json          # one-plugin marketplace ("aaif")
│   └── plugin.json               # plugin manifest (aaif-meetups)
├── skills/
│   ├── aaif-announcement-post/SKILL.md
│   ├── aaif-create-chapter/{SKILL.md, scripts/}
│   └── …  (12 skills total)
└── README.md
```

Bundled scripts are referenced from `SKILL.md` via `${CLAUDE_SKILL_DIR}/scripts/…`
so they resolve correctly once installed.

---

## Contributing

Issues and PRs welcome — new chapter‑ops skills, content variants, and
genericizing the AAIF‑specific IDs into config are all fair game. Keep each skill's
`description` action‑oriented (“Use when asked to …”) so it auto‑activates well.

## License

[MIT](LICENSE) © AAIF
