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
from tracks.common.validator import (
    validate_contract,
    validate_fixture_file,
    validate_evaluation_against_rubric,
    validate_practice_task_against_knowledge_and_rubric,
    validate_feedback_against_evaluation,
    validate_transmission_record_invariants,
    validate_transmission_bundle,
    load_bundle_from_directory,
)


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


# ---------------------------------------------------------------------------
# 10. Attempt Numbering Invariant Tests
# ---------------------------------------------------------------------------

def test_learner_attempt_invalid_attempt_numbers():
    ev = EvidenceRef(
        evidence_id="EV-1", source_id="test.mp4", modality=Modality.VIDEO
    )
    # BASELINE with attempt_number != 1 should fail
    with pytest.raises(ValidationError, match="BASELINE attempt must have attempt_number == 1"):
        LearnerAttempt(
            attempt_id="ATT-BAD-1",
            task_id="TASK-1",
            learner=ParticipantRef(participant_id="P1", name="Learner 1"),
            attempt_type=AttemptType.BASELINE,
            attempt_number=2,  # Invalid for baseline
            evidence=ev,
        )

    # RETRY with attempt_number < 2 should fail
    with pytest.raises(ValidationError, match="RETRY attempt must have attempt_number >= 2"):
        LearnerAttempt(
            attempt_id="ATT-BAD-2",
            task_id="TASK-1",
            learner=ParticipantRef(participant_id="P1", name="Learner 1"),
            attempt_type=AttemptType.RETRY,
            attempt_number=1,  # Invalid for retry
            evidence=ev,
        )


# ---------------------------------------------------------------------------
# 11. Canonical Replay Fixture (transmission_case_001) Tests
# ---------------------------------------------------------------------------

def test_canonical_replay_fixture_case_001():
    fixture_dir = Path(__file__).parent / "fixtures" / "transmission_case_001"
    assert fixture_dir.exists(), f"Fixture directory not found: {fixture_dir}"

    # 1. Test directory loading
    bundle_data = load_bundle_from_directory(fixture_dir)
    assert "knowledge_package" in bundle_data
    assert "rubric" in bundle_data

    # 2. Test bundle validation
    is_valid, errors = validate_transmission_bundle(bundle_data)
    assert is_valid is True, f"Canonical bundle validation failed with errors: {errors}"

    # 3. Test bundle.json file validation via CLI function
    bundle_json_path = fixture_dir / "bundle.json"
    success, msg, _ = validate_fixture_file(bundle_json_path, is_bundle=True)
    assert success is True, f"Failed to validate bundle.json: {msg}"

    # 4. Test directory validation via CLI function
    success_dir, msg_dir, _ = validate_fixture_file(fixture_dir, is_bundle=True)
    assert success_dir is True, f"Failed to validate fixture directory: {msg_dir}"


# ---------------------------------------------------------------------------
# 12. Cross-Contract Invariant Negative Tests
# ---------------------------------------------------------------------------

def test_cross_contract_evaluation_against_rubric_failures():
    rubric = RubricDefinition(
        rubric_id="R-01",
        skill_id="SK-01",
        title="Test Rubric",
        criteria=[
            RubricCriterion(
                criterion_id="C1",
                name="Crit 1",
                description="Desc 1",
                observable_indicator="Ind 1",
                weight=2.0,
                required=True,
            ),
            RubricCriterion(
                criterion_id="C2",
                name="Crit 2",
                description="Desc 2",
                observable_indicator="Ind 2",
                weight=3.0,
                required=True,
            ),
        ],
        passing_score=4.0,
    )

    # Failure 1: Unknown criterion
    eval_unknown = Evaluation(
        evaluation_id="E1",
        attempt_id="A1",
        rubric_id="R-01",
        criterion_results=[
            CriterionResult(
                criterion_id="C-UNKNOWN",
                status=CriterionStatus.SATISFIED,
                score=2.0,
                observed_finding="Unknown test",
            )
        ],
        total_score=2.0,
    )
    errs = validate_evaluation_against_rubric(eval_unknown, rubric)
    assert any("unknown criterion_id 'C-UNKNOWN'" in e for e in errs)

    # Failure 2: Score exceeds weight
    eval_over_weight = Evaluation(
        evaluation_id="E2",
        attempt_id="A1",
        rubric_id="R-01",
        criterion_results=[
            CriterionResult(
                criterion_id="C1",
                status=CriterionStatus.SATISFIED,
                score=3.5,  # Weight is 2.0!
                observed_finding="Over weight",
            )
        ],
        total_score=3.5,
    )
    errs2 = validate_evaluation_against_rubric(eval_over_weight, rubric)
    assert any("exceeds rubric max points" in e for e in errs2)

    # Failure 3: Missing required criterion
    eval_missing_req = Evaluation(
        evaluation_id="E3",
        attempt_id="A1",
        rubric_id="R-01",
        criterion_results=[
            CriterionResult(
                criterion_id="C1",
                status=CriterionStatus.SATISFIED,
                score=2.0,
                observed_finding="Only C1",
            )
        ],
        total_score=2.0,
    )
    errs3 = validate_evaluation_against_rubric(eval_missing_req, rubric)
    assert any("Required rubric criterion 'C2'" in e for e in errs3)

    # Failure 4: Passed flag is True but total_score below passing_score
    eval_inconsistent_pass = Evaluation(
        evaluation_id="E4",
        attempt_id="A1",
        rubric_id="R-01",
        criterion_results=[
            CriterionResult(
                criterion_id="C1",
                status=CriterionStatus.SATISFIED,
                score=2.0,
                observed_finding="Finding 1",
            ),
            CriterionResult(
                criterion_id="C2",
                status=CriterionStatus.PARTIALLY_SATISFIED,
                score=1.0,
                observed_finding="Finding 2",
            ),
        ],
        total_score=3.0,  # Below passing_score 4.0
        passed=True,      # Inconsistent!
    )
    errs4 = validate_evaluation_against_rubric(eval_inconsistent_pass, rubric)
    assert any("below rubric passing_score" in e for e in errs4)


def test_cross_contract_feedback_failures():
    evaluation = Evaluation(
        evaluation_id="EVAL-01",
        attempt_id="ATT-01",
        rubric_id="RUB-01",
        criterion_results=[
            CriterionResult(
                criterion_id="C1",
                status=CriterionStatus.PARTIALLY_SATISFIED,
                score=1.0,
                observed_finding="Observed C1",
            )
        ],
        total_score=1.0,
    )

    # Feedback references non-existent criterion
    feedback_bad = Feedback(
        feedback_id="FB-01",
        evaluation_id="EVAL-01",
        attempt_id="ATT-01",
        summary="Summary",
        items=[
            FeedbackItem(
                criterion_id="C-NON-EXISTENT",
                what_was_observed="Obs",
                what_differed="Diff",
                corrective_advice="Advice",
            )
        ],
    )
    errs = validate_feedback_against_evaluation(feedback_bad, evaluation)
    assert any("references criterion 'C-NON-EXISTENT' not evaluated" in e for e in errs)


# ---------------------------------------------------------------------------
# 13. Current cross-contract alignment invariants
# ---------------------------------------------------------------------------

def test_cross_contract_alignment_rejects_mismatched_attempts_and_criteria():
    rubric = RubricDefinition(
        rubric_id="R-ALIGN",
        skill_id="SKILL-ALIGN",
        title="Alignment Rubric",
        criteria=[
            RubricCriterion(
                criterion_id="C1",
                name="Criterion 1",
                description="Observable criterion",
                observable_indicator="Visible indicator",
                weight=2.0,
                required=True,
            ),
            RubricCriterion(
                criterion_id="C2",
                name="Criterion 2",
                description="Observable criterion",
                observable_indicator="Visible indicator",
                weight=2.0,
                required=True,
            ),
        ],
        passing_score=3.0,
    )
    task = PracticeTask(
        task_id="TASK-ALIGN",
        package_id="PKG-ALIGN",
        rubric_id="R-ALIGN",
        title="Alignment task",
        instructions="Perform the bounded task.",
        target_criteria_ids=["C1", "C2"],
    )
    ev1 = EvidenceRef(
        evidence_id="EV-A1",
        source_id="baseline.mp4",
        modality=Modality.VIDEO,
    )
    ev2 = EvidenceRef(
        evidence_id="EV-A2",
        source_id="retry.mp4",
        modality=Modality.VIDEO,
    )
    baseline = LearnerAttempt(
        attempt_id="ATT-A1",
        task_id="TASK-ALIGN",
        learner=ParticipantRef(participant_id="L1", name="Learner"),
        attempt_type=AttemptType.BASELINE,
        attempt_number=1,
        evidence=ev1,
    )
    retry = LearnerAttempt(
        attempt_id="ATT-A2",
        task_id="TASK-ALIGN",
        learner=ParticipantRef(participant_id="L1", name="Learner"),
        attempt_type=AttemptType.RETRY,
        attempt_number=2,
        evidence=ev2,
    )
    baseline_eval = Evaluation(
        evaluation_id="E-A1",
        attempt_id="WRONG-ATTEMPT",
        rubric_id="R-ALIGN",
        criterion_results=[
            CriterionResult(
                criterion_id="C1",
                status=CriterionStatus.SATISFIED,
                score=1.0,
                observed_finding="Observed",
            ),
            CriterionResult(
                criterion_id="C2",
                status=CriterionStatus.PARTIALLY_SATISFIED,
                score=1.0,
                observed_finding="Observed",
            ),
        ],
        total_score=2.0,
    )
    retry_eval = Evaluation(
        evaluation_id="E-A2",
        attempt_id="ATT-A2",
        rubric_id="R-ALIGN",
        criterion_results=[
            CriterionResult(
                criterion_id="C1",
                status=CriterionStatus.SATISFIED,
                score=2.0,
                observed_finding="Improved",
            ),
            CriterionResult(
                criterion_id="C2",
                status=CriterionStatus.SATISFIED,
                score=2.0,
                observed_finding="Improved",
            ),
        ],
        total_score=4.0,
        passed=True,
    )
    record = TransmissionRecord(
        transmission_id="TX-ALIGN",
        skill_id="SKILL-ALIGN",
        package_id="PKG-ALIGN",
        rubric_id="R-ALIGN",
        expert_id="EXP-1",
        learner_id="L1",
        baseline_attempt_id="ATT-A1",
        retry_attempt_id="ATT-A2",
        baseline_score=2.0,
        retry_score=4.0,
        transmission_gain=2.0,
        criteria_improved=["C1", "C2"],
        lineage=LineageMetadata(recorded_at="2026-10-04T12:00:00Z"),
    )

    errors = validate_transmission_record_invariants(
        record, task, rubric, baseline, retry, baseline_eval, retry_eval
    )
    assert any("baseline_eval attempt_id" in e for e in errors)


def test_cross_contract_alignment_rejects_unknown_improved_criterion_and_required_partial_pass():
    rubric = RubricDefinition(
        rubric_id="R-PASS",
        skill_id="SKILL-PASS",
        title="Pass semantics",
        criteria=[
            RubricCriterion(
                criterion_id="C1",
                name="Required criterion",
                description="Must be satisfied",
                observable_indicator="Observable",
                weight=2.0,
                required=True,
            ),
        ],
        passing_score=1.0,
    )
    evaluation = Evaluation(
        evaluation_id="E-PASS",
        attempt_id="A-PASS",
        rubric_id="R-PASS",
        criterion_results=[
            CriterionResult(
                criterion_id="C1",
                status=CriterionStatus.PARTIALLY_SATISFIED,
                score=1.0,
                observed_finding="Only partial",
            ),
        ],
        total_score=1.0,
        passed=True,
    )
    errors = validate_evaluation_against_rubric(evaluation, rubric)
    assert any("PARTIALLY_SATISFIED" in e for e in errors)

    task = PracticeTask(
        task_id="TASK-PASS",
        package_id="PKG-PASS",
        rubric_id="R-PASS",
        title="Task",
        instructions="Practice",
        target_criteria_ids=["C1"],
    )
    ev = EvidenceRef(evidence_id="EV-PASS", source_id="a.mp4", modality=Modality.VIDEO)
    baseline = LearnerAttempt(
        attempt_id="A-BASE",
        task_id="TASK-PASS",
        learner=ParticipantRef(participant_id="L1", name="Learner"),
        attempt_type=AttemptType.BASELINE,
        attempt_number=1,
        evidence=ev,
    )
    retry = LearnerAttempt(
        attempt_id="A-RETRY",
        task_id="TASK-PASS",
        learner=ParticipantRef(participant_id="L1", name="Learner"),
        attempt_type=AttemptType.RETRY,
        attempt_number=2,
        evidence=ev,
    )
    base_eval = Evaluation(
        evaluation_id="EB",
        attempt_id="A-BASE",
        rubric_id="R-PASS",
        criterion_results=[
            CriterionResult(
                criterion_id="C1",
                status=CriterionStatus.NOT_SATISFIED,
                score=0.0,
                observed_finding="Baseline",
            )
        ],
        total_score=0.0,
    )
    retry_eval = Evaluation(
        evaluation_id="ER",
        attempt_id="A-RETRY",
        rubric_id="R-PASS",
        criterion_results=[
            CriterionResult(
                criterion_id="C1",
                status=CriterionStatus.SATISFIED,
                score=1.0,
                observed_finding="Retry",
            )
        ],
        total_score=1.0,
    )
    record = TransmissionRecord(
        transmission_id="TX-PASS",
        skill_id="SKILL-PASS",
        package_id="PKG-PASS",
        rubric_id="R-PASS",
        expert_id="EXP-1",
        learner_id="L1",
        baseline_attempt_id="A-BASE",
        retry_attempt_id="A-RETRY",
        baseline_score=0.0,
        retry_score=1.0,
        transmission_gain=1.0,
        criteria_improved=["UNKNOWN-CRITERION"],
        lineage=LineageMetadata(recorded_at="2026-10-04T12:00:00Z"),
    )
    errors = validate_transmission_record_invariants(
        record, task, rubric, baseline, retry, base_eval, retry_eval
    )
    assert any("does not exist in RubricDefinition" in e for e in errors)
