"""Build v2 tabla goal artifacts with the audio model enabled.

Writes v2 knowledge artifacts to tracks/cases/tabla/knowledge/ and promotes
the Flash-Lite golden run to tracks/cases/tabla/runs/golden/.
Live call budget: 1 audio call.

Usage: python tools/build_tabla_v2.py
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tracks" / "track-a" / "src", ROOT / "tracks" / "common"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tracks.common.models import load_dotenv, ModelRegistry
from tracks.common.runtime import RunContext
from track_a.api import build_case

load_dotenv(ROOT / ".env")

case_dir = ROOT / "tracks" / "cases" / "tabla"
data_dir = ROOT / "var" / "data"
data_dir.mkdir(parents=True, exist_ok=True)

# Create RunContext with audio model enabled (live mode)
# Per 00-COMMON.md: audio = gemini-3.5-flash-lite
registry = ModelRegistry({"audio": "gemini-3.5-flash-lite"})
ctx = RunContext.create(case_dir, data_dir, "live", registry=registry)

print("Building tabla v2 goal (live, audio model enabled)...")
try:
    h = build_case(case_dir, ctx)
except Exception as exc:
    print(f"Build failed: {exc}")
    sys.exit(1)

print(f"Built: case_id={h.case_id}")
if h.warnings:
    for w in h.warnings:
        print(f"  WARNING: {w}")

goal = h.goal
if goal:
    payload = goal.payload
    timbre = payload.get("timbre")
    print(f"\nTimbre: k={timbre['k'] if timbre else None}, "
          f"silhouette={timbre['silhouette'] if timbre else None}")
    print(f"Bols status: {payload.get('bols_status')}")
    if payload.get("class_display"):
        print(f"Class display: {payload['class_display']}")
    print(f"Strokes: {len(payload.get('onsets', []))}")
    print(f"Run keys: {h.versions}")

# Promote runs to golden
run_keys = getattr(h, "versions", [])
if not run_keys:
    print("\nNo run keys to promote")
else:
    src_run_dir = data_dir / "runs" / "tabla"
    golden_dir = case_dir / "runs" / "golden"
    golden_dir.mkdir(parents=True, exist_ok=True)
    promoted = []
    if src_run_dir.exists():
        for rk in run_keys:
            # Run keys are the replay filenames stored in the run store
            for f in src_run_dir.glob(f"*{rk}*"):
                dst = golden_dir / f.name
                shutil.copy2(f, dst)
                promoted.append(f.name)
                print(f"Promoted {f.name} -> golden/")
    if not promoted:
        print(f"Run store {src_run_dir}: no matching files for keys {run_keys}")
        # Try scanning for any recent json files
        if src_run_dir.exists():
            recent = sorted(src_run_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]
            if recent:
                print(f"Recent files in run store: {[f.name for f in recent]}")
                # Promote the most recent ones (likely from this build)
                for f in recent:
                    dst = golden_dir / f.name
                    shutil.copy2(f, dst)
                    promoted.append(f.name)
                    print(f"Promoted {f.name} -> golden/")

print(f"\nDone. Promoted {len(promoted)} run file(s) to golden/.")
