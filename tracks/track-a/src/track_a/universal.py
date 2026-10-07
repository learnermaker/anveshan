"""Layer 2: propose a SkillModel from a PerceptionRecord + user intent.

Uses LAZY imports for tracks.common.perceivers (WP1 owns that module).
Import it inside functions only, never at module level.
See docs/kiro/specs/K7-engines-generalise.md §2 and docs/plans/wave2-master-spec.md §7.9.
"""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tracks.common.models import ImagePart, ModelError, load_prompt
from tracks.common.perception import PerceptionRecord
from tracks.common.profile import IntakeResult, ProbeFacts
from tracks.common.runtime import RunContext
from tracks.common.skill_model import (
    Check,
    Constraint,
    Relevance,
    SkillModel,
    STRUCTURE_ATTEMPT_KINDS,
    Step,
    TargetProperty,
)

log = logging.getLogger(__name__)

PROMPT_DIR = Path(__file__).resolve().parents[3] / "common" / "prompts"
STRUCTURE_SKILL_PROMPT = PROMPT_DIR / "structure_skill_v1.txt"
PROMPT_ID = "structure_skill"

# Maximum properties to include in goal_state
MAX_PROPERTIES = 8
# Confidence for all inferred steps/properties
INFERRED_CONFIDENCE = 0.5
TRANSITION_CALM = 0.5   # video segments with < 50 % calm frames are transitions, not steps


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _obs_of_kind(record: PerceptionRecord, segment_id: str, kind: str) -> List[Any]:
    return [o for o in record.observations if o.segment_id == segment_id and o.kind == kind]


def _all_obs_of_kind(record: PerceptionRecord, kind: str) -> List[Any]:
    return [o for o in record.observations if o.kind == kind]


def _det_obs(record: PerceptionRecord) -> List[Any]:
    """All deterministic measurement observations."""
    return [o for o in record.observations if o.producer.startswith("det:") and o.kind == "measurement"]


def _get_segment(record: PerceptionRecord, seg_id: str):
    return record.segment(seg_id)


def _build_structures(probe: ProbeFacts) -> List[str]:
    """Select at most 2 structures from probe.structures_available in priority order."""
    available = set(probe.structures_available)
    structures: List[str] = []
    modality = probe.modality

    if modality == "image":
        if "final_state" in available:
            structures.append("final_state")
    elif modality == "video":
        if "procedure" in available:
            structures.append("procedure")
            # Add temporal_pattern if rhythm specialist is available on the audio track
            if "rhythm" in (probe.specialists_available or []):
                structures.append("temporal_pattern")
        elif "final_state" in available:
            structures.append("final_state")
        if len(structures) < 2 and "temporal_pattern" in available and "temporal_pattern" not in structures:
            structures.append("temporal_pattern")
    elif modality == "audio":
        if "temporal_pattern" in available:
            structures.append("temporal_pattern")
        elif "utterance" in available:
            structures.append("utterance")

    # Always have at least one structure
    if not structures and available:
        structures.append(next(iter(probe.structures_available)))

    return structures[:2]  # at most 2


def _build_goal_state(
    record: PerceptionRecord,
    structures: List[str],
    specialists: Dict[str, Any],
) -> List[TargetProperty]:
    """Build TargetProperty list from property observations + line_art facts."""
    props: List[TargetProperty] = []

    # For procedure: use last still segment; for final_state: use whole
    if "procedure" in structures:
        # Find the last still/time segment
        time_segs = [s for s in record.segments if s.kind == "time"]
        if time_segs:
            last_seg = time_segs[-1]
            prop_obs = _obs_of_kind(record, last_seg.segment_id, "property")
            base_seg_id = last_seg.segment_id
        else:
            prop_obs = _all_obs_of_kind(record, "property")
            base_seg_id = "seg-000"
    else:
        # final_state or utterance: use whole-image segment
        prop_obs = _all_obs_of_kind(record, "property")
        base_seg_id = "seg-000"

    # Add property observations (max MAX_PROPERTIES)
    for i, obs in enumerate(prop_obs[:MAX_PROPERTIES]):
        seg = record.segment(obs.segment_id)
        region = seg.region if seg.kind == "region" else None
        stmt = obs.label + (f": {obs.detail}" if obs.detail else "")
        props.append(TargetProperty(
            prop_id=f"prop-{len(props) + 1:02d}",
            statement=stmt,
            region=region,
            evidence=[obs.obs_id],
            certainty="inferred",
            keep=True,
        ))

    # Add line_art facts as observed properties
    if "line_art" in specialists:
        la = specialists["line_art"]
        # Extract dot count, curve count, symmetry from the specialist payload
        n_dots = la.get("features", {}).get("n_dots", la.get("n_dots"))
        n_curves = la.get("features", {}).get("n_curves", la.get("n_curves"))
        sym = la.get("symmetry", {})
        rot_order = sym.get("rotation_order") if sym else None

        # Find det: measurement obs_ids for these facts
        det_obs = _det_obs(record)
        det_ids = [o.obs_id for o in det_obs]

        if n_dots is not None:
            props.append(TargetProperty(
                prop_id=f"prop-{len(props) + 1:02d}",
                statement=f"{n_dots} dots",
                region=None,
                evidence=det_ids[:2],
                certainty="observed",
                keep=True,
            ))
        if n_curves is not None:
            props.append(TargetProperty(
                prop_id=f"prop-{len(props) + 1:02d}",
                statement=f"{n_curves} continuous lines",
                region=None,
                evidence=det_ids[:2],
                certainty="observed",
                keep=True,
            ))
        if rot_order is not None and rot_order >= 2:
            props.append(TargetProperty(
                prop_id=f"prop-{len(props) + 1:02d}",
                statement=f"{rot_order}-fold rotational symmetry",
                region=None,
                evidence=det_ids[:1],
                certainty="observed",
                keep=True,
            ))

    return props


def _build_steps(record: PerceptionRecord, structures: List[str]) -> Tuple[List[Step], str]:
    """Build Step list from video segments or image action observations."""
    steps: List[Step] = []
    order = "none"

    if "procedure" in structures:
        # Build steps from time segments with state observations
        time_segs = [s for s in record.segments if s.kind == "time"]
        # Collect segments that have a state observation
        # Transition segments (mostly hands/camera in motion) are not states of the work:
        # skip them when enough calm segments exist, so steps are the stable states.
        def _calm(seg) -> float:
            vals = [o.value for o in _obs_of_kind(record, seg.segment_id, "measurement") if o.label == "calm_fraction"]
            return float(vals[0]) if vals and isinstance(vals[0], (int, float)) else 1.0

        calm_segs = [s for s in time_segs if _calm(s) >= TRANSITION_CALM]
        if len(calm_segs) >= 2:
            time_segs = calm_segs
        step_segs = []
        for seg in time_segs:
            state_obs = _obs_of_kind(record, seg.segment_id, "state")
            if state_obs:
                step_segs.append((seg, state_obs[0]))

        # Merge consecutive segments with identical state labels
        merged: List[Tuple[Any, Any, List[Any]]] = []
        for seg, state_obs in step_segs:
            if merged and merged[-1][1].label == state_obs.label:
                merged[-1][2].append(seg)
            else:
                merged.append((seg, state_obs, [seg]))

        # Find the longest active segment to mark critical step
        longest_active_idx = None
        longest_dur = -1.0
        for idx, (seg, state_obs, all_segs) in enumerate(merged):
            dur = (all_segs[-1].end_sec or 0) - (all_segs[0].start_sec or 0)
            if dur > longest_dur:
                longest_dur = dur
                longest_active_idx = idx

        critical_idx = (longest_active_idx + 1) if longest_active_idx is not None and (longest_active_idx + 1) < len(merged) else longest_active_idx

        for idx, (seg, state_obs, all_segs) in enumerate(merged):
            action_obs = _obs_of_kind(record, seg.segment_id, "action")
            action = action_obs[0].label if action_obs else None
            step_name = state_obs.label[:60]
            evidence_ids = [state_obs.obs_id]
            if action_obs:
                evidence_ids.append(action_obs[0].obs_id)

            # Use the first and last segment for time range
            start_sec = all_segs[0].start_sec
            end_sec = all_segs[-1].end_sec
            keyframe_asset = all_segs[0].keyframe_asset

            steps.append(Step(
                step_id=f"step-{len(steps) + 1:02d}",
                index=len(steps),
                name=step_name,
                state_after=state_obs.label,
                action=action,
                start_sec=start_sec,
                end_sec=end_sec,
                keyframe_asset=keyframe_asset,
                segment_id=seg.segment_id,
                evidence=evidence_ids,
                certainty="inferred",
                source_established=True,
                critical=(idx == critical_idx),
            ))
        order = "strict" if steps else "none"

    elif "final_state" in structures:
        # Build inferred steps from 'build step i:' action observations
        action_obs = [o for o in record.observations if o.kind == "action" and o.label.startswith("build step")]
        if not action_obs:
            # Check for line_art stages - we'll handle in goal_state instead
            pass
        else:
            for idx, obs in enumerate(action_obs):
                seg = record.segment(obs.segment_id)
                steps.append(Step(
                    step_id=f"step-{len(steps) + 1:02d}",
                    index=len(steps),
                    name=obs.label[:60],
                    state_after=obs.label[:60],
                    action=obs.label,
                    start_sec=None,
                    end_sec=None,
                    keyframe_asset=None,
                    segment_id=obs.segment_id,
                    evidence=[obs.obs_id],
                    certainty="inferred",
                    source_established=False,
                    critical=False,
                ))
        order = "none"

    return steps, order


def _build_constraints(record: PerceptionRecord) -> List[Constraint]:
    """Build constraints from 'avoid: ...' quality observations."""
    constraints: List[Constraint] = []
    quality_obs = [o for o in record.observations if o.kind == "quality" and o.label.startswith("avoid:")]
    for obs in quality_obs:
        constraints.append(Constraint(
            constraint_id=f"con-{len(constraints) + 1:02d}",
            statement=obs.label,
            evidence=[obs.obs_id],
            certainty="inferred",
            keep=False,  # off by default; user enables
        ))
    return constraints


def _build_temporal(record: PerceptionRecord, specialists: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract temporal info from rhythm specialist payload."""
    if "rhythm" not in specialists:
        return None
    rp = specialists["rhythm"]
    # Build a summary dict from the rhythm payload
    pulse_sec = rp.get("pulse_sec")
    tempo_bpm = rp.get("tempo_bpm") or (60.0 / pulse_sec if pulse_sec and pulse_sec > 0 else None)
    cycle_length = rp.get("cycle_length")
    return {
        "pulse_sec": pulse_sec,
        "tempo_bpm": tempo_bpm,
        "cycle_length": cycle_length,
        "source": "rhythm_specialist",
    }


def _build_utterance(record: PerceptionRecord) -> Optional[Dict[str, Any]]:
    """Extract utterance info from speech observations."""
    speech_obs = [o for o in record.observations if o.kind == "speech"]
    if not speech_obs:
        return None
    obs = speech_obs[0]
    transcript = obs.detail or obs.label
    # Duration from measurement observations
    duration_obs = [o for o in record.observations if o.kind == "measurement" and "duration" in o.label.lower()]
    duration_sec = duration_obs[0].value if duration_obs else record.media.duration_sec
    return {
        "transcript": transcript,
        "language": None,
        "duration_sec": duration_sec,
    }


def _default_checks(
    structures: List[str],
    goal_state: List[TargetProperty],
    steps: List[Step],
    constraints: List[Constraint],
    specialists: Dict[str, Any],
    source_modality: str,
) -> List[Check]:
    """Build the default check set per the spec table."""
    checks: List[Check] = []

    if "final_state" in structures:
        checks.append(Check(
            check_id="CHK-FS-SIM",
            kind="final_similarity",
            name="Final result similarity",
            observable_indicator="Cosine similarity between learner final state and goal image",
            targets=[],
            metric_id="u.final_similarity",
            method="deterministic",
            weight=1,
            required=False,
            process=False,
        ))
        kept_props = [p for p in goal_state if p.keep and p.certainty == "inferred"][:4]
        for i, prop in enumerate(kept_props):
            checks.append(Check(
                check_id=f"CHK-FS-P{i + 1:02d}",
                kind="final_property",
                name=f"Property: {prop.statement[:40]}",
                observable_indicator=f"Property is met: {prop.statement[:100]}",
                targets=[prop.prop_id],
                metric_id=f"u.final_property.{prop.prop_id}",
                method="model_status",
                weight=2,
                required=(i == 0),  # first one required
                process=False,
            ))

        # Completeness against the expert's result: catches a missing/extra part even when the
        # global similarity is high (judged with the expert image shown as reference).
        checks.append(Check(
            check_id="CHK-FS-ALL",
            kind="final_property",
            name="Complete: nothing missing or extra",
            observable_indicator=("Every part visible in the expert reference result is also present in the attempt, "
                                  "in the same arrangement, with nothing missing and nothing extra"),
            targets=[],
            metric_id="u.final_property.complete",
            method="model_status",
            weight=2,
            required=True,
            process=False,
        ))

        if "line_art" in specialists:
            # Get line_art criterion templates from the specialist payload
            la_checks = _kolam_line_art_checks(specialists["line_art"])
            checks.extend(la_checks)

    if "procedure" in structures:
        critical_steps = [s for s in steps if s.critical]
        checks.append(Check(
            check_id="CHK-PR-COV",
            kind="step_coverage",
            name="Step coverage",
            observable_indicator="Fraction of goal steps matched in attempt",
            targets=[s.step_id for s in steps],
            metric_id="u.step_coverage",
            method="deterministic",
            weight=3,
            required=True,
            process=True,
        ))
        checks.append(Check(
            check_id="CHK-PR-ORD",
            kind="step_order",
            name="Step order",
            observable_indicator="Number of step order violations",
            targets=[s.step_id for s in steps],
            metric_id="u.step_order",
            method="deterministic",
            weight=2,
            required=True,
            process=True,
        ))
        checks.append(Check(
            check_id="CHK-PR-OFF",
            kind="off_path",
            name="Off-path segments",
            observable_indicator="Number of extended off-path runs",
            targets=[],
            metric_id="u.off_path",
            method="deterministic",
            weight=1,
            required=False,
            process=True,
        ))
        last_step = steps[-1] if steps else None
        checks.append(Check(
            check_id="CHK-PR-FIN",
            kind="final_property",
            name="Final state match",
            observable_indicator="Last step matches the demonstrated final state",
            targets=[last_step.step_id] if last_step else [],
            metric_id="u.final_state_match",
            method="model_status",
            weight=3,
            required=True,
            process=False,
        ))
        if critical_steps:
            cstep = critical_steps[0]
            checks.append(Check(
                check_id=f"CHK-PR-Q01",
                kind="step_quality",
                name=f"Quality: {cstep.name[:40]}",
                observable_indicator=f"Critical step quality: {cstep.name[:80]}",
                targets=[cstep.step_id],
                metric_id=f"u.step_quality.{cstep.step_id}",
                method="model_status",
                weight=2,
                required=False,
                process=True,
            ))

        if "rhythm" in specialists:
            rh_checks = _rhythm_checks(specialists["rhythm"])
            checks.extend(rh_checks)

    if "temporal_pattern" in structures and "procedure" not in structures:
        if "rhythm" in specialists:
            rh_checks = _rhythm_checks(specialists["rhythm"])
            checks.extend(rh_checks)

    if "utterance" in structures:
        checks.append(Check(
            check_id="CHK-UT-TXT",
            kind="utterance_match",
            name="Utterance match",
            observable_indicator="Normalised edit distance of transcript words",
            targets=[],
            metric_id="u.utterance_match",
            method="deterministic",
            weight=3,
            required=True,
            process=False,
        ))
        checks.append(Check(
            check_id="CHK-UT-PACE",
            kind="pace_match",
            name="Pace match",
            observable_indicator="Relative duration difference",
            targets=[],
            metric_id="u.pace_match",
            method="deterministic",
            weight=1,
            required=False,
            process=False,
        ))

    return checks


def _kolam_line_art_checks(la_payload: Dict[str, Any]) -> List[Check]:
    """Build line_art checks from a Kolam-style specialist payload."""
    # Try to get criterion templates from the kolam payload
    # Each criterion template has: criterion_id, metric, direction, bands
    # We'll create one check per known kolam metric
    checks = []
    known_kolam_metrics = [
        ("kolam.coverage", "Total coverage", "Fraction of goal line covered by learner", 3, True),
        ("kolam.precision", "Precision (no stray lines)", "Fraction of learner ink on the goal line", 2, True),
        ("kolam.dot_relation_match", "Dot relations", "Fraction of dots with correct on/off relation", 2, True),
        ("kolam.curves_completed_ratio", "Curves completed", "Fraction of continuous lines completed", 2, False),
        ("kolam.pen_lifts_excess", "Pen lifts", "Excess pen lifts beyond number of lines", 1, False),
    ]
    for i, (metric, name, indicator, weight, required) in enumerate(known_kolam_metrics):
        check_id = f"CHK-LA-{i + 1:02d}"
        # Store the metric binding in params for the builder to use
        checks.append(Check(
            check_id=check_id,
            kind="line_art",
            name=name,
            observable_indicator=indicator,
            targets=[],
            metric_id=f"line_art:{metric}",
            method="specialist",
            weight=weight,
            required=required,
            process=(metric == "kolam.pen_lifts_excess"),
            params={"binding": {
                "metric": f"line_art:{metric}",
                "direction": "lower_is_better" if "lifts" in metric else "higher_is_better",
                "bands": [],
                "process": (metric == "kolam.pen_lifts_excess"),
            }},
        ))
    return checks


def _rhythm_checks(rh_payload: Dict[str, Any]) -> List[Check]:
    """Rhythm checks for ANY rhythmic audio (onset-based DSP specialist), with explicit bands.

    Bands follow the calibrated Tabla observers (tempo 5/10 %, timing 50/100 ms, completeness
    1/3); steadiness is relative to the source's own inter-onset variability, so a loose
    folk rhythm and a metronomic one are both judged against themselves.
    """
    src_cv = rh_payload.get("ioi_cv")
    try:
        src_cv = float(src_cv) if src_cv is not None else 0.1
    except (TypeError, ValueError):
        src_cv = 0.1
    lo = lambda sat, part: [{"status": "satisfied", "max": sat}, {"status": "partially_satisfied", "max": part}]  # noqa: E731
    hi = lambda sat, part: [{"status": "satisfied", "min": sat}, {"status": "partially_satisfied", "min": part}]  # noqa: E731
    spec = [
        ("tabla.tempo_error_pct", "Tempo", "Tempo within 5 % of the source", 3, True, "lower_is_better", lo(5.0, 10.0)),
        ("tabla.timing_median_ms", "Timing", "Median onset timing error under 50 ms", 3, True, "lower_is_better", lo(50.0, 100.0)),
        ("tabla.ioi_cv", "Steadiness", f"Inter-onset variability close to the source's ({src_cv:.2f})", 2, True,
         "lower_is_better", lo(round(src_cv + 0.05, 3), round(src_cv + 0.12, 3))),
        ("tabla.missing_extra", "Completeness", "At most 1 missing or extra onset", 2, False, "lower_is_better", lo(1.0, 3.0)),
        ("tabla.bass_accuracy", "Accents", "Low/accented onsets in the same places as the source", 1, False,
         "higher_is_better", hi(0.9, 0.7)),
    ]
    checks = []
    for i, (metric, name, indicator, weight, required, direction, bands) in enumerate(spec):
        checks.append(Check(
            check_id=f"CHK-RH-{i + 1:02d}",
            kind="rhythm",
            name=name,
            observable_indicator=indicator,
            targets=[],
            metric_id=f"rhythm:{metric}",
            method="specialist",
            weight=weight,
            required=required,
            process=False,
            params={"binding": {"metric": f"rhythm:{metric}", "direction": direction, "bands": bands, "process": False}},
        ))
    return checks


def _build_relevance(
    structures: List[str],
    source_modality: str,
    record: PerceptionRecord,
) -> Relevance:
    """Build the Relevance object."""
    expected_kinds: List[str] = []
    for s in structures:
        for k in STRUCTURE_ATTEMPT_KINDS.get(s, []):
            if k not in expected_kinds:
                expected_kinds.append(k)

    # Drop "trace" unless line_art is present — handled by caller
    min_sim = 0.72 if source_modality == "image" else 0.70

    # Reference segments: whole for image, all keyframe segments for video
    ref_seg_ids: List[str] = []
    if source_modality == "image":
        ref_seg_ids = ["seg-000"]
    else:
        ref_seg_ids = [s.segment_id for s in record.segments if s.kind == "time" and s.keyframe_asset]
        if not ref_seg_ids:
            ref_seg_ids = ["seg-000"]

    return Relevance(
        expected_kinds=expected_kinds,
        min_similarity=min_sim,
        reference_segment_ids=ref_seg_ids,
    )


def _apply_wording(
    skill_model: SkillModel,
    title_hint: Optional[str],
    description: Optional[str],
    ctx: RunContext,
    warnings: List[str],
) -> SkillModel:
    """Optional wording call via structure_skill_v1.txt. On failure, deterministic texts."""
    if ctx is None or getattr(ctx, "gateway", None) is None:
        return skill_model

    # Build compact JSON summary
    check_ids = [c.check_id for c in skill_model.checks]
    summary_obj = {
        "structures": list(skill_model.structures),
        "source_modality": skill_model.source_modality,
        "title_hint": title_hint or "",
        "description": description or "",
        "steps": [{"step_id": s.step_id, "name": s.name[:60]} for s in skill_model.steps],
        "properties": [{"prop_id": p.prop_id, "statement": p.statement[:60]} for p in skill_model.goal_state],
        "check_ids": check_ids,
    }

    try:
        prompt_text, ver = load_prompt(
            STRUCTURE_SKILL_PROMPT,
            skill_summary_json=json.dumps(summary_obj, indent=2),
        )
        from pydantic import BaseModel

        class WordingDTO(BaseModel):
            skill_title: str = ""
            summary: str = ""
            domain: str = ""
            vocabulary: Dict[str, str] = {}
            check_texts: Dict[str, Dict[str, str]] = {}

        result = ctx.gateway.generate_json(
            model_key="vision_fast",
            prompt_id=PROMPT_ID,
            prompt_version=ver,
            prompt_text=prompt_text,
            schema=WordingDTO,
            expected_behavior="skill title, summary, vocabulary, and check wording; no provenance claims",
        )
        dto = result.data

        # Apply to skill model fields
        updates: Dict[str, Any] = {}
        if dto.skill_title:
            updates["skill_title"] = dto.skill_title[:60]
        if dto.summary:
            updates["summary"] = dto.summary[:300]
        vocabulary = dict(skill_model.vocabulary)
        if dto.vocabulary:
            vocabulary.update(dto.vocabulary)

        # Apply check texts (only existing check ids)
        new_checks = []
        for chk in skill_model.checks:
            if chk.check_id in dto.check_texts:
                ct = dto.check_texts[chk.check_id]
                new_checks.append(chk.model_copy(update={
                    "name": ct.get("name", chk.name)[:60],
                    "observable_indicator": ct.get("observable_indicator", chk.observable_indicator)[:160],
                }))
            else:
                new_checks.append(chk)

        return skill_model.model_copy(update={
            **updates,
            "vocabulary": vocabulary,
            "checks": new_checks,
        })

    except (ModelError, Exception) as exc:
        warnings.append(f"wording model call failed ({type(exc).__name__}: {exc}); using deterministic texts")
        return skill_model


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose_skill_model(
    record: PerceptionRecord,
    probe: ProbeFacts,
    intake: IntakeResult,
    ctx: RunContext,
    title_hint: Optional[str],
    description: Optional[str],
    source_path: Optional[Path] = None,
) -> Tuple[SkillModel, Dict[str, Any], List[str]]:
    """Deterministic composition + optional wording call.

    Returns (SkillModel, built_with dict, warnings list).
    LAZY-imports tracks.common.perceivers only inside this function (never at module level).
    """
    warnings: List[str] = []
    built_with: Dict[str, Any] = {}

    source_modality = probe.modality

    # 1. Determine structures
    structures = _build_structures(probe)
    if not structures:
        structures = ["final_state"]  # fallback

    # 2. Resolve specialists
    specialists: Dict[str, Any] = {}

    if "line_art" in (probe.specialists_available or []) and source_path is not None:
        try:
            from tracks.common.goals.kolam import payload_from_image
            la_payload, _ = payload_from_image(source_path)
            specialists["line_art"] = la_payload
            built_with["line_art_builder"] = "tracks.common.goals.kolam.payload_from_image@v1"
        except Exception as exc:
            warnings.append(f"line_art specialist failed: {exc}")

    if "rhythm" in (probe.specialists_available or []) and source_path is not None:
        try:
            # Prefer tracks.common.goals.tabla.payload_from_audio if available
            try:
                from tracks.common.goals.tabla import payload_from_audio  # type: ignore
                rh_out = payload_from_audio(source_path, None)
                # WP4 API: (payload, built_with, warnings, run_keys); older API: payload only
                rh_payload = rh_out[0] if isinstance(rh_out, tuple) else rh_out
                if isinstance(rh_out, tuple) and len(rh_out) > 2 and rh_out[2]:
                    warnings.extend(f"rhythm: {w}" for w in rh_out[2])
                specialists["rhythm"] = rh_payload if isinstance(rh_payload, dict) else rh_payload.model_dump(mode="json")
            except (ImportError, AttributeError):
                # Fallback: call track_a.goals.tabla.build
                from tracks.common.casedata import SourceRecord
                from track_a.goals.tabla import build as tabla_build
                import tempfile

                dummy_source = SourceRecord(
                    source_id="tmp.rhythm",
                    role="expert_audio",
                    mime_type="audio/wav",
                    sha256="0" * 64,
                    bytes=0,
                    path=str(source_path),
                    creator="tmp",
                    license="tmp",
                    attribution="tmp",
                    runtime_label="SYNTHETIC",
                )
                tr = tabla_build(source_path, dummy_source, ctx, case_id="tmp", version=1)
                specialists["rhythm"] = tr.goal_payload
            built_with["rhythm_builder"] = "track_a.goals.tabla.build@v1"
        except Exception as exc:
            warnings.append(f"rhythm specialist failed: {exc}")

    # 3. Goal state (final_state properties + line_art facts)
    goal_state = []
    if "final_state" in structures or "procedure" in structures:
        goal_state = _build_goal_state(record, structures, specialists)

    # 4. Steps
    steps, order = _build_steps(record, structures)

    # 5. Constraints
    constraints = _build_constraints(record)

    # 6. Temporal
    temporal = None
    if "temporal_pattern" in structures:
        temporal = _build_temporal(record, specialists)

    # 7. Utterance
    utterance = None
    if "utterance" in structures:
        utterance = _build_utterance(record)

    # 8. Default checks
    checks = _default_checks(structures, goal_state, steps, constraints, specialists, source_modality)

    # Drop "trace" from expected_kinds unless line_art is present
    relevance = _build_relevance(structures, source_modality, record)
    if "line_art" not in specialists:
        relevance = Relevance(
            expected_kinds=[k for k in relevance.expected_kinds if k != "trace"],
            min_similarity=relevance.min_similarity,
            ambiguous_band=relevance.ambiguous_band,
            reference_segment_ids=relevance.reference_segment_ids,
        )

    # Default title/summary from title_hint or source modality
    default_title = title_hint or f"Skill from {source_modality}"
    default_summary = description or f"A {source_modality}-based skill composed by the universal pipeline."

    skill = SkillModel(
        skill_title=default_title[:60],
        summary=default_summary[:300],
        source_modality=source_modality,
        structures=structures,
        goal_state=goal_state,
        steps=steps,
        order=order,
        constraints=constraints,
        temporal=temporal,
        utterance=utterance,
        specialists=specialists,
        relevance=relevance,
        checks=checks,
        warnings=list(warnings),
    )

    # 9. Optional wording call
    use_wording = False
    if ctx is not None and getattr(ctx, "gateway", None) is not None:
        skill = _apply_wording(skill, title_hint, description, ctx, warnings)
        use_wording = True

    built_with.update({
        "structures": list(structures),
        "specialists": list(specialists.keys()),
        "wording_model": use_wording,
    })

    # Add warnings to the model
    if warnings:
        skill = skill.model_copy(update={"warnings": list(skill.warnings) + [w for w in warnings if w not in skill.warnings]})

    return skill, built_with, warnings
