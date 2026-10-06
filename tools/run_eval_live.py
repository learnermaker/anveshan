"""Run origami evaluations in live mode with rate-limit pauses between variants.

Usage (worktree root):
    python tools/run_eval_live.py [--variants perfect missing_state swapped_order truncated real_learner]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT, ROOT / "tracks" / "track-b" / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tracks.common.casedata import GoalModel, load_versioned
from tracks.common.media import sha256_file
from tracks.common.models import load_dotenv
from tracks.common.runtime import RunContext
from track_b.evaluators.origami import evaluate
from track_b.trajectory import AttemptMedia

load_dotenv(ROOT / ".env")

CASE_DIR = ROOT / "tracks" / "cases" / "origami"
HERE = ROOT / "tracks" / "track-b" / "eval" / "origami"
OUT = ROOT / "var" / "eval" / "origami"
RATE_LIMIT_SLEEP_S = 75  # seconds to wait between variants to avoid 429


def score_result(result: dict, gt: dict) -> dict:
    """Compute agreement scores."""
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
        "uncertain_states": tr["artifacts"]["uncertain_states"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", nargs="*", default=["perfect", "missing_state", "swapped_order", "truncated", "real_learner"])
    args = ap.parse_args()

    gt_all = json.loads((HERE / "labels" / "synthetic_ground_truth.json").read_text(encoding="utf-8"))
    goal = load_versioned(CASE_DIR / "knowledge", "goal_model", GoalModel)
    ctx = RunContext.create(CASE_DIR, ROOT / "var" / "data", "live")
    (OUT / "results").mkdir(parents=True, exist_ok=True)

    report = {"mode": "live", "goal_version": goal.version, "variants": {}}

    for vi, name in enumerate(args.variants):
        if name not in gt_all["variants"]:
            print(f"Skipping unknown variant: {name}")
            continue
        gt = gt_all["variants"][name]
        video = ROOT / gt["file"]
        if not video.exists():
            print(f"MISSING video for {name}: {video}")
            continue
        print(f"\n--- Evaluating {name} ({vi+1}/{len(args.variants)}) ---")
        att = AttemptMedia(kind="video", path=video, source_id=f"eval.origami.{name}",
                           sha256=sha256_file(video), mime_type="video/mp4")
        try:
            r = evaluate(goal, att, ctx)
            result = {
                "metrics": {k: {"value": v.value, "finding": v.finding, "uncertain_reason": v.uncertain_reason}
                            for k, v in r.metrics.items()},
                "trajectory": {
                    "events": [{**asdict(e), "evidence": e.evidence.model_dump(mode="json")} for e in r.events],
                    "curve": r.curve, "final_state": r.final_state, "artifacts": r.artifacts,
                },
                "run_keys": r.run_keys, "warnings": r.warnings,
            }
            (OUT / "results" / f"{name}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
            sc = score_result(result, gt)
            report["variants"][name] = sc
            print(f"  {name}: {json.dumps(sc)}")
        except Exception as exc:
            print(f"  ERROR evaluating {name}: {exc}")
            report["variants"][name] = {"error": str(exc)[:200]}

        if vi < len(args.variants) - 1:
            print(f"  Waiting {RATE_LIMIT_SLEEP_S}s for rate limit...")
            time.sleep(RATE_LIMIT_SLEEP_S)

    (OUT / "results" / "agreement.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport saved to {OUT/'results'/'agreement.json'}")


if __name__ == "__main__":
    main()
