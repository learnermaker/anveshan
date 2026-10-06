"""Promote evaluator run dirs (from all 5 variants) to tracks/cases/origami/runs/golden/
so recorded mode can replay the evaluations.

Usage (worktree root):
    python tools/promote_eval_golden_runs.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tracks" / "track-b" / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

CASE_DIR = ROOT / "tracks" / "cases" / "origami"
SRC_RUNS = ROOT / "var" / "data" / "runs" / "origami"
GOLDEN_ROOT = CASE_DIR / "runs" / "golden"
RESULTS_DIR = ROOT / "var" / "eval" / "origami" / "results"

VARIANTS = ["perfect", "missing_state", "swapped_order", "truncated", "real_learner"]

promoted = 0
skipped = 0

for variant in VARIANTS:
    rpath = RESULTS_DIR / f"{variant}.json"
    if not rpath.exists():
        print(f"  MISSING result for {variant}")
        continue
    result = json.loads(rpath.read_text())
    run_keys = result.get("run_keys", [])
    if not run_keys:
        print(f"  No run_keys in {variant} result")
        continue
    for key in run_keys:
        src = SRC_RUNS / key
        dst = GOLDEN_ROOT / key
        if dst.exists():
            skipped += 1
            continue
        if not src.exists():
            print(f"  MISSING run dir: {key[:16]}... (variant={variant})")
            continue
        shutil.copytree(src, dst)
        promoted += 1
    print(f"  {variant}: {len(run_keys)} run keys processed")

print(f"\nPromoted {promoted} new runs, skipped {skipped} already-present")
print(f"Golden root: {GOLDEN_ROOT}")
