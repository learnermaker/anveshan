"""
Tests for EvidenceGrounder v1 (offline, no LLM).

Covers: valid packages, grounding violations (empty evidence, inverted
intervals, negative timestamps, is_observed/verification_state mismatch),
goal-conditioned confidence rule, and uncertainty flag collection.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMMON = _REPO_ROOT / "tracks" / "common"
if str(_COMMON) not in sys.path:
    sys.path.insert(0, str(_COMMON))

from schemas.evidence import EvidenceRef, Modality, VerificationState
from schemas.knowledge import (
    ClaimType,
    ConsentMetadata,
    ExpertReview,
    KnowledgeClaim,
    KnowledgePackage,
    ReviewStatus,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obs_ev(eid: str = "ev-01") -> EvidenceRef:
    return EvidenceRef(
        evidence_id=eid,
        source_id="src-test",
        modality=Modality.IMAGE,
        verification_state=VerificationState.OBSERVED,
        confidence=1.0,
    )


def _inf_ev(eid: str = "ev-01", confidence: float = 0.5) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=eid,
        source_id="src-test",
        modality=Modality.IMAGE,
        verification_state=VerificationState.INFERRED,
        confidence=confidence,
    )


def _video_ev(eid: str, start: float, end: float, vs=VerificationState.OBSERVED) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=eid,
        source_id="src-video",
        modality=Modality.VIDEO,
        start_sec=start,
        end_sec=end,
        verification_state=vs,
        confidence=1.0,
    )


def _claim(
    cid: str = "CLM-01",
    is_observed: bool = True,
    ev: EvidenceRef | None = None,
) -> KnowledgeClaim:
    return KnowledgeClaim(
        claim_id=cid,
        claim_type=ClaimType.STEP,
        statement="Test fold step.",
        is_observed=is_observed,
        evidence_refs=[ev or _obs_ev()],
    )


def _package(claims: list[KnowledgeClaim]) -> KnowledgePackage:
    return KnowledgePackage(
        package_id="kp.test.1",
        skill_id="skill-test",
        title="Test Package",
        summary="Test summary.",
        claims=claims,
        consent=ConsentMetadata(
            contributor_name="Test",
            consent_scope="research_prototype",
        ),
        expert_review=ExpertReview(
            reviewer_name="Test Reviewer",
            status=ReviewStatus.PENDING,
        ),
    )


def _adapter_package(tmp_path: Path) -> KnowledgePackage:
    """Build a real KnowledgePackage from the adapter using fixture data."""
    from adapter import FoldingAgentAdapter

    run_dir = tmp_path / "run_test"
    logs_dir = run_dir / "logs"
    figs_dir = run_dir / "figs"
    logs_dir.mkdir(parents=True)
    figs_dir.mkdir(parents=True)

    shutil.copy(FIXTURES / "sample_checkpoint.json", run_dir / "checkpoints.json")
    shutil.copy(FIXTURES / "sample_attempt_tree.json", logs_dir / "attempt_tree.json")
    shutil.copy(FIXTURES / "sample_frames.json", run_dir / "frames.json")
    (figs_dir / "attempt_n0_render.png").write_bytes(b"PNG")
    (figs_dir / "attempt_n1_render.png").write_bytes(b"PNG")

    vm = tmp_path / "video_meta.json"
    shutil.copy(FIXTURES / "video_meta.json", vm)

    ad = FoldingAgentAdapter(
        fold_output_dir=run_dir,
        video_meta_path=vm,
        source_attribution="Test CC BY 3.0",
        run_id="run_test",
    )
    return ad.build_knowledge_package()


# ---------------------------------------------------------------------------
# TestGroundingValid
# ---------------------------------------------------------------------------

class TestGroundingValid:
    def test_valid_observed_package_passes(self) -> None:
        from grounding import EvidenceGrounder
        pkg = _package([_claim("CLM-01"), _claim("CLM-02")])
        result = EvidenceGrounder().validate(pkg)
        assert result.is_valid

    def test_valid_inferred_claim_passes(self) -> None:
        from grounding import EvidenceGrounder
        claim = _claim("CLM-01", is_observed=False, ev=_inf_ev())
        pkg = _package([claim])
        result = EvidenceGrounder().validate(pkg)
        assert result.is_valid

    def test_valid_video_timestamps_pass(self) -> None:
        from grounding import EvidenceGrounder
        claim = KnowledgeClaim(
            claim_id="CLM-01",
            claim_type=ClaimType.STEP,
            statement="Step with video evidence.",
            is_observed=True,
            evidence_refs=[_video_ev("ev-vid-01", 10.0, 22.0)],
        )
        result = EvidenceGrounder().validate(_package([claim]))
        assert result.is_valid

    def test_adapter_package_passes_grounding(self, tmp_path: Path) -> None:
        """The full adapter output must pass grounding validation."""
        from grounding import EvidenceGrounder
        pkg = _adapter_package(tmp_path)
        result = EvidenceGrounder().validate(pkg)
        assert result.is_valid, f"Violations: {result.violations}"

    def test_no_violations_empty_list(self) -> None:
        from grounding import EvidenceGrounder
        pkg = _package([_claim()])
        result = EvidenceGrounder().validate(pkg)
        assert result.violations == []


# ---------------------------------------------------------------------------
# TestGroundingViolations
# ---------------------------------------------------------------------------

class TestGroundingViolations:
    def test_unobserved_claim_with_observed_evidence_fails(self) -> None:
        from grounding import EvidenceGrounder
        # is_observed=False but evidence is OBSERVED — violates forward rule
        claim = _claim("CLM-01", is_observed=False, ev=_obs_ev())
        pkg = _package([claim])
        result = EvidenceGrounder().validate(pkg)
        assert not result.is_valid
        assert any("epistemic_consistency" in v for v in result.violations)

    def test_inverted_interval_rejected_by_schema(self) -> None:
        """EvidenceRef schema must reject end_sec < start_sec at construction."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="end_sec"):
            _video_ev("ev-01", start=30.0, end=10.0)

    def test_negative_start_sec_rejected_by_schema(self) -> None:
        """EvidenceRef schema must reject start_sec < 0 at construction."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="greater_than_equal"):
            EvidenceRef(
                evidence_id="ev-neg",
                source_id="src",
                modality=Modality.VIDEO,
                start_sec=-1.0,
                end_sec=5.0,
                verification_state=VerificationState.OBSERVED,
                confidence=1.0,
            )

    def test_goal_conditioned_inferred_high_confidence_fails(self) -> None:
        from grounding import EvidenceGrounder
        claim = _claim("CLM-01", is_observed=False, ev=_inf_ev(confidence=0.9))
        pkg = _package([claim])
        result = EvidenceGrounder().validate(pkg, transmission_mode="goal-conditioned")
        assert not result.is_valid
        assert any("confidence" in v for v in result.violations)

    def test_goal_conditioned_inferred_low_confidence_passes(self) -> None:
        from grounding import EvidenceGrounder
        claim = _claim("CLM-01", is_observed=False, ev=_inf_ev(confidence=0.4))
        pkg = _package([claim])
        result = EvidenceGrounder().validate(pkg, transmission_mode="goal-conditioned")
        assert result.is_valid

    def test_multiple_violations_all_collected(self) -> None:
        from grounding import EvidenceGrounder
        # Two claims both with epistemic violations (is_observed=False + OBSERVED evidence)
        c1 = _claim("CLM-01", is_observed=False, ev=_obs_ev("ev-01"))
        c2 = _claim("CLM-02", is_observed=False, ev=_obs_ev("ev-02"))
        result = EvidenceGrounder().validate(_package([c1, c2]))
        assert not result.is_valid
        assert len(result.violations) == 2

    def test_raise_if_invalid_raises(self) -> None:
        from grounding import EvidenceGrounder, GroundingViolation
        claim = _claim("CLM-01", is_observed=False, ev=_obs_ev())
        pkg = _package([claim])
        result = EvidenceGrounder().validate(pkg)
        with pytest.raises(GroundingViolation):
            result.raise_if_invalid()

    def test_raise_if_invalid_does_not_raise_on_valid(self) -> None:
        from grounding import EvidenceGrounder
        pkg = _package([_claim()])
        result = EvidenceGrounder().validate(pkg)
        result.raise_if_invalid()  # must not raise


# ---------------------------------------------------------------------------
# TestUncertaintyFlags
# ---------------------------------------------------------------------------

class TestUncertaintyFlags:
    def test_all_observed_no_flags(self) -> None:
        from grounding import EvidenceGrounder
        pkg = _package([_claim("CLM-01"), _claim("CLM-02")])
        result = EvidenceGrounder().validate(pkg)
        assert result.uncertainty_flags == []

    def test_inferred_claim_flagged(self) -> None:
        from grounding import EvidenceGrounder
        inferred = _claim("CLM-01", is_observed=False, ev=_inf_ev())
        pkg = _package([_claim("CLM-02"), inferred])
        result = EvidenceGrounder().validate(pkg)
        assert any("CLM-01" in f for f in result.uncertainty_flags)
        assert not any("CLM-02" in f for f in result.uncertainty_flags)

    def test_observed_claim_with_inferred_evidence_flagged(self) -> None:
        from grounding import EvidenceGrounder
        # is_observed=True but EvidenceRef says INFERRED — unusual but valid
        ev = EvidenceRef(
            evidence_id="ev-mix",
            source_id="src",
            modality=Modality.IMAGE,
            verification_state=VerificationState.INFERRED,
            confidence=0.8,
        )
        claim = KnowledgeClaim(
            claim_id="CLM-01",
            claim_type=ClaimType.STEP,
            statement="Mixed epistemic state.",
            is_observed=True,
            evidence_refs=[ev],
        )
        result = EvidenceGrounder().validate(_package([claim]))
        assert any("CLM-01" in f for f in result.uncertainty_flags)

    def test_adapter_package_no_flags_for_match_checkpoints(self, tmp_path: Path) -> None:
        """Adapter fixture has all MATCH checkpoints → no uncertainty flags."""
        from grounding import EvidenceGrounder
        pkg = _adapter_package(tmp_path)
        result = EvidenceGrounder().validate(pkg)
        assert result.uncertainty_flags == []
