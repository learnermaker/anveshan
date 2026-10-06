"""Session routes and the Track B attempt-media adapter."""

from __future__ import annotations

import hashlib
import json
import sys
import types

from fastapi.testclient import TestClient

from anveshan_service.main import create_app

TRACE = json.dumps({"canvas": {"width": 492, "height": 499}, "goal_case_id": "kolam", "goal_version": 1,
                    "strokes": [{"points": [[1, 2, 0], [3, 4, 10]]}], "duration_ms": 10}).encode()


def _start(client, case_id="kolam"):
    r = client.post("/api/sessions", json={"case_id": case_id, "learner_name": "Asha"})
    assert r.status_code == 200, r.text
    return r.json()


def test_start_and_get_session(client):
    body = _start(client)
    assert body == {"session_id": "sess.kolam.0001", "state": "STARTED"}
    r = client.get(f"/api/sessions/{body['session_id']}")
    assert r.status_code == 200 and r.json()["learner_name"] == "Asha" and r.json()["attempts"] == []


def test_start_session_validation(client):
    assert client.post("/api/sessions", json={"case_id": "kolam", "learner_name": "  "}).status_code == 400
    assert client.post("/api/sessions", json={"case_id": "kolam"}).status_code == 400
    assert client.post("/api/sessions", json={"case_id": "../x", "learner_name": "A"}).status_code == 400
    assert client.post("/api/sessions", json={"case_id": "nope", "learner_name": "A"}).status_code == 404


def test_unknown_and_invalid_session(client):
    r = client.get("/api/sessions/sess.unknown.9")
    assert r.status_code == 404 and r.json()["error"]["category"] == "MISSING_EVIDENCE"
    assert client.get("/api/sessions/bad%20id!").status_code == 400
    assert client.get("/api/sessions/..%2F..%2Fsecret").status_code in (400, 404)


def test_trace_attempt_with_raster(client, tracks, settings):
    sid = _start(client)["session_id"]
    raster = b"\x89PNG" + b"r" * 300
    r = client.post(
        f"/api/sessions/{sid}/attempts",
        data={"kind": "trace"},
        files={"file": ("trace.json", TRACE, "application/json"), "raster": ("trace.png", raster, "image/png")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["attempt"]["attempt_id"] == "attempt.kolam.1"
    assert r.json()["mode"] == "recorded"
    media = tracks.b.media[-1]
    digest = hashlib.sha256(TRACE).hexdigest()
    assert media.kind == "trace" and media.sha256 == digest and media.source_id == f"upload.{digest[:12]}"
    assert media.path == settings.data_dir / "uploads" / f"{digest}.json" and media.mime_type == "application/json"
    assert set(media.extra) == {"raster"} and media.extra["raster"].read_bytes() == raster
    ctx = tracks.b.ctx[-1]
    assert ctx.case_dir == settings.cases_root / "kolam" and ctx.data_dir == settings.data_dir
    # state persisted via save_session
    assert client.get(f"/api/sessions/{sid}").json()["state"] == "BASELINE_DONE"


def test_audio_attempt_live_mode_and_optional_video(client, tracks):
    sid = _start(client, "origami")["session_id"]
    r = client.post(
        f"/api/sessions/{sid}/attempts?mode=live",
        data={"kind": "audio"},
        files={"file": ("take.wav", b"RIFF" + b"a" * 100, "audio/wav"), "video": ("take.webm", b"webm" * 10, "video/webm")},
    )
    assert r.status_code == 200, r.text
    assert r.json()["mode"] == "live"
    media = tracks.b.media[-1]
    assert media.kind == "audio" and media.mime_type == "audio/wav" and set(media.extra) == {"video"}


def test_attempt_bad_kind_and_missing_file(client):
    sid = _start(client)["session_id"]
    r = client.post(f"/api/sessions/{sid}/attempts", data={"kind": "smell"}, files={"file": ("a.bin", b"x", "x/y")})
    assert r.status_code == 400
    r = client.post(f"/api/sessions/{sid}/attempts", data={"kind": "image"})
    assert r.status_code == 400


def test_attempt_unknown_session_is_404(client):
    r = client.post("/api/sessions/sess.none.1/attempts", data={"kind": "image"}, files={"file": ("a.jpg", b"x", "image/jpeg")})
    assert r.status_code == 404


def test_attempt_over_limit_is_413(client, settings):
    sid = _start(client)["session_id"]
    big = b"v" * (settings.max_upload_bytes + 1)
    r = client.post(f"/api/sessions/{sid}/attempts", data={"kind": "video"}, files={"file": ("v.mp4", big, "video/mp4")})
    assert r.status_code == 413


def test_intake_from_upload_is_preferred(client, tracks, monkeypatch):
    seen = {}

    def from_upload(**kw):
        seen.update(kw)
        return types.SimpleNamespace(kind=kw["kind"], path=kw["path"], via="intake")

    intake = types.ModuleType("track_b.intake")
    intake.from_upload = from_upload
    monkeypatch.setitem(sys.modules, "track_b.intake", intake)
    sid = _start(client)["session_id"]
    r = client.post(f"/api/sessions/{sid}/attempts", data={"kind": "image"}, files={"file": ("p.jpg", b"jpgdata", "image/jpeg")})
    assert r.status_code == 200, r.text
    assert tracks.b.media[-1].via == "intake"
    assert seen["kind"] == "image" and seen["mime_type"] == "image/jpeg" and seen["extra"] == {}


def test_complete_session(client):
    sid = _start(client)["session_id"]
    client.post(f"/api/sessions/{sid}/attempts", data={"kind": "image"}, files={"file": ("p.jpg", b"jpg1", "image/jpeg")})
    r = client.post(f"/api/sessions/{sid}/complete")
    assert r.status_code == 200
    assert set(r.json()) == {"bundle", "transmission_record", "comparison"}
    assert client.get(f"/api/sessions/{sid}").json()["state"] == "COMPLETED"


def test_missing_track_b_is_503(settings, tracks, monkeypatch):
    monkeypatch.setitem(sys.modules, "track_b.api", None)
    c = TestClient(create_app(settings), raise_server_exceptions=False)
    r = c.post("/api/sessions", json={"case_id": "kolam", "learner_name": "A"})
    assert r.status_code == 503 and "track_b.api" in r.json()["error"]["message"]
