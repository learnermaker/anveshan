"""Health, case routes, error mapping and Track A adapter behaviour."""

from __future__ import annotations

import hashlib
import sys

import pytest
from fastapi.testclient import TestClient

from anveshan_service.errors import CATEGORY_STATUS
from anveshan_service.main import create_app
from anveshan_service.paths import check_case_id
from anveshan_service.errors import ServiceError
from tracks.common.models import AnveshanFailure, FailureCategory


def test_health_shape_and_no_secrets(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaTESTSECRETVALUE123")
    monkeypatch.setenv("ANVESHAN_AUDIO_MODEL", "")
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    m = body["models"]
    assert body == {"ok": True, "mode": "recorded", "mode_override": True, "curated_review_open": True,
                    "own_key_supported": True,
                    "steward_enabled": False, "steward_open": False, "data_ttl_hours": 0.0,
                    "models": {"text_image": m["text_image"], "video_frames": m["video_frames"],
                               "vision_fast": m["vision_fast"], "embedding": m["embedding"], "audio": None, "audio_enabled": False}}
    assert "AIzaTESTSECRETVALUE123" not in r.text


def test_health_audio_enabled(client, monkeypatch):
    monkeypatch.setenv("ANVESHAN_AUDIO_MODEL", "some-audio-model")
    assert client.get("/api/health").json()["models"]["audio_enabled"] is True


def test_list_and_get_case(client, tracks, settings):
    r = client.get("/api/cases")
    assert r.status_code == 200
    assert [c["case_id"] for c in r.json()] == ["kolam", "origami"]
    assert tracks.a.calls[0] == ("list_cases", settings.cases_root, settings.data_dir)
    r = client.get("/api/cases/kolam")
    assert r.status_code == 200 and r.json()["case_id"] == "kolam"


@pytest.mark.parametrize("bad", ["Kolam", "kolam~zz", "kolam~0123456789abc", "a b", "...", "kolam.x"])
def test_invalid_case_id_is_400(client, bad):
    r = client.get(f"/api/cases/{bad}")
    assert r.status_code == 400, r.text
    assert r.json()["error"]["category"] == "INVALID_INPUT"


@pytest.mark.parametrize("bad", ["../etc", "..\\x", "kolam/../../x", "", "kolam~../..", "~0123456789ab"])
def test_case_id_validator_rejects_traversal(bad):
    with pytest.raises(ServiceError) as e:
        check_case_id(bad)
    assert e.value.status == 400


def test_encoded_traversal_never_escapes(client):
    for path in ("/api/cases/..%2F..%2Fetc", "/api/cases/%2e%2e", "/api/media/..%2Fkolam/src.target.v1"):
        assert client.get(path).status_code in (400, 404)


def test_unknown_case_is_404(client):
    r = client.get("/api/cases/nope")
    assert r.status_code == 404
    assert r.json()["error"]["category"] == "MISSING_EVIDENCE"


def test_unknown_derived_case_is_404(client):
    assert client.get("/api/cases/kolam~0123456789ab").status_code == 404


def test_build_default_mode_and_override(client, tracks):
    r = client.post("/api/cases/kolam/build")
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "recorded" and r.json()["source_id"] is None
    r = client.post("/api/cases/kolam/build?mode=live", json={"source_id": "src.target.v1"})
    assert r.json()["mode"] == "live" and r.json()["source_id"] == "src.target.v1"
    ctx = tracks.a.calls[-1][2]
    assert ctx.mode == "live" and ctx.case_dir.name == "kolam" and ctx.gateway.mode == "live"


def test_invalid_mode_is_400(client):
    r = client.post("/api/cases/kolam/build?mode=fast")
    assert r.status_code == 400 and r.json()["error"]["category"] == "INVALID_INPUT"


def test_query(client, tracks):
    r = client.post("/api/cases/kolam/query", json={"question": "Why loop around dots?"})
    assert r.status_code == 200
    assert r.json()["cited_claim_ids"] == ["CLM-1"] and r.json()["run"]["mode"] == "recorded"
    assert client.post("/api/cases/kolam/query", json={"question": "   "}).status_code == 400
    assert client.post("/api/cases/kolam/query", json={}).status_code == 400


def test_review(client, tracks):
    r = client.post("/api/cases/kolam/review", json={"action": "approve", "reviewer": "expert", "note": "ok"})
    assert r.status_code == 200 and r.json()["review_status_after"] == "approve"
    assert client.post("/api/cases/kolam/review", json={"action": "delete_everything"}).status_code == 400


@pytest.mark.parametrize(
    "category,status",
    [("INVALID_INPUT", 400), ("MISSING_EVIDENCE", 404), ("REPLAY_MISMATCH", 409), ("HUMAN_REVIEW_REQUIRED", 422),
     ("MODEL_FAILURE", 502), ("MODEL_TIMEOUT", 502), ("CONTRACT_VIOLATION", 500)],
)
def test_failure_mapping(client, tracks, category, status):
    assert CATEGORY_STATUS[category] == status
    tracks.a.raise_on_query = AnveshanFailure(FailureCategory(category), "boom", {"replay_key": "abc"})
    r = client.post("/api/cases/kolam/query", json={"question": "q"})
    assert r.status_code == status
    assert r.json() == {"error": {"category": category, "message": "boom", "details": {"replay_key": "abc"}}}


def test_duck_typed_track_failure_is_mapped(client, tracks):
    class TrackBFailure(Exception):
        def __init__(self):
            super().__init__("x")
            self.category = FailureCategory.REPLAY_MISMATCH
            self.message = "no recorded run"
            self.details = {"api_key": "should-not-leak"}

    tracks.a.raise_on_query = TrackBFailure()
    r = client.post("/api/cases/kolam/query", json={"question": "q"})
    assert r.status_code == 409
    assert r.json()["error"]["details"] == {"api_key": "[REDACTED]"}


def test_unexpected_error_is_generic_500(client, tracks, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaLEAKYSECRET999")
    tracks.a.raise_on_query = RuntimeError("failed with key AIzaLEAKYSECRET999")
    r = client.post("/api/cases/kolam/query", json={"question": "q"})
    assert r.status_code == 500
    assert r.json()["error"]["category"] == "INTERNAL_ERROR"
    assert "AIzaLEAKYSECRET999" not in r.text and "failed with key" not in r.text


def test_secret_redacted_from_failure_message(client, tracks, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "AIzaLEAKYSECRET999")
    tracks.a.raise_on_query = AnveshanFailure(FailureCategory.MODEL_FAILURE, "bad key AIzaLEAKYSECRET999")
    r = client.post("/api/cases/kolam/query", json={"question": "q"})
    assert r.status_code == 502 and "AIzaLEAKYSECRET999" not in r.text


def test_source_upload_creates_derived_case(client, tracks, settings):
    data = b"\xff\xd8\xff" + b"k" * 500
    r = client.post("/api/cases/kolam/sources", files={"file": ("my kolam.JPG", data, "image/jpeg")})
    assert r.status_code == 200, r.text
    digest = hashlib.sha256(data).hexdigest()
    assert r.json() == {"case_id": f"kolam~{digest[:12]}"}
    stored = settings.data_dir / "uploads" / f"{digest}.jpg"
    assert stored.read_bytes() == data
    call = tracks.a.calls[-1]
    assert call[0] == "create_upload_case" and call[3] == "kolam" and call[4] == stored and call[5] == "image/jpeg"
    assert not list((settings.data_dir / "uploads").glob(".part-*"))
    # the derived case resolves under <data_dir>/cases
    r = client.get(f"/api/cases/kolam~{digest[:12]}")
    assert r.status_code == 200 and r.json()["case_id"] == f"kolam~{digest[:12]}"
    # uploading against a derived id uses its base case
    r = client.post(f"/api/cases/kolam~{digest[:12]}/sources", files={"file": ("x.png", b"png-bytes", "image/png")})
    assert r.status_code == 200 and tracks.a.calls[-1][3] == "kolam"


def test_source_upload_unknown_base_is_404(client):
    r = client.post("/api/cases/nope/sources", files={"file": ("x.jpg", b"abc", "image/jpeg")})
    assert r.status_code == 404


def test_upload_over_limit_is_413(client, settings):
    big = b"x" * (settings.max_upload_bytes + 10)
    r = client.post("/api/cases/kolam/sources", files={"file": ("big.jpg", big, "image/jpeg")})
    assert r.status_code == 413
    assert r.json()["error"]["category"] == "INVALID_INPUT"
    assert not list((settings.data_dir / "uploads").glob("*"))


def test_request_body_over_limit_rejected_up_front(tmp_path, tracks):
    from anveshan_service.settings import Settings

    s = Settings(cases_root=tmp_path / "cases", data_dir=tmp_path / "data", max_upload_mb=0.01, static_dir=None)
    c = TestClient(create_app(s), raise_server_exceptions=False)
    r = c.post("/api/cases/kolam/sources", files={"file": ("big.jpg", b"x" * (3 << 20), "image/jpeg")})
    assert r.status_code == 413


def test_empty_upload_is_400(client):
    r = client.post("/api/cases/kolam/sources", files={"file": ("e.jpg", b"", "image/jpeg")})
    assert r.status_code == 400


def test_missing_track_a_is_503_but_health_works(settings, tracks, monkeypatch):
    monkeypatch.setitem(sys.modules, "track_a.api", None)
    c = TestClient(create_app(settings), raise_server_exceptions=False)
    r = c.get("/api/cases")
    assert r.status_code == 503
    assert r.json()["error"]["category"] == "SERVICE_UNAVAILABLE"
    assert "track_a.api" in r.json()["error"]["message"]
    assert c.get("/api/health").status_code == 200


def test_cors_header(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:5173"
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers


def test_unknown_api_route_is_json_404(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404 and "error" in r.json()
