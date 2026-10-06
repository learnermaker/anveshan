"""Deterministic alignment helpers for the universal procedure evaluator.

Provides frame labelling (cosine nearest-step) and Needleman-Wunsch sequence
alignment for step coverage and order-violation counting.

No model calls. No I/O.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Union

import numpy as np

Label = Union[int, str]   # int step index (0-based) | "transition" | "off"


def label_frames(
    frame_vecs: np.ndarray,       # (F, D) unit float32 — one row per attempt frame
    step_vecs: np.ndarray,        # (N, D) unit float32 — one row per source step keyframe
    margin: float = 0.03,         # if best - second_best < margin -> "transition"
    floor: float = 0.60,          # if best < floor -> "off"
) -> List[Label]:
    """For each attempt frame return its nearest step index or a special label.

    Algorithm:
    1. cosine_similarity = frame_vecs @ step_vecs.T  (already unit vectors)
    2. best  = argmax per row
    3. second_best = max of remaining columns per row
    4. if best_sim < floor  -> "off"
       elif best_sim - second_best < margin -> "transition"
       else -> best (int)
    """
    if frame_vecs.shape[0] == 0 or step_vecs.shape[0] == 0:
        return []
    sims = frame_vecs @ step_vecs.T          # (F, N)
    n = step_vecs.shape[0]
    labels: List[Label] = []
    for row in sims:
        best_idx = int(np.argmax(row))
        best_sim = float(row[best_idx])
        if best_sim < floor:
            labels.append("off")
            continue
        if n == 1:
            labels.append(best_idx)
            continue
        mask = np.ones(n, dtype=bool)
        mask[best_idx] = False
        second_sim = float(row[mask].max())
        if best_sim - second_sim < margin:
            labels.append("transition")
        else:
            labels.append(best_idx)
    return labels


def mode_filter(labels: List[Label], window: int = 3) -> List[Label]:
    """Centered majority filter; replaces a label only when majority in window."""
    from collections import Counter

    half = window // 2
    out: List[Label] = []
    for i, orig in enumerate(labels):
        win = labels[max(0, i - half): i + half + 1]
        best, cnt = Counter(win).most_common(1)[0]
        out.append(best if cnt * 2 > len(win) else orig)
    return out


# ---------------------------------------------------------------------------
# Needleman–Wunsch alignment of observed step sequence vs expected
# ---------------------------------------------------------------------------

_GAP_PENALTY = -1
_MATCH_SCORE = 2
_MISMATCH_SCORE = -1


def needleman_wunsch(
    observed: List[int],      # step indices actually seen (0-based), in order
    expected: List[int],      # goal step indices in expected order (0-based)
) -> Dict[str, object]:
    """Global alignment of observed to expected step sequence.

    Returns:
        matched:    number of steps in observed that align to their expected slot
        missing:    number of expected steps with no aligned observed step (gap in observed)
        extra:      number of observed steps that are gaps in the expected (extra steps)
        violations: number of observed steps that are out of order relative to their expected
                    positions (counted from the alignment; a step appearing before its expected
                    position when a later step was already seen)
        alignment:  list of (obs_idx_or_None, exp_idx_or_None) pairs
    """
    n_obs = len(observed)
    n_exp = len(expected)
    if n_obs == 0 and n_exp == 0:
        return {"matched": 0, "missing": 0, "extra": 0, "violations": 0, "alignment": []}
    if n_obs == 0:
        return {"matched": 0, "missing": n_exp, "extra": 0, "violations": 0,
                "alignment": [(None, e) for e in expected]}
    if n_exp == 0:
        return {"matched": 0, "missing": 0, "extra": n_obs, "violations": 0,
                "alignment": [(o, None) for o in observed]}

    # Build scoring matrix
    dp = np.full((n_obs + 1, n_exp + 1), 0, dtype=np.int32)
    for i in range(n_obs + 1):
        dp[i, 0] = i * _GAP_PENALTY
    for j in range(n_exp + 1):
        dp[0, j] = j * _GAP_PENALTY

    for i in range(1, n_obs + 1):
        for j in range(1, n_exp + 1):
            score = _MATCH_SCORE if observed[i - 1] == expected[j - 1] else _MISMATCH_SCORE
            dp[i, j] = max(
                dp[i - 1, j - 1] + score,
                dp[i - 1, j] + _GAP_PENALTY,
                dp[i, j - 1] + _GAP_PENALTY,
            )

    # Traceback
    alignment: List[Tuple[Optional[int], Optional[int]]] = []
    i, j = n_obs, n_exp
    while i > 0 or j > 0:
        if i == 0:
            alignment.append((None, expected[j - 1]))
            j -= 1
        elif j == 0:
            alignment.append((observed[i - 1], None))
            i -= 1
        else:
            score = _MATCH_SCORE if observed[i - 1] == expected[j - 1] else _MISMATCH_SCORE
            if dp[i, j] == dp[i - 1, j - 1] + score:
                alignment.append((observed[i - 1], expected[j - 1]))
                i -= 1
                j -= 1
            elif dp[i, j] == dp[i - 1, j] + _GAP_PENALTY:
                alignment.append((observed[i - 1], None))
                i -= 1
            else:
                alignment.append((None, expected[j - 1]))
                j -= 1
    alignment.reverse()

    # Count stats
    matched = sum(1 for o, e in alignment if o is not None and e is not None and o == e)
    missing = sum(1 for o, e in alignment if o is None and e is not None)
    extra = sum(1 for o, e in alignment if o is not None and e is None)

    # Order violations: count positions in observed_step_sequence where the step index
    # is less than the maximum step index seen so far — i.e., a "backward" move.
    # This matches the origami_trajectory definition of out_of_order events.
    violations = 0
    max_seen = -1
    for step_idx in observed:
        if step_idx < max_seen:
            violations += 1
        else:
            max_seen = step_idx

    return {
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "violations": violations,
        "alignment": alignment,
    }
