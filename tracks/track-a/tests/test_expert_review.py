from pathlib import Path
import pytest
from tracks.common.schemas import (
    ClaimType,
    ConsentMetadata,
    EvidenceRef,
    KnowledgeClaim,
    KnowledgePackage,
    Modality,
    ReviewStatus,
)
from case_registry import load_manifest
from expert_review import ExpertReviewService
from models import FailureCategory, TrackAFailure


@pytest.fixture
def sample_package() -> KnowledgePackage:
    ev = EvidenceRef(
        evidence_id="ev_01",
        source_id="video.mp4",
        modality=Modality.VIDEO,
        start_sec=4.5,
        end_sec=12.0,
    )
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.STEP,
        statement="Clean micrometer faces with lint-free paper",
        is_observed=True,
        evidence_refs=[ev],
    )
    consent = ConsentMetadata(
        contributor_name="Marcus Vance",
        consent_scope="engineering_replay_only",
    )
    return KnowledgePackage(
        package_id="kp.micrometer.1",
        skill_id="SKILL-OPT-CALIB",
        title="Micrometer Zeroing",
        summary="Calibration procedure",
        claims=[claim],
        consent=consent,
    )


def test_review_lifecycle(sample_package: KnowledgePackage) -> None:
    service = ExpertReviewService()

    # 1. Submit for review -> PENDING
    pkg = service.submit_for_review(sample_package, "Master Metrologist")
    assert pkg.expert_review is not None
    assert pkg.expert_review.status == ReviewStatus.PENDING

    # 2. Revise claim -> REVISED
    pkg = service.revise_claim(
        pkg,
        "CLM-01",
        "Unidirectional continuous wipe using optical paper",
        "Master Metrologist",
        notes="Specified unidirectional motion",
    )
    assert pkg.expert_review.status == ReviewStatus.REVISED
    assert "unidirectional" in pkg.claims[0].statement.lower()

    # 3. Approve -> APPROVED
    pkg = service.approve_package(pkg, "Master Metrologist", notes="Looks perfect")
    assert pkg.expert_review.status == ReviewStatus.APPROVED


def test_revise_nonexistent_claim_fails(sample_package: KnowledgePackage) -> None:
    service = ExpertReviewService()
    with pytest.raises(TrackAFailure) as exc:
        service.revise_claim(sample_package, "CLM-99", "new statement", "Expert")
    assert exc.value.category == FailureCategory.INVALID_INPUT


def test_export_markdown(sample_package: KnowledgePackage, cases_root: Path) -> None:
    service = ExpertReviewService()
    manifest = load_manifest(cases_root, "micrometer")
    md = service.export_markdown(sample_package, manifest)
    assert "# Expert Review Sheet" in md
    assert "Marcus Vance" in md
    assert "CLM-01" in md
    assert "[4.5s - 12.0s]" in md
    assert "Precision metrology" in md
