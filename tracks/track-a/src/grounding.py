from typing import List, Literal
from tracks.common.schemas import (
    EvidenceRef,
    KnowledgeClaim,
    KnowledgePackage,
    VerificationState,
)
from models import FailureCategory, TrackAFailure


class GroundingService:
    """Epistemological evidence grounding service implementing Spec 4.

    Enforces temporal monotonicity, observation-vs-inference discipline,
    and mode-specific verification rules across the 6-tier Source Hierarchy.
    """

    def __init__(self, temporal_jitter_sec: float = 1.5) -> None:
        self.temporal_jitter_sec = temporal_jitter_sec

    def validate_intervals(self, evidence_refs: List[EvidenceRef]) -> None:
        """Enforce temporal monotonicity: 0 <= start_sec <= end_sec."""
        for ev in evidence_refs:
            if ev.start_sec is not None:
                if ev.start_sec < 0.0:
                    raise TrackAFailure(
                        FailureCategory.CONTRACT_VIOLATION,
                        f"Negative start_sec ({ev.start_sec}) in evidence {ev.evidence_id}",
                        {"evidence_id": ev.evidence_id, "start_sec": ev.start_sec},
                    )
            if ev.start_sec is not None and ev.end_sec is not None:
                if ev.end_sec < ev.start_sec:
                    raise TrackAFailure(
                        FailureCategory.CONTRACT_VIOLATION,
                        f"Inverted interval: end_sec ({ev.end_sec}) < start_sec ({ev.start_sec}) in evidence {ev.evidence_id}",
                        {
                            "evidence_id": ev.evidence_id,
                            "start_sec": ev.start_sec,
                            "end_sec": ev.end_sec,
                        },
                    )

    def verify_claim_support(self, claim: KnowledgeClaim) -> None:
        """Ensure every claim is backed by at least one EvidenceRef."""
        if not claim.evidence_refs:
            raise TrackAFailure(
                FailureCategory.UNSUPPORTED_CLAIM,
                f"Claim {claim.claim_id} lacks supporting EvidenceRef",
                {"claim_id": claim.claim_id, "statement": claim.statement},
            )

    def enforce_epistemological_state(
        self,
        claim: KnowledgeClaim,
        transmission_mode: Literal["forward", "goal-conditioned", "corrective"] = "forward",
    ) -> None:
        """Enforce observed vs inferred rules based on transmission mode."""
        self.verify_claim_support(claim)
        self.validate_intervals(claim.evidence_refs)

        for ev in claim.evidence_refs:
            # Mode-specific epistemological enforcement
            if transmission_mode == "goal-conditioned":
                # For goal-conditioned cases, candidate procedures must be INFERRED with confidence <= 0.5
                if not claim.is_observed:
                    if ev.verification_state == VerificationState.OBSERVED:
                        raise TrackAFailure(
                            FailureCategory.CONTRACT_VIOLATION,
                            f"Goal-conditioned claim {claim.claim_id} is unobserved procedure but evidence is marked OBSERVED",
                            {"claim_id": claim.claim_id},
                        )
                    if ev.confidence > 0.5:
                        raise TrackAFailure(
                            FailureCategory.CONTRACT_VIOLATION,
                            f"Inferred procedure claim {claim.claim_id} cannot have confidence > 0.5 (got {ev.confidence})",
                            {"claim_id": claim.claim_id, "confidence": ev.confidence},
                        )
            else:
                # Forward / Corrective modes
                if not claim.is_observed:
                    if ev.verification_state == VerificationState.OBSERVED:
                        raise TrackAFailure(
                            FailureCategory.CONTRACT_VIOLATION,
                            f"Unobserved claim {claim.claim_id} cannot have OBSERVED evidence locator",
                            {"claim_id": claim.claim_id},
                        )

    def validate_package_grounding(
        self,
        package: KnowledgePackage,
        transmission_mode: Literal["forward", "goal-conditioned", "corrective"] = "forward",
    ) -> List[str]:
        """Perform full epistemological audit of all claims in package.

        Returns list of claims flagged as INFERRED (uncertainty summary).
        """
        uncertainty_flags: List[str] = []
        for claim in package.claims:
            self.enforce_epistemological_state(claim, transmission_mode)
            if not claim.is_observed or any(
                ev.verification_state == VerificationState.INFERRED
                for ev in claim.evidence_refs
            ):
                uncertainty_flags.append(
                    f"{claim.claim_id}: {claim.statement} (INFERRED)"
                )
        return uncertainty_flags
