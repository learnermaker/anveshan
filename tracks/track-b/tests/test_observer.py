"""Tests for the Multimodal Gemini Observer in Track B."""

import sys
from pathlib import Path
import pytest

track_b_dir = Path(__file__).parent.parent
if str(track_b_dir) not in sys.path:
    sys.path.insert(0, str(track_b_dir))

from tracks.common.schemas import (
    RubricDefinition,
    RubricCriterion,
    PracticeTask,
    LearnerAttempt,
    AttemptType,
    ParticipantRef,
    EvidenceRef,
    Modality,
    CriterionStatus,
)
from src.observer import GeminiObserver
from src.evaluator import evaluate_attempt
from src.pipeline import TransmissionPipeline


@pytest.fixture
def sample_rubric():
    return RubricDefinition(
        rubric_id="rubric-obs-01",
        skill_id="test-obs-skill",
        title="Observer Test Rubric",
        passing_score=75.0,
        criteria=[
            RubricCriterion(
                criterion_id="C01",
                name="Grid Layout",
                description="Equidistant 3x3 layout",
                observable_indicator="Grid layout visible",
                weight=20.0,
                required=True,
            ),
            RubricCriterion(
                criterion_id="C02",
                name="Outer Loop",
                description="Outer loop clearance",
                observable_indicator="Clear envelope",
                weight=40.0,
                required=True,
            ),
            RubricCriterion(
                criterion_id="C03",
                name="Symmetry",
                description="Bilateral quadrant reflection",
                observable_indicator="Quadrant symmetry",
                weight=40.0,
                required=False,
            ),
        ],
    )


@pytest.fixture
def baseline_attempt():
    return LearnerAttempt(
        attempt_id="att-obs-base-01",
        task_id="task-obs-01",
        learner=ParticipantRef(participant_id="learner-obs-01", name="Learner 1"),
        attempt_type=AttemptType.BASELINE,
        attempt_number=1,
        evidence=EvidenceRef(
            evidence_id="ev-obs-base",
            source_id="learner_video.mp4",
            modality=Modality.VIDEO,
            start_sec=0.0,
            end_sec=30.0,
        ),
    )


@pytest.fixture
def retry_attempt():
    return LearnerAttempt(
        attempt_id="att-obs-retry-02",
        task_id="task-obs-01",
        learner=ParticipantRef(participant_id="learner-obs-01", name="Learner 1"),
        attempt_type=AttemptType.RETRY,
        attempt_number=2,
        evidence=EvidenceRef(
            evidence_id="ev-obs-retry",
            source_id="learner_video_retry.mp4",
            modality=Modality.VIDEO,
            start_sec=0.0,
            end_sec=25.0,
        ),
    )


def test_observer_initialization():
    """Verify observer initializes safely without crash even when api_key is empty."""
    observer = GeminiObserver(api_key="", fallback_mode=True)
    assert not observer.is_live()


def test_observer_observe_baseline(sample_rubric, baseline_attempt):
    """Verify observer produces valid CriterionResults for baseline attempt."""
    observer = GeminiObserver(api_key="", fallback_mode=True)
    results = observer.observe(baseline_attempt, sample_rubric)

    assert len(results) == len(sample_rubric.criteria)
    result_map = {r.criterion_id: r for r in results}

    assert "C01" in result_map
    assert "C02" in result_map
    assert "C03" in result_map

    # Baseline flaw on C02 should be observed
    assert result_map["C02"].status == CriterionStatus.NOT_SATISFIED
    assert result_map["C02"].score <= sample_rubric.criteria[1].weight
    assert result_map["C02"].evidence_ref is not None


def test_observer_feeds_into_evaluator(sample_rubric, baseline_attempt, retry_attempt):
    """Verify observer output plugs directly into evaluate_attempt and transmission pipeline."""
    observer = GeminiObserver(api_key="", fallback_mode=True)

    base_obs = observer.observe(baseline_attempt, sample_rubric)
    base_eval = evaluate_attempt(baseline_attempt, sample_rubric, base_obs)

    assert not base_eval.passed  # C02 is NOT_SATISFIED on baseline
    assert base_eval.total_score < sample_rubric.passing_score

    retry_obs = observer.observe(retry_attempt, sample_rubric)
    retry_eval = evaluate_attempt(retry_attempt, sample_rubric, retry_obs)

    assert retry_eval.passed  # Retry satisfies required criteria
    assert retry_eval.total_score > base_eval.total_score


def test_observer_live_client_detection():
    """Verify observer detects API key from environment when present."""
    observer = GeminiObserver(fallback_mode=True)
    # If .env has the user's API key, is_live will be True
    if observer.api_key:
        assert observer.is_live()
        assert observer.model_name == "gemini-flash-lite-latest"
