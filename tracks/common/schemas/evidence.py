"""Evidence reference schema for multimodal source grounding.

Represents temporal, spatial, or textual locators tying claims and attempts
to authentic source media.
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, model_validator


class Modality(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    SENSOR = "sensor"


class VerificationState(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    UNVERIFIED = "unverified"


class EvidenceRef(BaseModel):
    """Multimodal evidence locator for claims, steps, and attempts."""

    evidence_id: str = Field(..., description="Unique identifier for this evidence reference")
    source_id: str = Field(..., description="Identifier of the source media or file (e.g. URI, file hash)")
    modality: Modality = Field(..., description="Media modality: video, audio, image, text, sensor")
    start_sec: Optional[float] = Field(None, ge=0.0, description="Start timestamp in seconds from beginning of media")
    end_sec: Optional[float] = Field(None, ge=0.0, description="End timestamp in seconds from beginning of media")
    cue_excerpt: Optional[str] = Field(None, description="Observable transcript excerpt or visual description")
    verification_state: VerificationState = Field(
        default=VerificationState.OBSERVED,
        description="Whether this evidence was directly observed, inferred by model, or unverified",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Calibration score or confidence of the detection/locator (0.0 to 1.0)",
    )

    @model_validator(mode="after")
    def validate_timestamps(self) -> "EvidenceRef":
        if self.start_sec is not None and self.end_sec is not None:
            if self.end_sec < self.start_sec:
                raise ValueError(
                    f"end_sec ({self.end_sec}) cannot be earlier than start_sec ({self.start_sec})"
                )
        return self
