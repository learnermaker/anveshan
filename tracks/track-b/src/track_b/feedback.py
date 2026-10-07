"""Grounded, deterministic feedback (track-b-spec §7.1, evaluation-core §6).

One FeedbackItem per criterion that is not SATISFIED, first divergence first, then the
rest in criterion_map order. ``expert_evidence_ref`` is the criterion map's reference
evidence for THAT criterion (never round-robin); None when the map has none.
UNCERTAIN items are evidence-quality guidance, not skill corrections.

Optional wording pass (P2): pass ``wording`` = a callable that takes the template
Feedback and returns a reworded Feedback (e.g. a Gemma call recorded through the model
gateway). ``guard_wording`` keeps the rewrite only if every number, criterion id and claim
id from the template survives and no new numbers appear; otherwise the template is kept.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Set

from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import CriterionStatus, Evaluation, Feedback, FeedbackItem
from tracks.common.validator import validate_feedback_against_evaluation

from track_b.handoff import TrackBHandoff

WordingPass = Callable[[Feedback], Feedback]

OBSERVABILITY_ADVICE: Dict[str, str] = {
    "trace": "Draw the whole pattern on the canvas in one session so every stroke is recorded.",
    "image": (
        "Retake the photo straight above the pattern, in even light, with the whole pattern in frame. "
        "To have the drawing process checked, draw on the canvas instead."
    ),
    "audio": "Record closer to the instrument in a quiet room, without clipping, for the full task length.",
    "video": "Film with the paper fully in frame, in good light, with a steady camera, for the whole task.",
}


def _fmt(x: float) -> str:
    return f"{x:g}"


def _differed(indicator: str, deviation: Optional[str]) -> str:
    """One sentence on the gap. The deviation analysis usually restates the indicator, so it is
    used alone when it already contains it (no "Expected: X. Does not meet: X." repetition)."""
    indicator = indicator.rstrip(".")
    deviation = (deviation or "").strip()
    if deviation and indicator.lower() in deviation.lower():
        return deviation
    return f"Expected: {indicator}. {deviation}".strip()


def _where(first: Dict[str, Any]) -> str:
    pos = first.get("position")
    if pos is None:
        return ""
    kind = first.get("position_kind") or ""
    if kind == "time":
        return f" at {float(pos):.1f} s"
    return f" at {kind} {_fmt(float(pos))}"


def _claims(handoff: TrackBHandoff, cid: str) -> str:
    return ", ".join(handoff.criterion_map.criteria[cid].source_claim_ids)


def _ordered_ids(handoff: TrackBHandoff, evaluation: Evaluation, first_cid: Optional[str]) -> List[str]:
    non_sat = [r.criterion_id for r in evaluation.criterion_results if r.status != CriterionStatus.SATISFIED]
    non_sat.sort(key=lambda c: (handoff.criterion_map.criteria[c].order_index, c))
    if first_cid in non_sat:
        non_sat.remove(first_cid)
        non_sat.insert(0, first_cid)
    return non_sat


def _item(handoff: TrackBHandoff, evaluation: Evaluation, cid: str, attempt_kind: str) -> FeedbackItem:
    result = next(r for r in evaluation.criterion_results if r.criterion_id == cid)
    crit = handoff.criterion(cid)
    entry = handoff.criterion_map.criteria[cid]
    expert = handoff.expert_evidence(cid)
    if result.status == CriterionStatus.UNCERTAIN:
        return FeedbackItem(
            criterion_id=cid,
            what_was_observed=result.observed_finding,
            what_differed=f"{crit.name} could not be assessed from this attempt, so it was scored 0 (uncertain).",
            corrective_advice=(
                OBSERVABILITY_ADVICE.get(attempt_kind, "Re-record so this criterion is clearly observable.")
                + f" Then the evaluator can check: {crit.observable_indicator.rstrip('.')}."
            ),
            expert_evidence_ref=expert,
            learner_evidence_ref=result.evidence_ref,
        )
    return FeedbackItem(
        criterion_id=cid,
        what_was_observed=result.observed_finding,
        what_differed=_differed(crit.observable_indicator, result.deviation_analysis),
        corrective_advice=f"{entry.drill_hint.rstrip('.')}. Why it matters: {entry.why_it_matters}",
        expert_evidence_ref=expert,
        learner_evidence_ref=result.evidence_ref,
    )


def _summary(handoff: TrackBHandoff, evaluation: Evaluation, first: Optional[Dict[str, Any]]) -> str:
    results = evaluation.criterion_results
    n_sat = sum(1 for r in results if r.status == CriterionStatus.SATISFIED)
    parts = [
        f"{n_sat} of {len(results)} criteria met "
        f"({_fmt(evaluation.total_score)} / {_fmt(handoff.rubric.max_possible_score)})."
    ]
    if first is not None:
        where = _where(first)
        parts.append(f"First divergence: {first['criterion_name']}{where} [{', '.join(first['source_claim_ids'])}].")
    if evaluation.uncertainty_flags:
        parts.append(f"Not assessable from this attempt: {', '.join(evaluation.uncertainty_flags)}.")
    parts.append("Passed." if evaluation.passed else "Not yet passed; retry the full task.")
    return " ".join(parts)


def build_feedback(
    *,
    feedback_id: str,
    handoff: TrackBHandoff,
    evaluation: Evaluation,
    first_divergence: Optional[Dict[str, Any]],
    attempt_kind: str,
    wording: Optional[WordingPass] = None,
) -> Feedback:
    first_cid = first_divergence["criterion_id"] if first_divergence else None
    ids = _ordered_ids(handoff, evaluation, first_cid)
    if ids:
        items = [_item(handoff, evaluation, cid, attempt_kind) for cid in ids]
        focus = ids
    else:
        # Every criterion satisfied: the contract needs >= 1 item, so give one factual
        # consolidation item for the first criterion in goal order.
        cid = min(handoff.criterion_map.criteria, key=lambda c: (handoff.criterion_map.criteria[c].order_index, c))
        result = next(r for r in evaluation.criterion_results if r.criterion_id == cid)
        entry = handoff.criterion_map.criteria[cid]
        items = [
            FeedbackItem(
                criterion_id=cid,
                what_was_observed=result.observed_finding,
                what_differed="No difference from the expected indicator was detected.",
                corrective_advice=f"Repeat the full task to confirm it is consistent. Why it matters: {entry.why_it_matters}",
                expert_evidence_ref=handoff.expert_evidence(cid),
                learner_evidence_ref=result.evidence_ref,
            )
        ]
        focus = []
    template = Feedback(
        feedback_id=feedback_id,
        evaluation_id=evaluation.evaluation_id,
        attempt_id=evaluation.attempt_id,
        summary=_summary(handoff, evaluation, first_divergence),
        items=items,
        recommended_retry_focus=focus,
    )
    feedback = template
    if wording is not None:
        protected = {r.criterion_id for r in evaluation.criterion_results}
        for cid in ids:
            protected.update(handoff.criterion_map.criteria[cid].source_claim_ids)
        feedback = guard_wording(template, wording(template), protected)
    errors = validate_feedback_against_evaluation(feedback, evaluation)
    if errors:
        raise AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, "feedback failed evaluation validation", {"errors": errors})
    return feedback


# ---------------------------------------------------------------------------
# Wording guard
# ---------------------------------------------------------------------------

_NUM = re.compile(r"\d+(?:\.\d+)?")


def _texts(fb: Feedback) -> List[str]:
    out = [fb.summary]
    for it in fb.items:
        out += [it.what_was_observed, it.what_differed, it.corrective_advice]
    return out


def guard_wording(template: Feedback, candidate: Feedback, protected_ids: Set[str]) -> Feedback:
    """Accept ``candidate`` only if structure, ids, evidence and numbers are preserved."""
    if (
        candidate.feedback_id != template.feedback_id
        or candidate.evaluation_id != template.evaluation_id
        or candidate.attempt_id != template.attempt_id
        or candidate.recommended_retry_focus != template.recommended_retry_focus
        or [i.criterion_id for i in candidate.items] != [i.criterion_id for i in template.items]
        or [(i.expert_evidence_ref, i.learner_evidence_ref) for i in candidate.items]
        != [(i.expert_evidence_ref, i.learner_evidence_ref) for i in template.items]
    ):
        return template
    t_fields, c_fields = _texts(template), _texts(candidate)
    if set(_NUM.findall(" ".join(t_fields))) != set(_NUM.findall(" ".join(c_fields))):
        return template
    for t_field, c_field in zip(t_fields, c_fields):  # ids must stay in the same field
        for pid in protected_ids:
            if pid in t_field and pid not in c_field:
                return template
    return candidate
