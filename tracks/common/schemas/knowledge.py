"""Knowledge package schema representing structured expert demonstration.

Emitted by Track A and consumed by downstream teaching and rubric generation.
Includes embedded governance (consent) and auditability (expert review).
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from .evidence import EvidenceRef


class ClaimType(str, Enum):
    STEP = "step"
    CUE = "cue"
    CONDITION = "condition"
    EXCEPTION = "exception"
    FAILURE_MODE = "failure_mode"


class ReviewStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REVISED = "revised"
    REJECTED = "rejected"


class ConsentMetadata(BaseModel):
    """Contributor consent and data sovereignty boundaries."""

    contributor_name: str = Field(..., description="Name or identifier of the knowledge contributor/expert")
    consent_scope: str = Field(
        ...,
        description="Agreed scope of use (e.g. 'hackathon_prototype', 'educational_research')",
    )
    revocable: bool = Field(default=True, description="Whether contributor retains right of withdrawal")
    granted_at: Optional[str] = Field(None, description="ISO timestamp of consent confirmation")
    notes: Optional[str] = Field(None, description="Specific restrictions, community caveats, or notes")


class ExpertReview(BaseModel):
    """Human expert review gate verifying fidelity of AI-extracted claims."""

    reviewer_name: str = Field(..., description="Name of reviewing domain expert")
    status: ReviewStatus = Field(
        default=ReviewStatus.PENDING,
        description="Human review verdict: pending, approved, revised, rejected",
    )
    reviewed_at: Optional[str] = Field(None, description="ISO timestamp of review")
    notes: Optional[str] = Field(None, description="Feedback or required corrections from expert")


class KnowledgeClaim(BaseModel):
    """A discrete proposition extracted from source demonstration with provenance."""

    claim_id: str = Field(..., description="Unique claim identifier (e.g. CLM-01)")
    claim_type: ClaimType = Field(..., description="step, cue, condition, exception, failure_mode")
    statement: str = Field(..., description="Verbatim or concise description of the extracted knowledge")
    is_observed: bool = Field(
        default=True,
        description="True if directly observed in source media, False if model inference",
    )
    evidence_refs: List[EvidenceRef] = Field(
        ...,
        min_length=1,
        description="Provenance links to authentic source media backing this claim",
    )


class KnowledgePackage(BaseModel):
    """Contract for the complete structured expert demonstration."""

    package_id: str = Field(..., description="Unique identifier for this knowledge package")
    skill_id: str = Field(..., description="Target skill identifier")
    title: str = Field(..., description="Descriptive title of the demonstrated technique")
    summary: str = Field(..., description="Concise synopsis of the demonstrated procedure")
    claims: List[KnowledgeClaim] = Field(
        ...,
        min_length=1,
        description="Structured claims (steps, cues, conditions, failure modes)",
    )
    consent: ConsentMetadata = Field(..., description="Contributor consent record")
    expert_review: Optional[ExpertReview] = Field(
        None,
        description="Human-in-the-loop expert review status",
    )

    @model_validator(mode="after")
    def validate_claims(self) -> "KnowledgePackage":
        claim_ids = [c.claim_id for c in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            duplicates = [cid for cid in claim_ids if claim_ids.count(cid) > 1]
            raise ValueError(f"Duplicate claim_ids found: {set(duplicates)}")
        return self
