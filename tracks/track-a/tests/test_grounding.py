import pytest
from tracks.common.schemas import (
    ClaimType,
    ConsentMetadata,
    EvidenceRef,
    KnowledgeClaim,
    KnowledgePackage,
    Modality,
    VerificationState,
)
from grounding import GroundingService
from models import FailureCategory, TrackAFailure


@pytest.fixture
def grounding_service() -> GroundingService:
    return GroundingService()


def test_valid_intervals(grounding_service: GroundingService) -> None:
    ev = EvidenceRef(
        evidence_id="ev_01",
        source_id="src_01",
        modality=Modality.VIDEO,
        start_sec=10.0,
        end_sec=15.5,
    )
    # Should not raise
    grounding_service.validate_intervals([ev])


def test_negative_timestamp_raises(grounding_service: GroundingService) -> None:
    # We construct with bypass or dict to test validator if pydantic allows or test service
    with pytest.raises(Exception):
        # Pydantic ge=0.0 will catch this directly
        EvidenceRef(
            evidence_id="ev_neg",
            source_id="src_01",
            modality=Modality.VIDEO,
            start_sec=-1.0,
            end_sec=5.0,
        )


def test_inverted_interval_raises() -> None:
    with pytest.raises(Exception, match="end_sec"):
        EvidenceRef(
            evidence_id="ev_inv",
            source_id="src_01",
            modality=Modality.VIDEO,
            start_sec=10.0,
            end_sec=5.0,
        )


def test_epistemological_unobserved_claim_with_observed_evidence_fails(
    grounding_service: GroundingService,
) -> None:
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
        statement="Inferred procedure masquerading as observation",
        is_observed=False,
        evidence_refs=[ev],
    )
    with pytest.raises(TrackAFailure) as exc:
        grounding_service.enforce_epistemological_state(claim, "forward")
    assert exc.value.category == FailureCategory.CONTRACT_VIOLATION


def test_goal_conditioned_inferred_procedure_confidence_cap(
    grounding_service: GroundingService,
) -> None:
    ev = EvidenceRef(
        evidence_id="ev_01",
        source_id="src_01",
        modality=Modality.IMAGE,
        start_sec=0.0,
        end_sec=0.0,
        verification_state=VerificationState.INFERRED,
        confidence=0.9,  # exceeds 0.5 cap
    )
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.CONDITION,
        statement="Inferred procedural step",
        is_observed=False,
        evidence_refs=[ev],
    )
    with pytest.raises(TrackAFailure) as exc:
        grounding_service.enforce_epistemological_state(claim, "goal-conditioned")
    assert exc.value.category == FailureCategory.CONTRACT_VIOLATION
    assert "cannot have confidence > 0.5" in str(exc.value)


def test_validate_package_grounding_audit(grounding_service: GroundingService) -> None:
    ev_obs = EvidenceRef(
        evidence_id="ev_01",
        source_id="src_01",
        modality=Modality.VIDEO,
        start_sec=1.0,
        end_sec=2.0,
        verification_state=VerificationState.OBSERVED,
    )
    ev_inf = EvidenceRef(
        evidence_id="ev_02",
        source_id="src_01",
        modality=Modality.TEXT,
        verification_state=VerificationState.INFERRED,
        confidence=0.4,
    )
    pkg = KnowledgePackage(
        package_id="pkg_test",
        skill_id="skill_test",
        title="Test",
        summary="Test",
        claims=[
            KnowledgeClaim(
                claim_id="CLM-01",
                claim_type=ClaimType.STEP,
                statement="Observed step",
                is_observed=True,
                evidence_refs=[ev_obs],
            ),
            KnowledgeClaim(
                claim_id="CLM-02",
                claim_type=ClaimType.EXCEPTION,
                statement="Inferred exception",
                is_observed=False,
                evidence_refs=[ev_inf],
            ),
        ],
        consent=ConsentMetadata(contributor_name="Test", consent_scope="Test"),
    )
    uncertainty = grounding_service.validate_package_grounding(pkg, "forward")
    assert len(uncertainty) == 1
    assert "CLM-02" in uncertainty[0]
