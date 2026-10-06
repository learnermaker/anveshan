"""Deterministic scoring: metric value -> band -> status -> score (track-b-spec §5).

This is the ONLY place scores are produced. Models never set scores.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

from tracks.common.casedata import ObserverBinding, Observers
from tracks.common.schemas import CriterionStatus, EvidenceRef, RubricDefinition

from track_b.trajectory import MetricValue, TrajectoryResult

SCORE_POLICY_ID = "score_policy_v1"

SCORE_POLICY_V1: Dict[CriterionStatus, float] = {
    CriterionStatus.SATISFIED: 1.0,
    CriterionStatus.PARTIALLY_SATISFIED: 0.5,
    CriterionStatus.NOT_SATISFIED: 0.0,
    CriterionStatus.UNCERTAIN: 0.0,
}

PROCESS_NOT_OBSERVABLE = "process not observable"


@dataclass
class ScoredCriterion:
    criterion_id: str
    metric_id: str
    status: CriterionStatus
    score: float
    value: Optional[float]
    finding: str
    evidence: Optional[EvidenceRef]
    position: Optional[float]
    uncertain_reason: Optional[str] = None


def band_status(binding: ObserverBinding, value: float) -> CriterionStatus:
    """First band whose inclusive [min, max] contains ``value`` wins; else ``otherwise``."""
    for band in binding.bands:
        if band.min is not None and value < band.min:
            continue
        if band.max is not None and value > band.max:
            continue
        return CriterionStatus(band.status)
    return CriterionStatus(binding.otherwise)


def policy_score(status: CriterionStatus, weight: float) -> float:
    return round(weight * SCORE_POLICY_V1[status], 4)


def score_criterion(
    criterion_id: str,
    weight: float,
    binding: ObserverBinding,
    metric: Optional[MetricValue],
    process_observable: bool,
) -> ScoredCriterion:
    reason: Optional[str] = None
    value: Optional[float] = None
    finding = ""
    evidence: Optional[EvidenceRef] = None
    position: Optional[float] = None
    if metric is not None:
        value, finding, evidence, position = metric.value, metric.finding, metric.evidence, metric.position

    if binding.process and not process_observable:
        status, reason = CriterionStatus.UNCERTAIN, PROCESS_NOT_OBSERVABLE
        value, position = None, None
        finding = f"Not assessed: {PROCESS_NOT_OBSERVABLE} from a final-state attempt."
    elif metric is None:
        status, reason = CriterionStatus.UNCERTAIN, f"metric {binding.metric} was not produced by the evaluator"
        finding = f"Not assessed: {reason}."
    elif value is None or (isinstance(value, float) and math.isnan(value)):
        status = CriterionStatus.UNCERTAIN
        reason = metric.uncertain_reason or f"metric {binding.metric} could not be computed"
        value = None
        if not finding:
            finding = f"Not assessed: {reason}."
        elif reason not in finding:
            finding = f"{finding} (not assessable: {reason})"
    else:
        status = band_status(binding, float(value))

    return ScoredCriterion(
        criterion_id=criterion_id,
        metric_id=binding.metric,
        status=status,
        score=policy_score(status, weight),
        value=value,
        finding=finding,
        evidence=evidence,
        position=position,
        uncertain_reason=reason,
    )


def score_trajectory(rubric: RubricDefinition, observers: Observers, trajectory: TrajectoryResult) -> Dict[str, ScoredCriterion]:
    """Score every rubric criterion (rubric order). Never drops a criterion."""
    out: Dict[str, ScoredCriterion] = {}
    for crit in rubric.criteria:
        binding = observers.criteria[crit.criterion_id]
        out[crit.criterion_id] = score_criterion(
            crit.criterion_id,
            crit.weight,
            binding,
            trajectory.metrics.get(binding.metric),
            trajectory.process_observable,
        )
    return out
