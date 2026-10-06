"""Kolam goal builder: finished kolam image (ONLY input) -> GoalModel payload, grounded claims,
criterion templates and a practice task. docs/plans/evaluation-core.md §3.1.

Deterministic geometry (``tracks.common.kolam_geometry``) produces every number. Computed
properties are OBSERVED claims; the drawing path (curve decomposition + stage order) is an
INFERRED reconstruction ("one suggested way"). An optional Gemma call adds a plain
description and instruction wording; it can only add warnings, never override geometry.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, Field

from tracks.common import kolam_geometry as kg
from tracks.common import locators
from tracks.common.casedata import Band, ObserverBinding, SourceRecord
from tracks.common.goals.kolam import MIN_STAGES, SAMPLE_STEP_PX, KolamGoal, payload_from_image
from tracks.common.models import AnveshanFailure, FailureCategory, ImagePart, ModelError, load_prompt
from tracks.common.schemas import EvidenceRef, KnowledgeClaim, TaskConstraint
from tracks.common.schemas.evidence import Modality, VerificationState
from tracks.common.schemas.knowledge import ClaimType

from . import CriterionTemplate, GoalBuildResult

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "kolam_describe_v1.txt"
PROMPT_ID = "kolam_describe"
INFERRED_CONFIDENCE = 0.4

_FORBIDDEN = ("artist", "tradition", "meaning", "symboli", "festival", "history", "originally drawn", "auspicious")


class _StageInstruction(BaseModel):
    stage_id: str
    instruction: str


class KolamDescribeDTO(BaseModel):
    description: str
    motif_guess: Optional[str] = None
    rotation_order_estimate: Optional[int] = None
    curve_count_estimate: Optional[int] = None
    stage_instructions: List[_StageInstruction] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------


def _pct_region(source_id: str, pts: np.ndarray, size: Tuple[int, int], pad: float) -> str:
    w, h = size
    x0, y0 = pts.min(axis=0) - pad
    x1, y1 = pts.max(axis=0) + pad
    x0, y0 = max(0.0, float(x0)), max(0.0, float(y0))
    x1, y1 = min(float(w), float(x1)), min(float(h), float(y1))
    return locators.with_region(source_id, 100 * x0 / w, 100 * y0 / h, 100 * (x1 - x0) / w, 100 * (y1 - y0) / h)


def _pct(p: Sequence[float], size: Tuple[int, int]) -> str:
    return f"({100 * p[0] / size[0]:.0f}% across, {100 * p[1] / size[1]:.0f}% down)"


def _ev(evidence_id: str, locator: str, excerpt: str, observed: bool) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=evidence_id,
        source_id=locator,
        modality=Modality.IMAGE,
        start_sec=None,
        end_sec=None,
        cue_excerpt=excerpt,
        verification_state=VerificationState.OBSERVED if observed else VerificationState.INFERRED,
        confidence=1.0 if observed else INFERRED_CONFIDENCE,
    )


def _ring_summary(dots: List[kg.Dot], centre: Sequence[float]) -> str:
    if len(dots) < 2:
        return ""
    r = sorted(math.hypot(d.x - centre[0], d.y - centre[1]) for d in dots)
    groups: List[List[float]] = []
    for v in r:
        if groups and v - groups[-1][-1] <= 4.0:
            groups[-1].append(v)
        else:
            groups.append([v])
    parts = [f"{len(g)} at radius ~{np.mean(g):.0f} px" for g in groups]
    return "; by distance from the centre: " + ", ".join(parts)


def _clean_model_text(text: str) -> Tuple[str, bool]:
    """Drop sentences that assert provenance/meaning (not allowed from an image)."""
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    kept = [s for s in sentences if not any(f in s.lower() for f in _FORBIDDEN)]
    return (". ".join(kept) + ("." if kept else "")), len(kept) != len(sentences)


# ---------------------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------------------



def build(source_path: Path, source: SourceRecord, ctx: Any, *, case_id: str, version: int) -> GoalBuildResult:
    source_path = Path(source_path)
    payload, built_with = payload_from_image(source_path)
    built_with["builder"] = "track_a.goals.kolam@v1"
    goal = KolamGoal.model_validate(payload)
    sid = source.source_id
    size = (goal.canvas.width, goal.canvas.height)
    tau = goal.tau
    warnings: List[str] = []
    run_keys: List[str] = []
    k = len(goal.curves)
    n_dots = len(goal.dots)
    sym = goal.symmetry
    f = goal.features
    all_pts = np.concatenate([np.asarray(c.points) for c in goal.curves])
    whole = _pct_region(sid, all_pts, size, tau)
    dots_arr = np.array([[d.x, d.y] for d in goal.dots]) if goal.dots else all_pts
    dots_region = _pct_region(sid, dots_arr, size, 8.0)
    dot_objs = [kg.Dot(d.x, d.y, d.r) for d in goal.dots]

    # ---- optional Gemma enrichment --------------------------------------------------
    stages_flat = [(c, s) for c in goal.curves for s in c.stages]
    dto: Optional[KolamDescribeDTO] = None
    if ctx is not None and getattr(ctx, "gateway", None) is not None:
        summary = (f"- dots: {n_dots}\n- continuous curves: {k} ({f.n_closed} closed)\n"
                   f"- line crossings: {f.n_crossings}\n- rotational symmetry order: {sym.rotation_order}\n"
                   f"- mirror axes: {len(sym.mirror_axes_deg)}")
        stage_lines = []
        for c, s in stages_flat:
            pts = np.asarray(c.points)
            a, b = pts[s.start], pts[min(s.end, len(pts)) - 1]
            stage_lines.append(f"- {s.id}: from {_pct(a, size)} to {_pct(b, size)}")
        text, ver = load_prompt(PROMPT_PATH, computed_summary=summary, stages="\n".join(stage_lines))
        try:
            res = ctx.gateway.generate_json(
                model_key="text_image", prompt_id=PROMPT_ID, prompt_version=ver, prompt_text=text,
                schema=KolamDescribeDTO, parts=[ImagePart(source_path.read_bytes(), source.mime_type)],
                expected_behavior="plain description, symmetry/curve sanity check, per-stage wording; no provenance claims",
            )
            dto = res.data
            run_keys.append(res.metadata.replay_key)
        except ModelError as exc:
            warnings.append(f"kolam_describe model call unavailable ({exc.category.value}); built deterministically without model wording")
    if dto is not None:
        if dto.rotation_order_estimate is not None and dto.rotation_order_estimate != sym.rotation_order:
            warnings.append(f"model rotation-order estimate {dto.rotation_order_estimate} disagrees with computed {sym.rotation_order}; computed value kept")
        if dto.curve_count_estimate is not None and dto.curve_count_estimate != k:
            warnings.append(f"model curve-count estimate {dto.curve_count_estimate} disagrees with computed {k}; computed value kept")

    # ---- claims ------------------------------------------------------------------------
    claims: List[KnowledgeClaim] = []

    def add(ctype: ClaimType, statement: str, locator: str, excerpt: str, observed: bool) -> str:
        cid = f"CLM-{len(claims) + 1:02d}"
        claims.append(KnowledgeClaim(
            claim_id=cid, claim_type=ctype, statement=statement, is_observed=observed,
            evidence_refs=[_ev(f"ev.kolam.{cid.lower()}", locator, excerpt, observed)],
        ))
        return cid

    c_dots = add(ClaimType.CONDITION,
                 f"The finished kolam has {n_dots} pulli (dots){_ring_summary(dot_objs, sym.centre)}.",
                 dots_region, f"{n_dots} dots detected (computed)", True)
    closed_txt = ("a closed loop" if k == 1 else "all closed loops") if f.n_closed == k else f"{f.n_closed} closed, {k - f.n_closed} open"
    c_curves = add(ClaimType.CONDITION,
                   f"The line work forms {k} continuous line{'s' if k != 1 else ''} ({closed_txt}) when every "
                   f"one of the {f.n_crossings} crossings is read as two lines passing straight through.",
                   whole, f"{k} curve(s), {f.n_crossings} crossings (computed)", True)
    if sym.rotation_order >= 2:
        sym_txt = f"The pattern has {sym.rotation_order}-fold rotational symmetry about its centre"
    else:
        sym_txt = "No rotational symmetry was detected"
    sym_txt += (f" and {len(sym.mirror_axes_deg)} mirror ax{'es' if len(sym.mirror_axes_deg) != 1 else 'is'}."
                if sym.mirror_axes_deg else " and no mirror symmetry (it turns in one direction).")
    c_sym = add(ClaimType.CONDITION, sym_txt, whole, f"rotation order {sym.rotation_order} (computed overlap)", True)
    rc = f.relation_counts
    rel_parts = [f"{rc.get('on_line', 0)} dots lie on the line (it passes through them)"]
    if rc.get("enclosed", 0):
        rel_parts.append(f"{rc['enclosed']} {'is' if rc['enclosed'] == 1 else 'are'} enclosed by the line without touching it")
    if rc.get("free", 0):
        rel_parts.append(f"{rc['free']} {'is' if rc['free'] == 1 else 'are'} outside every loop")
    c_rel = add(ClaimType.CONDITION, "; ".join(rel_parts) + ".", dots_region, "dot-line relations (computed)", True)
    if f.free_endpoints == 0:
        ends_txt = "Every line in the image belongs to these continuous lines: there are no loose ends and no stray marks."
    else:
        ends_txt = f"The line work has {f.free_endpoints} loose end(s); the rest belongs to continuous lines."
    c_ends = add(ClaimType.CONDITION, ends_txt, whole, f"{f.free_endpoints} free line ends (computed)", True)

    instr_by_stage = {}
    if dto is not None:
        for si in dto.stage_instructions:
            txt, dropped = _clean_model_text(si.instruction)
            if dropped:
                warnings.append(f"dropped model wording asserting provenance/meaning in {si.stage_id}")
            if txt:
                instr_by_stage[si.stage_id] = txt
    step_ids: List[str] = []
    n_stages = len(stages_flat)
    dot_pos = {d.id: (d.x, d.y) for d in goal.dots}
    for idx, (c, s) in enumerate(stages_flat):
        pts = np.asarray(c.points)
        end = min(s.end, len(pts))
        seg = pts[s.start:end]
        a = seg[0]
        b = pts[end % len(pts)] if c.closed else seg[-1]
        on = [i for i in c.dot_ids if np.min(np.hypot(seg[:, 0] - dot_pos[i][0], seg[:, 1] - dot_pos[i][1])) <= 3.0]
        via = f", passing through {len(on)} dots" if on else ""
        stmt = (f"Suggested stage {idx + 1} of {n_stages} (one possible way, inferred from the final image; "
                f"line {c.id}): without lifting, draw from {_pct(a, size)} to {_pct(b, size)}{via}.")
        if s.id in instr_by_stage:
            stmt += f" Model wording (inferred): {instr_by_stage[s.id]}"
        step_ids.append(add(ClaimType.STEP, stmt, _pct_region(sid, seg, size, tau),
                            f"inferred stage {s.id}", False))
    if dto is not None:
        desc, dropped = _clean_model_text(dto.description)
        if dropped:
            warnings.append("dropped model description sentences asserting provenance/meaning")
        if desc:
            add(ClaimType.CUE, f"Model description of the image (inferred, unverified): {desc}", whole,
                "model description (inferred)", False)

    ev_of = {c.claim_id: c.evidence_refs[0].evidence_id for c in claims}

    def crit(cid: str, name: str, desc: str, indicator: str, weight: float, required: bool, order: int,
             cites: List[str], why: str, drill: str, obs: ObserverBinding) -> CriterionTemplate:
        return CriterionTemplate(criterion_id=cid, name=name, description=desc, observable_indicator=indicator,
                                 weight=weight, required=required, order_index=order, source_claim_ids=cites,
                                 reference_evidence_ids=[ev_of[c] for c in cites], why_it_matters=why,
                                 drill_hint=drill, observer=obs)

    first_step = step_ids[0]
    curves_partial = [Band(status="partially_satisfied", min=(k - 1) / k - 1e-6)] if k >= 2 else []
    criteria = [
        crit("CRIT-KOLAM-COVERAGE", "Every line of the target is drawn",
             "The learner's ink covers the target's continuous line(s) within the tolerance band.",
             f"fraction of goal line samples (every {SAMPLE_STEP_PX:.0f} px) with learner ink within {tau:.1f} px",
             3, True, 0, [c_curves] + step_ids[:1],
             f"The finished pattern is made of {k} continuous line{'s' if k != 1 else ''} through the dots ({c_curves}); a missing section leaves the figure open.",
             "Trace the faint goal line once, stage by stage, then redraw from memory.",
             ObserverBinding(metric="kolam.coverage", direction="higher_is_better",
                             bands=[Band(status="satisfied", min=0.90), Band(status="partially_satisfied", min=0.70)])),
        crit("CRIT-KOLAM-PRECISION", "No stray lines off the pattern",
             "The learner's ink stays on the target line(s).",
             f"fraction of learner ink samples within {tau:.1f} px of the goal line",
             2, True, 1, [c_ends],
             f"The target has no loose ends or stray marks ({c_ends}); in a powder kolam a stray line cannot be erased.",
             "Slow down at crossings and dots; keep the line inside the faint band.",
             ObserverBinding(metric="kolam.precision", direction="higher_is_better",
                             bands=[Band(status="satisfied", min=0.92), Band(status="partially_satisfied", min=0.80)])),
        crit("CRIT-KOLAM-DOTS", "Each pulli keeps the same relation to the line",
             "Dots the target line passes through are passed through; dots it leaves free stay untouched.",
             "fraction of assessed dots whose on-line / off-line relation matches the target",
             2, True, 2, [c_rel, c_dots],
             f"The dots fix the geometry: {rc.get('on_line', 0)} of {n_dots} lie on the line ({c_rel}) out of the dot grid ({c_dots}).",
             "Draw only the segment between two neighbouring dots, aiming straight through each dot.",
             ObserverBinding(metric="kolam.dot_relation_match", direction="higher_is_better",
                             bands=[Band(status="satisfied", min=0.95), Band(status="partially_satisfied", min=0.80)])),
        crit("CRIT-KOLAM-CURVES", "Each continuous line completed",
             "Every continuous line of the target reaches at least 90% coverage.",
             "fraction of goal curves with coverage >= 0.9",
             2, False, 3, [c_curves, first_step],
             f"Each of the {k} line{'s' if k != 1 else ''} closes on itself ({c_curves}); an unfinished line breaks the loop.",
             "Repeat the stage where the line stopped until it joins the next stage.",
             ObserverBinding(metric="kolam.curves_completed_ratio", direction="higher_is_better",
                             bands=[Band(status="satisfied", min=0.999)] + curves_partial)),
        crit("CRIT-KOLAM-CONTINUITY", "Drawn as continuous strokes",
             "The pattern is drawn with few pen lifts beyond the number of continuous lines.",
             f"number of strokes minus the {k} continuous line(s) (pen lifts in excess)",
             1, False, 4, [c_ends, c_curves],
             f"The figure is {k} unbroken line{'s' if k != 1 else ''} with no loose ends ({c_ends}), so it can be drawn without lifting the hand.",
             "Practise one stage in a single motion, keeping the pen down through the crossings.",
             ObserverBinding(metric="kolam.pen_lifts_excess", direction="lower_is_better",
                             bands=[Band(status="satisfied", max=1), Band(status="partially_satisfied", max=max(k, 3))],
                             process=True)),
    ]

    # ---- task ---------------------------------------------------------------------------
    lines = [
        f"1. The canvas shows the {n_dots} dots of the target [{c_dots}]. Draw on the canvas; the dots stay where they are.",
        f"2. The target is {k} continuous line{'s' if k != 1 else ''} with no loose ends [{c_curves}, {c_ends}]; try to draw each without lifting.",
        f"3. Pass through every dot the target line passes through, and keep dots the line leaves free untouched [{c_rel}].",
    ]
    n = 4
    for (c, s), clm in zip(stages_flat, step_ids):
        lines.append(f"{n}. Stage {s.id} - one suggested way (inferred), not the original drawing order: follow [{clm}].")
        n += 1
    lines.append(f"{n}. Check the finished drawing against the {sym.rotation_order}-fold symmetry of the target [{c_sym}].")
    task_instructions = "\n".join(lines)
    constraints = [
        TaskConstraint(constraint_type="tool_spec", description="Draw on the app canvas over the target dots (goal-image pixel coordinates).", value=f"{size[0]}x{size[1]} px"),
        TaskConstraint(constraint_type="material_spec", description="Continuous lines preferred: draw each line without lifting.", value=f"{k} line(s)"),
    ]

    built_with.update({"model_runs": run_keys, "prompt": f"{PROMPT_ID}@v1" if run_keys else None, "case_id": case_id, "version": version})
    title = "Kolam (final image): reconstruct the line through the dots"
    summary = (f"Finished kolam image only: {n_dots} dots, {k} continuous line(s), {f.n_crossings} crossings, "
               f"{sym.rotation_order}-fold rotation (computed). The {n_stages}-stage drawing path is an inferred suggestion.")
    return GoalBuildResult(
        title=title, summary=summary, goal_payload=payload, claims=claims, criteria=criteria,
        task_title="Draw the kolam on the dot grid", task_instructions=task_instructions,
        task_constraints=constraints, warnings=warnings, run_keys=run_keys, built_with=built_with,
    )
