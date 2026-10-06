"""Pass-semantics regression (track-plan-review §7.2 P0): required criteria must be SATISFIED."""

import pytest

from tracks.common.schemas import CriterionStatus as S, EvaluatorType
from tracks.common.validator import validate_evaluation_against_rubric

from track_b.evaluate import build_evaluation
from track_b.handoff import load_handoff
from track_b.scoring import ScoredCriterion, policy_score

from core_fixtures import make_case


def _scored(handoff, statuses):
    out = {}
    for c in handoff.rubric.criteria:
        st = statuses[c.criterion_id]
        out[c.criterion_id] = ScoredCriterion(
            criterion_id=c.criterion_id, metric_id="m", status=st, score=policy_score(st, c.weight), value=None,
            finding=f"{c.criterion_id} finding", evidence=None, position=None,
            uncertain_reason="blurry" if st == S.UNCERTAIN else None,
        )
    return out


def _eval(handoff, statuses, model_assisted=False):
    return build_evaluation(evaluation_id="e1", attempt_id="a1", rubric=handoff.rubric,
                            scored=_scored(handoff, statuses), model_assisted=model_assisted, evaluated_at="t")


@pytest.mark.parametrize("required_status", [S.PARTIALLY_SATISFIED, S.UNCERTAIN, S.NOT_SATISFIED])
def test_required_not_satisfied_never_passes(tmp_path, required_status):
    h = load_handoff(make_case(tmp_path, passing_score=1.0))  # total easily above passing_score
    ev, warnings = _eval(h, {"CRIT-A": S.SATISFIED, "CRIT-B": required_status, "CRIT-C": S.SATISFIED})
    assert ev.passed is False
    assert validate_evaluation_against_rubric(ev, h.rubric) == []
    if required_status == S.UNCERTAIN:
        assert ev.uncertainty_flags == ["CRIT-B"]
        assert any(w.startswith("HUMAN_REVIEW_REQUIRED") and "CRIT-B" in w for w in warnings)
    else:
        assert not warnings


def test_optional_failure_can_still_pass_and_total_is_sum(tmp_path):
    h = load_handoff(make_case(tmp_path))
    ev, warnings = _eval(h, {"CRIT-A": S.SATISFIED, "CRIT-B": S.SATISFIED, "CRIT-C": S.UNCERTAIN})
    assert ev.passed is True and ev.total_score == 5 and warnings == []
    assert ev.evaluator_type == EvaluatorType.DETERMINISTIC
    assert [r.criterion_id for r in ev.criterion_results] == ["CRIT-A", "CRIT-B", "CRIT-C"]
    assert "Few pen lifts" in ev.criterion_results[2].deviation_analysis


def test_passing_score_gate(tmp_path):
    h = load_handoff(make_case(tmp_path, passing_score=6.0))
    ev, _ = _eval(h, {"CRIT-A": S.SATISFIED, "CRIT-B": S.SATISFIED, "CRIT-C": S.NOT_SATISFIED})
    assert ev.total_score == 5 and ev.passed is False


def test_model_assisted_when_runs_present(tmp_path):
    h = load_handoff(make_case(tmp_path))
    ev, _ = _eval(h, {"CRIT-A": S.SATISFIED, "CRIT-B": S.SATISFIED, "CRIT-C": S.SATISFIED}, model_assisted=True)
    assert ev.evaluator_type == EvaluatorType.MODEL_ASSISTED
