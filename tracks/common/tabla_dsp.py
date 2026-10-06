"""Deterministic tabla DSP shared by Track A (goal model) and Track B (learner evaluation).

numpy only. Everything here is auditable arithmetic on onset lists produced by
``tracks.common.onsets``; no model calls. This is a shared utility, not a contract.

Vocabulary used throughout:

stroke pulse   the finest regular inter-onset interval: every observed stroke lies
               (approximately) on an integer multiple of it. This is what the audio
               establishes directly. It is NOT asserted to be the matra (beat) of a taal.
grid index     integer pulse slot of each stroke (``k``), assigned from IOIs.
beat           a counting convention of ``beat_pulses`` pulses (see ``beat_grouping``);
               reported for display, never used for scoring (tempo error is level-free).
cycle          lag (in pulses) of the strongest repetition of the bass pattern.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np
from pydantic import BaseModel

ALGO_VERSION = "tabla_dsp_v1"

# Match-cost weights for the stroke alignment (documented in evaluation-core §5.2).
W_TIMING = 1.0        # (deviation / pulse)^2
W_BASS = 0.5          # bass flag mismatch
W_STRENGTH = 0.2      # |strength difference| (strengths are 0..1)
GAP_COST = 0.5        # cost of leaving a goal stroke unmatched (missing) or a learner stroke unmatched (extra)


# ---------------------------------------------------------------------------
# Pulse (stroke grid) estimation
# ---------------------------------------------------------------------------


def _pulse_score(iois: np.ndarray, period: float, tol: float = 0.12) -> float:
    n = np.maximum(1, np.round(iois / period))
    err = np.abs(iois - n * period) / period
    return float(np.mean(np.exp(-((err / tol) ** 2))))


def estimate_pulse(
    times: Sequence[float],
    lo: float = 0.08,
    hi: float = 1.0,
    step: float = 0.0005,
    tie: float = 0.95,
    prefer: Optional[float] = None,
) -> Tuple[float, float]:
    """Return ``(pulse_sec, fit_score)``.

    Every candidate period in [lo, hi] is scored by how well all IOIs fall on integer
    multiples of it. Integer sub-divisions of the true pulse score equally well, so the
    *largest* period scoring within ``tie`` of the best is chosen (the coarsest grid that
    still explains every stroke). With ``prefer`` set (learner side), the candidate within
    the tie set closest to ``prefer`` is chosen instead. The result is refined by a
    least-squares fit of times against cumulative grid indices.
    """
    t = np.asarray(times, dtype=float)
    if t.size < 3:
        raise ValueError("need at least 3 onsets to estimate a pulse")
    iois = np.diff(t)
    iois = iois[(iois > 0.5 * lo) & (iois < 4.0 * hi)]
    if iois.size < 2:
        raise ValueError("not enough usable inter-onset intervals")
    cands = np.arange(lo, hi + step / 2, step)
    scores = np.array([_pulse_score(iois, p) for p in cands])
    best = float(scores.max())
    ok = np.where(scores >= tie * best)[0]
    if prefer is None:
        p0 = float(cands[ok[-1]])
    else:
        p0 = float(cands[ok[np.argmin(np.abs(cands[ok] - prefer))]])
    k = grid_indices(t, p0)
    p, _ = fit_line(k.astype(float), t)
    return float(p), round(best, 4)


def grid_indices(times: Sequence[float], pulse: float) -> np.ndarray:
    """Integer pulse slot of each onset (first onset = 0) from rounded IOIs."""
    t = np.asarray(times, dtype=float)
    if t.size == 0:
        return np.zeros(0, dtype=int)
    steps = np.maximum(1, np.round(np.diff(t) / pulse)).astype(int)
    return np.concatenate([[0], np.cumsum(steps)])


def fit_line(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Least-squares ``y = slope * x + intercept``; returns (slope, intercept)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 2 or float(np.ptp(x)) == 0.0:
        return 1.0, float(np.mean(y - x)) if x.size else 0.0
    A = np.vstack([x, np.ones_like(x)]).T
    slope, intercept = np.linalg.lstsq(A, y, rcond=None)[0]
    return float(slope), float(intercept)


def robust_fit_line(x: np.ndarray, y: np.ndarray, iters: int = 3, k: float = 3.0) -> Tuple[float, float]:
    """Iteratively trimmed least squares (drops points beyond k * MAD, min 3 kept)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    keep = np.ones(x.size, dtype=bool)
    slope, icpt = fit_line(x, y)
    for _ in range(iters):
        r = y - (slope * x + icpt)
        mad = float(np.median(np.abs(r - np.median(r[keep])))) + 1e-6
        new_keep = np.abs(r) <= k * 1.4826 * mad + 0.01
        if new_keep.sum() < 3 or np.array_equal(new_keep, keep):
            break
        keep = new_keep
        slope, icpt = fit_line(x[keep], y[keep])
    return slope, icpt


def pulse_cv(times: Sequence[float], pulse: float) -> Optional[float]:
    """Stability: coefficient of variation of IOIs normalised by their pulse multiple.

    Raw IOI CV is meaningless for tabla (a theka mixes 1-, 2- and 3-pulse gaps), so each
    IOI is divided by its integer pulse count before computing std/mean.
    """
    t = np.asarray(times, dtype=float)
    if t.size < 3:
        return None
    iois = np.diff(t)
    n = np.maximum(1, np.round(iois / pulse))
    per = iois / n
    m = float(per.mean())
    return float(per.std() / m) if m > 0 else None


def beat_grouping(pulse: float, min_beat_sec: float = 0.3) -> int:
    """Counting convention: the smallest k in (1, 2, 4) with k * pulse >= min_beat_sec.

    This is a display convention (<= 200 counted beats per minute), not an observation
    of the taal's matra. Tempo error is computed at pulse level and is unaffected.
    """
    for k in (1, 2, 4):
        if k * pulse >= min_beat_sec:
            return k
    return 4


# ---------------------------------------------------------------------------
# Cycle (repetition of the bass pattern)
# ---------------------------------------------------------------------------


@dataclass
class CycleEstimate:
    length_pulses: Optional[int]
    confidence: float                   # normalised autocorrelation at the chosen lag (0..1)
    autocorr: List[Tuple[int, float]] = field(default_factory=list)
    reason: Optional[str] = None


def estimate_cycle(
    grid_idx: Sequence[int],
    bass: Sequence[bool],
    strength: Optional[Sequence[float]] = None,
    min_lag: int = 4,
    max_lag: int = 64,
    min_conf: float = 0.3,
    tie: float = 0.85,
) -> CycleEstimate:
    """Cycle length (pulses) from the autocorrelation of the bass pattern on the pulse grid.

    Slot series: +1 bass stroke, -1 non-bass stroke (weighted by strength if given), 0 empty.
    The smallest lag whose normalised autocorrelation is within ``tie`` of the best lag is
    chosen (multiples of the cycle correlate equally well). At least two full cycles must
    fit in the series. Below ``min_conf`` the cycle is reported as not established.
    """
    k = np.asarray(grid_idx, dtype=int)
    if k.size < 8:
        return CycleEstimate(None, 0.0, reason="too few strokes")
    n = int(k[-1]) + 1
    s = np.zeros(n)
    w = np.ones(k.size) if strength is None else 0.5 + np.asarray(strength, dtype=float)
    for i, slot in enumerate(k):
        s[slot] = (1.0 if bass[i] else -1.0) * w[i]
    s = s - s.mean()
    denom = float(np.dot(s, s))
    hi = min(max_lag, n // 2)
    if denom <= 0 or hi < min_lag:
        return CycleEstimate(None, 0.0, reason="series shorter than two cycles")
    acs = []
    for lag in range(min_lag, hi + 1):
        # unbiased normalisation by overlap length
        a = float(np.dot(s[:-lag], s[lag:])) / (n - lag) * n / denom
        acs.append((lag, round(a, 4)))
    best = max(a for _, a in acs)
    if best < min_conf:
        return CycleEstimate(None, round(best, 4), acs, reason=f"no repetition above {min_conf}")
    for lag, a in acs:
        if a >= tie * best:
            return CycleEstimate(lag, round(a, 4), acs)
    return CycleEstimate(None, round(best, 4), acs, reason="no lag selected")  # pragma: no cover


# ---------------------------------------------------------------------------
# Bass threshold adaptation (learner side)
# ---------------------------------------------------------------------------


def two_means_centres(values: Sequence[float]) -> Tuple[float, float, float]:
    """Return (lo_centre, hi_centre, threshold) of a deterministic 1-D 2-means split."""
    v = np.sort(np.asarray(values, dtype=float))
    if v.size < 2 or v[0] == v[-1]:
        c = float(v[0]) if v.size else 0.0
        return c, c, c
    lo, hi = float(v[0]), float(v[-1])
    for _ in range(100):
        mid = (lo + hi) / 2
        a, b = v[v <= mid], v[v > mid]
        if a.size == 0 or b.size == 0:
            break
        nlo, nhi = float(a.mean()), float(b.mean())
        if abs(nlo - lo) < 1e-9 and abs(nhi - hi) < 1e-9:
            break
        lo, hi = nlo, nhi
    return lo, hi, (lo + hi) / 2


@dataclass
class BassThreshold:
    value: float
    adapted: bool
    rule: str


def learner_bass_threshold(
    learner_low: Sequence[float],
    goal_threshold: float,
    goal_centres: Tuple[float, float],
    min_ashman_d: float = 2.0,
    min_minority: float = 0.15,
    min_shift_frac: float = 0.25,
) -> BassThreshold:
    """Use the goal's bass threshold unless the learner recording is clearly at another level.

    Rule (deterministic): split the learner's low-band ratios with 2-means. Adapt to the
    learner's own threshold only if (a) the learner distribution is clearly bimodal
    (Ashman's D >= 2 and the minority cluster holds >= 15 % of strokes) and (b) BOTH learner
    cluster centres are shifted in the same direction from the goal centres by more than
    25 % of the goal's centre gap (a different drum, room or microphone). Otherwise the goal
    threshold is kept, so a learner who omits bass is judged against the source's level.
    """
    v = np.asarray(learner_low, dtype=float)
    keep = BassThreshold(goal_threshold, False, "goal threshold (learner levels compatible or not bimodal)")
    if v.size < 6:
        return keep
    lo, hi, thr = two_means_centres(v)
    a, b = v[v <= thr], v[v > thr]
    if a.size == 0 or b.size == 0:
        return keep
    d = np.sqrt(2.0) * abs(hi - lo) / np.sqrt(float(a.var()) + float(b.var()) + 1e-12)
    minority = min(a.size, b.size) / v.size
    g_lo, g_hi = goal_centres
    gap = max(g_hi - g_lo, 1e-6)
    d_lo, d_hi = lo - g_lo, hi - g_hi
    same_dir = np.sign(d_lo) == np.sign(d_hi) and d_lo != 0
    shifted = min(abs(d_lo), abs(d_hi)) > min_shift_frac * gap
    if d >= min_ashman_d and minority >= min_minority and same_dir and shifted:
        return BassThreshold(
            float(thr), True,
            f"learner threshold (bimodal D={d:.2f}, centres shifted {d_lo:+.3f}/{d_hi:+.3f} vs goal gap {gap:.3f})",
        )
    return keep


# ---------------------------------------------------------------------------
# Alignment (DTW with skip penalties)
# ---------------------------------------------------------------------------


@dataclass
class Stroke:
    t: float
    strength: float
    bass: bool


@dataclass
class Alignment:
    pairs: List[Tuple[int, int]]          # (goal index, learner index)
    missing: List[int]                    # goal indices without a learner stroke
    extra: List[int]                      # learner indices inside the goal span without a goal stroke
    outside: List[int]                    # learner indices before/after the goal span (not penalised)
    cost: float


def align_strokes(
    goal: Sequence[Stroke],
    learner_mapped: Sequence[Stroke],
    pulse: float,
    gap: float = GAP_COST,
) -> Alignment:
    """Monotone alignment of learner strokes (times already mapped into goal time) to goal strokes.

    Dynamic time warping over the two stroke sequences where, besides matching, either side
    may be skipped at cost ``gap`` (missing goal stroke / extra learner stroke). Match cost
    = W_TIMING*(dt/pulse)^2 + W_BASS*[bass differs] + W_STRENGTH*|strength difference|.
    Learner strokes before the first or after the last goal stroke (beyond half a pulse) are
    free (``outside``): recording slightly longer than the segment is not an error.
    """
    G, L = len(goal), len(learner_mapped)
    gt = np.array([s.t for s in goal]) if G else np.zeros(0)
    lt = np.array([s.t for s in learner_mapped]) if L else np.zeros(0)
    if G == 0:
        return Alignment([], [], [], list(range(L)), 0.0)
    lo_edge, hi_edge = gt[0] - 0.5 * pulse, gt[-1] + 0.5 * pulse
    free = (lt < lo_edge) | (lt > hi_edge)

    def mcost(i: int, j: int) -> float:
        g, l = goal[i], learner_mapped[j]
        dt = (l.t - g.t) / pulse
        return W_TIMING * dt * dt + W_BASS * float(g.bass != l.bass) + W_STRENGTH * abs(g.strength - l.strength)

    INF = 1e18
    D = np.full((G + 1, L + 1), INF)
    B = np.zeros((G + 1, L + 1), dtype=np.int8)  # 1 match, 2 skip goal (missing), 3 skip learner (extra)
    D[0, 0] = 0.0
    for j in range(1, L + 1):
        D[0, j] = D[0, j - 1] + (0.0 if free[j - 1] else gap)
        B[0, j] = 3
    for i in range(1, G + 1):
        D[i, 0] = D[i - 1, 0] + gap
        B[i, 0] = 2
        for j in range(1, L + 1):
            best, arg = D[i - 1, j - 1] + mcost(i - 1, j - 1), 1
            c = D[i - 1, j] + gap
            if c < best:
                best, arg = c, 2
            c = D[i, j - 1] + (0.0 if free[j - 1] else gap)
            if c < best:
                best, arg = c, 3
            D[i, j], B[i, j] = best, arg
    pairs: List[Tuple[int, int]] = []
    missing: List[int] = []
    extra: List[int] = []
    outside: List[int] = []
    i, j = G, L
    while i > 0 or j > 0:
        b = B[i, j]
        if b == 1:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif b == 2:
            missing.append(i - 1)
            i -= 1
        else:
            (outside if free[j - 1] else extra).append(j - 1)
            j -= 1
    pairs.reverse()
    missing.reverse()
    extra.reverse()
    outside.reverse()
    return Alignment(pairs, missing, extra, outside, float(D[G, L]))


def initial_fit(
    goal_t: Sequence[float],
    learner_t: Sequence[float],
    pulse: float,
    scales: Sequence[float],
    max_shift: float,
    goal_bass: Optional[Sequence[bool]] = None,
    learner_bass: Optional[Sequence[bool]] = None,
    shift_penalty: float = 0.25,
) -> Tuple[float, float]:
    """Coarse ``learner_t ~= a + b * goal_t`` maximising onset coincidence; deterministic grid search.

    For every time scale ``b`` in ``scales`` and offset on a grid of pulse/20 within ``max_shift``
    of aligning the first onsets, each goal onset scores a Gaussian (sigma = 0.15 pulse, in goal
    time) of the distance to its nearest mapped learner onset, weighted 1.0 if the bass flags agree
    and 0.3 otherwise. A dense, even stroke grid coincides with itself at every whole-pulse shift,
    so the bass pattern and a prior of ``shift_penalty`` per pulse of departure from "first strokes
    aligned" disambiguate. Ties go to the scale closest to 1.
    """
    g = np.asarray(goal_t, dtype=float)
    l = np.asarray(learner_t, dtype=float)
    if g.size == 0 or l.size == 0:
        return 0.0, 1.0
    gb = np.asarray(goal_bass if goal_bass is not None else np.zeros(g.size, bool), dtype=bool)
    lb = np.asarray(learner_bass if learner_bass is not None else np.zeros(l.size, bool), dtype=bool)
    sigma = 0.15 * pulse
    step = pulse / 20
    best = (-1e18, 0.0, 1.0)
    for b in sorted(scales, key=lambda s: (abs(s - 1.0), s)):
        m = l / b
        base = float(m[0] - g[0])
        shifts = np.arange(base - max_shift, base + max_shift + step / 2, step)
        d = np.abs(m[None, None, :] - shifts[:, None, None] - g[None, :, None])   # (shift, goal, learner)
        nearest = d.argmin(axis=2)
        dmin = np.take_along_axis(d, nearest[..., None], axis=2)[..., 0]
        agree = np.where(lb[nearest] == gb[None, :], 1.0, 0.3)
        v = (np.exp(-0.5 * (dmin / sigma) ** 2) * agree).sum(axis=1) - shift_penalty * np.abs(shifts - base) / pulse
        k = int(np.argmax(v))
        if float(v[k]) > best[0] + 1e-9:
            best = (float(v[k]), float(shifts[k]) * b, float(b))
    return best[1], best[2]


def levenshtein(a: Sequence[str], b: Sequence[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


# ---------------------------------------------------------------------------
# Audio helpers and the (optional) bol-naming DTO
# ---------------------------------------------------------------------------


def wav_bytes(x: np.ndarray, sample_rate: int) -> bytes:
    """Mono 16-bit PCM WAV bytes (for an AudioPart)."""
    import io
    import wave

    pcm = (np.clip(np.asarray(x, dtype=np.float32), -1.0, 1.0) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def clipping_fraction(x: np.ndarray, level: float = 0.99) -> float:
    x = np.asarray(x, dtype=np.float32)
    return float(np.mean(np.abs(x) >= level)) if x.size else 0.0


def match_bols(
    onset_times: Sequence[float], labelled: Sequence[Tuple[float, str]], tol: float = 0.08
) -> Tuple[List[Optional[str]], int]:
    """Assign model bol labels to detected onsets (nearest within ``tol`` s). Returns (labels, unmatched)."""
    labels: List[Optional[str]] = [None] * len(onset_times)
    unmatched = 0
    ot = np.asarray(onset_times, dtype=float)
    for t, bol in labelled:
        if ot.size == 0:
            unmatched += 1
            continue
        i = int(np.argmin(np.abs(ot - t)))
        if abs(ot[i] - t) <= tol and labels[i] is None:
            labels[i] = bol.strip()
        else:
            unmatched += 1
    return labels, unmatched


class GoalAnalysisError(ValueError):
    """The audio does not support a goal model (too few strokes or no stroke pulse)."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind  # "too_few_strokes" | "no_pulse"


def analyze_goal_audio(
    x: np.ndarray,
    sample_rate: int,
    timing_ms: float = 50.0,
    tempo_pct: float = 5.0,
    min_onsets: int = 8,
) -> dict:
    """Deterministic analysis of an expert window -> TablaGoal payload fields (minus window/bols).

    Onsets (spectral flux), bass flag by 2-means on the low-band ratios, stroke pulse and grid,
    cycle, beat grouping. Raises GoalAnalysisError if the audio cannot support a goal.
    """
    from tracks.common.onsets import OnsetParams, detect_onsets

    params = OnsetParams()
    on = detect_onsets(x, sample_rate, params)
    if len(on) < min_onsets:
        raise GoalAnalysisError("too_few_strokes", f"only {len(on)} detectable strokes (need >= {min_onsets})")
    t = np.asarray(on.times_sec, dtype=float)
    lo_c, hi_c, thr = two_means_centres(on.low_ratio)
    bass = [r > thr for r in on.low_ratio]
    try:
        pulse, score = estimate_pulse(t)
    except ValueError as exc:
        raise GoalAnalysisError("no_pulse", f"no stroke pulse: {exc}") from exc
    k = grid_indices(t, pulse)
    slope, icpt = robust_fit_line(k.astype(float), t)
    resid_ms = np.abs(t - (icpt + slope * k)) * 1000.0
    cyc = estimate_cycle(k, bass, on.strength)
    beat_k = beat_grouping(slope)
    beat_period = beat_k * slope
    n_slots = int(k[-1]) + 1
    slot_of = {int(s): i for i, s in enumerate(k)}
    grid = [
        {"index": s, "t": round(icpt + slope * s, 4), "stroke": slot_of.get(s),
         "bass": bass[slot_of[s]] if s in slot_of else None}
        for s in range(n_slots)
    ]
    beats = []
    for b in range((n_slots + beat_k - 1) // beat_k):
        slots = range(b * beat_k, min((b + 1) * beat_k, n_slots))
        beats.append({"index": b, "t": round(icpt + slope * b * beat_k, 4),
                      "bass": any(bass[slot_of[s]] for s in slots if s in slot_of)})
    cv = pulse_cv(t, slope)
    return {
        "sample_rate": sample_rate,
        "duration_sec": round(len(x) / sample_rate, 3),
        "onset_params": params.__dict__.copy(),
        "onsets": [
            {"t": float(t[i]), "strength": float(min(1.0, on.strength[i])), "low_ratio": float(on.low_ratio[i]),
             "bass": bool(bass[i]), "grid_index": int(k[i])}
            for i in range(len(t))
        ],
        "bass_threshold": round(float(thr), 4),
        "bass_centres": [round(float(lo_c), 4), round(float(hi_c), 4)],
        "bass_fraction": round(float(np.mean(bass)), 4),
        "stroke_pulse_sec": round(float(slope), 4),
        "pulse_fit_score": score,
        "grid_residual_median_ms": round(float(np.median(resid_ms)), 1),
        "beat_pulses": beat_k,
        "beat_rule": "beat = smallest k in (1,2,4) pulses with k*pulse >= 0.3 s (counting convention, not an observed matra)",
        "beat_period_sec": round(float(beat_period), 4),
        "tempo_bpm": round(60.0 / float(beat_period), 1),
        "strokes_per_min": round(60.0 / float(slope), 1),
        "ioi_cv": None if cv is None else round(cv, 4),
        "cycle_length_pulses": cyc.length_pulses,
        "cycle_length_beats": None if cyc.length_pulses is None else round(cyc.length_pulses / beat_k, 2),
        "cycle_confidence": cyc.confidence,
        "cycle_note": cyc.reason,
        "grid": grid,
        "beats": beats,
        "tolerances": {"timing_ms": timing_ms, "tempo_pct": tempo_pct},
        "bols": None,
        "bols_status": "audio_model_disabled",
    }


class BolItem(BaseModel):
    t: float
    bol: str


class BolsDTO(BaseModel):
    """Model output for prompts/tabla_bols_v1 (validated by the gateway)."""

    bols: List[BolItem]
    notes: str = ""
