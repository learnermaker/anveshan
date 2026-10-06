"""First divergence (evaluation-core §2/§6, track-b-spec §6.2). Deterministic.

Candidates are criteria whose status is NOT_SATISFIED or PARTIALLY_SATISFIED.
UNCERTAIN never qualifies.

1. If any candidate's metric has a *material* trajectory event, the first divergence is
   the earliest such event ("the smallest t with a material violation"); ties break by
   criterion_map.order_index, then required before optional, then criterion id.
2. Otherwise it is the first unmet goal criterion in O order: criterion_map.order_index,
   then required before optional, then the metric's position, then criterion id.
3. No candidates -> None (if criteria are uncertain the drill becomes "re-record").

Where track-b-spec §6.2 (order_index first) and evaluation-core (earliest violation first)
differ, evaluation-core wins.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Tuple

from tracks.common.schemas import CriterionStatus, Evaluation

from track_b.handoff import TrackBHandoff
from track_b.scoring import ScoredCriterion
from track_b.trajectory import DivergenceEvent, TrajectoryResult

CANDIDATE_STATUSES = {CriterionStatus.NOT_SATISFIED, CriterionStatus.PARTIALLY_SATISFIED}


def _dump(ev) -> Optional[Dict[str, Any]]:
    return ev.model_dump(mode="json") if ev is not None else None


def find_first_divergence(
    handoff: TrackBHandoff,
    evaluation: Evaluation,
    scored: Dict[str, ScoredCriterion],
    trajectory: TrajectoryResult,
) -> Optional[Dict[str, Any]]:
    results = {r.criterion_id: r for r in evaluation.criterion_results}
    candidates = [cid for cid, r in results.items() if r.status in CANDIDATE_STATUSES]
    if not candidates:
        return None

    def order_key(cid: str) -> Tuple[int, int]:
        entry = handoff.criterion_map.criteria[cid]
        return (entry.order_index, 0 if handoff.criterion(cid).required else 1)

    # Earliest material event per candidate (matched by the criterion's bound metric).
    first_event: Dict[str, DivergenceEvent] = {}
    if trajectory.process_observable:
        for cid in candidates:
            metric_id = handoff.observers.criteria[cid].metric
            events = [e for e in trajectory.events if e.metric == metric_id and e.severity == "material"]
            if events:
                first_event[cid] = min(events, key=lambda e: e.position)

    event: Optional[DivergenceEvent] = None
    if first_event:
        chosen = min(first_event, key=lambda c: (first_event[c].position, *order_key(c), c))
        event = first_event[chosen]
    else:
        def fallback_key(c: str):
            pos = scored[c].position
            return (*order_key(c), pos if pos is not None and not math.isnan(pos) else math.inf, c)

        chosen = min(candidates, key=fallback_key)

    result = results[chosen]
    crit = handoff.criterion(chosen)
    entry = handoff.criterion_map.criteria[chosen]
    if event is not None:
        position: Optional[float] = event.position
        position_kind: str = event.position_kind
        learner_evidence = event.evidence
    else:
        position = scored[chosen].position
        position_kind = trajectory.curve_kind
        learner_evidence = result.evidence_ref
    return {
        "criterion_id": chosen,
        "criterion_name": crit.name,
        "status": result.status.value,
        "position": position,
        "position_kind": position_kind,
        "learner_evidence": _dump(learner_evidence),
        "expert_evidence": _dump(handoff.expert_evidence(chosen)),
        "observed_finding": result.observed_finding,
        "why_it_matters": entry.why_it_matters,
        "source_claim_ids": list(entry.source_claim_ids),
        "drill_hint": entry.drill_hint,
    }
