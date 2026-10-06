"""Track B kolam evaluator: synthetic-variant status agreement tests.

Runs the evaluator on every folder under tracks/track-b/eval/kolam/synthetic/,
asserts that the computed criterion statuses and first-divergence agree with
label.json, and checks that the missing-stage coverage is well below the 0.90
sat boundary (robustness guard after the two-stage fragility fix).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import importlib.util as _ilu
from typing import Optional

import pytest

from tracks.common.casedata import GoalModel
from tracks.common.goals.kolam import payload_from_image

from track_b.evaluators import get_evaluator
from track_b.evaluators.kolam import evaluate
from track_b.trajectory import AttemptMedia

REPO_ROOT = Path(__file__).resolve().parents[3]
TARGET = REPO_ROOT / "tracks" / "cases" / "kolam" / "source" / "ithayakkamalam_target.jpg"
SYNTHETIC = Path(__file__).resolve().parent.parent / "eval" / "kolam" / "synthetic"

# ---------------------------------------------------------------------------
# Band functions imported directly from run_eval.py (single authoritative source).
# Resolved K1-tests-review finding "band-duplication-drift": no longer a copy.
# If run_eval.py thresholds change, the test automatically uses the updated values.
# ---------------------------------------------------------------------------

_run_eval_path = Path(__file__).resolve().parents[1] / "eval" / "kolam" / "run_eval.py"
_run_eval_spec = _ilu.spec_from_file_location("run_eval_kolam", _run_eval_path)
_run_eval_mod = _ilu.module_from_spec(_run_eval_spec)
_run_eval_spec.loader.exec_module(_run_eval_mod)  # type: ignore[union-attr]
_default_bands = _run_eval_mod.default_bands   # tracks/track-b/eval/kolam/run_eval.py
_status = _run_eval_mod.status                 # tracks/track-b/eval/kolam/run_eval.py


def _first_div_ok(expected: Optional[dict], events) -> bool:
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


def _events_ok(expected_events: list, actual_events) -> bool:
    for x in expected_events:
        hits = [e for e in actual_events if e.kind == x["kind"]]
        if "stroke" in x:
            hits = [e for e in hits if e.evidence.source_id.endswith(f"#stroke={x['stroke']}")]
        if "dot_id" in x:
            hits = [e for e in hits if e.evidence.evidence_id.endswith("." + x["dot_id"])]
        if "stage" in x:
            hits = [e for e in hits if e.evidence.evidence_id.endswith("." + x["stage"])]
        if not hits:
            return False
    return True


# ---------------------------------------------------------------------------
# Module-scoped goal model (built once from the real target, ~1.4 s)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def goal_model() -> GoalModel:
    payload, built_with = payload_from_image(TARGET)
    return GoalModel(
        case_id="kolam",
        version=1,
        modality="kolam_image",
        source_ids=["src.kolam.target.v1"],
        package_id="kp.kolam.1",
        built_with=built_with,
        payload=payload,
    )


# ---------------------------------------------------------------------------
# Parametrized evaluator test
# ---------------------------------------------------------------------------

_VARIANT_DIRS = sorted(SYNTHETIC.glob("*/")) if SYNTHETIC.exists() else []


def test_registry_points_to_kolam_evaluator():
    assert get_evaluator("kolam_image") is evaluate


@pytest.mark.parametrize("variant_dir", _VARIANT_DIRS, ids=[d.name for d in _VARIANT_DIRS])
def test_evaluator_matches_expected_statuses(variant_dir: Path, goal_model: GoalModel):
    """Criterion statuses, first divergence, and expected events all agree with label.json."""
    label = json.loads((variant_dir / "label.json").read_text(encoding="utf-8"))
    kind = label["attempt_kind"]
    attempt_path = variant_dir / ("trace.json" if kind == "trace" else "attempt.png")
    mime = "application/json" if kind == "trace" else "image/png"

    att = AttemptMedia(
        kind=kind,
        path=attempt_path,
        source_id=f"src.attempt.kolam.synthetic.{variant_dir.name}",
        sha256=hashlib.sha256(attempt_path.read_bytes()).hexdigest(),
        mime_type=mime,
    )

    from tracks.common.goals.kolam import KolamGoal
    k = len(KolamGoal.model_validate(goal_model.payload).curves)
    bands = _default_bands(k)

    res = evaluate(goal_model, att, None)

    got_statuses = {
        cid: _status(spec, res.metrics[spec["metric"]].value, res.process_observable)
        for cid, spec in bands.items()
    }
    expected_statuses = label["expected_statuses"]
    disagreements = {cid: (got_statuses[cid], expected_statuses[cid])
                     for cid in expected_statuses if got_statuses[cid] != expected_statuses[cid]}
    assert not disagreements, (
        f"[{variant_dir.name}] status disagreements: "
        + ", ".join(f"{c}: got {g!r} expected {e!r}" for c, (g, e) in disagreements.items())
    )

    # First divergence agreement
    assert _first_div_ok(label["expected_first_divergence"], res.events), (
        f"[{variant_dir.name}] first-divergence mismatch; "
        f"expected {label['expected_first_divergence']}, "
        f"material events: {[e.kind for e in res.events if e.severity == 'material']}"
    )

    # Expected events present
    assert _events_ok(label.get("expected_events", []), res.events), (
        f"[{variant_dir.name}] expected events not all found; "
        f"expected {label.get('expected_events', [])}"
    )


def test_missing_stage_coverage_well_below_0_90_boundary(goal_model: GoalModel):
    """missing_stage coverage must be < 0.88 (not fragile at the 0.90 sat boundary)."""
    variant_dir = SYNTHETIC / "missing_stage"
    label = json.loads((variant_dir / "label.json").read_text(encoding="utf-8"))
    attempt_path = variant_dir / "trace.json"

    att = AttemptMedia(
        kind="trace",
        path=attempt_path,
        source_id="src.attempt.kolam.synthetic.missing_stage",
        sha256=hashlib.sha256(attempt_path.read_bytes()).hexdigest(),
        mime_type="application/json",
    )
    res = evaluate(goal_model, att, None)
    cov = res.metrics["kolam.coverage"].value
    assert cov is not None and cov < 0.88, (
        f"missing_stage coverage {cov:.4f} is too close to the 0.90 band boundary; "
        "regenerate synthetic files with two omitted stages"
    )
    assert cov >= 0.70, (
        f"missing_stage coverage {cov:.4f} unexpectedly dropped below the 0.70 partial boundary"
    )


def test_image_path_process_criteria_are_uncertain(goal_model: GoalModel):
    """For raster attempts, process criterion (CONTINUITY) is always uncertain."""
    raster_dir = SYNTHETIC / "raster_perfect"
    attempt_path = raster_dir / "attempt.png"

    att = AttemptMedia(
        kind="image",
        path=attempt_path,
        source_id="src.attempt.kolam.synthetic.raster_perfect",
        sha256=hashlib.sha256(attempt_path.read_bytes()).hexdigest(),
        mime_type="image/png",
    )
    res = evaluate(goal_model, att, None)
    assert not res.process_observable, "image path should set process_observable=False"
    pen_lifts = res.metrics["kolam.pen_lifts_excess"]
    assert pen_lifts.value is None, (
        f"pen_lifts_excess should be None for image path, got {pen_lifts.value}"
    )
    assert pen_lifts.uncertain_reason, "pen_lifts_excess should carry an uncertain_reason"
