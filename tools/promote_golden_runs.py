"""Promote the accepted goal-build run dirs to tracks/cases/origami/runs/golden/
and verify that recorded mode reproduces byte-identical artifacts.

Usage (worktree root):
    python tools/promote_golden_runs.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tracks" / "track-a" / "src", ROOT / "tracks" / "common"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tracks.common.models import load_dotenv

load_dotenv(ROOT / ".env")

case_dir = ROOT / "tracks" / "cases" / "origami"
src_runs = ROOT / "var" / "data" / "runs" / "origami"
golden_root = case_dir / "runs" / "golden"

# Read the accepted run keys from goal_model.v1.json
gm_path = case_dir / "knowledge" / "goal_model.v1.json"
gm = json.loads(gm_path.read_text())
run_keys = gm.get("built_with", {}).get("run_keys", [])
if not run_keys:
    # Try top-level
    run_keys = gm.get("run_keys", [])
print(f"Found {len(run_keys)} run keys to promote")

# Copy runs
golden_root.mkdir(parents=True, exist_ok=True)
promoted = []
for key in run_keys:
    src = src_runs / key
    dst = golden_root / key
    if not src.exists():
        print(f"  MISSING: {key}")
        continue
    if dst.exists():
        print(f"  already exists: {key[:16]}...")
        promoted.append(key)
        continue
    shutil.copytree(src, dst)
    print(f"  promoted: {key[:16]}...")
    promoted.append(key)
print(f"Promoted {len(promoted)}/{len(run_keys)} runs to {golden_root}")

# Verify recorded mode reproduces byte-identical artifacts
print("\nVerifying recorded replay...")
from tracks.common.runtime import RunContext
from track_a.api import build_case

# Clean up the current knowledge dir so we rebuild from scratch in recorded mode
existing_assets = list((case_dir / "knowledge" / "goal_assets").glob("*.jpg")) if (case_dir / "knowledge" / "goal_assets").exists() else []
existing_json = [
    case_dir / "knowledge" / "goal_model.v1.json",
    case_dir / "knowledge" / "criterion_map.v1.json",
    case_dir / "knowledge" / "knowledge_package.v1.json",
]

# Save checksums of the live build artifacts
live_sums = {}
for p in existing_assets:
    live_sums[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
for p in existing_json:
    if p.exists():
        live_sums[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()

# Remove current knowledge artifacts (except golden runs and source)
for p in existing_assets:
    p.unlink(missing_ok=True)
for p in existing_json:
    if p.exists():
        p.unlink()
practice_jsons = [
    case_dir / "practice" / "observers.v1.json",
    case_dir / "practice" / "practice_task.v1.json",
    case_dir / "practice" / "rubric.v1.json",
]
for p in practice_jsons:
    if p.exists():
        p.unlink()
print("  Removed live artifacts, running in recorded mode...")

ctx = RunContext.create(case_dir, ROOT / "var" / "data_rec", "recorded")
try:
    h = build_case(case_dir, ctx)
    print(f"  Recorded build: {h.case_id} versions={h.versions}")
    # Compare checksums
    replay_assets = list((case_dir / "knowledge" / "goal_assets").glob("*.jpg")) if (case_dir / "knowledge" / "goal_assets").exists() else []
    replay_json = [
        case_dir / "knowledge" / "goal_model.v1.json",
        case_dir / "knowledge" / "criterion_map.v1.json",
        case_dir / "knowledge" / "knowledge_package.v1.json",
    ]
    all_match = True
    for p in replay_assets:
        rec_sum = hashlib.sha256(p.read_bytes()).hexdigest()
        live_sum = live_sums.get(p.name, None)
        if live_sum is None:
            print(f"  NEW file (not in live build): {p.name}")
        elif rec_sum == live_sum:
            print(f"  MATCH: {p.name}")
        else:
            print(f"  MISMATCH: {p.name}")
            all_match = False
    for p in replay_json:
        if not p.exists():
            continue
        rec_sum = hashlib.sha256(p.read_bytes()).hexdigest()
        live_sum = live_sums.get(p.name, None)
        if live_sum is None:
            print(f"  NEW file: {p.name}")
        elif rec_sum == live_sum:
            print(f"  MATCH: {p.name}")
        else:
            print(f"  MISMATCH: {p.name}")
            all_match = False
    if all_match:
        print("\nRECORDED REPLAY: byte-identical artifacts confirmed")
    else:
        print("\nRECORDED REPLAY: MISMATCH detected - investigate before committing golden runs")
except Exception as exc:
    print(f"  Recorded build FAILED: {exc}")
