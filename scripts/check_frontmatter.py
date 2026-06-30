#!/usr/bin/env python3
"""Validate the YAML frontmatter of SKILL.md files.

A SKILL.md whose frontmatter fails to parse loads at runtime with *empty
metadata* — every field (including the `description` that drives auto-activation)
is silently dropped. `claude plugin validate` does NOT parse skill frontmatter,
so this hook is the guard — it runs both locally on commit and in CI (the
pre-commit job). Requires PyYAML (pulled in by pre-commit).
"""
import re
import sys

import yaml

FRONTMATTER = re.compile(r"^---\n(.*?)\n---", re.S)


def check(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = FRONTMATTER.match(text)
    if not m:
        return [f"{path}: no `---` YAML frontmatter block at the top of the file"]
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        first = str(e).splitlines()[0]
        return [f"{path}: frontmatter is not valid YAML ({first})"]
    if not isinstance(data, dict):
        return [f"{path}: frontmatter must be a YAML mapping"]
    errors = []
    for field in ("name", "description"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            errors.append(f"{path}: frontmatter is missing a non-empty `{field}`")
    return errors


def main(argv: list[str]) -> int:
    problems = [err for path in argv for err in check(path)]
    for err in problems:
        print(err, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
