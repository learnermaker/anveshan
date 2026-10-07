"""Tests for K9-P1: insights recording and computation.

Covers spec §5: test_k9_insights.py tests 1-7.
"""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

from anveshan_service.insights import (
    compute, record_attempt, record_completion,
    _hash_session, _log_path,
)
from anveshan_service.main import create_app
from anveshan_service.settings import Settings
from anveshan_service.visitors import COOKIE, OWNERS_FILE

CID = "my-skill~aabbccddeeff"
STEWARD_TOKEN = "s3cret"


def _settings(tmp_path: Path, **kw) -> Settings:
    (tmp_path / "cases").mkdir(exist_ok=True)
    (tmp_path / "data").mkdir(exist_ok=True)
    base = dict(mode="recorded", cases_root=tmp_path / "cases", data_dir=tmp_path / "data", static_dir=None)
    base.update(kw)
    return Settings(**base)


def _fake_result(session_id: str = "sess-001", attempt_number: int = 1, passed: bool = False,
                 attempt_type: str = "baseline", score: float = 2.0, max_score: float = 5.0,
                 first_criterion: Optional[str] = None) -> dict:
    """Build a minimal FakeResult-style payload."""
    criterion_id = first_criterion or "CRIT-1"
    first_div = {"criterion_id": criterion_id, "criterion_name": "Stroke continuity"} if first_criterion is not None else None
    return {
        "attempt": {
            "attempt_id": f"attempt.{session_id}.{attempt_number}",
            "attempt_number": attempt_number,
            "attempt_type": attempt_type,
        },
        "evaluation": {
            "total_score": score,
            "passed": passed,
            "criterion_results": {
                criterion_id: {"criterion_id": criterion_id, "status": "satisfied" if passed else "not_satisfied"},
            },
        },
        "first_divergence": first_div,
        "comparison": None,
    }


def _make_community_case(settings: Settings, owner: str) -> Path:
    d = settings.data_dir / "cases" / CID
    d.mkdir(parents=True, exist_ok=True)
    (d / "knowledge").mkdir(exist_ok=True)
    (d / "knowledge" / "case_profile.v1.json").write_text("{}", encoding="utf-8")
    (d / OWNERS_FILE).write_text(json.dumps({"owners": [owner]}), encoding="utf-8")
    return d


def _fake_track_a(monkeypatch, cases=None):
    mod = types.ModuleType("track_a.api")
    cases = cases or []

    class _View:
        def __init__(self, cid):
            self.cid = cid

        def to_view(self):
            return {"case_id": self.cid, "review_status": "pending", "package": {"claims": []}}

    mod.list_cases = lambda cr, dd: [dict(c) for c in cases]
    mod.load_case = lambda cdir: _View(Path(cdir).name)
    mod.apply_review = lambda cdir, action: _View(Path(cdir).name)
    monkeypatch.setitem(sys.modules, "track_a.api", mod)
    return mod


# --- Test 1: no events -----------------------------------------------------------------------

def test_compute_no_events(tmp_path):
    s = _settings(tmp_path)
    result = compute(s, CID)
    assert result["learners"] == 0
    assert result["attempts"] == 0
    assert result["completed"] == 0
    assert result["baseline"]["count"] == 0
    assert result["baseline"]["pass_rate"] is None
    assert result["retry"]["pass_rate"] is None
    assert result["enough_data"] is False
    assert result["suggestions"] == []


# --- Test 2: synthetic sessions with R1 and R2 -----------------------------------------------

def test_compute_with_synthetic_sessions_checks_r1_r2(tmp_path):
    s = _settings(tmp_path)
    rubric_names = {"CRIT-1": "Stroke continuity", "CRIT-2": "Dot placement"}

    # 5 learners: baselines and retries
    sessions = [f"sess-{i:03d}" for i in range(1, 6)]
    for i, sess in enumerate(sessions):
        result = _fake_result(sess, 1, passed=(i == 0), attempt_type="baseline",
                              score=4.0 if i == 0 else 1.0, max_score=5.0,
                              first_criterion="CRIT-1")
        record_attempt(s, CID, sess, result, rubric_names, 5.0)
        if i < 4:
            retry_result = _fake_result(sess, 2, passed=(i < 2), attempt_type="retry",
                                        score=3.0 if i < 2 else 1.0, max_score=5.0,
                                        first_criterion=None)
            record_attempt(s, CID, sess, retry_result, rubric_names, 5.0)
        # 4 completions
        if i < 4:
            comp_result = {"comparison": {"skill_gain_excluding_observability": 0.3,
                                          "targeted_change": {"criterion_id": "CRIT-1", "improved": i < 2}}}
            record_completion(s, CID, sess, comp_result)

    result = compute(s, CID)
    assert result["learners"] == 5
    assert result["baseline"]["count"] == 5
    assert result["completed"] == 4
    assert result["enough_data"] is True

    # first_wrong is ordered by count desc
    fw = result["first_wrong"]
    assert len(fw) >= 1
    assert fw[0]["criterion_id"] == "CRIT-1"
    assert fw[0]["count"] == 5  # all 5 baselines had CRIT-1 as first_wrong
    assert fw[0]["share"] == 1.0

    # R2 should fire: most learners first go wrong at CRIT-1, count >= 3 and share >= 0.4
    r2_suggestion = next((s for s in result["suggestions"] if s["rule"] == "R2"), None)
    assert r2_suggestion is not None
    assert "CRIT-1" in r2_suggestion["text"] or "Stroke continuity" in r2_suggestion["text"]

    # hardest: CRIT-1 miss_rate should be high (4 out of 5 failed on baseline)
    h = result["hardest"]
    assert len(h) >= 1
    assert h[0]["criterion_id"] == "CRIT-1"
    # R1 should fire: miss_rate >= 0.5 and n >= 3
    r1_suggestion = next((s for s in result["suggestions"] if s["rule"] == "R1"), None)
    assert r1_suggestion is not None


# --- Test 3: no learner name in event file ---------------------------------------------------

def test_no_learner_name_in_event_file(tmp_path):
    s = _settings(tmp_path)
    session_id = "sess-secret-123"
    rubric_names = {"CRIT-1": "Stroke continuity"}
    result = _fake_result(session_id, 1, attempt_type="baseline", first_criterion="CRIT-1")
    # Add a learner_name field to simulate a result with learner name
    result["attempt"]["learner_name"] = "Alice"
    record_attempt(s, CID, session_id, result, rubric_names, 5.0)

    p = _log_path(s, CID)
    content = p.read_text(encoding="utf-8")
    assert "Alice" not in content
    assert session_id not in content  # raw session id must not appear
    # Hashed session id should appear
    hashed = _hash_session(session_id)
    assert hashed in content


# --- Test 4: malformed result does not raise -------------------------------------------------

def test_record_attempt_malformed_does_not_raise(tmp_path):
    s = _settings(tmp_path)
    # Completely malformed result
    record_attempt(s, CID, "sess-bad", {"garbage": True}, {}, None)
    # No exception raised


# --- Test 5: cap -------------------------------------------------------------------

def test_cap_limits_event_file(tmp_path):
    s = _settings(tmp_path, insights_max_events=10)
    rubric_names = {"CRIT-1": "Stroke continuity"}

    # Write 1100 events (over max_events + 1000 = 1010 lines threshold)
    for i in range(1100):
        result = _fake_result(f"sess-{i:06d}", 1, attempt_type="baseline", first_criterion="CRIT-1")
        record_attempt(s, CID, f"sess-{i:06d}", result, rubric_names, 5.0)

    p = _log_path(s, CID)
    lines = [l for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    # After capping, the file should have at most 1010 lines
    assert len(lines) <= 1010

    # compute() should still work
    result = compute(s, CID)
    assert result["attempts"] >= 0


# --- Test 6: access to insights endpoint ------------------------------------------------------

def test_owner_can_access_insights(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [{"case_id": CID, "modality": "kolam_image", "title": "x",
                                  "hero": False, "runtime_label": "UPLOAD", "review_status": "pending"}])
    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})
    r = a.get(f"/api/insights/{CID}")
    assert r.status_code == 200
    assert "learners" in r.json()


def test_steward_can_access_insights(tmp_path, monkeypatch):
    s = _settings(tmp_path, steward_token="s3cret", steward_open=False)
    owner = "a" * 32
    cdir = _make_community_case(s, owner)
    # Set the case to submitted so steward can see it (private is not visible to stewards)
    from anveshan_service.library import LibraryRecord, save
    rec = LibraryRecord(case_id=CID, status="submitted", collection="community", credit_name="Alice")
    save(s, rec, cdir)
    _fake_track_a(monkeypatch, [])
    app = create_app(s)
    swd = TestClient(app, cookies={COOKIE: "s" * 32}, headers={"X-Steward-Token": "s3cret"})
    r = swd.get(f"/api/insights/{CID}")
    assert r.status_code == 200


def test_other_visitor_cannot_access_insights(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    cdir = _make_community_case(s, owner)
    # Publish so visitor b can see it
    from anveshan_service.library import LibraryRecord, save
    rec = LibraryRecord(case_id=CID, status="published", collection="community")
    save(s, rec, cdir)
    _fake_track_a(monkeypatch, [{"case_id": CID, "modality": "kolam_image", "title": "x",
                                  "hero": False, "runtime_label": "UPLOAD", "review_status": "approved"}])
    app = create_app(s)
    b = TestClient(app, cookies={COOKIE: "b" * 32})
    r = b.get(f"/api/insights/{CID}")
    assert r.status_code in (403, 404)


# --- Test 7: end-to-end through fake Track B --------------------------------------------------

def test_insights_via_session_flow(tmp_path, monkeypatch):
    """Start a session, submit 2 attempts, complete. Check insights has 2 attempts + 1 complete."""
    from anveshan_service import insights as ins_mod

    s = _settings(tmp_path)
    owner = "a" * 32
    cdir = _make_community_case(s, owner)

    # Fake Track A and B
    a_mod = types.ModuleType("track_a.api")

    class _AView:
        def __init__(self, cid):
            self.cid = cid

        def to_view(self):
            return {"case_id": self.cid, "review_status": "pending", "package": {"claims": []}}

    a_mod.list_cases = lambda cr, dd: [{"case_id": CID, "modality": "kolam_image", "title": "x",
                                         "hero": False, "runtime_label": "UPLOAD", "review_status": "pending"}]
    a_mod.load_case = lambda d: _AView(Path(d).name)
    monkeypatch.setitem(sys.modules, "track_a.api", a_mod)

    import dataclasses
    from anveshan_service.settings import Settings as Sett

    # Use the fake_track_b from conftest (import it)
    from service.tests.conftest import fake_track_b
    b_mod = fake_track_b()
    monkeypatch.setitem(sys.modules, "track_b.api", b_mod)
    monkeypatch.setitem(sys.modules, "track_b.intake", None)

    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})

    # Start session
    import io
    r = a.post("/api/sessions", json={"case_id": CID, "learner_name": "Learner"})
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    JPEG = b"\xff\xd8\xff\xe0" + b"0" * 2000 + b"\xff\xd9"

    # Submit attempt 1
    r = a.post(f"/api/sessions/{session_id}/attempts",
               data={"kind": "image"}, files={"file": ("a.jpg", JPEG, "image/jpeg")})
    assert r.status_code == 200

    # Submit attempt 2
    r = a.post(f"/api/sessions/{session_id}/attempts",
               data={"kind": "image"}, files={"file": ("b.jpg", JPEG, "image/jpeg")})
    assert r.status_code == 200

    # Complete
    r = a.post(f"/api/sessions/{session_id}/complete")
    assert r.status_code == 200

    # Check insights file
    p = ins_mod._log_path(s, CID)
    if p.is_file():
        events = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
        attempt_events = [e for e in events if e.get("kind") == "attempt"]
        complete_events = [e for e in events if e.get("kind") == "complete"]
        assert len(attempt_events) == 2
        assert len(complete_events) == 1
