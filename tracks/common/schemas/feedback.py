"""Feedback schema providing evidence-grounded coaching to the learner.

Produced by Track B coaching loop after Evaluation; informs the learner's retry.
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from .evidence import EvidenceRef


class FeedbackItem(BaseModel):
    """Specific, grounded coaching feedback item for a criterion."""

    criterion_id: str = Field(..., description="Rubric criterion this feedback targets")
    what_was_observed: str = Field(..., description="Objective description of what the learner did")
    what_differed: str = Field(
        ...,
        description="How the learner's performance differed from the expert demonstration",
    )
    corrective_advice: str = Field(
        ...,
        description="Actionable coaching on how to correct the issue on next attempt",
    )
    expert_evidence_ref: Optional[EvidenceRef] = Field(
        None,
        description="Reference to expert demonstration video showing the correct technique/cue",
    )
    learner_evidence_ref: Optional[EvidenceRef] = Field(
        None,
        description="Reference to the learner's own clip where the deviation occurred",
    )


class Feedback(BaseModel):
    """Structured feedback delivered to a learner before retry."""

    feedback_id: str = Field(..., description="Unique feedback identifier")
    evaluation_id: str = Field(..., description="ID of the Evaluation that generated this feedback")
    attempt_id: str = Field(..., description="ID of the LearnerAttempt evaluated")
    summary: str = Field(..., description="Encouraging, synthesized coaching overview")
    items: List[FeedbackItem] = Field(
        ...,
        min_length=1,
        description="Targeted criterion-level coaching items",
    )
    recommended_retry_focus: List[str] = Field(
        default_factory=list,
        description="List of criterion IDs prioritized for the next attempt",
    )
