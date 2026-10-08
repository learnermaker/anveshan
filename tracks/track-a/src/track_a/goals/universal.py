"""Universal goal builder: confirmed SkillModel (via CaseProfile) -> GoalBuildResult.

A confirmed profile (``profile.confirmed_by_user=True``) is required (INVALID_INPUT otherwise).
No new perception calls. Loads the source PerceptionRecord from
``ctx.case_dir / "knowledge" / "perception_source.v1.json"``.

See docs/kiro/specs/K7-engines-generalise.md §3 and docs/plans/universal-pipeline.md §5.4.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tracks.common.casedata import Band, ObserverBinding, SourceRecord
from tracks.common.locators import with_frame, with_region
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.perception import PerceptionRecord
from tracks.common.profile import CaseProfile
from tracks.common.runtime import RunContext
from tracks.common.schemas import EvidenceRef, KnowledgeClaim, TaskConstraint
from tracks.common.schemas.evidence import Modality, VerificationState
from tracks.common.schemas.knowledge import ClaimType
from tracks.common.skill_model import Check, SkillModel, Step, TargetProperty

from track_a.goals import CriterionTemplate, GoalBuildResult

INFERRED_CONFIDENCE = 0.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


CAPTURE_ASK = {
    "video": "film your hands doing it",
    "image": "take a photo of what you made",
    "audio": "record yourself playing",
}


def capture_instruction(kinds: List[str]) -> str:
    """Ask for the attempt in physical-world terms ("film your hands"), not "upload a file"."""
    asks = [CAPTURE_ASK.get(k, f"share a {k}") for k in kinds] or ["share your attempt"]
    text = " or ".join(asks)
    return f"When you have tried it, {text}."


def _modality_enum(mime_type: str) -> Modality:
    prefix = mime_type.split("/", 1)[0].lower()
    if prefix == "image":
        return Modality.IMAGE
    if prefix == "video":
        return Modality.VIDEO
    if prefix == "audio":
        return Modality.AUDIO
    return Modality.IMAGE


def _ev_observed(eid: str, source_id: str, modality: Modality,
                 excerpt: str,
                 start: Optional[float] = None,
                 end: Optional[float] = None) -> EvidenceRef:
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


def _ev_inferred(eid: str, source_id: str, modality: Modality,
                 excerpt: str,
                 start: Optional[float] = None,
                 end: Optional[float] = None) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=eid,
        source_id=source_id,
        modality=modality,
        start_sec=start,
        end_sec=end,
        cue_excerpt=excerpt,
        verification_state=VerificationState.INFERRED,
        confidence=INFERRED_CONFIDENCE,
    )


def _whole_locator(source_id: str) -> str:
    """Whole-image locator."""
    return with_region(source_id, 0, 0, 100, 100)


def _region_locator(source_id: str, region: Optional[List[float]]) -> str:
    if region and len(region) == 4:
        return with_region(source_id, region[0], region[1], region[2], region[3])
    return _whole_locator(source_id)


# ---------------------------------------------------------------------------
# Claims builders
# ---------------------------------------------------------------------------

def _measurement_claims(
    skill: SkillModel,
    record: PerceptionRecord,
    source_id: str,
    modality: Modality,
    duration_sec: Optional[float],
) -> List[KnowledgeClaim]:
    """Build observed measurement claims from det: observations, max 4."""
    claims: List[KnowledgeClaim] = []
    det_obs = [o for o in record.observations if o.producer.startswith("det:") and o.kind == "measurement"]

    if modality == Modality.IMAGE:
        # Find width/height obs
        width_obs = next((o for o in det_obs if "width" in o.label.lower() or "px" in o.label.lower()), None)
        if width_obs:
            cid = f"CLM-{len(claims) + 1:02d}"
            w = record.media.width or 0
            h = record.media.height or 0
            stmt = f"Image is {w}×{h} px"
            # Add contrast if available
            contrast_obs = next((o for o in det_obs if "contrast" in o.label.lower()), None)
            if contrast_obs and contrast_obs.value is not None:
                stmt += f"; contrast {contrast_obs.value:.2f}"
            ev = _ev_observed(f"ev.universal.{cid.lower()}", _whole_locator(source_id), Modality.IMAGE, stmt)
            claims.append(KnowledgeClaim(claim_id=cid, claim_type=ClaimType.CONDITION, statement=stmt,
                                         is_observed=True, evidence_refs=[ev]))
        else:
            # Still emit a measurement claim for the image dimensions if available
            w = record.media.width or 0
            h = record.media.height or 0
            if w > 0 and h > 0:
                cid = f"CLM-{len(claims) + 1:02d}"
                stmt = f"Image is {w}×{h} px"
                ev = _ev_observed(f"ev.universal.{cid.lower()}", _whole_locator(source_id), Modality.IMAGE, stmt)
                claims.append(KnowledgeClaim(claim_id=cid, claim_type=ClaimType.CONDITION, statement=stmt,
                                             is_observed=True, evidence_refs=[ev]))

    elif modality == Modality.VIDEO:
        n_segs = len([s for s in record.segments if s.kind == "time"])
        dur = duration_sec or 0.0
        if n_segs > 0 or dur > 0:
            cid = f"CLM-{len(claims) + 1:02d}"
            stmt = f"The demonstration has {n_segs} segments over {dur:.1f}s"
            ev = _ev_observed(f"ev.universal.{cid.lower()}", source_id, Modality.VIDEO, stmt,
                              start=0.0, end=dur)
            claims.append(KnowledgeClaim(claim_id=cid, claim_type=ClaimType.CONDITION, statement=stmt,
                                         is_observed=True, evidence_refs=[ev]))

    elif modality == Modality.AUDIO:
        dur = duration_sec or 0.0
        onset_count_obs = next((o for o in det_obs if "onset" in o.label.lower()), None)
        n_onsets = int(onset_count_obs.value) if onset_count_obs and onset_count_obs.value else 0
        cid = f"CLM-{len(claims) + 1:02d}"
        stmt = f"Duration {dur:.1f}s; {n_onsets} onsets"
        ev = _ev_observed(f"ev.universal.{cid.lower()}", source_id, Modality.AUDIO, stmt,
                          start=0.0, end=dur)
        claims.append(KnowledgeClaim(claim_id=cid, claim_type=ClaimType.CONDITION, statement=stmt,
                                     is_observed=True, evidence_refs=[ev]))

    return claims[:4]


def _condition_claims(
    skill: SkillModel,
    source_id: str,
    modality: Modality,
    duration_sec: Optional[float],
    existing_count: int,
) -> List[KnowledgeClaim]:
    """Build CONDITION claims from goal_state properties with keep=True."""
    claims: List[KnowledgeClaim] = []
    for prop in skill.goal_state:
        if not prop.keep:
            continue
        cid = f"CLM-{existing_count + len(claims) + 1:02d}"
        vstate = VerificationState.OBSERVED if prop.certainty == "observed" else VerificationState.INFERRED
        conf = 1.0 if prop.certainty == "observed" else INFERRED_CONFIDENCE
        locator = _region_locator(source_id, prop.region)

        if modality == Modality.IMAGE:
            ev = EvidenceRef(
                evidence_id=f"ev.universal.{cid.lower()}",
                source_id=locator,
                modality=Modality.IMAGE,
                start_sec=None,
                end_sec=None,
                cue_excerpt=prop.statement,
                verification_state=vstate,
                confidence=conf,
            )
        elif modality == Modality.VIDEO:
            # Use the last segment's interval
            ev = EvidenceRef(
                evidence_id=f"ev.universal.{cid.lower()}",
                source_id=source_id,
                modality=Modality.VIDEO,
                start_sec=0.0,
                end_sec=duration_sec or 0.0,
                cue_excerpt=prop.statement,
                verification_state=vstate,
                confidence=conf,
            )
        else:
            ev = EvidenceRef(
                evidence_id=f"ev.universal.{cid.lower()}",
                source_id=source_id,
                modality=modality,
                start_sec=0.0,
                end_sec=duration_sec or 0.0,
                cue_excerpt=prop.statement,
                verification_state=vstate,
                confidence=conf,
            )
        claims.append(KnowledgeClaim(
            claim_id=cid,
            claim_type=ClaimType.CONDITION,
            statement=prop.statement,
            is_observed=(prop.certainty == "observed"),
            evidence_refs=[ev],
        ))
    return claims


def _step_claims(
    skill: SkillModel,
    source_id: str,
    modality: Modality,
    duration_sec: Optional[float],
    existing_count: int,
) -> List[KnowledgeClaim]:
    """Build STEP claims from steps."""
    claims: List[KnowledgeClaim] = []
    for step in skill.steps:
        cid = f"CLM-{existing_count + len(claims) + 1:02d}"
        n = step.index + 1
        if step.source_established:
            stmt = f"Demonstrated step {n}: {step.name}"
        else:
            stmt = f"Suggested step {n} (inferred): {step.name}"

        if modality == Modality.VIDEO and step.start_sec is not None and step.end_sec is not None:
            ev = EvidenceRef(
                evidence_id=f"ev.universal.{cid.lower()}",
                source_id=source_id,
                modality=Modality.VIDEO,
                start_sec=step.start_sec,
                end_sec=step.end_sec,
                cue_excerpt=stmt,
                verification_state=VerificationState.INFERRED,
                confidence=INFERRED_CONFIDENCE,
            )
        elif modality == Modality.IMAGE and step.segment_id:
            ev = EvidenceRef(
                evidence_id=f"ev.universal.{cid.lower()}",
                source_id=_whole_locator(source_id),
                modality=Modality.IMAGE,
                start_sec=None,
                end_sec=None,
                cue_excerpt=stmt,
                verification_state=VerificationState.INFERRED,
                confidence=INFERRED_CONFIDENCE,
            )
        else:
            ev = EvidenceRef(
                evidence_id=f"ev.universal.{cid.lower()}",
                source_id=source_id,
                modality=modality,
                start_sec=0.0,
                end_sec=duration_sec or 0.0,
                cue_excerpt=stmt,
                verification_state=VerificationState.INFERRED,
                confidence=INFERRED_CONFIDENCE,
            )
        claims.append(KnowledgeClaim(
            claim_id=cid,
            claim_type=ClaimType.STEP,
            statement=stmt,
            is_observed=False,
            evidence_refs=[ev],
        ))
    return claims


def _constraint_claims(
    skill: SkillModel,
    source_id: str,
    modality: Modality,
    duration_sec: Optional[float],
    existing_count: int,
) -> List[KnowledgeClaim]:
    """Build FAILURE_MODE claims from enabled constraints."""
    claims: List[KnowledgeClaim] = []
    for con in skill.constraints:
        if not con.keep:
            continue
        cid = f"CLM-{existing_count + len(claims) + 1:02d}"
        ev = EvidenceRef(
            evidence_id=f"ev.universal.{cid.lower()}",
            source_id=source_id,
            modality=modality,
            start_sec=0.0,
            end_sec=duration_sec or 0.0,
            cue_excerpt=con.statement,
            verification_state=VerificationState.INFERRED,
            confidence=INFERRED_CONFIDENCE,
        )
        claims.append(KnowledgeClaim(
            claim_id=cid,
            claim_type=ClaimType.CONDITION,  # FAILURE_MODE maps to CONDITION
            statement=con.statement,
            is_observed=False,
            evidence_refs=[ev],
        ))
    return claims


def _temporal_claim(
    skill: SkillModel,
    source_id: str,
    modality: Modality,
    duration_sec: Optional[float],
    existing_count: int,
) -> Optional[KnowledgeClaim]:
    if not skill.temporal:
        return None
    cid = f"CLM-{existing_count + 1:02d}"
    t = skill.temporal
    pulse = t.get("pulse_sec")
    bpm = t.get("tempo_bpm")
    stmt = "Rhythm cue"
    if bpm:
        stmt = f"Rhythm: tempo {bpm:.1f} BPM"
    if pulse:
        stmt += f", pulse {pulse:.3f}s"
    ev = EvidenceRef(
        evidence_id=f"ev.universal.{cid.lower()}",
        source_id=source_id,
        modality=modality,
        start_sec=0.0,
        end_sec=duration_sec or 0.0,
        cue_excerpt=stmt,
        verification_state=VerificationState.OBSERVED,
        confidence=1.0,
    )
    return KnowledgeClaim(claim_id=cid, claim_type=ClaimType.CUE, statement=stmt,
                          is_observed=True, evidence_refs=[ev])


def _utterance_claim(
    skill: SkillModel,
    source_id: str,
    modality: Modality,
    duration_sec: Optional[float],
    existing_count: int,
) -> Optional[KnowledgeClaim]:
    if not skill.utterance:
        return None
    cid = f"CLM-{existing_count + 1:02d}"
    u = skill.utterance
    transcript = u.get("transcript", "")
    stmt = f"Utterance: {transcript[:200]}"
    ev = EvidenceRef(
        evidence_id=f"ev.universal.{cid.lower()}",
        source_id=source_id,
        modality=modality,
        start_sec=0.0,
        end_sec=duration_sec or 0.0,
        cue_excerpt=stmt,
        verification_state=VerificationState.INFERRED,
        confidence=INFERRED_CONFIDENCE,
    )
    return KnowledgeClaim(claim_id=cid, claim_type=ClaimType.CUE, statement=stmt,
                          is_observed=False, evidence_refs=[ev])


# ---------------------------------------------------------------------------
# Criterion templates
# ---------------------------------------------------------------------------

# Band tables per check kind
_BANDS: Dict[str, Tuple[float, float, str]] = {
    # (satisfied_min_or_max, partial_min_or_max, direction_key)
    "final_similarity":   (0.90, 0.80, "higher"),
    "final_property":     (1.0,  0.5,  "higher"),
    "step_quality":       (1.0,  0.5,  "higher"),
    "step_coverage":      (0.90, 0.60, "higher"),
    "step_order":         (0.0,  1.0,  "lower"),
    "off_path":           (0.0,  1.0,  "lower"),
    "utterance_match":    (0.90, 0.70, "higher"),
    "pace_match":         (0.15, 0.30, "lower"),
}

_DRILL_HINTS: Dict[str, str] = {
    "final_similarity": "Check that your result matches the reference image overall.",
    "final_property": "Review the specific property in the reference and adjust your result.",
    "step_coverage": "Practice each step separately before combining them.",
    "step_order": "Follow the demonstrated sequence; rewatch the video for the correct order.",
    "off_path": "Identify where you deviated and focus on staying on track.",
    "step_quality": "Compare your execution of this critical step with the reference.",
    "line_art": "Trace the reference carefully, paying attention to this specific line property.",
    "rhythm": "Use a metronome to practice the timing pattern separately.",
    "utterance_match": "Listen to the reference and repeat until the words match exactly.",
    "pace_match": "Practice to match the demonstrated speed and duration.",
}


def _make_binding(check: Check) -> ObserverBinding:
    """Create an ObserverBinding from check kind and metric."""
    if check.method == "specialist" and "binding" in check.params:
        b = check.params["binding"]
        direction = b.get("direction", "higher_is_better")
        bands_raw = b.get("bands", [])
        bands = [Band(**bd) for bd in bands_raw] if bands_raw else [Band(status="satisfied", min=0.7)]
        return ObserverBinding(
            metric=check.metric_id,
            direction=direction,
            bands=bands,
            process=check.process,
        )

    kind = check.kind
    if kind not in _BANDS:
        # Default binding
        return ObserverBinding(
            metric=check.metric_id,
            direction="higher_is_better",
            bands=[Band(status="satisfied", min=0.7), Band(status="partially_satisfied", min=0.5)],
            process=check.process,
        )

    sat, partial, direction_key = _BANDS[kind]
    direction = "higher_is_better" if direction_key == "higher" else "lower_is_better"
    if direction_key == "higher":
        bands = [
            Band(status="satisfied", min=sat),
            Band(status="partially_satisfied", min=partial),
        ]
    else:
        bands = [
            Band(status="satisfied", max=sat),
            Band(status="partially_satisfied", max=partial),
        ]
    return ObserverBinding(
        metric=check.metric_id,
        direction=direction,
        bands=bands,
        process=check.process,
    )


def _criterion_from_check(
    check: Check,
    claims: List[KnowledgeClaim],
    claim_id_map: Dict[str, str],  # prop_id/step_id -> CLM-xx
    order_index: int,
) -> Optional[CriterionTemplate]:
    """Build one CriterionTemplate from a check."""
    if not check.enabled:
        return None

    crit_id = f"CRIT-U-{check.check_id}"
    claim_ids: List[str] = []
    for target in check.targets:
        if target in claim_id_map:
            claim_ids.append(claim_id_map[target])

    # Add measurement claim for similarity/coverage if no targets
    if not claim_ids and claims:
        claim_ids = [claims[0].claim_id]

    # Build why_it_matters (must cite one claim_id)
    cite = claim_ids[0] if claim_ids else (claims[0].claim_id if claims else "CLM-01")
    why = f"{check.observable_indicator} ({cite})"

    drill = _DRILL_HINTS.get(check.kind, "Practice until this criterion is met.")

    ev_ids = []
    for c in claims:
        if c.claim_id in claim_ids:
            ev_ids.extend(e.evidence_id for e in c.evidence_refs)

    return CriterionTemplate(
        criterion_id=crit_id,
        name=check.name,
        description=check.observable_indicator,
        observable_indicator=check.observable_indicator,
        weight=check.weight,
        required=check.required,
        order_index=order_index,
        source_claim_ids=claim_ids if claim_ids else [cite],
        reference_evidence_ids=ev_ids,
        why_it_matters=why,
        drill_hint=drill,
        observer=_make_binding(check),
    )


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build(
    source_path: Path,
    source: SourceRecord,
    ctx: Any,
    *,
    case_id: str,
    version: int,
    profile: Optional[CaseProfile] = None,
) -> GoalBuildResult:
    """Build case artifacts from a confirmed CaseProfile.

    ``profile`` is required (INVALID_INPUT if absent or not confirmed_by_user=True).
    No new perception calls are made.
    """
    if profile is None:
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT,
            "universal builder requires a confirmed CaseProfile (profile=…)",
        )
    if not profile.confirmed_by_user:
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT,
            f"profile for {case_id} has not been confirmed by user (confirmed_by_user=False)",
        )

    skill = profile.skill_model
    warnings: List[str] = list(skill.warnings)
    warnings.append("Composed case: claims named by AI are inferred until reviewed.")

    source_id = source.source_id
    mime_type = source.mime_type
    modality_enum = _modality_enum(mime_type)
    duration_sec = source.duration_sec

    # Load perception record if available
    record: Optional[PerceptionRecord] = None
    perception_path = None
    if ctx is not None:
        case_dir = Path(ctx.case_dir) if not isinstance(ctx.case_dir, Path) else ctx.case_dir
        for name in ["perception_source.v1.json", "perception_source.v2.json"]:
            p = case_dir / "knowledge" / name
            if p.exists():
                perception_path = p
                break
    if perception_path and perception_path.exists():
        try:
            record = PerceptionRecord.model_validate_json(perception_path.read_text(encoding="utf-8"))
        except Exception as exc:
            warnings.append(f"Could not load perception record: {exc}")

    # Build claims in order
    all_claims: List[KnowledgeClaim] = []

    # 1. Measurement claims
    if record is not None:
        meas = _measurement_claims(skill, record, source_id, modality_enum, duration_sec)
        all_claims.extend(meas)
    else:
        # Create a minimal measurement claim
        if modality_enum == Modality.IMAGE:
            w = source.dimensions[0] if source.dimensions else 0
            h = source.dimensions[1] if source.dimensions else 0
            if w > 0:
                cid = f"CLM-{len(all_claims) + 1:02d}"
                stmt = f"Image is {w}×{h} px"
                ev = _ev_observed(f"ev.universal.{cid.lower()}", _whole_locator(source_id), Modality.IMAGE, stmt)
                all_claims.append(KnowledgeClaim(claim_id=cid, claim_type=ClaimType.CONDITION, statement=stmt,
                                                 is_observed=True, evidence_refs=[ev]))
        else:
            dur = duration_sec or 0.0
            cid = f"CLM-{len(all_claims) + 1:02d}"
            stmt = f"Duration {dur:.1f}s"
            ev = _ev_observed(f"ev.universal.{cid.lower()}", source_id, modality_enum, stmt,
                              start=0.0, end=dur)
            all_claims.append(KnowledgeClaim(claim_id=cid, claim_type=ClaimType.CONDITION, statement=stmt,
                                             is_observed=True, evidence_refs=[ev]))

    # 2. CONDITION claims from goal_state
    cond_claims = _condition_claims(skill, source_id, modality_enum, duration_sec, len(all_claims))
    all_claims.extend(cond_claims)

    # 3. STEP claims
    step_claims = _step_claims(skill, source_id, modality_enum, duration_sec, len(all_claims))
    # For image without build steps: add a fallback step
    if "final_state" in skill.structures and not step_claims and not any(
        s for s in skill.steps
    ):
        cid = f"CLM-{len(all_claims) + 1:02d}"
        stmt = "Reproduce the target as shown (suggested, inferred)"
        ev = EvidenceRef(
            evidence_id=f"ev.universal.{cid.lower()}",
            source_id=_whole_locator(source_id),
            modality=modality_enum,
            start_sec=None,
            end_sec=None,
            cue_excerpt=stmt,
            verification_state=VerificationState.INFERRED,
            confidence=INFERRED_CONFIDENCE,
        )
        all_claims.append(KnowledgeClaim(claim_id=cid, claim_type=ClaimType.STEP, statement=stmt,
                                         is_observed=False, evidence_refs=[ev]))
        step_claims = []  # Already added directly
    else:
        all_claims.extend(step_claims)

    # 4. FAILURE_MODE claims from constraints
    constraint_claims = _constraint_claims(skill, source_id, modality_enum, duration_sec, len(all_claims))
    all_claims.extend(constraint_claims)

    # 5. Temporal CUE claim
    if skill.temporal:
        tclaim = _temporal_claim(skill, source_id, modality_enum, duration_sec, len(all_claims))
        if tclaim:
            all_claims.append(tclaim)

    # 6. Utterance CUE claim
    if skill.utterance:
        uclaim = _utterance_claim(skill, source_id, modality_enum, duration_sec, len(all_claims))
        if uclaim:
            all_claims.append(uclaim)

    # Map prop_id / step_id / constraint_id -> claim_id. Each builder emits exactly one claim per
    # kept input, in input order, so the map is exact (no positional guessing across claim types).
    claim_id_map: Dict[str, str] = {}
    kept_props = [p for p in skill.goal_state if p.keep]
    kept_cons = [c for c in skill.constraints if c.keep]
    for prop, claim in zip(kept_props, cond_claims):
        claim_id_map[prop.prop_id] = claim.claim_id
    for step, claim in zip(skill.steps, step_claims):
        claim_id_map[step.step_id] = claim.claim_id
    for con, claim in zip(kept_cons, constraint_claims):
        claim_id_map[con.constraint_id] = claim.claim_id

    # Build criteria from enabled checks
    criteria: List[CriterionTemplate] = []
    for i, check in enumerate(skill.checks):
        ct = _criterion_from_check(check, all_claims, claim_id_map, i)
        if ct is not None:
            criteria.append(ct)

    if not criteria:
        # Fallback: at least one criterion
        cid_fallback = all_claims[0].claim_id if all_claims else "CLM-01"
        criteria.append(CriterionTemplate(
            criterion_id="CRIT-U-DEFAULT",
            name="Overall similarity",
            description="Overall match to the goal",
            observable_indicator="The attempt matches the goal overall",
            weight=1.0,
            required=True,
            order_index=0,
            source_claim_ids=[cid_fallback],
            reference_evidence_ids=[],
            why_it_matters=f"The goal is defined by the source ({cid_fallback})",
            drill_hint="Compare your attempt to the reference.",
            observer=ObserverBinding(
                metric="u.final_similarity",
                direction="higher_is_better",
                bands=[Band(status="satisfied", min=0.9), Band(status="partially_satisfied", min=0.7)],
            ),
        ))

    # Build task
    task_title = f"Practice: {skill.skill_title}"
    inst_lines: List[str] = []
    n = 1
    if skill.steps:
        inst_lines.append("Work through these stages; each is what your work should look like at that point:")
        for step in skill.steps:
            claim_ref = f" [{claim_id_map.get(step.step_id, '')}]" if step.step_id in claim_id_map else ""
            inst_lines.append(f"{n}. {step.name[:1].upper()}{step.name[1:]}{claim_ref}")
            n += 1
    elif skill.goal_state:
        inst_lines.append("Achieve these properties:")
        for prop in skill.goal_state[:4]:
            if prop.keep:
                claim_ref = f" [{claim_id_map.get(prop.prop_id, '')}]" if prop.prop_id in claim_id_map else ""
                inst_lines.append(f"{n}. {prop.statement}{claim_ref}")
                n += 1

    # Add upload instruction
    accepted_kinds = skill.relevance.expected_kinds
    inst_lines.append(f"{n}. {capture_instruction(accepted_kinds)}")
    task_instructions = "\n".join(inst_lines)

    goal_payload = skill.model_dump(mode="json")
    if perception_path:
        goal_payload["perception_file"] = "knowledge/" + perception_path.name
    else:
        goal_payload["perception_file"] = "knowledge/perception_source.v1.json"

    run_keys = list(profile.model_run_keys)

    built_with: Dict[str, Any] = {
        "builder": "track_a.goals.universal@v1",
        "case_id": case_id,
        "version": version,
        "profile_case_id": profile.case_id,
        "structures": list(skill.structures),
        "run_keys": run_keys,
    }

    return GoalBuildResult(
        title=skill.skill_title,
        summary=skill.summary,
        goal_payload=goal_payload,
        claims=all_claims,
        criteria=criteria,
        task_title=task_title,
        task_instructions=task_instructions,
        task_constraints=[
            TaskConstraint(
                constraint_type="upload_spec",
                description=f"Upload your attempt as {', '.join(accepted_kinds)}.",
                value=",".join(accepted_kinds),
            )
        ],
        warnings=warnings,
        run_keys=run_keys,
        built_with=built_with,
    )
