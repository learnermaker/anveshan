#!/usr/bin/env python3
"""Summarise Gemini token usage recorded with each live run (docs/architecture/token-economy.md).

Scans run directories (<root>/**/<replay_key>/{run_metadata,raw_response}.json) and groups by
model and prompt. Runs recorded before usage capture (2026-10-07) have no counts and are listed
as "no usage" so the report never guesses.

Usage: .venv/Scripts/python tools/token_report.py [ROOT ...]   (default: var tracks/cases)
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ("prompt_token_count", "candidates_token_count", "thoughts_token_count", "cached_content_token_count", "total_token_count")


def scan(roots: list[Path]) -> dict[tuple[str, str], dict]:
    groups: dict[tuple[str, str], dict] = defaultdict(lambda: {"runs": 0, "no_usage": 0, "images": 0, **{f: 0 for f in FIELDS}})
    for root in roots:
        for raw_path in root.rglob("raw_response.json"):
            meta_path = raw_path.with_name("run_metadata.json")
            if not meta_path.exists():
                continue
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                raw = json.loads(raw_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            g = groups[(meta.get("model_id", "?"), f"{meta.get('prompt_id', '?')}@{meta.get('prompt_version', '?')}")]
            g["runs"] += 1
            g["images"] += sum(1 for d in meta.get("input_digests") or [] if str(d).startswith("ImagePart:"))
            usage = raw.get("usage") if isinstance(raw, dict) else None
            if not usage:
                g["no_usage"] += 1
                continue
            for f in FIELDS:
                g[f] += int(usage.get(f, 0) or 0)
    return groups


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv] or [ROOT / "var", ROOT / "tracks" / "cases"]
    groups = scan([r for r in roots if r.exists()])
    if not groups:
        print("No runs found.")
        return 0
    print(f"{'model':<26} {'prompt':<36} {'runs':>5} {'no usage':>8} {'img/run':>7} {'in/run':>8} {'out/run':>8} {'think/run':>9} {'cached':>8}")
    totals = {f: 0 for f in FIELDS}
    for (model, prompt), g in sorted(groups.items()):
        n = g["runs"] - g["no_usage"]
        per = (lambda f: g[f] // n) if n else (lambda f: 0)
        print(f"{model[:26]:<26} {prompt[:36]:<36} {g['runs']:>5} {g['no_usage']:>8} {g['images'] / g['runs']:>7.1f} "
              f"{per('prompt_token_count'):>8} {per('candidates_token_count'):>8} {per('thoughts_token_count'):>9} {g['cached_content_token_count']:>8}")
        for f in FIELDS:
            totals[f] += g[f]
    print(f"\nTotals with usage recorded: input {totals['prompt_token_count']}, output {totals['candidates_token_count']}, "
          f"thinking {totals['thoughts_token_count']}, cached {totals['cached_content_token_count']}, all {totals['total_token_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
