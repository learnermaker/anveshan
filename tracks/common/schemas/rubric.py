"""Rubric schema defining explicit observable criteria.

This is the shared source of truth for evaluation across Track A and Track B.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class RubricCriterion(BaseModel):
    """An explicit, observable criterion within a rubric."""

    criterion_id: str = Field(..., description="Unique criterion identifier (e.g. C01, tension_check)")
    name: str = Field(..., description="Short descriptive name of the criterion")
    description: str = Field(..., description="What the learner is expected to demonstrate")
    observable_indicator: str = Field(
        ...,
        description="Concrete, observable cue, action, or physical indicator to verify",
    )
    weight: float = Field(
        default=1.0,
        gt=0.0,
        description="Maximum points achievable for this criterion (acts as criterion weight/scale)",
    )
    required: bool = Field(
        default=True,
        description="Whether satisfying this criterion is mandatory for overall pass",
    )


class RubricDefinition(BaseModel):
    """Shared rubric contract serving as the source of truth for evaluation."""

    rubric_id: str = Field(..., description="Unique identifier for the rubric")
    skill_id: str = Field(..., description="Identifier of the skill this rubric evaluates")
    title: str = Field(..., description="Human-readable title of the rubric")
    description: Optional[str] = Field(None, description="Context, scope, or evaluation instructions")
    criteria: List[RubricCriterion] = Field(
        ...,
        min_length=1,
        description="List of observable criteria. Must contain at least one criterion.",
    )
    passing_score: Optional[float] = Field(
        None,
        ge=0.0,
        description="Explicit minimum total score required to achieve competency. If None, passing requires satisfying all required criteria.",
    )

    @property
    def max_possible_score(self) -> float:
        """Sum of all criterion weights."""
        return sum(c.weight for c in self.criteria)

    @model_validator(mode="after")
    def validate_rubric(self) -> "RubricDefinition":
        criterion_ids = [c.criterion_id for c in self.criteria]
        if len(criterion_ids) != len(set(criterion_ids)):
            duplicates = [cid for cid in criterion_ids if criterion_ids.count(cid) > 1]
            raise ValueError(f"Duplicate criterion_ids found in rubric: {set(duplicates)}")

        if self.passing_score is not None:
            max_score = sum(c.weight for c in self.criteria)
            if self.passing_score > max_score:
                raise ValueError(
                    f"passing_score ({self.passing_score}) cannot exceed max possible score ({max_score})"
                )
        return self
