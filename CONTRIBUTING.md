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
- **Quote `argument-hint` values fully.** A value like `"<City>" [--slug <x>]`
  (a quoted scalar followed by bare text) is *invalid YAML* — the whole
  frontmatter then fails to parse and the skill loads with empty metadata
  (description dropped, so it never auto-activates). Single-quote the entire
  value instead: `argument-hint: '<City> [--slug <x>]'`.
- Read and write Google Sheets/Drive **by header name / resource lookup**, not by
  fixed column letters, so skills survive layout changes.
- These skills ship with AAIF's own Google resource IDs. If you're adapting them
  for another chapter, change the constants at the top of each `scripts/*.py` and
  the IDs referenced in the `SKILL.md`.

## Checks

This repo ships a [pre-commit](https://pre-commit.com/) config and a `validate`
GitHub Actions workflow. Set up the hooks once:

```bash
pipx install pre-commit        # or: pip install --user pre-commit
pre-commit install             # run the hooks on every commit
pre-commit run --all-files     # run them now against the whole repo
```

The hooks cover JSON/YAML/whitespace hygiene, Ruff (bug-focused lint of the
helper scripts), codespell, gitleaks secret scanning, and a SKILL.md
frontmatter check.

Then validate the manifests — **run both targets**; the marketplace check alone
does *not* parse each skill's frontmatter:

```bash
claude plugin validate .                        # marketplace.json
claude plugin validate ./plugins/aaif-meetups   # plugin.json + every SKILL.md
```

CI runs all of the above on each PR. Finally, install your local copy to try it
live:

```bash
/plugin marketplace add ./           # from the repo root
/plugin install aaif-meetups@aaif
```

## Pull requests

Fork, branch, commit, and open a PR against `main`. Keep changes focused and
explain what a reviewer should check.
