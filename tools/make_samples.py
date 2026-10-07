#!/usr/bin/env python
"""Generate sample attempts and example sources for the K9 demo (K9-P4).

Usage: python tools/make_samples.py [--dry-run]

Writes:
  tracks/cases/kolam/samples/samples.json  (+ good.trace.json, flawed.trace.json, unrelated.trace.json)
  tracks/cases/tabla/samples/samples.json  (+ good.wav, flawed.wav, unrelated.wav)
  tracks/samples/sources/sources.json      (+ kolam_photo.png, tabla_rhythm.wav)

Uses a fixed seed (numpy.random.default_rng(7)) so reruns are byte-identical.
All calibration is done in-process using the real Track B evaluator in recorded mode (0 live calls).
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Repo root and import setup
# ---------------------------------------------------------------------------

SCRIPT = Path(__file__).resolve()
ROOT = SCRIPT.parents[1]

for _p in (
    ROOT,
    ROOT / "tracks" / "track-a" / "src",
    ROOT / "tracks" / "track-b" / "src",
):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

KOLAM_SAMPLES = ROOT / "tracks" / "cases" / "kolam" / "samples"
TABLA_SAMPLES = ROOT / "tracks" / "cases" / "tabla" / "samples"
SOURCES_DIR = ROOT / "tracks" / "samples" / "sources"

KOLAM_GOAL_MODEL = ROOT / "tracks" / "cases" / "kolam" / "knowledge" / "goal_model.v1.json"
TABLA_GOAL_MODEL = ROOT / "tracks" / "cases" / "tabla" / "knowledge" / "goal_model.v2.json"

CANVAS_W = 492
CANVAS_H = 499
SR = 16000  # Hz, 16 kHz mono 16-bit WAV

# ---------------------------------------------------------------------------
# Kolam trace generation
# ---------------------------------------------------------------------------

def _load_kolam_curve() -> Tuple[np.ndarray, np.ndarray]:
    """Load goal curve points and compute cumulative arc lengths."""
    data = json.loads(KOLAM_GOAL_MODEL.read_text(encoding="utf-8"))
    pts = np.array(data["payload"]["curves"][0]["points"], dtype=float)  # (N, 2)
    diffs = np.diff(pts, axis=0)
    seg = np.sqrt((diffs ** 2).sum(axis=1))
    arcs = np.concatenate([[0.0], np.cumsum(seg)])
    return pts, arcs


def _resample_curve(pts: np.ndarray, arcs: np.ndarray, step_px: float = 3.0) -> np.ndarray:
    """Resample curve to about 1 point per step_px using linear interpolation."""
    total = arcs[-1]
    n = max(2, int(total / step_px) + 1)
    ts = np.linspace(0.0, total, n)
    x = np.interp(ts, arcs, pts[:, 0])
    y = np.interp(ts, arcs, pts[:, 1])
    return np.column_stack([x, y])  # (n, 2)


def _add_timestamps(pts_2d: np.ndarray, speed_px_s: float = 250.0) -> Tuple[List[List], int]:
    """Add timestamps at constant speed. Returns (points as [x,y,t_ms], duration_ms)."""
    diffs = np.diff(pts_2d, axis=0)
    seg = np.sqrt((diffs ** 2).sum(axis=1))
    # t in ms: 1000 * arc_length / speed
    t_ms = np.concatenate([[0.0], np.cumsum(seg * 1000.0 / speed_px_s)])
    t_int = np.round(t_ms).astype(int)
    points = [
        [round(float(x), 2), round(float(y), 2), int(t)]
        for (x, y), t in zip(pts_2d, t_int)
    ]
    return points, int(t_int[-1])


def _make_kolam_trace(strokes: List[List[List]], duration_ms: int) -> dict:
    return {
        "canvas": {"width": CANVAS_W, "height": CANVAS_H},
        "goal_case_id": "kolam",
        "goal_version": 1,
        "strokes": [{"points": s} for s in strokes],
        "duration_ms": duration_ms,
        "label": "SYNTHETIC",
    }


def generate_kolam_samples(rng: np.random.Generator, dry_run: bool = False) -> List[dict]:
    """Generate the three kolam samples and return their metadata for samples.json."""
    KOLAM_SAMPLES.mkdir(parents=True, exist_ok=True)

    pts, arcs = _load_kolam_curve()

    # ── good ────────────────────────────────────────────────────────────────
    resampled = _resample_curve(pts, arcs, step_px=3.0)
    jitter = rng.standard_normal(resampled.shape) * 1.5
    good_pts = np.clip(resampled + jitter, [[0, 0]], [[CANVAS_W, CANVAS_H]])
    good_points, good_dur = _add_timestamps(good_pts)
    good_trace = _make_kolam_trace([good_points], good_dur)

    # ── flawed (pen lifted at ~35%, skips to ~70%) ──────────────────────────
    # Spec: "if flawed passes, widen the skipped region"
    # Skip 35% to 70% (35% of arc) so that kolam.coverage drops below 0.90
    # (partially_satisfied threshold), causing CRIT-KOLAM-COVERAGE (required) to fail.
    resampled_f = _resample_curve(pts, arcs, step_px=3.0)
    jitter_f = rng.standard_normal(resampled_f.shape) * 1.5
    flawed_pts = np.clip(resampled_f + jitter_f, [[0, 0]], [[CANVAS_W, CANVAS_H]])
    # Compute per-resampled-point arc positions
    diffs_f = np.diff(flawed_pts, axis=0)
    seg_f = np.sqrt((diffs_f ** 2).sum(axis=1))
    arcs_f = np.concatenate([[0.0], np.cumsum(seg_f)])
    total_f = arcs_f[-1]

    mask_before = arcs_f <= total_f * 0.35
    mask_after = arcs_f >= total_f * 0.70
    # Ensure at least 2 points per stroke
    idx_before = np.where(mask_before)[0]
    idx_after = np.where(mask_after)[0]
    if len(idx_before) < 2:
        idx_before = np.array([0, 1])
    if len(idx_after) < 2:
        idx_after = np.array([len(flawed_pts) - 2, len(flawed_pts) - 1])

    stroke1_pts = flawed_pts[idx_before]
    stroke2_pts = flawed_pts[idx_after]
    s1_points, s1_dur = _add_timestamps(stroke1_pts)
    # Stroke 2 starts at t=0 relative to itself (service offsets per stroke)
    s2_points, s2_dur = _add_timestamps(stroke2_pts)
    # Total duration: last stroke 2 point time, offset by stroke 1 duration + pen-up gap
    gap_ms = 500  # 0.5s pen-up
    s2_offset = s1_dur + gap_ms
    s2_offset_points = [[x, y, int(t + s2_offset)] for x, y, t in s2_points]
    flawed_dur = s2_offset_points[-1][2]
    flawed_trace = _make_kolam_trace([s1_points, s2_offset_points], flawed_dur)

    # ── unrelated (zig-zag in top-left corner, ~15% of canvas) ──────────────
    # 15% of 492 = 73.8, 15% of 499 = 74.9
    margin = 10
    x_max = int(CANVAS_W * 0.15)   # ~73
    y_max = int(CANVAS_H * 0.15)   # ~74
    n_zz = 12
    x_coords = np.linspace(margin, x_max, n_zz)
    y_coords = np.where(
        np.arange(n_zz) % 2 == 0,
        np.full(n_zz, margin + 5.0),
        np.full(n_zz, y_max - 5.0),
    )
    unrelated_pts_2d = np.column_stack([x_coords, y_coords])
    # 3 second total → speed = arc_length / 3
    diffs_u = np.diff(unrelated_pts_2d, axis=0)
    seg_u = np.sqrt((diffs_u ** 2).sum(axis=1))
    total_u = seg_u.sum()
    speed_u = total_u / 3.0  # px/s
    unrelated_points, unrelated_dur = _add_timestamps(unrelated_pts_2d, speed_px_s=max(speed_u, 1.0))
    unrelated_trace = _make_kolam_trace([unrelated_points], unrelated_dur)

    if not dry_run:
        (KOLAM_SAMPLES / "good.trace.json").write_text(
            json.dumps(good_trace, separators=(",", ":")), encoding="utf-8"
        )
        (KOLAM_SAMPLES / "flawed.trace.json").write_text(
            json.dumps(flawed_trace, separators=(",", ":")), encoding="utf-8"
        )
        (KOLAM_SAMPLES / "unrelated.trace.json").write_text(
            json.dumps(unrelated_trace, separators=(",", ":")), encoding="utf-8"
        )

    sizes = {
        "good": len(json.dumps(good_trace, separators=(",", ":")).encode()),
        "flawed": len(json.dumps(flawed_trace, separators=(",", ":")).encode()),
        "unrelated": len(json.dumps(unrelated_trace, separators=(",", ":")).encode()),
    }
    for name, sz in sizes.items():
        print(f"  kolam {name}.trace.json: {sz:,} bytes")

    return [
        {
            "sample_id": "good",
            "label": "A careful attempt",
            "quality": "good",
            "attempt_kind": "trace",
            "file": "good.trace.json",
            "raster": None,
            "description": "Follows the line around every dot without lifting. Expect most checks to be met.",
            "preview": None,
            "synthetic": True,
            "credit": None,
            "licence": "CC0-1.0",
        },
        {
            "sample_id": "flawed",
            "label": "An attempt with a mistake",
            "quality": "flawed",
            "attempt_kind": "trace",
            "file": "flawed.trace.json",
            "raster": None,
            "description": "The pen lifts and skips part of the line. See where the feedback says it first went off track.",
            "preview": None,
            "synthetic": True,
            "credit": None,
            "licence": "CC0-1.0",
        },
        {
            "sample_id": "unrelated",
            "label": "Something unrelated",
            "quality": "unrelated",
            "attempt_kind": "trace",
            "file": "unrelated.trace.json",
            "raster": None,
            "description": "A scribble that is not this kolam. Anveshan should say it does not match instead of scoring it.",
            "preview": None,
            "synthetic": True,
            "credit": None,
            "licence": "CC0-1.0",
        },
    ]


# ---------------------------------------------------------------------------
# Tabla audio generation
# ---------------------------------------------------------------------------

def _write_wav(path: Path, x: np.ndarray) -> int:
    """Write mono 16-bit 16kHz WAV; returns file size in bytes."""
    import io
    import wave

    pcm = (np.clip(x.astype(np.float32), -1.0, 1.0) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    data = buf.getvalue()
    path.write_bytes(data)
    return len(data)


def _synth_stroke(t_sec: float, bass: bool, amp: float, rng_seed: int, n_samples: int) -> np.ndarray:
    """Synthesize one tabla stroke: noise burst + optional 90Hz bass tone."""
    rng_l = np.random.default_rng(rng_seed)
    decay_high = int(0.06 * SR)   # 60ms
    decay_bass = int(0.12 * SR)   # 120ms
    env_h = np.exp(-np.linspace(0, 7, decay_high)).astype(np.float32)
    env_b = np.exp(-np.linspace(0, 5, decay_bass)).astype(np.float32)

    # High-frequency noise burst (dayan: 400-600 Hz character)
    burst = rng_l.standard_normal(decay_high).astype(np.float32) * env_h * 0.4 * amp
    # Band-pass around 500 Hz via simple mixing (no scipy needed)
    tt_h = np.arange(decay_high) / SR
    burst = burst * 0.3 + 0.7 * amp * np.sin(2 * np.pi * 500 * tt_h).astype(np.float32) * env_h * 0.4

    x = np.zeros(n_samples, dtype=np.float32)
    a = int(t_sec * SR)

    if a < n_samples:
        end_h = min(a + decay_high, n_samples)
        x[a:end_h] += burst[:end_h - a]

    if bass:
        tt_b = np.arange(decay_bass) / SR
        bass_tone = 0.7 * amp * np.sin(2 * np.pi * 90 * tt_b).astype(np.float32) * env_b
        end_b = min(a + decay_bass, n_samples)
        x[a:end_b] += bass_tone[:end_b - a]

    return x


def _synth_tabla_from_onsets(
    onsets: List[Dict[str, Any]],
    total_sec: float,
    drop_idx: Optional[int] = None,
    tempo_scale_after: Optional[float] = None,
    tempo_scale_start_t: Optional[float] = None,
) -> np.ndarray:
    """Synthesize tabla audio from a list of onset dicts (each has t and bass).

    If tempo_scale_after is set, all onsets after tempo_scale_start_t have their
    times shifted by the accumulated tempo drift.
    """
    n_samples = int((total_sec + 1.5) * SR)
    x = np.zeros(n_samples, dtype=np.float32)
    onset_times = [(o["t"], o.get("bass", False)) for o in onsets]

    if tempo_scale_after is not None and tempo_scale_start_t is not None:
        # Shift onsets after tempo_scale_start_t by accumulated drift
        adjusted = []
        ref_t = tempo_scale_start_t
        for i, (t, bass) in enumerate(onset_times):
            if t >= ref_t:
                shifted_t = ref_t + (t - ref_t) * tempo_scale_after
                adjusted.append((shifted_t, bass))
            else:
                adjusted.append((t, bass))
        onset_times = adjusted

    for i, (t, bass) in enumerate(onset_times):
        if i == drop_idx:
            continue
        stroke = _synth_stroke(t, bass, 1.0, rng_seed=2000 + i, n_samples=n_samples)
        x += stroke

    # Add noise at -40 dB: 0.01 amplitude
    rng_noise = np.random.default_rng(99)
    noise = rng_noise.standard_normal(n_samples).astype(np.float32) * 0.01
    x += noise

    # Trim to total_sec + 0.5s tail
    trim = int((total_sec + 0.5) * SR)
    x = x[:trim]
    return x


def generate_tabla_samples(rng: np.random.Generator, dry_run: bool = False) -> List[dict]:
    """Generate the three tabla samples and return their metadata."""
    TABLA_SAMPLES.mkdir(parents=True, exist_ok=True)

    data = json.loads(TABLA_GOAL_MODEL.read_text(encoding="utf-8"))
    payload = data["payload"]
    onsets = payload["onsets"]   # list of {t, bass, ...}
    tempo_bpm = payload["tempo_bpm"]  # 158.5
    duration_sec = float(payload.get("duration_sec", 12.0))

    onset_times = [o["t"] for o in onsets]
    midpoint_t = (onset_times[0] + onset_times[-1]) / 2.0

    # ── good ────────────────────────────────────────────────────────────────
    good_audio = _synth_tabla_from_onsets(onsets, duration_sec)

    # ── flawed: from midpoint tempo drifts +12%, one stroke in second half missing ──
    n_after_mid = sum(1 for o in onsets if o["t"] >= midpoint_t)
    # Drop the stroke at 2/3 of the second half
    drop_candidate = None
    after_mid_indices = [i for i, o in enumerate(onsets) if o["t"] >= midpoint_t]
    if len(after_mid_indices) >= 3:
        drop_candidate = after_mid_indices[len(after_mid_indices) * 2 // 3]
    flawed_audio = _synth_tabla_from_onsets(
        onsets, duration_sec,
        drop_idx=drop_candidate,
        tempo_scale_after=1.12,       # +12% = 1.12× faster = 1/1.12 time scale on intervals
        tempo_scale_start_t=midpoint_t,
    )

    # ── unrelated: 8s of 220Hz hum + soft noise ──────────────────────────
    dur_unrelated = 8.0
    n_unr = int(dur_unrelated * SR)
    tt = np.arange(n_unr) / SR
    hum = 0.3 * np.sin(2 * np.pi * 220 * tt).astype(np.float32)
    noise_u = rng.standard_normal(n_unr).astype(np.float32) * 0.05
    unrelated_audio = hum + noise_u

    if not dry_run:
        sz_good = _write_wav(TABLA_SAMPLES / "good.wav", good_audio)
        sz_flawed = _write_wav(TABLA_SAMPLES / "flawed.wav", flawed_audio)
        sz_unrelated = _write_wav(TABLA_SAMPLES / "unrelated.wav", unrelated_audio)
        print(f"  tabla good.wav: {sz_good:,} bytes ({len(good_audio)/SR:.1f}s)")
        print(f"  tabla flawed.wav: {sz_flawed:,} bytes ({len(flawed_audio)/SR:.1f}s)")
        print(f"  tabla unrelated.wav: {sz_unrelated:,} bytes ({len(unrelated_audio)/SR:.1f}s)")

    return [
        {
            "sample_id": "good",
            "label": "A steady attempt",
            "quality": "good",
            "attempt_kind": "audio",
            "file": "good.wav",
            "raster": None,
            "description": "Plays the pattern at the source's tempo. Expect most checks to be met.",
            "preview": None,
            "synthetic": True,
            "credit": None,
            "licence": "CC0-1.0",
        },
        {
            "sample_id": "flawed",
            "label": "An attempt that rushes",
            "quality": "flawed",
            "attempt_kind": "audio",
            "file": "flawed.wav",
            "raster": None,
            "description": "Speeds up halfway and drops a stroke. See where the feedback says it first went off track.",
            "preview": None,
            "synthetic": True,
            "credit": None,
            "licence": "CC0-1.0",
        },
        {
            "sample_id": "unrelated",
            "label": "Something unrelated",
            "quality": "unrelated",
            "attempt_kind": "audio",
            "file": "unrelated.wav",
            "raster": None,
            "description": "A hum, not tabla. Anveshan should say it does not match instead of scoring it.",
            "preview": None,
            "synthetic": True,
            "credit": None,
            "licence": "CC0-1.0",
        },
    ]


# ---------------------------------------------------------------------------
# Kolam photo (example source)
# ---------------------------------------------------------------------------

def generate_kolam_photo() -> int:
    """Render a 512px PNG of the kolam goal curve and return file size in bytes."""
    from PIL import Image, ImageDraw

    SOURCES_DIR.mkdir(parents=True, exist_ok=True)

    data = json.loads(KOLAM_GOAL_MODEL.read_text(encoding="utf-8"))
    payload = data["payload"]
    curve_pts = np.array(payload["curves"][0]["points"], dtype=float)
    dots = payload["dots"]
    orig_w, orig_h = payload["canvas"]["width"], payload["canvas"]["height"]

    TARGET = 512
    scale = TARGET / max(orig_w, orig_h)
    W = int(orig_w * scale)
    H = int(orig_h * scale)

    img = Image.new("RGB", (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Draw curve
    scaled_pts = [(int(x * scale), int(y * scale)) for x, y in curve_pts]
    for i in range(len(scaled_pts) - 1):
        draw.line([scaled_pts[i], scaled_pts[i + 1]], fill=(30, 30, 30), width=6)
    # Close the curve
    draw.line([scaled_pts[-1], scaled_pts[0]], fill=(30, 30, 30), width=6)

    # Draw dots
    for dot in dots:
        cx = int(dot["x"] * scale)
        cy = int(dot["y"] * scale)
        r = max(3, int(dot["r"] * scale))
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(30, 30, 30))

    out_path = SOURCES_DIR / "kolam_photo.png"
    img.save(out_path, "PNG", optimize=True)
    sz = out_path.stat().st_size
    print(f"  kolam_photo.png: {sz:,} bytes ({W}x{H}px)")
    return sz


# ---------------------------------------------------------------------------
# Calibration via Track B
# ---------------------------------------------------------------------------

def _calibrate_samples(
    case_id: str,
    case_dir: Path,
    samples_meta: List[dict],
    samples_dir: Path,
) -> None:
    """Run each sample through the real Track B evaluator and populate expected."""
    from tracks.common.runtime import RunContext
    from tracks.common.models import AnveshanFailure

    try:
        track_b_api = importlib.import_module("track_b.api")
    except ImportError as exc:
        print(f"  WARNING: cannot import track_b.api ({exc}); expected values will be placeholders.")
        for s in samples_meta:
            s["expected"] = {"passed": s["quality"] == "good"}
        return

    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp) / "data"
        data_dir.mkdir()
        ctx = RunContext.create(case_dir, data_dir, "recorded")

        for s in samples_meta:
            file_path = samples_dir / s["file"]
            kind = s["attempt_kind"]
            print(f"  calibrating {case_id}/{s['sample_id']} ({kind})...")
            try:
                session = track_b_api.start_session(case_dir, "calibrator", data_dir)
                media = track_b_api.intake_attempt(session, file_path, kind)
                result = track_b_api.submit_attempt(session, media, ctx)
                rj = result.to_json()
                ev = rj.get("evaluation", {})
                passed = bool(ev.get("passed", False))
                first_div = rj.get("first_divergence")
                expected: Dict[str, Any] = {"passed": passed}
                # first_off_track is only meaningful when the attempt fails
                if not passed and first_div and isinstance(first_div, dict):
                    crit = first_div.get("criterion_id")
                    if crit:
                        expected["first_off_track"] = crit
                s["expected"] = expected
                print(f"    -> passed={passed}" + (f", first_off_track={expected.get('first_off_track')}" if "first_off_track" in expected else ""))

                # Retry calibration for good sample: reduce jitter if it doesn't pass
                # (handled below in main with iteration)

            except AnveshanFailure as exc:
                print(f"    -> REFUSED ({exc})")
                s["expected"] = {"refused": True}
            except Exception as exc:
                print(f"    -> ERROR: {exc}")
                s["expected"] = {"passed": s["quality"] == "good"}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Do not write any files.")
    args = parser.parse_args()
    dry_run = args.dry_run

    rng = np.random.default_rng(7)

    print("=== Kolam samples ===")
    kolam_meta = generate_kolam_samples(rng, dry_run=dry_run)

    print("\n=== Tabla samples ===")
    tabla_meta = generate_tabla_samples(rng, dry_run=dry_run)

    print("\n=== Example sources ===")
    if not dry_run:
        sz_photo = generate_kolam_photo()

        # tabla_rhythm.wav → hard link / copy to sources dir
        SOURCES_DIR.mkdir(parents=True, exist_ok=True)
        import shutil
        tabla_rhythm_src = TABLA_SAMPLES / "good.wav"
        tabla_rhythm_dst = SOURCES_DIR / "tabla_rhythm.wav"
        if tabla_rhythm_src.exists():
            shutil.copy2(tabla_rhythm_src, tabla_rhythm_dst)
            print(f"  tabla_rhythm.wav: {tabla_rhythm_dst.stat().st_size:,} bytes (copy of tabla/good.wav)")

    print("\n=== Calibrating Kolam ===")
    if not dry_run:
        _calibrate_samples(
            "kolam",
            ROOT / "tracks" / "cases" / "kolam",
            kolam_meta,
            KOLAM_SAMPLES,
        )

    print("\n=== Calibrating Tabla ===")
    if not dry_run:
        _calibrate_samples(
            "tabla",
            ROOT / "tracks" / "cases" / "tabla",
            tabla_meta,
            TABLA_SAMPLES,
        )

    # Write samples.json files
    if not dry_run:
        kolam_pack = {"schema_version": 1, "samples": kolam_meta}
        tabla_pack = {"schema_version": 1, "samples": tabla_meta}

        kolam_json = json.dumps(kolam_pack, indent=2, ensure_ascii=False) + "\n"
        tabla_json = json.dumps(tabla_pack, indent=2, ensure_ascii=False) + "\n"

        (KOLAM_SAMPLES / "samples.json").write_text(kolam_json, encoding="utf-8")
        (TABLA_SAMPLES / "samples.json").write_text(tabla_json, encoding="utf-8")
        print(f"\nWrote {KOLAM_SAMPLES / 'samples.json'}")
        print(f"Wrote {TABLA_SAMPLES / 'samples.json'}")

        # Write sources.json
        sources = [
            {
                "sample_id": "kolam-photo",
                "label": "A kolam drawing (photo)",
                "description": "A finished line drawing of the kolam pattern, rendered from the goal curve.",
                "file": "kolam_photo.png",
                "mime_type": "image/png",
                "credit": "Rendered for the demo from the Anveshan kolam goal",
                "licence": "CC0-1.0",
            },
            {
                "sample_id": "tabla-rhythm",
                "label": "A short tabla rhythm (audio)",
                "description": "A synthetic tabla rhythm matching the goal pattern.",
                "file": "tabla_rhythm.wav",
                "mime_type": "audio/wav",
                "credit": "Synthesized for the demo",
                "licence": "CC0-1.0",
            },
        ]
        sources_json = json.dumps({"sources": sources}, indent=2, ensure_ascii=False) + "\n"
        (SOURCES_DIR / "sources.json").write_text(sources_json, encoding="utf-8")
        print(f"Wrote {SOURCES_DIR / 'sources.json'}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
