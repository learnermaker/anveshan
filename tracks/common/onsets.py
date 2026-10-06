"""Deterministic audio onset detection shared by Track A (goal model) and Track B (learner).

Spectral-flux onsets with an adaptive moving-median threshold. numpy only.
Each onset carries strength and a low-band energy ratio used as a bass
(tabla bayan) proxy. This is a shared utility, not a contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


@dataclass(frozen=True)
class OnsetParams:
    n_fft: int = 1024
    hop: int = 256
    median_window_sec: float = 0.5
    delta: float = 0.08
    min_gap_sec: float = 0.09
    low_band_hz: float = 250.0
    feature_window_sec: float = 0.08


@dataclass
class Onsets:
    sample_rate: int
    times_sec: List[float] = field(default_factory=list)
    strength: List[float] = field(default_factory=list)   # normalised flux at the onset (0..1)
    low_ratio: List[float] = field(default_factory=list)  # energy < low_band_hz / total, in feature window

    def __len__(self) -> int:
        return len(self.times_sec)


def _spectrogram(x: np.ndarray, n_fft: int, hop: int) -> np.ndarray:
    if len(x) < n_fft:
        x = np.pad(x, (0, n_fft - len(x)))
    frames = sliding_window_view(x, n_fft)[::hop] * np.hanning(n_fft)
    return np.abs(np.fft.rfft(frames, axis=1))


def detect_onsets(x: np.ndarray, sample_rate: int, params: OnsetParams = OnsetParams()) -> Onsets:
    """Return onsets for mono float audio ``x``. Deterministic for identical input."""
    x = np.asarray(x, dtype=np.float32)
    out = Onsets(sample_rate=sample_rate)
    if x.size == 0 or float(np.max(np.abs(x))) == 0.0:
        return out
    S = _spectrogram(x, params.n_fft, params.hop)
    freqs = np.fft.rfftfreq(params.n_fft, 1.0 / sample_rate)
    flux = np.maximum(0.0, np.diff(S, axis=0)).sum(axis=1)
    peak = float(flux.max())
    if peak <= 0:
        return out
    flux = flux / peak
    k = max(1, int(params.median_window_sec * sample_rate / params.hop))
    padded = np.pad(flux, (k, k), mode="edge")
    med = np.median(sliding_window_view(padded, 2 * k + 1), axis=1)[: len(flux)]
    if len(flux) < 3:
        return out
    is_peak = (
        (flux[1:-1] > med[1:-1] + params.delta)
        & (flux[1:-1] >= flux[:-2])
        & (flux[1:-1] > flux[2:])
    )
    idx = np.where(is_peak)[0] + 1
    low_mask = freqs < params.low_band_hz
    win = max(1, int(params.feature_window_sec * sample_rate / params.hop))
    last_t = -1e9
    for i in idx:
        # flux[i] compares frame i+1 to frame i; report the centre of frame i+1.
        t = ((i + 1) * params.hop + params.n_fft // 2) / sample_rate
        if t - last_t < params.min_gap_sec:
            continue
        seg = S[i + 1 : i + 1 + win]
        total = float(seg.sum()) + 1e-9
        out.times_sec.append(round(float(t), 4))
        out.strength.append(round(float(flux[i]), 4))
        out.low_ratio.append(round(float(seg[:, low_mask].sum()) / total, 4))
        last_t = t
    return out


def two_means_threshold(values: List[float]) -> float:
    """Deterministic 1-D 2-means split; returns the midpoint between cluster centres."""
    v = np.sort(np.asarray(values, dtype=float))
    if v.size < 2 or v[0] == v[-1]:
        return float(v[0]) if v.size else 0.0
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
    return (lo + hi) / 2
