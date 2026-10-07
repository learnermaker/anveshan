"""Public-demo protections: mode override, rate limits, visitor isolation, review gating,
housekeeping, the daily live-call budget and the live read-through cache (no live calls)."""

from __future__ import annotations

import json
import os
import sys
import time
import types
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from anveshan_service.housekeeping import sweep
from anveshan_service.limits import TokenBucket, route_class
from anveshan_service.main import create_app
from anveshan_service.settings import Settings
from anveshan_service.visitors import COOKIE, OWNERS_FILE

CID = "my-skill~aabbccddeeff"


def _settings(tmp_path: Path, **kw) -> Settings:
    (tmp_path / "cases").mkdir(exist_ok=True)
    (tmp_path / "data").mkdir(exist_ok=True)
    base = dict(mode="recorded", cases_root=tmp_path / "cases", data_dir=tmp_path / "data", static_dir=None)
    base.update(kw)
    return Settings(**base)


def _fake_track_a(monkeypatch, cases):
    mod = types.ModuleType("track_a.api")

    class _View:
        def __init__(self, cid):
            self.cid = cid

        def to_view(self):
            return {"case_id": self.cid}

    mod.list_cases = lambda cases_root, data_dir: [dict(c) for c in cases]
    mod.load_case = lambda cdir: _View(Path(cdir).name)
    mod.apply_review = lambda cdir, action: _View(Path(cdir).name)
    monkeypatch.setitem(sys.modules, "track_a.api", mod)


# --- mode override -----------------------------------------------------------------------------


def test_mode_override_ignored_when_disabled(tmp_path):
    from anveshan_service.deps import get_mode

    class Req:
        class app:
            class state:
                settings = _settings(tmp_path, allow_mode_override=False)

    assert get_mode(Req, "live") == "recorded"
    Req.app.state.settings = _settings(tmp_path, allow_mode_override=True)
    assert get_mode(Req, "live") == "live"


def test_cloud_run_defaults_are_strict(monkeypatch, tmp_path):
    monkeypatch.setenv("K_SERVICE", "anveshan")
    for k in ("ANVESHAN_ALLOW_MODE_OVERRIDE", "ANVESHAN_CURATED_REVIEW_OPEN", "ANVESHAN_DATA_TTL_H"):
        monkeypatch.delenv(k, raising=False)
    s = Settings.from_env(env_file=None)
    assert s.allow_mode_override is False
    assert s.curated_review_open is False
    assert s.rate_limits["compose"] == 6 and s.rate_limits["attempt"] == 30
    assert s.data_ttl_hours == 6.0 and s.secure_cookies is True


def test_local_defaults_are_open(monkeypatch):
    monkeypatch.delenv("K_SERVICE", raising=False)
    for k in ("ANVESHAN_ALLOW_MODE_OVERRIDE", "ANVESHAN_CURATED_REVIEW_OPEN", "ANVESHAN_DATA_TTL_H", "ANVESHAN_DATA_CAP_MB"):
        monkeypatch.delenv(k, raising=False)
    s = Settings.from_env(env_file=None)
    assert s.allow_mode_override is True and s.rate_limits == {} and s.data_ttl_hours == 0


# --- rate limits -------------------------------------------------------------------------------


def test_route_classes():
    assert route_class("POST", "/api/compose/analyze") == "compose"
    assert route_class("POST", "/api/sessions/s1/attempts") == "attempt"
    assert route_class("POST", "/api/sessions/s1/attempts/sample/good") == "attempt"
    assert route_class("POST", "/api/cases/kolam/query") == "query"
    assert route_class("GET", "/api/cases") is None


def test_token_bucket_refills():
    now = [0.0]
    b = TokenBucket(2, clock=lambda: now[0])
    assert b.take("ip")[0] and b.take("ip")[0]
    ok, wait = b.take("ip")
    assert not ok and 1700 < wait <= 1800
    now[0] += 1800
    assert b.take("ip")[0]
    assert b.take("other")[0]  # buckets are per client


def test_rate_limited_route_returns_429(tmp_path, monkeypatch):
    _fake_track_a(monkeypatch, [])
    client = TestClient(create_app(_settings(tmp_path, rate_limits={"query": 1})))
    first = client.post("/api/cases/kolam/query", json={"question": "x"})
    assert first.status_code != 429
    second = client.post("/api/cases/kolam/query", json={"question": "x"})
    assert second.status_code == 429
    body = second.json()["error"]
    assert body["category"] == "RATE_LIMITED" and body["details"]["retry_after_s"] > 0
    assert "Retry-After" in second.headers


# --- visitor isolation -------------------------------------------------------------------------


def _owned_case(settings: Settings, owner: str) -> Path:
    d = settings.data_dir / "cases" / CID
    d.mkdir(parents=True)
    (d / OWNERS_FILE).write_text(json.dumps({"owners": [owner]}), encoding="utf-8")
    return d


def test_visitor_cookie_is_minted_once(tmp_path, monkeypatch):
    _fake_track_a(monkeypatch, [])
    client = TestClient(create_app(_settings(tmp_path)))
    r = client.get("/api/cases")
    assert COOKIE in r.cookies
    r2 = client.get("/api/cases")
    assert COOKIE not in r2.cookies  # already set; not re-minted


def test_composed_case_private_to_owner(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    _fake_track_a(monkeypatch, [{"case_id": "kolam"}, {"case_id": CID}])
    owner = "a" * 32
    _owned_case(s, owner)
    app = create_app(s)
    a = TestClient(app, cookies={COOKIE: owner})
    b = TestClient(app, cookies={COOKIE: "b" * 32})
    assert [c["case_id"] for c in a.get("/api/cases").json()] == ["kolam", CID]
    assert [c["case_id"] for c in b.get("/api/cases").json()] == ["kolam"]
    assert a.get(f"/api/cases/{CID}").status_code == 200
    assert b.get(f"/api/cases/{CID}").status_code == 404


def test_legacy_case_without_owners_stays_visible(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    _fake_track_a(monkeypatch, [{"case_id": CID}])
    (s.data_dir / "cases" / CID).mkdir(parents=True)
    assert TestClient(create_app(s)).get(f"/api/cases/{CID}").status_code == 200


def test_isolation_can_be_disabled(tmp_path, monkeypatch):
    s = _settings(tmp_path, isolate_visitors=False)
    _fake_track_a(monkeypatch, [{"case_id": CID}])
    _owned_case(s, "a" * 32)
    assert TestClient(create_app(s), cookies={COOKIE: "b" * 32}).get(f"/api/cases/{CID}").status_code == 200


def test_draft_private_to_owner(tmp_path, monkeypatch):
    s = _settings(tmp_path)
    ddir = s.data_dir / "drafts" / "abcd1234abcd1234"
    ddir.mkdir(parents=True)
    (ddir / OWNERS_FILE).write_text(json.dumps({"owners": ["a" * 32]}), encoding="utf-8")
    mod = types.ModuleType("track_a.composer")

    class D:
        def to_view(self):
            return {"draft_id": "abcd1234abcd1234"}

    mod.load_draft = lambda data_dir, draft_id: D()
    monkeypatch.setitem(sys.modules, "track_a.composer", mod)
    app = create_app(s)
    assert TestClient(app, cookies={COOKIE: "a" * 32}).get("/api/compose/abcd1234abcd1234").status_code == 200
    assert TestClient(app, cookies={COOKIE: "b" * 32}).get("/api/compose/abcd1234abcd1234").status_code == 404


# --- review gating -----------------------------------------------------------------------------


def test_curated_review_needs_token_when_closed(tmp_path, monkeypatch):
    s = _settings(tmp_path, curated_review_open=False, review_token="t0ken-value")
    (s.cases_root / "kolam").mkdir()
    _fake_track_a(monkeypatch, [])
    client = TestClient(create_app(s))
    body = {"action": "approve", "reviewer": "x"}
    r = client.post("/api/cases/kolam/review", json=body)
    assert r.status_code == 403 and r.json()["error"]["category"] == "REVIEW_DISABLED"
    assert client.post("/api/cases/kolam/review", json=body, headers={"X-Review-Token": "wrong"}).status_code == 403
    assert client.post("/api/cases/kolam/review", json=body, headers={"X-Review-Token": "t0ken-value"}).status_code == 200


def test_own_composed_case_review_allowed_when_closed(tmp_path, monkeypatch):
    s = _settings(tmp_path, curated_review_open=False)
    _fake_track_a(monkeypatch, [])
    _owned_case(s, "a" * 32)
    client = TestClient(create_app(s), cookies={COOKIE: "a" * 32})
    assert client.post(f"/api/cases/{CID}/review", json={"action": "approve"}).status_code == 200


# --- housekeeping ------------------------------------------------------------------------------


def _entry(root: Path, sub: str, name: str, size: int, age_h: float, now: float) -> Path:
    d = root / sub / name
    d.mkdir(parents=True)
    f = d / "blob.bin"
    f.write_bytes(b"x" * size)
    t = now - age_h * 3600
    os.utime(f, (t, t))
    os.utime(d, (t, t))
    return d


def test_sweep_ttl_and_cap(tmp_path):
    now = time.time()
    old = _entry(tmp_path, "drafts", "old", 10, 10, now)
    mid = _entry(tmp_path, "uploads", "mid", 600, 2, now)
    new = _entry(tmp_path, "cases", "new", 600, 0.1, now)
    keep_other = _entry(tmp_path, "scratch", "untouched", 10, 100, now)
    removed = sweep(tmp_path, ttl_hours=6, cap_bytes=1000, now=now)
    assert old in removed and mid in removed  # TTL, then oldest-first eviction to the cap
    assert new.exists() and keep_other.exists()


# --- gateway: daily budget and live cache ------------------------------------------------------


class _Resp:
    text = '{"ok": true}'


class _FakeClient:
    def __init__(self):
        self.calls = 0
        outer = self

        class Models:
            def generate_content(self, **kw):
                outer.calls += 1
                return _Resp()

        self.models = Models()


def _gateway(tmp_path, client):
    from tracks.common.models import ModelGateway, ModelRegistry, RunStore

    return ModelGateway("live", RunStore([tmp_path / "runs"]), registry=ModelRegistry({"vision_fast": "m"}), client=client)


def _call(gw, version="v1"):
    from pydantic import BaseModel

    class Out(BaseModel):
        ok: bool

    return gw.generate_json(model_key="vision_fast", prompt_id="p", prompt_version=version, prompt_text="hi", schema=Out)


def test_live_cache_reuses_identical_call(tmp_path, monkeypatch):
    monkeypatch.delenv("ANVESHAN_LIVE_CACHE", raising=False)
    monkeypatch.delenv("ANVESHAN_DAILY_CALL_BUDGET", raising=False)
    client = _FakeClient()
    gw = _gateway(tmp_path, client)
    first = _call(gw)
    second = _call(gw)
    assert client.calls == 1
    assert first.metadata.runtime_class == "LIVE"
    assert second.metadata.runtime_class == "RECORDED_LIVE" and "live_cache_hit" in second.metadata.notes
    _call(gw, version="v2")  # a prompt version bump misses the cache
    assert client.calls == 2


def test_live_cache_can_be_disabled(tmp_path, monkeypatch):
    monkeypatch.setenv("ANVESHAN_LIVE_CACHE", "0")
    monkeypatch.delenv("ANVESHAN_DAILY_CALL_BUDGET", raising=False)
    client = _FakeClient()
    gw = _gateway(tmp_path, client)
    _call(gw)
    _call(gw)
    assert client.calls == 2


def test_daily_budget_blocks_live_calls_only(tmp_path, monkeypatch):
    from tracks.common.models import DAILY_BUDGET, ModelError

    monkeypatch.setenv("ANVESHAN_DAILY_CALL_BUDGET", "1")
    monkeypatch.delenv("ANVESHAN_LIVE_CACHE", raising=False)
    monkeypatch.setattr(DAILY_BUDGET, "_day", "")
    client = _FakeClient()
    gw = _gateway(tmp_path, client)
    _call(gw)  # uses the single budgeted call
    _call(gw)  # cache hit: free
    with pytest.raises(ModelError) as exc:
        _call(gw, version="v2")
    assert exc.value.details["reason"] == "daily_budget"
    assert client.calls == 1


# --- concurrency -------------------------------------------------------------------------------


def test_same_draft_writes_never_interleave(tmp_path, monkeypatch):
    import threading

    s = _settings(tmp_path)
    active = {"now": 0, "max": 0}
    guard = threading.Lock()
    mod = types.ModuleType("track_a.composer")

    class D:
        def to_view(self):
            return {"draft_id": "0123456789abcdef"}

    def create_draft(data_dir, file_path, mime, ctx, **kw):
        with guard:
            active["now"] += 1
            active["max"] = max(active["max"], active["now"])
        time.sleep(0.2)
        with guard:
            active["now"] -= 1
        return D()

    mod.create_draft = create_draft
    monkeypatch.setitem(sys.modules, "track_a.composer", mod)
    client = TestClient(create_app(s))
    same = b"\xff\xd8same-bytes\xff\xd9"

    def post():
        client.post("/api/compose/analyze", data={"rights_confirmed": "true"}, files={"file": ("a.jpg", same, "image/jpeg")})

    threads = [threading.Thread(target=post) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert active["max"] == 1
