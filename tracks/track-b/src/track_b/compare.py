"""Baseline vs retry comparison (track-b-spec §8.1, evaluation-core §2 targeted change).

``transmission_gain`` on the record stays the contract formula (retry - baseline). This
view adds per-criterion transitions, the targeted change of the baseline first-divergence
criterion, and the gain excluding observability-only transitions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import CriterionStatus, Evaluation, RubricDefinition

U = CriterionStatus.UNCERTAIN


def transition(b_status: CriterionStatus, b_score: float, r_status: CriterionStatus, r_score: float) -> str:
    if b_status == U and r_status != U:
        return "observability_gain"
    if b_status != U and r_status == U:
        return "observability_loss"
    if r_score > b_score:
        return "improved"
    if r_score < b_score:
        return "regressed"
    return "unchanged"


def criteria_improved(rubric: RubricDefinition, baseline: Evaluation, retry: Evaluation) -> List[str]:
    """Score went up AND the baseline was not UNCERTAIN (skill change, not observability)."""
    b = {r.criterion_id: r for r in baseline.criterion_results}
    r = {x.criterion_id: x for x in retry.criterion_results}
    return [
        c.criterion_id
        for c in rubric.criteria
        if c.criterion_id in b and c.criterion_id in r
        and r[c.criterion_id].score > b[c.criterion_id].score
        and b[c.criterion_id].status != U
    ]


def compare_attempts(
    rubric: RubricDefinition,
    baseline: Evaluation,
    retry: Evaluation,
    baseline_first_divergence: Optional[Dict[str, Any]],
    baseline_curve: List[List[float]],
    retry_curve: List[List[float]],
    recommended_retry_focus: Optional[List[str]] = None,
) -> Dict[str, Any]:
    b = {r.criterion_id: r for r in baseline.criterion_results}
    r = {x.criterion_id: x for x in retry.criterion_results}
    for focus in recommended_retry_focus or []:
        if focus not in r:
            raise AnveshanFailure(
                FailureCategory.CONTRACT_VIOLATION, f"retry evaluation is missing retry-focus criterion {focus}"
            )

    transitions: Dict[str, str] = {}
    skill_gain = 0.0
    for c in rubric.criteria:
        cid = c.criterion_id
        kind = transition(b[cid].status, b[cid].score, r[cid].status, r[cid].score)
        transitions[cid] = kind
        if kind not in ("observability_gain", "observability_loss"):
            skill_gain += r[cid].score - b[cid].score

    targeted: Dict[str, Any] = {"criterion_id": None, "before": None, "after": None, "changed": False, "improved": False}
    if baseline_first_divergence is not None:
        cid = baseline_first_divergence["criterion_id"]
        targeted = {
            "criterion_id": cid,
            "before": b[cid].status.value,
            "after": r[cid].status.value,
            "changed": b[cid].status != r[cid].status,
            "improved": r[cid].score > b[cid].score,
        }

    return {
        "transitions": transitions,
        "targeted_change": targeted,
        "skill_gain_excluding_observability": round(skill_gain, 4),
        "curves": {"baseline": baseline_curve, "retry": retry_curve},
    }
