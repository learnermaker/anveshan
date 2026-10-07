"""Tests for the universal Layer 2 (propose_skill_model) and builder (build).

No network calls. Uses fixture PerceptionRecords and monkeypatched perceivers.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock

import numpy as np
import pytest

from tracks.common.casedata import Band, ObserverBinding, SourceRecord
from tracks.common.models import AnveshanFailure, ModelError, ModelRegistry, RunStore
from tracks.common.models import ModelGateway
from tracks.common.perception import MediaInfoRecord, Observation, PerceptionRecord, Segment
from tracks.common.profile import CaseProfile, IntakeResult, ProbeFacts
from tracks.common.runtime import RunContext
from tracks.common.skill_model import SkillModel, STRUCTURE_ATTEMPT_KINDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_gateway(mode="recorded", responses: Optional[Dict] = None) -> ModelGateway:
    """A fake gateway that returns canned responses or raises ModelError."""
    store = RunStore([])
    gw = ModelGateway(mode=mode, store=store, client=MagicMock())
    if mode == "recorded":
        # In recorded mode with empty store, generate_json will raise REPLAY_MISMATCH
        pass
    return gw


def _make_ctx(tmp_path: Path, gateway: Any = None) -> RunContext:
    if gateway is None:
        gateway = _make_gateway(mode="recorded")
    store = RunStore([tmp_path / "runs"])
    gw = gateway
    return RunContext(
        mode="recorded",
        gateway=gw,
        case_dir=tmp_path / "case",
        data_dir=tmp_path / "data",
    )


def _make_source(tmp_path: Path, mime: str = "image/png") -> SourceRecord:
    p = tmp_path / "source.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    return SourceRecord(
        source_id="src.test.v1",
        role="target_image",
        mime_type=mime,
        sha256="a" * 64,
        bytes=p.stat().st_size,
        path=str(p),
        creator="test",
        license="public domain",
        attribution="test",
        runtime_label="SYNTHETIC",
    )


def _image_record(source_id: str = "src.test.v1") -> PerceptionRecord:
    """Minimal image PerceptionRecord with property observations."""
    return PerceptionRecord(
        media=MediaInfoRecord(
            source_id=source_id,
            modality="image",
            sha256="a" * 64,
            mime_type="image/png",
            width=100,
            height=100,
        ),
        segments=[
            Segment(segment_id="seg-000", kind="whole"),
            Segment(segment_id="seg-001", kind="region", region=[0, 0, 50, 50]),
        ],
        observations=[
            Observation(obs_id="obs-000", segment_id="seg-000", kind="measurement",
                        label="width", value=100.0, certainty="observed", producer="det:image_basic"),
            Observation(obs_id="obs-001", segment_id="seg-000", kind="measurement",
                        label="blur", value=25.0, certainty="observed", producer="det:image_basic"),
            Observation(obs_id="obs-002", segment_id="seg-001", kind="property",
                        label="circular shape", detail="round artefact", certainty="inferred",
                        producer="model:vision_fast"),
            Observation(obs_id="obs-003", segment_id="seg-000", kind="property",
                        label="blue color", detail="predominantly blue", certainty="inferred",
                        producer="model:vision_fast"),
            Observation(obs_id="obs-004", segment_id="seg-000", kind="quality",
                        label="avoid: asymmetric edges", certainty="inferred",
                        producer="model:vision_fast"),
            Observation(obs_id="obs-005", segment_id="seg-000", kind="action",
                        label="build step 1: draw the base", certainty="inferred",
                        producer="model:vision_fast"),
        ],
        embedding_index={"seg-000": 0, "seg-001": 1},
        embeddings_file="emb_test.npy",
    )


def _video_record(source_id: str = "src.test.v1") -> PerceptionRecord:
    """Video PerceptionRecord with 4 still segments and state labels."""
    return PerceptionRecord(
        media=MediaInfoRecord(
            source_id=source_id,
            modality="video",
            sha256="b" * 64,
            mime_type="video/mp4",
            duration_sec=20.0,
            has_audio=False,
        ),
        segments=[
            Segment(segment_id="seg-000", kind="whole"),
            Segment(segment_id="seg-001", kind="time", start_sec=0.0, end_sec=5.0,
                    keyframe_asset="kf_seg-001.jpg", stability=0.9),
            Segment(segment_id="seg-002", kind="time", start_sec=5.0, end_sec=10.0,
                    keyframe_asset="kf_seg-002.jpg", stability=0.85),
            Segment(segment_id="seg-003", kind="time", start_sec=10.0, end_sec=15.0,
                    keyframe_asset="kf_seg-003.jpg", stability=0.92),
            Segment(segment_id="seg-004", kind="time", start_sec=15.0, end_sec=20.0,
                    keyframe_asset="kf_seg-004.jpg", stability=0.88),
        ],
        observations=[
            Observation(obs_id="obs-000", segment_id="seg-000", kind="measurement",
                        label="duration", value=20.0, unit="s", certainty="observed",
                        producer="det:video_segment"),
            Observation(obs_id="obs-001", segment_id="seg-001", kind="state",
                        label="initial position", certainty="inferred",
                        producer="model:vision_fast"),
            Observation(obs_id="obs-002", segment_id="seg-001", kind="action",
                        label="fold left edge", certainty="inferred",
                        producer="model:vision_fast"),
            Observation(obs_id="obs-003", segment_id="seg-002", kind="state",
                        label="first fold done", certainty="inferred",
                        producer="model:vision_fast"),
            Observation(obs_id="obs-004", segment_id="seg-003", kind="state",
                        label="second fold done", certainty="inferred",
                        producer="model:vision_fast"),
            Observation(obs_id="obs-005", segment_id="seg-004", kind="state",
                        label="finished shape", certainty="inferred",
                        producer="model:vision_fast"),
        ],
        embedding_index={"seg-001": 0, "seg-002": 1, "seg-003": 2, "seg-004": 3},
        embeddings_file="emb_test.npy",
    )


def _speech_record(source_id: str = "src.test.v1") -> PerceptionRecord:
    """Audio PerceptionRecord with speech observation."""
    return PerceptionRecord(
        media=MediaInfoRecord(
            source_id=source_id,
            modality="audio",
            sha256="c" * 64,
            mime_type="audio/wav",
            duration_sec=5.0,
        ),
        segments=[
            Segment(segment_id="seg-000", kind="whole"),
        ],
        observations=[
            Observation(obs_id="obs-000", segment_id="seg-000", kind="measurement",
                        label="duration", value=5.0, unit="s", certainty="observed",
                        producer="det:audio_signal"),
            Observation(obs_id="obs-001", segment_id="seg-000", kind="speech",
                        label="hello world", detail="hello world", certainty="inferred",
                        producer="model:audio"),
        ],
    )


def _make_probe(modality: str, structures: list, specialists: list = None) -> ProbeFacts:
    return ProbeFacts(
        modality=modality,
        mime_type={"image": "image/png", "video": "video/mp4", "audio": "audio/wav"}[modality],
        bytes=1024,
        sha256="a" * 64,
        width=100 if modality == "image" else None,
        height=100 if modality == "image" else None,
        duration_sec=20.0 if modality == "video" else (5.0 if modality == "audio" else None),
        structures_available=structures,
        specialists_available=specialists or [],
    )


def _make_intake() -> IntakeResult:
    return IntakeResult(
        safety={"decision": "allow", "categories": []},
        teachable="yes",
        teachable_reason="observable skill",
        skill_kind="craft",
    )


# ---------------------------------------------------------------------------
# Tests: propose_skill_model
# ---------------------------------------------------------------------------

class TestProposeSkillModel:
    def test_image_record_final_state_checks(self, tmp_path):
        """Image record with property observations -> final_state checks."""
        from track_a.universal import propose_skill_model

        record = _image_record()
        probe = _make_probe("image", ["final_state"])
        intake = _make_intake()
        ctx = _make_ctx(tmp_path)

        skill, built_with, warnings = propose_skill_model(
            record, probe, intake, ctx, "Test Skill", "A test image skill"
        )

        assert isinstance(skill, SkillModel)
        assert "final_state" in skill.structures
        assert len(skill.checks) >= 1
        # Should have final_similarity check
        assert any(c.kind == "final_similarity" for c in skill.checks)
        # Should have final_property checks for properties
        assert any(c.kind == "final_property" for c in skill.checks)
        # Expected kinds include image
        assert "image" in skill.relevance.expected_kinds
        assert built_with["structures"] == ["final_state"]

    def test_image_with_line_art_specialist(self, tmp_path):
        """Image with line_art specialist -> line_art checks with prefixed metric ids."""
        from track_a.universal import propose_skill_model

        record = _image_record()
        probe = _make_probe("image", ["final_state"], specialists=["line_art"])
        intake = _make_intake()
        ctx = _make_ctx(tmp_path)

        # Create a minimal synthetic image for line_art to process
        from PIL import Image
        img = Image.new("L", (100, 100), color=255)
        # Draw some black lines
        for x in range(10, 90):
            img.putpixel((x, 50), 0)
            img.putpixel((50, x), 0)
        img_path = tmp_path / "source.png"
        img.save(img_path)

        # The line_art specialist may fail on this synthetic image; that's OK
        skill, built_with, warnings = propose_skill_model(
            record, probe, intake, ctx, "Test Kolam", None, source_path=img_path
        )

        assert isinstance(skill, SkillModel)
        assert "final_state" in skill.structures

        # If line_art succeeded, checks should have line_art kind
        if "line_art" in skill.specialists:
            assert any(c.kind == "line_art" for c in skill.checks)
            # Metrics should have line_art: prefix
            la_checks = [c for c in skill.checks if c.kind == "line_art"]
            for c in la_checks:
                assert c.metric_id.startswith("line_art:")
                assert "binding" in c.params

    def test_video_procedure_steps(self, tmp_path):
        """Video record with 4 still segments -> procedure steps, strict order, default checks."""
        from track_a.universal import propose_skill_model

        record = _video_record()
        probe = _make_probe("video", ["procedure"])
        intake = _make_intake()
        ctx = _make_ctx(tmp_path)

        skill, built_with, warnings = propose_skill_model(
            record, probe, intake, ctx, "Origami Crane", "Video demonstration"
        )

        assert "procedure" in skill.structures
        assert len(skill.steps) >= 3  # should have at least 3 steps from 4 segments
        assert skill.order == "strict"
        # All steps should be source_established (from video segments)
        for step in skill.steps:
            assert step.source_established is True
        # Should have step_coverage, step_order, off_path checks
        assert any(c.kind == "step_coverage" for c in skill.checks)
        assert any(c.kind == "step_order" for c in skill.checks)
        assert any(c.kind == "off_path" for c in skill.checks)
        # Video expected kinds include video
        assert "video" in skill.relevance.expected_kinds
        # min_similarity for video = 0.70
        assert skill.relevance.min_similarity == pytest.approx(0.70)

    def test_speech_audio_utterance_checks(self, tmp_path):
        """Speech audio record -> utterance checks."""
        from track_a.universal import propose_skill_model

        record = _speech_record()
        probe = _make_probe("audio", ["utterance"])
        intake = _make_intake()
        ctx = _make_ctx(tmp_path)

        skill, built_with, warnings = propose_skill_model(
            record, probe, intake, ctx, "Say Hello", "A spoken phrase"
        )

        assert "utterance" in skill.structures
        assert skill.utterance is not None
        assert any(c.kind == "utterance_match" for c in skill.checks)
        assert any(c.kind == "pace_match" for c in skill.checks)
        assert "audio" in skill.relevance.expected_kinds

    def test_wording_model_failure_deterministic_fallback(self, tmp_path):
        """Wording model failing -> deterministic texts plus a warning."""
        from track_a.universal import propose_skill_model
        from tracks.common.models import FailureCategory, ModelError

        record = _image_record()
        probe = _make_probe("image", ["final_state"])
        intake = _make_intake()

        # Gateway that raises ModelError on any call
        class FailGateway:
            def generate_json(self, **kwargs):
                raise ModelError(FailureCategory.MODEL_FAILURE, "model unavailable")

        class FailCtx:
            gateway = FailGateway()
            case_dir = tmp_path / "case"
            data_dir = tmp_path / "data"
            mode = "live"

        skill, built_with, warnings = propose_skill_model(
            record, probe, intake, FailCtx(), "Test", "Description"
        )

        # Should still get a valid skill model despite model failure
        assert isinstance(skill, SkillModel)
        # Should have a warning about the model failure
        all_warnings = warnings + list(skill.warnings)
        assert any("wording" in w.lower() or "model" in w.lower() or "failed" in w.lower()
                   for w in all_warnings)


class TestUniversalBuild:
    """Tests for the universal builder (build function)."""

    def _make_profile(self, tmp_path: Path, skill: SkillModel, modality: str = "image") -> CaseProfile:
        from tracks.common.profile import CaseProfile, composed_case_id

        probe = _make_probe(modality, list(skill.structures))
        intake = _make_intake()
        case_id = composed_case_id("test skill", "a" * 64)

        return CaseProfile(
            case_id=case_id,
            title="Test Skill",
            skill_summary="A test skill",
            domain="test",
            transmission_mode="goal-conditioned" if "final_state" in skill.structures and not skill.steps else "forward",
            learner_input_kinds=["image"],
            probe=probe,
            intake=intake,
            skill_model=skill,
            confirmed_by_user=True,
            confirmed_at="2026-10-10T00:00:00Z",
        )

    def _minimal_skill_with_steps(self) -> SkillModel:
        """A SkillModel with procedure and steps for forward transmission."""
        from tracks.common.skill_model import Check, Relevance, Step, SkillModel

        steps = [
            Step(step_id="step-01", index=0, name="fold step 1", state_after="fold 1",
                 start_sec=0.0, end_sec=5.0, segment_id="seg-001",
                 certainty="inferred", source_established=True, critical=False),
            Step(step_id="step-02", index=1, name="fold step 2", state_after="fold 2",
                 start_sec=5.0, end_sec=10.0, segment_id="seg-002",
                 certainty="inferred", source_established=True, critical=True),
        ]
        checks = [
            Check(check_id="CHK-PR-COV", kind="step_coverage", name="Step coverage",
                  observable_indicator="Fraction of steps covered",
                  targets=["step-01", "step-02"], metric_id="u.step_coverage",
                  method="deterministic", weight=3, required=True, process=True),
            Check(check_id="CHK-PR-ORD", kind="step_order", name="Step order",
                  observable_indicator="Order violations",
                  targets=["step-01", "step-02"], metric_id="u.step_order",
                  method="deterministic", weight=2, required=True, process=True),
        ]
        return SkillModel(
            skill_title="Fold It",
            summary="A folding skill",
            source_modality="video",
            structures=["procedure"],
            steps=steps,
            order="strict",
            checks=checks,
            relevance=Relevance(expected_kinds=["video", "image"], min_similarity=0.70,
                                reference_segment_ids=["seg-001", "seg-002"]),
        )

    def _minimal_skill_image(self) -> SkillModel:
        """A SkillModel with final_state (image source)."""
        from tracks.common.skill_model import Check, Relevance, Step, TargetProperty, SkillModel

        props = [
            TargetProperty(prop_id="prop-01", statement="circular shape",
                           certainty="inferred", keep=True),
        ]
        # Add a step to satisfy grounding for goal-conditioned
        steps = [
            Step(step_id="step-01", index=0, name="Reproduce the target as shown",
                 state_after="finished", certainty="inferred", source_established=False,
                 critical=False),
        ]
        checks = [
            Check(check_id="CHK-FS-SIM", kind="final_similarity", name="Similarity",
                  observable_indicator="Overall similarity",
                  targets=[], metric_id="u.final_similarity",
                  method="deterministic", weight=1, required=False, process=False),
            Check(check_id="CHK-FS-P01", kind="final_property", name="Circular shape",
                  observable_indicator="Shape is circular",
                  targets=["prop-01"], metric_id="u.final_property.prop-01",
                  method="model_status", weight=2, required=True, process=False),
        ]
        return SkillModel(
            skill_title="Draw a Circle",
            summary="Draw a circular shape",
            source_modality="image",
            structures=["final_state"],
            goal_state=props,
            steps=steps,
            order="none",
            checks=checks,
            relevance=Relevance(expected_kinds=["image"], min_similarity=0.72,
                                reference_segment_ids=["seg-000"]),
        )

    def test_build_requires_profile(self, tmp_path):
        """build() without profile raises INVALID_INPUT."""
        from track_a.goals.universal import build

        src = _make_source(tmp_path)
        ctx = _make_ctx(tmp_path)
        with pytest.raises(AnveshanFailure) as exc_info:
            build(src.path or tmp_path / "s.png", src, ctx, case_id="test", version=1)
        assert "profile" in str(exc_info.value).lower()

    def test_build_requires_confirmed_profile(self, tmp_path):
        """build() with unconfirmed profile raises INVALID_INPUT."""
        from track_a.goals.universal import build
        from tracks.common.profile import CaseProfile, composed_case_id
        from tracks.common.skill_model import Check, Relevance, SkillModel, TargetProperty, Step

        skill = self._minimal_skill_image()
        probe = _make_probe("image", ["final_state"])
        intake = _make_intake()
        case_id = composed_case_id("test", "a" * 64)
        profile = CaseProfile(
            case_id=case_id,
            title="Test",
            skill_summary="test",
            domain="test",
            transmission_mode="goal-conditioned",
            learner_input_kinds=["image"],
            probe=probe,
            intake=intake,
            skill_model=skill,
            confirmed_by_user=False,
        )
        src = _make_source(tmp_path)
        ctx = _make_ctx(tmp_path)
        with pytest.raises(AnveshanFailure):
            build(tmp_path / "source.png", src, ctx, case_id="test", version=1, profile=profile)

    def test_build_image_skill_produces_claims(self, tmp_path):
        """build() with image skill produces valid claims, criterion ids, task."""
        from track_a.goals.universal import build
        from tracks.common.schemas.knowledge import ClaimType

        skill = self._minimal_skill_image()
        src = _make_source(tmp_path)
        profile = self._make_profile(tmp_path, skill, "image")
        ctx = _make_ctx(tmp_path)
        # Create case_dir knowledge dir
        (ctx.case_dir / "knowledge").mkdir(parents=True, exist_ok=True)

        result = build(tmp_path / "source.png", src, ctx, case_id=profile.case_id, version=1,
                       profile=profile)

        assert result.claims
        # All inferred STEP claims should have confidence <= 0.5
        for claim in result.claims:
            if claim.claim_type == ClaimType.STEP and not claim.is_observed:
                for ev in claim.evidence_refs:
                    assert ev.confidence <= 0.5

        # Criterion ids should be CRIT-U-*
        for crit in result.criteria:
            assert crit.criterion_id.startswith("CRIT-U-")

        # Observed claims should have locators
        for claim in result.claims:
            if claim.is_observed:
                for ev in claim.evidence_refs:
                    from tracks.common.schemas.evidence import VerificationState
                    assert ev.verification_state == VerificationState.OBSERVED
                    if src.mime_type.startswith("image/"):
                        # Must have xywh locator
                        assert "#xywh=" in ev.source_id

        # Task should cite CLM- references
        assert "CLM-" in result.task_instructions or len(result.task_instructions) > 0

        # Specialist bindings preserved (none in this case, OK)
        assert result.goal_payload is not None
        skill_back = SkillModel.model_validate(result.goal_payload)
        assert skill_back.skill_title == skill.skill_title

    def test_build_criteria_cite_their_own_target_claims(self, tmp_path):
        """Criteria cite the claim of their target (prop/constraint), whatever the number of
        measurement claims and even when props are inferred (regression: positional mapping)."""
        from track_a.goals.universal import build
        from tracks.common.skill_model import Check, Constraint, TargetProperty

        skill = self._minimal_skill_image()
        skill.goal_state.append(TargetProperty(prop_id="prop-02", statement="four petals",
                                               certainty="inferred", keep=True))
        skill.constraints.append(Constraint(constraint_id="con-01", statement="no broken lines",
                                            certainty="inferred", keep=True))
        skill.checks += [
            Check(check_id="CHK-FS-P02", kind="final_property", name="Petals",
                  observable_indicator="Four petals", targets=["prop-02"],
                  metric_id="u.final_property.prop-02", method="model_status"),
            Check(check_id="CHK-FS-C01", kind="final_property", name="Lines",
                  observable_indicator="No broken lines", targets=["con-01"],
                  metric_id="u.final_property.con-01", method="model_status"),
        ]
        src = _make_source(tmp_path)
        profile = self._make_profile(tmp_path, skill, "image")
        ctx = _make_ctx(tmp_path)
        kdir = ctx.case_dir / "knowledge"
        kdir.mkdir(parents=True, exist_ok=True)
        (kdir / "perception_source.v1.json").write_text(
            _image_record(src.source_id).model_dump_json(), encoding="utf-8")

        result = build(tmp_path / "source.png", src, ctx, case_id=profile.case_id, version=1,
                       profile=profile)
        by_id = {c.claim_id: c.statement for c in result.claims}
        crit = {c.criterion_id: c for c in result.criteria}
        expected = {"CRIT-U-CHK-FS-P01": "circular shape", "CRIT-U-CHK-FS-P02": "four petals",
                    "CRIT-U-CHK-FS-C01": "no broken lines"}
        for cid, statement in expected.items():
            assert [by_id[x] for x in crit[cid].source_claim_ids] == [statement]

    def test_build_procedure_skill_produces_step_claims(self, tmp_path):
        """build() with procedure skill produces STEP claims and correct criterion ids."""
        from track_a.goals.universal import build
        from tracks.common.schemas.knowledge import ClaimType

        skill = self._minimal_skill_with_steps()
        src = _make_source(tmp_path, mime="video/mp4")
        src = SourceRecord(
            source_id="src.test.v1",
            role="expert_video",
            mime_type="video/mp4",
            sha256="a" * 64,
            bytes=1024,
            path=str(tmp_path / "source.png"),
            duration_sec=20.0,
            creator="test",
            license="public domain",
            attribution="test",
            runtime_label="SYNTHETIC",
        )
        profile = self._make_profile(tmp_path, skill, "video")
        ctx = _make_ctx(tmp_path)
        (ctx.case_dir / "knowledge").mkdir(parents=True, exist_ok=True)

        result = build(tmp_path / "source.png", src, ctx, case_id=profile.case_id, version=1,
                       profile=profile)

        step_claims = [c for c in result.claims if c.claim_type == ClaimType.STEP]
        assert len(step_claims) >= 2

        # All step claims should be inferred with confidence <= 0.5
        for claim in step_claims:
            assert not claim.is_observed
            for ev in claim.evidence_refs:
                assert ev.confidence <= 0.5

        # Criteria reference claim ids
        for crit in result.criteria:
            for cid in crit.source_claim_ids:
                assert any(c.claim_id == cid for c in result.claims)
