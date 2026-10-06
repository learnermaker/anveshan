"""Generate SYNTHETIC tabla learner attempts from the goal window audio, with exact ground truth.

Every attempt is a deterministic (seeded) re-synthesis of the expert window: the audio is cut
into one segment per goal stroke (from 30 ms before the detected onset to the next segment) and
the segments are relocated / removed / filtered. Ground truth therefore is exact: we know which
stroke moved, by how much, and which strokes lost their bass.

Outputs
  var/eval/tabla/<name>.wav                          (gitignored; derived from CC BY-SA audio)
  tracks/track-b/eval/tabla/labels/<name>.json       (committed ground truth)
  tracks/track-b/eval/tabla/labels/goal_model.snapshot.json   (goal the labels refer to)

Goal: the latest tracks/cases/tabla/knowledge/goal_model.v*.json if present; otherwise it is
bootstrapped with the Track A builder (eval tooling only; the track_b package never imports
track_a). All attempts are labelled runtime_label SYNTHETIC.

Usage: python tracks/track-b/eval/tabla/make_synthetic.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
for p in (ROOT, ROOT / "tracks" / "track-a" / "src", ROOT / "tracks" / "track-b" / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from tracks.common import tabla_dsp as dsp  # noqa: E402
from tracks.common.casedata import GoalModel, latest_version, load_sources, load_versioned, resolve_media, write_json  # noqa: E402
from tracks.common.media import decode_audio  # noqa: E402

SR = 16000
SEED = 20261006
PRE = 0.03
OUT_DIR = ROOT / "var" / "eval" / "tabla"
LABEL_DIR = Path(__file__).resolve().parent / "labels"
CASE_DIR = ROOT / "tracks" / "cases" / "tabla"

# evaluation-core §5.2 bands (steady bands come from the goal build, see built_with)
BANDS = {
    "CRIT-TABLA-TEMPO": ("tabla.tempo_error_pct", "lower", 5.0, 10.0),
    "CRIT-TABLA-TIMING": ("tabla.timing_median_ms", "lower", 50.0, 100.0),
    "CRIT-TABLA-BAYAN": ("tabla.bass_accuracy", "higher", 0.9, 0.7),
    "CRIT-TABLA-COMPLETE": ("tabla.missing_extra", "lower", 1.0, 3.0),
}


def status(value: float, direction: str, sat: float, partial: float) -> str:
    if direction == "lower":
        return "satisfied" if value <= sat else "partially_satisfied" if value <= partial else "not_satisfied"
    return "satisfied" if value >= sat else "partially_satisfied" if value >= partial else "not_satisfied"


def load_goal() -> GoalModel:
    kdir = CASE_DIR / "knowledge"
    if latest_version(kdir, "goal_model") is not None:
        return load_versioned(kdir, "goal_model", GoalModel)
    from tracks.common.models import ModelRegistry
    from tracks.common.runtime import RunContext
    from track_a.goals.tabla import build

    src = load_sources(CASE_DIR).primary()
    ctx = RunContext.create(CASE_DIR, ROOT / "var", "recorded", registry=ModelRegistry({"audio": ""}))
    r = build(resolve_media(CASE_DIR, src), src, ctx, case_id="tabla", version=1)
    return GoalModel(case_id="tabla", version=1, modality="tabla_audio", source_ids=[src.source_id],
                     package_id="kp.tabla.1", built_with=r.built_with, payload=r.goal_payload, warnings=r.warnings)


def segments(x: np.ndarray, times: List[float]) -> List[np.ndarray]:
    starts = [max(0, int(round((t - PRE) * SR))) for t in times]
    ends = starts[1:] + [len(x)]
    return [x[a:b].copy() for a, b in zip(starts, ends)]


def fade(seg: np.ndarray, n_in: int = 48, n_out: int = 80) -> np.ndarray:
    s = seg.copy()
    n_in, n_out = min(n_in, len(s)), min(n_out, len(s))
    if n_in:
        s[:n_in] *= np.linspace(0, 1, n_in)
    if n_out:
        s[-n_out:] *= np.linspace(1, 0, n_out)
    return s


def render(x: np.ndarray, times: List[float], new_times: List[float | None], segs: List[np.ndarray], length: int | None = None) -> np.ndarray:
    """Overlap-add each stroke segment at its new time (None = dropped). Audio before the first stroke is kept."""
    head = max(0, int(round((times[0] - PRE) * SR)))
    n = length or len(x)
    out = np.zeros(n + SR, dtype=np.float32)
    out[:head] = x[:head]
    placed = [(i, tt) for i, tt in enumerate(new_times) if tt is not None]
    for k, (i, t) in enumerate(placed):
        seg = segs[i]
        a = int(round((t - PRE) * SR))
        if k + 1 < len(placed):  # a stroke moved earlier cuts the previous stroke's ring (keeps labels exact)
            nxt = int(round((placed[k + 1][1] - PRE) * SR))
            seg = seg[: max(1, min(len(seg), nxt - a))]
        s = fade(seg)
        out[a:a + len(s)] += s[: max(0, len(out) - a)]
    return out[:n]


def high_pass(seg: np.ndarray, cutoff: float = 320.0) -> np.ndarray:
    F = np.fft.rfft(seg)
    f = np.fft.rfftfreq(len(seg), 1 / SR)
    gain = np.clip((f - cutoff * 0.75) / (cutoff * 0.25), 0, 1)
    return np.fft.irfft(F * gain, n=len(seg)).astype(np.float32)


def expected_metrics(goal_t: np.ndarray, true_t: Dict[int, float], pulse: float, bass_goal: List[bool],
                     bass_learner: Dict[int, bool], missing: List[int]) -> Dict[str, float]:
    js = sorted(true_t)
    gx = np.array([goal_t[j] for j in js])
    ly = np.array([true_t[j] for j in js])
    b, a = dsp.robust_fit_line(gx, ly)
    dev = np.abs(ly - (a + b * gx)) * 1000
    gb = [j for j in js if bass_goal[j]]
    gn = [j for j in js if not bass_goal[j]]
    rec = []
    if gb:
        rec.append(sum(bass_learner[j] for j in gb) / len(gb))
    if gn:
        rec.append(sum(not bass_learner[j] for j in gn) / len(gn))
    return {
        "tabla.tempo_error_pct": round(abs(1 / b - 1) * 100, 2),
        "tabla.timing_median_ms": round(float(np.median(dev)), 1),
        "tabla.bass_accuracy": round(float(np.mean(rec)), 4),
        "tabla.missing_extra": float(len(missing)),
        "tabla.ioi_cv": round(float(dsp.pulse_cv(sorted(ly), pulse * b)), 4),
    }


def main() -> int:
    goal = load_goal()
    g = goal.payload
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LABEL_DIR.mkdir(parents=True, exist_ok=True)
    write_json(LABEL_DIR / "goal_model.snapshot.json", goal)
    src = load_sources(CASE_DIR).get(goal.source_ids[0])
    w0, w1 = g["window_sec"]
    x = decode_audio(resolve_media(CASE_DIR, src), SR, start_sec=w0, end_sec=w1)
    t = [o["t"] for o in g["onsets"]]
    gt = np.array(t)
    n = len(t)
    bass_goal = [o["bass"] for o in g["onsets"]]
    pulse = g["stroke_pulse_sec"]
    tol_ms = g["tolerances"]["timing_ms"]
    steady_sat, steady_partial = goal.built_with.get("bands", {}).get("steady", [0.08, 0.15])
    segs = segments(x, t)
    rng = np.random.default_rng(SEED)
    cases: List[Dict[str, Any]] = []

    def add(name: str, audio: np.ndarray, desc: str, true_t: Dict[int, float], bass_l: Dict[int, bool],
            missing: List[int], perturbed: List[int], first: Dict[str, Any] | None, params: Dict[str, Any]) -> None:
        m = expected_metrics(gt, true_t, pulse, bass_goal, bass_l, missing)
        st = {cid: status(m[metric], d, s, p) for cid, (metric, d, s, p) in BANDS.items()}
        st["CRIT-TABLA-STEADY"] = status(m["tabla.ioi_cv"], "lower", steady_sat, steady_partial)
        st["CRIT-TABLA-BOLS"] = "uncertain"
        dsp_wav = OUT_DIR / f"{name}.wav"
        dsp_wav.write_bytes(dsp.wav_bytes(audio, SR))
        label = {
            "name": name, "runtime_label": "SYNTHETIC", "description": desc, "seed": SEED, "params": params,
            "goal_package_id": goal.package_id, "goal_source_id": goal.source_ids[0], "goal_window_sec": [w0, w1],
            "wav": f"var/eval/tabla/{name}.wav",
            "perturbed_goal_strokes": perturbed,
            "missing_goal_strokes": missing,
            "true_onsets": [{"goal": j, "t": round(true_t[j], 4), "bass": bass_l[j]} for j in sorted(true_t)],
            "expected_first_divergence": first,
            "expected_metrics": m,
            "expected_statuses": st,
        }
        write_json(LABEL_DIR / f"{name}.json", label)
        cases.append(label)
        print(f"{name}: {st}")

    ident = {j: t[j] for j in range(n)}
    bl = {j: bass_goal[j] for j in range(n)}

    # 1. perfect copy (the goal window audio itself)
    add("perfect", x, "Exact copy of the goal window audio.", ident, bl, [], [], None, {})

    # 2/3. jitter. Two strokes may not come closer than MIN_IOI (the detector merges onsets
    # closer than 0.09 s); on a violation the opposite sign is tried, then no shift.
    MIN_IOI = 0.10

    def jitter(lo_ms: float, hi_ms: float, start_idx: int, blocks: bool = False) -> Dict[int, float]:
        """blocks=True: pattern (s, s, 0) repeating with a random sign s per block. At a ~0.19 s pulse,
        independent +/-55-90 ms shifts of neighbours would collide; two same-sign shifts followed by an
        unshifted stroke keep every interval >= MIN_IOI while moving 2/3 of the strokes."""
        d = np.zeros(n)
        sign = 1.0
        for j in range(start_idx, n):
            mag = rng.uniform(lo_ms, hi_ms) / 1000.0
            p = (j - start_idx) % 3
            if not blocks or p == 0:
                sign = 1.0 if rng.random() < 0.5 else -1.0
            if blocks and p == 2:
                mag = 0.0
            options = (sign * mag, 0.0) if blocks else (sign * mag, -sign * mag, 0.0)
            for v in options:
                ok_prev = j == 0 or (t[j] + v) - (t[j - 1] + d[j - 1]) >= MIN_IOI
                ok_next = j == n - 1 or t[j + 1] - (t[j] + v) >= MIN_IOI
                if ok_prev and ok_next:
                    break
            else:
                v = 0.0
            d[j] = v
        return {j: t[j] + float(d[j]) for j in range(n)}

    def first_off_grid(true_t: Dict[int, float]) -> int | None:
        """First goal stroke whose true deviation after a robust offset/tempo fit exceeds the tolerance."""
        js = sorted(true_t)
        gx = np.array([t[j] for j in js])
        ly = np.array([true_t[j] for j in js])
        b, a = dsp.robust_fit_line(gx, ly)
        for j, gxx, lyy in zip(js, gx, ly):
            if abs(lyy - (a + b * gxx)) * 1000 > tol_ms:
                return j
        return None

    tj = jitter(0.0, 20.0, 0)
    add("jitter_mild", render(x, t, [tj[j] for j in range(n)], segs),
        "Every stroke displaced by uniform(0, 20) ms with random sign.", tj, bl, [], list(range(n)), None,
        {"jitter_abs_ms": [0, 20]})

    start = 6  # first strokes untouched so the first divergence is not at t=0
    th = jitter(55.0, 90.0, start, blocks=True)
    moved = [j for j in range(start, n) if th[j] != t[j]]
    fb = first_off_grid(th)
    add("jitter_heavy", render(x, t, [th[j] for j in range(n)], segs),
        f"From stroke {start} on, strokes displaced by 55-90 ms in blocks (s, s, 0) with a random sign s per block "
        f"({len(moved)} moved; a shift is skipped when it would bring two strokes closer than {MIN_IOI:.2f} s). "
        f"Strokes 0..{start - 1} untouched.",
        th, bl, [], moved,
        None if fb is None else {"time": round(th[fb], 4), "goal_stroke": fb, "kinds": ["late_stroke", "early_stroke"]},
        {"jitter_abs_ms": [55, 90], "from_stroke": start, "min_ioi_sec": MIN_IOI})

    # 4. tempo +8 % (stroke times compressed about the first stroke; segments truncated)
    k = 1.08
    tt = {j: t[0] + (t[j] - t[0]) / k for j in range(n)}
    segs_t = []
    for j in range(n):
        nxt = (tt[j + 1] - PRE) if j + 1 < n else None
        seg = segs[j]
        if nxt is not None:
            seg = seg[: max(1, int(round((nxt - (tt[j] - PRE)) * SR)))]
        segs_t.append(seg)
    length = int(round((t[0] + (len(x) / SR - t[0]) / k) * SR))
    add("tempo_plus8", render(x, t, [tt[j] for j in range(n)], segs_t, length=length),
        "Tempo 8% faster: every stroke time compressed by 1/1.08 about the first stroke.",
        tt, bl, [], list(range(1, n)), {"time": round(tt[0], 4), "goal_stroke": 0, "kinds": ["tempo_off"]},
        {"tempo_factor": k})

    # 5. three dropped strokes (interior, non-adjacent)
    # only clearly audible strokes (strength >= 0.25): missing soft strokes are "minor" events by design
    pool = [j for j in range(5, n - 5) if g["onsets"][j]["strength"] >= 0.25]
    drops: List[int] = []
    while len(drops) < 3:
        j = int(rng.choice(pool))
        if all(abs(j - d) > 2 for d in drops):
            drops.append(j)
    drops.sort()
    td = {j: t[j] for j in range(n) if j not in drops}
    add("dropped3", render(x, t, [None if j in drops else t[j] for j in range(n)], segs),
        f"Goal strokes {drops} removed (silence).", td, {j: bass_goal[j] for j in td}, drops, drops,
        {"time": round(t[drops[0]], 4), "goal_stroke": drops[0], "kinds": ["missing_stroke"]}, {"dropped": drops})

    # 6. bass removed in the middle third of the window
    lo_t, hi_t = len(x) / SR / 3, 2 * len(x) / SR / 3
    section = [j for j in range(n) if lo_t <= t[j] < hi_t and bass_goal[j]]
    segs_b = [high_pass(s) if j in section else s for j, s in enumerate(segs)]
    bl_b = {j: (False if j in section else bass_goal[j]) for j in range(n)}
    add("bass_removed_mid", render(x, t, [t[j] for j in range(n)], segs_b),
        f"Low frequencies (< ~320 Hz) removed from the {len(section)} bass strokes between {lo_t:.2f} and {hi_t:.2f} s.",
        ident, bl_b, [], section,
        {"time": round(t[section[0]], 4), "goal_stroke": section[0], "kinds": ["bass_missing"]},
        {"section_sec": [round(lo_t, 3), round(hi_t, 3)], "high_pass_hz": 320})

    write_json(LABEL_DIR / "index.json", {"seed": SEED, "cases": [c["name"] for c in cases]})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
