"""Assemble the Evaluation contract from scored criteria (track-b-spec §6.1).

``passed`` follows the common validator exactly: (passing_score is None or total >=
passing_score) AND every required criterion is SATISFIED.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import (
    CriterionResult,
    CriterionStatus,
    Evaluation,
    EvaluatorType,
    RubricCriterion,
    RubricDefinition,
)
from tracks.common.validator import validate_evaluation_against_rubric

from track_b.scoring import ScoredCriterion


def deviation_analysis(crit: RubricCriterion, scored: ScoredCriterion) -> str:
    indicator = crit.observable_indicator.rstrip(".")
    if scored.status == CriterionStatus.SATISFIED:
        return f"Matches the expected indicator: {indicator}."
    if scored.status == CriterionStatus.UNCERTAIN:
        return f"Could not be compared with the expected indicator ({indicator}): {scored.uncertain_reason}."
    label = "Partly meets" if scored.status == CriterionStatus.PARTIALLY_SATISFIED else "Does not meet"
    target = getattr(scored, "target", None)
    if target and scored.value is not None:
        return f"{label} the target. Measured {scored.value:.3g} for {indicator}; the target is {target}."
    return f"{label} the expected indicator: {indicator}."


def is_passed(rubric: RubricDefinition, results: List[CriterionResult], total: float) -> bool:
    by_id = {c.criterion_id: c for c in rubric.criteria}
    if rubric.passing_score is not None and total < rubric.passing_score:
        return False
    return all(r.status == CriterionStatus.SATISFIED for r in results if by_id[r.criterion_id].required)


def build_evaluation(
    *,
    evaluation_id: str,
    attempt_id: str,
    rubric: RubricDefinition,
    scored: Dict[str, ScoredCriterion],
    model_assisted: bool,
    evaluated_at: str,
) -> Tuple[Evaluation, List[str]]:
    """Return (validated Evaluation, warnings). Validator errors raise CONTRACT_VIOLATION."""
    results: List[CriterionResult] = []
    warnings: List[str] = []
    for crit in rubric.criteria:
        s = scored[crit.criterion_id]
        results.append(
            CriterionResult(
                criterion_id=crit.criterion_id,
                status=s.status,
                score=s.score,
                observed_finding=s.finding or f"{crit.name}: no finding reported.",
                deviation_analysis=deviation_analysis(crit, s),
                evidence_ref=s.evidence,
            )
        )
        if crit.required and s.status == CriterionStatus.UNCERTAIN:
            warnings.append(
                f"HUMAN_REVIEW_REQUIRED: required criterion {crit.criterion_id} is uncertain ({s.uncertain_reason})"
            )
    total = round(sum(r.score for r in results), 4)
    evaluation = Evaluation(
        evaluation_id=evaluation_id,
        attempt_id=attempt_id,
        rubric_id=rubric.rubric_id,
        criterion_results=results,
        total_score=total,
        passed=is_passed(rubric, results, total),
        evaluator_type=EvaluatorType.MODEL_ASSISTED if model_assisted else EvaluatorType.DETERMINISTIC,
        uncertainty_flags=[r.criterion_id for r in results if r.status == CriterionStatus.UNCERTAIN],
        evaluated_at=evaluated_at,
    )
    errors = validate_evaluation_against_rubric(evaluation, rubric)
    if errors:
        raise AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, "evaluation failed rubric validation", {"errors": errors})
    return evaluation, warnings
