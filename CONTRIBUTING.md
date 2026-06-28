# Contributing

Thanks for helping improve the AAIF Meetups Toolkit. The repo is a Claude Code
**plugin marketplace** — one plugin (`aaif-meetups`) whose skills live under
`plugins/aaif-meetups/skills/`.

## Adding or editing a skill

A skill is a folder with a `SKILL.md` (plus an optional `scripts/` dir):

```
plugins/aaif-meetups/skills/<skill-name>/
├── SKILL.md
└── scripts/            # optional helper scripts
```

`SKILL.md` starts with YAML frontmatter:

```yaml
---
name: aaif-something
description: One line — what it does AND when to use it ("Use when asked to …"),
  so Claude auto-activates it at the right moment.
argument-hint: "<optional> [args]"
---

# Title
Clear, step-by-step instructions…
```

Guidelines:
- **Reference bundled scripts with `${CLAUDE_SKILL_DIR}/scripts/...`**, never a
  hardcoded `.claude/skills/...` path — the variable resolves wherever the skill
  is installed.
- Keep the `description` action-oriented; it's what triggers auto-activation.
- Read and write Google Sheets/Drive **by header name / resource lookup**, not by
  fixed column letters, so skills survive layout changes.
- These skills ship with AAIF's own Google resource IDs. If you're adapting them
  for another chapter, change the constants at the top of each `scripts/*.py` and
  the IDs referenced in the `SKILL.md`.

## Testing

Validate the marketplace + plugin manifests before opening a PR:

```bash
claude plugin validate .
```

Then install your local copy to try it live:

```bash
/plugin marketplace add ./           # from the repo root
/plugin install aaif-meetups@aaif
```

## Pull requests

Fork, branch, commit, and open a PR against `main`. Keep changes focused and
explain what a reviewer should check.
