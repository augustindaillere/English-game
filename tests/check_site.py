#!/usr/bin/env python3
"""Checks the built site in dist/: every board tile has a page and every internal link works."""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"
errors = []

tiles = json.loads((ROOT / "content" / "tiles.json").read_text(encoding="utf-8"))
ids = [t["id"] for t in tiles]
if len(ids) != len(set(ids)):
    errors.append("duplicate tile ids")
for t in tiles:
    if not (DIST / "tiles" / f"{t['id']}.html").exists():
        errors.append(f"missing page for {t['id']}")
    for r in t.get("related", []):
        if r not in ids:
            errors.append(f"{t['id']}: unknown related tile {r}")

for page in DIST.rglob("*.html"):
    for href in re.findall(r'(?:href|src)="([^"#]+)"', page.read_text(encoding="utf-8")):
        if href.startswith(("http://", "https://", "mailto:")):
            continue
        if not (page.parent / href).resolve().exists():
            errors.append(f"{page.relative_to(DIST)}: broken link {href}")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"OK: {len(tiles)} tiles, all internal links valid")
