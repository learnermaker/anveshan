"""Origami goal builder: expert video window -> ordered paper states R_0..R_k.

docs/plans/evaluation-core.md §4.1. Pipeline:

1. PyAV samples frames at 1 fps over the source's skill window (``window_sec``), max side 384 px.
2. Gemma (``video_frames``; JPEG frames only, never the video file) labels each frame in
   batches of <= 12 with a paper state name / transition / unclear (prompt origami_states_v1).
   Batches run in order and each batch is told the state names found so far.
3. Deterministic merge (this module, no model): mode filter (window 3) -> runs of >= 2 frames ->
   ordered states; the keyframe is the stablest frame of the state (lowest mean grayscale change
   to its neighbours, preferring frames without hand occlusion).
4. Keyframes are written to ``<case_dir>/knowledge/goal_assets/origami_state_<i>.jpg``.

Claims: one STEP claim per state (OBSERVED, interval in the expert video), one order claim
(OBSERVED), and model-described "how to fold" claims (INFERRED). Deterministic given the
same source and recorded model runs. A missing/disabled model raises ModelError.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional, Sequence, Tuple

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from tracks.common import locators
from tracks.common.casedata import Band, ObserverBinding, SourceRecord
from tracks.common.goals.origami import PAYLOAD_MODEL
from tracks.common.media import Frame, image_to_jpeg_bytes, probe, sample_frames
from tracks.common.models import AnveshanFailure, FailureCategory, ImagePart, ModelError, load_prompt
from tracks.common.runtime import RunContext
from tracks.common.schemas import (
    ClaimType,
    EvidenceRef,
    KnowledgeClaim,
    Modality,
    TaskConstraint,
    VerificationState,
)
from track_a.goals import CriterionTemplate, GoalBuildResult

ALGORITHM = "origami_goal_v1"
FPS = 1.0
BATCH_SIZE = 12
MAX_SIDE = 384
MIN_RUN = 2
MODE_WINDOW = 3
MODEL_KEY = "video_frames"
PROMPT_ID = "origami_states"
PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "origami_states_v1.txt"
ASSET_DIR = Path("knowledge") / "goal_assets"

METRIC_FINAL = "origami.final_match"
METRIC_ORDER = "origami.order_violations"
METRIC_MISSING = "origami.missing_states"
METRIC_OFF_PATH = "origami.off_path_events"
METRIC_KEYSTEP = "origami.keystep_ok"


# ---------------------------------------------------------------------------
# Model output DTOs
# ---------------------------------------------------------------------------


class FrameStateDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    t: float
    phase: Literal["state", "transition", "unclear"]
    state_name: Optional[str] = None
    properties: List[str] = Field(default_factory=list)
    hands_occlude: bool = False

    @model_validator(mode="after")
    def _name(self) -> "FrameStateDTO":
        if self.phase == "state" and not (self.state_name and self.state_name.strip()):
            raise ValueError(f"frame t={self.t}: phase 'state' needs a state_name")
        return self


class FoldNoteDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    state_name: str
    how_to: str


class StatesBatchDTO(BaseModel):
    model_config = ConfigDict(extra="ignore")
    frames: List[FrameStateDTO] = Field(min_length=1)
    fold_notes: List[FoldNoteDTO] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Deterministic helpers
# ---------------------------------------------------------------------------


def norm_name(name: Optional[str]) -> Optional[str]:
    if name is None:
        return None
    s = " ".join(name.strip().lower().split())
    return s or None


def mode_filter(labels: Sequence[Optional[str]], window: int = MODE_WINDOW) -> List[Optional[str]]:
    """Centered majority filter. A label replaces the original only if it holds a strict
    majority of the (possibly edge-truncated) window; otherwise the original stays."""
    half = window // 2
    out: List[Optional[str]] = []
    for i, orig in enumerate(labels):
        win = list(labels[max(0, i - half): i + half + 1])
        best, n = Counter(win).most_common(1)[0]
        out.append(best if n * 2 > len(win) else orig)
    return out


def motion_scores(frames: Sequence[Frame]) -> List[float]:
    """Mean absolute grayscale change to the neighbouring frames (lower = stabler)."""
    grays = [np.asarray(f.image.convert("L").resize((64, 48)), dtype=np.float32) for f in frames]
    out: List[float] = []
    for i, g in enumerate(grays):
        diffs = [float(np.mean(np.abs(g - grays[j]))) for j in (i - 1, i + 1) if 0 <= j < len(grays)]
        out.append(round(sum(diffs) / len(diffs), 4) if diffs else 0.0)
    return out


@dataclass
class MergedState:
    name: str
    frame_ids: List[int] = field(default_factory=list)   # frames (raw label == name) inside the state span
    start_sec: float = 0.0
    end_sec: float = 0.0


def merge_states(
    times: Sequence[float], raw: Sequence[Optional[str]], min_run: int = MIN_RUN
) -> Tuple[List[MergedState], List[str]]:
    """Ordered states from per-frame names (None = transition/unclear).

    Runs of the filtered labels with >= min_run frames create a state at their first
    occurrence. A later run of the most recent state (only transitions or short blips in
    between) extends it; a run of an earlier state after a different state is a revisit
    and is ignored with a warning (the expert sequence is forward)."""
    filt = mode_filter(raw)
    runs: List[Tuple[str, int, int]] = []
    i = 0
    while i < len(filt):
        j = i
        while j + 1 < len(filt) and filt[j + 1] == filt[i]:
            j += 1
        if filt[i] is not None and j - i + 1 >= min_run:
            runs.append((filt[i], i, j))
        i = j + 1
    states: List[MergedState] = []
    seen: Dict[str, int] = {}
    warnings: List[str] = []
    for name, a, b in runs:
        if name not in seen:
            seen[name] = len(states)
            states.append(MergedState(name=name, start_sec=times[a], end_sec=times[b]))
        elif states[-1].name == name:
            states[-1].end_sec = times[b]
        else:
            warnings.append(f"state '{name}' seen again at t={times[a]:.1f}-{times[b]:.1f}s after a later state; revisit ignored")
    for s in states:
        s.frame_ids = [k for k, t in enumerate(times) if s.start_sec <= t <= s.end_sec and raw[k] == s.name]
    return states, warnings


def pick_keyframe(frame_ids: Sequence[int], motion: Sequence[float], occluded: Sequence[bool]) -> int:
    clear = [k for k in frame_ids if not occluded[k]]
    pool = clear or list(frame_ids)
    return min(pool, key=lambda k: (motion[k], k))


def key_state_by_dwell(states: Sequence[MergedState]) -> Tuple[int, float]:
    """The state with the longest expert transition into it (ties -> earliest)."""
    best, best_d = 1, -1.0
    for j in range(1, len(states)):
        d = states[j].start_sec - states[j - 1].end_sec
        if d > best_d + 1e-9:
            best, best_d = j, d
    return best, round(best_d, 3)


def top_properties(props_per_frame: Sequence[Sequence[str]], limit: int = 4) -> List[str]:
    counts: Counter = Counter()
    first: Dict[str, int] = {}
    for i, props in enumerate(props_per_frame):
        for p in props:
            q = " ".join(p.strip().lower().split())
            if q:
                counts[q] += 1
                first.setdefault(q, i)
    return sorted(counts, key=lambda q: (-counts[q], first[q]))[:limit]


# ---------------------------------------------------------------------------
# Model step
# ---------------------------------------------------------------------------


def _known_states_text(known: Dict[str, List[str]]) -> str:
    if not known:
        return "(none yet)"
    return "\n".join(f"- {n}: {', '.join(p) if p else '(no properties yet)'}" for n, p in known.items())


def observe_frames(frames: Sequence[Frame], ctx: RunContext, batch_size: int = BATCH_SIZE):
    """Run the per-frame state recognition. Returns (per-frame DTOs, fold notes, run keys)."""
    out: List[FrameStateDTO] = []
    notes: Dict[str, str] = {}
    run_keys: List[str] = []
    known: Dict[str, List[str]] = {}
    for b in range(0, len(frames), batch_size):
        batch = frames[b: b + batch_size]
        prompt, version = load_prompt(
            PROMPT_PATH,
            fps=f"{FPS:g}",
            known_states=_known_states_text(known),
            frame_times=", ".join(f"t={f.time_sec:.1f}s" for f in batch),
        )
        parts = [ImagePart(data=image_to_jpeg_bytes(f.image), label=f"Frame t={f.time_sec:.1f}s") for f in batch]
        res = ctx.gateway.generate_json(
            model_key=MODEL_KEY,
            prompt_id=PROMPT_ID,
            prompt_version=version,
            prompt_text=prompt,
            schema=StatesBatchDTO,
            parts=parts,
            expected_behavior="one paper-state label per expert frame",
        )
        run_keys.append(res.metadata.replay_key)
        data: StatesBatchDTO = res.data  # type: ignore[assignment]
        by_t = {round(fr.t, 1): fr for fr in data.frames}
        missing = [f.time_sec for f in batch if round(f.time_sec, 1) not in by_t]
        if missing:
            raise ModelError(
                FailureCategory.MODEL_FAILURE,
                f"{PROMPT_ID}: model output has no label for frames {missing}",
                {"replay_key": res.metadata.replay_key},
            )
        for f in batch:
            fr = by_t[round(f.time_sec, 1)]
            out.append(fr)
            name = norm_name(fr.state_name) if fr.phase == "state" else None
            if name and name not in known:
                known[name] = [p.strip().lower() for p in fr.properties][:4]
        for n in data.fold_notes:
            key = norm_name(n.state_name)
            if key and n.how_to.strip():
                notes.setdefault(key, n.how_to.strip())
    return out, notes, run_keys


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def _clm(n: int) -> str:
    return f"CLM-{n:02d}"


def build(source_path: Path, source: SourceRecord, ctx: RunContext, *, case_id: str, version: int) -> GoalBuildResult:
    if source.role not in ("expert_video", "expert_demonstration"):
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"origami goal needs an expert video, got role {source.role}")
    warnings: List[str] = []
    if source.window_sec:
        w0, w1 = float(source.window_sec[0]), float(source.window_sec[1])
    else:
        info = probe(source_path)
        w0, w1 = 0.0, float(info.duration_sec or 0.0)
        warnings.append("source has no window_sec; using the whole video")
    frames = sample_frames(source_path, fps=FPS, start_sec=w0, end_sec=w1, max_side=MAX_SIDE)
    if len(frames) < 2 * MIN_RUN:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"too few frames in window [{w0}, {w1}] ({len(frames)})")

    dtos, fold_notes, run_keys = observe_frames(frames, ctx)
    times = [f.time_sec for f in frames]
    raw = [norm_name(d.state_name) if d.phase == "state" else None for d in dtos]
    merged, merge_warn = merge_states(times, raw)
    warnings += merge_warn
    if len(merged) < 2:
        raise AnveshanFailure(
            FailureCategory.AMBIGUOUS_EVIDENCE,
            f"only {len(merged)} stable paper state(s) recognised in the window; cannot define a goal path",
            {"run_keys": run_keys},
        )

    motion = motion_scores(frames)
    occluded = [d.hands_occlude for d in dtos]
    asset_dir = ctx.case_dir / ASSET_DIR
    asset_dir.mkdir(parents=True, exist_ok=True)
    states: List[dict] = []
    agreement: List[float] = []
    for i, m in enumerate(merged):
        kf = pick_keyframe(m.frame_ids, motion, occluded)
        asset = f"origami_state_{i}.jpg"
        (asset_dir / asset).write_bytes(image_to_jpeg_bytes(frames[kf].image, quality=80))
        props = top_properties([dtos[k].properties for k in m.frame_ids]) or [m.name]
        if props == [m.name]:
            warnings.append(f"state R{i} '{m.name}': model gave no properties; using the name as checklist")
        in_span = [k for k, t in enumerate(times) if m.start_sec <= t <= m.end_sec]
        agreement.append(round(len(m.frame_ids) / len(in_span), 2) if in_span else 0.0)
        states.append(
            {
                "index": i,
                "name": m.name,
                "properties": props,
                "start_sec": m.start_sec,
                "end_sec": m.end_sec,
                "keyframe_sec": times[kf],
                "keyframe_asset": asset,
            }
        )
    k = len(states) - 1
    key_idx, key_dwell = key_state_by_dwell(merged)
    payload = PAYLOAD_MODEL.model_validate(
        {"window": [w0, w1], "fps": FPS, "states": states, "final_state_index": k, "key_state_index": key_idx}
    ).model_dump(mode="json")

    sid = source.source_id
    claims: List[KnowledgeClaim] = []
    state_claim: Dict[int, str] = {}
    for i, s in enumerate(states):
        cid = _clm(len(claims) + 1)
        state_claim[i] = cid
        claims.append(
            KnowledgeClaim(
                claim_id=cid,
                claim_type=ClaimType.STEP,
                statement=f"State R{i} ({s['name']}): {'; '.join(s['properties'])}.",
                is_observed=True,
                evidence_refs=[
                    EvidenceRef(
                        evidence_id=f"ev.origami.state.{i:02d}",
                        source_id=sid,
                        modality=Modality.VIDEO,
                        start_sec=s["start_sec"],
                        end_sec=s["end_sec"],
                        cue_excerpt="; ".join(s["properties"]),
                        verification_state=VerificationState.OBSERVED,
                        confidence=agreement[i],
                    ),
                    EvidenceRef(
                        evidence_id=f"ev.origami.keyframe.{i:02d}",
                        source_id=locators.with_frame(sid, s["keyframe_sec"]),
                        modality=Modality.VIDEO,
                        start_sec=s["keyframe_sec"],
                        end_sec=s["keyframe_sec"],
                        cue_excerpt=f"keyframe {s['keyframe_asset']}",
                        verification_state=VerificationState.OBSERVED,
                        confidence=agreement[i],
                    ),
                ],
            )
        )
    order_cid = _clm(len(claims) + 1)
    path_text = " -> ".join(f"R{s['index']} {s['name']}" for s in states)
    claims.append(
        KnowledgeClaim(
            claim_id=order_cid,
            claim_type=ClaimType.CONDITION,
            statement=f"In the demonstration the paper passes through the states in this order: {path_text}.",
            is_observed=True,
            evidence_refs=[
                EvidenceRef(
                    evidence_id="ev.origami.order",
                    source_id=sid,
                    modality=Modality.VIDEO,
                    start_sec=states[0]["start_sec"],
                    end_sec=states[-1]["end_sec"],
                    cue_excerpt=path_text,
                    verification_state=VerificationState.OBSERVED,
                    confidence=round(min(agreement), 2),
                )
            ],
        )
    )
    howto_claim: Dict[int, str] = {}
    for j in range(1, len(states)):
        note = fold_notes.get(states[j]["name"])
        if not note:
            continue
        cid = _clm(len(claims) + 1)
        howto_claim[j] = cid
        a, b = states[j - 1]["end_sec"], states[j]["start_sec"]
        claims.append(
            KnowledgeClaim(
                claim_id=cid,
                claim_type=ClaimType.STEP,
                statement=f"From R{j - 1} ({states[j - 1]['name']}) to R{j} ({states[j]['name']}): {note}",
                is_observed=False,
                evidence_refs=[
                    EvidenceRef(
                        evidence_id=f"ev.origami.howto.{j:02d}",
                        source_id=sid,
                        modality=Modality.VIDEO,
                        start_sec=a,
                        end_sec=b,
                        cue_excerpt=note,
                        verification_state=VerificationState.INFERRED,
                        confidence=0.5,
                    )
                ],
            )
        )

    final = states[k]
    key = states[key_idx]
    kf_ev = [f"ev.origami.keyframe.{i:02d}" for i in range(len(states))]
    key_cites = [state_claim[key_idx]] + ([howto_claim[key_idx]] if key_idx in howto_claim else [])
    criteria = [
        CriterionTemplate(
            criterion_id="CRIT-ORI-ORDER",
            name="Folds in the demonstrated order",
            description="The learner reaches the paper states in the order the expert demonstrated.",
            observable_indicator="number of states reached out of the demonstrated order",
            weight=2.0, required=True, order_index=0,
            source_claim_ids=[order_cid],
            reference_evidence_ids=["ev.origami.order"],
            why_it_matters=f"The expert's video establishes the path {path_text} ({order_cid}).",
            drill_hint="Fold along with the reference keyframes one state at a time and check each state before moving on.",
            observer=ObserverBinding(metric=METRIC_ORDER, direction="lower_is_better",
                                     bands=[Band(status="satisfied", max=0), Band(status="partially_satisfied", max=1)],
                                     process=True),
        ),
        CriterionTemplate(
            criterion_id="CRIT-ORI-COMPLETE",
            name="Every demonstrated state reached",
            description="Each paper state R0..Rk from the demonstration appears in the attempt.",
            observable_indicator="number of demonstrated states never reached",
            weight=2.0, required=False, order_index=1,
            source_claim_ids=[state_claim[i] for i in range(len(states))],
            reference_evidence_ids=kf_ev,
            why_it_matters=f"The demonstration passes through {len(states)} distinct states ({state_claim[0]}-{state_claim[k]}).",
            drill_hint="Pause at each reference state and compare your paper to its keyframe before folding on.",
            observer=ObserverBinding(metric=METRIC_MISSING, direction="lower_is_better",
                                     bands=[Band(status="satisfied", max=0), Band(status="partially_satisfied", max=1)],
                                     process=True),
        ),
        CriterionTemplate(
            criterion_id="CRIT-ORI-CLEAN",
            name="No off-path folds",
            description="No sustained folds outside the demonstrated states and no fall-back of two or more states.",
            observable_indicator="number of off-path or regression events (>= 2 consecutive frames)",
            weight=1.0, required=False, order_index=2,
            source_claim_ids=[order_cid],
            reference_evidence_ids=["ev.origami.order"],
            why_it_matters=f"The expert goes from R0 to R{k} along the demonstrated state sequence ({order_cid}).",
            drill_hint="If the paper stops looking like any reference state, unfold to the last matching state and redo that fold.",
            observer=ObserverBinding(metric=METRIC_OFF_PATH, direction="lower_is_better",
                                     bands=[Band(status="satisfied", max=0), Band(status="partially_satisfied", max=1)],
                                     process=True),
        ),
        CriterionTemplate(
            criterion_id="CRIT-ORI-KEYSTEP",
            name=f"Key step executed as shown: R{key_idx} {key['name']}",
            description=f"The learner reaches R{key_idx} ({key['name']}) in order and without off-path folds on the way.",
            observable_indicator=f"R{key_idx} reached in order with a clean transition from R{key_idx - 1}",
            weight=2.0, required=False, order_index=3,
            source_claim_ids=key_cites,
            reference_evidence_ids=[f"ev.origami.keyframe.{key_idx:02d}"],
            why_it_matters=(
                f"R{key_idx} ({key['name']}) is the state the expert spends longest reaching "
                f"({key_dwell:.0f} s of folding from R{key_idx - 1}) ({state_claim[key_idx]})."
            ),
            drill_hint=f"Practise the fold from R{key_idx - 1} to R{key_idx} slowly, matching the reference keyframe.",
            observer=ObserverBinding(metric=METRIC_KEYSTEP, direction="higher_is_better",
                                     bands=[Band(status="satisfied", min=1.0)], process=True),
        ),
        CriterionTemplate(
            criterion_id="CRIT-ORI-FINAL",
            name=f"Reaches the target form ({final['name']})",
            description=f"The attempt ends in R{k} ({final['name']}).",
            observable_indicator="last stable state is R_k and the final frame matches the R_k checklist",
            weight=3.0, required=True, order_index=4,
            source_claim_ids=[state_claim[k]],
            reference_evidence_ids=[f"ev.origami.keyframe.{k:02d}"],
            why_it_matters=f"The demonstration ends in R{k} ({final['name']}): {'; '.join(final['properties'])} ({state_claim[k]}).",
            drill_hint="Compare your final paper with the target keyframe property by property.",
            observer=ObserverBinding(metric=METRIC_FINAL, direction="higher_is_better",
                                     bands=[Band(status="satisfied", min=1.0), Band(status="partially_satisfied", min=0.5)]),
        ),
    ]

    lines = [f"1. Start from R0 ({states[0]['name']}): {'; '.join(states[0]['properties'])}. [{state_claim[0]}]"]
    for j in range(1, len(states)):
        s = states[j]
        cite = f"[{state_claim[j]}]" + (f"[{howto_claim[j]}]" if j in howto_claim else "")
        how = f" {fold_notes[s['name']]}" if j in howto_claim else ""
        lines.append(f"{j + 1}. Fold to R{j} ({s['name']}): {'; '.join(s['properties'])}.{how} {cite}")
    lines.append(f"{len(states) + 1}. Stop at R{k} ({final['name']}) and hold it to the camera. [{state_claim[k]}][{order_cid}]")

    return GoalBuildResult(
        title="Origami crane: square to bird base",
        summary=f"{len(states)} paper states recognised in the expert video window {w0:g}-{w1:g} s: {path_text}.",
        goal_payload=payload,
        claims=claims,
        criteria=criteria,
        task_title="Fold a crane up to the bird base",
        task_instructions="\n".join(lines),
        task_constraints=[
            TaskConstraint(constraint_type="material_spec", description="One square sheet of paper", value="about 15 cm square"),
            TaskConstraint(constraint_type="scope", description=f"Stop at R{k} ({final['name']})", value=f"R{k}"),
            TaskConstraint(
                constraint_type="capture",
                description="Top-down video with the paper and hands in frame. Frames are sampled at 1 fps, at most 90 frames; longer videos are subsampled evenly.",
                value="1 fps, <= 90 frames",
            ),
        ],
        warnings=warnings,
        run_keys=run_keys,
        built_with={
            "algorithm": ALGORITHM,
            "fps": FPS,
            "batch_size": BATCH_SIZE,
            "max_side": MAX_SIDE,
            "min_run_frames": MIN_RUN,
            "mode_filter_window": MODE_WINDOW,
            "keyframe_rule": "lowest mean grayscale change to neighbouring frames among the state's frames, preferring frames without hand occlusion",
            "key_state_rule": "longest expert transition into the state (start_j - end_{j-1})",
            "prompt": f"{PROMPT_ID}@v1",
            "model_key": MODEL_KEY,
            "window": [w0, w1],
            "frames_sampled": len(frames),
            "state_agreement": agreement,
            "placeholder": False,
        },
    )
