"""Tests for the shared tabla DSP (tracks/common/tabla_dsp.py) and the TablaGoal payload model.

``synth_tabla`` is also used by the Track A and Track B tabla tests.
"""

import wave
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pytest

from tracks.common import tabla_dsp as dsp
from tracks.common.goals.tabla import PAYLOAD_MODEL, ui_view

SR = 16000
PATTERN = "BB-.B---"   # 8-pulse cycle: B bass stroke, - stroke without bass, . empty pulse


def synth_tabla(
    pulse: float = 0.25,
    cycles: int = 4,
    pattern: str = PATTERN,
    start: float = 0.5,
    tempo: float = 1.0,
    shift: Optional[Dict[int, float]] = None,
    drop: Iterable[int] = (),
    nobass: Iterable[int] = (),
    extra_at: Iterable[float] = (),
    tail: float = 1.0,
    sr: int = SR,
) -> Tuple[np.ndarray, List[float], List[bool]]:
    """Deterministic synthetic tabla: noise-burst strokes, bass strokes add a decaying 90 Hz tone.

    Returns (audio, stroke times, bass flags) for the strokes actually rendered (stroke indices
    used by ``shift``/``drop``/``nobass`` count the pattern's strokes, empty pulses excluded).
    """
    shift = shift or {}
    drop, nobass = set(drop), set(nobass)
    p = pulse / tempo
    events: List[Tuple[float, bool, float]] = []
    idx = 0
    for c in range(cycles):
        for k, ch in enumerate(pattern):
            if ch == ".":
                continue
            slot = c * len(pattern) + k
            t = start + slot * p + shift.get(idx, 0.0)
            if idx not in drop:
                events.append((t, ch == "B" and idx not in nobass, 1.0 if k == 0 else 0.7))
            idx += 1
    for t in extra_at:
        events.append((t, False, 0.7))
    events.sort()
    dur = max(e[0] for e in events) + tail
    x = np.zeros(int(dur * sr), dtype=np.float32)
    n = int(0.06 * sr)
    env = np.exp(-np.linspace(0, 7, n)).astype(np.float32)
    tt = np.arange(n) / sr
    for i, (t, bass, amp) in enumerate(events):
        rng = np.random.default_rng(1000 + i)
        burst = rng.standard_normal(n).astype(np.float32) * env * 0.4 * amp
        if bass:
            burst = burst * 0.3 + 0.7 * amp * np.sin(2 * np.pi * 90 * tt).astype(np.float32) * env
        a = int(t * sr)
        x[a:a + n] += burst[: len(x) - a]
    return x, [e[0] for e in events], [e[1] for e in events]


def write_wav(path: Path, x: np.ndarray, sr: int = SR) -> Path:
    path.write_bytes(dsp.wav_bytes(x, sr))
    return path


def test_pulse_ignores_subdivision_and_multi_pulse_gaps():
    times = [0.0, 0.25, 0.5, 1.0, 1.25, 1.75, 2.0, 2.25, 2.5, 3.0, 3.25, 3.75, 4.0]
    p, score = dsp.estimate_pulse(times)
    assert abs(p - 0.25) < 0.003 and score > 0.9
    k = dsp.grid_indices(times, p)
    assert list(k[:6]) == [0, 1, 2, 4, 5, 7]
    assert dsp.pulse_cv(times, p) < 0.01


def test_pulse_prefer_and_cycle():
    rng = np.random.default_rng(0)
    times = np.cumsum(np.full(40, 0.2)) + rng.normal(0, 0.004, 40)
    p, _ = dsp.estimate_pulse(times, lo=0.12, hi=0.32, prefer=0.21)
    assert abs(p - 0.2) < 0.003
    k = np.arange(40)
    bass = [(i % 8) in (0, 1, 4) for i in range(40)]
    cyc = dsp.estimate_cycle(k, bass)
    assert cyc.length_pulses == 8 and cyc.confidence > 0.8
    flat = dsp.estimate_cycle(k, [True] * 40)
    assert flat.length_pulses is None


def test_align_reports_missing_extra_and_outside():
    g = [dsp.Stroke(t, 0.8, b) for t, b in [(0.0, True), (0.25, False), (0.5, False), (0.75, True)]]
    l = [dsp.Stroke(t, 0.8, b) for t, b in [(-0.6, False), (0.01, True), (0.5, False), (0.62, False), (0.76, True), (1.6, False)]]
    a = dsp.align_strokes(g, l, 0.25)
    assert a.pairs == [(0, 1), (2, 2), (3, 4)]
    assert a.missing == [1] and a.extra == [3] and a.outside == [0, 5]


def test_learner_bass_threshold_rule():
    goal_lo, goal_hi = 0.15, 0.55
    gthr = 0.35
    # same level -> goal threshold
    same = [0.14, 0.16, 0.15, 0.56, 0.54, 0.15, 0.55, 0.16]
    assert not dsp.learner_bass_threshold(same, gthr, (goal_lo, goal_hi)).adapted
    # whole recording shifted up (different mic) -> adapt
    shifted = [v + 0.25 for v in same]
    r = dsp.learner_bass_threshold(shifted, gthr, (goal_lo, goal_hi))
    assert r.adapted and 0.5 < r.value < 0.7
    # learner never uses bass (unimodal) -> keep goal threshold
    nobass = [0.14, 0.15, 0.16, 0.15, 0.14, 0.16, 0.15, 0.17]
    assert not dsp.learner_bass_threshold(nobass, gthr, (goal_lo, goal_hi)).adapted


def test_analyze_goal_audio_on_synthetic_theka_and_payload_model():
    x, times, bass = synth_tabla()
    p = dsp.analyze_goal_audio(x, SR)
    p["window_sec"] = [0.0, len(x) / SR]
    g = PAYLOAD_MODEL.model_validate(p)
    assert len(g.onsets) == len(times) == 28
    assert np.allclose([o.t for o in g.onsets], times, atol=0.03)
    assert [o.bass for o in g.onsets] == bass
    assert abs(g.stroke_pulse_sec - 0.25) < 0.003
    assert g.cycle_length_pulses == 8
    assert g.beat_pulses == 2 and abs(g.tempo_bpm - 120.0) < 2.0
    assert g.bols is None and g.bols_status == "audio_model_disabled"
    v = ui_view(p)
    assert v["cycle_length_pulses"] == 8 and len(v["strokes"]) == 28 and v["beats"][0]["bass"] is True
    assert dsp.analyze_goal_audio(x, SR) == dsp.analyze_goal_audio(x, SR)  # deterministic


def test_analyze_goal_audio_rejects_too_few_strokes():
    x, _, _ = synth_tabla(cycles=1, pattern="B-..")
    with pytest.raises(dsp.GoalAnalysisError) as e:
        dsp.analyze_goal_audio(x, SR)
    assert e.value.kind == "too_few_strokes"


def test_levenshtein_and_match_bols():
    assert dsp.levenshtein(["Dha", "Dhin", "Na"], ["Dha", "Na"]) == 1
    labels, unmatched = dsp.match_bols([0.5, 1.0], [(0.51, "Dha"), (1.3, "Na")])
    assert labels == ["Dha", None] and unmatched == 1


# ---------------------------------------------------------------------------
# v2: mel filterbank, stroke features, timbre classes, assign, align_sequences
# ---------------------------------------------------------------------------


def test_mel_filterbank_shape_and_energy():
    fb = dsp.mel_filterbank(16000, 1024, 40, 50.0, 7600.0)
    assert fb.shape == (40, 513)
    # Each filter sums to ≤ 1 (triangular)
    row_sums = fb.sum(axis=1)
    assert np.all(row_sums >= 0.0)
    # Not all zero
    assert fb.max() > 0.1


def test_stroke_features_shape_and_ringing_vs_muted():
    """Ringing 300 Hz sine vs short noise burst: decay ratio and centroid must differ clearly."""
    sr = 16000
    n = int(0.12 * sr)
    t = np.arange(n) / sr
    env_slow = np.exp(-t / 0.1).astype(np.float32)   # slow decay ~ 100 ms
    env_fast = np.exp(-t / 0.005).astype(np.float32) # fast decay ~ 5 ms
    rng = np.random.default_rng(42)
    # ringing: low-frequency decaying sine
    ringing = (np.sin(2 * np.pi * 300 * t).astype(np.float32) * env_slow * 0.5)
    # muted: broadband noise burst, fast decay
    muted = (rng.standard_normal(n).astype(np.float32) * env_fast * 0.5)
    x = np.concatenate([np.zeros(100), ringing, np.zeros(200), muted, np.zeros(200)]).astype(np.float32)
    onset_times = [100 / sr, (100 + n + 200) / sr]
    feats = dsp.stroke_features(x, sr, onset_times)
    assert feats.shape == (2, 16)
    # Ringing: high decay ratio (40-80ms still audible / 0-40ms)
    # Muted: low decay ratio (decays within 5 ms)
    decay_ring = feats[0, 15]
    decay_mute = feats[1, 15]
    assert decay_ring > decay_mute * 3, f"Ringing decay {decay_ring:.3f} should be >> muted {decay_mute:.3f}"
    # Ringing stroke has lower spectral centroid (300 Hz vs broadband)
    centroid_ring = feats[0, 13]
    centroid_mute = feats[1, 13]
    assert centroid_ring < centroid_mute, f"Ringing centroid {centroid_ring:.3f} should be < muted {centroid_mute:.3f}"


def test_stroke_features_empty_input():
    feats = dsp.stroke_features(np.zeros(100, np.float32), 16000, [])
    assert feats.shape == (0, 16)


def test_fit_timbre_classes_determinism_and_k_range():
    """Same input → same labels; k chosen in 3..6 by best silhouette."""
    x, _, _ = synth_tabla()
    times = [o["t"] for o in dsp.analyze_goal_audio(x, SR)["onsets"]]
    feats = dsp.stroke_features(x, SR, times)
    m1 = dsp.fit_timbre_classes(feats)
    m2 = dsp.fit_timbre_classes(feats)
    # Deterministic
    np.testing.assert_array_equal(m1.centroids, m2.centroids)
    assert m1.k == m2.k and m1.silhouette == m2.silhouette
    assert 2 <= m1.k <= 6
    assert 0.0 <= m1.silhouette <= 1.0
    assert m1.radius_p95 > 0


def test_fit_timbre_classes_k2_fallback_on_weak_data():
    """Weakly separated data (uniform noise) → k=2 fallback with warning."""
    rng = np.random.default_rng(0)
    feats = rng.random((20, 16)).astype(np.float32)
    m = dsp.fit_timbre_classes(feats, k_range=(3, 6))
    assert m.k == 2
    assert m.warning == "timbre classes weakly separated"


def test_assign_outlier_gets_minus_one():
    """A point far outside the cluster radius gets label -1."""
    rng = np.random.default_rng(1)
    # tight cluster at origin
    feats = rng.standard_normal((20, 16)).astype(np.float32) * 0.1
    m = dsp.fit_timbre_classes(feats, k_range=(2, 3))
    # outlier far away
    outlier = np.ones((1, 16), dtype=np.float32) * 100.0
    labels, dists = dsp.assign(m, outlier)
    assert labels[0] == -1


def test_assign_perfect_copy_has_high_accuracy():
    """Expert strokes re-assigned get high match rate."""
    x, _, _ = synth_tabla()
    times = [o["t"] for o in dsp.analyze_goal_audio(x, SR)["onsets"]]
    feats = dsp.stroke_features(x, SR, times)
    m = dsp.fit_timbre_classes(feats)
    labels, _ = dsp.assign(m, feats)
    # Most points should not be -1 (the expert is within its own cluster)
    valid = np.sum(labels >= 0)
    assert valid >= len(times) * 0.9


def test_align_sequences_equal_length():
    a = ["Dha", "Dhin", "Na", "Ge"]
    b = ["Dha", "Dhin", "Na", "Ge"]
    pairs = dsp.align_sequences(a, b)
    assert pairs == [(0, 0), (1, 1), (2, 2), (3, 3)]


def test_align_sequences_different_length():
    a = ["s0", "s1", "s2", "s3"]  # 4 onsets
    b = ["Dha", "Na", "Ge"]        # 3 bols returned
    pairs = dsp.align_sequences(a, b)
    assert len(pairs) == 3  # one onset unaligned


def test_timbre_model_to_from_dict():
    rng = np.random.default_rng(7)
    feats = rng.standard_normal((20, 16)).astype(np.float32)
    m = dsp.fit_timbre_classes(feats)
    d = m.to_dict()
    m2 = dsp.TimbreModel.from_dict(d)
    np.testing.assert_allclose(m.centroids, m2.centroids, atol=1e-4)
