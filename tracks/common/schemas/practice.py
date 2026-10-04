"""Practice task schema defining a bounded exercise for a learner.

Handoff contract from Track A to Track B.
Binds to both the KnowledgePackage and the RubricDefinition.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class TaskConstraint(BaseModel):
    """Execution constraint for the practice task."""

    constraint_type: str = Field(..., description="e.g. time_limit, tool_spec, material_spec, safety")
    description: str = Field(..., description="Explanation of the constraint")
    value: Optional[str] = Field(None, description="Quantified value if applicable (e.g. '60s', '45 degrees')")


class PracticeTask(BaseModel):
    """The bounded practice activity assigned to a learner."""

    task_id: str = Field(..., description="Unique practice task identifier")
    package_id: str = Field(..., description="ID of the KnowledgePackage being practiced")
    rubric_id: str = Field(..., description="ID of the RubricDefinition used to evaluate this task")
    title: str = Field(..., description="Title of the practice assignment")
    instructions: str = Field(..., description="Clear step-by-step instructions for the learner")
    constraints: List[TaskConstraint] = Field(
        default_factory=list,
        description="Physical, temporal, or material constraints for the task",
    )
    target_criteria_ids: List[str] = Field(
        default_factory=list,
        description="Optional list of specific rubric criteria IDs targeted by this task",
    )
