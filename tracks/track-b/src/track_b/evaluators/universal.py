"""Universal trajectory evaluator (Layer 3).

Receives a GoalModel with modality="universal" whose payload is a SkillModel,
runs structure-appropriate checks, and returns a TrajectoryResult.

LAZY imports for tracks.common.perceivers (WP1 owns it). Import inside functions.
See docs/kiro/specs/K7-engines-generalise.md §4.
"""

from __future__ import annotations

import importlib
import json
import logging
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from tracks.common import locators
from tracks.common.casedata import GoalModel
from tracks.common.models import (
    AnveshanFailure,
    FailureCategory,
    ImagePart,
    ModelError,
    load_prompt,
)
from tracks.common.runtime import RunContext
from tracks.common.schemas import EvidenceRef
from tracks.common.schemas.evidence import Modality, VerificationState
from tracks.common.skill_model import SkillModel

from track_b.trajectory import AttemptMedia, DivergenceEvent, MetricValue, TrajectoryResult
from track_b.evaluators.universal_align import label_frames, mode_filter, needleman_wunsch

log = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parents[4] / "common" / "prompts"

UNIVERSAL_WARNING = "Universal pipeline: AI-perceived checks are lower confidence than specialist measurements"


# ---------------------------------------------------------------------------
# Evidence helpers
# ---------------------------------------------------------------------------

def _ev(eid: str, source_id: str, modality: Modality, excerpt: str,
        start: Optional[float] = None, end: Optional[float] = None) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=eid,
        source_id=source_id,
        modality=modality,
        start_sec=start,
        end_sec=end,
        cue_excerpt=excerpt,
        verification_state=VerificationState.OBSERVED,
        confidence=1.0,
    )


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

def _quality_gate(attempt: AttemptMedia, record: Any) -> None:
    """Raise INVALID_INPUT for unusable attempts."""
    if record is None:
        return
    obs = getattr(record, "observations", [])
    for o in obs:
        if o.kind != "measurement":
            continue
        lbl = o.label.lower()
        val = o.value
        if val is None:
            continue
        if attempt.kind == "image":
            if "blur" in lbl and val < 0.002:
                raise AnveshanFailure(
                    FailureCategory.INVALID_INPUT,
                    f"Image is too blurry (blur score {val:.4f} < 0.002); please re-record.",
                )
            if "brightness" in lbl and val < 0.02:
                raise AnveshanFailure(
                    FailureCategory.INVALID_INPUT,
                    f"Image is too dark (brightness {val:.3f} < 0.02); please re-record.",
                )
        elif attempt.kind == "audio":
            if "rms" in lbl and val < 0.005:
                raise AnveshanFailure(
                    FailureCategory.INVALID_INPUT,
                    "Audio is silent (RMS < 0.005); please re-record.",
                )


# ---------------------------------------------------------------------------
# Relevance gate
# ---------------------------------------------------------------------------

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na < 1e-9 or nb < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _relevance_gate(
    skill: SkillModel,
    attempt: AttemptMedia,
    attempt_record: Any,
    source_emb: Optional[np.ndarray],
    attempt_emb: Optional[np.ndarray],
    ctx: Optional[RunContext],
    source_record: Any,
    warnings: List[str],
) -> float:
    """Return similarity score, or raise INVALID_INPUT if irrelevant.
    Returns -1.0 if embeddings unavailable (skip gate).
    """
    if source_emb is None or attempt_emb is None:
        return -1.0

    rel = skill.relevance
    min_sim = rel.min_similarity
    amb_band = rel.ambiguous_band

    # Mean of reference segment rows vs attempt embedding
    ref_ids = rel.reference_segment_ids
    if attempt_record is None:
        return -1.0

    attempt_idx = getattr(attempt_record, "embedding_index", {})
    if not attempt_idx:
        return -1.0

    # Attempt: whole (image), or mean of keyframe rows (video)
    if attempt.kind == "image":
        row = attempt_idx.get("seg-000", 0)
        att_vec = attempt_emb[row] if row < len(attempt_emb) else attempt_emb[0]
    else:
        att_rows = [attempt_emb[r] for _, r in attempt_idx.items() if r < len(attempt_emb)]
        if not att_rows:
            return -1.0
        att_vec = np.mean(att_rows, axis=0)

    # Source reference
    source_idx = getattr(source_record, "embedding_index", {}) if source_record else {}
    ref_rows = [source_emb[source_idx[sid]] for sid in ref_ids
                if sid in source_idx and source_idx[sid] < len(source_emb)]
    if not ref_rows:
        ref_rows = [source_emb[0]] if len(source_emb) > 0 else None
    if not ref_rows:
        return -1.0
    src_vec = np.mean(ref_rows, axis=0)

    s = _cosine(att_vec, src_vec)

    if s < min_sim:
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT,
            f"This doesn't look like an attempt at {skill.skill_title} (similarity {s:.2f}). "
            f"Please upload {', '.join(skill.relevance.expected_kinds)}.",
            {"similarity": s, "min_similarity": min_sim},
        )

    if s < min_sim + amb_band and ctx is not None and getattr(ctx, "gateway", None) is not None:
        # Vision fast yes/no check
        try:
            _ambiguous_relevance_check(skill, attempt, source_record, ctx, s)
        except AnveshanFailure:
            raise
        except Exception as exc:
            warnings.append(f"Ambiguous relevance check failed: {exc}")

    return s


def _ambiguous_relevance_check(
    skill: SkillModel,
    attempt: AttemptMedia,
    source_record: Any,
    ctx: RunContext,
    similarity: float,
) -> None:
    """One vision_fast call to check relevance in the ambiguous band."""
    from pydantic import BaseModel

    class RelevanceDTO(BaseModel):
        relevant: bool = True
        reason: str = ""

    prompt_path = PROMPT_DIR / "relevance_v1.txt"
    if not prompt_path.exists():
        return
    prompt_text, ver = load_prompt(prompt_path, skill_title=skill.skill_title)

    # Try to get a source keyframe
    parts: List[Any] = []
    if source_record is not None:
        segs = getattr(source_record, "segments", [])
        for seg in segs:
            if seg.keyframe_asset and seg.kind == "time":
                # Load the keyframe from the asset dir if available
                # For now, pass without the image
                break

    if attempt.kind == "image" and attempt.path.exists():
        try:
            from PIL import Image
            import io
            img = Image.open(attempt.path)
            img.thumbnail((512, 512))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            parts.append(ImagePart(buf.getvalue(), "image/jpeg", "Attempt image"))
        except Exception:
            pass

    result = ctx.gateway.generate_json(
        model_key="vision_fast",
        prompt_id="relevance_check",
        prompt_version=ver,
        prompt_text=prompt_text,
        schema=RelevanceDTO,
        parts=parts,
        expected_behavior="yes/no relevance check for attempt image",
    )
    if not result.data.relevant:
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT,
            f"This doesn't look like an attempt at {skill.skill_title} (similarity {similarity:.2f}; {result.data.reason}). "
            f"Please upload {', '.join(skill.relevance.expected_kinds)}.",
            {"similarity": similarity, "reason": result.data.reason},
        )


# ---------------------------------------------------------------------------
# Final-state checks
# ---------------------------------------------------------------------------

def _judge_final(
    skill: SkillModel,
    attempt: AttemptMedia,
    attempt_record: Any,
    source_record: Any,
    source_emb: Optional[np.ndarray],
    attempt_emb: Optional[np.ndarray],
    ctx: Optional[RunContext],
    warnings: List[str],
) -> Dict[str, MetricValue]:
    """Run final_state checks: similarity + model property judgements."""
    metrics: Dict[str, MetricValue] = {}

    # Similarity
    sim_val = None
    source_idx = getattr(source_record, "embedding_index", {}) if source_record else {}
    attempt_idx = getattr(attempt_record, "embedding_index", {}) if attempt_record else {}

    if source_emb is not None and attempt_emb is not None and source_idx and attempt_idx:
        # Source: last keyframe or whole
        if "seg-000" in source_idx:
            src_row = source_emb[source_idx["seg-000"]]
        elif source_idx:
            src_row = source_emb[list(source_idx.values())[-1]]
        else:
            src_row = source_emb[0]

        # Attempt: whole for image, last keyframe for video
        if attempt.kind == "image" and "seg-000" in attempt_idx:
            att_row = attempt_emb[attempt_idx["seg-000"]]
        else:
            att_keys = sorted(attempt_idx.keys())
            att_row = attempt_emb[attempt_idx[att_keys[-1]]] if att_keys else attempt_emb[0]

        sim_val = _cosine(src_row, att_row)

    sim_ev = _ev(f"ev.universal.final_sim.{attempt.source_id[:8]}",
                 attempt.source_id, _modality_enum(attempt.mime_type),
                 f"cosine similarity {sim_val:.3f}" if sim_val is not None else "embedding unavailable")
    metrics["u.final_similarity"] = MetricValue(
        sim_val,
        f"Cosine similarity: {sim_val:.3f}" if sim_val is not None else "embeddings not available",
        evidence=sim_ev,
    )

    # Model property judgements (one vision_fast call for all final_property checks)
    final_prop_checks = [c for c in skill.checks if c.kind == "final_property" and c.enabled]
    if final_prop_checks and ctx is not None and getattr(ctx, "gateway", None) is not None:
        judge_results = _call_judge_final(skill, attempt, source_record, final_prop_checks, ctx, warnings)
        for check in final_prop_checks:
            result = judge_results.get(check.check_id)
            if result is None:
                metrics[check.metric_id] = MetricValue(
                    None, "not reported by model", uncertain_reason="not reported by model"
                )
            else:
                status = result.get("status", "cannot_tell")
                finding = result.get("finding", "")
                if status == "met":
                    value = 1.0
                elif status == "partly":
                    value = 0.5
                elif status == "not_met":
                    value = 0.0
                else:  # cannot_tell
                    value = None
                    finding = finding or "model could not tell from the evidence"

                region = result.get("region")
                if region and len(region) == 4:
                    ev_id = locators.with_region(attempt.source_id, *region)
                else:
                    ev_id = attempt.source_id
                ev = _ev(
                    f"ev.universal.fprop.{check.check_id.lower()}.{attempt.source_id[:8]}",
                    ev_id,
                    _modality_enum(attempt.mime_type),
                    finding[:200],
                )
                metrics[check.metric_id] = MetricValue(
                    value,
                    finding,
                    evidence=ev,
                    uncertain_reason="model could not tell from the evidence" if status == "cannot_tell" else None,
                )
    else:
        for check in final_prop_checks:
            metrics[check.metric_id] = MetricValue(
                None, "model gateway not available", uncertain_reason="model gateway not available"
            )

    return metrics


def _call_judge_final(
    skill: SkillModel,
    attempt: AttemptMedia,
    source_record: Any,
    checks: List[Any],
    ctx: RunContext,
    warnings: List[str],
) -> Dict[str, Any]:
    """One vision_fast call for all final_property checks."""
    from pydantic import BaseModel

    class CheckResult(BaseModel):
        check_id: str = ""
        status: str = "cannot_tell"
        finding: str = ""
        region: Optional[List[float]] = None

    class JudgeFinalDTO(BaseModel):
        results: List[CheckResult] = []

    prompt_path = PROMPT_DIR / "judge_final_v1.txt"
    if not prompt_path.exists():
        return {}

    checks_json = json.dumps([
        {"check_id": c.check_id, "target_statement": c.observable_indicator}
        for c in checks
    ], indent=2)

    prompt_text, ver = load_prompt(prompt_path, checks_json=checks_json)

    parts: List[Any] = []
    # Attempt final image (≤ 2 images, max side 512)
    if attempt.kind == "image" and attempt.path.exists():
        try:
            from PIL import Image
            import io
            img = Image.open(attempt.path)
            img.thumbnail((512, 512))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=75)
            parts.append(ImagePart(buf.getvalue(), "image/jpeg", "Attempt image"))
        except Exception as exc:
            warnings.append(f"Could not load attempt image: {exc}")

    try:
        result = ctx.gateway.generate_json(
            model_key="vision_fast",
            prompt_id="judge_final",
            prompt_version=ver,
            prompt_text=prompt_text,
            schema=JudgeFinalDTO,
            parts=parts,
            expected_behavior="judge final properties of the attempt",
        )
        return {r.check_id: r.model_dump() for r in result.data.results}
    except ModelError as exc:
        warnings.append(f"judge_final model call failed: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Procedure alignment
# ---------------------------------------------------------------------------

def _procedure_checks(
    skill: SkillModel,
    attempt: AttemptMedia,
    attempt_record: Any,
    source_emb: Optional[np.ndarray],
    attempt_emb: Optional[np.ndarray],
    source_record: Any,
    ctx: Optional[RunContext],
    warnings: List[str],
) -> Tuple[Dict[str, MetricValue], List[DivergenceEvent], List[Tuple[float, float]]]:
    """Run procedure checks. Returns (metrics, events, curve)."""
    metrics: Dict[str, MetricValue] = {}
    events: List[DivergenceEvent] = []
    curve: List[Tuple[float, float]] = [(0.0, 0.0)]

    if attempt.kind != "video":
        # Image attempt for a procedure: process checks UNCERTAIN
        for check in skill.checks:
            if check.process and check.enabled:
                metrics[check.metric_id] = MetricValue(
                    None,
                    "process not observable from an image attempt",
                    uncertain_reason="process_observable=False for image attempts",
                )
        return metrics, events, curve

    if source_emb is None or attempt_emb is None:
        for check in skill.checks:
            if check.kind in ("step_coverage", "step_order", "off_path") and check.enabled:
                metrics[check.metric_id] = MetricValue(
                    None, "embeddings not available", uncertain_reason="embeddings not available"
                )
        return metrics, events, curve

    n_steps = len(skill.steps)
    if n_steps == 0:
        return metrics, events, curve

    # Source: step keyframe rows
    source_idx = getattr(source_record, "embedding_index", {}) if source_record else {}
    step_rows: List[Optional[np.ndarray]] = []
    for step in skill.steps:
        seg_id = step.segment_id
        if seg_id and seg_id in source_idx and source_idx[seg_id] < len(source_emb):
            step_rows.append(source_emb[source_idx[seg_id]])
        else:
            # Fallback: use the nth row if available
            idx = step.index
            if idx < len(source_emb):
                step_rows.append(source_emb[idx])
            else:
                step_rows.append(source_emb[-1])

    step_vecs = np.stack(step_rows)  # (N, D)

    # Attempt: per-frame rows from specialists["frames"]
    att_specialists = getattr(attempt_record, "specialists", {}) if attempt_record else {}
    frames_info = att_specialists.get("frames", {})
    frame_rows = frames_info.get("rows", [])
    frame_times = frames_info.get("times", [])

    if not frame_rows or attempt_emb is None:
        for check in skill.checks:
            if check.kind in ("step_coverage", "step_order", "off_path") and check.enabled:
                metrics[check.metric_id] = MetricValue(
                    None, "frame embeddings not available", uncertain_reason="frame embeddings not available"
                )
        return metrics, events, curve

    # Build frame embedding matrix
    valid_rows = [r for r in frame_rows if r < len(attempt_emb)]
    if not valid_rows:
        return metrics, events, curve
    frame_vecs = attempt_emb[valid_rows]  # (F, D)
    n_frames = len(frame_vecs)

    # Label frames
    raw_labels = label_frames(frame_vecs, step_vecs, margin=0.03, floor=0.60)
    filt_labels = mode_filter(raw_labels, window=3)

    # Extract step index labels
    step_labels: List[int] = [l for l in filt_labels if isinstance(l, int)]
    obs_seq = step_labels  # sequence of step indices seen

    expected = list(range(n_steps))
    nw = needleman_wunsch(obs_seq, expected)

    n_matched = nw["matched"]
    coverage = n_matched / n_steps if n_steps > 0 else 0.0
    violations = nw["violations"]

    # Count off-path runs lasting >= 2s
    off_path_count = 0
    i = 0
    while i < len(filt_labels):
        if filt_labels[i] == "off":
            j = i
            while j < len(filt_labels) and filt_labels[j] == "off":
                j += 1
            if frame_times and len(frame_times) > j - 1 and len(frame_times) > i:
                t_start = frame_times[i] if i < len(frame_times) else 0.0
                t_end = frame_times[min(j - 1, len(frame_times) - 1)]
                if t_end - t_start >= 2.0:
                    off_path_count += 1
            i = j
        else:
            i += 1

    # Coverage metric
    ev_cov = _ev(f"ev.universal.coverage.{attempt.source_id[:8]}",
                 attempt.source_id, Modality.VIDEO, f"step coverage {coverage:.2f}",
                 0.0, frame_times[-1] if frame_times else 0.0)
    metrics["u.step_coverage"] = MetricValue(coverage, f"Matched {n_matched}/{n_steps} steps", evidence=ev_cov)

    # Order metric
    ev_ord = _ev(f"ev.universal.order.{attempt.source_id[:8]}",
                 attempt.source_id, Modality.VIDEO, f"order violations {violations}",
                 0.0, frame_times[-1] if frame_times else 0.0)
    metrics["u.step_order"] = MetricValue(float(violations), f"{violations} order violation(s)", evidence=ev_ord)

    # Off-path metric
    ev_off = _ev(f"ev.universal.offpath.{attempt.source_id[:8]}",
                 attempt.source_id, Modality.VIDEO, f"off-path runs {off_path_count}",
                 0.0, frame_times[-1] if frame_times else 0.0)
    metrics["u.off_path"] = MetricValue(float(off_path_count), f"{off_path_count} off-path run(s) >= 2s", evidence=ev_off)

    # Events for missing steps
    alignment = nw.get("alignment", [])
    for obs_step, exp_step in alignment:
        if obs_step is None and exp_step is not None:
            # Missing step — interpolated position
            frac = exp_step / max(n_steps - 1, 1)
            t_pos = (frame_times[-1] if frame_times else 0.0) * frac
            events.append(DivergenceEvent(
                metric="u.step_coverage",
                kind="missing_state",
                position=t_pos,
                position_kind="time",
                evidence=_ev(f"ev.universal.missing.step{exp_step}.{attempt.source_id[:8]}",
                             attempt.source_id, Modality.VIDEO,
                             f"Step {exp_step} ({skill.steps[exp_step].name if exp_step < n_steps else '?'}) not found",
                             t_pos, t_pos),
                detail=f"Step {exp_step} not found in attempt",
            ))

    # Curve: (time, max step fraction)
    if frame_times:
        max_matched = 0
        for i, (t, lbl) in enumerate(zip(frame_times, filt_labels)):
            if isinstance(lbl, int):
                max_matched = max(max_matched, lbl + 1)
            curve.append((t, max_matched / n_steps if n_steps > 0 else 0.0))

    # Final state match check for procedure
    for check in skill.checks:
        if check.metric_id == "u.final_state_match" and check.enabled:
            if ctx is not None and getattr(ctx, "gateway", None) is not None:
                judge_results = _call_judge_final(
                    skill, attempt, source_record, [check], ctx, warnings
                )
                result = judge_results.get(check.check_id)
                if result:
                    status = result.get("status", "cannot_tell")
                    value = {"met": 1.0, "partly": 0.5, "not_met": 0.0}.get(status)
                    metrics[check.metric_id] = MetricValue(
                        value, result.get("finding", ""),
                        uncertain_reason=("model could not tell from the evidence" if status == "cannot_tell" else None)
                    )
                else:
                    metrics[check.metric_id] = MetricValue(None, "not reported by model",
                                                           uncertain_reason="not reported by model")
            else:
                metrics[check.metric_id] = MetricValue(
                    None, "model gateway not available", uncertain_reason="model gateway not available"
                )

    # Step quality check for critical step
    critical_steps = [s for s in skill.steps if s.critical]
    for check in skill.checks:
        if check.kind == "step_quality" and check.enabled and critical_steps:
            cstep = critical_steps[0]
            if ctx is not None and getattr(ctx, "gateway", None) is not None:
                metrics[check.metric_id] = _judge_step_quality(
                    skill, attempt, cstep, source_emb, source_record, attempt_emb, attempt_record, ctx, warnings
                )
            else:
                metrics[check.metric_id] = MetricValue(
                    None, "model gateway not available", uncertain_reason="model gateway not available"
                )

    return metrics, events, curve


def _judge_step_quality(
    skill: SkillModel,
    attempt: AttemptMedia,
    step: Any,
    source_emb: Optional[np.ndarray],
    source_record: Any,
    attempt_emb: Optional[np.ndarray],
    attempt_record: Any,
    ctx: RunContext,
    warnings: List[str],
) -> MetricValue:
    """One judge_step call for a critical step."""
    from pydantic import BaseModel

    class JudgeStepDTO(BaseModel):
        status: str = "cannot_tell"
        finding: str = ""

    prompt_path = PROMPT_DIR / "judge_step_v1.txt"
    if not prompt_path.exists():
        return MetricValue(None, "prompt not found", uncertain_reason="prompt not found")

    prompt_text, ver = load_prompt(prompt_path, step_description=f"{step.name}: {step.state_after}")

    parts: List[Any] = []
    # Try to load attempt frame that best matches the critical step
    att_specialists = getattr(attempt_record, "specialists", {}) if attempt_record else {}
    frames_info = att_specialists.get("frames", {}) if att_specialists else {}
    frame_rows = frames_info.get("rows", [])
    frame_times = frames_info.get("times", [])

    if frame_rows and attempt_emb is not None:
        source_idx = getattr(source_record, "embedding_index", {}) if source_record else {}
        seg_id = step.segment_id
        if seg_id and seg_id in source_idx:
            step_vec = source_emb[source_idx[seg_id]]
            # Find best matching attempt frame
            valid = [(i, frame_rows[i]) for i in range(len(frame_rows)) if frame_rows[i] < len(attempt_emb)]
            if valid:
                sims = [float(np.dot(attempt_emb[r], step_vec)) for _, r in valid]
                best_i = int(np.argmax(sims))

    try:
        result = ctx.gateway.generate_json(
            model_key="vision_fast",
            prompt_id="judge_step",
            prompt_version=ver,
            prompt_text=prompt_text,
            schema=JudgeStepDTO,
            parts=parts,
            expected_behavior="judge quality of critical step",
        )
        status = result.data.status
        value = {"met": 1.0, "partly": 0.5, "not_met": 0.0}.get(status)
        return MetricValue(
            value,
            result.data.finding,
            uncertain_reason="model could not tell from the evidence" if status == "cannot_tell" else None,
        )
    except ModelError as exc:
        warnings.append(f"judge_step model call failed: {exc}")
        return MetricValue(None, f"model call failed: {exc}", uncertain_reason=str(exc))


# ---------------------------------------------------------------------------
# Specialist delegation
# ---------------------------------------------------------------------------

def _run_specialist(
    skill: SkillModel,
    specialist_name: str,
    modality_str: str,
    attempt: AttemptMedia,
    ctx: Optional[RunContext],
    warnings: List[str],
) -> Optional[TrajectoryResult]:
    """Delegate to the specialist evaluator (kolam or tabla) and return its TrajectoryResult."""
    payload = skill.specialists.get(specialist_name)
    if payload is None:
        return None

    # Build a minimal GoalModel for the specialist
    from tracks.common.casedata import GoalModel as GM
    goal_specialist = GM(
        case_id="universal-specialist",
        version=1,
        modality=modality_str,
        source_ids=[attempt.source_id],
        package_id="pkg.universal.specialist",
        payload=payload,
    )

    try:
        if specialist_name == "line_art":
            from track_b.evaluators.kolam import evaluate as kolam_evaluate
            return kolam_evaluate(goal_specialist, attempt, ctx)
        elif specialist_name == "rhythm":
            from track_b.evaluators.tabla import evaluate as tabla_evaluate
            return tabla_evaluate(goal_specialist, attempt, ctx)
    except AnveshanFailure:
        raise
    except Exception as exc:
        warnings.append(f"{specialist_name} specialist evaluation failed: {exc}")
        return None


def _prefix_metrics(result: TrajectoryResult, prefix: str) -> TrajectoryResult:
    """Return a copy with all metric ids and events prefixed."""
    new_metrics = {}
    for k, v in result.metrics.items():
        new_metrics[f"{prefix}{k}"] = v

    new_events = []
    for ev in result.events:
        new_ev = DivergenceEvent(
            metric=f"{prefix}{ev.metric}",
            kind=ev.kind,
            position=ev.position,
            position_kind=ev.position_kind,
            evidence=ev.evidence,
            detail=ev.detail,
            severity=ev.severity,
        )
        new_events.append(new_ev)

    return TrajectoryResult(
        metrics=new_metrics,
        events=new_events,
        curve=result.curve,
        curve_kind=result.curve_kind,
        process_observable=result.process_observable,
        final_state=result.final_state,
        artifacts=result.artifacts,
        run_keys=result.run_keys,
        warnings=result.warnings,
    )


# ---------------------------------------------------------------------------
# Utterance checks
# ---------------------------------------------------------------------------

def _utterance_checks(
    skill: SkillModel,
    attempt: AttemptMedia,
    attempt_record: Any,
) -> Dict[str, MetricValue]:
    """Deterministic utterance checks."""
    metrics: Dict[str, MetricValue] = {}

    source_utt = skill.utterance
    if not source_utt:
        return metrics

    # Get attempt transcript from speech observations
    speech_obs = []
    if attempt_record:
        speech_obs = [o for o in getattr(attempt_record, "observations", [])
                      if o.kind == "speech"]

    src_transcript = source_utt.get("transcript", "")
    src_duration = source_utt.get("duration_sec") or 0.0

    if not speech_obs:
        # No transcript available
        for check in skill.checks:
            if check.kind in ("utterance_match", "pace_match") and check.enabled:
                metrics[check.metric_id] = MetricValue(
                    None,
                    "transcript unavailable (audio model disabled)",
                    uncertain_reason="transcript unavailable (audio model disabled)",
                )
        return metrics

    att_transcript = speech_obs[0].detail or speech_obs[0].label

    # Duration from attempt measurement
    dur_obs = [o for o in getattr(attempt_record, "observations", [])
               if o.kind == "measurement" and "duration" in o.label.lower()]
    att_duration = float(dur_obs[0].value) if dur_obs and dur_obs[0].value else (
        getattr(attempt_record, "media", None) and attempt_record.media.duration_sec or 0.0
    )

    for check in skill.checks:
        if check.kind == "utterance_match" and check.enabled:
            val = _utterance_match(src_transcript, att_transcript)
            ev = _ev(f"ev.universal.utt.{attempt.source_id[:8]}",
                     attempt.source_id, Modality.AUDIO,
                     f"utterance match {val:.3f}")
            metrics[check.metric_id] = MetricValue(val, f"Utterance match: {val:.3f}", evidence=ev)

        elif check.kind == "pace_match" and check.enabled:
            if src_duration > 0:
                pace = abs(att_duration - src_duration) / src_duration
            else:
                pace = 0.0
            ev = _ev(f"ev.universal.pace.{attempt.source_id[:8]}",
                     attempt.source_id, Modality.AUDIO,
                     f"pace error {pace:.3f}")
            metrics[check.metric_id] = MetricValue(pace, f"Pace error: {pace:.3f}", evidence=ev)

    return metrics


def _utterance_match(src: str, att: str) -> float:
    """1 - normalised Levenshtein on word sequences, clamped 0..1."""
    # Try to reuse tabla_dsp.levenshtein if available
    try:
        from tracks.common.tabla_dsp import levenshtein as _lev
    except (ImportError, AttributeError):
        _lev = _levenshtein_impl

    src_words = src.lower().strip().split()
    att_words = att.lower().strip().split()

    # Strip punctuation
    import re
    src_words = [re.sub(r"[^a-z0-9]", "", w) for w in src_words if re.sub(r"[^a-z0-9]", "", w)]
    att_words = [re.sub(r"[^a-z0-9]", "", w) for w in att_words if re.sub(r"[^a-z0-9]", "", w)]

    n = max(len(src_words), 1)
    dist = _lev(src_words, att_words)
    return max(0.0, min(1.0, 1.0 - dist / n))


def _levenshtein_impl(a: List, b: List) -> int:
    """Levenshtein distance on lists."""
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[:]
        dp[0] = i
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[j] = prev[j - 1]
            else:
                dp[j] = 1 + min(prev[j], dp[j - 1], prev[j - 1])
    return dp[n]


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _modality_enum(mime_type: str) -> Modality:
    prefix = mime_type.split("/", 1)[0].lower()
    if prefix == "image":
        return Modality.IMAGE
    if prefix == "video":
        return Modality.VIDEO
    if prefix == "audio":
        return Modality.AUDIO
    return Modality.IMAGE


# ---------------------------------------------------------------------------
# Main evaluate
# ---------------------------------------------------------------------------

def evaluate(goal: GoalModel, attempt: AttemptMedia, ctx: Any = None) -> TrajectoryResult:
    """Universal evaluator: SkillModel + attempt -> TrajectoryResult."""
    if goal.modality != "universal":
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT,
            f"universal evaluator got modality {goal.modality!r}; expected 'universal'",
        )

    skill = SkillModel.model_validate(goal.payload)
    warnings: List[str] = [UNIVERSAL_WARNING]
    run_keys: List[str] = []

    # 1. Kind gate
    expected = set(skill.relevance.expected_kinds)
    if attempt.kind not in expected:
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT,
            f"This skill accepts {sorted(expected)} attempts; got {attempt.kind!r}.",
        )

    # 2. Perceive the attempt (lazy import perceivers)
    attempt_record = None
    attempt_emb: Optional[np.ndarray] = None
    asset_dir = None

    if attempt.kind != "trace":
        try:
            perceivers = importlib.import_module("tracks.common.perceivers")
            case_dir = Path(ctx.case_dir) if ctx else Path(".")
            asset_dir = case_dir / "attempts" / attempt.sha256[:12]
            asset_dir.mkdir(parents=True, exist_ok=True)
            attempt_record = perceivers.perceive(
                attempt.path,
                attempt.mime_type,
                ctx,
                source_id=attempt.source_id,
                asset_dir=asset_dir,
                purpose="attempt",
                want_specialists=False,
            )
            if attempt_record.embeddings_file and asset_dir:
                try:
                    attempt_emb = perceivers.load_embeddings(attempt_record, asset_dir)
                except Exception:
                    attempt_emb = None
            if attempt_record.runs:
                run_keys.extend(attempt_record.runs)
        except ImportError:
            warnings.append("tracks.common.perceivers not available; skipping attempt perception")
        except AnveshanFailure:
            raise
        except Exception as exc:
            warnings.append(f"Attempt perception failed: {exc}")

    # 3. Quality gate
    _quality_gate(attempt, attempt_record)

    # Load source perception record and embeddings
    source_record = None
    source_emb: Optional[np.ndarray] = None
    perception_file = skill.perception_file or "knowledge/perception_source.v1.json"
    if ctx is not None:
        case_dir = Path(ctx.case_dir) if not isinstance(ctx.case_dir, Path) else ctx.case_dir
        perc_path = case_dir / perception_file
        if perc_path.exists():
            try:
                from tracks.common.perception import PerceptionRecord
                source_record = PerceptionRecord.model_validate_json(
                    perc_path.read_text(encoding="utf-8")
                )
                try:
                    perceivers = importlib.import_module("tracks.common.perceivers")
                    emb_dir = perc_path.parent
                    source_emb = perceivers.load_embeddings(source_record, emb_dir)
                except Exception:
                    source_emb = None
            except Exception as exc:
                warnings.append(f"Could not load source perception: {exc}")

    # 4. Relevance gate (image/video)
    similarity = -1.0
    if attempt.kind in ("image", "video"):
        similarity = _relevance_gate(
            skill, attempt, attempt_record, source_emb, attempt_emb, ctx, source_record, warnings
        )

    # 5. Run structure-appropriate checks
    all_metrics: Dict[str, MetricValue] = {}
    all_events: List[DivergenceEvent] = []
    primary_curve: List[Tuple[float, float]] = [(0.0, 0.0)]
    primary_curve_kind = "stroke"

    for structure in skill.structures:
        if structure == "final_state":
            fm = _judge_final(skill, attempt, attempt_record, source_record,
                              source_emb, attempt_emb, ctx, warnings)
            all_metrics.update(fm)

            if "line_art" in skill.specialists and attempt.kind in ("trace", "image"):
                la_result = _run_specialist(skill, "line_art", "kolam_image", attempt, ctx, warnings)
                if la_result:
                    la_prefixed = _prefix_metrics(la_result, "line_art:")
                    all_metrics.update(la_prefixed.metrics)
                    all_events.extend(la_prefixed.events)
                    if not primary_curve or len(primary_curve) <= 1:
                        primary_curve = la_result.curve
                        primary_curve_kind = la_result.curve_kind

            # Final state curve
            if not all_metrics:
                pass
            else:
                fp_checks = [c for c in skill.checks if c.kind == "final_property" and c.enabled]
                if fp_checks:
                    n_met = sum(1 for c in fp_checks
                                if all_metrics.get(c.metric_id) and all_metrics[c.metric_id].value == 1.0)
                    frac = n_met / len(fp_checks)
                    primary_curve = [(0.0, 0.0), (1.0, frac)]
                    primary_curve_kind = "stroke"

        elif structure == "procedure":
            pm, pe, pc = _procedure_checks(
                skill, attempt, attempt_record, source_emb, attempt_emb, source_record, ctx, warnings
            )
            all_metrics.update(pm)
            all_events.extend(pe)
            if pc and len(pc) > 1:
                primary_curve = pc
                primary_curve_kind = "time"

        elif structure == "temporal_pattern":
            if "rhythm" in skill.specialists:
                # For video attempt: extract audio track first
                if attempt.kind == "video":
                    audio_attempt = _extract_audio_from_video(attempt, warnings)
                    if audio_attempt:
                        rh_result = _run_specialist(skill, "rhythm", "tabla_audio", audio_attempt, ctx, warnings)
                    else:
                        rh_result = None
                else:
                    rh_result = _run_specialist(skill, "rhythm", "tabla_audio", attempt, ctx, warnings)

                if rh_result:
                    rh_prefixed = _prefix_metrics(rh_result, "rhythm:")
                    all_metrics.update(rh_prefixed.metrics)
                    all_events.extend(rh_prefixed.events)
                    if not primary_curve or len(primary_curve) <= 1:
                        primary_curve = rh_result.curve
                        primary_curve_kind = rh_result.curve_kind

        elif structure == "utterance":
            um = _utterance_checks(skill, attempt, attempt_record)
            all_metrics.update(um)

    # Sort events by position
    all_events.sort(key=lambda e: e.position)

    # process_observable: False for image attempts
    process_observable = (attempt.kind != "image")

    # For image attempts: mark all process checks as UNCERTAIN
    if not process_observable:
        for check in skill.checks:
            if check.process and check.enabled and check.metric_id in all_metrics:
                all_metrics[check.metric_id] = MetricValue(
                    None,
                    "process not observable from an image attempt",
                    uncertain_reason="process_observable=False for image attempts",
                )

    artifacts: Dict[str, Any] = {
        "relevance": similarity if similarity >= 0 else None,
    }
    if attempt_record and asset_dir:
        artifacts["attempt_perception"] = str(asset_dir / "perception.json")

    return TrajectoryResult(
        metrics=all_metrics,
        events=all_events,
        curve=primary_curve,
        curve_kind=primary_curve_kind,
        process_observable=process_observable,
        final_state={},
        artifacts=artifacts,
        run_keys=run_keys,
        warnings=warnings,
    )


def _extract_audio_from_video(attempt: AttemptMedia, warnings: List[str]) -> Optional[AttemptMedia]:
    """Extract audio track from a video attempt to a temp WAV file."""
    try:
        import av
        import io

        with av.open(str(attempt.path)) as container:
            audio_streams = [s for s in container.streams if s.type == "audio"]
            if not audio_streams:
                warnings.append("Video has no audio track for temporal/utterance checks")
                return None

        # Write to temp file
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = Path(tmp.name)
        tmp.close()

        with av.open(str(attempt.path)) as inp:
            with av.open(str(tmp_path), "w") as out:
                out_stream = out.add_stream("pcm_s16le")
                for frame in inp.decode(audio=0):
                    for packet in out_stream.encode(frame):
                        out.mux(packet)
                for packet in out_stream.encode(None):
                    out.mux(packet)

        return AttemptMedia(
            kind="audio",
            path=tmp_path,
            source_id=f"{attempt.source_id}.audio",
            sha256=attempt.sha256,
            mime_type="audio/wav",
        )
    except Exception as exc:
        warnings.append(f"Audio extraction from video failed: {exc}")
        return None
