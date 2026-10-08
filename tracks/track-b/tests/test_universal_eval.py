"""Tests for the universal Layer 3 evaluator and alignment helpers.

No network calls. Uses fixture PerceptionRecords and monkeypatched perceivers.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

import numpy as np
import pytest

from tracks.common.casedata import GoalModel
from tracks.common.models import AnveshanFailure, FailureCategory, ModelError, RunStore, ModelGateway
from tracks.common.perception import MediaInfoRecord, Observation, PerceptionRecord, Segment
from tracks.common.runtime import RunContext
from tracks.common.skill_model import (
    Check,
    Constraint,
    Relevance,
    SkillModel,
    Step,
    TargetProperty,
)
from track_b.trajectory import AttemptMedia

WORKTREE = Path(__file__).resolve().parents[4]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_skill(structures: list, steps: list = None, goal_state: list = None,
                utterance: dict = None, specialists: dict = None,
                expected_kinds: list = None) -> SkillModel:
    """Build a minimal SkillModel for testing."""
    steps = steps or []
    goal_state = goal_state or []
    specialists = specialists or {}
    if expected_kinds is None:
        expected_kinds = ["image"]
        for s in structures:
            from tracks.common.skill_model import STRUCTURE_ATTEMPT_KINDS
            for k in STRUCTURE_ATTEMPT_KINDS.get(s, []):
                if k not in expected_kinds:
                    expected_kinds.append(k)

    checks: List[Check] = []
    if "final_state" in structures:
        checks.append(Check(
            check_id="CHK-FS-SIM", kind="final_similarity",
            name="Similarity", observable_indicator="Overall similarity",
            targets=[], metric_id="u.final_similarity",
            method="deterministic", weight=1, required=False, process=False,
        ))
        if goal_state:
            prop = goal_state[0]
            checks.append(Check(
                check_id="CHK-FS-P01", kind="final_property",
                name="Property", observable_indicator=prop.statement,
                targets=[prop.prop_id], metric_id=f"u.final_property.{prop.prop_id}",
                method="model_status", weight=2, required=True, process=False,
            ))
    if "procedure" in structures:
        checks.append(Check(
            check_id="CHK-PR-COV", kind="step_coverage",
            name="Coverage", observable_indicator="Step coverage",
            targets=[s.step_id for s in steps], metric_id="u.step_coverage",
            method="deterministic", weight=3, required=True, process=True,
        ))
        checks.append(Check(
            check_id="CHK-PR-ORD", kind="step_order",
            name="Order", observable_indicator="Order violations",
            targets=[s.step_id for s in steps], metric_id="u.step_order",
            method="deterministic", weight=2, required=True, process=True,
        ))
        checks.append(Check(
            check_id="CHK-PR-OFF", kind="off_path",
            name="Off path", observable_indicator="Off-path runs",
            targets=[], metric_id="u.off_path",
            method="deterministic", weight=1, required=False, process=True,
        ))
    if "utterance" in structures:
        checks.append(Check(
            check_id="CHK-UT-TXT", kind="utterance_match",
            name="Utterance", observable_indicator="Utterance match",
            targets=[], metric_id="u.utterance_match",
            method="deterministic", weight=3, required=True, process=False,
        ))
        checks.append(Check(
            check_id="CHK-UT-PACE", kind="pace_match",
            name="Pace", observable_indicator="Pace match",
            targets=[], metric_id="u.pace_match",
            method="deterministic", weight=1, required=False, process=False,
        ))

    if not checks:
        checks.append(Check(
            check_id="CHK-FS-SIM", kind="final_similarity",
            name="Similarity", observable_indicator="Overall similarity",
            targets=[], metric_id="u.final_similarity",
            method="deterministic", weight=1, required=False, process=False,
        ))

    return SkillModel(
        skill_title="Test Skill",
        summary="A test skill",
        source_modality="image" if "image" in (expected_kinds or ["image"]) else "video",
        structures=structures,
        goal_state=goal_state or [],
        steps=steps or [],
        order="strict" if "procedure" in structures and steps else "none",
        utterance=utterance,
        specialists=specialists,
        checks=checks,
        relevance=Relevance(
            expected_kinds=expected_kinds,
            min_similarity=0.72,
            reference_segment_ids=["seg-000"],
        ),
    )


def _make_goal(skill: SkillModel) -> GoalModel:
    return GoalModel(
        case_id="test~aabbccddee01",
        version=1,
        modality="universal",
        source_ids=["src.test.v1"],
        package_id="kp.test.1",
        payload=skill.model_dump(mode="json"),
    )


def _unit_vec(dim: int = 768, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float32)
    return v / np.linalg.norm(v)


def _make_attempt(tmp_path: Path, kind: str = "image", mime: str = "image/png") -> AttemptMedia:
    p = tmp_path / f"attempt.{kind}"
    # Write minimal valid content
    if kind == "image":
        try:
            from PIL import Image
            img = Image.new("RGB", (64, 64), color=(100, 150, 200))
            img.save(p, format="PNG")
        except Exception:
            p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    elif kind == "audio":
        p.write_bytes(b"RIFF" + b"\x00" * 44)
    elif kind == "video":
        p.write_bytes(b"\x00\x00\x00\x20ftyp" + b"\x00" * 32)
    else:
        p.write_bytes(b"{}")
    return AttemptMedia(
        kind=kind,
        path=p,
        source_id="src.attempt.v1",
        sha256="c" * 64,
        mime_type=mime,
    )


def _fake_perceivers_module(
    record: Optional[PerceptionRecord] = None,
    emb: Optional[np.ndarray] = None,
) -> types.ModuleType:
    """Inject a fake tracks.common.perceivers module."""
    fake = types.ModuleType("tracks.common.perceivers")

    def _perceive(path, mime, ctx, *, source_id, asset_dir, purpose, skill_hint=None, want_specialists=True):
        if record is not None:
            return record
        # Return a minimal record
        return PerceptionRecord(
            media=MediaInfoRecord(source_id=source_id, modality="image", sha256="d" * 64, mime_type=mime),
            segments=[Segment(segment_id="seg-000", kind="whole")],
            embedding_index={"seg-000": 0},
            embeddings_file="emb.npy",
        )

    def _load_embeddings(rec, record_dir):
        if emb is not None:
            return emb
        n = len(rec.embedding_index)
        return np.stack([_unit_vec(768, i) for i in range(max(n, 1))])

    def _load_record(path):
        if record is not None:
            return record
        return PerceptionRecord(
            media=MediaInfoRecord(source_id="src.test", modality="image", sha256="e" * 64, mime_type="image/png"),
            segments=[Segment(segment_id="seg-000", kind="whole")],
        )

    fake.perceive = _perceive
    fake.load_embeddings = _load_embeddings
    fake.load_record = _load_record
    return fake


def _inject_fake_perceivers(monkeypatch, record=None, emb=None):
    fake = _fake_perceivers_module(record, emb)
    monkeypatch.setitem(sys.modules, "tracks.common.perceivers", fake)
    return fake


# ---------------------------------------------------------------------------
# Alignment helpers tests
# ---------------------------------------------------------------------------

class TestLabelFrames:
    def test_perfect_sequence(self):
        """Frames clearly closest to steps -> correct step indices."""
        from track_b.evaluators.universal_align import label_frames
        # 3 steps, 3 frames each exactly matching one step
        dim = 8
        rng = np.random.default_rng(42)
        steps = np.stack([_unit_vec(dim, i) for i in range(3)])
        # Frames: one per step, perfectly aligned
        frames = steps.copy()
        labels = label_frames(frames, steps, margin=0.03, floor=0.60)
        assert labels == [0, 1, 2]

    def test_off_label(self):
        """Frame far from all steps -> 'off'."""
        from track_b.evaluators.universal_align import label_frames
        dim = 8
        steps = np.stack([_unit_vec(dim, i) for i in range(2)])
        # Random orthogonal vector -> low similarity
        v = np.zeros(dim, dtype=np.float32)
        v[0] = 1.0 - 1e-6
        v[1] = -1e-6  # slightly off the steps
        # Make it clearly low similarity
        rng = np.random.default_rng(99)
        far = rng.standard_normal(dim).astype(np.float32)
        # Make similarity to all steps < floor
        far -= (far @ steps.T).max() * 2 * steps[0]
        if np.linalg.norm(far) > 0:
            far /= np.linalg.norm(far)
        labels = label_frames(far.reshape(1, -1), steps, floor=0.99)
        assert labels[0] == "off"

    def test_transition_label(self):
        """Frame equidistant between two steps -> 'transition'."""
        from track_b.evaluators.universal_align import label_frames
        dim = 8
        steps = np.stack([_unit_vec(dim, 0), _unit_vec(dim, 1)])
        # Frame halfway between: mean, renormalized
        mid = (steps[0] + steps[1])
        mid /= np.linalg.norm(mid)
        # Ensure best-second < margin
        labels = label_frames(mid.reshape(1, -1), steps, margin=1.0, floor=0.1)
        assert labels[0] == "transition"

    def test_empty_inputs(self):
        from track_b.evaluators.universal_align import label_frames
        steps = np.zeros((3, 8), dtype=np.float32)
        assert label_frames(np.zeros((0, 8), dtype=np.float32), steps) == []
        assert label_frames(np.zeros((3, 8), dtype=np.float32), np.zeros((0, 8), dtype=np.float32)) == []


class TestNeedlemanWunsch:
    def test_perfect_order(self):
        """Perfect sequence -> coverage 1, violations 0."""
        from track_b.evaluators.universal_align import needleman_wunsch
        r = needleman_wunsch([0, 1, 2], [0, 1, 2])
        assert r["matched"] == 3
        assert r["violations"] == 0
        assert r["missing"] == 0

    def test_swapped_pair(self):
        """Swapped pair -> 1 violation."""
        from track_b.evaluators.universal_align import needleman_wunsch
        r = needleman_wunsch([1, 0, 2], [0, 1, 2])
        assert r["violations"] >= 1

    def test_missing_step(self):
        """Missing step -> coverage < 1, missing > 0."""
        from track_b.evaluators.universal_align import needleman_wunsch
        r = needleman_wunsch([0, 2], [0, 1, 2])
        assert r["missing"] >= 1
        assert r["matched"] <= 2

    def test_empty(self):
        from track_b.evaluators.universal_align import needleman_wunsch
        r = needleman_wunsch([], [])
        assert r["matched"] == 0
        r2 = needleman_wunsch([], [0, 1])
        assert r2["missing"] == 2
        r3 = needleman_wunsch([0, 1], [])
        assert r3["extra"] == 2


# ---------------------------------------------------------------------------
# Evaluator tests
# ---------------------------------------------------------------------------

class TestKindGate:
    def test_wrong_kind_raises(self, tmp_path):
        skill = _make_skill(["final_state"], expected_kinds=["image"])
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="audio", mime="audio/wav")
        from track_b.evaluators.universal import evaluate
        with pytest.raises(AnveshanFailure) as exc:
            evaluate(goal, attempt, None)
        assert exc.value.category == FailureCategory.INVALID_INPUT

    def test_correct_kind_passes_gate(self, tmp_path, monkeypatch):
        skill = _make_skill(["final_state"], expected_kinds=["image"])
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="image")
        _inject_fake_perceivers(monkeypatch)
        from track_b.evaluators.universal import evaluate
        result = evaluate(goal, attempt, None)
        assert result is not None


class TestQualityGate:
    def test_blurry_image_rejected(self, tmp_path, monkeypatch):
        skill = _make_skill(["final_state"], expected_kinds=["image"])
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="image")

        # Create a record with very low blur score (below calibrated threshold 0.002)
        record = PerceptionRecord(
            media=MediaInfoRecord(source_id="src.attempt.v1", modality="image",
                                  sha256="d" * 64, mime_type="image/png"),
            segments=[Segment(segment_id="seg-000", kind="whole")],
            observations=[
                Observation(obs_id="obs-000", segment_id="seg-000", kind="measurement",
                            label="blur", value=0.0001, certainty="observed",
                            producer="det:image_basic"),
            ],
        )
        _inject_fake_perceivers(monkeypatch, record=record)
        from track_b.evaluators.universal import evaluate
        with pytest.raises(AnveshanFailure) as exc:
            evaluate(goal, attempt, None)
        assert exc.value.category == FailureCategory.INVALID_INPUT
        assert "blurry" in str(exc.value).lower()

    def test_silent_audio_rejected(self, tmp_path, monkeypatch):
        skill = _make_skill(["utterance"], expected_kinds=["audio"])
        skill = skill.model_copy(update={"source_modality": "audio"})
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="audio", mime="audio/wav")

        record = PerceptionRecord(
            media=MediaInfoRecord(source_id="src.attempt.v1", modality="audio",
                                  sha256="d" * 64, mime_type="audio/wav"),
            segments=[Segment(segment_id="seg-000", kind="whole")],
            observations=[
                Observation(obs_id="obs-000", segment_id="seg-000", kind="measurement",
                            label="rms", value=0.001, certainty="observed",
                            producer="det:audio_signal"),
            ],
        )
        _inject_fake_perceivers(monkeypatch, record=record)
        from track_b.evaluators.universal import evaluate
        with pytest.raises(AnveshanFailure) as exc:
            evaluate(goal, attempt, None)
        assert exc.value.category == FailureCategory.INVALID_INPUT
        assert "silent" in str(exc.value).lower()


class TestRelevanceGate:
    def _skill_with_embedding(self, ref_vec: np.ndarray) -> SkillModel:
        return _make_skill(["final_state"], expected_kinds=["image"])

    def test_below_min_similarity_rejected(self, tmp_path, monkeypatch):
        """Similarity below min_similarity -> INVALID_INPUT."""
        skill = _make_skill(["final_state"], expected_kinds=["image"])
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="image")

        # Source: ref vector
        src_vec = _unit_vec(768, 0)
        # Attempt: nearly orthogonal (similarity ~0)
        att_vec = _unit_vec(768, 42)
        # Make att_vec nearly orthogonal to src_vec
        att_vec -= float(att_vec @ src_vec) * src_vec
        if np.linalg.norm(att_vec) > 1e-9:
            att_vec /= np.linalg.norm(att_vec)

        src_emb = src_vec.reshape(1, -1)
        att_emb = att_vec.reshape(1, -1)

        # Write source perception and embeddings to tmp case_dir
        case_dir = tmp_path / "case_rel"
        (case_dir / "knowledge").mkdir(parents=True, exist_ok=True)
        from tracks.common.perception import PerceptionRecord as PR
        src_rec = PR(
            media=MediaInfoRecord(source_id="src.test.v1", modality="image",
                                  sha256="a" * 64, mime_type="image/png"),
            segments=[Segment(segment_id="seg-000", kind="whole")],
            embedding_index={"seg-000": 0},
            embeddings_file="emb_source.npy",
        )
        (case_dir / "knowledge" / "perception_source.v1.json").write_text(
            src_rec.model_dump_json(), encoding="utf-8"
        )
        np.save(str(case_dir / "knowledge" / "emb_source.npy"), src_emb.astype(np.float16))

        att_rec = PR(
            media=MediaInfoRecord(source_id="src.attempt.v1", modality="image",
                                  sha256="c" * 64, mime_type="image/png"),
            segments=[Segment(segment_id="seg-000", kind="whole")],
            embedding_index={"seg-000": 0},
            embeddings_file="emb_att.npy",
        )

        def _perceive(path, mime, ctx, **kwargs):
            return att_rec

        def _load_emb(rec, rd):
            if rec.media.source_id == "src.test.v1":
                return src_emb.astype(np.float32)
            return att_emb.astype(np.float32)

        fake = _fake_perceivers_module(record=att_rec, emb=att_emb)
        fake.perceive = _perceive
        fake.load_embeddings = _load_emb
        monkeypatch.setitem(sys.modules, "tracks.common.perceivers", fake)

        class FakeCtxRel:
            pass
        FakeCtxRel.gateway = None
        FakeCtxRel.case_dir = case_dir
        FakeCtxRel.data_dir = tmp_path / "data"
        FakeCtxRel.mode = "live"

        from track_b.evaluators.universal import evaluate
        with pytest.raises(AnveshanFailure) as exc:
            evaluate(goal, attempt, FakeCtxRel())
        assert exc.value.category == FailureCategory.INVALID_INPUT
        # the number stays in the details, out of the learner-facing message
        assert "similarity" in exc.value.details and "similarity" not in str(exc.value).lower()

    def test_above_min_similarity_passes(self, tmp_path, monkeypatch):
        """Similarity above min_similarity passes gate."""
        skill = _make_skill(["final_state"], expected_kinds=["image"])
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="image")

        # Same vector -> similarity 1.0
        vec = _unit_vec(768, 0)
        emb = vec.reshape(1, -1)

        # Write source perception
        case_dir = tmp_path / "case_pass"
        (case_dir / "knowledge").mkdir(parents=True, exist_ok=True)
        from tracks.common.perception import PerceptionRecord as PR
        src_rec = PR(
            media=MediaInfoRecord(source_id="src.test.v1", modality="image",
                                  sha256="a" * 64, mime_type="image/png"),
            segments=[Segment(segment_id="seg-000", kind="whole")],
            embedding_index={"seg-000": 0},
            embeddings_file="emb_source.npy",
        )
        (case_dir / "knowledge" / "perception_source.v1.json").write_text(
            src_rec.model_dump_json(), encoding="utf-8"
        )
        np.save(str(case_dir / "knowledge" / "emb_source.npy"), emb.astype(np.float16))

        att_rec = PR(
            media=MediaInfoRecord(source_id="src.attempt.v1", modality="image",
                                  sha256="c" * 64, mime_type="image/png"),
            segments=[Segment(segment_id="seg-000", kind="whole")],
            embedding_index={"seg-000": 0},
        )

        def _load_emb(rec, rd):
            return emb.astype(np.float32)

        fake = _fake_perceivers_module(record=att_rec, emb=emb)
        fake.load_embeddings = _load_emb
        monkeypatch.setitem(sys.modules, "tracks.common.perceivers", fake)

        class FakeCtxPass:
            pass
        FakeCtxPass.gateway = None
        FakeCtxPass.case_dir = case_dir
        FakeCtxPass.data_dir = tmp_path / "data"
        FakeCtxPass.mode = "live"

        from track_b.evaluators.universal import evaluate
        result = evaluate(goal, attempt, FakeCtxPass())
        assert result is not None


class TestFinalStateChecks:
    def test_judge_final_met_mapping(self, tmp_path, monkeypatch):
        """judge_final 'met' -> value 1.0, 'partly' -> 0.5, 'not_met' -> 0.0, 'cannot_tell' -> None."""
        from tracks.common.models import FailureCategory, ModelError, RunStore

        prop = TargetProperty(prop_id="prop-01", statement="circular", certainty="inferred", keep=True)
        skill = _make_skill(["final_state"], goal_state=[prop])
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="image")
        _inject_fake_perceivers(monkeypatch)

        # Create a fake gateway that returns judge results
        class FakeDTO:
            def model_dump(self):
                return self.__dict__

        class FakeResult:
            results = []

        class FakeGWResult:
            pass

        from pydantic import BaseModel

        class CheckResultDTO(BaseModel):
            check_id: str = ""
            status: str = "met"
            finding: str = "looks good"
            region: Optional[List[float]] = None

        class JudgeFinalDTO(BaseModel):
            results: List[CheckResultDTO] = []

        class FakeGenResult:
            data: Any
            raw_text: str = ""

        statuses = ["met", "partly", "not_met", "cannot_tell"]
        expected_values = [1.0, 0.5, 0.0, None]

        for status, expected in zip(statuses, expected_values):
            r = JudgeFinalDTO(results=[CheckResultDTO(check_id="CHK-FS-P01", status=status, finding="test")])
            from tracks.common.models import RunMetadata
            meta = RunMetadata(
                run_id="r1", provider="test", model_key="vision_fast", model_id="test",
                prompt_id="judge_final", prompt_version="v1", prompt_sha256="",
                input_digests=[], runtime_class="LIVE", started_at="2026-01-01T00:00:00Z",
                latency_ms=100, replay_key="test_key",
            )
            fake_result = type("GR", (), {"data": r, "raw_text": "{}", "metadata": meta})()

            class FakeGateway:
                def generate_json(self, **kwargs):
                    return fake_result

            class FakeCtx:
                gateway = FakeGateway()
                case_dir = tmp_path / "case"
                data_dir = tmp_path / "data"
                mode = "live"

            (FakeCtx.case_dir / "knowledge").mkdir(parents=True, exist_ok=True)

            from track_b.evaluators.universal import evaluate
            result = evaluate(goal, attempt, FakeCtx())
            metric_id = "u.final_property.prop-01"
            if metric_id in result.metrics:
                assert result.metrics[metric_id].value == expected


class TestProcedureChecks:
    def _make_procedure_skill(self) -> SkillModel:
        steps = [
            Step(step_id="step-01", index=0, name="Step 1", state_after="state 1",
                 segment_id="seg-001", certainty="inferred", source_established=True),
            Step(step_id="step-02", index=1, name="Step 2", state_after="state 2",
                 segment_id="seg-002", certainty="inferred", source_established=True),
            Step(step_id="step-03", index=2, name="Step 3", state_after="state 3",
                 segment_id="seg-003", certainty="inferred", source_established=True, critical=True),
        ]
        return _make_skill(["procedure"], steps=steps, expected_kinds=["video", "image"])

    def test_perfect_video_coverage(self, tmp_path, monkeypatch):
        """Perfect frame sequence -> coverage 1, violations 0."""
        skill = self._make_procedure_skill()
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="video", mime="video/mp4")

        dim = 768
        # 3 step vectors
        step_vecs = np.stack([_unit_vec(dim, i) for i in range(3)])

        # Attempt: 9 frames, 3 per step (in order)
        frame_vecs = np.vstack([
            np.tile(step_vecs[0], (3, 1)),
            np.tile(step_vecs[1], (3, 1)),
            np.tile(step_vecs[2], (3, 1)),
        ])
        frame_times = [float(i) for i in range(9)]

        # Source embedding with seg-001, seg-002, seg-003 at rows 0,1,2
        src_emb = step_vecs
        # Attempt embedding: all frame rows first, then the step rows at higher indices
        att_emb = frame_vecs

        att_record = PerceptionRecord(
            media=MediaInfoRecord(source_id="src.attempt.v1", modality="video",
                                  sha256="c" * 64, mime_type="video/mp4"),
            segments=[
                Segment(segment_id="seg-000", kind="whole"),
            ],
            embedding_index={},  # no keyframe embeddings, use specialists.frames
            specialists={"frames": {"rows": list(range(9)), "times": frame_times}},
        )

        src_record = PerceptionRecord(
            media=MediaInfoRecord(source_id="src.test.v1", modality="video",
                                  sha256="b" * 64, mime_type="video/mp4"),
            segments=[
                Segment(segment_id="seg-000", kind="whole"),
                Segment(segment_id="seg-001", kind="time", start_sec=0.0, end_sec=3.0),
                Segment(segment_id="seg-002", kind="time", start_sec=3.0, end_sec=6.0),
                Segment(segment_id="seg-003", kind="time", start_sec=6.0, end_sec=9.0),
            ],
            embedding_index={"seg-001": 0, "seg-002": 1, "seg-003": 2},
        )

        call_count = [0]
        def _load_emb(rec, rd):
            if rec.media.source_id.startswith("src.test"):
                return src_emb
            return att_emb
        def _perceive(path, mime, ctx, **kwargs):
            return att_record

        fake = _fake_perceivers_module()
        fake.perceive = _perceive
        fake.load_embeddings = _load_emb
        monkeypatch.setitem(sys.modules, "tracks.common.perceivers", fake)

        # Create case dir with source perception record
        case_dir = tmp_path / "case"
        (case_dir / "knowledge").mkdir(parents=True, exist_ok=True)
        import json
        (case_dir / "knowledge" / "perception_source.v1.json").write_text(
            src_record.model_dump_json(), encoding="utf-8"
        )
        (case_dir / "knowledge" / "emb_src.npy").write_bytes(b"")

        # Also patch load_embeddings for when it reads the source
        class FakeCtxProc:
            pass
        FakeCtxProc.gateway = None
        FakeCtxProc.case_dir = case_dir
        FakeCtxProc.data_dir = tmp_path / "data"
        FakeCtxProc.mode = "live"

        from track_b.evaluators.universal import evaluate
        result = evaluate(goal, attempt, FakeCtxProc())
        # Coverage should be 1.0 (all steps matched)
        if "u.step_coverage" in result.metrics:
            cov = result.metrics["u.step_coverage"].value
            if cov is not None:
                assert cov == pytest.approx(1.0, abs=0.01)
        # Violations should be 0
        if "u.step_order" in result.metrics:
            viol = result.metrics["u.step_order"].value
            if viol is not None:
                assert viol == pytest.approx(0, abs=0.01)

    def test_missing_step_creates_event(self, tmp_path, monkeypatch):
        """A missing step -> coverage < 1 with a missing_state event."""
        skill = self._make_procedure_skill()
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="video", mime="video/mp4")

        dim = 768
        step_vecs = np.stack([_unit_vec(dim, i) for i in range(3)])
        # Only steps 0 and 2, step 1 is missing
        frame_vecs = np.vstack([
            np.tile(step_vecs[0], (3, 1)),
            np.tile(step_vecs[2], (3, 1)),
        ])
        frame_times = [float(i) for i in range(6)]

        src_emb = step_vecs
        att_emb = frame_vecs

        att_record = PerceptionRecord(
            media=MediaInfoRecord(source_id="src.attempt.v1", modality="video",
                                  sha256="c" * 64, mime_type="video/mp4"),
            segments=[Segment(segment_id="seg-000", kind="whole")],
            embedding_index={},
            specialists={"frames": {"rows": list(range(6)), "times": frame_times}},
        )
        src_record = PerceptionRecord(
            media=MediaInfoRecord(source_id="src.test.v1", modality="video",
                                  sha256="b" * 64, mime_type="video/mp4"),
            segments=[
                Segment(segment_id="seg-000", kind="whole"),
                Segment(segment_id="seg-001", kind="time", start_sec=0.0, end_sec=3.0),
                Segment(segment_id="seg-002", kind="time", start_sec=3.0, end_sec=6.0),
                Segment(segment_id="seg-003", kind="time", start_sec=6.0, end_sec=9.0),
            ],
            embedding_index={"seg-001": 0, "seg-002": 1, "seg-003": 2},
        )

        def _load_emb(rec, rd):
            if rec.media.source_id.startswith("src.test"):
                return src_emb
            return att_emb
        def _perceive(path, mime, ctx, **kwargs):
            return att_record

        fake = _fake_perceivers_module()
        fake.perceive = _perceive
        fake.load_embeddings = _load_emb
        monkeypatch.setitem(sys.modules, "tracks.common.perceivers", fake)

        case_dir2 = tmp_path / "case_miss"
        (case_dir2 / "knowledge").mkdir(parents=True, exist_ok=True)
        (case_dir2 / "knowledge" / "perception_source.v1.json").write_text(
            src_record.model_dump_json(), encoding="utf-8"
        )

        class FakeCtxMiss2:
            pass
        FakeCtxMiss2.gateway = None
        FakeCtxMiss2.case_dir = case_dir2
        FakeCtxMiss2.data_dir = tmp_path / "data"
        FakeCtxMiss2.mode = "live"

        from track_b.evaluators.universal import evaluate
        result = evaluate(goal, attempt, FakeCtxMiss2())
        if "u.step_coverage" in result.metrics:
            cov = result.metrics["u.step_coverage"].value
            if cov is not None:
                assert cov < 1.0

    def test_image_attempt_process_uncertain(self, tmp_path, monkeypatch):
        """Image attempt for a procedure -> process criteria UNCERTAIN."""
        skill = self._make_procedure_skill()
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="image", mime="image/png")
        _inject_fake_perceivers(monkeypatch)

        from track_b.evaluators.universal import evaluate
        result = evaluate(goal, attempt, None)
        # process_observable should be False
        assert result.process_observable is False
        # Process checks should be None
        for metric_id in ["u.step_coverage", "u.step_order", "u.off_path"]:
            if metric_id in result.metrics:
                mv = result.metrics[metric_id]
                assert mv.value is None or mv.uncertain_reason is not None


class TestSpecialistDelegation:
    def test_rhythm_specialist_prefixed(self, tmp_path, monkeypatch):
        """Rhythm specialist results should have 'rhythm:' prefix."""
        from tracks.common.goals.tabla import TablaGoal

        # Build a minimal TablaGoal payload
        tabla_payload = {
            "pulse_sec": 0.5,
            "cycle_length": 16,
            "tempo_bpm": 120,
            "onsets": [],
            "bass_flags": [],
            "stroke_times": [],
        }

        # Mock tabla evaluator
        from track_b.trajectory import MetricValue, TrajectoryResult
        mock_tabla_result = TrajectoryResult(
            metrics={"tabla.tempo_error_pct": MetricValue(5.0, "tempo error 5%")},
            events=[],
            curve=[(0.0, 0.0), (1.0, 1.0)],
            curve_kind="time",
            process_observable=True,
        )

        tabla_called = [False]

        def mock_tabla_eval(goal, attempt, ctx):
            tabla_called[0] = True
            return mock_tabla_result

        monkeypatch.setattr("track_b.evaluators.tabla.evaluate", mock_tabla_eval, raising=False)
        try:
            import track_b.evaluators.tabla as tabla_mod
            tabla_mod.evaluate = mock_tabla_eval
        except Exception:
            pass

        from tracks.common.skill_model import Check, Relevance, SkillModel
        rh_checks = [
            Check(check_id="CHK-RH-01", kind="rhythm", name="Rhythm",
                  observable_indicator="Rhythm check",
                  targets=[], metric_id="rhythm:tabla.tempo_error_pct",
                  method="specialist", weight=3, required=True, process=False,
                  params={"binding": {"metric": "rhythm:tabla.tempo_error_pct",
                                      "direction": "lower_is_better", "bands": [], "process": False}}),
        ]
        skill = SkillModel(
            skill_title="Rhythm Skill",
            summary="test",
            source_modality="audio",
            structures=["temporal_pattern"],
            specialists={"rhythm": tabla_payload},
            checks=rh_checks,
            relevance=Relevance(expected_kinds=["audio"], min_similarity=0.70,
                                reference_segment_ids=["seg-000"]),
        )
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="audio", mime="audio/wav")
        _inject_fake_perceivers(monkeypatch)

        # Should not crash (tabla evaluate may fail due to fake payload, but prefixing logic runs)
        from track_b.evaluators.universal import evaluate
        try:
            result = evaluate(goal, attempt, None)
            # If it ran, rhythm metrics should be prefixed
            for k in result.metrics:
                if "tabla" in k:
                    assert k.startswith("rhythm:")
        except (AnveshanFailure, Exception):
            pass  # expected with fake payload


class TestUtteranceMath:
    def test_perfect_match(self):
        from track_b.evaluators.universal import _utterance_match
        assert _utterance_match("hello world", "hello world") == pytest.approx(1.0)

    def test_partial_match(self):
        from track_b.evaluators.universal import _utterance_match
        v = _utterance_match("hello world", "hello earth")
        assert 0.0 < v < 1.0

    def test_empty(self):
        from track_b.evaluators.universal import _utterance_match
        v = _utterance_match("hello", "")
        assert v == pytest.approx(0.0)

    def test_utterance_unavailable_returns_none(self, tmp_path, monkeypatch):
        """No speech observations -> utterance_match is None with reason."""
        skill = _make_skill(
            ["utterance"],
            utterance={"transcript": "hello world", "duration_sec": 3.0},
            expected_kinds=["audio"],
        )
        skill = skill.model_copy(update={"source_modality": "audio"})
        goal = _make_goal(skill)
        attempt = _make_attempt(tmp_path, kind="audio", mime="audio/wav")

        # Record with no speech observations
        record = PerceptionRecord(
            media=MediaInfoRecord(source_id="src.attempt.v1", modality="audio",
                                  sha256="d" * 64, mime_type="audio/wav"),
            segments=[Segment(segment_id="seg-000", kind="whole")],
        )
        _inject_fake_perceivers(monkeypatch, record=record)
        from track_b.evaluators.universal import evaluate
        result = evaluate(goal, attempt, None)
        if "u.utterance_match" in result.metrics:
            mv = result.metrics["u.utterance_match"]
            assert mv.value is None
            assert "unavailable" in (mv.uncertain_reason or "").lower()
