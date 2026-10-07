"""LIS order metric for universal procedure attempts."""
import numpy as np

from track_b.evaluators.universal import order_violations


def _labels(seq, reps=3):
    return [s for s in seq for _ in range(reps)]


def test_in_order_is_zero():
    lab = _labels([0, 1, 2, 3])
    assert order_violations(lab, np.zeros((len(lab), 4)), [float(i) for i in range(len(lab))], 4) == 0


def test_swapped_pair_counts_one():
    lab = _labels([0, 2, 1, 3])
    assert order_violations(lab, np.zeros((len(lab), 4)), [float(i) for i in range(len(lab))], 4) == 1


def test_flicker_between_neighbours_is_tolerated():
    lab = [0, 0, 1, 0, 1, 1, 2, 2]
    assert order_violations(lab, np.zeros((len(lab), 3)), [float(i) for i in range(len(lab))], 3) == 0
