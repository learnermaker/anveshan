"""Print a summary of evaluation results for all variants."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
results_dir = ROOT / "var" / "eval" / "origami" / "results"
gt_path = ROOT / "tracks" / "track-b" / "eval" / "origami" / "labels" / "synthetic_ground_truth.json"
gt_all = json.loads(gt_path.read_text())
variants = ["perfect", "missing_state", "swapped_order", "truncated", "real_learner"]

def score(result, gt):
    exp = gt["expected"]
    tr = result["trajectory"]
    events = tr["events"]
    fd = events[0] if events else None
    efd = exp["first_divergence"]
    frame_labels = tr["artifacts"]["frame_labels"]
    intervals = gt["state_intervals"]
    hits = total = 0
    for fr in frame_labels:
        truth = next((int(s) for s, ivs in intervals.items() for a, b in ivs if a - 0.5 <= fr["t"] <= b + 0.5), None)
        if truth is None:
            continue
        total += 1
        hits += fr["filtered"] == truth
    fa = round(hits / total, 3) if total else None
    return {
        "frame_state_accuracy": fa,
        "missing_exact": tr["artifacts"]["missing_states"] == exp["missing_states"],
        "order_violations_exact": result["metrics"]["origami.order_violations"]["value"] == exp["order_violations"],
        "final_agrees": tr["final_state"]["reached_by_trajectory"] == exp["final_reached"],
        "first_divergence_kind_agrees": (fd is None and efd is None) or (fd is not None and efd is not None and fd["kind"] == efd["kind"]),
        "first_divergence_abs_error_sec": (round(abs(fd["position"] - efd["position_sec"]), 2) if fd and efd else None),
    }

for v in variants:
    p = results_dir / (v + ".json")
    if not p.exists():
        print(f"{v}: MISSING")
        continue
    r = json.loads(p.read_text())
    gt = gt_all["variants"][v]
    m = r["metrics"]
    traj = r["trajectory"]
    sc = score(r, gt)
    
    final_val = m.get("origami.final_match", {}).get("value")
    order_val = m.get("origami.order_violations", {}).get("value")
    missing_val = m.get("origami.missing_states", {}).get("value")
    off_val = m.get("origami.off_path_events", {}).get("value")
    progress_val = m.get("origami.progress", {}).get("value")
    
    last_stable = traj.get("final_state", {}).get("last_stable_state")
    reached = traj.get("final_state", {}).get("reached_by_trajectory")
    missing_states = traj["artifacts"]["missing_states"]
    uncertain = traj["artifacts"]["uncertain_states"]
    
    events = traj["events"]
    first_div = events[0] if events else None
    
    print(f"=== {v} ===")
    print(f"  Metrics: final_match={final_val} order_viol={order_val} missing={missing_val} off_path={off_val} progress={progress_val}")
    print(f"  Trajectory: last_stable=R{last_stable} reached={reached}")
    print(f"  Missing states: {missing_states}")
    print(f"  Uncertain states: {[x['state'] for x in uncertain]}")
    if first_div:
        kind = first_div.get("kind")
        pos = first_div.get("position")
        det = first_div.get("detail", "")[:60]
        print(f"  First divergence: {kind} at t={pos}s  ({det})")
    else:
        print(f"  First divergence: none")
    print(f"  Agreement: {sc}")
    print()
