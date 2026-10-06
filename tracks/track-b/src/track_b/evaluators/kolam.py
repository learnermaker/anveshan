"""Kolam trajectory evaluator (deterministic). docs/plans/evaluation-core.md §3.2.

``attempt.kind == "trace"``: canvas trace JSON (docs/plans/service-api.md §4), strokes in goal
image pixels with timestamps. Every stroke prefix is scored against the goal line:
coverage, precision, off-path runs (violations), dot relations, stage/curve completion,
pen lifts, progress curve over time.

``attempt.kind == "image"``: a photo/raster of a finished drawing. Ink and dots are detected,
registered to the goal by a similarity transform, and final-state metrics are computed.
Process metrics are UNCERTAIN: a final image does not show how it was drawn.

Never imports track_a; reads the goal payload through tracks.common.goals.kolam.
"""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from tracks.common import kolam_geometry as kg
from tracks.common import locators
from tracks.common.casedata import GoalModel
from tracks.common.goals.kolam import KolamGoal, dense_goal, goal_samples
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import EvidenceRef
from tracks.common.schemas.evidence import Modality, VerificationState
from track_b.trajectory import AttemptMedia, DivergenceEvent, MetricValue, TrajectoryResult

COMPLETE_AT = 0.9              # stage / curve counts as completed at this coverage
CURVE_CHUNK = 32               # dense points per progress-curve update
PROCESS_UNOBSERVABLE = "process not observable from a final image"
ORDER_NOTE = "order reported only, not scored: the target image does not establish the original drawing order"


# ---------------------------------------------------------------------------------------
# shared helpers
# ---------------------------------------------------------------------------------------


class _Goal:
    def __init__(self, goal: GoalModel):
        if goal.modality != "kolam_image":
            raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"kolam evaluator got modality {goal.modality}")
        self.g = KolamGoal.model_validate(goal.payload)
        self.samples, self.cidx, self.sidx = goal_samples(self.g)
        self.dense = dense_goal(self.g, 1.0)
        self.tau = float(self.g.tau)
        self.w = float(self.g.stroke_width)
        self.k = len(self.g.curves)
        self.stage_ids: List[str] = []
        self.stage_key: List[Tuple[int, int]] = []
        for ci, c in enumerate(self.g.curves):
            n = max(1, len(c.stages))
            for si in range(n):
                self.stage_ids.append(c.stages[si].id if c.stages else f"{c.id}.S1")
                self.stage_key.append((ci, si))
        self.stage_of_sample = np.array([self.stage_key.index((int(c), int(s))) for c, s in zip(self.cidx, self.sidx)])
        # dot neighbourhoods: goal samples near each dot decide whether the dot is "assessed"
        self.dot_nbrs = []
        for d in self.g.dots:
            rad = max(3.0 * self.tau, d.line_distance + self.tau)
            dd = np.hypot(self.samples[:, 0] - d.x, self.samples[:, 1] - d.y)
            self.dot_nbrs.append(np.flatnonzero(dd <= rad))


def _ev(eid: str, source_id: str, modality: Modality, excerpt: str,
        start: Optional[float] = None, end: Optional[float] = None) -> EvidenceRef:
    return EvidenceRef(evidence_id=eid, source_id=source_id, modality=modality, start_sec=start, end_sec=end,
                       cue_excerpt=excerpt, verification_state=VerificationState.OBSERVED, confidence=1.0)


def _stage_bbox_pct(goal: _Goal, stage: int) -> str:
    pts = goal.samples[goal.stage_of_sample == stage]
    w, h = goal.g.canvas.width, goal.g.canvas.height
    x0, y0 = pts.min(axis=0)
    x1, y1 = pts.max(axis=0)
    return f"x {100 * x0 / w:.0f}-{100 * x1 / w:.0f}%, y {100 * y0 / h:.0f}-{100 * y1 / h:.0f}%"


def _dot_relations(goal: _Goal, ink: np.ndarray, covered: np.ndarray) -> List[Dict[str, Any]]:
    """Compare each goal dot's relation with the learner's line ink (points in goal coords)."""
    out = []
    for i, d in enumerate(goal.g.dots):
        if len(ink):
            dist = np.hypot(ink[:, 0] - d.x, ink[:, 1] - d.y)
            j = int(np.argmin(dist))
            ld = float(dist[j])
        else:
            j, ld = -1, float("inf")
        touched = ld <= d.r + goal.w
        nb = goal.dot_nbrs[i]
        near_cov = float(covered[nb].mean()) if nb.size else 0.0
        assessed = near_cov >= 0.5 or touched
        if d.relation == "on_line":
            learner_rel = "on_line" if ld <= goal.tau else "off_line"
            match = ld <= goal.tau
        else:
            learner_rel = "on_line" if touched else "off_line"
            match = not touched
        out.append({"dot_id": d.id, "goal": d.relation, "learner": learner_rel, "distance": round(ld, 2),
                    "assessed": bool(assessed), "match": bool(match), "nearest_index": j})
    return out


def _dot_metric(rels: List[Dict[str, Any]], evidence: Optional[EvidenceRef], pos: Optional[float]) -> MetricValue:
    assessed = [r for r in rels if r["assessed"]]
    if not assessed:
        return MetricValue(None, "no dot could be assessed: the learner drew nowhere near the dots",
                           uncertain_reason="no assessed dots")
    ok = sum(1 for r in assessed if r["match"])
    bad = [r for r in assessed if not r["match"]]
    detail = "; ".join(f"{r['dot_id']} goal {r['goal']} but learner line at {r['distance']:.1f} px" for r in bad[:5])
    return MetricValue(round(ok / len(assessed), 4),
                       f"{ok} of {len(assessed)} assessed dots keep the target relation ({len(rels) - len(assessed)} not assessed)"
                       + (f"; mismatches: {detail}" if bad else ""), evidence=evidence, position=pos)


def _completion(goal: _Goal, covered: np.ndarray) -> Tuple[Dict[str, float], Dict[str, float]]:
    stage_cov = {sid: round(float(covered[goal.stage_of_sample == s].mean()), 4) for s, sid in enumerate(goal.stage_ids)}
    curve_cov = {c.id: round(float(covered[goal.cidx == ci].mean()), 4) for ci, c in enumerate(goal.g.curves)}
    return stage_cov, curve_cov


# ---------------------------------------------------------------------------------------
# trace
# ---------------------------------------------------------------------------------------


def _load_trace(attempt: AttemptMedia, goal: _Goal) -> Tuple[List[np.ndarray], List[str]]:
    warnings: List[str] = []
    try:
        data = json.loads(attempt.path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"unreadable trace JSON: {exc}") from exc
    strokes_in = data.get("strokes")
    if not isinstance(strokes_in, list):
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, "trace JSON has no 'strokes' list")
    sx = sy = 1.0
    canvas = data.get("canvas") or {}
    if canvas.get("width") and canvas.get("height"):
        if (int(canvas["width"]), int(canvas["height"])) != (goal.g.canvas.width, goal.g.canvas.height):
            sx = goal.g.canvas.width / float(canvas["width"])
            sy = goal.g.canvas.height / float(canvas["height"])
            warnings.append(f"trace canvas {canvas['width']}x{canvas['height']} rescaled to goal {goal.g.canvas.width}x{goal.g.canvas.height}")
    strokes = []
    for s in strokes_in:
        pts = np.asarray(s.get("points", []) if isinstance(s, dict) else s, dtype=np.float64)
        if pts.ndim != 2 or pts.shape[0] == 0 or pts.shape[1] < 2:
            continue
        if pts.shape[1] == 2:
            pts = np.hstack([pts, np.zeros((len(pts), 1))])
        pts = pts[:, :3].copy()
        pts[:, 0] *= sx
        pts[:, 1] *= sy
        strokes.append(pts)
    if not strokes:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, "trace has no strokes with points")
    return strokes, warnings


def _densify(stroke: np.ndarray) -> np.ndarray:
    """Resample a stroke to ~1 px spacing; columns x, y, t_ms."""
    if len(stroke) < 2:
        return stroke.copy()
    seg = np.hypot(*np.diff(stroke[:, :2], axis=0).T)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    if cum[-1] <= 0:
        return stroke[:1].copy()
    s = np.linspace(0.0, cum[-1], max(2, int(math.ceil(cum[-1])) + 1))
    return np.stack([np.interp(s, cum, stroke[:, i]) for i in range(3)], axis=1)


def _evaluate_trace(goal: _Goal, attempt: AttemptMedia) -> TrajectoryResult:
    strokes, warnings = _load_trace(attempt, goal)
    trace_id = attempt.source_id + ".trace"
    tau = goal.tau
    n_samples = len(goal.samples)
    goal_min = np.full(n_samples, np.inf)
    covered_at = np.full(n_samples, np.nan)        # time (s) each goal sample was first covered
    curve: List[Tuple[float, float]] = [(0.0, 0.0)]
    events: List[DivergenceEvent] = []
    per_stroke = []
    n_in = n_tot = 0
    all_ink: List[np.ndarray] = []
    ink_stroke: List[np.ndarray] = []
    off_n = 0
    for k, raw in enumerate(strokes):
        dense = _densify(raw)
        all_ink.append(dense)
        ink_stroke.append(np.full(len(dense), k))
        d_goal = kg.min_dists(dense[:, :2], goal.dense)
        inside = d_goal <= tau
        n_in += int(inside.sum())
        n_tot += len(dense)
        # off-path runs (in arc length ~ points at 1 px spacing)
        off_px = 0
        i = 0
        while i < len(dense):
            if inside[i]:
                i += 1
                continue
            j = i
            while j < len(dense) and not inside[j]:
                j += 1
            run = j - i
            if run > 2 * tau:
                off_px += run
                t0, t1 = float(dense[i, 2]) / 1000.0, float(dense[j - 1, 2]) / 1000.0
                mid = dense[(i + j) // 2]
                worst = float(d_goal[i:j].max())
                off_n += 1
                events.append(DivergenceEvent(
                    metric="kolam.precision", kind="off_path_ink", position=round(t0, 3), position_kind="time",
                    evidence=_ev(f"ev.{attempt.source_id}.off_path.{off_n:02d}", locators.with_index(trace_id, "stroke", k),
                                 Modality.SENSOR, f"stroke {k}: {run} px of ink beyond the {tau:.1f} px band (max {worst:.1f} px) near ({mid[0]:.0f}, {mid[1]:.0f})",
                                 round(t0, 3), round(max(t0, t1), 3)),
                    detail=f"stroke {k} left the target line for {run} px (up to {worst:.1f} px away, tolerance {tau:.1f} px) at {t0:.2f}s",
                ))
            i = j
        # coverage updates in chunks for the progress curve
        for a in range(0, len(dense), CURVE_CHUNK):
            chunk = dense[a : a + CURVE_CHUNK]
            dm = kg.min_dists(goal.samples, chunk[:, :2])
            newly = (dm <= tau) & np.isnan(covered_at)
            covered_at[newly] = float(chunk[-1, 2]) / 1000.0
            goal_min = np.minimum(goal_min, dm)
            curve.append((round(float(chunk[-1, 2]) / 1000.0, 3), round(float((goal_min <= tau).mean()), 4)))
        per_stroke.append({
            "stroke": k, "points": int(len(raw)),
            "t_start": round(float(raw[0, 2]) / 1000.0, 3), "t_end": round(float(raw[-1, 2]) / 1000.0, 3),
            "length_px": round(float(len(dense) - 1), 1),
            "coverage_after": round(float((goal_min <= tau).mean()), 4),
            "precision_after": round(n_in / max(1, n_tot), 4),
            "off_path_px": int(off_px),
        })
    covered = goal_min <= tau
    coverage = float(covered.mean())
    precision = n_in / max(1, n_tot)
    ink = np.concatenate(all_ink)
    ink_k = np.concatenate(ink_stroke)
    end_t = float(max(s[-1, 2] for s in strokes)) / 1000.0

    # dot relations
    rels = _dot_relations(goal, ink[:, :2], covered)
    dot_events = []
    for r in rels:
        if r["assessed"] and not r["match"] and r["nearest_index"] >= 0:
            p = ink[r["nearest_index"]]
            k = int(ink_k[r["nearest_index"]])
            t = float(p[2]) / 1000.0
            what = ("passes beside it" if r["goal"] == "on_line" else "touches it")
            dot_events.append(DivergenceEvent(
                metric="kolam.dot_relation_match", kind="dot_relation", position=round(t, 3), position_kind="time",
                evidence=_ev(f"ev.{attempt.source_id}.dot.{r['dot_id']}", locators.with_index(trace_id, "stroke", k), Modality.SENSOR,
                             f"stroke {k}: dot {r['dot_id']} should be {r['goal']}; learner line {what} at {r['distance']:.1f} px",
                             round(t, 3), round(t, 3)),
                detail=f"dot {r['dot_id']} is {r['goal']} in the target, but the learner's line {what} ({r['distance']:.1f} px from its centre) in stroke {k} at {t:.2f}s",
            ))
    events.extend(dot_events)

    # stage / curve completion and order
    stage_cov, curve_cov = _completion(goal, covered)
    completion_time = {}
    for s, sid in enumerate(goal.stage_ids):
        times = covered_at[goal.stage_of_sample == s]
        if stage_cov[sid] >= COMPLETE_AT:
            completion_time[sid] = float(np.nanquantile(times, COMPLETE_AT)) if np.isfinite(times).any() else None
    order = sorted(completion_time, key=lambda s: (completion_time[s], goal.stage_ids.index(s)))
    for s, sid in enumerate(goal.stage_ids):
        if stage_cov[sid] < COMPLETE_AT:
            events.append(DivergenceEvent(
                metric="kolam.coverage", kind="incomplete_stage", position=round(end_t + 0.001 * (s + 1), 3), position_kind="time",
                evidence=_ev(f"ev.{attempt.source_id}.incomplete.{sid}", trace_id, Modality.SENSOR,
                             f"goal stage {sid} ({_stage_bbox_pct(goal, s)}) only {stage_cov[sid]:.0%} covered by the end of the attempt",
                             round(end_t, 3), round(end_t, 3)),
                detail=f"suggested stage {sid} reached {stage_cov[sid]:.0%} coverage (needs {COMPLETE_AT:.0%}) by the end ({end_t:.2f}s)",
                severity="material" if stage_cov[sid] < 0.5 else "minor",
            ))
    events.sort(key=lambda e: (e.position, e.kind, e.evidence.evidence_id))

    curves_done = sum(1 for v in curve_cov.values() if v >= COMPLETE_AT)
    n_strokes = len(strokes)
    excess = max(0, n_strokes - goal.k)
    first_off = next((e for e in events if e.kind == "off_path_ink"), None)
    first_dot = next((e for e in events if e.kind == "dot_relation"), None)
    worst_stage = min(stage_cov, key=lambda s: (stage_cov[s], s))
    trace_ev = _ev(f"ev.{attempt.source_id}.trace", trace_id, Modality.SENSOR,
                   f"{n_strokes} strokes, {end_t:.1f}s", 0.0, round(end_t, 3))
    metrics = {
        "kolam.coverage": MetricValue(
            round(coverage, 4),
            f"{coverage:.1%} of the target line ({int(covered.sum())}/{n_samples} samples) has learner ink within {tau:.1f} px; "
            f"least-covered stage {worst_stage} at {stage_cov[worst_stage]:.0%}", evidence=trace_ev),
        "kolam.precision": MetricValue(
            round(precision, 4),
            f"{precision:.1%} of learner ink ({n_in}/{n_tot} px) lies within {tau:.1f} px of the target line; "
            f"{sum(1 for e in events if e.kind == 'off_path_ink')} off-path run(s) longer than {2 * tau:.0f} px",
            evidence=first_off.evidence if first_off else trace_ev, position=first_off.position if first_off else None),
        "kolam.dot_relation_match": _dot_metric(rels, first_dot.evidence if first_dot else None,
                                                first_dot.position if first_dot else None),
        "kolam.curves_completed_ratio": MetricValue(
            round(curves_done / goal.k, 4),
            f"{curves_done} of {goal.k} continuous line(s) completed (coverage >= {COMPLETE_AT:.0%}): "
            + ", ".join(f"{c} {v:.0%}" for c, v in curve_cov.items()), evidence=trace_ev),
        "kolam.pen_lifts_excess": MetricValue(
            float(excess),
            f"{n_strokes} stroke(s) for {goal.k} continuous line(s): {excess} pen lift(s) in excess", evidence=trace_ev),
        "kolam.stages_completed_ratio": MetricValue(
            round(sum(1 for v in stage_cov.values() if v >= COMPLETE_AT) / len(stage_cov), 4),
            f"{sum(1 for v in stage_cov.values() if v >= COMPLETE_AT)} of {len(stage_cov)} suggested stages completed: "
            + ", ".join(f"{s} {v:.0%}" for s, v in stage_cov.items()), evidence=trace_ev),
    }
    first_material = next((e for e in events if e.severity == "material"), None)
    final_state = {
        "input": "trace", "coverage": round(coverage, 4), "precision": round(precision, 4),
        "n_strokes": n_strokes, "duration_sec": round(end_t, 3), "stage_coverage": stage_cov, "curve_coverage": curve_cov,
        "dot_relations": [{k2: v for k2, v in r.items() if k2 != "nearest_index"} for r in rels],
        "first_divergence": None if first_material is None else {
            "kind": first_material.kind, "position": first_material.position, "locator": first_material.evidence.source_id},
    }
    artifacts = {
        "per_stroke": per_stroke,
        "stage_completion_order": {"order": order, "times_sec": {s: round(t, 3) for s, t in completion_time.items() if t is not None},
                                   "suggested_order": goal.stage_ids, "note": ORDER_NOTE},
        "tau_px": round(tau, 3),
    }
    return TrajectoryResult(metrics=metrics, events=events, curve=curve, curve_kind="time", process_observable=True,
                            final_state=final_state, artifacts=artifacts, warnings=warnings)


# ---------------------------------------------------------------------------------------
# image (photo / raster)
# ---------------------------------------------------------------------------------------


def _inverse(sim: kg.Similarity, pts: np.ndarray) -> np.ndarray:
    th = math.radians(sim.theta_deg)
    m = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]]) * sim.scale
    return (np.asarray(pts, dtype=np.float64) - np.array([sim.tx, sim.ty])) @ np.linalg.inv(m).T


def _img_region(source_id: str, pts: np.ndarray, shape: Tuple[int, int], pad: float) -> str:
    h, w = shape
    x0, y0 = pts.min(axis=0) - pad
    x1, y1 = pts.max(axis=0) + pad
    x0, y0, x1, y1 = max(0.0, x0), max(0.0, y0), min(float(w), x1), min(float(h), y1)
    return locators.with_region(source_id, 100 * x0 / w, 100 * y0 / h, 100 * max(0.0, x1 - x0) / w, 100 * max(0.0, y1 - y0) / h)


def _evaluate_image(goal: _Goal, attempt: AttemptMedia) -> TrajectoryResult:
    try:
        an = kg.analyze_image(attempt.path)
    except OSError as exc:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"unreadable image: {exc}") from exc
    lpts = an.skeleton_points()
    if len(lpts) < 10:
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, "no line work detected in the image")
    tau = goal.tau
    gdots = [kg.Dot(d.x, d.y, d.r) for d in goal.g.dots]
    sim = kg.register_similarity(lpts, an.dots, goal.dense, gdots, (goal.g.canvas.height, goal.g.canvas.width), tau)
    q = sim.apply(lpts)
    d_goal = kg.min_dists(q, goal.dense)
    inside = d_goal <= tau
    precision = float(inside.mean())
    # coverage and dot relations use the skeleton of the FULL ink (dots included, so the line
    # runs through on-line dots), minus tiny components (an untouched dot thins to a few pixels)
    full_skel = kg.remove_small_components(kg.thin(an.ink), int(max(6, round(4 * an.stroke_width * an.scale))))
    ys, xs = np.nonzero(full_skel)
    rel_pts = sim.apply(np.stack([xs, ys], axis=1).astype(np.float64) / an.scale)
    dm = kg.min_dists(goal.samples, rel_pts)
    covered = dm <= tau
    coverage = float(covered.mean())
    warnings: List[str] = []
    if sim.score < 0.5:
        warnings.append(f"registration to the goal is weak (score {sim.score:.2f}); final-state metrics may be unreliable")
    whole_ev = _ev(f"ev.{attempt.source_id}.image", attempt.source_id, Modality.IMAGE,
                   f"photo registered to goal: scale {sim.scale:.3f}, rotation {sim.theta_deg:.2f} deg ({sim.method})")
    # off-path ink regions: connected groups of off-band learner skeleton pixels
    events: List[DivergenceEvent] = []
    off = ~inside
    if off.any():
        mask = np.zeros(an.skeleton.shape, dtype=bool)
        sk = np.round(lpts[off] * an.scale).astype(int)
        mask[np.clip(sk[:, 1], 0, mask.shape[0] - 1), np.clip(sk[:, 0], 0, mask.shape[1] - 1)] = True
        lab, n = kg.label_components(kg.dilate(mask, 1.5))
        regions = []
        for r in range(1, n + 1):
            ys, xs = np.nonzero((lab == r) & mask)
            if len(ys) * (1.0 / an.scale) * sim.scale > 2 * tau:
                regions.append(np.stack([xs, ys], axis=1) / an.scale)
        regions.sort(key=lambda p: (-len(p), float(p[:, 1].min()), float(p[:, 0].min())))
        for i, pts in enumerate(regions):
            gp = sim.apply(pts.mean(axis=0, keepdims=True))[0]
            events.append(DivergenceEvent(
                metric="kolam.precision", kind="off_path_ink", position=0.0, position_kind="stroke",
                evidence=_ev(f"ev.{attempt.source_id}.off_path.{i + 1:02d}", _img_region(attempt.source_id, pts, an.shape, 4.0),
                             Modality.IMAGE, f"{len(pts)} px of ink outside the {tau:.1f} px band near goal ({gp[0]:.0f}, {gp[1]:.0f})"),
                detail=f"ink region of ~{len(pts) * sim.scale:.0f} px lies off the target line (when it was drawn is not observable from a final image)",
            ))
    rels = _dot_relations(goal, rel_pts, covered)
    for r in rels:
        if r["assessed"] and not r["match"]:
            d = next(x for x in goal.g.dots if x.id == r["dot_id"])
            lp = _inverse(sim, np.array([[d.x, d.y]]))
            events.append(DivergenceEvent(
                metric="kolam.dot_relation_match", kind="dot_relation", position=0.0, position_kind="stroke",
                evidence=_ev(f"ev.{attempt.source_id}.dot.{r['dot_id']}", _img_region(attempt.source_id, lp, an.shape, 3 * d.r / max(sim.scale, 1e-6)),
                             Modality.IMAGE, f"dot {r['dot_id']} should be {r['goal']}; nearest learner line {r['distance']:.1f} px"),
                detail=f"dot {r['dot_id']} is {r['goal']} in the target; learner line {r['distance']:.1f} px from its centre",
            ))
    stage_cov, curve_cov = _completion(goal, covered)
    curves_done = sum(1 for v in curve_cov.values() if v >= COMPLETE_AT)
    first_off = next((e for e in events if e.kind == "off_path_ink"), None)
    first_dot = next((e for e in events if e.kind == "dot_relation"), None)
    metrics = {
        "kolam.coverage": MetricValue(round(coverage, 4),
                                      f"{coverage:.1%} of the target line ({int(covered.sum())}/{len(covered)} samples) has learner ink within {tau:.1f} px after registration",
                                      evidence=whole_ev),
        "kolam.precision": MetricValue(round(precision, 4),
                                       f"{precision:.1%} of learner line pixels ({int(inside.sum())}/{len(inside)}) lie within {tau:.1f} px of the target line; "
                                       f"{sum(1 for e in events if e.kind == 'off_path_ink')} off-path region(s)",
                                       evidence=first_off.evidence if first_off else whole_ev),
        "kolam.dot_relation_match": _dot_metric(rels, first_dot.evidence if first_dot else None, None),
        "kolam.curves_completed_ratio": MetricValue(round(curves_done / goal.k, 4),
                                                    f"{curves_done} of {goal.k} continuous line(s) completed: " + ", ".join(f"{c} {v:.0%}" for c, v in curve_cov.items()),
                                                    evidence=whole_ev),
        "kolam.stages_completed_ratio": MetricValue(
            round(sum(1 for v in stage_cov.values() if v >= COMPLETE_AT) / len(stage_cov), 4),
            f"{sum(1 for v in stage_cov.values() if v >= COMPLETE_AT)} of {len(stage_cov)} suggested stages present: "
            + ", ".join(f"{s} {v:.0%}" for s, v in stage_cov.items()), evidence=whole_ev),
        "kolam.pen_lifts_excess": MetricValue(None, f"pen lifts cannot be counted: {PROCESS_UNOBSERVABLE}",
                                              uncertain_reason=PROCESS_UNOBSERVABLE),
        "kolam.first_divergence": MetricValue(None, f"first divergence in time cannot be located: {PROCESS_UNOBSERVABLE}",
                                              uncertain_reason=PROCESS_UNOBSERVABLE),
    }
    final_state = {
        "input": "image", "coverage": round(coverage, 4), "precision": round(precision, 4),
        "stage_coverage": stage_cov, "curve_coverage": curve_cov,
        "dot_relations": [{k2: v for k2, v in r.items() if k2 != "nearest_index"} for r in rels],
        "detected_dots": len(an.dots),
        "registration": {"scale": round(sim.scale, 4), "theta_deg": round(sim.theta_deg, 3), "tx": round(sim.tx, 2),
                         "ty": round(sim.ty, 2), "score": round(sim.score, 4), "method": sim.method},
        "first_divergence": None,
    }
    artifacts = {"tau_px": round(tau, 3), "note": PROCESS_UNOBSERVABLE}
    return TrajectoryResult(metrics=metrics, events=events, curve=[], curve_kind="stroke", process_observable=False,
                            final_state=final_state, artifacts=artifacts, warnings=warnings)


def evaluate(goal: GoalModel, attempt: AttemptMedia, ctx: Any = None) -> TrajectoryResult:
    g = _Goal(goal)
    if attempt.kind == "trace":
        return _evaluate_trace(g, attempt)
    if attempt.kind == "image":
        return _evaluate_image(g, attempt)
    raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"kolam accepts trace or image attempts, not {attempt.kind!r}")
