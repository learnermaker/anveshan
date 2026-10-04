import pytest
from pydantic import ValidationError
from tracks.common.schemas import (
    ClaimType,
    ConsentMetadata,
    CriterionResult,
    CriterionStatus,
    Evaluation,
    EvidenceRef,
    KnowledgeClaim,
    KnowledgePackage,
    Modality,
    PracticeTask,
    RubricCriterion,
    RubricDefinition,
    VerificationState,
)
from tracks.common.validator import (
    validate_evaluation_against_rubric,
    validate_practice_task_against_knowledge_and_rubric,
)
from case_registry import CaseManifest, validate_manifest_semantics
from grounding import GroundingService
from models import FailureCategory, TrackAFailure


def test_inverted_intervals_fail() -> None:
    service = GroundingService()
    # Pydantic validates intervals on creation
    with pytest.raises(ValidationError, match="end_sec"):
        EvidenceRef(
            evidence_id="ev_01",
            source_id="src_01",
            modality=Modality.VIDEO,
            start_sec=10.0,
            end_sec=5.0,  # inverted
        )

    # Also test GroundingService.validate_intervals directly with mock
    class MockEv:
        evidence_id = "ev_mock"
        start_sec = 10.0
        end_sec = 5.0
    with pytest.raises(TrackAFailure) as exc:
        service.validate_intervals([MockEv()])  # type: ignore
    assert exc.value.category == FailureCategory.CONTRACT_VIOLATION


def test_negative_timestamp_fail() -> None:
    service = GroundingService()
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        EvidenceRef(
            evidence_id="ev_neg",
            source_id="src_01",
            modality=Modality.VIDEO,
            start_sec=-1.0,
            end_sec=5.0,
        )

    class MockEvNeg:
        evidence_id = "ev_mock_neg"
        start_sec = -2.0
        end_sec = 5.0
    with pytest.raises(TrackAFailure) as exc:
        service.validate_intervals([MockEvNeg()])  # type: ignore
    assert exc.value.category == FailureCategory.CONTRACT_VIOLATION


def test_ungrounded_claims_fail() -> None:
    service = GroundingService()
    with pytest.raises(ValidationError, match="at least 1 item"):
        KnowledgeClaim(
            claim_id="CLM-01",
            claim_type=ClaimType.STEP,
            statement="Unsupported step without evidence",
            is_observed=True,
            evidence_refs=[],  # empty
        )

    # Test GroundingService directly with mock
    class MockClaim:
        claim_id = "CLM-MOCK"
        statement = "Mock without ev"
        evidence_refs = []
    with pytest.raises(TrackAFailure) as exc:
        service.verify_claim_support(MockClaim())  # type: ignore
    assert exc.value.category == FailureCategory.UNSUPPORTED_CLAIM


def test_duplicate_claim_ids_fail() -> None:
    ev = EvidenceRef(
        evidence_id="ev_01",
        source_id="src_01",
        modality=Modality.VIDEO,
        start_sec=1.0,
        end_sec=2.0,
    )
    claim1 = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.STEP,
        statement="First claim",
        evidence_refs=[ev],
    )
    claim2 = KnowledgeClaim(
        claim_id="CLM-01",  # duplicate ID
        claim_type=ClaimType.CUE,
        statement="Second claim",
        evidence_refs=[ev],
    )
    with pytest.raises(ValueError, match="Duplicate claim_ids"):
        KnowledgePackage(
            package_id="pkg_dup",
            skill_id="skill_dup",
            title="Dup",
            summary="Dup",
            claims=[claim1, claim2],
            consent=ConsentMetadata(contributor_name="Test", consent_scope="Test"),
        )


def test_inferred_claim_masquerading_as_observation_fail() -> None:
    service = GroundingService()
    ev = EvidenceRef(
        evidence_id="ev_01",
        source_id="src_01",
        modality=Modality.VIDEO,
        start_sec=0.0,
        end_sec=1.0,
        verification_state=VerificationState.OBSERVED,
    )
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.STEP,
        statement="Inferred procedure masquerading",
        is_observed=False,  # unobserved
        evidence_refs=[ev],
    )
    with pytest.raises(TrackAFailure) as exc:
        service.enforce_epistemological_state(claim, "forward")
    assert exc.value.category == FailureCategory.CONTRACT_VIOLATION


def test_practice_task_missing_rubric_criterion_fail() -> None:
    ev = EvidenceRef(evidence_id="ev_01", source_id="src_01", modality=Modality.VIDEO, start_sec=1.0, end_sec=2.0)
    pkg = KnowledgePackage(
        package_id="pkg_01",
        skill_id="skill_01",
        title="Title",
        summary="Summary",
        claims=[KnowledgeClaim(claim_id="CLM-01", claim_type=ClaimType.STEP, statement="Stmt", evidence_refs=[ev])],
        consent=ConsentMetadata(contributor_name="Test", consent_scope="Test"),
    )
    rubric = RubricDefinition(
        rubric_id="rubric_01",
        skill_id="skill_01",
        title="Rubric",
        criteria=[
            RubricCriterion(
                criterion_id="CRIT-01",
                name="Crit 1",
                description="Desc",
                observable_indicator="Obs",
                weight=2.0,
            )
        ],
    )
    task = PracticeTask(
        task_id="task_01",
        package_id="pkg_01",
        rubric_id="rubric_01",
        title="Task",
        instructions="Do it",
        target_criteria_ids=["CRIT-01", "CRIT-MISSING"],  # CRIT-MISSING not in rubric!
    )
    errs = validate_practice_task_against_knowledge_and_rubric(task, pkg, rubric)
    assert any("CRIT-MISSING" in e for e in errs)


def test_required_criteria_satisfaction_gate_fail() -> None:
    """CRIT-07: evaluation.passed cannot be True if required criterion is not SATISFIED."""
    rubric = RubricDefinition(
        rubric_id="rubric_gate",
        skill_id="skill_gate",
        title="Gate Rubric",
        criteria=[
            RubricCriterion(
                criterion_id="CRIT-REQ",
                name="Required criterion",
                description="Mandatory step",
                observable_indicator="Obs",
                weight=5.0,
                required=True,
            )
        ],
        passing_score=3.0,
    )
    eval_invalid = Evaluation(
        evaluation_id="eval_01",
        attempt_id="att_01",
        rubric_id="rubric_gate",
        criterion_results=[
            CriterionResult(
                criterion_id="CRIT-REQ",
                status=CriterionStatus.PARTIALLY_SATISFIED,
                score=3.5,
                observed_finding="Technique incomplete",
            )
        ],
        total_score=3.5,
        passed=True,  # VIOLATION: passed cannot be True!
    )
    errs = validate_evaluation_against_rubric(eval_invalid, rubric)
    assert any("required criterion 'CRIT-REQ' is PARTIALLY_SATISFIED" in e for e in errs)


def test_criterion_score_exceeding_weight_fail() -> None:
    rubric = RubricDefinition(
        rubric_id="rubric_wt",
        skill_id="skill_wt",
        title="Weight Rubric",
        criteria=[
            RubricCriterion(
                criterion_id="CRIT-01",
                name="Crit",
                description="Desc",
                observable_indicator="Obs",
                weight=3.0,
            )
        ],
    )
    eval_over = Evaluation(
        evaluation_id="eval_01",
        attempt_id="att_01",
        rubric_id="rubric_wt",
        criterion_results=[
            CriterionResult(
                criterion_id="CRIT-01",
                status=CriterionStatus.SATISFIED,
                score=5.0,  # exceeds weight 3.0!
                observed_finding="Over",
            )
        ],
        total_score=5.0,
        passed=True,
    )
    errs = validate_evaluation_against_rubric(eval_over, rubric)
    assert any("exceeds rubric max points" in e for e in errs)


def test_goal_conditioned_observed_procedure_fail() -> None:
    service = GroundingService()
    ev = EvidenceRef(
        evidence_id="ev_01",
        source_id="src_01",
        modality=Modality.IMAGE,
        verification_state=VerificationState.OBSERVED,
    )
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.CONDITION,
        statement="Inferred procedural step",
        is_observed=False,
        evidence_refs=[ev],
    )
    with pytest.raises(TrackAFailure) as exc:
        service.enforce_epistemological_state(claim, "goal-conditioned")
    assert exc.value.category == FailureCategory.CONTRACT_VIOLATION


def test_manifest_semantic_violations() -> None:
    m3 = CaseManifest(
        schema_version="1.0",
        case_id="c3",
        bundle_case_id="b3",
        title="T",
        domain="D",
        archetype="A",
        workspace_type="W",
        transmission_mode="forward",
        source_posture="authentic_expert",
        epistemic_status="E",
        data_status="S",
        pack_version="1.0",
        case_version="1.0",
        status="ENGINEERING_FIXTURE",
        source_mode="FORWARD",
        runtime_class="AUTHENTIC",
    )
    fails = validate_manifest_semantics(m3)
    assert any("semantic rule 3" in f for f in fails)
