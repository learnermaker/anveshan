import sys
from pathlib import Path
import pytest

# Ensure track-b root is in sys.path for importing src modules
track_b_dir = Path(__file__).parent.parent
if str(track_b_dir) not in sys.path:
    sys.path.insert(0, str(track_b_dir))

from tracks.common.schemas import (
    KnowledgePackage,
    RubricDefinition,
    RubricCriterion,
    PracticeTask,
    TaskConstraint,
    LearnerAttempt,
    AttemptType,
    ParticipantRef,
    EvidenceRef,
    Modality,
    CriterionResult,
    CriterionStatus,
    EvaluatorType,
)
from tracks.common.validator import load_bundle_from_directory, validate_transmission_bundle
from src.evaluator import evaluate_attempt
from src.feedback import generate_coaching_feedback
from src.transmission import compute_transmission_record
from src.pipeline import TransmissionPipeline


@pytest.fixture
def sample_rubric():
    return RubricDefinition(
        rubric_id="rubric-test-01",
        skill_id="test-skill",
        title="Test Skill Rubric",
        passing_score=70.0,
        criteria=[
            RubricCriterion(
                criterion_id="C01",
                name="Setup",
                description="Setup check",
                observable_indicator="Proper setup",
                weight=30.0,
                required=True,
            ),
            RubricCriterion(
                criterion_id="C02",
                name="Execution",
                description="Execution check",
                observable_indicator="Proper execution",
                weight=50.0,
                required=True,
            ),
            RubricCriterion(
                criterion_id="C03",
                name="Style",
                description="Style check",
                observable_indicator="Good style",
                weight=20.0,
                required=False,
            ),
        ],
    )


@pytest.fixture
def sample_task():
    return PracticeTask(
        task_id="task-test-01",
        package_id="pkg-test-01",
        rubric_id="rubric-test-01",
        title="Test Practice Assignment",
        instructions="Perform test task",
    )


@pytest.fixture
def sample_learner():
    return ParticipantRef(participant_id="learner-test-42", name="Test Student")


@pytest.fixture
def baseline_attempt(sample_learner):
    return LearnerAttempt(
        attempt_id="att-base-01",
        task_id="task-test-01",
        learner=sample_learner,
        attempt_type=AttemptType.BASELINE,
        attempt_number=1,
        evidence=EvidenceRef(
            evidence_id="ev-base-01",
            source_id="base.mp4",
            modality=Modality.VIDEO,
            start_sec=0.0,
            end_sec=20.0,
        ),
    )


@pytest.fixture
def retry_attempt(sample_learner):
    return LearnerAttempt(
        attempt_id="att-retry-02",
        task_id="task-test-01",
        learner=sample_learner,
        attempt_type=AttemptType.RETRY,
        attempt_number=2,
        evidence=EvidenceRef(
            evidence_id="ev-retry-02",
            source_id="retry.mp4",
            modality=Modality.VIDEO,
            start_sec=0.0,
            end_sec=18.0,
        ),
    )


# ---------------------------------------------------------------------------
# Evaluator Tests
# ---------------------------------------------------------------------------

def test_evaluate_attempt_valid(baseline_attempt, sample_rubric):
    results = [
        CriterionResult(
            criterion_id="C01",
            status=CriterionStatus.SATISFIED,
            score=30.0,
            observed_finding="Good setup",
        ),
        CriterionResult(
            criterion_id="C02",
            status=CriterionStatus.NOT_SATISFIED,
            score=10.0,
            observed_finding="Execution error",
        ),
        CriterionResult(
            criterion_id="C03",
            status=CriterionStatus.PARTIALLY_SATISFIED,
            score=10.0,
            observed_finding="Fair style",
        ),
    ]

    evaluation = evaluate_attempt(baseline_attempt, sample_rubric, results)

    assert evaluation.total_score == 50.0
    # Required criterion C02 is NOT_SATISFIED, so passed must be False
    assert not evaluation.passed
    assert evaluation.attempt_id == baseline_attempt.attempt_id
    assert evaluation.rubric_id == sample_rubric.rubric_id


def test_evaluate_attempt_score_exceeds_weight_raises(baseline_attempt, sample_rubric):
    results = [
        CriterionResult(
            criterion_id="C01",
            status=CriterionStatus.SATISFIED,
            score=35.0,  # Max is 30.0!
            observed_finding="Too high score",
        ),
        CriterionResult(
            criterion_id="C02",
            status=CriterionStatus.SATISFIED,
            score=50.0,
            observed_finding="Execution",
        ),
    ]
    with pytest.raises(ValueError, match="exceeds rubric maximum allowed weight"):
        evaluate_attempt(baseline_attempt, sample_rubric, results)


def test_evaluate_attempt_missing_required_criterion_raises(baseline_attempt, sample_rubric):
    results = [
        CriterionResult(
            criterion_id="C01",
            status=CriterionStatus.SATISFIED,
            score=30.0,
            observed_finding="Setup done",
        )
        # C02 is required but missing!
    ]
    with pytest.raises(ValueError, match="Required rubric criterion 'C02'"):
        evaluate_attempt(baseline_attempt, sample_rubric, results)


def test_evaluate_attempt_uncertainty_flags(baseline_attempt, sample_rubric):
    results = [
        CriterionResult(
            criterion_id="C01",
            status=CriterionStatus.SATISFIED,
            score=30.0,
            observed_finding="Setup",
        ),
        CriterionResult(
            criterion_id="C02",
            status=CriterionStatus.UNCERTAIN,
            score=25.0,
            observed_finding="Obscured by camera angle",
        ),
        CriterionResult(
            criterion_id="C03",
            status=CriterionStatus.SATISFIED,
            score=20.0,
            observed_finding="Style okay",
        ),
    ]
    evaluation = evaluate_attempt(baseline_attempt, sample_rubric, results)
    assert "C02" in evaluation.uncertainty_flags


# ---------------------------------------------------------------------------
# Feedback Tests
# ---------------------------------------------------------------------------

def test_generate_coaching_feedback(baseline_attempt, sample_rubric):
    results = [
        CriterionResult(
            criterion_id="C01",
            status=CriterionStatus.SATISFIED,
            score=30.0,
            observed_finding="Good setup",
        ),
        CriterionResult(
            criterion_id="C02",
            status=CriterionStatus.NOT_SATISFIED,
            score=10.0,
            observed_finding="Chalk crossed boundary",
            deviation_analysis="Should stay within boundary",
        ),
        CriterionResult(
            criterion_id="C03",
            status=CriterionStatus.PARTIALLY_SATISFIED,
            score=10.0,
            observed_finding="Slightly uneven",
        ),
    ]
    evaluation = evaluate_attempt(baseline_attempt, sample_rubric, results)
    feedback = generate_coaching_feedback(evaluation, sample_rubric)

    assert feedback.evaluation_id == evaluation.evaluation_id
    assert "C02" in feedback.recommended_retry_focus
    assert "C03" in feedback.recommended_retry_focus
    assert len(feedback.items) == 2
    assert "Review the targeted coaching items" in feedback.summary


# ---------------------------------------------------------------------------
# Transmission Engine & Pipeline Tests
# ---------------------------------------------------------------------------

def test_compute_transmission_record(
    sample_task, sample_rubric, baseline_attempt, retry_attempt
):
    b_results = [
        CriterionResult(criterion_id="C01", status=CriterionStatus.SATISFIED, score=30.0, observed_finding="Setup ok"),
        CriterionResult(criterion_id="C02", status=CriterionStatus.NOT_SATISFIED, score=10.0, observed_finding="Error"),
        CriterionResult(criterion_id="C03", status=CriterionStatus.PARTIALLY_SATISFIED, score=5.0, observed_finding="Fair"),
    ]
    r_results = [
        CriterionResult(criterion_id="C01", status=CriterionStatus.SATISFIED, score=30.0, observed_finding="Setup ok"),
        CriterionResult(criterion_id="C02", status=CriterionStatus.SATISFIED, score=45.0, observed_finding="Fixed"),
        CriterionResult(criterion_id="C03", status=CriterionStatus.SATISFIED, score=20.0, observed_finding="Clean"),
    ]

    b_eval = evaluate_attempt(baseline_attempt, sample_rubric, b_results)
    r_eval = evaluate_attempt(retry_attempt, sample_rubric, r_results)

    record = compute_transmission_record(
        task=sample_task,
        rubric=sample_rubric,
        baseline_attempt=baseline_attempt,
        retry_attempt=retry_attempt,
        baseline_eval=b_eval,
        retry_eval=r_eval,
    )

    assert b_eval.total_score == 45.0
    assert r_eval.total_score == 95.0
    # Gain: 95.0 - 45.0 = 50.0
    assert record.transmission_gain == 50.0
    assert "C02" in record.criteria_improved
    assert "C03" in record.criteria_improved
    assert "C01" not in record.criteria_improved  # 30.0 -> 30.0 was not an increase
    assert record.lineage.provenance_hash.startswith("sha256-")


def test_transmission_pipeline_case_001_replay():
    """Verify that TransmissionPipeline successfully executes against case-001 fixture."""
    fixture_dir = Path(__file__).parent.parent / "fixtures" / "replay" / "case-001"
    bundle_data = load_bundle_from_directory(fixture_dir)

    pkg = KnowledgePackage.model_validate(bundle_data["knowledge_package"])
    rubric = RubricDefinition.model_validate(bundle_data["rubric"])
    task = PracticeTask.model_validate(bundle_data["practice_task"])
    b_att = LearnerAttempt.model_validate(bundle_data["baseline_attempt"])
    r_att = LearnerAttempt.model_validate(bundle_data["retry_attempt"])

    b_obs = [
        CriterionResult.model_validate(cr)
        for cr in bundle_data["baseline_evaluation"]["criterion_results"]
    ]
    r_obs = [
        CriterionResult.model_validate(cr)
        for cr in bundle_data["retry_evaluation"]["criterion_results"]
    ]

    pipeline = TransmissionPipeline(rubric=rubric, task=task, knowledge_package=pkg)
    full_bundle = pipeline.run_full_cycle(
        baseline_attempt=b_att,
        baseline_observations=b_obs,
        retry_attempt=r_att,
        retry_observations=r_obs,
        expert_id="expert-meenakshi",
    )

    assert full_bundle["transmission_record"]["transmission_gain"] == 50.0
    assert full_bundle["transmission_record"]["criteria_improved"] == ["C02", "C03"]

    # Validate output through universal validator
    valid, errors = validate_transmission_bundle(full_bundle)
    assert valid, f"Bundle validation failed: {errors}"
