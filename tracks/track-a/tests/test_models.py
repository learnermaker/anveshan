import pytest
from tracks.common.schemas import (
    ConsentMetadata,
    KnowledgePackage,
    VerificationState,
    ClaimType,
    ReviewStatus,
)
from models import (
    FailureCategory,
    TrackAFailure,
    ExtractedStepDTO,
    ExtractedCueDTO,
    ExtractedConditionDTO,
    ExtractedTargetPropertyDTO,
    RunMetadataDTO,
    ExtractionResponseDTO,
    normalize_dto_to_knowledge_package,
    generate_package_id,
    generate_rubric_id,
    generate_task_id,
)


def test_failure_taxonomy_values() -> None:
    expected_categories = {
        "INVALID_INPUT",
        "MISSING_EVIDENCE",
        "AMBIGUOUS_EVIDENCE",
        "UNSUPPORTED_CLAIM",
        "CONTRACT_VIOLATION",
        "MODEL_FAILURE",
        "MODEL_TIMEOUT",
        "REPLAY_MISMATCH",
        "HUMAN_REVIEW_REQUIRED",
    }
    actual = {cat.value for cat in FailureCategory}
    assert actual == expected_categories


def test_track_a_failure_exception() -> None:
    exc = TrackAFailure(
        FailureCategory.MISSING_EVIDENCE,
        "No evidence found",
        {"timestamp": 12.5},
    )
    assert exc.category == FailureCategory.MISSING_EVIDENCE
    assert "MISSING_EVIDENCE" in str(exc)
    assert exc.details["timestamp"] == 12.5


def test_artifact_id_generators() -> None:
    assert generate_package_id("micrometer", 1) == "kp.micrometer.1"
    assert generate_rubric_id("kolam", 2) == "rubric.kolam.2"
    assert generate_task_id("origami", 1) == "task.origami.1"


def test_forward_mode_normalization() -> None:
    run_meta = RunMetadataDTO(
        provider="google",
        model_id="gemini-3.8-flash",
        prompt_id="expert_extraction",
        prompt_version="v1",
        input_artifact_id="micrometer_video",
        runtime_class="REPLAY",
        run_id="run_001",
    )
    dto = ExtractionResponseDTO(
        case_id="micrometer",
        skill_id="SKILL-OPT-CALIB",
        title="Micrometer Calibration",
        summary="Zeroing dial micrometer",
        source_media_id="video_001.mp4",
        transmission_mode="forward",
        steps=[
            ExtractedStepDTO(
                index=1,
                title="Wipe anvils",
                description="Use optical lint-free paper",
                start_sec=4.5,
                end_sec=12.0,
            )
        ],
        cues=[
            ExtractedCueDTO(
                modality="audio",
                statement="3 clicks from ratchet",
                observable_indicator="Audio waveform has 3 peaks",
                start_sec=18.0,
                end_sec=22.5,
                evidence_sufficiency="OBSERVED",
            )
        ],
        run_metadata=run_meta,
    )
    consent = ConsentMetadata(
        contributor_name="Marcus Vance",
        consent_scope="engineering_replay_only",
    )
    pkg = normalize_dto_to_knowledge_package(dto, consent)
    assert isinstance(pkg, KnowledgePackage)
    assert pkg.package_id == "kp.micrometer.1"
    assert pkg.skill_id == "SKILL-OPT-CALIB"
    assert len(pkg.claims) == 2
    assert pkg.claims[0].claim_type == ClaimType.STEP
    assert pkg.claims[0].evidence_refs[0].start_sec == 4.5
    assert pkg.claims[1].claim_type == ClaimType.CUE
    assert pkg.claims[1].evidence_refs[0].verification_state == VerificationState.OBSERVED
    assert pkg.expert_review.status == ReviewStatus.PENDING


def test_goal_conditioned_mode_normalization() -> None:
    run_meta = RunMetadataDTO(
        provider="google",
        model_id="gemini-3.8-flash",
        prompt_id="goal_conditioned_extraction",
        prompt_version="v1",
        input_artifact_id="kolam_target_photo",
        runtime_class="REPLAY",
        run_id="run_kolam_01",
    )
    dto = ExtractionResponseDTO(
        case_id="kolam",
        skill_id="skill-kolam-geometry",
        title="Kolam Dot Lattice",
        summary="5x5 dot matrix loop",
        source_media_id="kolam_target.jpg",
        transmission_mode="goal-conditioned",
        target_properties=[
            ExtractedTargetPropertyDTO(
                property_id="pulli_grid",
                description="5x5 orthogonal dot lattice",
                evidence_sufficiency="OBSERVED",
                measurement="40mm spacing",
            ),
            ExtractedTargetPropertyDTO(
                property_id="loop_smoothness",
                description="Inferred continuous stroke cadence",
                evidence_sufficiency="PARTIAL",
            ),
        ],
        run_metadata=run_meta,
    )
    consent = ConsentMetadata(
        contributor_name="Kolam Practitioner",
        consent_scope="educational",
    )
    pkg = normalize_dto_to_knowledge_package(dto, consent)
    assert len(pkg.claims) == 2
    assert pkg.claims[0].is_observed is True
    assert pkg.claims[0].evidence_refs[0].verification_state == VerificationState.OBSERVED
    assert pkg.claims[1].is_observed is False
    assert pkg.claims[1].evidence_refs[0].verification_state == VerificationState.INFERRED
    assert pkg.claims[1].evidence_refs[0].confidence == 0.5


def test_empty_dto_raises_unsupported_claim() -> None:
    run_meta = RunMetadataDTO(
        provider="google",
        model_id="gemini",
        prompt_id="test",
        prompt_version="1",
        input_artifact_id="art",
        run_id="1",
    )
    dto = ExtractionResponseDTO(
        case_id="test",
        skill_id="test",
        title="test",
        summary="test",
        source_media_id="test",
        run_metadata=run_meta,
    )
    consent = ConsentMetadata(contributor_name="test", consent_scope="test")
    with pytest.raises(TrackAFailure) as exc:
        normalize_dto_to_knowledge_package(dto, consent)
    assert exc.value.category == FailureCategory.UNSUPPORTED_CLAIM
