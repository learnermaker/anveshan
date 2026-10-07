"""End-to-end session with a fake evaluator: baseline -> feedback -> retry -> validated bundle."""

import json
import re

import pytest

from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import ReviewStatus
from tracks.common.validator import validate_transmission_bundle

from track_b import api
from track_b.clock import FixedClock, SequentialIdFactory
from track_b.transmission import canonical_json

from core_fixtures import install_fake_evaluator, make_case, make_ctx, write_trace

BASELINE = {"fake.coverage": 0.75, "fake.precision": None, "fake.continuity": 6}
RETRY = {"fake.coverage": 0.95, "fake.precision": 0.95, "fake.continuity": 3}


def _session(tmp_path, monkeypatch, review=ReviewStatus.APPROVED, run_keys=None, mode="recorded"):
    install_fake_evaluator(monkeypatch)
    case = make_case(tmp_path / "cases", review=review)
    data = tmp_path / "data"
    s = api.start_session(case, "Asha", data, clock=FixedClock(), ids=SequentialIdFactory())
    ctx = make_ctx(case, data, mode)
    return s, ctx, case, data


def _submit(s, ctx, tmp_path, metrics, name, **kw):
    media = api.intake_attempt(s, write_trace(tmp_path / name, metrics, **kw), "trace")
    return api.submit_attempt(s, media, ctx)


def run_full(tmp_path, monkeypatch, **kw):
    s, ctx, case, data = _session(tmp_path, monkeypatch, **kw)
    b = _submit(s, ctx, tmp_path, BASELINE, "b.json", events=[{"metric": "fake.continuity", "position": 2.0}])
    r = _submit(s, ctx, tmp_path, RETRY, "r.json")
    return s, b, r, api.complete_session(s)


def test_full_session_produces_valid_bundle(tmp_path, monkeypatch):
    s, b, r, res = run_full(tmp_path, monkeypatch)
    bj, rj, out = b.to_json(), r.to_json(), res.to_json()
    assert set(bj) == {"attempt", "evaluation", "trajectory", "metrics", "first_divergence", "feedback", "drill", "coaching",
                       "runtime_class", "warnings", "run_keys"}
    assert set(bj["trajectory"]) == {"curve", "curve_kind", "events", "process_observable", "artifacts", "final_state"}
    assert bj["attempt"]["attempt_id"] == "attempt.fakecase.sess-0001.baseline.1"
    assert bj["attempt"]["evidence"]["source_id"] == "src.attempt.fakecase.sess-0001.1"
    assert bj["attempt"]["evidence"]["end_sec"] == 0.5
    assert rj["attempt"]["attempt_type"] == "retry" and rj["attempt"]["attempt_number"] == 2
    assert bj["runtime_class"] == "DETERMINISTIC"
    assert bj["metrics"]["fake.precision"] == {"value": None, "finding": "fake.precision not computable",
                                               "uncertain_reason": "too little ink"}
    # baseline: A partial, B uncertain (required -> human review warning), C not satisfied with a material event
    assert bj["evaluation"]["passed"] is False
    assert any(w.startswith("HUMAN_REVIEW_REQUIRED") for w in bj["warnings"])
    assert bj["first_divergence"]["criterion_id"] == "CRIT-C"
    assert bj["feedback"]["items"][0]["criterion_id"] == "CRIT-C"
    assert bj["drill"]["criterion_id"] == "CRIT-C"
    # retry passed -> no feedback/drill
    assert rj["evaluation"]["passed"] is True and rj["feedback"] is None and rj["drill"] is None

    assert set(out) == {"bundle", "transmission_record", "comparison"}
    ok, errors = validate_transmission_bundle(out["bundle"])
    assert ok, errors
    rec = out["transmission_record"]
    assert rec["transmission_id"] == "tx.fakecase.sess-0001"
    assert rec["expert_id"] == "Test Source (SYNTHETIC)"
    assert rec["learner_id"] == "learner.sess-0001"
    assert rec["baseline_score"] == 1.5 and rec["retry_score"] == 5.5 and rec["transmission_gain"] == 4.0
    assert rec["criteria_improved"] == ["CRIT-A", "CRIT-C"]  # CRIT-B was uncertain at baseline
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", rec["lineage"]["provenance_hash"])
    assert rec["lineage"]["recorded_at"] == "2026-10-06T00:00:00Z"
    notes = rec["lineage"]["adaptation_notes"]
    assert notes == "score_policy_v1; observers v1; drill: CRIT-C; observability transitions: CRIT-B uncertain->satisfied"
    cmp_ = out["comparison"]
    assert cmp_["transitions"] == {"CRIT-A": "improved", "CRIT-B": "observability_gain", "CRIT-C": "improved"}
    assert cmp_["targeted_change"]["criterion_id"] == "CRIT-C" and cmp_["targeted_change"]["after"] == "partially_satisfied"
    assert cmp_["skill_gain_excluding_observability"] == 2.0
    assert s.state == "COMPLETED"
    json.dumps(out)  # serialisable


def test_bundle_is_byte_identical_across_runs(tmp_path, monkeypatch):
    out1 = run_full(tmp_path / "one", monkeypatch)[3].to_json()
    out2 = run_full(tmp_path / "two", monkeypatch)[3].to_json()
    assert canonical_json(out1["bundle"]) == canonical_json(out2["bundle"])
    assert out1["transmission_record"]["lineage"]["provenance_hash"] == out2["transmission_record"]["lineage"]["provenance_hash"]


def test_unapproved_package_noted(tmp_path, monkeypatch):
    _, b, _, res = run_full(tmp_path, monkeypatch, review=ReviewStatus.PENDING)
    assert any("not expert-approved" in w for w in b.to_json()["warnings"])
    assert res.to_json()["transmission_record"]["lineage"]["adaptation_notes"].endswith("package not expert-approved")


@pytest.mark.parametrize("mode,expected", [("recorded", "RECORDED_LIVE"), ("live", "LIVE")])
def test_runtime_class_from_runs(tmp_path, monkeypatch, mode, expected):
    s, ctx, _, _ = _session(tmp_path, monkeypatch, mode=mode)
    out = _submit(s, ctx, tmp_path, BASELINE, "b.json", run_keys=["abc"]).to_json()
    assert out["runtime_class"] == expected and out["run_keys"] == ["abc"]
    assert out["evaluation"]["evaluator_type"] == "model_assisted"


def test_state_machine_and_persistence(tmp_path, monkeypatch):
    s, ctx, case, data = _session(tmp_path, monkeypatch)
    with pytest.raises(AnveshanFailure) as e:
        api.complete_session(s)
    assert e.value.category == FailureCategory.INVALID_INPUT
    _submit(s, ctx, tmp_path, BASELINE, "b.json")
    assert s.state == "FEEDBACK_READY"

    api.save_session(s, data)
    assert (data / "sessions" / f"{s.session_id}.json").exists()
    s2 = api.load_session(s.session_id, data, clock=FixedClock())
    assert s2.to_json() == s.to_json()

    _submit(s2, ctx, tmp_path, BASELINE, "r1.json")  # failed retry -> feedback for it, may retry again
    assert s2.state == "RETRY_EVALUATED"
    r2 = _submit(s2, ctx, tmp_path, RETRY, "r2.json")
    assert r2.to_json()["attempt"]["attempt_number"] == 3
    res = api.complete_session(s2)
    assert res.to_json()["transmission_record"]["retry_attempt_id"].endswith("retry.3")
    assert api.complete_session(s2).to_json() == res.to_json()  # idempotent
    with pytest.raises(AnveshanFailure):
        _submit(s2, ctx, tmp_path, RETRY, "r3.json")


def test_retry_before_feedback_rejected(tmp_path, monkeypatch):
    s, ctx, _, _ = _session(tmp_path, monkeypatch)
    s.state = "BASELINE_EVALUATED"
    s.attempts.append({"result": {}, "media": {}})
    with pytest.raises(AnveshanFailure) as e:
        _submit(s, ctx, tmp_path, RETRY, "r.json")
    assert e.value.category == FailureCategory.INVALID_INPUT


def test_wrong_kind_rejected(tmp_path, monkeypatch):
    s, ctx, _, _ = _session(tmp_path, monkeypatch)
    media = api.intake_attempt(s, write_trace(tmp_path / "b.json", BASELINE), "trace")
    media.kind = "audio"
    with pytest.raises(AnveshanFailure) as e:
        api.submit_attempt(s, media, ctx)
    assert e.value.category == FailureCategory.INVALID_INPUT and "trace or image" in e.value.message


def test_load_session_errors(tmp_path):
    with pytest.raises(AnveshanFailure) as e:
        api.load_session("missing", tmp_path)
    assert e.value.category == FailureCategory.MISSING_EVIDENCE
    with pytest.raises(AnveshanFailure) as e:
        api.load_session("../evil", tmp_path)
    assert e.value.category == FailureCategory.INVALID_INPUT


def test_start_session_requires_name(tmp_path):
    with pytest.raises(AnveshanFailure):
        api.start_session(make_case(tmp_path), "  ", tmp_path)
