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
