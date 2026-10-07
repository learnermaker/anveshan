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


# ---------------------------------------------------------------------------
# GeminiEvidenceEnricher  (v2 — requires GOOGLE_API_KEY)
# ---------------------------------------------------------------------------

class GeminiEvidenceEnricher:
    """
    Enriches KnowledgeClaim cue_excerpts via a Gemini model call.

    v2 of the EvidenceGrounder enrichment step.  For each claim, calls
    Gemini with the geometric state summary + critic_analysis and replaces
    the raw critic_analysis passthrough with a richer, grounded cue_excerpt.

    Does NOT change verification_state or confidence — those are already
    set deterministically by FoldingAgentAdapter based on critic_verdict.

    Parameters
    ----------
    model_id : str
        Gemini model to call (default: gemini-2.0-flash).
    api_key : str | None
        GOOGLE_API_KEY.  Falls back to environment / .env.
    prompt_path : Path | None
        Override the default prompt file location.
    """

    DEFAULT_MODEL = "gemini-3.8-flash"
    PROMPT_FILE = Path(__file__).parent / "prompts" / "evidence_grounder_v1.txt"

    def __init__(
        self,
        model_id: str | None = None,
        api_key: str | None = None,
        prompt_path: Path | None = None,
    ) -> None:
        self.model_id = model_id or self.DEFAULT_MODEL
        self._api_key = api_key
        self._prompt_path = prompt_path or self.PROMPT_FILE
        self._client: Any = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def enrich(
        self,
        package: KnowledgePackage,
        checkpoints: list[Any],  # list[FoldCheckpoint] — imported lazily
    ) -> KnowledgePackage:
        """
        Replace cue_excerpt on each EvidenceRef with a Gemini-enriched
        description.  All other fields are unchanged.

        Returns the same package object (mutated in place).
        """
        client = self._ensure_client()
        prompt_template = self._prompt_path.read_text(encoding="utf-8")

        # Build checkpoint lookup by frame_index
        cp_by_frame: dict[int, Any] = {cp.frame_index: cp for cp in checkpoints}

        for claim in package.claims:
            # Determine which checkpoint backs this claim
            # CLM-01 → frame_index 1, CLM-02 → frame_index 2, etc.
            try:
                frame_n = int(claim.claim_id.split("-")[-1])
            except (ValueError, IndexError):
                continue

            cp = cp_by_frame.get(frame_n)
            if cp is None:
                continue

            raw = cp.raw_representation
            edges = raw.get("edges", [])
            mountain = [[e[0], e[1]] for e in edges if len(e) >= 3 and str(e[2]).upper() == "M"]
            valley   = [[e[0], e[1]] for e in edges if len(e) >= 3 and str(e[2]).upper() == "V"]
            layers   = raw.get("layers", [])
            faces    = raw.get("faces", {})
            orient   = raw.get("faces_orientations", {})
            back_up  = [fid for fid, o in orient.items() if o == 1]

            prompt = prompt_template.format(
                claim_id=claim.claim_id,
                claim_type=claim.claim_type.value,
                critic_analysis=cp.critic_analysis or "",
                critic_verdict=cp.critic_verdict,
                operations_delta=cp.operations,
                vertex_count=len(raw.get("vertices", {})),
                face_count=len(faces),
                mountain_edges=mountain,
                valley_edges=valley,
                layer_count=len(layers),
                faces_back_up=back_up,
            )

            enriched_excerpt = self._call_gemini(client, prompt)

            # Update cue_excerpt on ALL evidence refs for this claim (one call shared)
            for ev in claim.evidence_refs:
                ev.cue_excerpt = enriched_excerpt[:500]

        return package

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client

        key = self._api_key or self._load_env_key()
        if not key:
            raise RuntimeError(
                "GOOGLE_API_KEY not set. "
                "Add it to research/origami_hybrid/.env before running live enrichment."
            )

        from google import genai
        from google.genai import types

        self._client = genai.Client(
            api_key=key,
            http_options=types.HttpOptions(timeout=60_000),
        )
        return self._client

    @staticmethod
    def _load_env_key() -> str:
        """Load GOOGLE_API_KEY from .env if python-dotenv is available."""
        import os
        # Try dotenv first
        try:
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent / ".env", override=False)
        except ImportError:
            pass
        return os.environ.get("GOOGLE_API_KEY", "")

    def _call_gemini(self, client: Any, prompt: str) -> str:
        """Call Gemini with fixed-interval retry on 429 and 5xx."""
        import time
        from google.genai import types
        from google.genai.errors import ClientError, ServerError

        max_retries = 3
        retry_wait = 60.0  # free-tier suggests ~45s; use 60s to be safe

        for attempt in range(max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=self.model_id,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=256,
                    ),
                )
                return (response.text or "").strip()
            except (ClientError, ServerError) as exc:
                retryable = (
                    (isinstance(exc, ClientError) and exc.code == 429) or
                    isinstance(exc, ServerError)
                )
                if retryable and attempt < max_retries:
                    time.sleep(retry_wait)
                    continue
                raise
