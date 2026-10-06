"""Fixtures for service tests: temp case packs and fake Track A / Track B modules.

The real ``track_a.api`` / ``track_b.api`` are built in parallel; the service is tested against
fakes that follow docs/plans/service-api.md §2-§3 exactly.
"""

from __future__ import annotations

import json
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from fastapi.testclient import TestClient

from anveshan_service.main import create_app
from anveshan_service.settings import Settings

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 2000 + b"\xff\xd9"


def _source(source_id: str, role: str, path: str, mime: str, **kw: Any) -> Dict[str, Any]:
    d = {
        "source_id": source_id,
        "role": role,
        "mime_type": mime,
        "sha256": "0" * 64,
        "bytes": 1,
        "path": path,
        "creator": "test",
        "license": "CC0",
        "attribution": "test",
        "runtime_label": "INTERNET_REFERENCE",
    }
    d.update(kw)
    return d


def make_case(cases_root: Path, case_id: str = "kolam") -> Path:
    cdir = cases_root / case_id
    (cdir / "source").mkdir(parents=True)
    (cdir / "media" / "cache").mkdir(parents=True)
    (cdir / "knowledge" / "goal_assets").mkdir(parents=True)
    (cdir / "source" / "target.jpg").write_bytes(JPEG)
    (cdir / "source" / "held.jpg").write_bytes(JPEG)
    (cdir / "source" / "secret.jpg").write_bytes(JPEG)
    (cdir / "media" / "cache" / "src.demo.v1.ogv").write_bytes(b"OggS" + b"\x00" * 4000)
    (cdir / "media" / "cache" / "src.audio.v1.ogg").write_bytes(b"OggS" + b"\x01" * 1000)
    (cdir / "knowledge" / "goal_assets" / "kf_01.jpg").write_bytes(JPEG)
    (cdir / "knowledge" / "secret.json").write_text("{}", encoding="utf-8")
    sources = [
        _source("src.target.v1", "target_image", "source/target.jpg", "image/jpeg"),
        _source("src.held.v1", "held_out_reference", "source/held.jpg", "image/jpeg", used_by_system=False),
        _source("src.learner.v1", "learner_attempt", "source/held.jpg", "image/jpeg", used_by_system=False),
        _source("src.research.v1", "expert_demonstration", "source/secret.jpg", "image/jpeg", access_level="research_only"),
        _source("src.demo.v1", "expert_video", "media/cache/src.demo.v1.ogv", "video/ogg"),
        _source("src.audio.v1", "expert_audio", "media/cache/src.audio.v1.ogg", "audio/ogg"),
        _source("src.uncached.v1", "expert_video", "media/cache/src.uncached.v1.ogv", "video/ogg", url="https://example.org/x.ogv"),
    ]
    (cdir / "source" / "source.json").write_text(json.dumps({"case_id": case_id, "sources": sources}), encoding="utf-8")
    return cdir


# ---------------------------------------------------------------------------
# Fake Track A
# ---------------------------------------------------------------------------


class FakeHandoff:
    def __init__(self, case_dir: Path, **extra: Any) -> None:
        self.case_dir = case_dir
        self.extra = extra

    def to_view(self) -> Dict[str, Any]:
        return {"case_id": self.case_dir.name, "review_status": "pending", **self.extra}


def fake_track_a() -> types.ModuleType:
    m = types.ModuleType("track_a.api")
    m.calls = []  # type: ignore[attr-defined]
    m.raise_on_query = None  # type: ignore[attr-defined]

    def list_cases(cases_root: Path, data_dir: Path) -> List[dict]:
        m.calls.append(("list_cases", cases_root, data_dir))
        return [{"case_id": p.name, "title": p.name, "modality": "kolam_image", "hero": True,
                 "runtime_label": "INTERNET_REFERENCE", "review_status": "pending"} for p in sorted(cases_root.iterdir())]

    def load_case(case_dir: Path) -> FakeHandoff:
        m.calls.append(("load_case", case_dir))
        return FakeHandoff(case_dir)

    def build_case(case_dir: Path, ctx: Any, source_id: Optional[str] = None) -> FakeHandoff:
        m.calls.append(("build_case", case_dir, ctx, source_id))
        return FakeHandoff(case_dir, built=True, mode=ctx.mode, source_id=source_id)

    def create_upload_case(cases_root: Path, data_dir: Path, base_case_id: str, file_path: Path, mime: str) -> Path:
        m.calls.append(("create_upload_case", cases_root, data_dir, base_case_id, file_path, mime))
        d = data_dir / "cases" / f"{base_case_id}~{file_path.stem[:12]}"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def answer_query(case_dir: Path, question: str, ctx: Any) -> dict:
        m.calls.append(("answer_query", case_dir, question, ctx))
        if m.raise_on_query is not None:
            raise m.raise_on_query
        return {"answer": "loops go around dots", "cited_claim_ids": ["CLM-1"], "evidence": [], "sufficient": True,
                "run": {"mode": ctx.mode}}

    def apply_review(case_dir: Path, action: dict) -> FakeHandoff:
        m.calls.append(("apply_review", case_dir, action))
        return FakeHandoff(case_dir, review_status_after=action["action"])

    for f in (list_cases, load_case, build_case, create_upload_case, answer_query, apply_review):
        setattr(m, f.__name__, f)
    return m


# ---------------------------------------------------------------------------
# Fake Track B
# ---------------------------------------------------------------------------


@dataclass
class FakeSession:
    session_id: str
    case_id: str
    learner_name: str
    state: str = "STARTED"
    attempts: List[Dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        return {"session_id": self.session_id, "case_id": self.case_id, "learner_name": self.learner_name,
                "state": self.state, "attempts": self.attempts}


class FakeResult:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload

    def to_json(self) -> Dict[str, Any]:
        return self.payload


def fake_track_b() -> types.ModuleType:
    m = types.ModuleType("track_b.api")
    m.media = []  # type: ignore[attr-defined]
    m.ctx = []  # type: ignore[attr-defined]

    def start_session(case_dir: Path, learner_name: str, data_dir: Path, *, clock: Any = None, ids: Any = None) -> FakeSession:
        return FakeSession(session_id=f"sess.{case_dir.name.replace('~', '-')}.0001", case_id=case_dir.name, learner_name=learner_name)

    def save_session(session: FakeSession, data_dir: Path) -> None:
        p = data_dir / "sessions" / f"{session.session_id}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(session.to_json()), encoding="utf-8")

    def load_session(session_id: str, data_dir: Path) -> FakeSession:
        p = data_dir / "sessions" / f"{session_id}.json"
        d = json.loads(p.read_text(encoding="utf-8"))  # FileNotFoundError when unknown
        return FakeSession(**d)

    def submit_attempt(session: FakeSession, media: Any, ctx: Any) -> FakeResult:
        m.media.append(media)
        m.ctx.append(ctx)
        n = len(session.attempts) + 1
        session.state = "BASELINE_DONE" if n == 1 else "RETRY_DONE"
        session.attempts.append({"n": n, "kind": media.kind})
        return FakeResult({"attempt": {"attempt_id": f"attempt.{session.case_id}.{n}"}, "evaluation": {},
                           "trajectory": {"curve": [[0, 0], [1, 1]]}, "metrics": {}, "first_divergence": None,
                           "feedback": None, "drill": None, "runtime_class": "DETERMINISTIC", "warnings": [],
                           "run_keys": [], "mode": ctx.mode})

    def complete_session(session: FakeSession) -> FakeResult:
        session.state = "COMPLETED"
        return FakeResult({"bundle": {}, "transmission_record": {"transmission_id": f"tx.{session.case_id}"},
                           "comparison": {"transitions": {}}})

    for f in (start_session, save_session, load_session, submit_attempt, complete_session):
        setattr(m, f.__name__, f)
    return m


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    cases_root = tmp_path / "cases"
    make_case(cases_root, "kolam")
    make_case(cases_root, "origami")
    return Settings(mode="recorded", cases_root=cases_root, data_dir=tmp_path / "data", max_upload_mb=1.0,
                    cors_origins=["http://localhost:5173"], static_dir=None)


@pytest.fixture
def tracks(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    a, b = fake_track_a(), fake_track_b()
    monkeypatch.setitem(sys.modules, "track_a.api", a)
    monkeypatch.setitem(sys.modules, "track_b.api", b)
    monkeypatch.setitem(sys.modules, "track_b.intake", None)  # force the direct AttemptMedia path by default
    return types.SimpleNamespace(a=a, b=b)


@pytest.fixture
def client(settings: Settings, tracks: types.SimpleNamespace) -> TestClient:
    return TestClient(create_app(settings), raise_server_exceptions=False)
