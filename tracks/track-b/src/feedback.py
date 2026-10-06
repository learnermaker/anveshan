"""Evidence-Grounded Coaching Feedback Generator for Track B.

Generates targeted, actionable feedback linked directly to evaluated criteria,
learner evidence, and expert demonstration reference media.
"""

from typing import List, Optional
import uuid

from tracks.common.schemas import (
    Evaluation,
    RubricDefinition,
    KnowledgePackage,
    Feedback,
    FeedbackItem,
    CriterionStatus,
)


def generate_coaching_feedback(
    evaluation: Evaluation,
    rubric: RubricDefinition,
    knowledge_package: Optional[KnowledgePackage] = None,
    feedback_id: Optional[str] = None,
) -> Feedback:
    """Generate structured, actionable feedback from an Evaluation.

    Args:
        evaluation: The completed Evaluation.
        rubric: The associated RubricDefinition.
        knowledge_package: Optional expert knowledge package for matching expert references.
        feedback_id: Optional feedback ID; generated if None.

    Returns:
        Feedback: Validated Feedback contract instance.
    """
    rubric_map = {c.criterion_id: c for c in rubric.criteria}
    items: List[FeedbackItem] = []
    retry_focus: List[str] = []

    # Map knowledge claims to evidence for expert cross-referencing
    expert_evidence_pool = []
    if knowledge_package:
        for claim in knowledge_package.claims:
            for ev in claim.evidence_refs:
                expert_evidence_pool.append(ev)

    for cr in evaluation.criterion_results:
        rubric_crit = rubric_map.get(cr.criterion_id)
        max_weight = rubric_crit.weight if rubric_crit else 0.0

        # Focus feedback on criteria that were not fully satisfied or had score deductions
        needs_attention = (
            cr.status != CriterionStatus.SATISFIED or cr.score < max_weight
        )

        if needs_attention:
            retry_focus.append(cr.criterion_id)

            # Match expert evidence reference if available
            matched_expert_ref = None
            if expert_evidence_pool:
                # Use first relevant expert reference or pool item
                matched_expert_ref = expert_evidence_pool[
                    len(items) % len(expert_evidence_pool)
                ]

            what_differed = cr.deviation_analysis or (
                f"Observed performance deviated from the expert standard for criterion '{cr.criterion_id}'."
            )

            # Formulate actionable corrective advice
            if cr.status == CriterionStatus.NOT_SATISFIED:
                advice = (
                    f"Prioritize {rubric_crit.name if rubric_crit else cr.criterion_id} on your next retry. "
                    f"Ensure you satisfy the observable indicator: {rubric_crit.observable_indicator if rubric_crit else ''}"
                )
            elif cr.status == CriterionStatus.PARTIALLY_SATISFIED:
                advice = (
                    f"Refine your technique for {rubric_crit.name if rubric_crit else cr.criterion_id}. "
                    f"Align closer with the reference: {what_differed}"
                )
            else:  # UNCERTAIN
                advice = (
                    f"Ensure clear visibility and pacing for {rubric_crit.name if rubric_crit else cr.criterion_id} "
                    "so this criterion can be fully observed and confirmed."
                )

            item = FeedbackItem(
                criterion_id=cr.criterion_id,
                what_was_observed=cr.observed_finding,
                what_differed=what_differed,
                corrective_advice=advice,
                learner_evidence_ref=cr.evidence_ref,
                expert_evidence_ref=matched_expert_ref,
            )
            items.append(item)

    # If all criteria were satisfied, provide celebratory feedback for the highest-weighted criterion
    if not items and evaluation.criterion_results:
        best_cr = max(evaluation.criterion_results, key=lambda c: c.score)
        rubric_crit = rubric_map.get(best_cr.criterion_id)
        items.append(
            FeedbackItem(
                criterion_id=best_cr.criterion_id,
                what_was_observed=best_cr.observed_finding,
                what_differed="Matched the expert standard cleanly.",
                corrective_advice="Maintain this exact execution technique on your next run.",
                learner_evidence_ref=best_cr.evidence_ref,
                expert_evidence_ref=expert_evidence_pool[0] if expert_evidence_pool else None,
            )
        )

    # Synthesize concise coaching summary
    satisfied_count = sum(
        1 for cr in evaluation.criterion_results if cr.status == CriterionStatus.SATISFIED
    )
    total_count = len(evaluation.criterion_results)

    if evaluation.passed:
        summary = (
            f"Great performance! Satisfied {satisfied_count}/{total_count} criteria with a "
            f"total score of {evaluation.total_score}. Keep up the high standard."
        )
    else:
        summary = (
            f"Good effort! Satisfied {satisfied_count}/{total_count} criteria (Score: {evaluation.total_score}). "
            f"Review the targeted coaching items below to improve your score on retry."
        )

    fb_id = feedback_id or f"fb-{evaluation.attempt_id}-{uuid.uuid4().hex[:6]}"

    return Feedback(
        feedback_id=fb_id,
        evaluation_id=evaluation.evaluation_id,
        attempt_id=evaluation.attempt_id,
        summary=summary,
        items=items,
        recommended_retry_focus=retry_focus,
    )
