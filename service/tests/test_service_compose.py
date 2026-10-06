"""Tests for POST /api/compose endpoints (monkeypatched composer, no live calls)."""

from __future__ import annotations

import io
import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from anveshan_service.main import create_app
from anveshan_service.settings import Settings

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 2000 + b"\xff\xd9"

# ---------------------------------------------------------------------------
# Minimal Draft view builder
# ---------------------------------------------------------------------------


def _make_draft_view(
    draft_id: str = "abcd1234abcd1234",
    refused: bool = False,
    proposal: Optional[dict] = None,
    warnings: Optional[list] = None,
) -> dict:
    return {
        "draft_id": draft_id,
        "probe": None,
        "intake": {"safety": {"decision": "ok", "notices": [], "policy": "policy_v1"}, "teachable": "yes", "teachable_reason": "good", "skill_kind": "art"},
        "proposal": proposal,
        "refused": refused,
        "refusal_message": "We can't use this file: weapons" if refused else None,
        "warnings": warnings or [],
        "structure_labels": {},
        "specialist_labels": {},
        "perception": {"segments": [], "observations": []},
    }


def _make_case_view() -> dict:
    return {
        "case_id": "my-skill~aabbcc112233",
        "title": "My Skill",
        "modality": "universal",
        "hero": False,
        "manifest": {"case_id": "my-skill~aabbcc112233"},
        "sources": [],
        "goal": None,
        "package": {},
        "rubric": {},
        "task": {},
        "criterion_map": None,
        "observers": None,
        "review_status": "pending",
        "runtime_label": "UPLOAD",
        "warnings": [],
        "versions": {},
        "lesson": {},
        "profile": None,
    }


# ---------------------------------------------------------------------------
# Fake track_a composer
# ---------------------------------------------------------------------------


class FakeDraft:
    def __init__(self, view: dict):
        self._view = view

    def to_view(self) -> dict:
        return self._view


def _fake_composer_module(
    create_draft_response: Optional[dict] = None,
    load_draft_response: Optional[dict] = None,
    refine_draft_response: Optional[dict] = None,
    create_case_dir: Optional[str] = None,
    create_draft_fail: bool = False,
    load_draft_fail: bool = False,
) -> types.ModuleType:
    mod = types.ModuleType("track_a.composer")

    def create_draft(data_dir, file_path, mime, ctx, *, title_hint=None, description=None, rights_confirmed=False):
        if not rights_confirmed:
            from tracks.common.models import AnveshanFailure, FailureCategory
            raise AnveshanFailure(FailureCategory.INVALID_INPUT, "rights required")
        if create_draft_fail:
            from tracks.common.models import AnveshanFailure, FailureCategory
            raise AnveshanFailure(FailureCategory.INVALID_INPUT, "create_draft failed")
        view = create_draft_response or _make_draft_view()
        return FakeDraft(view)

    def load_draft(data_dir, draft_id):
        if load_draft_fail:
            from tracks.common.models import AnveshanFailure, FailureCategory
            raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"draft {draft_id} not found")
        view = load_draft_response or _make_draft_view(draft_id=draft_id)
        return FakeDraft(view)

    def refine_draft(data_dir, draft_id, ctx, *, title, description):
        view = refine_draft_response or _make_draft_view(draft_id=draft_id)
        return FakeDraft(view)

    def create_case_from_draft(cases_root, data_dir, draft_id, edits):
        if create_case_dir:
            return Path(create_case_dir)
        return Path(str(data_dir) + "/cases/test-case~aabbcc112233")

    mod.create_draft = create_draft
    mod.load_draft = load_draft
    mod.refine_draft = refine_draft
    mod.create_case_from_draft = create_case_from_draft
    return mod


def _fake_track_a_module(case_view: Optional[dict] = None) -> types.ModuleType:
    mod = types.ModuleType("track_a.api")

    class FakeHandoff:
        def to_view(self):
            return case_view or _make_case_view()

    def build_case(case_dir, ctx, source_id=None):
        return FakeHandoff()

    def load_case(case_dir):
        return FakeHandoff()

    def list_cases(cases_root, data_dir):
        return []

    mod.build_case = build_case
    mod.load_case = load_case
    mod.list_cases = list_cases
    return mod


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path):
    settings = Settings(
        mode="recorded",
        cases_root=tmp_path / "cases",
        data_dir=tmp_path / "data",
        max_upload_mb=10.0,
        cors_origins=[],
        static_dir=None,
    )
    app = create_app(settings)
    (tmp_path / "cases").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    return TestClient(app)


def _with_fake_composer(client, monkeypatch, **kwargs):
    """Inject fake modules into sys.modules for the test."""
    fake_composer = _fake_composer_module(**kwargs)
    fake_track_a = _fake_track_a_module()
    # Patch via sys.modules
    old_composer = sys.modules.get("track_a.composer")
    old_track_a = sys.modules.get("track_a.api")
    sys.modules["track_a.composer"] = fake_composer
    sys.modules["track_a.api"] = fake_track_a
    yield
    if old_composer is None:
        sys.modules.pop("track_a.composer", None)
    else:
        sys.modules["track_a.composer"] = old_composer
    if old_track_a is None:
        sys.modules.pop("track_a.api", None)
    else:
        sys.modules["track_a.api"] = old_track_a


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_analyze_returns_200_on_success(client, tmp_path, monkeypatch):
    fake_composer = _fake_composer_module(create_draft_response=_make_draft_view())
    monkeypatch.setitem(sys.modules, "track_a.composer", fake_composer)

    response = client.post(
        "/api/compose/analyze",
        data={"title": "Test", "rights_confirmed": "true"},
        files={"file": ("test.jpg", JPEG, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "draft_id" in data
    assert data["refused"] is False


def test_analyze_refused_draft_returns_200(client, tmp_path, monkeypatch):
    """A refused draft should still return HTTP 200 (not an error)."""
    fake_composer = _fake_composer_module(
        create_draft_response=_make_draft_view(refused=True)
    )
    monkeypatch.setitem(sys.modules, "track_a.composer", fake_composer)

    response = client.post(
        "/api/compose/analyze",
        data={"title": "Test", "rights_confirmed": "true"},
        files={"file": ("bad.jpg", JPEG, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["refused"] is True
    assert data["refusal_message"] is not None


def test_analyze_without_rights_returns_400(client, tmp_path, monkeypatch):
    """Without rights_confirmed=true, should return 400 or raise."""
    fake_composer = _fake_composer_module()
    monkeypatch.setitem(sys.modules, "track_a.composer", fake_composer)

    response = client.post(
        "/api/compose/analyze",
        data={"title": "Test", "rights_confirmed": "false"},
        files={"file": ("test.jpg", JPEG, "image/jpeg")},
    )
    assert response.status_code in (400, 422)


def test_get_draft_found(client, tmp_path, monkeypatch):
    """GET /{draft_id} returns 200 when draft exists."""
    draft_id = "abcd1234abcd1234"
    fake_composer = _fake_composer_module(load_draft_response=_make_draft_view(draft_id=draft_id))
    monkeypatch.setitem(sys.modules, "track_a.composer", fake_composer)

    response = client.get(f"/api/compose/{draft_id}")
    assert response.status_code == 200
    assert response.json()["draft_id"] == draft_id


def test_get_draft_not_found(client, tmp_path, monkeypatch):
    """GET /{draft_id} returns 404 when draft does not exist."""
    fake_composer = _fake_composer_module(load_draft_fail=True)
    monkeypatch.setitem(sys.modules, "track_a.composer", fake_composer)

    response = client.get("/api/compose/abcd1234abcd1234")
    assert response.status_code == 404


def test_get_draft_invalid_id(client, tmp_path, monkeypatch):
    """GET with invalid draft_id format returns 400."""
    fake_composer = _fake_composer_module()
    monkeypatch.setitem(sys.modules, "track_a.composer", fake_composer)

    response = client.get("/api/compose/not-a-valid-id!!")
    assert response.status_code == 400


def test_refine_draft(client, tmp_path, monkeypatch):
    """POST /{draft_id}/refine returns 200 with an updated view."""
    draft_id = "abcd1234abcd1234"
    fake_composer = _fake_composer_module(
        refine_draft_response=_make_draft_view(draft_id=draft_id, proposal={"confirmed_by_user": False})
    )
    monkeypatch.setitem(sys.modules, "track_a.composer", fake_composer)

    response = client.post(
        f"/api/compose/{draft_id}/refine",
        json={"title": "Refined Title", "description": "A grid drawing skill"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["draft_id"] == draft_id


def test_create_case_returns_case_view(client, tmp_path, monkeypatch):
    """POST /{draft_id}/create should return a case view."""
    draft_id = "abcd1234abcd1234"
    case_dir = tmp_path / "data" / "cases" / "my-skill~aabbcc112233"
    case_dir.mkdir(parents=True, exist_ok=True)
    fake_composer = _fake_composer_module(create_case_dir=str(case_dir))
    fake_track_a = _fake_track_a_module()
    monkeypatch.setitem(sys.modules, "track_a.composer", fake_composer)
    monkeypatch.setitem(sys.modules, "track_a.api", fake_track_a)

    response = client.post(
        f"/api/compose/{draft_id}/create",
        json={"title": "My Skill"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "case_id" in data
