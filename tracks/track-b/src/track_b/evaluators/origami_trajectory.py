"""Deterministic origami trajectory analysis (no model, no I/O).

Input: per-learner-frame labels (int state index, "transition", "off_path", "unclear") with
their times, and the goal's final state index k. Rules (docs/plans/evaluation-core.md §4.2):

- labels are mode-filtered (centered window 3, strict majority);
- a *stable* state run is >= ``min_run`` consecutive filtered frames with the same state;
- ``progress(t)`` = max stable state reached so far / k;
- violations: ``off_path`` for >= min_run consecutive frames, or a stable run that falls back
  >= ``regression_states`` below the max state reached (regression);
- order: a state first reached after a later state (it was skipped, then back-filled) is an
  out-of-order event placed at the jump where it was skipped;
- skipped states: a jump of more than one state. The skip is UNCERTAIN ("not visible") when the
  frames between the two stable runs contain ``unclear`` labels, a brief (unstable) sighting of
  the skipped state, or a spacing gap > ``sparse_factor`` x the median frame spacing;
  otherwise the state is missing. States after the last reached one are missing unless the
  video ends in unclear frames;
- final: the last stable state is k (the pairwise image check is added by the evaluator).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from statistics import median
from typing import Dict, List, Optional, Sequence, Tuple, Union

Label = Union[int, str]
NON_STATE = ("transition", "off_path", "unclear")

MIN_RUN = 2
REGRESSION_STATES = 2
SPARSE_FACTOR = 2.5
MODE_WINDOW = 3


def mode_filter(labels: Sequence[Label], window: int = MODE_WINDOW) -> List[Label]:
    """Centered majority filter; a label replaces the original only with a strict majority of
    the (edge-truncated) window."""
    half = window // 2
    out: List[Label] = []
    for i, orig in enumerate(labels):
        win = list(labels[max(0, i - half): i + half + 1])
        best, n = Counter(win).most_common(1)[0]
        out.append(best if n * 2 > len(win) else orig)
    return out


def runs_of(labels: Sequence[Label]) -> List[Tuple[Label, int, int]]:
    out: List[Tuple[Label, int, int]] = []
    i = 0
    while i < len(labels):
        j = i
        while j + 1 < len(labels) and labels[j + 1] == labels[i]:
            j += 1
        out.append((labels[i], i, j))
        i = j + 1
    return out


@dataclass
class TrajEvent:
    kind: str                     # off_path | regression | out_of_order | missing_state
    metric: str                   # off_path_events | order_violations | missing_states
    position: float               # learner time (s) where the divergence happens
    t_start: float
    t_end: float
    frame_index: int
    expected_state: Optional[int]
    detail: str


@dataclass
class Trajectory:
    times: List[float]
    raw: List[Label]
    filtered: List[Label]
    k: int
    stable_runs: List[Tuple[int, int, int]] = field(default_factory=list)   # (state, first idx, last idx)
    curve: List[Tuple[float, float]] = field(default_factory=list)
    first_reached: Dict[int, float] = field(default_factory=dict)
    events: List[TrajEvent] = field(default_factory=list)
    missing: List[int] = field(default_factory=list)
    uncertain_missing: List[Tuple[int, str]] = field(default_factory=list)
    order_violations: int = 0
    off_path_events: int = 0
    last_stable_state: Optional[int] = None
    keystep: Optional[float] = None
    keystep_reason: str = ""

    @property
    def final_reached(self) -> bool:
        return self.last_stable_state == self.k

    @property
    def progress(self) -> float:
        return self.curve[-1][1] if self.curve else 0.0


def analyze(
    times: Sequence[float],
    raw: Sequence[Label],
    k: int,
    key_state: Optional[int] = None,
    *,
    min_run: int = MIN_RUN,
    regression_states: int = REGRESSION_STATES,
    sparse_factor: float = SPARSE_FACTOR,
) -> Trajectory:
    if len(times) != len(raw):
        raise ValueError("times and labels differ in length")
    if k < 1:
        raise ValueError("k must be >= 1")
    for lab in raw:
        if isinstance(lab, bool) or not (isinstance(lab, int) and 0 <= lab <= k or lab in NON_STATE):
            raise ValueError(f"invalid label {lab!r}")
    times = [float(t) for t in times]
    raw = list(raw)
    filt = mode_filter(raw)
    tr = Trajectory(times=times, raw=raw, filtered=filt, k=k)
    n = len(times)
    if n == 0:
        tr.uncertain_missing = [(s, "no frames") for s in range(1, k + 1)]
        tr.keystep_reason = "no frames"
        return tr
    dts = [b - a for a, b in zip(times, times[1:])]
    med_dt = median(dts) if dts else 1.0

    all_runs = runs_of(filt)
    for lab, a, b in all_runs:
        if lab == "off_path" and b - a + 1 >= min_run:
            tr.events.append(TrajEvent("off_path", "off_path_events", times[a], times[a], times[b], a, None,
                                       f"paper matches no reference state for {b - a + 1} frames ({times[a]:.1f}-{times[b]:.1f} s)"))
    tr.stable_runs = [(int(lab), a, b) for lab, a, b in all_runs
                      if isinstance(lab, int) and b - a + 1 >= min_run]

    def gap_uncertain(s: int, lo: int, hi: int) -> Optional[str]:
        """Frames strictly between indices lo and hi (lo may be -1 = start of video)."""
        gap = range(lo + 1, hi)
        if any(raw[g] == "unclear" for g in gap):
            return "not visible: frames around the jump are unclear"
        if any(raw[g] == s for g in gap):
            return "seen only briefly (fewer than the stable-run minimum)"
        span = times[max(lo, 0): hi + 1]
        if len(span) >= 2 and max(b - a for a, b in zip(span, span[1:])) > sparse_factor * med_dt:
            return "not visible: frames around the jump are too sparse"
        if lo < 0 and hi == 0:
            return "not visible: the video starts after this state"
        return None

    max_state = -1
    prev_end = -1
    pending: Dict[int, Tuple[int, int, Optional[str]]] = {}   # skipped state -> (jump idx, prev end idx, uncertain reason)
    arrival: Dict[int, Tuple[int, int]] = {}                  # state -> (first idx, prev stable end idx)
    out_of_order: set = set()
    progress_at = [0.0] * n
    for s, a, b in tr.stable_runs:
        if s not in tr.first_reached:
            if s > max_state + 1:
                for m in range(max(max_state + 1, 1), s):
                    pending[m] = (a, prev_end, gap_uncertain(m, prev_end, a))
            elif s < max_state:
                if s in pending:
                    jump_idx, _, _ = pending.pop(s)
                    out_of_order.add(s)
                    tr.events.append(TrajEvent(
                        "out_of_order", "order_violations", times[jump_idx], times[jump_idx], times[a], jump_idx, s,
                        f"reached a later state at {times[jump_idx]:.1f} s before R{s}; R{s} reached only at {times[a]:.1f} s"))
                elif max_state - s >= regression_states:   # e.g. back to R0 that was never seen
                    tr.events.append(TrajEvent("regression", "off_path_events", times[a], times[a], times[b], a, max_state,
                                               f"fell back from R{max_state} to R{s} for {b - a + 1} frames"))
            tr.first_reached[s] = times[a]
            arrival[s] = (a, prev_end)
        elif max_state - s >= regression_states:
            tr.events.append(TrajEvent("regression", "off_path_events", times[a], times[a], times[b], a, max_state,
                                       f"fell back from R{max_state} to R{s} for {b - a + 1} frames"))
        max_state = max(max_state, s)
        for i in range(a, n):
            progress_at[i] = max(progress_at[i], max_state / k)
        prev_end = b
    tr.curve = [(times[i], round(progress_at[i], 4)) for i in range(n)]
    tr.last_stable_state = tr.stable_runs[-1][0] if tr.stable_runs else None

    for s in sorted(pending):
        jump_idx, lo, reason = pending[s]
        if reason:
            tr.uncertain_missing.append((s, reason))
        else:
            tr.missing.append(s)
            tr.events.append(TrajEvent("missing_state", "missing_states", times[jump_idx],
                                       times[max(lo, 0)], times[jump_idx], jump_idx, s,
                                       f"jumped past R{s} at {times[jump_idx]:.1f} s; R{s} never reached"))
    tail_unclear = (n >= min_run and all(lab == "unclear" for lab in raw[-min_run:])) or (
        not tr.stable_runs and sum(lab == "unclear" for lab in raw) * 2 >= n)
    for s in range(max(max_state + 1, 1), k + 1):
        if tail_unclear:
            tr.uncertain_missing.append((s, "not visible: the end of the video is unclear"))
        else:
            tr.missing.append(s)
            tr.events.append(TrajEvent("missing_state", "missing_states", times[-1], times[max(prev_end, 0)], times[-1],
                                       n - 1, s, f"attempt ends at R{max(max_state, 0)}; R{s} never reached"))
    tr.missing.sort()
    tr.order_violations = sum(e.kind == "out_of_order" for e in tr.events)
    tr.off_path_events = sum(e.kind in ("off_path", "regression") for e in tr.events)
    tr.events.sort(key=lambda e: (e.position, e.frame_index, e.expected_state if e.expected_state is not None else -1))

    if key_state is None:
        tr.keystep_reason = "goal has no key state"
    elif any(s == key_state for s, _ in tr.uncertain_missing):
        tr.keystep_reason = dict(tr.uncertain_missing)[key_state]
    elif key_state not in tr.first_reached:
        tr.keystep, tr.keystep_reason = 0.0, f"R{key_state} never reached"
    elif key_state in out_of_order or (key_state - 1) not in tr.first_reached or \
            tr.first_reached[key_state - 1] > tr.first_reached[key_state]:
        tr.keystep, tr.keystep_reason = 0.0, f"R{key_state} not reached from R{key_state - 1} in the demonstrated order"
    else:
        a, lo = arrival[key_state]
        t_lo = times[max(lo, 0)]
        bad = [e for e in tr.events if e.kind in ("off_path", "regression") and t_lo <= e.position <= times[a]]
        if bad:
            tr.keystep, tr.keystep_reason = 0.0, f"{bad[0].kind} at {bad[0].position:.1f} s on the way to R{key_state}"
        else:
            tr.keystep, tr.keystep_reason = 1.0, f"R{key_state} reached at {times[a]:.1f} s directly from R{key_state - 1}"
    return tr
