"""Kolam GoalModel payload (case data, not a contract) + UI view + payload readers.

Built by ``track_a.goals.kolam.build`` from the finished kolam image only; read by
``track_b.evaluators.kolam.evaluate``. Coordinates are goal-image pixels (x right, y down).
See docs/plans/evaluation-core.md §3.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field

from tracks.common import kolam_geometry as kg

SAMPLE_STEP_PX = 4.0


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
