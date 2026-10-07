#!/usr/bin/env python3
"""Fail when two tracked files have identical content (single-copy rule, AGENTS.md).

Keep one canonical file and link to it: an import or relative path in code, a pointer
(path + sha256) for pinned data, or a Markdown link in docs. Intentional exceptions are
listed as glob patterns in .github/duplicate-allowlist.txt, each with a reason.

Usage: python .github/scripts/check_duplicates.py
"""

from __future__ import annotations

import fnmatch
import hashlib
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST = ROOT / ".github" / "duplicate-allowlist.txt"


def allowed_patterns() -> list[str]:
    if not ALLOWLIST.exists():
        return []
    lines = ALLOWLIST.read_text(encoding="utf-8").splitlines()
    return [ln.split("#", 1)[0].strip() for ln in lines if ln.split("#", 1)[0].strip()]


def main() -> int:
    files = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True).stdout.decode("utf-8").split("\0")
    files = [f for f in files if f and (ROOT / f).is_file()]
    patterns = allowed_patterns()
    files = [f for f in files if not any(fnmatch.fnmatch(f, p) for p in patterns)]
    groups: dict[str, list[str]] = defaultdict(list)
    for f in files:
        data = (ROOT / f).read_bytes().replace(b"\r\n", b"\n")  # CRLF and LF copies are still copies
        if data.strip():
            groups[hashlib.sha256(data).hexdigest()].append(f)
    dupes = [sorted(g) for g in groups.values() if len(g) > 1]
    if not dupes:
        print(f"Duplicate files: PASS ({len(files)} tracked files checked)")
        return 0
    print("Duplicate files found. Keep one canonical copy and link to it (see AGENTS.md, single-copy rule):")
    for g in sorted(dupes):
        print("  - " + "\n    ".join(g))
    return 1


if __name__ == "__main__":
    sys.exit(main())
