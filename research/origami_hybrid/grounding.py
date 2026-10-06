"""
EvidenceGrounder — Anveshan epistemic layer for the hybrid pipeline.

v1 (this file): no LLM calls. Uses critic_analysis directly as cue_excerpt and
derives verification_state from selected_by_comparator (already done in the adapter).
Validates the KnowledgePackage against grounding rules equivalent to
GroundingService.validate_package_grounding() in tracks/track-a/src/grounding.py.

v2 (commit 10): replaces the passthrough with a Gemini LLM call for richer
cue_excerpt enrichment. The validation logic in this file stays unchanged.

This module does NOT import from tracks/track-a/src/. It re-implements the
core grounding rules using only tracks/common/schemas/ types.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Resolve common schemas (frozen seam — read-only)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON_SCHEMAS = _REPO_ROOT / "tracks" / "common" / "schemas"

if str(_COMMON_SCHEMAS.parent) not in sys.path:
    sys.path.insert(0, str(_COMMON_SCHEMAS.parent))

from schemas.evidence import EvidenceRef, VerificationState  # noqa: E402
from schemas.knowledge import KnowledgeClaim, KnowledgePackage  # noqa: E402


# ---------------------------------------------------------------------------
# Grounding violation exception
# ---------------------------------------------------------------------------

class GroundingViolation(Exception):
    """Raised when a claim fails an epistemic grounding rule."""

    def __init__(self, claim_id: str, rule: str, detail: str = "") -> None:
        self.claim_id = claim_id
        self.rule = rule
        self.detail = detail
        super().__init__(f"[{claim_id}] {rule}: {detail}")


# ---------------------------------------------------------------------------
# GroundingResult
# ---------------------------------------------------------------------------

@dataclass
class GroundingResult:
    """Output of EvidenceGrounder.validate()."""

    is_valid: bool = True
    uncertainty_flags: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)

    def raise_if_invalid(self) -> None:
        if not self.is_valid:
            raise GroundingViolation(
                claim_id="PACKAGE",
                rule="validate_package_grounding",
                detail="; ".join(self.violations),
            )


# ---------------------------------------------------------------------------
# EvidenceGrounder
# ---------------------------------------------------------------------------

class EvidenceGrounder:
    """
    Validates a KnowledgePackage against Anveshan epistemic grounding rules.

    v1 behaviour
    ------------
    * Validates every claim: evidence_refs non-empty, intervals monotonic,
      is_observed ↔ verification_state consistent (FORWARD mode rules).
    * Collects INFERRED claims into uncertainty_flags.
    * Does NOT make any LLM calls — cue_excerpt comes from the adapter.

    The rules are a standalone re-implementation of the rules in
    tracks/track-a/src/grounding.py (GroundingService), reproduced here
    so this module has no dependency on Track A internals.

    Parameters
    ----------
    temporal_jitter_sec : float
        Tolerance for near-zero negative timestamps (default 0.0 = strict).
    """

    def __init__(self, temporal_jitter_sec: float = 0.0) -> None:
        self.temporal_jitter_sec = temporal_jitter_sec

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(
        self,
        package: KnowledgePackage,
        transmission_mode: str = "forward",
    ) -> GroundingResult:
        """
        Validate all claims in a KnowledgePackage.

        Returns a GroundingResult — call result.raise_if_invalid() to raise
        on the first violation if desired.

        Parameters
        ----------
        package : KnowledgePackage
            The package to validate.
        transmission_mode : str
            "forward" (default), "goal-conditioned", or "corrective".
        """
        result = GroundingResult()
        for claim in package.claims:
            try:
                self._validate_claim(claim, transmission_mode)
            except GroundingViolation as exc:
                result.is_valid = False
                result.violations.append(str(exc))

            # Collect INFERRED regardless of validity
            if not claim.is_observed or any(
                ev.verification_state == VerificationState.INFERRED
                for ev in claim.evidence_refs
            ):
                result.uncertainty_flags.append(
                    f"{claim.claim_id}: {claim.statement[:80]} (INFERRED)"
                )

        return result

    # ------------------------------------------------------------------
    # Rule implementations
    # ------------------------------------------------------------------

    def _validate_claim(
        self,
        claim: KnowledgeClaim,
        transmission_mode: str,
    ) -> None:
        """Apply all grounding rules to a single claim."""
        self._rule_evidence_non_empty(claim)
        self._rule_temporal_monotonicity(claim)
        self._rule_epistemic_consistency(claim, transmission_mode)

    def _rule_evidence_non_empty(self, claim: KnowledgeClaim) -> None:
        """Rule: every claim must have ≥1 EvidenceRef."""
        if not claim.evidence_refs:
            raise GroundingViolation(
                claim_id=claim.claim_id,
                rule="evidence_non_empty",
                detail=f"claim '{claim.claim_id}' has no EvidenceRef",
            )

    def _rule_temporal_monotonicity(self, claim: KnowledgeClaim) -> None:
        """Rule: for each EvidenceRef, 0 <= start_sec <= end_sec."""
        for ev in claim.evidence_refs:
            if ev.start_sec is not None:
                if ev.start_sec < -self.temporal_jitter_sec:
                    raise GroundingViolation(
                        claim_id=claim.claim_id,
                        rule="temporal_monotonicity",
                        detail=(
                            f"evidence {ev.evidence_id}: "
                            f"negative start_sec={ev.start_sec}"
                        ),
                    )
            if ev.start_sec is not None and ev.end_sec is not None:
                if ev.end_sec < ev.start_sec - self.temporal_jitter_sec:
                    raise GroundingViolation(
                        claim_id=claim.claim_id,
                        rule="temporal_monotonicity",
                        detail=(
                            f"evidence {ev.evidence_id}: "
                            f"end_sec={ev.end_sec} < start_sec={ev.start_sec}"
                        ),
                    )

    def _rule_epistemic_consistency(
        self,
        claim: KnowledgeClaim,
        transmission_mode: str,
    ) -> None:
        """
        Rule: is_observed ↔ verification_state consistency.

        FORWARD / CORRECTIVE:
          is_observed=False  →  verification_state must NOT be OBSERVED
          is_observed=True   →  verification_state must be OBSERVED or UNVERIFIED

        GOAL-CONDITIONED:
          is_observed=False  →  same as above + confidence <= 0.5
        """
        for ev in claim.evidence_refs:
            if not claim.is_observed:
                if ev.verification_state == VerificationState.OBSERVED:
                    raise GroundingViolation(
                        claim_id=claim.claim_id,
                        rule="epistemic_consistency",
                        detail=(
                            f"evidence {ev.evidence_id}: "
                            f"is_observed=False but verification_state=OBSERVED"
                        ),
                    )
                if transmission_mode == "goal-conditioned" and ev.confidence > 0.5:
                    raise GroundingViolation(
                        claim_id=claim.claim_id,
                        rule="epistemic_consistency",
                        detail=(
                            f"evidence {ev.evidence_id}: "
                            f"goal-conditioned INFERRED claim has confidence={ev.confidence} > 0.5"
                        ),
                    )
