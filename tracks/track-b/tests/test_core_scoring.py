import pytest

from tracks.common.casedata import Band, ObserverBinding
from tracks.common.schemas import CriterionStatus as S

from track_b.scoring import PROCESS_NOT_OBSERVABLE, band_status, policy_score, score_criterion
from track_b.trajectory import MetricValue

HIGHER = ObserverBinding(metric="m", direction="higher_is_better",
                         bands=[Band(status="satisfied", min=0.9), Band(status="partially_satisfied", min=0.7)])
LOWER = ObserverBinding(metric="m", direction="lower_is_better", process=True,
                        bands=[Band(status="satisfied", max=0), Band(status="partially_satisfied", max=2)])


@pytest.mark.parametrize("value,status", [(0.95, S.SATISFIED), (0.9, S.SATISFIED), (0.89, S.PARTIALLY_SATISFIED),
                                          (0.7, S.PARTIALLY_SATISFIED), (0.69, S.NOT_SATISFIED)])
def test_higher_is_better_bands(value, status):
    assert band_status(HIGHER, value) == status


@pytest.mark.parametrize("value,status", [(0, S.SATISFIED), (1, S.PARTIALLY_SATISFIED), (2, S.PARTIALLY_SATISFIED),
                                          (3, S.NOT_SATISFIED)])
def test_lower_is_better_bands(value, status):
    assert band_status(LOWER, value) == status


def test_otherwise_status_is_configurable():
    b = ObserverBinding(metric="m", direction="higher_is_better", bands=[Band(status="satisfied", min=1)],
                        otherwise="uncertain")
    assert band_status(b, 0.2) == S.UNCERTAIN


def test_policy_fractions_and_rounding():
    assert policy_score(S.SATISFIED, 3) == 3
    assert policy_score(S.PARTIALLY_SATISFIED, 3) == 1.5
    assert policy_score(S.NOT_SATISFIED, 3) == 0
    assert policy_score(S.UNCERTAIN, 3) == 0
    assert policy_score(S.PARTIALLY_SATISFIED, 0.33333) == 0.1667


def test_none_value_is_uncertain_with_reason():
    s = score_criterion("C", 2, HIGHER, MetricValue(value=None, finding="", uncertain_reason="blurry"), True)
    assert s.status == S.UNCERTAIN and s.score == 0 and s.uncertain_reason == "blurry"
    assert "blurry" in s.finding


def test_missing_metric_is_uncertain():
    s = score_criterion("C", 2, HIGHER, None, True)
    assert s.status == S.UNCERTAIN and "not produced" in s.uncertain_reason


def test_process_criterion_uncertain_when_process_not_observable():
    m = MetricValue(value=0, finding="0 lifts")
    s = score_criterion("C", 1, LOWER, m, process_observable=False)
    assert s.status == S.UNCERTAIN and s.uncertain_reason == PROCESS_NOT_OBSERVABLE and s.score == 0
    assert score_criterion("C", 1, LOWER, m, process_observable=True).status == S.SATISFIED


def test_final_state_criterion_still_scored_without_process():
    s = score_criterion("C", 3, HIGHER, MetricValue(value=0.8, finding="80%"), process_observable=False)
    assert s.status == S.PARTIALLY_SATISFIED and s.score == 1.5
