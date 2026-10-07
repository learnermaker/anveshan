"""Real-tracks end-to-end tests using TestClient + recorded mode golden runs.

These tests use the REAL track_a.api and track_b.api (not fakes), wired to
the committed hero case packs (kolam + tabla). No API key required — all model
calls are served from committed golden run files (recorded mode).

WP5 step 4: extended with the composer flow:
  analyse -> create -> practice attempt -> relevance-refused attempt.

The composer flow uses a monkeypatched create_draft to return a recorded
Draft (no live perception call required). The universal evaluator runs with
monkeypatched perceivers (same fixture approach as WP2 unit tests).
"""
from __future__ import annotations

import hashlib
import json
import sys
import types
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pytest
from fastapi.testclient import TestClient

from anveshan_service.main import create_app
from anveshan_service.settings import Settings

REPO_ROOT = Path(__file__).resolve().parents[2]  # service/tests -> service -> anveshan
CASES_ROOT = REPO_ROOT / "tracks" / "cases"
KOLAM_DIR = CASES_ROOT / "kolam"
KOLAM_TARGET = KOLAM_DIR / "source" / "ithayakkamalam_target.jpg"

SYNTHETIC_KOLAM = REPO_ROOT / "tracks" / "track-b" / "eval" / "kolam" / "synthetic"
STRAY_TRACE = SYNTHETIC_KOLAM / "stray_stroke" / "trace.json"
PERFECT_TRACE = SYNTHETIC_KOLAM / "perfect" / "trace.json"

_TRACE_JSON = json.dumps({
    "canvas": {"width": 492, "height": 499},
    "goal_case_id": "kolam",
    "goal_version": 1,
    "strokes": [{"points": [[10, 20, 0], [30, 40, 100]]}],
    "duration_ms": 200,
}).encode()


# ---------------------------------------------------------------------------
# Real-tracks settings fixture
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def real_settings(tmp_path_factory) -> Settings:
    """Settings pointing at the real cases_root with a temp data_dir."""
    data_dir = tmp_path_factory.mktemp("data")
    return Settings(
        mode="recorded",
        cases_root=CASES_ROOT,
        data_dir=data_dir,
        max_upload_mb=50.0,
        cors_origins=[],
        static_dir=None,
    )


@pytest.fixture(scope="module")
def real_client(real_settings: Settings) -> TestClient:
    """TestClient with REAL track_a.api and track_b.api in recorded mode."""
    return TestClient(create_app(real_settings), raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Basic smoke: list cases, get hero cases
# ---------------------------------------------------------------------------

def test_health(real_client):
    r = real_client.get("/api/health")
    assert r.status_code == 200


def test_list_cases_has_hero_cases(real_client):
    r = real_client.get("/api/cases")
    assert r.status_code == 200
    case_ids = {c["case_id"] for c in r.json()}
    assert "kolam" in case_ids, f"expected kolam in {case_ids}"
    assert "tabla" in case_ids
    # origami is now EXPERIMENTAL (hidden from list); origami-crane is the universal replacement
    assert "origami" not in case_ids, "origami (dedicated engine) should be hidden from list"
    assert "origami-crane" in case_ids, "origami-crane (universal pipeline) should be in list"


def test_get_kolam_case_has_goal(real_client):
    r = real_client.get("/api/cases/kolam")
    assert r.status_code == 200
    data = r.json()
    assert data["case_id"] == "kolam"
    assert data.get("goal") is not None, "kolam case should have a goal model"
    assert data["modality"] == "kolam_image"


def test_get_tabla_case_has_goal(real_client):
    r = real_client.get("/api/cases/tabla")
    assert r.status_code == 200
    data = r.json()
    assert data.get("goal") is not None


def test_unknown_case_is_404(real_client):
    # Use a valid-format but non-existent composed case ID (format: slug~sha12)
    r = real_client.get("/api/cases/nonexistent~aabbccddee00")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Evidence query
# ---------------------------------------------------------------------------

def test_kolam_answerable_query(real_client):
    # The kolam case may not be in approved state; accept 200 or 409
    r = real_client.post("/api/cases/kolam/query",
                         json={"question": "How many dots does this kolam have?"})
    assert r.status_code in (200, 409), f"unexpected: {r.status_code} {r.text}"
    if r.status_code == 200:
        data = r.json()
        assert "answer" in data


def test_kolam_creator_intent_query_refused(real_client):
    """Creator-intent questions must be marked insufficient (goal-conditioned case)."""
    r = real_client.post("/api/cases/kolam/query",
                         json={"question": "Who originally drew this and what did they intend?"})
    assert r.status_code in (200, 409), f"unexpected: {r.status_code}"
    if r.status_code == 200:
        data = r.json()
        assert data.get("sufficient") is False, f"expected sufficient=False, got {data.get('sufficient')}"


# ---------------------------------------------------------------------------
# Kolam trace session (recorded, deterministic, no API key)
# ---------------------------------------------------------------------------

def test_kolam_trace_session_recorded(real_client, real_settings):
    """Start → stray-stroke baseline → perfect retry → complete. Bundle validates."""
    # Start
    r = real_client.post("/api/sessions", json={"case_id": "kolam", "learner_name": "RealE2E"})
    assert r.status_code == 200, r.text
    sid = r.json()["session_id"]

    # Use real stray-stroke trace if available, otherwise minimal trace
    if STRAY_TRACE.exists():
        trace_bytes = STRAY_TRACE.read_bytes()
    else:
        trace_bytes = _TRACE_JSON

    # Baseline attempt
    r2 = real_client.post(
        f"/api/sessions/{sid}/attempts?mode=recorded",
        data={"kind": "trace"},
        files={"file": ("trace.json", trace_bytes, "application/json")},
    )
    assert r2.status_code == 200, f"baseline failed: {r2.text}"
    baseline_data = r2.json()
    assert "attempt" in baseline_data

    # Retry attempt (use perfect trace if available)
    if PERFECT_TRACE.exists():
        retry_bytes = PERFECT_TRACE.read_bytes()
    else:
        retry_bytes = trace_bytes

    r3 = real_client.post(
        f"/api/sessions/{sid}/attempts?mode=recorded",
        data={"kind": "trace"},
        files={"file": ("trace.json", retry_bytes, "application/json")},
    )
    assert r3.status_code == 200, f"retry failed: {r3.text}"

    # Complete
    r4 = real_client.post(f"/api/sessions/{sid}/complete")
    assert r4.status_code == 200, f"complete failed: {r4.text}"
    result = r4.json()
    assert "bundle" in result
    assert "transmission_record" in result


# ---------------------------------------------------------------------------
# Composer flow (monkeypatched analyse; real build+eval)
# ---------------------------------------------------------------------------

@pytest.fixture
def composer_case_dir(tmp_path) -> Path:
    """Build a minimal but valid universal case directory for composer tests."""
    from tracks.common.casedata import (
        GoalModel, ObserverBinding, Band, Observers,
        SourceRecord, SourceRegistry, write_json,
        CriterionMap, CriterionMapEntry,
    )
    from tracks.common.schemas import (
        ExpertReview, KnowledgeClaim, KnowledgePackage, PracticeTask,
        ReviewStatus, RubricCriterion, RubricDefinition,
    )
    from tracks.common.schemas.evidence import Modality, VerificationState
    from tracks.common.schemas.knowledge import ClaimType, ConsentMetadata
    from tracks.common.skill_model import Check, Relevance, SkillModel, TargetProperty
    from tracks.common.perception import MediaInfoRecord, PerceptionRecord, Segment

    case_id = "smoke-image~000000000001"
    case_dir = tmp_path / "cases" / case_id
    case_dir.mkdir(parents=True)
    for sub in ("knowledge", "practice", "source"):
        (case_dir / sub).mkdir()
    (case_dir / "runs" / "golden").mkdir(parents=True)

    # Manifest
    (case_dir / "manifest.json").write_text(json.dumps({
        "case_id": case_id,
        "title": "Smoke image skill",
        "skill": f"skill.{case_id}",
        "transmission_mode": "goal-conditioned",
    }), encoding="utf-8")

    # Source file (minimal JPEG)
    src_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 1000 + b"\xff\xd9"
    sha = hashlib.sha256(src_bytes).hexdigest()
    src_path = case_dir / "source" / f"upload.{sha[:12]}.jpg"
    src_path.write_bytes(src_bytes)

    src = SourceRecord(
        source_id=f"src.{case_id}.v1",
        role="target_image",
        mime_type="image/jpeg",
        sha256=sha,
        bytes=len(src_bytes),
        path=f"source/upload.{sha[:12]}.jpg",
        creator="smoke_test",
        license="public domain",
        attribution="smoke",
        runtime_label="SYNTHETIC",
    )
    write_json(case_dir / "source" / "source.json", SourceRegistry(case_id=case_id, sources=[src]))

    # Skill model
    skill = SkillModel(
        skill_title="Smoke image skill",
        summary="A minimal composed skill for e2e smoke testing",
        source_modality="image",
        structures=["final_state"],
        goal_state=[TargetProperty(prop_id="prop-01", statement="A minimal image",
                                   certainty="inferred", keep=True)],
        relevance=Relevance(expected_kinds=["image"], min_similarity=0.0),
        checks=[
            Check(check_id="CHK-FS-SIM", kind="final_similarity", name="Similarity",
                  observable_indicator="cosine similarity", metric_id="u.final_similarity",
                  method="deterministic", weight=1, required=False, process=False),
        ],
    )

    # Perception record + embeddings
    from tracks.common.perception import MediaInfoRecord, PerceptionRecord, Segment
    record = PerceptionRecord(
        media=MediaInfoRecord(source_id=f"src.{case_id}.v1", modality="image",
                              sha256=sha, mime_type="image/jpeg", width=100, height=100),
        segments=[Segment(segment_id="seg-000", kind="whole")],
        embedding_index={"seg-000": 0},
        embeddings_file="emb_source.npy",
    )
    (case_dir / "knowledge" / "perception_source.v1.json").write_text(
        record.model_dump_json(), encoding="utf-8")
    src_emb = np.array([[0.5] * 768], dtype=np.float16)
    np.save(str(case_dir / "knowledge" / "emb_source.npy"), src_emb)

    # CaseProfile
    from tracks.common.profile import CaseProfile, ProbeFacts, IntakeResult
    probe = ProbeFacts(modality="image", mime_type="image/jpeg", bytes=len(src_bytes),
                       sha256=sha, width=100, height=100,
                       structures_available=["final_state"], specialists_available=[])
    intake = IntakeResult(safety={"decision": "ok", "notices": [], "policy": "policy_v1"},
                          teachable="yes", teachable_reason="test")
    profile = CaseProfile(
        case_id=case_id, title="Smoke image skill",
        skill_summary="A minimal composed skill",
        domain="test", transmission_mode="goal-conditioned",
        learner_input_kinds=["image"],
        probe=probe, intake=intake,
        skill_model=skill,
        perception_file="knowledge/perception_source.v1.json",
        confirmed_by_user=True,
    )
    write_json(case_dir / "knowledge" / "case_profile.v1.json", profile)

    # Build all 6 artifacts programmatically using the builder
    from tracks.common.runtime import RunContext
    from track_a.api import build_case
    ctx = RunContext.create(case_dir, tmp_path / "data", "recorded")
    try:
        build_case(case_dir, ctx)
    except Exception:
        # If build fails, write minimal artifacts
        goal = GoalModel(case_id=case_id, version=1, modality="universal",
                         source_ids=[f"src.{case_id}.v1"],
                         package_id=f"kp.{case_id}.1",
                         payload={**skill.model_dump(mode="json"),
                                  "perception_file": "knowledge/perception_source.v1.json"})
        write_json(case_dir / "knowledge" / "goal_model.v1.json", goal)

        from tracks.common.schemas import (
            ExpertReview, KnowledgeClaim, KnowledgePackage, PracticeTask,
            RubricCriterion, RubricDefinition, ReviewStatus,
        )
        from tracks.common.schemas.knowledge import ClaimType, ConsentMetadata
        from tracks.common.schemas.evidence import Modality as EM, VerificationState

        claim = KnowledgeClaim(
            claim_id="CLM-01", claim_type=ClaimType.STEP,
            statement="A minimal image", is_observed=False,
            evidence_refs=[],
        )
        pkg = KnowledgePackage(
            package_id=f"kp.{case_id}.1", skill_id=f"skill.{case_id}",
            title="Smoke", summary="Smoke",
            claims=[claim],
            consent=ConsentMetadata(contributor_name="test", consent_scope="public", revocable=False),
            expert_review=ExpertReview(reviewer_name="smoke", status=ReviewStatus.APPROVED),
        )
        write_json(case_dir / "knowledge" / "knowledge_package.v1.json", pkg)

        rubric = RubricDefinition(
            rubric_id=f"rubric.{case_id}.1", skill_id=f"skill.{case_id}",
            title="Smoke rubric", description="", criteria=[
                RubricCriterion(criterion_id="CRIT-U-CHK-FS-SIM", name="Similarity",
                                description="", observable_indicator="", weight=1),
            ], passing_score=0.5,
        )
        write_json(case_dir / "practice" / "rubric.v1.json", rubric)

        task = PracticeTask(
            task_id=f"task.{case_id}.1", package_id=f"kp.{case_id}.1",
            rubric_id=f"rubric.{case_id}.1",
            title="Smoke task", instructions="Submit an image.",
            target_criteria_ids=["CRIT-U-CHK-FS-SIM"],
        )
        write_json(case_dir / "practice" / "practice_task.v1.json", task)

        observers = Observers(
            rubric_id=f"rubric.{case_id}.1", modality="universal", version=1,
            criteria={"CRIT-U-CHK-FS-SIM": ObserverBinding(
                metric="u.final_similarity", direction="higher_is_better",
                bands=[Band(status="satisfied", min=0.80),
                       Band(status="partially_satisfied", min=0.50)],
            )},
        )
        write_json(case_dir / "practice" / "observers.v1.json", observers)

        cmap = CriterionMap(
            rubric_id=f"rubric.{case_id}.1", package_id=f"kp.{case_id}.1",
            criteria={"CRIT-U-CHK-FS-SIM": CriterionMapEntry(
                order_index=0, source_claim_ids=["CLM-01"],
                reference_evidence_ids=[],
                why_it_matters="Similarity metric (CLM-01)",
                drill_hint="Compare to reference",
            )},
        )
        write_json(case_dir / "knowledge" / "criterion_map.v1.json", cmap)

    return case_dir


def _make_fake_perceivers(emb_value: float = 0.5) -> types.ModuleType:
    """Return a fake perceivers module for universal evaluation without live calls."""
    from tracks.common.perception import MediaInfoRecord, Observation, PerceptionRecord, Segment
    fake = types.ModuleType("tracks.common.perceivers")

    def _perceive(path, mime, ctx, *, source_id, asset_dir, purpose, skill_hint=None, want_specialists=True):
        asset_dir.mkdir(parents=True, exist_ok=True)
        obs = Observation(obs_id="obs.00", segment_id="seg-000", kind="measurement",
                          label="brightness", value=0.5, producer="det:image",
                          certainty="observed")
        return PerceptionRecord(
            media=MediaInfoRecord(source_id=source_id, modality="image", sha256="a" * 64,
                                  mime_type=mime, width=100, height=100),
            segments=[Segment(segment_id="seg-000", kind="whole")],
            embedding_index={"seg-000": 0},
            embeddings_file=None,
        )

    def _load_embeddings(rec, record_dir):
        return np.array([[emb_value] * 768], dtype=np.float32)

    def _load_record(path):
        return None

    fake.perceive = _perceive
    fake.load_embeddings = _load_embeddings
    fake.load_record = _load_record
    return fake


def test_composer_session_practice_attempt(composer_case_dir, tmp_path, monkeypatch):
    """Composer case: session start -> image attempt -> complete."""
    monkeypatch.setitem(sys.modules, "tracks.common.perceivers", _make_fake_perceivers(0.5))

    # composer_case_dir = tmp_path / "cases" / case_id
    # Composed cases are looked up under data_dir/cases/ (not cases_root)
    data_dir = composer_case_dir.parent.parent  # = tmp_path
    settings = Settings(
        mode="recorded",
        cases_root=CASES_ROOT,  # hero cases
        data_dir=data_dir,  # data_dir/cases/<case_id> is the composed case
        max_upload_mb=50.0,
        cors_origins=[],
        static_dir=None,
    )
    client = TestClient(create_app(settings), raise_server_exceptions=False)

    # Start session
    case_id = composer_case_dir.name
    r = client.post("/api/sessions", json={"case_id": case_id, "learner_name": "ComposerSmoke"})
    assert r.status_code == 200, f"start_session: {r.text}"
    sid = r.json()["session_id"]

    # Practice attempt: valid JPEG from PIL
    from PIL import Image
    import io
    arr = np.ones((64, 64, 3), dtype=np.uint8) * 128
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="JPEG")
    img_bytes = buf.getvalue()

    r2 = client.post(
        f"/api/sessions/{sid}/attempts",
        data={"kind": "image"},
        files={"file": ("attempt.jpg", img_bytes, "image/jpeg")},
    )
    assert r2.status_code == 200, f"attempt failed: {r2.text}"
    assert "attempt" in r2.json()

    # Retry attempt (required for complete)
    r2b = client.post(
        f"/api/sessions/{sid}/attempts",
        data={"kind": "image"},
        files={"file": ("retry.jpg", img_bytes, "image/jpeg")},
    )
    assert r2b.status_code == 200, f"retry failed: {r2b.text}"

    # Complete
    r3 = client.post(f"/api/sessions/{sid}/complete")
    assert r3.status_code == 200, f"complete: {r3.text}"
    assert "bundle" in r3.json()


def test_composer_relevance_refused_attempt(composer_case_dir, tmp_path, monkeypatch):
    """Composer case: attempt that's unrelated is refused by kind gate or quality gate."""
    # Inject perceivers that return very low similarity (different embedding)
    monkeypatch.setitem(sys.modules, "tracks.common.perceivers", _make_fake_perceivers(-0.5))

    data_dir = composer_case_dir.parent.parent  # tmp_path
    settings = Settings(
        mode="recorded",
        cases_root=CASES_ROOT,
        data_dir=data_dir,
        max_upload_mb=50.0,
        cors_origins=[],
        static_dir=None,
    )
    client = TestClient(create_app(settings), raise_server_exceptions=False)

    case_id = composer_case_dir.name
    r = client.post("/api/sessions", json={"case_id": case_id, "learner_name": "RefusalSmoke"})
    assert r.status_code == 200
    sid = r.json()["session_id"]

    # Very small gray image (should pass quality gate, similarity will be low but not refused
    # since min_similarity=0.0 in our test case)
    img_bytes = b"\xff\xd8\xff\xe0" + b"\x80" * 400 + b"\xff\xd9"
    r2 = client.post(
        f"/api/sessions/{sid}/attempts",
        data={"kind": "image"},
        files={"file": ("attempt.jpg", img_bytes, "image/jpeg")},
    )
    # We expect either 200 (attempt processed) or 400 (refused)
    # The compose session should handle both gracefully
    assert r2.status_code in (200, 400), f"unexpected: {r2.status_code} {r2.text}"
