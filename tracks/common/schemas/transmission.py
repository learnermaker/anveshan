"""Transmission record schema representing the final proof artifact.

Records the end-to-end event:
Expert -> Knowledge -> Rubric -> Baseline -> Teaching -> Feedback -> Retry -> Gain -> Lineage.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class LineageMetadata(BaseModel):
    """Lineage, evolution, and provenance metadata."""

    parent_transmission_id: Optional[str] = Field(
        None,
        description="ID of a previous transmission if this is part of an evolutionary lineage chain",
    )
    recorded_at: str = Field(..., description="ISO timestamp of when the transmission was completed")
    provenance_hash: Optional[str] = Field(
        None,
        description="Cryptographic or content hash of source and attempt artifacts for auditability",
    )
    adaptation_notes: Optional[str] = Field(
        None,
        description="Notes on any technique adaptation or personalization made by the learner",
    )


class TransmissionRecord(BaseModel):
    """The immutable transmission record proving expertise transfer."""

    transmission_id: str = Field(..., description="Unique transmission event identifier")
    skill_id: str = Field(..., description="Target skill identifier")
    package_id: str = Field(..., description="KnowledgePackage ID containing expert source claims")
    rubric_id: str = Field(..., description="RubricDefinition ID applied for scoring")
    expert_id: str = Field(..., description="ID or name of expert source")
    learner_id: str = Field(..., description="ID or name of practicing learner")
    baseline_attempt_id: str = Field(..., description="LearnerAttempt ID for initial baseline attempt")
    retry_attempt_id: str = Field(..., description="LearnerAttempt ID for post-feedback retry attempt")
    baseline_score: float = Field(..., ge=0.0, description="Total score achieved on baseline attempt")
    retry_score: float = Field(..., ge=0.0, description="Total score achieved on retry attempt")
    transmission_gain: float = Field(
        ...,
        description="Measured improvement: retry_score - baseline_score (computed deterministically)",
    )
    criteria_improved: List[str] = Field(
        default_factory=list,
        description="List of criterion IDs that showed measurable improvement on retry",
    )
    lineage: LineageMetadata = Field(..., description="Lineage and provenance metadata")

    @model_validator(mode="after")
    def validate_transmission_gain(self) -> "TransmissionRecord":
        calculated_gain = round(self.retry_score - self.baseline_score, 4)
        if abs(self.transmission_gain - calculated_gain) > 1e-4:
            raise ValueError(
                f"transmission_gain ({self.transmission_gain}) must equal retry_score ({self.retry_score}) - "
                f"baseline_score ({self.baseline_score}) = {calculated_gain}"
            )
        return self
