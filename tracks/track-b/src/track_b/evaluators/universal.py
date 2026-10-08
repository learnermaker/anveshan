"""Universal trajectory evaluator (Layer 3).

Receives a GoalModel with modality="universal" whose payload is a SkillModel,
runs structure-appropriate checks, and returns a TrajectoryResult.

LAZY imports for tracks.common.perceivers (WP1 owns it). Import inside functions.
See docs/kiro/specs/K7-engines-generalise.md §4.
"""

from __future__ import annotations

import contextvars
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
from track_b.evaluators.universal_align import mode_filter

ABS_FLOOR = 0.60   # a frame less similar than this to every step is off-path (unrelated content)
RELEVANCE_DROP = 0.15   # video attempt must match the source within 0.15 of the source's own frame-to-frame consistency
CONF_MARGIN_MIN = 0.05   # minimum drop below the attempt's typical match level that marks a frame as unmatched
Z_OFF = 0.25       # a frame counts for a step only if it is >= 0.25 sd above its mean step similarity

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


# Directory of the source perception assets (keyframes) for the evaluation in progress.
_SOURCE_DIR: "contextvars.ContextVar[Optional[Path]]" = contextvars.ContextVar("universal_source_dir", default=None)
_ATTEMPT_DIR: "contextvars.ContextVar[Optional[Path]]" = contextvars.ContextVar("universal_attempt_dir", default=None)


def _jpeg(img: Any, max_side: int = 512) -> bytes:
    import io
    from tracks.common.media import to_rgb
    im = to_rgb(img)
    im.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _video_frame_part(path: Path, t: float, label: str) -> Optional[ImagePart]:
    """The attempt video frame at time ``t`` (first decoded frame at/after t)."""
    try:
        from tracks.common.media import sample_frames
        fr = sample_frames(path, fps=2.0, start_sec=max(0.0, t - 0.25), end_sec=t + 1.0, max_side=512)
        return ImagePart(_jpeg(fr[0].image), "image/jpeg", label) if fr else None
    except Exception:  # noqa: BLE001 - undecodable tail: judged without the frame (reported as warning)
        return None



def _source_image_part(ctx: Optional[RunContext]) -> Optional[ImagePart]:
    """The case's source image (expert result) as a judge reference, max side 512."""
    if ctx is None or getattr(ctx, "case_dir", None) is None:
        return None
    try:
        from PIL import Image
        from tracks.common.casedata import load_sources, resolve_media
        for src in load_sources(Path(ctx.case_dir)).sources:
            if (src.mime_type or "").startswith("image/"):
                return ImagePart(_jpeg(Image.open(resolve_media(Path(ctx.case_dir), src))), "image/jpeg",
                                 "Expert reference result")
    except Exception:  # noqa: BLE001 - caller records a warning when no reference is available
        return None
    return None


def _source_keyframe_part(asset: Optional[str], label: str) -> Optional[ImagePart]:
    d = _SOURCE_DIR.get()
    if not asset or d is None:
        return None
    for cand in (Path(d) / asset, Path(d) / "goal_assets" / asset):   # composed cases keep keyframes in goal_assets/
        if cand.exists():
            from PIL import Image
            return ImagePart(_jpeg(Image.open(cand)), "image/jpeg", label)
    return None



MATCH_BOOST = {"high": 2.0, "medium": 1.25, "low": 0.5}   # added to a frame's z-score for the matched step
MATCH_NONE_PENALTY = 1.0                                    # subtracted from all steps when the model saw no step


_CONF_RANK = {"low": 0, "medium": 1, "high": 2}
_MatchMap = Dict[str, Tuple[Optional[int], str]]


def combine_matches(first: _MatchMap, second: _MatchMap) -> _MatchMap:
    """Self-consistency: keep only labels that two differently ordered passes agree on.

    Agreement keeps the stronger confidence; any disagreement (different steps, or step vs none)
    drops the keyframe, so it neither boosts nor penalises the alignment (embeddings decide).
    """
    out: _MatchMap = {}
    for sid, (step, conf) in first.items():
        if sid not in second:
            continue
        step2, conf2 = second[sid]
        if step != step2:
            continue
        out[sid] = (step, conf if _CONF_RANK[conf] >= _CONF_RANK[conf2] else conf2)
    return out


def _match_dto():
    """Lenient DTO for the matcher: tolerates "2", "Expert step 2", "null" and missing confidence."""
    import re as _re
    from pydantic import BaseModel, field_validator, model_validator

    class _M(BaseModel):
        segment_id: str = ""
        step: Optional[int] = None
        confidence: str = "low"

        @field_validator("step", mode="before")
        @classmethod
        def _step(cls, v: Any) -> Optional[int]:
            if v is None or isinstance(v, bool):
                return None
            if isinstance(v, (int, float)):
                return int(v)
            m = _re.search(r"-?\d+", str(v))
            return int(m.group()) if m else None

        @field_validator("confidence", mode="before")
        @classmethod
        def _conf(cls, v: Any) -> str:
            v = str(v or "low").strip().lower()
            return v if v in MATCH_BOOST else "low"

    class _MatchDTO(BaseModel):
        matches: List[_M] = []

        @model_validator(mode="before")
        @classmethod
        def _bare_list(cls, v: Any) -> Any:
            return {"matches": v} if isinstance(v, list) else v  # the model sometimes drops the wrapper object

    return _MatchDTO


def _reference_step_matches(skill: SkillModel, attempt_record: Any, ctx: Optional[RunContext],
                            warnings: List[str]) -> _MatchMap:
    """Two vision_fast calls: which expert step does each learner keyframe show?

    Expert step keyframes and learner keyframes go side by side, so fine-grained states that
    global embeddings cannot separate (hands dominate the frame) are still told apart.
    The learner keyframes are shown in time order, then in reverse order; only labels both passes
    agree on are kept (``combine_matches``), which removes time-order bias and label flicker.
    The answer is an OBSERVATION feeding the deterministic monotone fit, never a score.
    Returns {attempt segment_id: (step index or None, confidence)}; {} when unavailable.
    """
    if ctx is None or getattr(ctx, "gateway", None) is None or attempt_record is None:
        return {}
    _MatchDTO = _match_dto()

    expert: List[Any] = []
    for st in skill.steps[:12]:
        ref = _source_keyframe_part(st.keyframe_asset, f"Expert step {st.index}: {st.name}")
        if ref is None:
            warnings.append(f"reference step matching skipped: no expert keyframe for step {st.index}; alignment uses embeddings only")
            return {}
        expert.append(ref)
    adir = _ATTEMPT_DIR.get()
    segs = [sg for sg in attempt_record.segments if sg.kind == "time" and sg.keyframe_asset]
    if adir is None or not segs:
        warnings.append("reference step matching skipped: attempt keyframes unavailable; alignment uses embeddings only")
        return {}
    from PIL import Image
    learner: List[Any] = []
    for sg in segs[:16]:
        fp = Path(adir) / sg.keyframe_asset
        if not fp.exists():
            continue
        learner.append(ImagePart(_jpeg(Image.open(fp), 320), "image/jpeg", f"Learner {sg.segment_id} at t={sg.keyframe_sec or 0:.1f}s"))
    n = len(skill.steps)

    def one_pass(learner_parts: List[Any], order_note: str) -> _MatchMap:
        prompt_text, ver = load_prompt(PROMPT_DIR / "match_steps_v2.txt", skill_title=skill.skill_title,
                                       order_note=order_note)
        res = ctx.gateway.generate_json(
            model_key="vision_fast", prompt_id="match_steps", prompt_version=ver, prompt_text=prompt_text,
            schema=_MatchDTO, parts=[*expert, *learner_parts], expected_behavior="one expert-step label per learner keyframe",
        )
        out: _MatchMap = {}
        for m in res.data.matches:
            step = m.step if (m.step is None or 0 <= m.step < n) else None
            out[m.segment_id] = (step, m.confidence if m.confidence in MATCH_BOOST else "low")
        return out

    try:
        first = one_pass(learner, "in time order")
    except (ModelError, FileNotFoundError) as exc:
        warnings.append(f"reference step matching unavailable ({exc}); alignment uses embeddings only")
        return {}
    if len(learner) < 2:
        return first
    try:
        second = one_pass(list(reversed(learner)), "in REVERSE time order (latest first)")
    except ModelError as exc:
        warnings.append(f"reference step matching consistency pass unavailable ({exc}); using a single pass")
        return first
    combined = combine_matches(first, second)
    dropped = len(first) - len(combined)
    if dropped:
        warnings.append(f"reference step matching: {dropped} of {len(first)} learner keyframes had inconsistent labels and were left to embeddings")
    return combined


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

    # Video procedures: compare frame-level best matches against the source's OWN consistency,
    # so one threshold works for clean screen recordings and noisy hand-held videos alike.
    if attempt.kind == "video" and source_record is not None:
        sf = (getattr(source_record, "specialists", {}) or {}).get("frames", {})
        af = (getattr(attempt_record, "specialists", {}) or {}).get("frames", {})
        s_rows = [r for r in sf.get("rows", []) if r < len(source_emb)]
        a_rows = [r for r in af.get("rows", []) if r < len(attempt_emb)]
        if len(s_rows) >= 4 and a_rows:
            S = np.asarray(source_emb[s_rows], dtype=np.float64)
            A = np.asarray(attempt_emb[a_rows], dtype=np.float64)
            S /= np.maximum(np.linalg.norm(S, axis=1, keepdims=True), 1e-9)
            A /= np.maximum(np.linalg.norm(A, axis=1, keepdims=True), 1e-9)
            self_sim = S @ S.T
            for i in range(len(S)):      # exclude self and immediate neighbours
                self_sim[i, max(0, i - 1): i + 2] = -1.0
            self_level = float(np.median(self_sim.max(axis=1)))
            s = float(np.median((A @ S.T).max(axis=1)))
            min_sim = max(min_sim, self_level - RELEVANCE_DROP)

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
            parts.append(ImagePart(_jpeg(Image.open(attempt.path), 512), "image/jpeg", "Attempt image"))
        except Exception as exc:  # noqa: BLE001 - an unreadable image is refused, never judged blind
            raise AnveshanFailure(FailureCategory.INVALID_INPUT,
                                  f"The attempt image could not be read ({exc}). Please upload a JPEG or PNG photo.")

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



def _compare_parts(skill: SkillModel, parts: List[Any], checks: List[Any], ctx: RunContext,
                   warnings: List[str]) -> Dict[str, Any]:
    """Enumerate-then-compare completeness (model lists parts; a deterministic rule decides).

    met = nothing missing/extra/misplaced; partly = exactly one discrepancy; not_met = more.
    """
    from pydantic import BaseModel

    class _PartsDTO(BaseModel):
        visible: bool = True
        expert_parts: List[str] = []
        attempt_parts: List[str] = []
        missing: List[str] = []
        extra: List[str] = []
        misplaced: List[str] = []

    try:
        prompt_text, ver = load_prompt(PROMPT_DIR / "compare_parts_v1.txt", skill_title=skill.skill_title)
        res = ctx.gateway.generate_json(
            model_key="vision_fast", prompt_id="compare_parts", prompt_version=ver, prompt_text=prompt_text,
            schema=_PartsDTO, parts=parts, expected_behavior="part lists for expert and attempt, with differences",
        )
    except (ModelError, FileNotFoundError) as exc:
        warnings.append(f"completeness comparison failed: {exc}")
        return {}
    d = res.data
    n = len(d.missing) + len(d.extra) + len(d.misplaced)
    if not d.visible:
        status, finding = "cannot_tell", "the learner's result is not visible"
    else:
        status = "met" if n == 0 else ("partly" if n == 1 else "not_met")
        bits = [f"missing: {', '.join(d.missing)}" if d.missing else "", f"extra: {', '.join(d.extra)}" if d.extra else "",
                f"misplaced: {', '.join(d.misplaced)}" if d.misplaced else ""]
        finding = "; ".join(b for b in bits if b) or f"all {len(d.expert_parts)} parts present and in place"
    return {c.check_id: {"check_id": c.check_id, "status": status, "finding": finding[:300], "region": None} for c in checks}


def _call_judge_final(
    skill: SkillModel,
    attempt: AttemptMedia,
    source_record: Any,
    checks: List[Any],
    ctx: RunContext,
    warnings: List[str],
    final_times: Optional[List[float]] = None,
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

    prompt_path = PROMPT_DIR / "judge_final_v2.txt"
    if not prompt_path.exists():
        return {}

    checks_json = json.dumps([
        {"check_id": c.check_id, "target_statement": c.observable_indicator}
        for c in checks
    ], indent=2)

    prompt_text, ver = load_prompt(prompt_path, checks_json=checks_json)

    parts: List[Any] = []
    have_attempt = False
    # Attempt final image (≤ 2 images, max side 512)
    if attempt.kind == "image" and attempt.path.exists():
        try:
            from PIL import Image
            parts.append(ImagePart(_jpeg(Image.open(attempt.path), 512), "image/jpeg", "Attempt image"))
            have_attempt = True
        except Exception as exc:  # noqa: BLE001 - reported; checks become UNCERTAIN below
            warnings.append(f"Could not load attempt image: {exc}")
        ref = _source_image_part(ctx)
        if ref is not None:
            parts.append(ref)
        else:
            warnings.append("expert reference image unavailable for the final-state judge")
    elif attempt.kind == "video" and attempt.path.exists():
        from tracks.common.media import probe
        dur = probe(attempt.path).duration_sec or 0.0
        got = 0
        times = final_times or [max(0.0, min(dur * f, dur - 0.5)) for f in (0.90, 0.95, 1.0)]
        for t in times:
            fp = _video_frame_part(attempt.path, t, f"Attempt: near the end (t={t:.1f}s)")
            if fp is not None:
                parts.append(fp)
                got += 1
        have_attempt = got > 0
        if not got:
            warnings.append("could not decode the attempt's final frames for the final-state judge")
        if skill.steps:
            ref = _source_keyframe_part(skill.steps[-1].keyframe_asset, "Expert reference: final state")
            if ref is not None:
                parts.append(ref)

    if not have_attempt:
        # Judging only the expert reference would invent a verdict: every check is UNCERTAIN instead.
        return {c.check_id: {"status": "cannot_tell", "finding": "the attempt's own image could not be read, so it was not judged"}
                for c in checks}

    out: Dict[str, Any] = {}
    complete = [c for c in checks if c.metric_id == "u.final_property.complete"]
    checks = [c for c in checks if c.metric_id != "u.final_property.complete"]
    if complete and parts:
        out.update(_compare_parts(skill, parts, complete, ctx, warnings))
    if not checks:
        return out
    checks_json = json.dumps([{"check_id": c.check_id, "target_statement": c.observable_indicator} for c in checks], indent=2)
    prompt_text, ver = load_prompt(prompt_path, checks_json=checks_json)
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
        out.update({r.check_id: r.model_dump() for r in result.data.results})
        return out
    except ModelError as exc:
        warnings.append(f"judge_final model call failed: {exc}")
        return out


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

    # Source: one prototype per step = centroid of the source frames inside the step's span
    # (robust to a single blurred/occluded keyframe); falls back to the keyframe row.
    source_idx = getattr(source_record, "embedding_index", {}) if source_record else {}
    src_frames = (getattr(source_record, "specialists", {}) or {}).get("frames", {}) if source_record else {}
    src_times = np.asarray(src_frames.get("times", []), dtype=np.float64)
    src_rows = np.asarray(src_frames.get("rows", []), dtype=int)
    step_rows: List[np.ndarray] = []
    for step in skill.steps:
        rows: List[int] = []
        if len(src_times) and step.start_sec is not None and step.end_sec is not None:
            sel = (src_times >= step.start_sec - 1e-6) & (src_times <= step.end_sec + 1e-6)
            rows = [int(r) for r in src_rows[sel] if r < len(source_emb)]
        if not rows:
            seg_id = step.segment_id
            if seg_id and seg_id in source_idx and source_idx[seg_id] < len(source_emb):
                rows = [source_idx[seg_id]]
            else:
                rows = [min(step.index, len(source_emb) - 1)]
        v = np.asarray(source_emb[rows], dtype=np.float64)
        v = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
        c = v.mean(axis=0)
        step_rows.append(c / max(float(np.linalg.norm(c)), 1e-9))

    step_vecs = np.stack(step_rows)  # (N, D) unit

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

    valid_rows = [r for r in frame_rows if r < len(attempt_emb)]
    if not valid_rows:
        return metrics, events, curve
    frame_vecs = np.asarray(attempt_emb[valid_rows], dtype=np.float64)
    frame_vecs = frame_vecs / np.maximum(np.linalg.norm(frame_vecs, axis=1, keepdims=True), 1e-9)
    frame_times = list(frame_times[: len(valid_rows)])

    # Similarity of every attempt frame to every step. Global embeddings of one scene are all
    # similar (cos ~0.9+), so each frame's scores are z-scored across steps: "which step does
    # this frame look MOST like", independent of the video's overall similarity level.
    from tracks.common.segmentation import monotone_align

    sim = frame_vecs @ step_vecs.T  # (F, N)
    if n_steps > 1:
        z = (sim - sim.mean(axis=1, keepdims=True)) / (sim.std(axis=1, keepdims=True) + 1e-6)
    else:
        z = sim - ABS_FLOOR
    # Confident frames: close to SOME step relative to this attempt's own typical match level
    # (adaptive margin from the spread of the attempt's best-match scores). Low-scoring frames
    # are transitions (hands moving) or, when calm for a while, a NOVEL state the expert never
    # showed (off-path, e.g. doing steps in a different order).
    best_sim = sim.max(axis=1)
    level = float(np.percentile(best_sim, 75))
    mad = float(np.median(np.abs(best_sim - np.median(best_sim))))
    margin = max(CONF_MARGIN_MIN, 3.0 * mad)
    on_frame = (best_sim >= ABS_FLOOR) & (best_sim >= level - margin)
    att_motion = np.asarray(frames_info.get("motion", [0.0] * len(frame_vecs))[: len(frame_vecs)], dtype=np.float64)
    if len(att_motion) < len(frame_vecs):
        att_motion = np.zeros(len(frame_vecs))
    from tracks.common.segmentation import motion_threshold
    calm = att_motion <= motion_threshold(att_motion)
    # Coverage / progress: best non-decreasing path through the steps (skips allowed, no going back).
    matches = _reference_step_matches(skill, attempt_record, ctx, warnings)
    if matches:
        ft = np.asarray(frame_times, dtype=np.float64)
        for sg in attempt_record.segments:
            if sg.kind != "time" or sg.segment_id not in matches:
                continue
            step, conf = matches[sg.segment_id]
            sel = (ft >= (sg.start_sec or 0.0) - 1e-6) & (ft <= (sg.end_sec or 0.0) + 1e-6)
            if step is None:
                z[sel] -= MATCH_NONE_PENALTY * (MATCH_BOOST[conf] / 2.0)
            else:
                z[sel, step] += MATCH_BOOST[conf]
                on_frame[sel] |= best_sim[sel] >= ABS_FLOOR
    path = monotone_align(np.where(on_frame[:, None], z, -1e3), off_score=Z_OFF)
    visited = sorted({p for p in path if p is not None})
    # Order: unconstrained per-frame best step (confident frames only), smoothed, then aligned
    # against the expected order with Needleman-Wunsch to count out-of-order steps.
    raw_labels: List[Any] = []
    for i in range(len(frame_vecs)):
        if not on_frame[i]:
            raw_labels.append("off" if (calm[i] or best_sim[i] < ABS_FLOOR) else "transition")
        else:
            j = int(np.argmax(z[i]))
            raw_labels.append(j if (n_steps == 1 or z[i, j] >= Z_OFF) else "transition")
    filt_labels = mode_filter(raw_labels, window=3)

    n_matched = len(visited)
    coverage = n_matched / n_steps if n_steps > 0 else 0.0
    violations = order_violations(raw_labels, z, frame_times, n_steps)

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
                    events.append(DivergenceEvent(
                        metric="u.off_path",
                        kind="off_path_state",
                        position=t_start,
                        position_kind="time",
                        evidence=_ev(f"ev.universal.offpath.{i}.{attempt.source_id[:8]}",
                                     attempt.source_id, Modality.VIDEO,
                                     f"From {t_start:.0f}s to {t_end:.0f}s the work is in a state the expert never showed",
                                     t_start, t_end),
                        detail=f"held state at {t_start:.0f}-{t_end:.0f}s matches no expert step (possible wrong order or extra step)",
                    ))
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

    # Events for missing steps: steps the monotone path never visits, placed where the
    # learner moved from the previous visited step to the next one.
    t_end = frame_times[-1] if frame_times else 0.0
    for exp_step in range(n_steps):
        if exp_step in visited:
            continue
        prev_t = [frame_times[i] for i, p in enumerate(path) if p is not None and p < exp_step]
        t_pos = prev_t[-1] if prev_t else 0.0
        if not prev_t and not any(p is not None and p > exp_step for p in path):
            t_pos = t_end
        events.append(DivergenceEvent(
            metric="u.step_coverage",
            kind="missing_state",
            position=t_pos,
            position_kind="time",
            evidence=_ev(f"ev.universal.missing.step{exp_step}.{attempt.source_id[:8]}",
                         attempt.source_id, Modality.VIDEO,
                         f"Step {exp_step} ({skill.steps[exp_step].name}) not found",
                         t_pos, t_pos),
            detail=f"Step {exp_step} not found in attempt",
        ))

    # Curve: (time, max step fraction)
    if frame_times:
        max_matched = 0
        for t, p in zip(frame_times, path):
            if p is not None:
                max_matched = max(max_matched, p + 1)
            curve.append((t, max_matched / n_steps if n_steps > 0 else 0.0))

    # Final state match check for procedure
    for check in skill.checks:
        if check.metric_id == "u.final_state_match" and check.enabled:
            if ctx is not None and getattr(ctx, "gateway", None) is not None:
                # Final evidence: the 3 frames of the last 20 % of the attempt that look most like the
                # expert's final step (calm, representative moments rather than fixed timestamps).
                # Prefer learner keyframes the reference matcher labelled as the final step (latest first).
                rank = {"high": 0, "medium": 1, "low": 2}
                final_kf = sorted(
                    ((rank[c], -(sg.keyframe_sec or 0.0), float(sg.keyframe_sec or 0.0))
                     for sg in attempt_record.segments
                     if sg.kind == "time" and sg.segment_id in matches
                     for st, c in [matches[sg.segment_id]] if st == n_steps - 1),
                )[:3]
                if final_kf:
                    final_times = sorted(t for _, _, t in final_kf)
                else:
                    tail = [i for i, t in enumerate(frame_times) if t >= 0.8 * frame_times[-1]] if frame_times else []
                    tail = sorted(tail, key=lambda i: -float(sim[i, n_steps - 1]))[:3]
                    final_times = sorted(float(frame_times[i]) for i in tail)
                judge_results = _call_judge_final(
                    skill, attempt, source_record, [check], ctx, warnings, final_times=final_times or None,
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
            if cstep.index not in visited:
                metrics[check.metric_id] = MetricValue(
                    0.0, f"the step '{cstep.name}' was never reached in the attempt, so its quality cannot be credited")
            elif ctx is not None and getattr(ctx, "gateway", None) is not None:
                aligned = [frame_times[i] for i, pth in enumerate(path) if pth == cstep.index and i < len(frame_times)]
                metrics[check.metric_id] = _judge_step_quality(
                    skill, attempt, cstep, source_emb, source_record, attempt_emb, attempt_record, ctx, warnings,
                    step_time=float(np.median(aligned)) if aligned else None,
                )
            else:
                metrics[check.metric_id] = MetricValue(
                    None, "model gateway not available", uncertain_reason="model gateway not available"
                )

    return metrics, events, curve



def order_violations(labels: List[Any], z: np.ndarray, times: List[float], n_steps: int) -> int:
    """Steps performed out of order = present steps - longest increasing run of step times.

    Each step's time is the median time of the attempt frames that look most like it.
    Times closer than two sampling periods count as simultaneous (adjacent source states
    can look almost identical), so only clear reorderings are counted. This is the
    "minimum number of steps to move" (LIS) measure, robust to per-frame flicker.
    """
    if n_steps < 2 or not times:
        return 0
    period = float(np.median(np.diff(times))) if len(times) > 1 else 1.0
    tol = 2.0 * period
    by_step: Dict[int, List[float]] = {}
    for i, lbl in enumerate(labels):
        if isinstance(lbl, int) and i < len(times):
            by_step.setdefault(lbl, []).append(times[i])
    present = sorted(((float(np.median(ts)), j) for j, ts in by_step.items() if len(ts) >= 2))
    if len(present) < 2:
        return 0
    # Quantise times by the tolerance so near-simultaneous steps tie, ties ordered by index.
    seq = [j for _, j in sorted(((round(t / tol), j) for t, j in present))]
    lis: List[int] = []
    import bisect
    for j in seq:
        k = bisect.bisect_left(lis, j)
        if k == len(lis):
            lis.append(j)
        else:
            lis[k] = j
    return len(seq) - len(lis)


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
    step_time: Optional[float] = None,
) -> MetricValue:
    """One judge_step call for a critical step (frames around the moment aligned to it)."""
    from pydantic import BaseModel

    class JudgeStepDTO(BaseModel):
        status: str = "cannot_tell"
        finding: str = ""

    prompt_path = PROMPT_DIR / "judge_step_v2.txt"
    if not prompt_path.exists():
        return MetricValue(None, "prompt not found", uncertain_reason="prompt not found")

    prompt_text, ver = load_prompt(prompt_path, step_description=f"{step.name}: {step.state_after}")

    parts: List[Any] = []
    # Try to load attempt frame that best matches the critical step
    att_specialists = getattr(attempt_record, "specialists", {}) if attempt_record else {}
    frames_info = att_specialists.get("frames", {}) if att_specialists else {}
    frame_rows = frames_info.get("rows", [])
    frame_times = frames_info.get("times", [])

    if step_time is not None and frame_times:
        period = float(np.median(np.diff(frame_times))) if len(frame_times) > 1 else 1.0
        for dt in (-0.5 * period, 0.0, 0.5 * period):
            t = max(0.0, step_time + dt)
            fp = _video_frame_part(attempt.path, t, f"Attempt: around the moment aligned to this step (t={t:.1f}s)")
            if fp is not None:
                parts.append(fp)
    elif frame_rows and attempt_emb is not None:
        source_idx = getattr(source_record, "embedding_index", {}) if source_record else {}
        seg_id = step.segment_id
        if seg_id and seg_id in source_idx:
            step_vec = source_emb[source_idx[seg_id]]
            # Find best matching attempt frame
            valid = [(i, frame_rows[i]) for i in range(len(frame_rows)) if frame_rows[i] < len(attempt_emb)]
            if valid:
                sims = [float(np.dot(attempt_emb[r], step_vec)) for _, r in valid]
                best_i = int(np.argmax(sims))
                if best_i < len(frame_times):
                    period = float(np.median(np.diff(frame_times))) if len(frame_times) > 1 else 1.0
                    for dt in (-0.5 * period, 0.0, 0.5 * period):
                        t = max(0.0, float(frame_times[best_i]) + dt)
                        fp = _video_frame_part(attempt.path, t, f"Attempt: around the moment most like this step (t={t:.1f}s)")
                        if fp is not None:
                            parts.append(fp)
    ref = _source_keyframe_part(step.keyframe_asset, "Expert reference: this step")
    if ref is not None:
        parts.append(ref)
    if not parts:
        return MetricValue(None, "no frame of this step could be shown to the judge",
                           uncertain_reason="no evidence frame")

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
            try:
                return tabla_evaluate(goal_specialist, attempt, ctx)
            except AnveshanFailure as exc:
                # The rhythm specialist serves ANY rhythmic skill here: drop tabla-specific wording.
                msg = exc.message
                for a, b in (("distinct drum strokes", "distinct notes, beats or strokes"), ("the tabla", "the sound source"),
                             ("the drums", "the sound source"), ("drum strokes", "notes or beats"), ("drums", "sound source")):
                    msg = msg.replace(a, b)
                raise AnveshanFailure(exc.category, msg, getattr(exc, "details", None)) from exc
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

def _audio_model_enabled(ctx: Any) -> bool:
    try:
        return bool(ctx.gateway.registry.model_id("audio"))
    except Exception:  # noqa: BLE001 - no gateway/registry: treat as disabled
        return False


def _utterance_checks(
    skill: SkillModel,
    attempt: AttemptMedia,
    attempt_record: Any,
    ctx: Any = None,
) -> Dict[str, MetricValue]:
    """Deterministic utterance checks.

    Raises INVALID_INPUT when the audio model listened and heard no speech (noise, music, silence),
    so a non-speech upload is refused instead of being scored.
    """
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
        if attempt_record is not None and _audio_model_enabled(ctx):
            raise AnveshanFailure(
                FailureCategory.INVALID_INPUT,
                "No speech can be heard in this recording. Record yourself saying the phrase clearly, close to the microphone.",
            )
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
            _ATTEMPT_DIR.set(asset_dir)
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
                    _SOURCE_DIR.set(emb_dir)
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
            um = _utterance_checks(skill, attempt, attempt_record, ctx)
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
