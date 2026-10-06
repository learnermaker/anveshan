"""Deterministic Criterion-Level Evaluation Engine for Track B.

Evaluates LearnerAttempts against an explicit RubricDefinition.
Enforces score bounds, required criteria, total score arithmetic,
and passing semantics with 100% deterministic code.
"""

from datetime import datetime, timezone
import uuid
from typing import List, Optional

from tracks.common.schemas import (
    LearnerAttempt,
    RubricDefinition,
    Evaluation,
    CriterionResult,
    CriterionStatus,
    EvaluatorType,
)


def evaluate_attempt(
    attempt: LearnerAttempt,
    rubric: RubricDefinition,
    criterion_results: List[CriterionResult],
    evaluator_type: EvaluatorType = EvaluatorType.MODEL_ASSISTED,
    evaluation_id: Optional[str] = None,
) -> Evaluation:
    """Evaluate a LearnerAttempt against a RubricDefinition.

    Args:
        attempt: The submitted LearnerAttempt.
        rubric: The authoritative RubricDefinition.
        criterion_results: List of criterion-level findings and scores.
        evaluator_type: Whether evaluation was deterministic, model-assisted, or expert.
        evaluation_id: Optional evaluation ID; generated if None.

    Returns:
        Evaluation: Validated Evaluation contract instance.

    Raises:
        ValueError: If criteria are missing, unrecognized, or exceed rubric bounds.
    """
    if not criterion_results:
        raise ValueError("Evaluation must contain at least one CriterionResult.")

    rubric_criteria_map = {c.criterion_id: c for c in rubric.criteria}
    evaluated_ids = set()

    for cr in criterion_results:
        if cr.criterion_id not in rubric_criteria_map:
            raise ValueError(
                f"Criterion '{cr.criterion_id}' is not defined in Rubric '{rubric.rubric_id}'"
            )
        rubric_crit = rubric_criteria_map[cr.criterion_id]
        if cr.score > rubric_crit.weight:
            raise ValueError(
                f"Score for criterion '{cr.criterion_id}' ({cr.score}) exceeds "
                f"rubric maximum allowed weight ({rubric_crit.weight})"
            )
        if cr.score < 0.0:
            raise ValueError(
                f"Score for criterion '{cr.criterion_id}' ({cr.score}) cannot be negative"
            )
        evaluated_ids.add(cr.criterion_id)

    # Validate that all required rubric criteria are evaluated
    for crit_id, crit in rubric_criteria_map.items():
        if crit.required and crit_id not in evaluated_ids:
            raise ValueError(
                f"Required rubric criterion '{crit_id}' ({crit.name}) is missing from results"
            )

    # Deterministic total score arithmetic
    total_score = round(sum(cr.score for cr in criterion_results), 4)

    # Uncertainty detection
    uncertainty_flags = [
        cr.criterion_id
        for cr in criterion_results
        if cr.status == CriterionStatus.UNCERTAIN
    ]

    # Deterministic passing gate
    passed = True
    if rubric.passing_score is not None:
        if total_score < rubric.passing_score:
            passed = False

    # Required criteria check: any required criterion marked NOT_SATISFIED fails the attempt
    for cr in criterion_results:
        rubric_crit = rubric_criteria_map.get(cr.criterion_id)
        if rubric_crit and rubric_crit.required:
            if cr.status == CriterionStatus.NOT_SATISFIED:
                passed = False
                break

    eval_id = evaluation_id or f"eval-{attempt.attempt_id}-{uuid.uuid4().hex[:6]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    return Evaluation(
        evaluation_id=eval_id,
        attempt_id=attempt.attempt_id,
        rubric_id=rubric.rubric_id,
        criterion_results=criterion_results,
        total_score=total_score,
        passed=passed,
        evaluator_type=evaluator_type,
        uncertainty_flags=uncertainty_flags,
        evaluated_at=now_iso,
    )
