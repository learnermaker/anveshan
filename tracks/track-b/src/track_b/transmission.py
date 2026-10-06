"""TransmissionRecord + validated 9-key bundle (track-b-spec §8.2).

Migrated from the legacy ``src/transmission.py`` with the review fixes: expert id from
consent, deterministic ids and timestamps (injected clock), full sha256 provenance hash
over the audit payload, adaptation notes, and validation of the whole bundle.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence

from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import (
    AttemptType,
    Evaluation,
    Feedback,
    LearnerAttempt,
    LineageMetadata,
    TransmissionRecord,
)
from tracks.common.validator import validate_transmission_bundle

from track_b.compare import criteria_improved
from track_b.handoff import TrackBHandoff, expert_id
from track_b.scoring import SCORE_POLICY_ID

BUNDLE_KEYS = (
    "knowledge_package",
    "rubric",
    "practice_task",
    "baseline_attempt",
    "baseline_evaluation",
    "feedback",
    "retry_attempt",
    "retry_evaluation",
    "transmission_record",
)


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def provenance_hash(
    handoff: TrackBHandoff,
    attempts: Sequence[LearnerAttempt],
    media_sha256: Sequence[str],
    evaluations: Sequence[Evaluation],
    feedback: Feedback,
) -> str:
    payload = {
        "package_id": handoff.package.package_id,
        "rubric": handoff.rubric.model_dump(mode="json"),
        "task": handoff.task.model_dump(mode="json"),
        "attempts": [
            {"attempt": a.model_dump(mode="json"), "media_sha256": sha} for a, sha in zip(attempts, media_sha256)
        ],
        "evaluations": [e.model_dump(mode="json") for e in evaluations],
        "feedback": feedback.model_dump(mode="json"),
        "score_policy": SCORE_POLICY_ID,
        "observers_version": handoff.observers.version,
    }
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def adaptation_notes(
    handoff: TrackBHandoff, drill_criterion: Optional[str], transitions: Dict[str, str], baseline: Evaluation, retry: Evaluation
) -> str:
    parts: List[str] = [SCORE_POLICY_ID, f"observers v{handoff.observers.version}"]
    if drill_criterion:
        parts.append(f"drill: {drill_criterion}")
    b = {r.criterion_id: r.status.value for r in baseline.criterion_results}
    r = {x.criterion_id: x.status.value for x in retry.criterion_results}
    obs = [f"{cid} {b[cid]}->{r[cid]}" for cid, kind in transitions.items() if kind.startswith("observability_")]
    if obs:
        parts.append("observability transitions: " + ", ".join(obs))
    if not handoff.approved:
        parts.append("package not expert-approved")
    return "; ".join(parts)


def build_transmission(
    *,
    handoff: TrackBHandoff,
    session_id: str,
    baseline_attempt: LearnerAttempt,
    retry_attempt: LearnerAttempt,
    baseline_eval: Evaluation,
    retry_eval: Evaluation,
    feedback: Feedback,
    media_sha256: Sequence[str],
    transitions: Dict[str, str],
    drill_criterion: Optional[str],
    recorded_at: str,
) -> Dict[str, Any]:
    """Return ``{"bundle": {...9 keys}, "transmission_record": {...}}``; validator errors raise."""
    if baseline_attempt.attempt_type != AttemptType.BASELINE or retry_attempt.attempt_type != AttemptType.RETRY:
        raise AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, "transmission needs a BASELINE and a RETRY attempt")
    baseline_score = round(baseline_eval.total_score, 4)
    retry_score = round(retry_eval.total_score, 4)
    record = TransmissionRecord(
        transmission_id=f"tx.{handoff.case_id}.{session_id}",
        skill_id=handoff.rubric.skill_id,
        package_id=handoff.package.package_id,
        rubric_id=handoff.rubric.rubric_id,
        expert_id=expert_id(handoff),
        learner_id=baseline_attempt.learner.participant_id,
        baseline_attempt_id=baseline_attempt.attempt_id,
        retry_attempt_id=retry_attempt.attempt_id,
        baseline_score=baseline_score,
        retry_score=retry_score,
        transmission_gain=round(retry_score - baseline_score, 4),
        criteria_improved=criteria_improved(handoff.rubric, baseline_eval, retry_eval),
        lineage=LineageMetadata(
            parent_transmission_id=None,
            recorded_at=recorded_at,
            provenance_hash=provenance_hash(
                handoff, [baseline_attempt, retry_attempt], media_sha256, [baseline_eval, retry_eval], feedback
            ),
            adaptation_notes=adaptation_notes(handoff, drill_criterion, transitions, baseline_eval, retry_eval),
        ),
    )
    bundle = {
        "knowledge_package": handoff.package.model_dump(mode="json"),
        "rubric": handoff.rubric.model_dump(mode="json"),
        "practice_task": handoff.task.model_dump(mode="json"),
        "baseline_attempt": baseline_attempt.model_dump(mode="json"),
        "baseline_evaluation": baseline_eval.model_dump(mode="json"),
        "feedback": feedback.model_dump(mode="json"),
        "retry_attempt": retry_attempt.model_dump(mode="json"),
        "retry_evaluation": retry_eval.model_dump(mode="json"),
        "transmission_record": record.model_dump(mode="json"),
    }
    ok, errors = validate_transmission_bundle(bundle)
    if not ok:
        raise AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, "transmission bundle failed validation", {"errors": errors})
    return {"bundle": bundle, "transmission_record": bundle["transmission_record"]}
