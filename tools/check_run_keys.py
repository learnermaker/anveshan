"""Check run keys in goal artifacts and find matching run directories."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
case_dir = ROOT / "tracks" / "cases" / "origami"
runs_dir = ROOT / "var" / "data" / "runs" / "origami"

# Look at goal_model.v1.json
gm_path = case_dir / "knowledge" / "goal_model.v1.json"
gm = json.loads(gm_path.read_text())
print("goal_model run_keys:", gm.get("run_keys", []))
print("built_with:", json.dumps(gm.get("built_with", {}), indent=2))
print()

# List all run directories
if runs_dir.exists():
    runs = sorted([d for d in runs_dir.iterdir() if d.is_dir()])
    print(f"Total run dirs in var/data/runs/origami: {len(runs)}")
    for d in runs:
        meta_path = d / "run_metadata.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text())
            pv = meta.get("prompt_version", "?")
            pid = meta.get("prompt_id", "?")
            lat = meta.get("latency_ms", "?")
            print(f"  {d.name[:16]}  {pid}@{pv}  {lat}ms")
