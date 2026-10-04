"""Comprehensive unit tests for the 8 shared contracts and deterministic validator."""

import json
from pathlib import Path
import pytest
from pydantic import ValidationError

from tracks.common.schemas import (
    EvidenceRef,
    Modality,
    VerificationState,
    KnowledgePackage,
    KnowledgeClaim,
    ClaimType,
    ConsentMetadata,
    ExpertReview,
    ReviewStatus,
    RubricDefinition,
    RubricCriterion,
    PracticeTask,
    TaskConstraint,
    LearnerAttempt,
    AttemptType,
    ParticipantRef,
    Evaluation,
    CriterionResult,
    CriterionStatus,
    EvaluatorType,
    Feedback,
    FeedbackItem,
    TransmissionRecord,
    LineageMetadata,
)
from tracks.common.validator import validate_contract, validate_fixture_file


# ---------------------------------------------------------------------------
# 1. EvidenceRef Tests
# ---------------------------------------------------------------------------

def test_evidence_ref_valid():
    ref = EvidenceRef(
        evidence_id="EV-001",
        source_id="video_demo_01.mp4",
        modality=Modality.VIDEO,
        start_sec=12.5,
        end_sec=25.0,
        cue_excerpt="Expert positions tool at 45 degree angle",
        verification_state=VerificationState.OBSERVED,
        confidence=0.98,
    )
    assert ref.start_sec == 12.5
    assert ref.end_sec == 25.0
    assert ref.modality == Modality.VIDEO

    # JSON round-trip
    dumped = ref.model_dump_json()
    loaded = EvidenceRef.model_validate_json(dumped)
    assert loaded == ref


def test_evidence_ref_invalid_timestamps():
    with pytest.raises(ValidationError, match="cannot be earlier than start_sec"):
        EvidenceRef(
            evidence_id="EV-BAD",
            source_id="video.mp4",
            modality=Modality.VIDEO,
            start_sec=30.0,
            end_sec=10.0,  # Invalid: end < start
        )


# ---------------------------------------------------------------------------
# 2. KnowledgePackage Tests
# ---------------------------------------------------------------------------

def test_knowledge_package_valid():
    ev = EvidenceRef(
        evidence_id="EV-10",
        source_id="demo.mp4",
        modality=Modality.VIDEO,
        start_sec=5.0,
        end_sec=15.0,
    )
    claim1 = KnowledgeClaim(
        claim_id="C-01",
        claim_type=ClaimType.STEP,
        statement="Clean surface with isopropyl alcohol before applying flux",
        is_observed=True,
        evidence_refs=[ev],
    )
    pkg = KnowledgePackage(
        package_id="PKG-001",
        skill_id="SKILL-SOLDER-01",
        title="SMD Soldering Surface Preparation",
        summary="Standard procedure for cleaning pads before micro-soldering.",
        claims=[claim1],
        consent=ConsentMetadata(
            contributor_name="Dr. Jane Doe",
            consent_scope="hackathon_prototype",
            revocable=True,
        ),
        expert_review=ExpertReview(
            reviewer_name="Master Tech Bob",
            status=ReviewStatus.APPROVED,
            notes="Accurate step sequence.",
        ),
    )
    assert pkg.expert_review.status == ReviewStatus.APPROVED
    assert len(pkg.claims) == 1

    # Round-trip
    dumped = pkg.model_dump_json()
    loaded = KnowledgePackage.model_validate_json(dumped)
    assert loaded.package_id == "PKG-001"


def test_knowledge_package_duplicate_claims():
    ev = EvidenceRef(
        evidence_id="EV-10", source_id="demo.mp4", modality=Modality.VIDEO
    )
    claim1 = KnowledgeClaim(
        claim_id="DUPE-ID",
        claim_type=ClaimType.STEP,
        statement="Step 1",
        evidence_refs=[ev],
    )
    claim2 = KnowledgeClaim(
        claim_id="DUPE-ID",
        claim_type=ClaimType.CUE,
        statement="Cue 1",
        evidence_refs=[ev],
    )
    with pytest.raises(ValidationError, match="Duplicate claim_ids found"):
        KnowledgePackage(
            package_id="PKG-BAD",
            skill_id="SKILL-01",
            title="Bad Pkg",
            summary="Testing duplicates",
            claims=[claim1, claim2],
            consent=ConsentMetadata(
                contributor_name="Tester", consent_scope="demo"
            ),
        )


# ---------------------------------------------------------------------------
# 3. RubricDefinition Tests
# ---------------------------------------------------------------------------

def test_rubric_definition_valid():
    c1 = RubricCriterion(
        criterion_id="CRIT-01",
        name="Angle of attack",
        description="Tool held between 40 and 50 degrees",
        observable_indicator="Tool alignment gauge shows 45 deg",
        weight=2.0,
    )
    c2 = RubricCriterion(
        criterion_id="CRIT-02",
        name="Dwell time",
        description="Contact duration under 3 seconds",
        observable_indicator="Timer clock duration",
        weight=3.0,
    )
    rubric = RubricDefinition(
        rubric_id="RUBRIC-001",
        skill_id="SKILL-SOLDER-01",
        title="Soldering Proficiency Rubric",
        criteria=[c1, c2],
        passing_score=4.0,
    )
    assert rubric.max_possible_score == 5.0
    assert rubric.passing_score == 4.0


def test_rubric_invalid_passing_score():
    c1 = RubricCriterion(
        criterion_id="CRIT-01",
        name="Test",
        description="Test desc",
        observable_indicator="Visible test",
        weight=2.0,
    )
    with pytest.raises(ValidationError, match="cannot exceed max possible score"):
        RubricDefinition(
            rubric_id="RUB-BAD",
            skill_id="SK-01",
            title="Bad Rubric",
            criteria=[c1],
            passing_score=5.0,  # Invalid: 5.0 > weight 2.0
        )


# ---------------------------------------------------------------------------
# 4. PracticeTask Tests
# ---------------------------------------------------------------------------

def test_practice_task_valid():
    task = PracticeTask(
        task_id="TASK-001",
        package_id="PKG-001",
        rubric_id="RUBRIC-001",
        title="Practice Surface Preparation",
        instructions="Perform surface cleaning and flux application on test board.",
        constraints=[
            TaskConstraint(
                constraint_type="time_limit",
                description="Complete prep within 60 seconds",
                value="60s",
            )
        ],
        target_criteria_ids=["CRIT-01", "CRIT-02"],
    )
    assert task.rubric_id == "RUBRIC-001"
    assert len(task.constraints) == 1


# ---------------------------------------------------------------------------
# 5. LearnerAttempt Tests
# ---------------------------------------------------------------------------

def test_learner_attempt_baseline_and_retry():
    ev_base = EvidenceRef(
        evidence_id="EV-ATT-01",
        source_id="learner_baseline.mp4",
        modality=Modality.VIDEO,
        start_sec=0.0,
        end_sec=40.0,
    )
    base_attempt = LearnerAttempt(
        attempt_id="ATT-BASE-01",
        task_id="TASK-001",
        learner=ParticipantRef(
            participant_id="USR-101",
            name="Alice",
            role="learner",
            notes="Beginner cohort",
        ),
        attempt_type=AttemptType.BASELINE,
        attempt_number=1,
        evidence=ev_base,
    )
    assert base_attempt.attempt_type == AttemptType.BASELINE
    assert base_attempt.attempt_number == 1

    ev_retry = EvidenceRef(
        evidence_id="EV-ATT-02",
        source_id="learner_retry.mp4",
        modality=Modality.VIDEO,
        start_sec=0.0,
        end_sec=32.0,
    )
    retry_attempt = LearnerAttempt(
        attempt_id="ATT-RETRY-01",
        task_id="TASK-001",
        learner=ParticipantRef(participant_id="USR-101", name="Alice"),
        attempt_type=AttemptType.RETRY,
        attempt_number=2,
        evidence=ev_retry,
    )
    assert retry_attempt.attempt_type == AttemptType.RETRY
    assert retry_attempt.attempt_number == 2


# ---------------------------------------------------------------------------
# 6. Evaluation Tests
# ---------------------------------------------------------------------------

def test_evaluation_valid_deterministic_math():
    r1 = CriterionResult(
        criterion_id="CRIT-01",
        status=CriterionStatus.SATISFIED,
        score=2.0,
        observed_finding="Tool aligned precisely at 45 degrees.",
    )
    r2 = CriterionResult(
        criterion_id="CRIT-02",
        status=CriterionStatus.PARTIALLY_SATISFIED,
        score=1.5,
        observed_finding="Dwell time was 3.5s (slightly high).",
    )
    eval_record = Evaluation(
        evaluation_id="EVAL-001",
        attempt_id="ATT-BASE-01",
        rubric_id="RUBRIC-001",
        criterion_results=[r1, r2],
        total_score=3.5,  # 2.0 + 1.5 = 3.5
        passed=False,
        evaluator_type=EvaluatorType.MODEL_ASSISTED,
    )
    assert eval_record.total_score == 3.5


def test_evaluation_mismatched_total_score():
    r1 = CriterionResult(
        criterion_id="CRIT-01",
        status=CriterionStatus.SATISFIED,
        score=2.0,
        observed_finding="Finding 1",
    )
    with pytest.raises(ValidationError, match="total_score"):
        Evaluation(
            evaluation_id="EVAL-BAD",
            attempt_id="ATT-01",
            rubric_id="RUB-01",
            criterion_results=[r1],
            total_score=5.0,  # Invalid: score is 2.0, total declared as 5.0
        )


# ---------------------------------------------------------------------------
# 7. Feedback Tests
# ---------------------------------------------------------------------------

def test_feedback_valid():
    item = FeedbackItem(
        criterion_id="CRIT-02",
        what_was_observed="Held iron on pad for 3.5 seconds.",
        what_differed="Expert demonstrated a 1.8 second dwell time.",
        corrective_advice="Lift iron immediately after solder flows smoothly across pad.",
    )
    feedback = Feedback(
        feedback_id="FB-001",
        evaluation_id="EVAL-001",
        attempt_id="ATT-BASE-01",
        summary="Good tool angle, but dwell time needs to be reduced.",
        items=[item],
        recommended_retry_focus=["CRIT-02"],
    )
    assert len(feedback.items) == 1
    assert feedback.recommended_retry_focus == ["CRIT-02"]


# ---------------------------------------------------------------------------
# 8. TransmissionRecord & Deterministic Gain Tests
# ---------------------------------------------------------------------------

def test_transmission_record_deterministic_gain():
    record = TransmissionRecord(
        transmission_id="TX-001",
        skill_id="SKILL-SOLDER-01",
        package_id="PKG-001",
        rubric_id="RUBRIC-001",
        expert_id="EXP-JANE",
        learner_id="USR-ALICE",
        baseline_attempt_id="ATT-BASE-01",
        retry_attempt_id="ATT-RETRY-01",
        baseline_score=3.5,
        retry_score=5.0,
        transmission_gain=1.5,  # Exactly 5.0 - 3.5
        criteria_improved=["CRIT-02"],
        lineage=LineageMetadata(
            recorded_at="2026-10-04T12:00:00Z",
            provenance_hash="sha256-abc123mock",
        ),
    )
    assert record.transmission_gain == 1.5


def test_transmission_record_invalid_gain_math():
    with pytest.raises(ValidationError, match="transmission_gain"):
        TransmissionRecord(
            transmission_id="TX-BAD",
            skill_id="SKILL-01",
            package_id="PKG-01",
            rubric_id="RUB-01",
            expert_id="EXP-1",
            learner_id="LRN-1",
            baseline_attempt_id="ATT-1",
            retry_attempt_id="ATT-2",
            baseline_score=2.0,
            retry_score=4.0,
            transmission_gain=3.0,  # Invalid: 4.0 - 2.0 = 2.0, not 3.0
            lineage=LineageMetadata(recorded_at="2026-10-04T12:00:00Z"),
        )


# ---------------------------------------------------------------------------
# 9. Validator Utility Tests
# ---------------------------------------------------------------------------

def test_validator_dict_and_file(tmp_path: Path):
    data = {
        "evidence_id": "EV-CLI",
        "source_id": "test.mp4",
        "modality": "video",
        "start_sec": 1.0,
        "end_sec": 5.0,
    }
    validated = validate_contract(data, "EvidenceRef")
    assert isinstance(validated, EvidenceRef)

    # Test file validation
    fixture_file = tmp_path / "valid_evidence.json"
    fixture_file.write_text(json.dumps(data), encoding="utf-8")

    success, msg, instance = validate_fixture_file(fixture_file, "EvidenceRef")
    assert success is True
    assert isinstance(instance, EvidenceRef)

    # Test auto-detection without explicit type
    success_auto, _, instance_auto = validate_fixture_file(fixture_file)
    assert success_auto is True
    assert isinstance(instance_auto, EvidenceRef)
