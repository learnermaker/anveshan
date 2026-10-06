"""Run the origami goal build against the real model (live).

Usage (worktree root):
    python tools/run_goal_build.py

Requires GEMINI_API_KEY in .env and media in tracks/cases/origami/media/cache/.
Writes built artifacts to tracks/cases/origami/knowledge/ and var/data/runs/origami/.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tracks" / "track-a" / "src", ROOT / "tracks" / "common"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tracks.common.models import load_dotenv
from tracks.common.runtime import RunContext
from track_a.api import build_case

load_dotenv(ROOT / ".env")

case_dir = ROOT / "tracks" / "cases" / "origami"
ctx = RunContext.create(case_dir, ROOT / "var" / "data", "live")
print("Building origami goal (live)...")
h = build_case(case_dir, ctx)
print(f"Built: {h.case_id} versions={h.versions}")
if h.warnings:
    print(f"Warnings: {h.warnings}")

goal = h.goal
if goal:
    states = goal.payload["states"]
    print(f"\nStates ({len(states)}):")
    for s in states:
        idx = s["index"]
        name = s["name"]
        start = s["start_sec"]
        end = s["end_sec"]
        props = s["properties"]
        print(f"  R{idx}  {name:30s}  [{start:.0f}-{end:.0f}s]  {props}")
    fi = goal.payload["final_state_index"]
    ki = goal.payload["key_state_index"]
    print(f"\nFinal state: R{fi}, Key state: R{ki}")
    print(f"\nRun keys: {h.versions}")
    assets = case_dir / "knowledge" / "goal_assets"
    if assets.exists():
        print(f"\nAssets written: {list(assets.iterdir())}")
