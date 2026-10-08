"""Tests for K9-P1: library lifecycle, access control and housekeeping protection.

Covers spec §5: test_k9_library.py tests 1-8 and §3.11.
"""

from __future__ import annotations

import json
import sys
import time
import types
from pathlib import Path
from typing import Any, Optional

import pytest
from fastapi.testclient import TestClient

from anveshan_service.main import create_app
from anveshan_service.settings import Settings
from anveshan_service.visitors import COOKIE, OWNERS_FILE
from anveshan_service.housekeeping import sweep

CID = "my-skill~aabbccddeeff"


def _settings(tmp_path: Path, **kw) -> Settings:
    (tmp_path / "cases").mkdir(exist_ok=True)
    (tmp_path / "data").mkdir(exist_ok=True)
    base = dict(
        mode="recorded",
        cases_root=tmp_path / "cases",
        data_dir=tmp_path / "data",
        static_dir=None,
    )
    base.update(kw)
    return Settings(**base)


def _fake_track_a(monkeypatch, cases=None, view_extra: Optional[dict] = None):
    """Install a fake track_a.api module. view_extra overrides the case view."""
    mod = types.ModuleType("track_a.api")
    cases = cases or []

    class _View:
        def __init__(self, cid, **kw):
            self.cid = cid
            self.kw = kw

        def to_view(self):
            v = {"case_id": self.cid, "review_status": "pending", "package": {"claims": []}}
            if view_extra:
                v.update(view_extra)
            v.update(self.kw)
            return v

    mod.list_cases = lambda cr, dd: [dict(c) for c in cases]
    mod.load_case = lambda cdir: _View(Path(cdir).name, **(view_extra or {}))
    mod.apply_review = lambda cdir, action: _View(Path(cdir).name)
    monkeypatch.setitem(sys.modules, "track_a.api", mod)
    return mod


def _make_community_case(settings: Settings, owner: str) -> Path:
    """Create a community case directory owned by the given visitor."""
    d = settings.data_dir / "cases" / CID
    d.mkdir(parents=True, exist_ok=True)
    (d / "knowledge").mkdir(exist_ok=True)
    # Write case_profile so kind_of returns "community"
    (d / "knowledge" / "case_profile.v1.json").write_text("{}", encoding="utf-8")
    (d / OWNERS_FILE).write_text(json.dumps({"owners": [owner]}), encoding="utf-8")
    return d


# --- Test 1: new community case access --------------------------------------------------------

def test_new_community_case_access(tmp_path, monkeypatch):
    """A new community case: owner=True, library_status private, can_submit=False with blocker."""
    s = _settings(tmp_path)
    owner = "a" * 32
    cdir = _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [{"case_id": CID, "modality": "kolam_image", "title": "x", "hero": False,
                                  "runtime_label": "UPLOAD", "review_status": "pending"}])

    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})
    cases = a.get("/api/cases").json()
    our_case = next((c for c in cases if c["case_id"] == CID), None)
    assert our_case is not None
    ac = our_case["access"]
    assert ac["owner"] is True
    assert ac["library_status"] == "private"
    assert ac["can_submit"] is False
    assert any("Check what the AI understood" in b for b in ac["submit_blockers"])


# --- Test 2: submit with review approved -------------------------------------------------------

def test_submit_with_review_approved(tmp_path, monkeypatch):
    """Submit with review approved -> status submitted, history has 'submitted'."""
    s = _settings(tmp_path)
    owner = "a" * 32
    cdir = _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [], view_extra={"case_id": CID, "review_status": "approved"})

    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})

    body = {
        "credit_name": "Alice",
        "licence": "CC-BY-4.0",
        "consent_scope": "public_practice",
        "rights_confirmed": True,
        "people_visible": False,
        "people_consented": False,
    }
    r = a.post(f"/api/library/{CID}/submit", json=body)
    assert r.status_code == 200, r.text
    rec = r.json()
    assert rec["status"] == "submitted"
    assert any(h["action"] == "submitted" for h in rec["history"])
    assert rec["rights_confirmed_at"] is not None


# --- Test 3: submit errors --------------------------------------------------------------------

def test_submit_missing_credit_gives_400(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [], view_extra={"case_id": CID, "review_status": "approved"})
    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})
    body = {"credit_name": "  ", "licence": "CC-BY-4.0", "consent_scope": "public_practice",
            "rights_confirmed": True, "people_visible": False, "people_consented": False}
    r = a.post(f"/api/library/{CID}/submit", json=body)
    assert r.status_code == 400
    assert "blockers" in r.json()["error"]["details"]


def test_submit_people_visible_without_consent_gives_400(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [], view_extra={"case_id": CID, "review_status": "approved"})
    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})
    body = {"credit_name": "Alice", "licence": "CC-BY-4.0", "consent_scope": "public_practice",
            "rights_confirmed": True, "people_visible": True, "people_consented": False}
    r = a.post(f"/api/library/{CID}/submit", json=body)
    assert r.status_code == 400


def test_submit_bad_licence_gives_error(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [], view_extra={"case_id": CID, "review_status": "approved"})
    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})
    body = {"credit_name": "Alice", "licence": "NOT-A-LICENCE", "consent_scope": "public_practice",
            "rights_confirmed": True, "people_visible": False, "people_consented": False}
    r = a.post(f"/api/library/{CID}/submit", json=body)
    assert r.status_code >= 400


def test_second_visitor_submit_gives_404(tmp_path, monkeypatch):
    """A second visitor cannot see a private case (case_dir 404)."""
    s = _settings(tmp_path)
    owner = "a" * 32
    _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [])
    app = create_app(s)
    b = TestClient(app, cookies={COOKIE: "b" * 32})
    # Pass a body that would otherwise be valid — the 404 must come from case_dir visibility, not validation
    valid_body = {"credit_name": "Bob", "licence": "CC-BY-4.0", "consent_scope": "public_practice",
                  "rights_confirmed": True, "people_visible": False, "people_consented": False}
    r = b.post(f"/api/library/{CID}/submit", json=valid_body)
    assert r.status_code == 404


# --- Test 4: withdraw --------------------------------------------------------------------------

def test_withdraw_submitted_to_private(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [], view_extra={"case_id": CID, "review_status": "approved"})
    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})
    body = {"credit_name": "Alice", "licence": "CC-BY-4.0", "consent_scope": "public_practice",
            "rights_confirmed": True, "people_visible": False, "people_consented": False}
    r = a.post(f"/api/library/{CID}/submit", json=body)
    assert r.status_code == 200
    r = a.post(f"/api/library/{CID}/withdraw")
    assert r.status_code == 200
    assert r.json()["status"] == "private"


def test_withdraw_already_private_gives_409(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [])
    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})
    r = a.post(f"/api/library/{CID}/withdraw")
    assert r.status_code == 409


# --- Test 5: visibility -----------------------------------------------------------------------

def test_private_skill_invisible_to_other_visitor(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [{"case_id": CID, "modality": "kolam_image", "title": "x",
                                  "hero": False, "runtime_label": "UPLOAD", "review_status": "pending"}])
    app = create_app(s)
    b = TestClient(app, cookies={COOKIE: "b" * 32})
    cases = b.get("/api/cases").json()
    assert not any(c["case_id"] == CID for c in cases)
    assert b.get(f"/api/cases/{CID}").status_code == 404


def test_published_skill_visible_to_other_visitor(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    cdir = _make_community_case(s, owner)

    # Manually set the library record to published
    from anveshan_service.library import LibraryRecord, save
    rec = LibraryRecord(case_id=CID, status="published", collection="community")
    save(s, rec, cdir)

    _fake_track_a(monkeypatch, [{"case_id": CID, "modality": "kolam_image", "title": "x",
                                  "hero": False, "runtime_label": "UPLOAD", "review_status": "approved"}])
    app = create_app(s)
    b = TestClient(app, cookies={COOKIE: "b" * 32})
    cases = b.get("/api/cases").json()
    our_case = next((c for c in cases if c["case_id"] == CID), None)
    assert our_case is not None
    assert our_case["access"]["owner"] is False

    r = b.get(f"/api/cases/{CID}")
    assert r.status_code == 200


def test_submitted_skill_visible_to_steward(tmp_path, monkeypatch):
    s = _settings(tmp_path, steward_token="s3cret", steward_open=False)
    owner = "a" * 32
    cdir = _make_community_case(s, owner)

    from anveshan_service.library import LibraryRecord, save
    rec = LibraryRecord(case_id=CID, status="submitted", collection="community", credit_name="Alice")
    save(s, rec, cdir)

    _fake_track_a(monkeypatch, [{"case_id": CID, "modality": "kolam_image", "title": "x",
                                  "hero": False, "runtime_label": "UPLOAD", "review_status": "approved"}])
    app = create_app(s)
    # Steward can see it
    swd = TestClient(app, cookies={COOKIE: "s" * 32}, headers={"X-Steward-Token": "s3cret"})
    cases = swd.get("/api/cases").json()
    assert any(c["case_id"] == CID for c in cases)
    # Non-steward, non-owner cannot see it
    b = TestClient(app, cookies={COOKIE: "b" * 32})
    b_cases = b.get("/api/cases").json()
    assert not any(c["case_id"] == CID for c in b_cases)


# --- Test 6: curated case access --------------------------------------------------------------

def test_curated_case_has_access_curated(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    (s.cases_root / "kolam").mkdir()
    _fake_track_a(monkeypatch, [{"case_id": "kolam", "modality": "kolam_image", "title": "Kolam",
                                  "hero": True, "runtime_label": "INTERNET_REFERENCE", "review_status": "pending"}])
    app = create_app(s)
    c = TestClient(app)
    cases = c.get("/api/cases").json()
    kolam = next((c for c in cases if c["case_id"] == "kolam"), None)
    assert kolam is not None
    assert kolam["access"]["collection"] == "curated"
    assert kolam["access"]["library_status"] == "published"


# --- Test 7: review gating --------------------------------------------------------------------

def test_visitor_b_cannot_review_published_community_skill(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    cdir = _make_community_case(s, owner)

    from anveshan_service.library import LibraryRecord, save
    rec = LibraryRecord(case_id=CID, status="published", collection="community")
    save(s, rec, cdir)

    _fake_track_a(monkeypatch, [])
    app = create_app(s)
    b = TestClient(app, cookies={COOKIE: "b" * 32})
    r = b.post(f"/api/cases/{CID}/review", json={"action": "approve"})
    assert r.status_code == 403
    assert r.json()["error"]["category"] == "NOT_OWNER"


def test_owner_can_review_own_skill(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    owner = "a" * 32
    cdir = _make_community_case(s, owner)
    _fake_track_a(monkeypatch, [])
    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})
    r = a.post(f"/api/cases/{CID}/review", json={"action": "approve"})
    assert r.status_code == 200
    assert r.json()["access"]["owner"] is True  # the creator's panel stays after a review


# --- Test 8: housekeeping protection ---------------------------------------------------------

def _make_entry(data_dir: Path, sub: str, name: str, size: int, age_h: float, now: float) -> Path:
    d = data_dir / sub / name
    d.mkdir(parents=True, exist_ok=True)
    f = d / "blob.bin"
    f.write_bytes(b"x" * size)
    t = now - age_h * 3600
    import os
    os.utime(f, (t, t))
    os.utime(d, (t, t))
    return d


def test_housekeeping_protects_published_case(tmp_path):
    """Housekeeping must not remove a published community case, but removes old private ones."""
    now = time.time()
    data_dir = tmp_path / "data"

    # Old private case
    old_private = _make_entry(data_dir, "cases", "skill~aabbcc111111", 10, 48, now)
    # Old published case (has .library.json with published status)
    old_published = _make_entry(data_dir, "cases", "skill~aabbcc222222", 10, 48, now)
    (old_published / ".library.json").write_text(
        json.dumps({"case_id": "skill~aabbcc222222", "status": "published", "collection": "community"}),
        encoding="utf-8",
    )

    removed = sweep(data_dir, ttl_hours=24, cap_bytes=0, now=now)
    assert old_private in removed
    assert old_published not in removed
    assert old_published.is_dir()


def test_housekeeping_removes_old_private_case(tmp_path):
    now = time.time()
    data_dir = tmp_path / "data"
    old = _make_entry(data_dir, "cases", "skill~private111111", 10, 48, now)
    # No .library.json = private
    removed = sweep(data_dir, ttl_hours=24, cap_bytes=0, now=now)
    assert old in removed
