"""Deterministic Transmission Record and Gain Engine for Track B.

Measures knowledge transfer between baseline and retry attempts,
calculating authoritative gain: gain = retry_score - baseline_score,
detecting improved criteria, and generating cryptographic provenance.
"""

from datetime import datetime, timezone
import hashlib
import json
from typing import List, Optional
import uuid

from tracks.common.schemas import (
    PracticeTask,
    RubricDefinition,
    LearnerAttempt,
    AttemptType,
    Evaluation,
    TransmissionRecord,
    LineageMetadata,
)


def compute_transmission_record(
    task: PracticeTask,
    rubric: RubricDefinition,
    baseline_attempt: LearnerAttempt,
    retry_attempt: LearnerAttempt,
    baseline_eval: Evaluation,
    retry_eval: Evaluation,
    expert_id: str = "expert-source",
    transmission_id: Optional[str] = None,
    parent_transmission_id: Optional[str] = None,
    adaptation_notes: Optional[str] = None,
) -> TransmissionRecord:
    """Compute an authoritative TransmissionRecord comparing baseline and retry.

    Args:
        task: The assigned PracticeTask.
        rubric: The shared RubricDefinition.
        baseline_attempt: The learner's initial AttemptType.BASELINE submission.
        retry_attempt: The learner's post-feedback AttemptType.RETRY submission.
        baseline_eval: Evaluation result of the baseline attempt.
        retry_eval: Evaluation result of the retry attempt.
        expert_id: Identifier of the source expert.
        transmission_id: Optional ID; generated if None.
        parent_transmission_id: Optional lineage ancestor ID.
        adaptation_notes: Optional context or notes on technique adaptation.

    Returns:
        TransmissionRecord: Immutable, validated transmission proof contract.

    Raises:
        ValueError: If attempt invariants, learner identities, or scores fail validation.
    """
    # 1. Attempt typing invariants
    if baseline_attempt.attempt_type != AttemptType.BASELINE:
        raise ValueError(
            f"Baseline attempt must have attempt_type BASELINE, got '{baseline_attempt.attempt_type}'"
        )
    if baseline_attempt.attempt_number != 1:
        raise ValueError(
            f"Baseline attempt must have attempt_number == 1, got {baseline_attempt.attempt_number}"
        )
    if retry_attempt.attempt_type != AttemptType.RETRY:
        raise ValueError(
            f"Retry attempt must have attempt_type RETRY, got '{retry_attempt.attempt_type}'"
        )
    if retry_attempt.attempt_number < 2:
        raise ValueError(
            f"Retry attempt must have attempt_number >= 2, got {retry_attempt.attempt_number}"
        )

    # 2. Distinct attempt IDs
    if baseline_attempt.attempt_id == retry_attempt.attempt_id:
        raise ValueError("baseline_attempt_id and retry_attempt_id must be distinct.")

    # 3. Learner identity alignment
    if (
        baseline_attempt.learner.participant_id
        != retry_attempt.learner.participant_id
    ):
        raise ValueError(
            f"Learner ID mismatch: baseline learner '{baseline_attempt.learner.participant_id}' "
            f"!= retry learner '{retry_attempt.learner.participant_id}'"
        )
    learner_id = baseline_attempt.learner.participant_id

    # 4. Context cross-contract checks
    if baseline_attempt.task_id != task.task_id or retry_attempt.task_id != task.task_id:
        raise ValueError("Both attempts must reference the provided PracticeTask task_id.")

    if baseline_eval.rubric_id != rubric.rubric_id or retry_eval.rubric_id != rubric.rubric_id:
        raise ValueError("Both evaluations must reference the provided RubricDefinition rubric_id.")

    # 5. Deterministic gain calculation
    baseline_score = round(baseline_eval.total_score, 4)
    retry_score = round(retry_eval.total_score, 4)
    transmission_gain = round(retry_score - baseline_score, 4)

    # 6. Criteria improvement identification
    baseline_scores = {cr.criterion_id: cr.score for cr in baseline_eval.criterion_results}
    retry_scores = {cr.criterion_id: cr.score for cr in retry_eval.criterion_results}

    criteria_improved: List[str] = []
    for crit_id, r_sc in retry_scores.items():
        b_sc = baseline_scores.get(crit_id, 0.0)
        if r_sc > b_sc:
            criteria_improved.append(crit_id)

    # 7. Provenance hash calculation
    audit_payload = {
        "task_id": task.task_id,
        "rubric_id": rubric.rubric_id,
        "learner_id": learner_id,
        "baseline_attempt_id": baseline_attempt.attempt_id,
        "retry_attempt_id": retry_attempt.attempt_id,
        "baseline_score": baseline_score,
        "retry_score": retry_score,
        "transmission_gain": transmission_gain,
        "criteria_improved": criteria_improved,
    }
    payload_bytes = json.dumps(audit_payload, sort_keys=True).encode("utf-8")
    provenance_hash = f"sha256-{hashlib.sha256(payload_bytes).hexdigest()[:24]}"

    t_id = transmission_id or f"trans-{task.task_id}-{uuid.uuid4().hex[:6]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    lineage = LineageMetadata(
        parent_transmission_id=parent_transmission_id,
        recorded_at=now_iso,
        provenance_hash=provenance_hash,
        adaptation_notes=adaptation_notes,
    )

    return TransmissionRecord(
        transmission_id=t_id,
        skill_id=rubric.skill_id,
        package_id=task.package_id,
        rubric_id=rubric.rubric_id,
        expert_id=expert_id,
        learner_id=learner_id,
        baseline_attempt_id=baseline_attempt.attempt_id,
        retry_attempt_id=retry_attempt.attempt_id,
        baseline_score=baseline_score,
        retry_score=retry_score,
        transmission_gain=transmission_gain,
        criteria_improved=criteria_improved,
        lineage=lineage,
    )
