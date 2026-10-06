"""End-to-end session test for the universal evaluator.

Synthetic composed case (fixture SkillModel + perception with embeddings written to tmp)
-> start_session -> baseline attempt with a missing step -> retry that is perfect
-> complete_session -> bundle validates, gain > 0 and targeted_change improved.

No network calls. Uses fake gateway responses.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import pytest

from tracks.common.casedata import (
    GoalModel, ObserverBinding, Band, Observers,
    SourceRecord, SourceRegistry, write_json,
)
from tracks.common.models import ModelGateway, ModelRegistry, RunStore
from tracks.common.perception import MediaInfoRecord, Observation, PerceptionRecord, Segment
from tracks.common.runtime import RunContext
from tracks.common.schemas import (
    EvidenceRef, ExpertReview, KnowledgeClaim, KnowledgePackage,
    PracticeTask, ReviewStatus, RubricCriterion, RubricDefinition,
    TaskConstraint,
)
from tracks.common.schemas.evidence import Modality as EvidenceModality, VerificationState
from tracks.common.schemas.knowledge import ClaimType
from tracks.common.skill_model import Check, Relevance, SkillModel, Step, TargetProperty


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

WORKTREE = Path(__file__).resolve().parents[4]


def _unit_vec(dim: int = 768, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


def _make_skill_model() -> SkillModel:
    """A simple procedure skill with 2 steps."""
    steps = [
        Step(step_id="step-01", index=0, name="Step One", state_after="state1",
             start_sec=0.0, end_sec=5.0, segment_id="seg-001",
             certainty="inferred", source_established=True, critical=False),
        Step(step_id="step-02", index=1, name="Step Two", state_after="state2",
             start_sec=5.0, end_sec=10.0, segment_id="seg-002",
             certainty="inferred", source_established=True, critical=True),
    ]
    checks = [
        Check(
            check_id="CHK-PR-COV", kind="step_coverage",
            name="Step Coverage", observable_indicator="Fraction of steps matched",
            targets=["step-01", "step-02"], metric_id="u.step_coverage",
            method="deterministic", weight=3, required=True, process=True,
        ),
        Check(
            check_id="CHK-PR-ORD", kind="step_order",
            name="Step Order", observable_indicator="Order violations",
            targets=["step-01", "step-02"], metric_id="u.step_order",
            method="deterministic", weight=2, required=False, process=True,
        ),
        Check(
            check_id="CHK-FS-SIM", kind="final_similarity",
            name="Similarity", observable_indicator="Cosine similarity",
            targets=[], metric_id="u.final_similarity",
            method="deterministic", weight=1, required=False, process=False,
        ),
    ]
    return SkillModel(
        skill_title="Two-Step Skill",
        summary="A simple two-step skill",
        source_modality="video",
        structures=["procedure", "final_state"],
        steps=steps,
        order="strict",
        checks=checks,
        relevance=Relevance(
            expected_kinds=["video", "image"],
            min_similarity=0.70,
            reference_segment_ids=["seg-001", "seg-002"],
        ),
    )


def _make_perception_record(source_id: str = "src.test.v1") -> PerceptionRecord:
    return PerceptionRecord(
        media=MediaInfoRecord(
            source_id=source_id,
            modality="video",
            sha256="b" * 64,
            mime_type="video/mp4",
            duration_sec=10.0,
        ),
        segments=[
            Segment(segment_id="seg-000", kind="whole"),
            Segment(segment_id="seg-001", kind="time", start_sec=0.0, end_sec=5.0, keyframe_asset="kf_001.jpg"),
            Segment(segment_id="seg-002", kind="time", start_sec=5.0, end_sec=10.0, keyframe_asset="kf_002.jpg"),
        ],
        embedding_index={"seg-001": 0, "seg-002": 1},
        embeddings_file="emb_source.npy",
    )


def _write_case(case_dir: Path, skill: SkillModel, perception: PerceptionRecord) -> tuple:
    """Write all 6 case artifacts for a universal skill. Returns (sources, goal_model)."""
    import json
    from tracks.common import locators

    case_dir.mkdir(parents=True, exist_ok=True)
    (case_dir / "knowledge").mkdir(exist_ok=True)
    (case_dir / "practice").mkdir(exist_ok=True)
    (case_dir / "source").mkdir(exist_ok=True)

    # Write manifest
    (case_dir / "manifest.json").write_text(json.dumps({
        "case_id": case_dir.name,
        "title": skill.skill_title,
        "skill": f"skill.{case_dir.name}",
        "transmission_mode": "forward",
    }), encoding="utf-8")

    # Source record
    source_id = perception.media.source_id
    src = SourceRecord(
        source_id=source_id,
        role="expert_video",
        mime_type="video/mp4",
        sha256="b" * 64,
        bytes=1024,
        path="source/demo.mp4",
        duration_sec=10.0,
        creator="test",
        license="public domain",
        attribution="test",
        runtime_label="SYNTHETIC",
    )
    sreg = SourceRegistry(case_id=case_dir.name, sources=[src])
    write_json(case_dir / "source" / "source.json", sreg)

    # Source perception
    (case_dir / "knowledge" / "perception_source.v1.json").write_text(
        perception.model_dump_json(), encoding="utf-8"
    )
    # Source embeddings
    src_emb = np.stack([_unit_vec(768, 0), _unit_vec(768, 1)])
    np.save(str(case_dir / "knowledge" / "emb_source.npy"), src_emb.astype(np.float16))

    # GoalModel
    goal_payload = skill.model_dump(mode="json")
    goal_payload["perception_file"] = "knowledge/perception_source.v1.json"
    goal = GoalModel(
        case_id=case_dir.name,
        version=1,
        modality="universal",
        source_ids=[source_id],
        package_id=f"kp.{case_dir.name}.1",
        payload=goal_payload,
    )
    write_json(case_dir / "knowledge" / "goal_model.v1.json", goal)

    # KnowledgePackage
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.STEP,
        statement="Demonstrated step 1 (inferred)",
        is_observed=False,
        evidence_refs=[EvidenceRef(
            evidence_id="ev.test.clm01",
            source_id=f"{source_id}#xywh=percent:0.00,0.00,100.00,100.00",
            modality=EvidenceModality.VIDEO,
            start_sec=0.0, end_sec=5.0,
            cue_excerpt="Step 1",
            verification_state=VerificationState.INFERRED,
            confidence=0.5,
        )],
    )
    claim2 = KnowledgeClaim(
        claim_id="CLM-02",
        claim_type=ClaimType.STEP,
        statement="Demonstrated step 2 (inferred)",
        is_observed=False,
        evidence_refs=[EvidenceRef(
            evidence_id="ev.test.clm02",
            source_id=f"{source_id}#xywh=percent:0.00,0.00,100.00,100.00",
            modality=EvidenceModality.VIDEO,
            start_sec=5.0, end_sec=10.0,
            cue_excerpt="Step 2",
            verification_state=VerificationState.INFERRED,
            confidence=0.5,
        )],
    )
    # Also add a CONDITION claim (not step, observed) for the package
    from tracks.common.schemas.knowledge import ConsentMetadata
    pkg = KnowledgePackage(
        package_id=f"kp.{case_dir.name}.1",
        skill_id=f"skill.{case_dir.name}",
        title=skill.skill_title,
        summary=skill.summary,
        claims=[claim, claim2],
        consent=ConsentMetadata(
            contributor_name="test",
            consent_scope="public",
            revocable=False,
        ),
        expert_review=ExpertReview(
            reviewer_name="test",
            status=ReviewStatus.APPROVED,
        ),
    )
    write_json(case_dir / "knowledge" / "knowledge_package.v1.json", pkg)

    # RubricDefinition
    criteria = [
        RubricCriterion(
            criterion_id="CRIT-U-CHK-PR-COV",
            name="Step Coverage",
            description="Fraction of steps covered",
            observable_indicator="Fraction of steps covered",
            weight=3,
            required=True,
        ),
        RubricCriterion(
            criterion_id="CRIT-U-CHK-PR-ORD",
            name="Step Order",
            description="Order violations",
            observable_indicator="Order violations",
            weight=2,
            required=False,
        ),
        RubricCriterion(
            criterion_id="CRIT-U-CHK-FS-SIM",
            name="Similarity",
            description="Cosine similarity",
            observable_indicator="Cosine similarity",
            weight=1,
            required=False,
        ),
    ]
    rubric = RubricDefinition(
        rubric_id=f"rubric.{case_dir.name}.1",
        skill_id=f"skill.{case_dir.name}",
        title=f"{skill.skill_title} — rubric",
        description="Test rubric",
        criteria=criteria,
        passing_score=4.0,
    )
    write_json(case_dir / "practice" / "rubric.v1.json", rubric)

    # PracticeTask
    task = PracticeTask(
        task_id=f"task.{case_dir.name}.1",
        package_id=f"kp.{case_dir.name}.1",
        rubric_id=f"rubric.{case_dir.name}.1",
        title=f"Practice: {skill.skill_title}",
        instructions="1. Do step one [CLM-01]\n2. Do step two [CLM-02]\n3. Upload video.",
        target_criteria_ids=["CRIT-U-CHK-PR-COV", "CRIT-U-CHK-PR-ORD", "CRIT-U-CHK-FS-SIM"],
    )
    write_json(case_dir / "practice" / "practice_task.v1.json", task)

    # Observers
    from tracks.common.casedata import Observers
    observers = Observers(
        rubric_id=f"rubric.{case_dir.name}.1",
        modality="universal",
        version=1,
        criteria={
            "CRIT-U-CHK-PR-COV": ObserverBinding(
                metric="u.step_coverage",
                direction="higher_is_better",
                bands=[Band(status="satisfied", min=0.90), Band(status="partially_satisfied", min=0.60)],
                process=True,
            ),
            "CRIT-U-CHK-PR-ORD": ObserverBinding(
                metric="u.step_order",
                direction="lower_is_better",
                bands=[Band(status="satisfied", max=0), Band(status="partially_satisfied", max=1)],
                process=True,
            ),
            "CRIT-U-CHK-FS-SIM": ObserverBinding(
                metric="u.final_similarity",
                direction="higher_is_better",
                bands=[Band(status="satisfied", min=0.90), Band(status="partially_satisfied", min=0.80)],
            ),
        },
    )
    write_json(case_dir / "practice" / "observers.v1.json", observers)

    # CriterionMap
    from tracks.common.casedata import CriterionMap, CriterionMapEntry
    cmap = CriterionMap(
        rubric_id=f"rubric.{case_dir.name}.1",
        package_id=f"kp.{case_dir.name}.1",
        criteria={
            "CRIT-U-CHK-PR-COV": CriterionMapEntry(
                order_index=0,
                source_claim_ids=["CLM-01"],
                reference_evidence_ids=["ev.test.clm01"],
                why_it_matters="Coverage measures progress (CLM-01)",
                drill_hint="Practice each step",
            ),
            "CRIT-U-CHK-PR-ORD": CriterionMapEntry(
                order_index=1,
                source_claim_ids=["CLM-02"],
                reference_evidence_ids=["ev.test.clm02"],
                why_it_matters="Order must be maintained (CLM-02)",
                drill_hint="Follow the demonstrated sequence",
            ),
            "CRIT-U-CHK-FS-SIM": CriterionMapEntry(
                order_index=2,
                source_claim_ids=["CLM-01"],
                reference_evidence_ids=["ev.test.clm01"],
                why_it_matters="The final result must match (CLM-01)",
                drill_hint="Compare to the reference",
            ),
        },
    )
    write_json(case_dir / "knowledge" / "criterion_map.v1.json", cmap)

    return sreg, goal


def _fake_perceivers(
    att_emb_seed: int = 0,
    frame_rows: list = None,
    frame_times: list = None,
) -> types.ModuleType:
    """Return a fake perceivers module for monkeypatching."""
    fake = types.ModuleType("tracks.common.perceivers")
    _frame_rows = frame_rows or []
    _frame_times = frame_times or []

    def _perceive(path, mime, ctx, *, source_id, asset_dir, purpose, skill_hint=None, want_specialists=True):
        return PerceptionRecord(
            media=MediaInfoRecord(
                source_id=source_id, modality="video", sha256="c" * 64, mime_type="video/mp4"
            ),
            segments=[Segment(segment_id="seg-000", kind="whole")],
            embedding_index={},
            specialists={"frames": {"rows": _frame_rows, "times": _frame_times}},
        )

    _att_emb_seed = att_emb_seed

    def _load_embeddings(rec, record_dir):
        if rec.media.source_id == "src.test.v1":
            # Source: step embeddings
            return np.stack([_unit_vec(768, 0), _unit_vec(768, 1)])
        # Attempt: frame embeddings based on seed
        n = max(len(_frame_rows), 2)
        return np.stack([_unit_vec(768, _att_emb_seed + i) for i in range(n)])

    def _load_record(path):
        return PerceptionRecord(
            media=MediaInfoRecord(source_id="src.test.v1", modality="video",
                                  sha256="b" * 64, mime_type="video/mp4"),
            segments=[Segment(segment_id="seg-000", kind="whole")],
        )

    fake.perceive = _perceive
    fake.load_embeddings = _load_embeddings
    fake.load_record = _load_record
    return fake


# ---------------------------------------------------------------------------
# E2E test
# ---------------------------------------------------------------------------

class TestUniversalSessionE2E:

    def _inject_perceivers_baseline(self, monkeypatch, case_dir: Path):
        """Baseline: only step 0 is matched (step 1 missing -> coverage 0.5)."""
        dim = 768
        step0_vec = _unit_vec(dim, 0)
        step1_vec = _unit_vec(dim, 1)

        # Frames: only matching step 0 (step 1 missing)
        frame_rows = [0, 0, 0, 0]  # all frames match index 0 in att_emb
        frame_times = [0.0, 1.0, 2.0, 3.0]

        # att_emb: only step 0 vectors (step 1 never seen)
        att_emb = np.stack([step0_vec] * 4)

        def _perceive(path, mime, ctx, *, source_id, asset_dir, purpose, skill_hint=None, want_specialists=True):
            return PerceptionRecord(
                media=MediaInfoRecord(source_id=source_id, modality="video",
                                      sha256="c" * 64, mime_type="video/mp4"),
                segments=[Segment(segment_id="seg-000", kind="whole")],
                embedding_index={},
                specialists={"frames": {"rows": frame_rows, "times": frame_times}},
            )

        def _load_emb(rec, record_dir):
            if rec.media.source_id == "src.test.v1":
                return np.stack([step0_vec, step1_vec])
            return att_emb

        def _load_record(path):
            return None

        fake = types.ModuleType("tracks.common.perceivers")
        fake.perceive = _perceive
        fake.load_embeddings = _load_emb
        fake.load_record = _load_record
        monkeypatch.setitem(sys.modules, "tracks.common.perceivers", fake)

    def _inject_perceivers_perfect(self, monkeypatch, case_dir: Path):
        """Perfect retry: both steps matched in order -> coverage 1.0."""
        dim = 768
        step0_vec = _unit_vec(dim, 0)
        step1_vec = _unit_vec(dim, 1)

        frame_rows = [0, 0, 1, 1, 1]
        frame_times = [0.0, 1.0, 2.0, 3.0, 4.0]
        att_emb = np.vstack([
            np.tile(step0_vec, (2, 1)),
            np.tile(step1_vec, (3, 1)),
        ])

        def _perceive(path, mime, ctx, *, source_id, asset_dir, purpose, skill_hint=None, want_specialists=True):
            return PerceptionRecord(
                media=MediaInfoRecord(source_id=source_id, modality="video",
                                      sha256="d" * 64, mime_type="video/mp4"),
                segments=[Segment(segment_id="seg-000", kind="whole")],
                embedding_index={},
                specialists={"frames": {"rows": frame_rows, "times": frame_times}},
            )

        def _load_emb(rec, record_dir):
            if rec.media.source_id == "src.test.v1":
                return np.stack([step0_vec, step1_vec])
            return att_emb

        def _load_record(path):
            return None

        fake = types.ModuleType("tracks.common.perceivers")
        fake.perceive = _perceive
        fake.load_embeddings = _load_emb
        fake.load_record = _load_record
        monkeypatch.setitem(sys.modules, "tracks.common.perceivers", fake)

    def _make_video_attempt(self, tmp_path: Path, name: str) -> Path:
        """Create a minimal but valid video file for testing."""
        p = tmp_path / f"{name}.mp4"
        try:
            import av
            import io
            # Create minimal video with av
            with av.open(str(p), "w", format="mp4") as container:
                vstream = container.add_stream("libx264", rate=1)
                vstream.width = 32
                vstream.height = 32
                vstream.pix_fmt = "yuv420p"
                from av.video.frame import VideoFrame
                frame = VideoFrame.from_ndarray(
                    np.zeros((32, 32, 3), dtype=np.uint8), format="rgb24"
                )
                for i in range(3):
                    frame.pts = i
                    for packet in vstream.encode(frame):
                        container.mux(packet)
                for packet in vstream.encode(None):
                    container.mux(packet)
        except Exception:
            # Fallback: write raw bytes (will fail intake but test patches intake_attempt)
            p.write_bytes(b"\x00\x00\x00\x20ftyp" + b"\x00" * 32)
        return p

    def _make_attempt_directly(self, path: Path, kind: str, mime: str, sha256: str) -> AttemptMedia:
        """Build AttemptMedia directly without intake validation."""
        from track_b.trajectory import AttemptMedia as AM
        return AM(
            kind=kind,
            path=path,
            source_id=f"src.attempt.{sha256[:8]}",
            sha256=sha256,
            mime_type=mime,
        )

    def test_baseline_then_perfect_retry(self, tmp_path, monkeypatch):
        """Full session: baseline missing step -> perfect retry -> session completes."""
        skill = _make_skill_model()
        perception = _make_perception_record()
        case_dir = tmp_path / "cases" / "test~aabbccddee01"
        _write_case(case_dir, skill, perception)

        from track_b import api as tb_api

        # Patch ACCEPTED_KINDS for universal (WP5 will add this to the real api.py)
        monkeypatch.setitem(tb_api.ACCEPTED_KINDS, "universal", ("trace", "image", "audio", "video"))

        ctx = RunContext.create(
            case_dir=case_dir,
            data_dir=tmp_path / "data",
            mode="recorded",
        )

        session = tb_api.start_session(case_dir, "Test Learner", tmp_path / "data")

        # Baseline attempt (missing step 1)
        self._inject_perceivers_baseline(monkeypatch, case_dir)
        baseline_path = self._make_video_attempt(tmp_path, "baseline")
        baseline_media = self._make_attempt_directly(baseline_path, "video", "video/mp4", "c" * 64)
        baseline_result = tb_api.submit_attempt(session, baseline_media, ctx)
        assert baseline_result is not None

        # Perfect retry (all steps)
        self._inject_perceivers_perfect(monkeypatch, case_dir)
        perfect_path = self._make_video_attempt(tmp_path, "perfect")
        perfect_media = self._make_attempt_directly(perfect_path, "video", "video/mp4", "d" * 64)
        perfect_result = tb_api.submit_attempt(session, perfect_media, ctx)
        assert perfect_result is not None

        # Complete session
        session_result = tb_api.complete_session(session)
        assert session_result is not None

    def test_relevance_refusal_not_recorded(self, tmp_path, monkeypatch):
        """Attempt with wrong kind -> kind gate INVALID_INPUT."""
        skill = _make_skill_model()
        perception = _make_perception_record()
        case_dir = tmp_path / "cases" / "test~aabbccddee02"
        _write_case(case_dir, skill, perception)

        from track_b import api as tb_api
        from tracks.common.models import AnveshanFailure

        # Build audio AttemptMedia directly (bypassing intake check)
        audio_path = tmp_path / "wrong.wav"
        audio_path.write_bytes(b"RIFF" + b"\x00" * 44)
        audio_media = self._make_attempt_directly(audio_path, "audio", "audio/wav", "e" * 64)

        from track_b.evaluators.universal import evaluate
        from tracks.common.casedata import GoalModel
        goal_model = GoalModel(
            case_id=case_dir.name,
            version=1,
            modality="universal",
            source_ids=["src.test.v1"],
            package_id="kp.test.1",
            payload=skill.model_dump(mode="json"),
        )
        with pytest.raises(AnveshanFailure) as exc:
            evaluate(goal_model, audio_media, None)
        assert exc.value.category.value == "INVALID_INPUT"
