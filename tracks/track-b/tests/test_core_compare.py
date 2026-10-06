from tracks.common.schemas import CriterionResult, CriterionStatus as S, Evaluation, RubricCriterion, RubricDefinition

from track_b.compare import compare_attempts, criteria_improved, transition
from track_b.scoring import policy_score

RUBRIC = RubricDefinition(
    rubric_id="r", skill_id="s", title="t",
    criteria=[RubricCriterion(criterion_id=c, name=c, description="d", observable_indicator="i", weight=2)
              for c in ("A", "B", "C", "D", "E")],
)


def _ev(eid, statuses):
    results = [CriterionResult(criterion_id=c, status=st, score=policy_score(st, 2), observed_finding="f")
               for c, st in zip("ABCDE", statuses)]
    return Evaluation(evaluation_id=eid, attempt_id=eid, rubric_id="r", criterion_results=results,
                      total_score=sum(r.score for r in results))


BASE = _ev("b", [S.NOT_SATISFIED, S.SATISFIED, S.UNCERTAIN, S.PARTIALLY_SATISFIED, S.SATISFIED])
RETRY = _ev("r", [S.SATISFIED, S.PARTIALLY_SATISFIED, S.SATISFIED, S.PARTIALLY_SATISFIED, S.UNCERTAIN])


def test_transition_kinds():
    assert transition(S.UNCERTAIN, 0, S.UNCERTAIN, 0) == "unchanged"
    assert transition(S.UNCERTAIN, 0, S.NOT_SATISFIED, 0) == "observability_gain"


def test_compare_transitions_and_gains():
    first = {"criterion_id": "A"}
    out = compare_attempts(RUBRIC, BASE, RETRY, first, [[0, 0.1]], [[0, 0.9]], recommended_retry_focus=["A", "D"])
    assert out["transitions"] == {"A": "improved", "B": "regressed", "C": "observability_gain", "D": "unchanged",
                                  "E": "observability_loss"}
    assert out["targeted_change"] == {"criterion_id": "A", "before": "not_satisfied", "after": "satisfied",
                                      "changed": True, "improved": True}
    # A +2, B -1, D 0; C (+2) and E (-2) are observability-only
    assert out["skill_gain_excluding_observability"] == 1.0
    assert out["curves"] == {"baseline": [[0, 0.1]], "retry": [[0, 0.9]]}


def test_criteria_improved_excludes_uncertain_baseline():
    assert criteria_improved(RUBRIC, BASE, RETRY) == ["A"]


def test_no_first_divergence_targeted_change_is_empty():
    out = compare_attempts(RUBRIC, BASE, RETRY, None, [], [])
    assert out["targeted_change"]["criterion_id"] is None and out["targeted_change"]["changed"] is False
