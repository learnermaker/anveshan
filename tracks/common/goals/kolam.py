"""Kolam GoalModel payload (case data, not a contract) + UI view + payload readers.

Built by ``track_a.goals.kolam.build`` from the finished kolam image only; read by
``track_b.evaluators.kolam.evaluate``. Coordinates are goal-image pixels (x right, y down).
See docs/plans/evaluation-core.md §3.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

from tracks.common import kolam_geometry as kg
from tracks.common.models import AnveshanFailure, FailureCategory

SAMPLE_STEP_PX = 4.0
MIN_STAGES = 3          # a single continuous line is split into >= 3 suggested drawing stages


class Canvas(BaseModel):
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class KolamDot(BaseModel):
    id: str
    x: float
    y: float
    r: float = Field(gt=0)
    relation: Literal["on_line", "enclosed", "free"]
    line_distance: float = Field(ge=0)


class KolamStage(BaseModel):
    id: str
    start: int = Field(ge=0)       # index into curve.points
    end: int                       # exclusive


class KolamCurve(BaseModel):
    id: str
    closed: bool
    points: List[List[float]] = Field(min_length=2)   # ordered polyline, ~2 px spacing
    start_index: int = 0
    length_px: float
    dot_ids: List[str] = Field(default_factory=list)  # on_line dots in passing order
    stages: List[KolamStage] = Field(default_factory=list)


class KolamSymmetry(BaseModel):
    rotation_order: int = Field(ge=1)
    mirror_axes_deg: List[float] = Field(default_factory=list)
    centre: List[float]
    scores: Dict[str, Any] = Field(default_factory=dict)


class KolamFeatures(BaseModel):
    n_dots: int
    n_curves: int
    n_closed: int
    n_crossings: int
    free_endpoints: int
    total_length_px: float
    relation_counts: Dict[str, int]
    sample_step_px: float = SAMPLE_STEP_PX
    n_samples: int


class KolamGoal(BaseModel):
    canvas: Canvas
    stroke_width: float = Field(gt=0)
    tau: float = Field(gt=0)
    dots: List[KolamDot]
    curves: List[KolamCurve] = Field(min_length=1)
    symmetry: KolamSymmetry
    features: KolamFeatures


PAYLOAD_MODEL = KolamGoal


def ui_view(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Small JSON for the app: canvas, dots and curves simplified for drawing (~6 px)."""
    g = KolamGoal.model_validate(payload)
    curves = []
    for c in g.curves:
        pts = kg.resample_polyline(np.asarray(c.points), 6.0, c.closed)
        curves.append({
            "id": c.id,
            "closed": c.closed,
            "points": [[round(float(x), 1), round(float(y), 1)] for x, y in pts],
            "stages": [{"id": s.id, "start": s.start, "end": s.end} for s in c.stages],
        })
    return {
        "kind": "kolam",
        "canvas": g.canvas.model_dump(),
        "stroke_width": round(g.stroke_width, 2),
        "tau": round(g.tau, 2),
        "dots": [{"id": d.id, "x": round(d.x, 1), "y": round(d.y, 1), "r": round(d.r, 1), "relation": d.relation} for d in g.dots],
        "curves": curves,
        "curve_count": len(g.curves),
        "rotation_order": g.symmetry.rotation_order,
    }


# ---------------------------------------------------------------------------------------
# Readers used by the evaluator
# ---------------------------------------------------------------------------------------


def goal_samples(goal: KolamGoal, step: float = SAMPLE_STEP_PX) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Goal features: skeleton samples every ``step`` px. Returns (points (n,2), curve index,
    stage index within the curve)."""
    pts, cidx, sidx = [], [], []
    for ci, c in enumerate(goal.curves):
        arr = np.asarray(c.points, dtype=np.float64)
        stages = c.stages or [KolamStage(id=f"{c.id}.S1", start=0, end=len(arr))]
        for si, s in enumerate(stages):
            seg = arr[s.start : s.end + 1] if s.end < len(arr) else (np.vstack([arr[s.start:], arr[:1]]) if c.closed else arr[s.start:])
            if len(seg) < 2:
                seg = arr[s.start : s.start + 1]
                rs = seg
            else:
                rs = kg.resample_polyline(seg, step, False)
                rs = rs[:-1] if len(rs) > 1 else rs     # the next stage starts at the cut
            pts.append(rs)
            cidx.append(np.full(len(rs), ci))
            sidx.append(np.full(len(rs), si))
    return np.concatenate(pts), np.concatenate(cidx), np.concatenate(sidx)


def dense_goal(goal: KolamGoal, step: float = 1.0) -> np.ndarray:
    out = [kg.resample_polyline(np.asarray(c.points), step, c.closed) for c in goal.curves]
    return np.concatenate(out)


def goal_dots(goal: KolamGoal) -> List[kg.Dot]:
    return [kg.Dot(d.x, d.y, d.r) for d in goal.dots]


def find_dot(goal: KolamGoal, dot_id: str) -> Optional[KolamDot]:
    for d in goal.dots:
        if d.id == dot_id:
            return d
    return None


# ---------------------------------------------------------------------------------------
# Construction (deterministic; used by the Track A builder and by synthetic-data tools)
# ---------------------------------------------------------------------------------------


def payload_from_image(source_path: Path, min_stages: int = MIN_STAGES) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Deterministic geometry -> (KolamGoal payload dict, built_with dict)."""
    an = kg.analyze_image(source_path)
    dec = kg.decompose_curves(an)
    if not dec.curves:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"no line work found in {source_path.name}")
    sym = kg.estimate_symmetry(an)
    rels = kg.dot_relations(an.dots, dec.curves, dec.closed, an.stroke_width)
    h, w = an.shape
    dots = []
    for i, (d, rel) in enumerate(zip(an.dots, rels)):
        dots.append({"id": f"D{i + 1:02d}", "x": round(d.x, 2), "y": round(d.y, 2), "r": round(d.r, 2),
                     "relation": rel["relation"], "line_distance": rel["line_distance"]})
    k = len(dec.curves)
    curves = []
    for ci, (pts, closed) in enumerate(zip(dec.curves, dec.closed)):
        cid = f"C{ci + 1}"
        on = []
        for d in dots:
            if d["relation"] != "on_line":
                continue
            dist = np.hypot(pts[:, 0] - d["x"], pts[:, 1] - d["y"])
            j = int(np.argmin(dist))
            if dist[j] <= d["r"] + an.stroke_width:
                on.append((j, d["id"]))
        stages_idx = kg.split_stages(pts, closed, sym["rotation_order"], sym["centre"], min_stages) if k < min_stages else [(0, len(pts))]
        curves.append({
            "id": cid,
            "closed": closed,
            "points": [[round(float(x), 2), round(float(y), 2)] for x, y in pts],
            "start_index": 0,
            "length_px": round(kg.polyline_length(pts, closed), 1),
            "dot_ids": [i for _, i in sorted(on)],
            "stages": [{"id": f"{cid}.S{si + 1}", "start": a, "end": b} for si, (a, b) in enumerate(stages_idx)],
        })
    counts = {r: sum(1 for d in dots if d["relation"] == r) for r in ("on_line", "enclosed", "free")}
    total_len = sum(c["length_px"] for c in curves)
    payload = {
        "canvas": {"width": w, "height": h},
        "stroke_width": round(an.stroke_width, 3),
        "tau": round(an.tau, 3),
        "dots": dots,
        "curves": curves,
        "symmetry": sym,
        "features": {
            "n_dots": len(dots),
            "n_curves": k,
            "n_closed": int(sum(dec.closed)),
            "n_crossings": int(sum(n for deg, n in dec.junction_degrees.items() if deg >= 3)),
            "free_endpoints": dec.free_endpoints,
            "total_length_px": round(total_len, 1),
            "relation_counts": counts,
            "sample_step_px": SAMPLE_STEP_PX,
            "n_samples": 0,
        },
    }
    payload["features"]["n_samples"] = int(len(goal_samples(KolamGoal.model_validate(payload))[0]))
    KolamGoal.model_validate(payload)
    built_with = {
        "algorithm": kg.ALGO_VERSION,
        "payload_builder": "tracks.common.goals.kolam.payload_from_image@v1",
        "binarize": an.threshold,
        "processing_scale": an.scale,
        "params": {
            "dot_peak_ratio": kg.DOT_PEAK_RATIO, "dot_ring_max": kg.DOT_RING_MAX,
            "symmetry_min_score": kg.SYMMETRY_MIN_SCORE, "tau": f"max({kg.TAU_MIN_PX}, {kg.TAU_W_FACTOR} * w)",
            "dir_arc_px": kg.DIR_ARC_PX, "min_stages": min_stages, "sample_step_px": SAMPLE_STEP_PX,
        },
        "junction_degrees": {str(a): b for a, b in dec.junction_degrees.items()},
    }
    return payload, built_with
