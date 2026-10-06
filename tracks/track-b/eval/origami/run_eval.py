"""Run the origami evaluator on the eval attempts and score agreement with the ground truth.

Prerequisites (see README.md): media fetched, ``make_synthetic.py`` run, the origami goal built
(knowledge/goal_model.vN.json + goal_assets keyframes). Needs GEMINI_API_KEY for ``--mode live``;
``--mode recorded`` replays runs recorded earlier.

    python tracks/track-b/eval/origami/run_eval.py --mode live
    python tracks/track-b/eval/origami/run_eval.py --mode recorded

Writes ``var/eval/origami/results/<variant>.json`` and ``var/eval/origami/results/agreement.json``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parents[4]
for p in (ROOT, ROOT / "tracks" / "track-b" / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

HERE = Path(__file__).resolve().parent
CASE_DIR = ROOT / "tracks" / "cases" / "origami"
OUT = ROOT / "var" / "eval" / "origami"


def frame_accuracy(frame_labels: List[dict], intervals: Dict[str, List[List[float]]]) -> Optional[float]:
    """Accuracy of filtered labels on frames that fall inside a labelled state interval."""
    hits = total = 0
    for fr in frame_labels:
        truth = next((int(s) for s, ivs in intervals.items() for a, b in ivs if a - 0.5 <= fr["t"] <= b + 0.5), None)
        if truth is None:
            continue
        total += 1
        hits += fr["filtered"] == truth
    return round(hits / total, 3) if total else None


def goal_agreement(goal_states: List[dict], label_states: List[dict]) -> dict:
    """Compare built goal states to the expert labels: count and boundary error after IoU matching."""
    def iou(a, b):
        inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
        union = max(a[1], b[1]) - min(a[0], b[0])
        return inter / union if union > 0 else 0.0

    lab = [(s["index"], s["intervals"][0][0], s["intervals"][-1][1]) for s in label_states]
    errs, matched = [], []
    for g in goal_states:
        best = max(lab, key=lambda l: iou((g["start_sec"], g["end_sec"]), (l[1], l[2])))
        if iou((g["start_sec"], g["end_sec"]), (best[1], best[2])) > 0:
            matched.append(best[0])
            errs += [abs(g["start_sec"] - best[1]), abs(g["end_sec"] - best[2])]
    return {
        "goal_state_count": len(goal_states),
        "label_state_count": len(lab),
        "matched_label_states": matched,
        "order_preserved": matched == sorted(matched),
        "median_boundary_error_sec": round(median(errs), 2) if errs else None,
    }


def score(result: dict, gt: dict) -> dict:
    exp = gt["expected"]
    tr = result["trajectory"]
    events = tr["events"]
    fd = events[0] if events else None
    efd = exp["first_divergence"]
    return {
        "frame_state_accuracy": frame_accuracy(tr["artifacts"]["frame_labels"], gt["state_intervals"]),
        "missing_exact": tr["artifacts"]["missing_states"] == exp["missing_states"],
        "order_violations_exact": result["metrics"]["origami.order_violations"]["value"] == exp["order_violations"],
        "final_agrees": tr["final_state"]["reached_by_trajectory"] == exp["final_reached"],
        "first_divergence_kind_agrees": (fd is None and efd is None) or (fd is not None and efd is not None and fd["kind"] == efd["kind"]),
        "first_divergence_abs_error_sec": (round(abs(fd["position"] - efd["position_sec"]), 2) if fd and efd else None),
        "uncertain_states": tr["artifacts"]["uncertain_states"],
    }


def main(argv=None) -> int:
    from dataclasses import asdict

    from tracks.common.casedata import GoalModel, load_versioned
    from tracks.common.media import sha256_file
    from tracks.common.models import load_dotenv
    from tracks.common.runtime import RunContext
    from track_b.evaluators.origami import evaluate
    from track_b.trajectory import AttemptMedia

    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["live", "recorded"], default="recorded")
    ap.add_argument("--variants", nargs="*")
    args = ap.parse_args(argv)
    load_dotenv(ROOT / ".env")
    gt_all = json.loads((HERE / "labels" / "synthetic_ground_truth.json").read_text(encoding="utf-8"))
    expert = json.loads((HERE / "labels" / "expert_window_labels.json").read_text(encoding="utf-8"))
    goal = load_versioned(CASE_DIR / "knowledge", "goal_model", GoalModel)
    ctx = RunContext.create(CASE_DIR, ROOT / "var" / "data", args.mode)
    (OUT / "results").mkdir(parents=True, exist_ok=True)
    report = {"mode": args.mode, "goal_version": goal.version,
              "goal_vs_expert_labels": goal_agreement(goal.payload["states"], expert["states"]), "variants": {}}
    for name, gt in gt_all["variants"].items():
        if args.variants and name not in args.variants:
            continue
        video = ROOT / gt["file"]
        att = AttemptMedia(kind="video", path=video, source_id=f"eval.origami.{name}", sha256=sha256_file(video), mime_type="video/mp4")
        r = evaluate(goal, att, ctx)
        result = {
            "metrics": {k: {"value": v.value, "finding": v.finding, "uncertain_reason": v.uncertain_reason} for k, v in r.metrics.items()},
            "trajectory": {"events": [{**asdict(e), "evidence": e.evidence.model_dump(mode="json")} for e in r.events],
                           "curve": r.curve, "final_state": r.final_state, "artifacts": r.artifacts},
            "run_keys": r.run_keys, "warnings": r.warnings,
        }
        (OUT / "results" / f"{name}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        report["variants"][name] = score(result, gt)
        print(name, json.dumps(report["variants"][name]))
    (OUT / "results" / "agreement.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
