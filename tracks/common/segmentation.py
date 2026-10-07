"""Domain-agnostic visual-state segmentation and step alignment for any video.

Any procedure video (origami, drawing, cooking, repair ...) is a sequence of visual
STATES joined by transitions. Nothing here knows the domain:

* ``layout_features``: a tiny grey thumbnail per frame (where things are), fused with the
  frame's Gemini Embedding 2 vector (what things are). Persistent changes in either show up.
* ``segment_k``: optimal split of the frame sequence into exactly K contiguous segments
  (dynamic programming over all change points, O(K F^2)) minimising within-segment scatter.
  Frames with large pixel motion (hands moving) get a low weight. K is chosen to
  OVER-segment; a single vision call later groups segments into named stages, so the
  method needs no per-video threshold (scale-free).
* ``monotone_align``: assigns attempt frames to source steps along a non-decreasing path
  (skips allowed), which is how missing steps and early stops are found.

Pure numpy and deterministic for given embeddings, so it is unit-testable and replayable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

import numpy as np

MOTION_WEIGHT = 0.25         # weight of a high-motion (transition) frame in the state cost
THUMB_SIZE = (24, 14)
THUMB_WEIGHT = 0.5           # relative weight of the layout thumbnail vs the embedding (tuned on 2 videos)


@dataclass
class StateSegment:
    start: int                 # first frame index (inclusive)
    end: int                   # last frame index (inclusive)
    keyframe: int              # calm frame closest to the segment centroid
    calm_fraction: float       # share of low-motion frames
    cohesion: float            # mean cosine of the segment's frames to its centroid


def _unit(e: np.ndarray) -> np.ndarray:
    e = np.asarray(e, dtype=np.float64)
    n = np.linalg.norm(e, axis=1, keepdims=True)
    return e / np.maximum(n, 1e-9)


def motion_threshold(motion: Sequence[float]) -> float:
    m = np.asarray(motion[1:] if len(motion) > 1 else motion, dtype=np.float64)
    if m.size == 0:
        return float("inf")
    return float(max(0.01, 2.0 * np.median(m)))


def _weights(f: int, motion: Optional[Sequence[float]]) -> Tuple[np.ndarray, np.ndarray]:
    mot = np.zeros(f) if motion is None else np.asarray(motion, dtype=np.float64)
    calm = mot <= motion_threshold(mot)
    return np.where(calm, 1.0, MOTION_WEIGHT), calm


def layout_features(images, embeddings: Optional[np.ndarray] = None) -> np.ndarray:
    """Unit feature per frame: [embedding, THUMB_WEIGHT * centred grey thumbnail]."""
    th = []
    for im in images:
        a = np.asarray(im.convert("L").resize(THUMB_SIZE), dtype=np.float64)
        a = a - a.mean()
        th.append(a.ravel() / max(float(np.linalg.norm(a)), 1e-9))
    t = np.array(th)
    if embeddings is None or len(embeddings) != len(t):
        return _unit(t)
    return _unit(np.hstack([_unit(embeddings), THUMB_WEIGHT * t]))


def default_k(n_frames: int, max_segments: int = 16, min_len: int = 2) -> int:
    return max(1, min(max_segments, n_frames // max(min_len + 1, 1)))


def segment_k(features: np.ndarray, k: int, motion: Optional[Sequence[float]] = None,
              *, min_len: int = 2) -> List[StateSegment]:
    """Optimal split into exactly ``k`` contiguous segments (each >= min_len frames)."""
    e = _unit(features)
    f = len(e)
    if f == 0:
        return []
    w, calm = _weights(f, motion)
    k = max(1, min(k, f // max(min_len, 1)))
    pw = np.concatenate([[0.0], np.cumsum(w)])
    pe = np.vstack([np.zeros((1, e.shape[1])), np.cumsum(w[:, None] * e, axis=0)])

    def cost_to(j: int, i: np.ndarray) -> np.ndarray:   # scatter of frames i..j-1
        ws = pw[j] - pw[i]
        vs = pe[j] - pe[i]
        return ws - np.sum(vs * vs, axis=1) / np.maximum(ws, 1e-9)

    inf = np.inf
    best = np.full((k + 1, f + 1), inf)
    back = np.zeros((k + 1, f + 1), dtype=int)
    best[0, 0] = 0.0
    for m in range(1, k + 1):
        for j in range(m * min_len, f + 1):
            i = np.arange((m - 1) * min_len, j - min_len + 1)
            tot = best[m - 1, i] + cost_to(j, i)
            q = int(np.argmin(tot))
            best[m, j], back[m, j] = tot[q], i[q]
    bounds = [f]
    j = f
    for m in range(k, 0, -1):
        j = int(back[m, j])
        bounds.append(j)
    bounds = bounds[::-1]
    return [_finish(e, w, calm, bounds[q], bounds[q + 1] - 1) for q in range(k)]


def _centroid(e: np.ndarray, w: np.ndarray, a: int, b: int) -> np.ndarray:
    c = (w[a:b + 1, None] * e[a:b + 1]).sum(axis=0)
    return c / max(np.linalg.norm(c), 1e-9)


def _finish(e: np.ndarray, w: np.ndarray, calm: np.ndarray, a: int, b: int) -> StateSegment:
    c = _centroid(e, w, a, b)
    sims = e[a:b + 1] @ c
    idx = np.arange(a, b + 1)
    # Keyframe: closest to the centroid among calm frames (falls back to all frames).
    pool = idx[calm[a:b + 1]] if calm[a:b + 1].any() else idx
    key = int(pool[np.argmax(e[pool] @ c)])
    return StateSegment(
        start=a, end=b, keyframe=key,
        calm_fraction=round(float(calm[a:b + 1].mean()), 4),
        cohesion=round(float(sims.mean()), 4),
    )


def state_prototypes(embeddings: np.ndarray, segments: Sequence[StateSegment],
                     motion: Optional[Sequence[float]] = None) -> np.ndarray:
    """Unit centroid per segment (robust step representation for alignment)."""
    e = _unit(embeddings)
    w, _ = _weights(len(e), motion)
    return np.stack([_centroid(e, w, s.start, s.end) for s in segments]) if segments else np.zeros((0, e.shape[1]))


def monotone_align(sim: np.ndarray, *, off_score: float = 0.0) -> List[Optional[int]]:
    """Assign each attempt frame to a step index (non-decreasing) or None (off/transition).

    ``sim`` is (frames x steps) of centred similarity scores (positive = looks like the step).
    The path may skip steps (missing steps show up as never visited) but never goes back,
    so a learner who revisits an earlier state is NOT credited with order; order
    violations are detected separately by comparing per-step best matches.
    Maximises sum of sim along the path; a frame may be 'off' at score ``off_score``.
    """
    f, k = sim.shape
    if f == 0 or k == 0:
        return [None] * f
    neg = -1e18
    # state 0..k-1 = on step s; dp over (frame, current step) where "current" = last visited step.
    dp = np.full((f, k), neg)
    on = np.zeros((f, k), dtype=bool)
    back = np.zeros((f, k), dtype=int)
    for s in range(k):
        cand_on, cand_off = sim[0, s], off_score if s == 0 else neg
        dp[0, s] = max(cand_on, cand_off)
        on[0, s] = cand_on >= cand_off
    for t in range(1, f):
        run = np.maximum.accumulate(dp[t - 1])
        arg = np.zeros(k, dtype=int)
        cur = 0
        for s in range(k):
            if dp[t - 1, s] >= dp[t - 1, cur]:
                cur = s
            arg[s] = cur
        stay = dp[t - 1] + off_score            # off frame keeps the current step
        move = run + sim[t]                     # on step s, coming from any step <= s
        dp[t] = np.maximum(stay, move)
        on[t] = move >= stay
        back[t] = np.where(on[t], arg, np.arange(k))
    s = int(np.argmax(dp[-1]))
    out: List[Optional[int]] = [None] * f
    for t in range(f - 1, -1, -1):
        out[t] = s if on[t, s] else None
        s = int(back[t, s]) if t > 0 else s
    return out
