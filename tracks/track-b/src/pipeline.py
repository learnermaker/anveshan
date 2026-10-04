"""End-to-End Transmission Pipeline Orchestrator for Track B.

Coordinates the full lifecycle:
PracticeTask -> Baseline Attempt -> Baseline Evaluation -> Feedback
             -> Retry Attempt -> Retry Evaluation -> TransmissionRecord.
"""

from typing import Any, Dict, List, Optional

from tracks.common.schemas import (
    KnowledgePackage,
    RubricDefinition,
    PracticeTask,
    LearnerAttempt,
    Evaluation,
    CriterionResult,
    Feedback,
    TransmissionRecord,
    EvaluatorType,
)
from tracks.common.validator import validate_transmission_bundle
from .evaluator import evaluate_attempt
from .feedback import generate_coaching_feedback
from .transmission import compute_transmission_record


class TransmissionPipeline:
    """Orchestrator for the Track B evaluation and transmission loop."""

    def __init__(self, rubric: RubricDefinition, task: PracticeTask, knowledge_package: Optional[KnowledgePackage] = None):
        self.rubric = rubric
        self.task = task
        self.knowledge_package = knowledge_package

    def evaluate_baseline(
        self,
        attempt: LearnerAttempt,
        observations: List[CriterionResult],
        evaluator_type: EvaluatorType = EvaluatorType.MODEL_ASSISTED,
    ) -> Evaluation:
        """Evaluate the initial baseline attempt."""
        return evaluate_attempt(
            attempt=attempt,
            rubric=self.rubric,
            criterion_results=observations,
            evaluator_type=evaluator_type,
        )

    def generate_feedback(self, evaluation: Evaluation) -> Feedback:
        """Generate evidence-linked coaching feedback."""
        return generate_coaching_feedback(
            evaluation=evaluation,
            rubric=self.rubric,
            knowledge_package=self.knowledge_package,
        )

    def evaluate_retry(
        self,
        attempt: LearnerAttempt,
        observations: List[CriterionResult],
        evaluator_type: EvaluatorType = EvaluatorType.MODEL_ASSISTED,
    ) -> Evaluation:
        """Evaluate the post-feedback retry attempt."""
        return evaluate_attempt(
            attempt=attempt,
            rubric=self.rubric,
            criterion_results=observations,
            evaluator_type=evaluator_type,
        )

    def complete_transmission(
        self,
        baseline_attempt: LearnerAttempt,
        retry_attempt: LearnerAttempt,
        baseline_eval: Evaluation,
        retry_eval: Evaluation,
        expert_id: str = "expert-source",
    ) -> TransmissionRecord:
        """Measure net improvement and issue the TransmissionRecord."""
        return compute_transmission_record(
            task=self.task,
            rubric=self.rubric,
            baseline_attempt=baseline_attempt,
            retry_attempt=retry_attempt,
            baseline_eval=baseline_eval,
            retry_eval=retry_eval,
            expert_id=expert_id,
        )

    def run_full_cycle(
        self,
        baseline_attempt: LearnerAttempt,
        baseline_observations: List[CriterionResult],
        retry_attempt: LearnerAttempt,
        retry_observations: List[CriterionResult],
        expert_id: str = "expert-source",
    ) -> Dict[str, Any]:
        """Execute the entire transmission cycle and return a validated replay bundle."""
        b_eval = self.evaluate_baseline(baseline_attempt, baseline_observations)
        fb = self.generate_feedback(b_eval)
        r_eval = self.evaluate_retry(retry_attempt, retry_observations)
        trans_rec = self.complete_transmission(
            baseline_attempt=baseline_attempt,
            retry_attempt=retry_attempt,
            baseline_eval=b_eval,
            retry_eval=r_eval,
            expert_id=expert_id,
        )

        bundle = {
            "knowledge_package": self.knowledge_package.model_dump(mode="json") if self.knowledge_package else {},
            "rubric": self.rubric.model_dump(mode="json"),
            "practice_task": self.task.model_dump(mode="json"),
            "baseline_attempt": baseline_attempt.model_dump(mode="json"),
            "baseline_evaluation": b_eval.model_dump(mode="json"),
            "feedback": fb.model_dump(mode="json"),
            "retry_attempt": retry_attempt.model_dump(mode="json"),
            "retry_evaluation": r_eval.model_dump(mode="json"),
            "transmission_record": trans_rec.model_dump(mode="json"),
        }

        # Verify bundle self-consistency
        is_valid, errors = validate_transmission_bundle(bundle)
        if not is_valid:
            raise ValueError(f"Pipeline output failed bundle validation: {errors}")

        return bundle
