"""Generate SYNTHETIC kolam learner attempts with exact ground truth (deterministic, seeded).

Goal geometry comes from the target image via ``tracks.common.goals.kolam.payload_from_image``
(the same deterministic routine the Track A builder uses). Every attempt is a perturbation of
the goal line, so the expected outcome is known by construction (evaluation-core §7).

Outputs (``tracks/track-b/eval/kolam/synthetic/`` if the total is < 2 MB, else ``var/``):
    <variant>/trace.json | attempt.png, <variant>/label.json, goal_payload.json

Usage: python tracks/track-b/eval/kolam/make_synthetic.py
"""

from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tracks.common import kolam_geometry as kg  # noqa: E402
from tracks.common.goals.kolam import KolamGoal, payload_from_image  # noqa: E402

TARGET = ROOT / "tracks/cases/kolam/source/ithayakkamalam_target.jpg"
OUT = Path(__file__).resolve().parent / "synthetic"
FALLBACK = ROOT / "var/kolam_synthetic"
SEED = 20261006
SPEED_PX_S = 250.0
POINT_STEP_PX = 4.0
GAP_MS = 600.0
MAX_BYTES = 2 * 1024 * 1024
LABEL = "SYNTHETIC"


def stage_polys(goal: KolamGoal) -> List[np.ndarray]:
    out = []
    for c in goal.curves:
        pts = np.asarray(c.points, dtype=np.float64)
        for s in c.stages:
            if s.end < len(pts):
                seg = pts[s.start : s.end + 1]
            else:
                seg = np.vstack([pts[s.start :], pts[:1]]) if c.closed else pts[s.start :]
            out.append(seg)
    return out


def join(polys: List[np.ndarray]) -> np.ndarray:
    out = [polys[0]]
    for p in polys[1:]:
        out.append(p[1:] if np.allclose(out[-1][-1], p[0]) else p)
    return np.concatenate(out)


class Timer:
    def __init__(self) -> None:
        self.t = 0.0

    def stroke(self, poly: np.ndarray) -> Dict[str, list]:
        pts = kg.resample_polyline(poly, POINT_STEP_PX, False)
        seg = np.concatenate([[0.0], np.hypot(*np.diff(pts, axis=0).T)])
        ts = self.t + np.cumsum(seg) / SPEED_PX_S * 1000.0
        self.t = float(ts[-1]) + GAP_MS
        return {"points": [[round(float(x), 2), round(float(y), 2), int(round(t))] for (x, y), t in zip(pts, ts)]}


def trace_json(goal: KolamGoal, polys: List[np.ndarray]) -> dict:
    tm = Timer()
    strokes = [tm.stroke(p) for p in polys]
    return {"canvas": {"width": goal.canvas.width, "height": goal.canvas.height}, "goal_case_id": "kolam",
            "goal_version": 1, "strokes": strokes, "duration_ms": int(round(tm.t - GAP_MS)), "label": LABEL}


def jitter(poly: np.ndarray, rng: np.random.Generator, amp: float) -> np.ndarray:
    n = len(poly)
    noise = rng.standard_normal((n, 2))
    k = np.ones(15) / 15.0
    sm = np.stack([np.convolve(np.pad(noise[:, i], 7, mode="wrap"), k, mode="valid") for i in range(2)], axis=1)
    sm = sm / max(1e-9, np.abs(sm).max()) * amp
    return poly + sm


def detour(poly: np.ndarray, centre, radius: float) -> np.ndarray:
    """Replace the part of ``poly`` inside ``radius`` of ``centre`` by an arc around it."""
    c = np.asarray(centre, dtype=np.float64)
    d = np.hypot(poly[:, 0] - c[0], poly[:, 1] - c[1])
    inside = np.flatnonzero(d < radius)
    if inside.size == 0:
        return poly
    i0, i1 = int(inside.min()), int(inside.max())
    a0 = math.atan2(poly[i0 - 1, 1] - c[1], poly[i0 - 1, 0] - c[0])
    a1 = math.atan2(poly[i1 + 1, 1] - c[1], poly[i1 + 1, 0] - c[0])
    da = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    ang = a0 + np.linspace(0, 1, 24) * da
    arc = np.stack([c[0] + radius * np.cos(ang), c[1] + radius * np.sin(ang)], axis=1)
    return np.vstack([poly[:i0], arc, poly[i1 + 1 :]])


def all_sat() -> Dict[str, str]:
    return {k: "satisfied" for k in ("CRIT-KOLAM-COVERAGE", "CRIT-KOLAM-PRECISION", "CRIT-KOLAM-DOTS", "CRIT-KOLAM-CURVES", "CRIT-KOLAM-CONTINUITY")}


def render_attempt(goal: KolamGoal, polys: List[np.ndarray], *, size=None, transform=None, dark_on_light=False,
                   blur=0.0, noise=0.0, seed=0) -> Image.Image:
    w, h = size or (goal.canvas.width, goal.canvas.height)
    dots = [kg.Dot(d.x, d.y, d.r) for d in goal.dots]
    width = goal.stroke_width
    if transform is not None:
        s, th, tx, ty = transform
        m = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]) * s
        polys = [p @ m.T + np.array([tx, ty]) for p in polys]
        dots = [kg.Dot(*(np.array([d.x, d.y]) @ m.T + np.array([tx, ty])), d.r * s) for d in dots]
        width *= s
    img = kg.render((w, h), polys, width, dots, ink_value=255, bg_value=0)
    if blur:
        img = img.filter(ImageFilter.GaussianBlur(blur))
    arr = np.asarray(img, dtype=np.float32)
    if noise:
        arr = arr + np.random.default_rng(seed).normal(0, noise, arr.shape)
    if dark_on_light:
        arr = 255.0 - arr
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def main(out: Optional[Path] = None) -> Path:
    rng = np.random.default_rng(SEED)
    payload, _ = payload_from_image(TARGET)
    goal = KolamGoal.model_validate(payload)
    polys = stage_polys(goal)
    n = len(polys)
    stage_ids = [s.id for c in goal.curves for s in c.stages]
    k = len(goal.curves)
    tau = goal.tau
    full = [join(polys)] if k == 1 else [np.asarray(c.points) for c in goal.curves]
    variants: Dict[str, dict] = {}

    def add(name, kind, data, perturbation, statuses, first_div, events=None, extra=None):
        variants[name] = {"kind": kind, "data": data, "label": {
            "variant": name, "label": LABEL, "attempt_kind": kind, "perturbation": perturbation,
            "expected_statuses": statuses, "expected_first_divergence": first_div,
            "expected_events": events or [], **(extra or {})}}

    add("perfect", "trace", trace_json(goal, full), "the goal line itself, one stroke per continuous line",
        all_sat(), None)
    add("jittered", "trace", trace_json(goal, [jitter(p, rng, 0.4 * tau) for p in full]),
        f"smooth noise up to {0.4 * tau:.1f} px (inside the {tau:.1f} px tolerance)", all_sat(), None)
    # Omit TWO consecutive stages so coverage falls to ~0.79, well below the 0.90 sat boundary.
    # (Omitting a single stage lands at ~0.899, right at the boundary, making the test fragile.)
    miss = 2 if n >= 4 else 0
    miss2 = miss + 1  # index of second stage to omit
    before_m = join(polys[:miss]) if miss > 0 else None
    after_m = join(polys[miss2 + 1 :]) if miss2 + 1 < n else None
    stroke_polys_m = [p for p in [before_m, after_m] if p is not None]
    st = all_sat()
    st.update({"CRIT-KOLAM-COVERAGE": "partially_satisfied", "CRIT-KOLAM-CURVES": "not_satisfied"})
    add("missing_stage", "trace", trace_json(goal, stroke_polys_m),
        f"suggested stages {stage_ids[miss]}+{stage_ids[miss2]} omitted; coverage ~0.79, well below 0.90 boundary",
        st,
        {"kind": "incomplete_stage", "stage": stage_ids[miss]},
        [{"kind": "incomplete_stage", "stage": stage_ids[miss]},
         {"kind": "incomplete_stage", "stage": stage_ids[miss2]}])
    # stray stroke between two halves
    half = n // 2
    cx, cy = goal.symmetry.centre
    stray = np.array([[cx - 25.0, goal.canvas.height - 12.0], [cx + 125.0, goal.canvas.height - 12.0]])
    st = all_sat()
    st["CRIT-KOLAM-CONTINUITY"] = "partially_satisfied"
    add("stray_stroke", "trace", trace_json(goal, [join(polys[:half]), stray, join(polys[half:])]),
        "a 150 px straight stray line (stroke 1) below the pattern, between the two halves", st,
        {"kind": "off_path_ink", "stroke": 1}, [{"kind": "off_path_ink", "stroke": 1}])
    st = all_sat()
    st["CRIT-KOLAM-CONTINUITY"] = "not_satisfied"
    add("extra_pen_lifts", "trace", trace_json(goal, polys),
        f"the loop broken into {n} strokes (one per suggested stage)", st, None)
    # wrong dot relation: detour around three on-line dots (stages 1, 4, 7)
    dot_pos = {d.id: (d.x, d.y, d.r) for d in goal.dots}
    det = full[0].copy()
    ids = goal.curves[0].dot_ids
    wrong = [ids[int(len(ids) * f)] for f in (1 / 6, 3 / 6, 5 / 6)]
    for did in wrong:
        det = detour(det, dot_pos[did][:2], dot_pos[did][2] + tau + 3.0)
    st = all_sat()
    st["CRIT-KOLAM-DOTS"] = "partially_satisfied"
    add("wrong_dot_relation", "trace", trace_json(goal, [det]),
        f"the line detours around on-line dots {wrong} ({tau + 3:.0f} px beyond the dot edge) instead of passing through them",
        st, {"kinds": ["dot_relation", "off_path_ink"], "stroke": 0},
        [{"kind": "dot_relation", "dot_id": d} for d in wrong], {"wrong_dots": wrong})
    st = all_sat()
    st.update({"CRIT-KOLAM-COVERAGE": "not_satisfied", "CRIT-KOLAM-CURVES": "not_satisfied"})
    add("partial", "trace", trace_json(goal, [join(polys[:half])]),
        f"only the first {half} of {n} suggested stages drawn", st,
        {"kind": "incomplete_stage", "stage": stage_ids[half]}, [{"kind": "incomplete_stage", "stage": stage_ids[half]}])
    # rasters for the photo path
    img_st = all_sat()
    img_st["CRIT-KOLAM-CONTINUITY"] = "uncertain"
    add("raster_perfect", "image", render_attempt(goal, full), "goal line rendered white on black at goal size",
        img_st, None, extra={"process_observable": False})
    tf = (1.3, math.radians(23.0), 190.0, -65.0)
    add("raster_rotated_scaled", "image",
        render_attempt(goal, full, size=(700, 720), transform=tf, dark_on_light=True, blur=0.8, noise=6.0, seed=SEED),
        "goal line rendered dark-on-light, rotated 23 deg, scaled 1.3, shifted, blurred and noisy (photo stand-in)",
        img_st, None, extra={"process_observable": False, "transform": {"scale": 1.3, "theta_deg": 23.0, "tx": 190.0, "ty": -65.0}})
    st = dict(img_st)
    st.update({"CRIT-KOLAM-COVERAGE": "partially_satisfied", "CRIT-KOLAM-CURVES": "not_satisfied"})
    raster_miss_polys = [p for p in [before_m, after_m] if p is not None]
    add("raster_missing_stage_rotated", "image",
        render_attempt(goal, raster_miss_polys, size=(700, 720), transform=tf, blur=0.8, noise=6.0, seed=SEED + 1),
        f"photo stand-in with stages {stage_ids[miss]}+{stage_ids[miss2]} missing", st, None,
        extra={"process_observable": False, "missing_stage": stage_ids[miss]})

    target = out or OUT
    tmp = ROOT / "var/kolam_synthetic_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    for name, v in variants.items():
        d = tmp / name
        d.mkdir()
        if v["kind"] == "trace":
            (d / "trace.json").write_text(json.dumps(v["data"], separators=(",", ":")) + "\n", encoding="utf-8")
        else:
            v["data"].save(d / "attempt.png", optimize=True)
        (d / "label.json").write_text(json.dumps(v["label"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (tmp / "README.md").write_text(
        "# SYNTHETIC kolam attempts\n\nGenerated by `make_synthetic.py` (seed %d) from the goal line of "
        "`tracks/cases/kolam/source/ithayakkamalam_target.jpg`. These are perturbations with known ground truth "
        "(`label.json`), not human attempts. Regenerate instead of editing.\n" % SEED, encoding="utf-8")
    total = sum(p.stat().st_size for p in tmp.rglob("*") if p.is_file())
    dest = target if total < MAX_BYTES else FALLBACK
    if dest.exists():
        shutil.rmtree(dest)
    shutil.move(str(tmp), str(dest))
    print(f"wrote {len(variants)} variants ({total / 1024:.0f} KB) to {dest}")
    return dest


if __name__ == "__main__":
    main()
