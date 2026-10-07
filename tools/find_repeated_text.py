#!/usr/bin/env python3
"""List paragraphs and list items (90+ chars) repeated across tracked Markdown files.

A report, not a CI gate: some repeats are required in place (tool discovery metadata, short checklists).
Everything else should be stated once and linked (AGENTS.md, documentation rules).

Usage: .venv/Scripts/python tools/find_repeated_text.py [REPO_ROOT]
"""

import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
files = [f for f in subprocess.run(["git", "ls-files", "*.md"], cwd=root, capture_output=True, text=True).stdout.split("\n")
         if f and not f.startswith("screenshots/")]
paras = defaultdict(set)
for f in files:
    try:
        t = (root / f).read_text(encoding="utf-8-sig")
    except Exception:
        continue
    for block in re.split(r"\n\s*\n", t):
        lines = block.split("\n") if block.lstrip().startswith(("-", "*", "|", "1.")) else [block]
        for line in lines:
            n = re.sub(r"[`*_>#|\-\s]+", " ", line).strip().lower()
            if len(n) >= 90:
                paras[n].add(f)
groups = defaultdict(list)
for p, fs in paras.items():
    if len(fs) > 1:
        groups[tuple(sorted(fs))].append(p)
for fs, ps in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    print(f"\n## {len(ps)} shared lines: " + " | ".join(fs))
    for p in ps[:3]:
        print("   - " + p[:140])
