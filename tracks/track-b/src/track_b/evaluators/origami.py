"""Origami trajectory evaluator (docs/plans/evaluation-core.md §4.2).

1. PyAV samples learner frames at 1 fps (at most ``MAX_FRAMES``; longer videos are subsampled
   evenly with a warning).
2. Gemma (``video_frames``) gets the reference keyframes R_0..R_k as labelled JPEGs plus batches
   of learner JPEG frames (never the video file) and labels each learner frame with a state index,
   "transition", "off_path" or "unclear" (prompt origami_match_v1).
3. ``origami_trajectory.analyze`` computes the deterministic trajectory: mode filter, progress,
   violations, skipped/missing states, order, last stable state.
4. A second Gemma call compares the learner's final frame with R_k using R_k's property
   checklist (prompt origami_final_v1). final_match = mean(last stable state == k, pairwise match).

All model output is parsed through Pydantic DTOs; invalid output raises ModelError. Metric ids
match the observer bindings written by track_a.goals.origami.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Literal, Optional, Sequence, Tuple, Union

import numpy as np
from PIL import Image
from pydantic import BaseModel, ConfigDict, Field, field_validator

from tracks.common import locators
from tracks.common.casedata import GoalModel
from tracks.common.goals.origami import OrigamiGoal
from tracks.common.media import Frame, image_to_jpeg_bytes, sample_frames
from tracks.common.models import AnveshanFailure, FailureCategory, ImagePart, ModelError, load_prompt
from tracks.common.runtime import RunContext
from tracks.common.schemas import EvidenceRef, Modality, VerificationState
from track_b.evaluators.origami_trajectory import Label, Trajectory, TrajEvent, analyze
from track_b.trajectory import AttemptMedia, DivergenceEvent, MetricValue, TrajectoryResult

FPS = 1.0
MAX_FRAMES = 90
MAX_SIDE = 384
MAX_IMAGES_PER_CALL = 8   # v2: learner frames only (no reference images); was 16
MIN_LEARNER_FRAMES_PER_CALL = 2
MODEL_KEY = "video_frames"
PROMPTS = Path(__file__).resolve().parents[3] / "prompts"
MATCH_PROMPT = PROMPTS / "origami_match_v2.txt"   # v2: text-only reference states
MATCH_PROMPT_V1 = PROMPTS / "origami_match_v1.txt"  # kept for reference
FINAL_PROMPT = PROMPTS / "origami_final_v1.txt"
ASSET_DIR = Path("knowledge") / "goal_assets"

M_FINAL = "origami.final_match"
M_ORDER = "origami.order_violations"
M_MISSING = "origami.missing_states"
M_OFF = "origami.off_path_events"
M_KEY = "origami.keystep_ok"
M_PROGRESS = "origami.progress"
_EVENT_METRIC = {"order_violations": M_ORDER, "missing_states": M_MISSING, "off_path_events": M_OFF}


# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


class FrameMatchDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    t: float
    state: Union[int, Literal["transition", "off_path", "unclear"]]
    note: str = ""

    @field_validator("state", mode="before")
    @classmethod
    def _state(cls, v):
        if isinstance(v, bool):
            raise ValueError("state must be an int or a label, not a boolean")
        if isinstance(v, float) and v.is_integer():
            return int(v)
        if isinstance(v, str) and v.strip().lstrip("Rr").isdigit():
            return int(v.strip().lstrip("Rr"))
        return v


class MatchBatchDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    frames: List[FrameMatchDTO] = Field(min_length=1)


class PropertyCheckDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    property: str
    present: Optional[bool] = None


class FinalCheckDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    matches: Optional[bool] = None
    properties: List[PropertyCheckDTO] = Field(default_factory=list)
    note: str = ""


# ---------------------------------------------------------------------------
# Frames
# ---------------------------------------------------------------------------


def subsample_even(frames: Sequence[Frame], cap: int) -> List[Frame]:
    if len(frames) <= cap:
        return list(frames)
    idx = sorted({int(round(i)) for i in np.linspace(0, len(frames) - 1, cap)})
    return [frames[i] for i in idx]


def load_reference_images(goal: OrigamiGoal, case_dir: Path) -> List[Image.Image]:
    out = []
    for s in goal.states:
        p = case_dir / ASSET_DIR / s.keyframe_asset
        if not p.exists():
            raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"reference keyframe {p} is missing; rebuild the goal")
        out.append(Image.open(p).convert("RGB"))
    return out


def _ref_parts(goal: OrigamiGoal, refs: Sequence[Image.Image]) -> List[ImagePart]:
    return [ImagePart(data=image_to_jpeg_bytes(img), label=f"Reference R{s.index}: {s.name}") for s, img in zip(goal.states, refs)]


def label_frames(goal: OrigamiGoal, refs: Sequence[Image.Image], frames: Sequence[Frame], ctx: RunContext):
    """Per-frame labels from Gemma.

    v2 policy: reference states described in text only (no reference images).
    Sends up to MAX_IMAGES_PER_CALL learner frames per call.
    Returns (labels, notes, run_keys).
    """
    per_call = MAX_IMAGES_PER_CALL  # learner frames only; ref states go as text in the prompt
    ref_text = "\n".join(f"- R{s.index}: {s.name} — {'; '.join(s.properties)}" for s in goal.states)
    k = goal.final_state_index
    labels: List[Label] = []
    notes: List[str] = []
    keys: List[str] = []
    for b in range(0, len(frames), per_call):
        batch = frames[b: b + per_call]
        prompt, version = load_prompt(
            MATCH_PROMPT, k=str(k), reference_states=ref_text,
            frame_times=", ".join(f"t={f.time_sec:.1f}s" for f in batch),
        )
        # v2: only learner frame images; reference states are in the prompt text
        parts = [ImagePart(data=image_to_jpeg_bytes(f.image), label=f"Learner frame t={f.time_sec:.1f}s") for f in batch]
        res = ctx.gateway.generate_json(
            model_key=MODEL_KEY, prompt_id="origami_match", prompt_version=version, prompt_text=prompt,
            schema=MatchBatchDTO, parts=parts, expected_behavior="one reference-state label per learner frame",
        )
        keys.append(res.metadata.replay_key)
        by_t: Dict[float, FrameMatchDTO] = {round(fr.t, 1): fr for fr in res.data.frames}  # type: ignore[attr-defined]
        for f in batch:
            fr = by_t.get(round(f.time_sec, 1))
            if fr is None:
                raise ModelError(FailureCategory.MODEL_FAILURE, f"origami_match: no label for learner frame t={f.time_sec:.1f}s",
                                 {"replay_key": res.metadata.replay_key})
            if isinstance(fr.state, int) and not 0 <= fr.state <= k:
                raise ModelError(FailureCategory.MODEL_FAILURE, f"origami_match: state {fr.state} outside R0..R{k}",
                                 {"replay_key": res.metadata.replay_key})
            labels.append(fr.state)
            notes.append(fr.note.strip())
    return labels, notes, keys


def final_check(goal: OrigamiGoal, refs: Sequence[Image.Image], last: Frame, ctx: RunContext):
    s = goal.states[goal.final_state_index]
    prompt, version = load_prompt(
        FINAL_PROMPT, k=str(s.index), name=s.name, properties="\n".join(f"- {p}" for p in s.properties),
    )
    parts = [
        ImagePart(data=image_to_jpeg_bytes(refs[s.index]), label=f"Reference R{s.index}: {s.name}"),
        ImagePart(data=image_to_jpeg_bytes(last.image), label=f"Learner final frame t={last.time_sec:.1f}s"),
    ]
    res = ctx.gateway.generate_json(
        model_key=MODEL_KEY, prompt_id="origami_final", prompt_version=version, prompt_text=prompt,
        schema=FinalCheckDTO, parts=parts, expected_behavior="pairwise final-state check against R_k checklist",
    )
    return res.data, res.metadata.replay_key


# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------


def _frame_ev(attempt: AttemptMedia, n: int, kind: str, t0: float, t1: float, note: str) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=f"ev.attempt.origami.{kind}.{n:02d}",
        source_id=locators.with_frame(attempt.source_id, t0 if kind != "missing_state" else t1),
        modality=Modality.VIDEO,
        start_sec=t0,
        end_sec=t1,
        cue_excerpt=note or None,
        verification_state=VerificationState.OBSERVED,
        confidence=1.0,
    )


def _note_at(tr: Trajectory, notes: Sequence[str], idx: int) -> str:
    return notes[idx] if 0 <= idx < len(notes) else ""


def to_result(goal: OrigamiGoal, tr: Trajectory, notes: Sequence[str], attempt: AttemptMedia,
              pairwise: Optional[FinalCheckDTO], warnings: List[str], run_keys: List[str]) -> TrajectoryResult:
    k = goal.final_state_index
    name = {s.index: s.name for s in goal.states}
    events: List[DivergenceEvent] = []
    for n, e in enumerate(tr.events):
        expected = f" (expected R{e.expected_state} {name[e.expected_state]})" if e.expected_state is not None and e.kind != "regression" else ""
        events.append(DivergenceEvent(
            metric=_EVENT_METRIC[e.metric], kind=e.kind, position=e.position, position_kind="time",
            evidence=_frame_ev(attempt, n, e.kind, e.t_start, e.t_end, _note_at(tr, notes, e.frame_index)),
            detail=e.detail + expected, severity="material",
        ))

    def first(metric: str) -> Tuple[Optional[EvidenceRef], Optional[float]]:
        for ev in events:
            if ev.metric == metric:
                return ev.evidence, ev.position
        return None, None

    metrics: Dict[str, MetricValue] = {}
    ev, pos = first(M_ORDER)
    metrics[M_ORDER] = MetricValue(
        value=float(tr.order_violations),
        finding=(f"{tr.order_violations} state(s) reached out of the demonstrated order"
                 + (f"; first at {pos:.1f} s" if pos is not None else "")),
        evidence=ev, position=pos)
    ev, pos = first(M_MISSING)
    unc = ", ".join(f"R{s} ({r})" for s, r in tr.uncertain_missing)
    if tr.missing:
        metrics[M_MISSING] = MetricValue(
            value=float(len(tr.missing)),
            finding=f"{len(tr.missing)} demonstrated state(s) never reached: {', '.join(f'R{s} {name[s]}' for s in tr.missing)}"
                    + (f"; uncertain: {unc}" if unc else ""),
            evidence=ev, position=pos)
    elif tr.uncertain_missing:
        metrics[M_MISSING] = MetricValue(value=None, finding=f"no confirmed missing state; uncertain: {unc}",
                                         uncertain_reason=tr.uncertain_missing[0][1])
    else:
        metrics[M_MISSING] = MetricValue(value=0.0, finding=f"all {k + 1} demonstrated states reached")
    ev, pos = first(M_OFF)
    metrics[M_OFF] = MetricValue(
        value=float(tr.off_path_events),
        finding=(f"{tr.off_path_events} off-path/regression event(s) (>= 2 consecutive frames)"
                 + (f"; first at {pos:.1f} s" if pos is not None else "")),
        evidence=ev, position=pos)
    metrics[M_KEY] = MetricValue(
        value=tr.keystep, finding=f"key step R{goal.key_state_index}: {tr.keystep_reason}" if goal.key_state_index is not None else tr.keystep_reason,
        uncertain_reason=None if tr.keystep is not None else tr.keystep_reason,
        position=tr.first_reached.get(goal.key_state_index) if goal.key_state_index is not None else None)

    last_t = tr.times[-1] if tr.times else 0.0
    final_ev = EvidenceRef(
        evidence_id="ev.attempt.origami.final", source_id=locators.with_frame(attempt.source_id, last_t),
        modality=Modality.VIDEO, start_sec=last_t, end_sec=last_t,
        cue_excerpt=(pairwise.note or None) if pairwise else None, verification_state=VerificationState.OBSERVED)
    stable = tr.final_reached
    pw = pairwise.matches if pairwise is not None else None
    last_desc = f"R{tr.last_stable_state}" if tr.last_stable_state is not None else "none"
    if pw is None:
        metrics[M_FINAL] = MetricValue(
            value=None, evidence=final_ev, position=last_t,
            finding=f"last stable state {last_desc} (target R{k}); final frame not clear enough for the pairwise check",
            uncertain_reason="final frame not visible enough for the pairwise check")
    else:
        val = (float(stable) + float(pw)) / 2.0
        metrics[M_FINAL] = MetricValue(
            value=val, evidence=final_ev, position=last_t,
            finding=f"last stable state {last_desc} (target R{k}); pairwise check vs R{k}: {'match' if pw else 'no match'}; final_match={val:.2f}")
    metrics[M_PROGRESS] = MetricValue(value=tr.progress, finding=f"max state reached R{max(tr.first_reached) if tr.first_reached else 0} of R{k} (progress {tr.progress:.2f})")

    frames_art = [{"t": t, "raw": r, "filtered": f, "note": _note_at(tr, notes, i)}
                  for i, (t, r, f) in enumerate(zip(tr.times, tr.raw, tr.filtered))]
    return TrajectoryResult(
        metrics=metrics,
        events=events,
        curve=list(tr.curve),
        curve_kind="time",
        process_observable=True,
        final_state={
            "last_stable_state": tr.last_stable_state,
            "target_state": k,
            "reached_by_trajectory": stable,
            "pairwise": pairwise.model_dump() if pairwise is not None else None,
        },
        artifacts={
            "frame_labels": frames_art,
            "stable_runs": [{"state": s, "start_sec": tr.times[a], "end_sec": tr.times[b]} for s, a, b in tr.stable_runs],
            "first_reached": {str(s): t for s, t in sorted(tr.first_reached.items())},
            "missing_states": tr.missing,
            "uncertain_states": [{"state": s, "reason": r} for s, r in tr.uncertain_missing],
            "reference_keyframes": {str(s.index): s.keyframe_asset for s in goal.states},
            "key_state_index": goal.key_state_index,
            "sampled_frames": len(tr.times),
        },
        run_keys=list(run_keys),
        warnings=list(warnings),
    )


def evaluate(goal: GoalModel, attempt: AttemptMedia, ctx: RunContext) -> TrajectoryResult:
    if attempt.kind != "video":
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"origami evaluator needs a video attempt, got {attempt.kind!r}")
    if goal.modality != "origami_video":
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"goal modality {goal.modality} is not origami_video")
    g = OrigamiGoal.model_validate(goal.payload)
    refs = load_reference_images(g, ctx.case_dir)
    try:
        frames = sample_frames(attempt.path, fps=FPS, max_side=MAX_SIDE)
    except ValueError as exc:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"cannot read video frames: {exc}") from exc
    if len(frames) < 2:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"attempt video has {len(frames)} frame(s) at {FPS:g} fps")
    warnings: List[str] = []
    if len(frames) > MAX_FRAMES:
        warnings.append(f"attempt has {len(frames)} frames at {FPS:g} fps; subsampled evenly to {MAX_FRAMES}")
        frames = subsample_even(frames, MAX_FRAMES)
    labels, notes, keys = label_frames(g, refs, frames, ctx)
    tr = analyze([f.time_sec for f in frames], labels, g.final_state_index, g.key_state_index)
    pairwise, fkey = final_check(g, refs, frames[-1], ctx)
    return to_result(g, tr, notes, attempt, pairwise, warnings, keys + [fkey])  # type: ignore[arg-type]
