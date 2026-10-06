"""Media serving (held-out exclusion, content types, Range) and the SPA static app."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from anveshan_service.main import create_app
from anveshan_service.settings import Settings

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 2000 + b"\xff\xd9"  # same bytes as conftest.make_case


def test_serves_used_source(client):
    r = client.get("/api/media/kolam/src.target.v1")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg" and r.content == JPEG


@pytest.mark.parametrize("source_id,ctype", [("src.demo.v1", "video/ogg"), ("src.audio.v1", "audio/ogg")])
def test_ogg_content_types_and_range(client, source_id, ctype):
    r = client.get(f"/api/media/origami/{source_id}")
    assert r.status_code == 200 and r.headers["content-type"] == ctype
    assert r.headers.get("accept-ranges") == "bytes"
    r = client.get(f"/api/media/origami/{source_id}", headers={"Range": "bytes=0-3"})
    assert r.status_code == 206 and r.content == b"OggS"
    assert r.headers["content-range"].startswith("bytes 0-3/")


@pytest.mark.parametrize("source_id", ["src.held.v1", "src.learner.v1", "src.research.v1", "src.missing.v1"])
def test_never_serves_held_out_or_unknown(client, source_id):
    r = client.get(f"/api/media/kolam/{source_id}")
    assert r.status_code == 404
    assert r.json()["error"]["category"] == "MISSING_EVIDENCE"
    assert r.content != JPEG


def test_uncached_source_is_404(client):
    r = client.get("/api/media/kolam/src.uncached.v1")
    assert r.status_code == 404 and "not cached" in r.json()["error"]["message"]


def test_goal_assets(client):
    r = client.get("/api/media/origami/goal/kf_01.jpg")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert client.get("/api/media/origami/goal/kf_99.jpg").status_code == 404
    assert client.get("/api/media/origami/goal/..secret.json").status_code == 400
    assert client.get("/api/media/origami/goal/..%2Fsecret.json").status_code in (400, 404)
    assert client.get("/api/media/origami/goal/.hidden").status_code == 400


def test_media_unknown_case(client):
    assert client.get("/api/media/nope/src.target.v1").status_code == 404
    assert client.get("/api/media/NOPE/src.target.v1").status_code == 400


@pytest.fixture
def spa_client(settings, tracks, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=root></div>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("secret", encoding="utf-8")
    s = Settings(**{**settings.__dict__, "static_dir": dist})
    return TestClient(create_app(s), raise_server_exceptions=False)


def test_spa_index_and_fallback(spa_client):
    for path in ("/", "/cases/kolam", "/sessions/x/attempt"):
        r = spa_client.get(path)
        assert r.status_code == 200 and "id=root" in r.text and r.headers["content-type"].startswith("text/html")
    r = spa_client.get("/assets/app.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]


def test_spa_does_not_shadow_api(spa_client):
    r = spa_client.get("/api/unknown/route")
    assert r.status_code == 404 and r.json()["error"]["category"] == "MISSING_EVIDENCE"
    assert spa_client.get("/api/health").json()["ok"] is True


def test_spa_no_traversal(spa_client):
    r = spa_client.get("/..%2Foutside.txt")
    assert "secret" not in r.text


def test_no_static_dir_means_no_root(client):
    assert client.get("/").status_code == 404
