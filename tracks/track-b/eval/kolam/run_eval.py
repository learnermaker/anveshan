"""Agreement of the kolam evaluator with SYNTHETIC ground truth.

For each variant in ``synthetic/`` (see make_synthetic.py) this evaluates the attempt against
the goal built from the target image, maps metrics to statuses with the default rubric bands
(evaluation-core §3.2; mirrored here because Track B does not import Track A — the case's
practice/observers.vN.json is authoritative once it exists), and compares with label.json:
per-criterion status agreement, expected events present, first-divergence agreement.

Usage: python tracks/track-b/eval/kolam/run_eval.py  (writes RESULTS.md and results.json here)
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Dict, Optional

ROOT = Path(__file__).resolve().parents[4]
for p in (ROOT, ROOT / "tracks/track-b/src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tracks.common.casedata import GoalModel  # noqa: E402
from tracks.common.goals.kolam import payload_from_image  # noqa: E402
from track_b.evaluators.kolam import evaluate  # noqa: E402
from track_b.trajectory import AttemptMedia  # noqa: E402

HERE = Path(__file__).resolve().parent
SYN = HERE / "synthetic"
TARGET = ROOT / "tracks/cases/kolam/source/ithayakkamalam_target.jpg"


def default_bands(k: int) -> Dict[str, dict]:
    curves_partial = [("partially_satisfied", (k - 1) / k - 1e-6)] if k >= 2 else []
    return {
        "CRIT-KOLAM-COVERAGE": {"metric": "kolam.coverage", "hi": True, "bands": [("satisfied", 0.90), ("partially_satisfied", 0.70)]},
        "CRIT-KOLAM-PRECISION": {"metric": "kolam.precision", "hi": True, "bands": [("satisfied", 0.92), ("partially_satisfied", 0.80)]},
        "CRIT-KOLAM-DOTS": {"metric": "kolam.dot_relation_match", "hi": True, "bands": [("satisfied", 0.95), ("partially_satisfied", 0.80)]},
        "CRIT-KOLAM-CURVES": {"metric": "kolam.curves_completed_ratio", "hi": True, "bands": [("satisfied", 0.999)] + curves_partial},
        "CRIT-KOLAM-CONTINUITY": {"metric": "kolam.pen_lifts_excess", "hi": False, "process": True,
                                  "bands": [("satisfied", 1), ("partially_satisfied", max(k, 3))]},
    }


def status(spec: dict, value: Optional[float], process_observable: bool) -> str:
    if value is None or (spec.get("process") and not process_observable):
        return "uncertain"
    for st, thr in spec["bands"]:
        if (value >= thr) if spec["hi"] else (value <= thr):
            return st
    return "not_satisfied"


def first_div_ok(expected, events) -> bool:
    material = [e for e in events if e.severity == "material"]
    if expected is None:
        return not material
    if not material:
        return False
    first = material[0]
    kinds = expected.get("kinds") or [expected["kind"]]
    if first.kind not in kinds:
        return False
    if "stroke" in expected:
        return first.evidence.source_id.endswith(f"#stroke={expected['stroke']}")
    if "stage" in expected:
        return expected["stage"] in first.evidence.evidence_id
    return True


def events_ok(expected, events) -> bool:
    for x in expected:
        hit = [e for e in events if e.kind == x["kind"]]
        if "stroke" in x:
            hit = [e for e in hit if e.evidence.source_id.endswith(f"#stroke={x['stroke']}")]
        if "dot_id" in x:
            hit = [e for e in hit if e.evidence.evidence_id.endswith("." + x["dot_id"])]
        if "stage" in x:
            hit = [e for e in hit if e.evidence.evidence_id.endswith("." + x["stage"])]
        if not hit:
            return False
    return True


def main() -> dict:
    payload, built_with = payload_from_image(TARGET)
    goal = GoalModel(case_id="kolam", version=1, modality="kolam_image", source_ids=["src.kolam.target.v1"],
                     package_id="kp.kolam.1", built_with=built_with, payload=payload)
    k = len(payload["curves"])
    bands = default_bands(k)
    rows = []
    for d in sorted(p for p in SYN.iterdir() if p.is_dir()):
        label = json.loads((d / "label.json").read_text(encoding="utf-8"))
        kind = label["attempt_kind"]
        path = d / ("trace.json" if kind == "trace" else "attempt.png")
        att = AttemptMedia(kind=kind, path=path, source_id=f"src.attempt.kolam.synthetic.{d.name}",
                           sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                           mime_type="application/json" if kind == "trace" else "image/png")
        t0 = time.perf_counter()
        res = evaluate(goal, att, None)
        print(f"{d.name}: {time.perf_counter() - t0:.2f}s")
        got = {cid: status(spec, res.metrics[spec["metric"]].value, res.process_observable) for cid, spec in bands.items()}
        exp = label["expected_statuses"]
        agree = {cid: got[cid] == exp[cid] for cid in exp}
        material = [e for e in res.events if e.severity == "material"]
        rows.append({
            "variant": d.name, "kind": kind,
            "metrics": {m: v.value for m, v in sorted(res.metrics.items())},
            "statuses": got, "expected": exp, "status_agreement": agree,
            "first_divergence": None if not material else {"kind": material[0].kind, "locator": material[0].evidence.source_id,
                                                           "position": material[0].position},
            "first_divergence_ok": first_div_ok(label["expected_first_divergence"], res.events),
            "events_ok": events_ok(label.get("expected_events", []), res.events),
            "process_observable": res.process_observable,
            "registration": res.final_state.get("registration"),
        })
    n_crit = sum(len(r["status_agreement"]) for r in rows)
    n_agree = sum(sum(r["status_agreement"].values()) for r in rows)
    summary = {
        "variants": len(rows), "criterion_status_agreement": f"{n_agree}/{n_crit}",
        "first_divergence_agreement": f"{sum(r['first_divergence_ok'] for r in rows)}/{len(rows)}",
        "expected_events_found": f"{sum(r['events_ok'] for r in rows)}/{len(rows)}",
    }
    out = {"summary": summary, "goal": {"curves": k, "dots": len(payload["dots"]), "tau": payload["tau"]}, "rows": rows}
    (HERE / "results.json").write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_md(out)
    print(json.dumps(summary))
    return out


def write_md(out: dict) -> None:
    s = out["summary"]
    lines = [
        "# Kolam evaluator — agreement with SYNTHETIC ground truth",
        "",
        "Generated by `run_eval.py` from the attempts in `synthetic/` (built by `make_synthetic.py`, seeded).",
        "All attempts are **SYNTHETIC** perturbations of the goal line with exact ground truth; they say",
        "nothing about agreement with human judges (no hand-drawn or expert-labelled attempts yet).",
        "",
        f"Goal: {out['goal']['curves']} continuous line(s), {out['goal']['dots']} dots, tau = {out['goal']['tau']} px.",
        "",
        f"- Criterion status agreement: **{s['criterion_status_agreement']}**",
        f"- First-divergence agreement: **{s['first_divergence_agreement']}**",
        f"- Expected events found: **{s['expected_events_found']}**",
        "",
        "| variant | input | coverage | precision | dots | curves | lifts excess | statuses (got; * = disagrees) | first divergence | ok |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    short = {"satisfied": "sat", "partially_satisfied": "part", "not_satisfied": "not", "uncertain": "unc"}
    for r in out["rows"]:
        m = r["metrics"]

        def f(v):
            return "—" if v is None else (f"{v:.3f}" if isinstance(v, float) and v % 1 else f"{v:g}")
        sts = ", ".join(f"{c.split('-')[-1].lower()} {short[r['statuses'][c]]}{'' if r['status_agreement'][c] else '*'}" for c in r["statuses"])
        fd = "none" if r["first_divergence"] is None else f"{r['first_divergence']['kind']} `{r['first_divergence']['locator'].split('.')[-1]}`"
        ok = "yes" if r["first_divergence_ok"] and r["events_ok"] and all(r["status_agreement"].values()) else "NO"
        lines.append(f"| {r['variant']} | {r['kind']} | {f(m['kolam.coverage'])} | {f(m['kolam.precision'])} | {f(m['kolam.dot_relation_match'])} | "
                     f"{f(m['kolam.curves_completed_ratio'])} | {f(m['kolam.pen_lifts_excess'])} | {sts} | {fd} | {ok} |")
    regs = [r for r in out["rows"] if r["registration"]]
    if regs:
        lines += ["", "Photo-path registration (learner -> goal similarity):", ""]
        for r in regs:
            g = r["registration"]
            lines.append(f"- {r['variant']}: scale {g['scale']}, rotation {g['theta_deg']} deg, score {g['score']} ({g['method']})")
        lines.append("  (rotated variant was rendered with scale 1.3 and +23 deg, so the inverse is scale ~0.769 and rotation ~337 deg, equivalent modulo the target's 360/n symmetry step.)")
    lines += ["", "Process criteria for image inputs are `uncertain` by design (process not observable from a final image).", ""]
    (HERE / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
