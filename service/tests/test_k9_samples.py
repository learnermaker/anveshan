"""Tests for K9-P4 sample pack and sample routes (service/anveshan_service/samples.py and routes/samples.py).

No live model calls. Fake Track A/B from conftest.py fixtures are used for route tests.
For the real-evaluation tests the actual track_b.api and real case packs are used in recorded mode.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import shutil
import sys
import types
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from anveshan_service.main import create_app
from anveshan_service.routes import samples as samples_routes
from anveshan_service.samples import SAMPLE_ID_RE, Sample, load_pack, load_sources, public_view, sample_paths
from anveshan_service.settings import Settings

# ---------------------------------------------------------------------------
# Repo root — worktree root is parents[2] of service/tests/<file>
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
KOLAM_DIR = REPO_ROOT / "tracks" / "cases" / "kolam"
TABLA_DIR = REPO_ROOT / "tracks" / "cases" / "tabla"

# ---------------------------------------------------------------------------
# Test-local fake tracks (no conftest import needed)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class _FakeSession:
    session_id: str
    case_id: str
    learner_name: str
    state: str = "STARTED"
    attempts: List[Dict[str, Any]] = dataclasses.field(default_factory=list)

    def to_json(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "case_id": self.case_id,
            "learner_name": self.learner_name,
            "state": self.state,
            "attempts": self.attempts,
        }


class _FakeResult:
    def __init__(self, payload: Dict[str, Any]) -> None:
        self.payload = payload

    def to_json(self) -> Dict[str, Any]:
        return self.payload


def _make_fake_track_b() -> types.ModuleType:
    m = types.ModuleType("track_b.api")
    m.media = []  # type: ignore[attr-defined]

    def start_session(case_dir: Path, learner_name: str, data_dir: Path, **kw: Any) -> _FakeSession:
        return _FakeSession(
            session_id=f"sess.{Path(case_dir).name}.0001",
            case_id=Path(case_dir).name,
            learner_name=learner_name,
        )

    def save_session(session: _FakeSession, data_dir: Path) -> None:
        p = data_dir / "sessions" / f"{session.session_id}.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(session.to_json()), encoding="utf-8")

    def load_session(session_id: str, data_dir: Path) -> _FakeSession:
        p = data_dir / "sessions" / f"{session_id}.json"
        d = json.loads(p.read_text(encoding="utf-8"))
        return _FakeSession(**d)

    def submit_attempt(session: _FakeSession, media: Any, ctx: Any) -> _FakeResult:
        m.media.append(media)
        n = len(session.attempts) + 1
        session.state = "BASELINE_DONE" if n == 1 else "RETRY_DONE"
        session.attempts.append({"n": n, "kind": media.kind})
        return _FakeResult({
            "attempt": {"attempt_id": f"attempt.{session.case_id}.{n}"},
            "evaluation": {"passed": True},
            "trajectory": {"curve": [[0, 0], [1, 1]]},
            "metrics": {},
            "first_divergence": None,
            "feedback": None,
            "drill": None,
            "runtime_class": "DETERMINISTIC",
            "warnings": [],
            "run_keys": [],
            "mode": getattr(ctx, "mode", "recorded"),
        })

    def complete_session(session: _FakeSession) -> _FakeResult:
        session.state = "COMPLETED"
        return _FakeResult({"bundle": {}, "transmission_record": {}})

    def intake_attempt(session: _FakeSession, path: Path, kind: str, extra: Any = None) -> Any:
        from anveshan_service.paths import content_type  # noqa: PLC0415
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        return types.SimpleNamespace(
            kind=kind,
            path=path,
            sha256=digest,
            mime_type=content_type(path),
            source_id=f"upload.{digest[:12]}",
            extra={},
        )

    for fn in (start_session, save_session, load_session, submit_attempt, complete_session, intake_attempt):
        setattr(m, fn.__name__, fn)
    return m


def _install_fakes(monkeypatch: pytest.MonkeyPatch):
    """Install minimal fake track_a and track_b into sys.modules."""
    # Minimal fake track_a
    a = types.ModuleType("track_a.api")

    def list_cases(cases_root: Path, data_dir: Path) -> List[dict]:
        return [{"case_id": p.name, "title": p.name, "modality": "kolam_image", "hero": True,
                 "runtime_label": "INTERNET_REFERENCE", "review_status": "pending"}
                for p in sorted(cases_root.iterdir()) if p.is_dir()]

    def load_case(case_dir: Path):
        return types.SimpleNamespace(
            case_dir=case_dir,
            to_view=lambda: {"case_id": case_dir.name, "review_status": "pending"},
        )

    setattr(a, "list_cases", list_cases)
    setattr(a, "load_case", load_case)

    b = _make_fake_track_b()
    monkeypatch.setitem(sys.modules, "track_a.api", a)
    monkeypatch.setitem(sys.modules, "track_b.api", b)
    monkeypatch.setitem(sys.modules, "track_b.intake", None)
    return a, b


def _make_case(cases_root: Path, case_id: str) -> Path:
    """Create a minimal case directory for service tests."""
    import json  # noqa: PLC0415
    JPEG = b"\xff\xd8\xff\xe0" + b"0" * 2000 + b"\xff\xd9"
    cdir = cases_root / case_id
    (cdir / "source").mkdir(parents=True)
    (cdir / "media" / "cache").mkdir(parents=True)
    (cdir / "knowledge" / "goal_assets").mkdir(parents=True)
    (cdir / "source" / "target.jpg").write_bytes(JPEG)
    (cdir / "source" / "held.jpg").write_bytes(JPEG)
    (cdir / "source" / "secret.jpg").write_bytes(JPEG)
    (cdir / "knowledge" / "secret.json").write_text("{}", encoding="utf-8")
    sources = [
        {"source_id": "src.target.v1", "role": "target_image", "mime_type": "image/jpeg",
         "sha256": "0" * 64, "bytes": 1, "path": "source/target.jpg", "creator": "test",
         "license": "CC0", "attribution": "test", "runtime_label": "INTERNET_REFERENCE"},
    ]
    (cdir / "source" / "source.json").write_text(
        json.dumps({"case_id": case_id, "sources": sources}), encoding="utf-8"
    )
    return cdir


def _settings(tmp_path: Path, cases_root: Path) -> Settings:
    return Settings(
        mode="recorded", cases_root=cases_root, data_dir=tmp_path / "data",
        max_upload_mb=10.0, static_dir=None
    )


def _client_with_samples(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    _install_fakes(monkeypatch)
    app = create_app(settings)
    # samples router is now registered in create_app; no explicit include_router needed
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# §5.1 load_pack on committed packs
# ---------------------------------------------------------------------------

class TestLoadPackCommitted:
    def test_kolam_pack_has_three_samples(self):
        pack = load_pack(KOLAM_DIR)
        assert len(pack) == 3

    def test_kolam_qualities(self):
        pack = load_pack(KOLAM_DIR)
        assert {s.quality for s in pack} == {"good", "flawed", "unrelated"}

    def test_kolam_files_exist_and_within_limit(self):
        from anveshan_service.samples import MAX_FILE_BYTES
        for s in load_pack(KOLAM_DIR):
            f = KOLAM_DIR / "samples" / s.file
            assert f.is_file(), f"missing {f}"
            assert f.stat().st_size <= MAX_FILE_BYTES, f"{f} exceeds 2 MB"

    def test_kolam_sample_ids_match_regex(self):
        for s in load_pack(KOLAM_DIR):
            assert SAMPLE_ID_RE.fullmatch(s.sample_id)

    def test_kolam_descriptions_non_empty(self):
        for s in load_pack(KOLAM_DIR):
            assert s.description.strip()

    def test_tabla_pack_has_three_samples(self):
        assert len(load_pack(TABLA_DIR)) == 3

    def test_tabla_qualities(self):
        assert {s.quality for s in load_pack(TABLA_DIR)} == {"good", "flawed", "unrelated"}

    def test_tabla_files_exist_and_within_limit(self):
        from anveshan_service.samples import MAX_FILE_BYTES
        for s in load_pack(TABLA_DIR):
            f = TABLA_DIR / "samples" / s.file
            assert f.is_file() and f.stat().st_size <= MAX_FILE_BYTES

    def test_empty_when_no_samples_dir(self, tmp_path: Path):
        cdir = tmp_path / "empty_case"
        cdir.mkdir()
        assert load_pack(cdir) == []


# ---------------------------------------------------------------------------
# §5.2 GET /api/cases/kolam/samples → 3 items with SampleAttempt keys
# ---------------------------------------------------------------------------

class TestListSamplesRoute:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        cases_root = tmp_path / "cases"
        cdir = _make_case(cases_root, "kolam")
        shutil.copytree(KOLAM_DIR / "samples", cdir / "samples")
        settings = _settings(tmp_path, cases_root)
        self.client = _client_with_samples(settings, monkeypatch)

    def test_returns_three_items(self):
        r = self.client.get("/api/cases/kolam/samples")
        assert r.status_code == 200, r.text
        assert len(r.json()) == 3

    def test_sample_attempt_keys(self):
        expected_keys = {
            "sample_id", "label", "quality", "attempt_kind",
            "description", "preview_url", "synthetic", "credit",
        }
        r = self.client.get("/api/cases/kolam/samples")
        for item in r.json():
            assert set(item.keys()) == expected_keys

    def test_qualities_present(self):
        r = self.client.get("/api/cases/kolam/samples")
        assert {item["quality"] for item in r.json()} == {"good", "flawed", "unrelated"}


# ---------------------------------------------------------------------------
# §5.3 Sample attempt through fake Track B
# ---------------------------------------------------------------------------

class TestSubmitSampleAttempt:
    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        cases_root = tmp_path / "cases"
        cdir = _make_case(cases_root, "kolam")
        shutil.copytree(KOLAM_DIR / "samples", cdir / "samples")
        settings = _settings(tmp_path, cases_root)
        self.client = _client_with_samples(settings, monkeypatch)
        r = self.client.post("/api/sessions", json={"case_id": "kolam", "learner_name": "Tester"})
        assert r.status_code == 200, r.text
        self.session_id = r.json()["session_id"]

    def test_submit_good_sample_returns_200(self):
        r = self.client.post(f"/api/sessions/{self.session_id}/attempts/sample/good")
        assert r.status_code == 200, r.text
        assert "attempt" in r.json()

    def test_sha256_matches_committed_file(self):
        """The media submitted to Track B must hash to the committed file's sha256."""
        b = sys.modules.get("track_b.api")
        before = len(b.media) if b else 0

        r = self.client.post(f"/api/sessions/{self.session_id}/attempts/sample/good")
        assert r.status_code == 200, r.text

        b2 = sys.modules.get("track_b.api")
        if b2 and len(b2.media) > before:
            media = b2.media[-1]
            committed = (KOLAM_DIR / "samples" / "good.trace.json").read_bytes()
            assert media.sha256 == hashlib.sha256(committed).hexdigest()

    def test_unknown_sample_gives_404(self):
        r = self.client.post(f"/api/sessions/{self.session_id}/attempts/sample/nonexistent")
        assert r.status_code == 404

    def test_invalid_sample_id_gives_400_or_404(self):
        r = self.client.post(f"/api/sessions/{self.session_id}/attempts/sample/../bad")
        assert r.status_code in (400, 404)


# ---------------------------------------------------------------------------
# §5.4 Security
# ---------------------------------------------------------------------------

def test_bad_sample_id_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cases_root = tmp_path / "cases"
    _make_case(cases_root, "kolam")
    settings = _settings(tmp_path, cases_root)
    client = _client_with_samples(settings, monkeypatch)
    r = client.get("/api/cases/kolam/samples/..%2F..%2Fsecret")
    assert r.status_code in (400, 404)


# ---------------------------------------------------------------------------
# §5.5 Compose samples
# ---------------------------------------------------------------------------

def test_list_sample_sources():
    sources = load_sources(REPO_ROOT)
    assert len(sources) >= 1
    for s in sources:
        assert "sample_id" in s
        assert "preview_url" in s


def test_source_files_exist():
    sources_json = REPO_ROOT / "tracks" / "samples" / "sources" / "sources.json"
    assert sources_json.is_file(), "sources.json not found"
    data = json.loads(sources_json.read_text(encoding="utf-8"))
    sources_dir = sources_json.parent
    for entry in data.get("sources", []):
        # Support canonical_path (repo-root-relative pointer, single-copy rule)
        canonical = entry.get("canonical_path", "")
        if canonical:
            assert (REPO_ROOT / canonical).is_file(), f"canonical_path missing: {canonical}"
            continue
        fname = entry.get("file", "")
        assert fname, f"source entry missing both 'file' and 'canonical_path': {entry.get('sample_id')}"
        assert (sources_dir / fname).is_file(), f"source file missing: {fname}"


# ---------------------------------------------------------------------------
# §5.5 Real evaluation regression guard
# ---------------------------------------------------------------------------

def _import_track_b_api():
    try:
        import track_b.api as api  # noqa: PLC0415
        return api
    except ImportError:
        return None


@pytest.mark.parametrize("case_id,case_dir_path", [
    ("kolam", KOLAM_DIR),
    ("tabla", TABLA_DIR),
])
def test_real_evaluation_matches_expected(
    case_id: str, case_dir_path: Path, tmp_path: Path
) -> None:
    """Committed samples' `expected` fields must match the real evaluator (recorded mode)."""
    from tracks.common.models import AnveshanFailure  # noqa: PLC0415
    from tracks.common.runtime import RunContext  # noqa: PLC0415

    api = _import_track_b_api()
    if api is None:
        pytest.skip("track_b.api not available")

    pack = load_pack(case_dir_path)
    assert len(pack) == 3, f"Expected 3 samples for {case_id}, got {len(pack)}"

    data_dir = tmp_path / "data"
    data_dir.mkdir()
    ctx = RunContext.create(case_dir_path, data_dir, "recorded")

    for s in pack:
        expected = s.expected or {}
        primary_path, _ = sample_paths(case_dir_path, s)
        assert primary_path.is_file(), f"{case_id}/{s.sample_id}: file not found"

        try:
            session = api.start_session(case_dir_path, "calibration", data_dir)
            media = api.intake_attempt(session, primary_path, s.attempt_kind)
            result = api.submit_attempt(session, media, ctx)
            rj = result.to_json()
            passed = bool(rj.get("evaluation", {}).get("passed", False))

            if expected.get("refused"):
                assert not passed, (
                    f"{case_id}/{s.sample_id}: expected refused but passed={passed}"
                )
            else:
                exp_passed = expected.get("passed", None)
                if exp_passed is not None:
                    assert passed == exp_passed, (
                        f"{case_id}/{s.sample_id}: expected passed={exp_passed}, got {passed}"
                    )

        except AnveshanFailure:
            assert expected.get("refused") or not expected.get("passed", True), (
                f"{case_id}/{s.sample_id}: unexpected refusal; expected={expected}"
            )
        except Exception as exc:
            raise AssertionError(f"{case_id}/{s.sample_id}: error: {exc}") from exc


# ---------------------------------------------------------------------------
# §5.6 HTTP-level test for POST /api/compose/sample/{sample_id}
# ---------------------------------------------------------------------------

class TestAnalyzeSampleSource:
    """Covers the compose/sample route end-to-end with a fake composer stub."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        _install_fakes(monkeypatch)

        # Fake track_a.composer — minimal stub that returns a view with a draft_id.
        composer_mod = types.ModuleType("track_a.composer")

        @dataclasses.dataclass
        class _FakeDraft:
            draft_id: str = "draft-sample-test-001"

            def to_view(self) -> Dict[str, Any]:
                return {"draft_id": self.draft_id, "status": "ready"}

        def create_draft(
            data_dir: Path,
            file_path: Path,
            mime: str,
            ctx: Any,
            title_hint: str = "",
            rights_confirmed: bool = False,
        ) -> "_FakeDraft":
            return _FakeDraft()

        setattr(composer_mod, "create_draft", create_draft)
        monkeypatch.setitem(sys.modules, "track_a.composer", composer_mod)

        # Capture add_owner calls.
        self.owned: List[Path] = []
        monkeypatch.setattr(
            "anveshan_service.routes.samples.add_owner",
            lambda path: self.owned.append(path),
        )

        settings = _settings(tmp_path, tmp_path / "cases")
        app = create_app(settings)
        # samples router is now registered in create_app; no explicit include_router needed
        self.client = TestClient(app, raise_server_exceptions=False)

    def test_returns_200_and_add_owner_called(self):
        """POST /api/compose/sample/{sample_id} returns 200 and calls add_owner."""
        # Uses the first real committed source (kolam-photo) so no fixture file is needed.
        r = self.client.post("/api/compose/sample/kolam-photo")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "draft_id" in data
        assert len(self.owned) == 1

    def test_canonical_path_source_returns_200(self):
        """tabla-rhythm points at the committed tabla sample via canonical_path (no copy)."""
        r = self.client.post("/api/compose/sample/tabla-rhythm")
        assert r.status_code == 200, r.text

    def test_unknown_source_returns_404(self):
        r = self.client.post("/api/compose/sample/no-such-source")
        assert r.status_code == 404
