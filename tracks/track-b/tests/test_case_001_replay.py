"""Test suite for Track B Replay Case 001."""

from pathlib import Path
import pytest
from tracks.common.validator import (
    load_bundle_from_directory,
    validate_transmission_bundle,
    validate_fixture_file,
)
from tracks.common.schemas import (
    TransmissionRecord,
    Evaluation,
    LearnerAttempt,
    AttemptType,
    RubricDefinition,
)

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "replay" / "case-001"


def test_case_001_fixture_bundle_validity():
    """Verify that case-001 passes the universal 8-contract bundle validator."""
    assert FIXTURE_DIR.exists(), f"Fixture directory not found at {FIXTURE_DIR}"
    valid, message, bundle = validate_fixture_file(FIXTURE_DIR, is_bundle=True)
    assert valid, f"Validation failed: {message}"
    assert bundle is not None


def test_case_001_transmission_gain_arithmetic():
    """Verify that baseline and retry attempts produce deterministic transmission gain."""
    bundle = load_bundle_from_directory(FIXTURE_DIR)
    
    baseline_eval = Evaluation.model_validate(bundle["baseline_evaluation"])
    retry_eval = Evaluation.model_validate(bundle["retry_evaluation"])
    record = TransmissionRecord.model_validate(bundle["transmission_record"])
    
    assert baseline_eval.total_score == 45.0
    assert retry_eval.total_score == 95.0
    assert not baseline_eval.passed
    assert retry_eval.passed
    
    # Authoritative gain check
    expected_gain = round(retry_eval.total_score - baseline_eval.total_score, 4)
    assert record.transmission_gain == expected_gain == 50.0
    
    # Criteria improvement checks
    assert "C02" in record.criteria_improved
    assert "C03" in record.criteria_improved


def test_case_001_attempt_invariants():
    """Verify that baseline is attempt 1 and retry is attempt 2 with same learner."""
    bundle = load_bundle_from_directory(FIXTURE_DIR)
    
    b_att = LearnerAttempt.model_validate(bundle["baseline_attempt"])
    r_att = LearnerAttempt.model_validate(bundle["retry_attempt"])
    
    assert b_att.attempt_type == AttemptType.BASELINE
    assert b_att.attempt_number == 1
    assert r_att.attempt_type == AttemptType.RETRY
    assert r_att.attempt_number == 2
    assert b_att.learner.participant_id == r_att.learner.participant_id == "learner-akash"
    assert b_att.evidence.modality.value == "video"
    assert r_att.evidence.modality.value == "video"
