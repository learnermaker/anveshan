"""Multimodal Gemini Observer for Track B.

Uses Google Gemini (gemini-2.5-flash / gemini-2.0-flash) to observe learner
attempt media (video/audio/images), ground observations with temporal timestamps,
and produce structured CriterionResult items conforming to common contracts.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

from tracks.common.schemas import (
    LearnerAttempt,
    RubricDefinition,
    CriterionResult,
    CriterionStatus,
    EvidenceRef,
    Modality,
)

# Structured response schema for Gemini output
class CriterionObservation(BaseModel):
    """Structured criterion observation output from Gemini."""
    criterion_id: str = Field(..., description="ID matching a criterion in the RubricDefinition")
    status: str = Field(..., description="'satisfied', 'partially_satisfied', 'not_satisfied', or 'uncertain'")
    score: float = Field(..., description="Awarded points, between 0.0 and criterion max weight")
    observed_finding: str = Field(..., description="Objective description of what was observed in the attempt")
    deviation_analysis: Optional[str] = Field(None, description="How the attempt differed from the reference demonstration")
    start_sec: Optional[float] = Field(None, description="Start timestamp of observed behavior in media")
    end_sec: Optional[float] = Field(None, description="End timestamp of observed behavior in media")
    confidence: float = Field(default=0.95, description="Confidence in this judgment (0.0 to 1.0)")


class ObservationResponse(BaseModel):
    """Container for multiple criterion observations from Gemini."""
    observations: List[CriterionObservation] = Field(..., description="Evaluated criteria observations")


def _load_env_file() -> None:
    """Helper to load .env file if environment variable is not explicitly set."""
    search_paths = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[3] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    for p in search_paths:
        if p.exists():
            try:
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        if k not in os.environ:
                            os.environ[k] = v.strip().strip("'\"")
            except Exception:
                pass


class GeminiObserver:
    """Multimodal observer adapter interfacing with Google Gemini GenAI SDK."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        fallback_mode: bool = True,
    ):
        """Initialize the Gemini Observer.

        Args:
            api_key: Gemini API key. Defaults to GEMINI_API_KEY environment variable.
            model_name: Gemini model ID. Defaults to GEMINI_MODEL env var or 'gemini-flash-lite-latest'.
            fallback_mode: If True, falls back to deterministic mock observations when API key is missing.
        """
        _load_env_file()
        if api_key is None:
            self.api_key = os.environ.get("GEMINI_API_KEY")
        else:
            self.api_key = api_key if api_key.strip() else None

        self.model_name = model_name or os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
        self.fallback_mode = fallback_mode
        self._client = None

        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                if not self.fallback_mode:
                    raise RuntimeError(f"Failed to initialize Google GenAI client: {e}")

    def is_live(self) -> bool:
        """Returns True if the observer has an active Google GenAI client."""
        return self._client is not None

    def observe(
        self,
        attempt: LearnerAttempt,
        rubric: RubricDefinition,
        media_path: Optional[Path] = None,
    ) -> List[CriterionResult]:
        """Inspect learner attempt media and produce criterion-level observations.

        Args:
            attempt: The submitted LearnerAttempt.
            rubric: The target RubricDefinition.
            media_path: Optional local path to the media file.

        Returns:
            List[CriterionResult]: Observations ready for evaluate_attempt().
        """
        if self._client is not None:
            try:
                return self._observe_with_gemini(attempt, rubric, media_path)
            except Exception as e:
                if not self.fallback_mode:
                    raise RuntimeError(f"Gemini observation failed: {e}")

        # Fallback / Offline mock observer
        return self._mock_observe(attempt, rubric)

    def _observe_with_gemini(
        self,
        attempt: LearnerAttempt,
        rubric: RubricDefinition,
        media_path: Optional[Path],
    ) -> List[CriterionResult]:
        """Execute live Gemini multimodal evaluation."""
        from google.genai import types

        rubric_prompt_lines = [
            f"Rubric: {rubric.title}",
            f"Description: {rubric.description or ''}",
            "Criteria to evaluate:",
        ]
        for c in rubric.criteria:
            req_str = "Mandatory" if c.required else "Optional"
            rubric_prompt_lines.append(
                f"- ID: {c.criterion_id} | Name: {c.name} | Max Points: {c.weight} | {req_str}\n"
                f"  Observable Indicator: {c.observable_indicator}\n"
                f"  Description: {c.description}"
            )

        system_instruction = (
            "You are an expert multimodal skill evaluator for Anveshan. "
            "Inspect the learner's practice evidence against each rubric criterion. "
            "For each criterion:\n"
            "1. Pinpoint exact start/end timestamps where the action was observed.\n"
            "2. State what was observed objectively.\n"
            "3. State any deviation from expert performance.\n"
            "4. Choose status: 'satisfied', 'partially_satisfied', 'not_satisfied', or 'uncertain'.\n"
            "5. Award score between 0.0 and criterion max weight (never exceed weight).\n"
            "If evidence is ambiguous or out of frame, assign status 'uncertain'."
        )

        contents = []

        # Attach media if provided and exists
        if media_path and media_path.exists():
            mime_type = "video/mp4" if attempt.evidence.modality == Modality.VIDEO else "image/jpeg"
            file_bytes = media_path.read_bytes()
            contents.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))

        prompt_text = (
            f"Evaluate Learner Attempt ({attempt.attempt_type.value}, attempt #{attempt.attempt_number}).\n"
            f"Evidence description: {attempt.evidence.cue_excerpt or ''}\n\n"
            + "\n".join(rubric_prompt_lines)
        )
        contents.append(prompt_text)

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type="application/json",
            response_schema=ObservationResponse,
            temperature=0.2,
        )

        models_to_try = [self.model_name]
        for fallback in ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-flash-latest"]:
            if fallback not in models_to_try:
                models_to_try.append(fallback)

        response = None
        last_error = None
        for m_name in models_to_try:
            try:
                response = self._client.models.generate_content(
                    model=m_name,
                    contents=contents,
                    config=config,
                )
                if response and response.text:
                    break
            except Exception as e:
                last_error = e
                continue

        if response is None or not response.text:
            raise last_error or RuntimeError("Gemini content generation failed across candidate models")

        raw_parsed = ObservationResponse.model_validate_json(response.text)
        return self._convert_observations_to_results(raw_parsed.observations, attempt, rubric)

    def _convert_observations_to_results(
        self,
        raw_obs: List[CriterionObservation],
        attempt: LearnerAttempt,
        rubric: RubricDefinition,
    ) -> List[CriterionResult]:
        """Convert raw Gemini observations into schema-compliant CriterionResult objects."""
        rubric_map = {c.criterion_id: c for c in rubric.criteria}
        results: List[CriterionResult] = []

        for obs in raw_obs:
            if obs.criterion_id not in rubric_map:
                continue
            rubric_crit = rubric_map[obs.criterion_id]

            # Enforce score bound
            clamped_score = max(0.0, min(obs.score, rubric_crit.weight))

            # Map status enum
            try:
                status_enum = CriterionStatus(obs.status.lower())
            except ValueError:
                status_enum = CriterionStatus.UNCERTAIN

            # Construct evidence ref with timestamps
            ev_ref = None
            if obs.start_sec is not None or obs.end_sec is not None:
                ev_ref = EvidenceRef(
                    evidence_id=f"ev-obs-{obs.criterion_id}-{attempt.attempt_id}",
                    source_id=attempt.evidence.source_id,
                    modality=attempt.evidence.modality,
                    start_sec=obs.start_sec,
                    end_sec=obs.end_sec,
                    cue_excerpt=obs.observed_finding,
                    confidence=obs.confidence,
                )

            results.append(
                CriterionResult(
                    criterion_id=obs.criterion_id,
                    status=status_enum,
                    score=clamped_score,
                    observed_finding=obs.observed_finding,
                    deviation_analysis=obs.deviation_analysis,
                    evidence_ref=ev_ref,
                )
            )

        return results

    def _mock_observe(
        self,
        attempt: LearnerAttempt,
        rubric: RubricDefinition,
    ) -> List[CriterionResult]:
        """Deterministic mock observations for offline testing and replay."""
        is_baseline = attempt.attempt_number == 1
        results: List[CriterionResult] = []

        for c in rubric.criteria:
            if is_baseline:
                # Baseline has flaws on C02 and C03
                if c.criterion_id == "C01":
                    status = CriterionStatus.SATISFIED
                    score = c.weight
                    finding = "Proper setup demonstrated matching reference."
                    deviation = None
                elif c.criterion_id == "C02":
                    status = CriterionStatus.NOT_SATISFIED
                    score = round(c.weight * 0.25, 2)
                    finding = "Observed chalk cut through dot center instead of outer loop."
                    deviation = "Failed outer boundary clearance."
                else:
                    status = CriterionStatus.PARTIALLY_SATISFIED
                    score = round(c.weight * 0.375, 2)
                    finding = "Asymmetrical quadrant loop curvature observed."
                    deviation = "Lacks bilateral reflection."
            else:
                # Retry satisfies all criteria
                status = CriterionStatus.SATISFIED
                score = round(c.weight * 0.95 if not c.required else c.weight, 2)
                finding = f"Clean execution satisfying {c.name} indicator."
                deviation = "Resolved previous divergence."

            ev_ref = EvidenceRef(
                evidence_id=f"ev-mock-{c.criterion_id}-{attempt.attempt_id}",
                source_id=attempt.evidence.source_id,
                modality=attempt.evidence.modality,
                start_sec=attempt.evidence.start_sec or 0.0,
                end_sec=attempt.evidence.end_sec or 10.0,
                cue_excerpt=finding,
                confidence=1.0,
            )

            results.append(
                CriterionResult(
                    criterion_id=c.criterion_id,
                    status=status,
                    score=score,
                    observed_finding=finding,
                    deviation_analysis=deviation,
                    evidence_ref=ev_ref,
                )
            )

        return results
