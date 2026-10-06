"""Micro-drill view model (track-b-spec §7.3). Practice only: never scored, never an attempt."""

from __future__ import annotations

from typing import Any, Dict, Optional

from tracks.common.schemas import CriterionStatus, Evaluation

from track_b.feedback import OBSERVABILITY_ADVICE
from track_b.handoff import TrackBHandoff


def build_drill(
    handoff: TrackBHandoff,
    evaluation: Evaluation,
    first_divergence: Optional[Dict[str, Any]],
    attempt_kind: str,
) -> Optional[Dict[str, Any]]:
    if first_divergence is not None:
        cid = first_divergence["criterion_id"]
        crit = handoff.criterion(cid)
        return {
            "kind": "practice",
            "criterion_id": cid,
            "title": f"Practise: {crit.name}",
            "instruction": first_divergence["drill_hint"],
            "focus_evidence": first_divergence["learner_evidence"],
            "expert_evidence": first_divergence["expert_evidence"],
            "success_hint": crit.observable_indicator,
            "source_claim_ids": first_divergence["source_claim_ids"],
            "scored": False,
        }
    uncertain = [r for r in evaluation.criterion_results if r.status == CriterionStatus.UNCERTAIN]
    if not uncertain:
        return None
    uncertain.sort(key=lambda r: (handoff.criterion_map.criteria[r.criterion_id].order_index, r.criterion_id))
    r = uncertain[0]
    crit = handoff.criterion(r.criterion_id)
    ev = handoff.expert_evidence(r.criterion_id)
    return {
        "kind": "re_record",
        "criterion_id": r.criterion_id,
        "title": f"Re-record so {crit.name} can be assessed",
        "instruction": OBSERVABILITY_ADVICE.get(attempt_kind, "Re-record so this criterion is clearly observable."),
        "focus_evidence": r.evidence_ref.model_dump(mode="json") if r.evidence_ref else None,
        "expert_evidence": ev.model_dump(mode="json") if ev else None,
        "success_hint": crit.observable_indicator,
        "source_claim_ids": list(handoff.criterion_map.criteria[r.criterion_id].source_claim_ids),
        "scored": False,
    }
