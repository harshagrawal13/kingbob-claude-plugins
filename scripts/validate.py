#!/usr/bin/env python3
"""Validate plugin manifests and skill frontmatter."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors = []


def err(msg: str) -> None:
    errors.append(msg)


# --- manifests ---
plugin_path = ROOT / ".claude-plugin" / "plugin.json"
marketplace_path = ROOT / ".claude-plugin" / "marketplace.json"

try:
    plugin = json.loads(plugin_path.read_text())
except Exception as e:  # noqa: BLE001
    err(f"{plugin_path}: invalid JSON ({e})")
    plugin = {}

try:
    marketplace = json.loads(marketplace_path.read_text())
except Exception as e:  # noqa: BLE001
    err(f"{marketplace_path}: invalid JSON ({e})")
    marketplace = {}

for field in ("name", "description", "version"):
    if not plugin.get(field):
        err(f"plugin.json: missing required field '{field}'")

version = plugin.get("version", "")
if version and not re.fullmatch(r"\d+\.\d+\.0", version):
    err(f"plugin.json: version '{version}' must match X.Y.0 (no patch slot)")

marketplace_names = {p.get("name") for p in marketplace.get("plugins", [])}
if plugin.get("name") and plugin["name"] not in marketplace_names:
    err(f"marketplace.json: no plugin entry named '{plugin['name']}'")

# --- skills ---
skills_dir = ROOT / "skills"
skill_dirs = sorted(d for d in skills_dir.iterdir() if d.is_dir()) if skills_dir.is_dir() else []
if not skill_dirs:
    err("skills/: no skill directories found")

for skill_dir in skill_dirs:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        err(f"{skill_dir}: missing SKILL.md")
        continue
    text = skill_md.read_text()
    m = re.match(r"\A---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        err(f"{skill_md}: missing YAML frontmatter block")
        continue
    front = m.group(1)
    fields = dict(
        (k.strip(), v.strip())
        for k, _, v in (line.partition(":") for line in front.splitlines())
        if _
    )
    if fields.get("name") != skill_dir.name:
        err(f"{skill_md}: frontmatter name '{fields.get('name')}' != directory '{skill_dir.name}'")
    if not fields.get("description"):
        err(f"{skill_md}: missing 'description' in frontmatter")

if errors:
    print("FAIL:")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print(f"OK: plugin '{plugin.get('name')}' v{version}, {len(skill_dirs)} skill(s) validated")
