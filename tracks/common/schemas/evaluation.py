"""Evaluation schema capturing criterion-level observations and scores.

Enforces that evaluation is tied strictly to explicit Rubric criteria
and prevents unconstrained single-number scoring.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from .evidence import EvidenceRef


class CriterionStatus(str, Enum):
    SATISFIED = "satisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    NOT_SATISFIED = "not_satisfied"
    UNCERTAIN = "uncertain"


class EvaluatorType(str, Enum):
    DETERMINISTIC = "deterministic"
    MODEL_ASSISTED = "model_assisted"
    HUMAN_EXPERT = "human_expert"


class CriterionResult(BaseModel):
    """Observation and scoring outcome for a single rubric criterion."""

    criterion_id: str = Field(..., description="ID matching a criterion in the RubricDefinition")
    status: CriterionStatus = Field(
        ...,
        description="satisfied, partially_satisfied, not_satisfied, or uncertain",
    )
    score: float = Field(
        ...,
        ge=0.0,
        description="Awarded score for this criterion (must be <= criterion weight)",
    )
    observed_finding: str = Field(
        ...,
        description="What was directly observed in the learner's attempt",
    )
    deviation_analysis: Optional[str] = Field(
        None,
        description="Difference between learner execution and expert demonstration",
    )
    evidence_ref: Optional[EvidenceRef] = Field(
        None,
        description="Specific timestamp/segment in the learner's attempt supporting this judgment",
    )


class Evaluation(BaseModel):
    """Criterion-level evaluation of a LearnerAttempt against a RubricDefinition."""

    evaluation_id: str = Field(..., description="Unique evaluation identifier")
    attempt_id: str = Field(..., description="ID of the LearnerAttempt evaluated")
    rubric_id: str = Field(..., description="ID of the RubricDefinition applied")
    criterion_results: List[CriterionResult] = Field(
        ...,
        min_length=1,
        description="Results for each criterion evaluated",
    )
    total_score: float = Field(
        ...,
        ge=0.0,
        description="Sum of all criterion scores awarded",
    )
    passed: bool = Field(
        default=False,
        description="Whether this attempt satisfied passing threshold and required criteria",
    )
    evaluator_type: EvaluatorType = Field(
        default=EvaluatorType.MODEL_ASSISTED,
        description="Evaluation agent type: deterministic, model_assisted, or human_expert",
    )
    uncertainty_flags: List[str] = Field(
        default_factory=list,
        description="List of criterion_ids flagged as UNCERTAIN due to ambiguous evidence",
    )
    evaluated_at: Optional[str] = Field(None, description="ISO timestamp of evaluation")

    @model_validator(mode="after")
    def validate_total_score(self) -> "Evaluation":
        calculated_total = sum(cr.score for cr in self.criterion_results)
        # Check within floating point tolerance
        if abs(self.total_score - calculated_total) > 1e-4:
            raise ValueError(
                f"total_score ({self.total_score}) must equal the sum of criterion scores ({calculated_total})"
            )
        return self
