#!/usr/bin/env python3
"""Validate the repository PR-body contract.

Usage:
  PR_BODY='...' python .github/scripts/check_pr_contract.py
  python .github/scripts/check_pr_contract.py --body-file /path/to/body.md
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


ISSUE_RE = re.compile(r"(?im)^\s*(?:-\s*)?(?:closes|fixes|resolves)\s+#(\d+)\s*$")
INCLUDED_RE = re.compile(r"(?im)^\s*\*\*Included\*\*\s*$")
EXCLUDED_RE = re.compile(r"(?im)^\s*\*\*Not included\*\*\s*$")
VALIDATION_RE = re.compile(r"(?im)^\s*##\s+Validation\s*$")


def validate_pr_body(body: str) -> list[str]:
    """Return human-readable contract violations; an empty list means valid."""
    missing: list[str] = []

    if not ISSUE_RE.search(body):
        missing.append("issue linkage")
    if not INCLUDED_RE.search(body):
        missing.append("scope included section")
    if not EXCLUDED_RE.search(body):
        missing.append("scope excluded section")
    if not VALIDATION_RE.search(body):
        missing.append("validation section")

    issue_numbers = ISSUE_RE.findall(body)
    if len(issue_numbers) != 1:
        missing.append("exactly one issue linkage")

    return missing


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an Anveshan PR body.")
    parser.add_argument("--body-file", type=Path, help="Read the PR body from a file.")
    args = parser.parse_args()

    if args.body_file:
        body = args.body_file.read_text(encoding="utf-8")
    else:
        body = os.environ.get("PR_BODY", "")

    violations = validate_pr_body(body)
    if violations:
        raise SystemExit("PR contract failed: " + ", ".join(violations))

    issue_number = ISSUE_RE.search(body).group(1)
    print(f"PR contract: PASS (linked issue #{issue_number})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
