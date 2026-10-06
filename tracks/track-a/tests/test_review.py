"""Expert review versioning."""

import pytest

from tracks.common.casedata import CriterionMap
from tracks.common.models import AnveshanFailure, FailureCategory

from track_a import api


@pytest.fixture
def built(cases_root, fake_builder, make_ctx):
    case_dir = cases_root / "kolam"
    api.build_case(case_dir, make_ctx(case_dir))
    return case_dir


def _pkg_file(case_dir, v):
    return case_dir / "knowledge" / f"knowledge_package.v{v}.json"


def test_approve_writes_new_version_and_keeps_old(built):
    before = _pkg_file(built, 1).read_bytes()
    h = api.apply_review(built, {"action": "approve", "reviewer": "Jim", "note": "looks right", "reviewed_at": "2026-10-06T00:00:00Z"})
    assert _pkg_file(built, 1).read_bytes() == before
    assert h.package.package_id == "kp.kolam.2" and h.review_status == "approved"
    assert h.package.expert_review.reviewer_name == "Jim"
    assert h.package.expert_review.reviewed_at == "2026-10-06T00:00:00Z"
    assert "looks right" in h.package.expert_review.notes and "kp.kolam.1" in h.package.expert_review.notes
    assert h.task.package_id == "kp.kolam.2" and h.criterion_map.package_id == "kp.kolam.2"
    assert h.rubric.rubric_id == "rubric.kolam.1" and h.goal.version == 1
    assert api.NOT_APPROVED_WARNING not in h.warnings
    assert api.load_case(built).package.package_id == "kp.kolam.2"


def test_revise_claim_preserves_old_statement(built):
    old = api.load_case(built).package.claims[0].statement
    h = api.apply_review(built, {"action": "revise_claim", "reviewer": "Jim", "claim_id": "CLM-01", "new_statement": "13 dots.", "note": "tighter"})
    assert h.review_status == "revised"
    assert h.package.claims[0].statement == "13 dots."
    assert old in h.package.expert_review.notes and "CLM-01 revised" in h.package.expert_review.notes
    assert h.package.claims[0].evidence_refs == api.load_case(built).package.claims[0].evidence_refs


def test_reject_claim_removes_and_flags_criteria(built):
    v1_map = (built / "knowledge" / "criterion_map.v1.json").read_bytes()
    h = api.apply_review(built, {"action": "reject_claim", "reviewer": "Jim", "claim_id": "CLM-02", "note": "not visible"})
    assert "CLM-02" not in [c.claim_id for c in h.package.claims]
    assert h.review_status == "revised"
    assert h.criterion_map.criteria["CRIT-KOLAM-DOTS"].why_it_matters.startswith("[FLAGGED: CLM-02")
    assert not h.criterion_map.criteria["CRIT-KOLAM-COVERAGE"].why_it_matters.startswith("[FLAGGED")
    assert any("CRIT-KOLAM-DOTS" in w for w in h.warnings)
    assert "CRIT-KOLAM-DOTS" in h.package.expert_review.notes
    assert (built / "knowledge" / "criterion_map.v1.json").read_bytes() == v1_map
    CriterionMap.model_validate_json((built / "knowledge" / "criterion_map.v2.json").read_text(encoding="utf-8"))


def test_reject_package_then_load_and_further_review(built):
    h = api.apply_review(built, {"action": "reject_package", "reviewer": "Jim", "note": "wrong pattern"})
    assert h.review_status == "rejected"
    loaded = api.load_case(built)
    assert loaded.review_status == "rejected" and any("rejected" in w for w in loaded.warnings)
    with pytest.raises(AnveshanFailure) as e:
        api.apply_review(built, {"action": "approve", "reviewer": "Jim"})
    assert e.value.category == FailureCategory.INVALID_INPUT


def test_load_prefers_approved_over_newer_pending(built, make_ctx):
    api.apply_review(built, {"action": "approve", "reviewer": "Jim"})  # v2 approved
    api.build_case(built, make_ctx(built))  # v3 pending
    h = api.load_case(built)
    assert h.package.package_id == "kp.kolam.2" and h.review_status == "approved"
    assert h.rubric.rubric_id == "rubric.kolam.1" and h.goal.version == 1


def test_latest_pending_gets_warning(built):
    h = api.load_case(built)
    assert h.review_status == "pending" and api.NOT_APPROVED_WARNING in h.warnings


@pytest.mark.parametrize(
    "action",
    [
        {"action": "bless", "reviewer": "Jim"},
        {"action": "approve"},
        {"action": "revise_claim", "reviewer": "Jim", "claim_id": "CLM-99", "new_statement": "x"},
        {"action": "revise_claim", "reviewer": "Jim", "claim_id": "CLM-01", "new_statement": "  "},
    ],
)
def test_invalid_review_actions(built, action):
    with pytest.raises(AnveshanFailure) as e:
        api.apply_review(built, action)
    assert e.value.category == FailureCategory.INVALID_INPUT


def test_showcase_not_reviewable(cases_root):
    with pytest.raises(AnveshanFailure) as e:
        api.apply_review(cases_root / "micrometer", {"action": "approve", "reviewer": "Jim"})
    assert e.value.category == FailureCategory.INVALID_INPUT
