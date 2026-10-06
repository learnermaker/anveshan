"""End-to-end session test for the kolam evaluator (deterministic, no API key).

Flow A  (trace baseline → trace retry):
  start_session → intake_attempt + submit_attempt with the stray-stroke synthetic trace
  (baseline) → perfect synthetic trace (retry) → complete_session.
  Asserts:
  * bundle passes validate_transmission_bundle
  * transmission_gain > 0
  * targeted_change shows CRIT-KOLAM-CONTINUITY improved

Flow B  (trace baseline → image retry):
  Same baseline; retry is the raster_perfect synthetic image.
  Asserts:
  * process criteria (CRIT-KOLAM-CONTINUITY) are UNCERTAIN in the retry result
  * trajectory.process_observable is False

The kolam evaluator is fully deterministic (no model calls), so RECORDED mode
needs no golden run files in the RunStore — it just cannot call a live API.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tracks.common.runtime import RunContext
from tracks.common.validator import validate_transmission_bundle

from track_b import api

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_DIR = REPO_ROOT / "tracks" / "cases" / "kolam"
SYNTHETIC = REPO_ROOT / "tracks" / "track-b" / "eval" / "kolam" / "synthetic"

STRAY_TRACE = SYNTHETIC / "stray_stroke" / "trace.json"
PERFECT_TRACE = SYNTHETIC / "perfect" / "trace.json"
RASTER_IMAGE = SYNTHETIC / "raster_perfect" / "attempt.png"

# Criterion ids that map to process metrics (should be UNCERTAIN from an image attempt).
PROCESS_CRITERIA = {"CRIT-KOLAM-CONTINUITY"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ctx(case_dir: Path, data_dir: Path) -> RunContext:
    """Recorded mode — the kolam evaluator makes no model calls so no golden runs needed."""
    return RunContext.create(case_dir, data_dir, "recorded")


def _intake_and_submit(session, path: Path, kind: str, ctx: RunContext):
    media = api.intake_attempt(session, path, kind)
    return api.submit_attempt(session, media, ctx)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_trace_stray_then_perfect(tmp_path):
    """Stray-stroke baseline (CONTINUITY partial) → perfect trace retry.

    Asserts bundle validates, gain is positive, and CRIT-KOLAM-CONTINUITY improved.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ctx = _ctx(CASE_DIR, data_dir)

    session = api.start_session(CASE_DIR, "TestLearner", data_dir)

    # Baseline: stray_stroke trace (3 strokes, 2 excess pen lifts → CONTINUITY partially_satisfied)
    b_res = _intake_and_submit(session, STRAY_TRACE, "trace", ctx)

    # Retry: perfect trace (1 stroke, 0 excess pen lifts → all satisfied)
    r_res = _intake_and_submit(session, PERFECT_TRACE, "trace", ctx)

    result = api.complete_session(session)
    out = result.to_json()

    # ── Bundle contract ────────────────────────────────────────────────────
    ok, errors = validate_transmission_bundle(out["bundle"])
    assert ok, f"Bundle invalid: {errors}"

    # ── Gain ──────────────────────────────────────────────────────────────
    rec = out["transmission_record"]
    assert rec["transmission_gain"] > 0, (
        f"Expected transmission_gain > 0, got {rec['transmission_gain']}"
    )

    # ── Targeted change: first-divergence criterion improved ───────────────
    cmp = out["comparison"]
    tc = cmp["targeted_change"]
    assert tc is not None, "targeted_change must not be None"
    assert tc["criterion_id"] == "CRIT-KOLAM-CONTINUITY", (
        f"Expected first-divergence criterion CRIT-KOLAM-CONTINUITY, got {tc['criterion_id']!r}"
    )
    assert tc["before"] == "partially_satisfied", (
        f"Expected CONTINUITY 'partially_satisfied' at baseline, got {tc['before']!r}"
    )
    assert tc["after"] == "satisfied", (
        f"Expected CONTINUITY 'satisfied' on retry, got {tc['after']!r}"
    )
    assert tc["improved"] is True, "targeted_change.improved must be True"

    # ── Baseline sanity: first_divergence points to CONTINUITY ────────────
    b_json = b_res.to_json()
    fd = b_json["first_divergence"]
    assert fd is not None, "Baseline with a stray stroke should have a first_divergence"
    assert fd["criterion_id"] == "CRIT-KOLAM-CONTINUITY"

    # ── Retry sanity: no first_divergence (all satisfied) ─────────────────
    r_json = r_res.to_json()
    assert r_json["first_divergence"] is None, (
        "Perfect trace retry should have no first_divergence"
    )
    assert r_json["evaluation"]["passed"] is True


def test_image_retry_process_criteria_uncertain(tmp_path):
    """Stray-stroke baseline → raster_perfect image retry.

    Asserts that process criteria are UNCERTAIN in the retry evaluation
    and that process_observable is False for the image attempt.
    """
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ctx = _ctx(CASE_DIR, data_dir)

    session = api.start_session(CASE_DIR, "TestLearner2", data_dir)

    # Baseline: stray_stroke trace (so the session has a valid baseline)
    _intake_and_submit(session, STRAY_TRACE, "trace", ctx)

    # Retry: raster image — process criteria cannot be observed
    r_res = _intake_and_submit(session, RASTER_IMAGE, "image", ctx)
    r_json = r_res.to_json()

    # Trajectory must report process not observable
    assert r_json["trajectory"]["process_observable"] is False, (
        "Image attempt must have process_observable=False"
    )

    # All process criteria must be UNCERTAIN in the evaluation
    criterion_results = {
        c["criterion_id"]: c for c in r_json["evaluation"]["criterion_results"]
    }
    for cid in PROCESS_CRITERIA:
        assert criterion_results[cid]["status"] == "uncertain", (
            f"Process criterion {cid} must be 'uncertain' for an image attempt, "
            f"got {criterion_results[cid]['status']!r}"
        )

    # The process metric itself must carry an uncertain_reason
    assert r_json["metrics"]["kolam.pen_lifts_excess"]["uncertain_reason"] is not None, (
        "kolam.pen_lifts_excess must carry an uncertain_reason for an image attempt"
    )
    assert r_json["metrics"]["kolam.pen_lifts_excess"]["value"] is None, (
        "kolam.pen_lifts_excess must be None (not computable) for an image attempt"
    )
