import pytest
from tracks.common.schemas import (
    ClaimType,
    ConsentMetadata,
    EvidenceRef,
    KnowledgeClaim,
    KnowledgePackage,
    Modality,
)
from models import FailureCategory, TrackAFailure
from query_service import EvidenceQueryService


@pytest.fixture
def sample_package() -> KnowledgePackage:
    ev = EvidenceRef(
        evidence_id="ev_01",
        source_id="video.mp4",
        modality=Modality.VIDEO,
        start_sec=18.0,
        end_sec=22.5,
        cue_excerpt="Ratchet thimble turned until 3 uniform clicks heard",
    )
    claim = KnowledgeClaim(
        claim_id="CLM-02",
        claim_type=ClaimType.CUE,
        statement="Apply 5N contact pressure via ratchet thimble",
        is_observed=True,
        evidence_refs=[ev],
    )
    return KnowledgePackage(
        package_id="kp.micrometer.1",
        skill_id="SKILL-OPT-CALIB",
        title="Micrometer Calibration",
        summary="Zeroing micrometer",
        claims=[claim],
        consent=ConsentMetadata(
            contributor_name="Marcus Vance",
            consent_scope="engineering_replay_only",
        ),
    )


def test_answer_supported_query(sample_package: KnowledgePackage) -> None:
    service = EvidenceQueryService()
    res = service.answer_query(sample_package, "How many clicks on the ratchet thimble?")
    assert "CLM-02" in res.answer
    assert len(res.evidence_refs) == 1
    assert res.evidence_refs[0].evidence_id == "ev_01"
    assert res.evidence_refs[0].start_sec == 18.0


def test_refuse_unsupported_query(sample_package: KnowledgePackage) -> None:
    service = EvidenceQueryService()
    with pytest.raises(TrackAFailure) as exc:
        service.answer_query(sample_package, "What temperature should the laser interferometer be?")
    assert exc.value.category == FailureCategory.MISSING_EVIDENCE
    assert "INSUFFICIENT_EVIDENCE" in str(exc.value)


def test_empty_query_raises_invalid_input(sample_package: KnowledgePackage) -> None:
    service = EvidenceQueryService()
    with pytest.raises(TrackAFailure) as exc:
        service.answer_query(sample_package, "???")
    assert exc.value.category == FailureCategory.INVALID_INPUT
