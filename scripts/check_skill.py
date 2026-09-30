#!/usr/bin/env python3
"""Check that SKILL.md loads as an Agent Skill.

Frontmatter parses, `name` and `description` follow the skill format limits,
and every repository path SKILL.md tells Claude to use exists.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
NAME = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PATH = re.compile(r"`((?:scripts|references|benchmarks|examples)/[\w./-]+)`")


def main() -> int:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        return _fail("SKILL.md has no YAML frontmatter")
    meta = yaml.safe_load(match.group(1))
    errors = []

    name = meta.get("name", "")
    if not NAME.match(name) or len(name) > 64:
        errors.append(f"name {name!r}: lowercase letters, digits and hyphens, at most 64")
    description = meta.get("description", "")
    if not description or len(description) > 1024:
        errors.append(f"description: 1-1024 characters, got {len(description)}")
    if re.search(r"<[a-zA-Z/]", description):
        errors.append("description must not contain XML tags")

    for path in sorted(set(PATH.findall(text))):
        if not (ROOT / path.rstrip("/")).exists():
            errors.append(f"SKILL.md mentions {path}, which does not exist")

    if errors:
        return _fail(*errors)
    print(f"skill ok: {name}")
    return 0


def _fail(*messages: str) -> int:
    for message in messages:
        print(f"error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
