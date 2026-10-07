"""Layer 1 video perceiver.

Whole-video sampling (adaptive fps), one embedding per frame, domain-agnostic visual-state
segmentation (tracks/common/segmentation.py; pixel-motion fallback), ONE vision_fast call that
describes every keyframe and groups them into ordered stages, optional audio track.
"""

from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import numpy as np
from PIL import Image
from pydantic import BaseModel, Field

from tracks.common.models import AnveshanFailure, FailureCategory, ImagePart, ModelError, load_prompt
from tracks.common.perception import MediaInfoRecord, Observation, PerceptionRecord, Segment
from tracks.common.runtime import RunContext

log = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_PROMPT_ID = "perceive_frames"
_PROMPT_VERSION_FILE = "perceive_frames_v2.txt"
_MAX_FRAMES = 120

_STILL_THRESHOLD = 0.02
_SMOOTH_WINDOW = 3
_MIN_SEG_DUR = 2.0
_MAX_SEGMENTS = 12


class _FramesPerceptionDTO(BaseModel):
    segments: List[dict] = Field(default_factory=list)
    safety_categories: List[str] = Field(default_factory=lambda: ["none"])
    teachable: str = "unclear"
    teachable_reason: str = ""
    skill_kind: str = ""


def _resize_jpeg(img: Image.Image, max_side: int) -> bytes:
    img2 = img.copy()
    img2.thumbnail((max_side, max_side), Image.LANCZOS)
    buf = io.BytesIO()
    img2.convert("RGB").save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _smooth(arr: np.ndarray, window: int) -> np.ndarray:
    """Simple moving average with edge padding."""
    if len(arr) < window:
        return arr.copy()
    padded = np.pad(arr, window // 2, mode="edge")
    return np.convolve(padded, np.ones(window) / window, mode="valid")[: len(arr)]


def _monotone_stages(segs: List[Segment], by_id: Dict[str, dict]) -> Dict[str, str]:
    """Stage name per segment, forced to a non-decreasing stage sequence.

    The model groups keyframes into stages; we enforce the grouping deterministically:
    a segment whose stage number goes backwards (or is missing) stays in the current stage,
    and every segment of one stage carries that stage's FIRST name, so step building
    merges them into one step.
    """
    out: Dict[str, str] = {}
    cur_stage, cur_name = -1, None
    for s in segs:
        d = by_id.get(s.segment_id) or {}
        try:
            st = int(d.get("stage"))
        except (TypeError, ValueError):
            st = None
        name = (d.get("stage_name") or d.get("state") or "").strip() or None
        if name and (cur_name is None or (st is not None and st > cur_stage)):
            cur_stage, cur_name = (st if st is not None else 0), name
        if cur_name:
            out[s.segment_id] = cur_name
    return out


def _drop_brief_in_progress(segs: List[Segment], by_id: Dict[str, dict], stages: Dict[str, str]) -> Dict[str, str]:
    """Remove stages that are only a brief mid-action moment (e.g. "drawing the door").

    A stage is dropped only if EVERY keyframe in it was flagged in_progress by the model AND
    it is shorter than half the median stage duration. Skills where hands are always on the
    work (origami, knots) keep their long hand-held stages.
    """
    dur: Dict[str, float] = {}
    settled: Dict[str, bool] = {}
    for s in segs:
        name = stages.get(s.segment_id)
        if not name:
            continue
        dur[name] = dur.get(name, 0.0) + float((s.end_sec or 0.0) - (s.start_sec or 0.0)) + 1.0
        settled[name] = settled.get(name, False) or not (by_id.get(s.segment_id) or {}).get("in_progress")
    if len(dur) < 3:
        return stages
    med = float(np.median(list(dur.values())))
    drop = {n for n in dur if not settled[n] and dur[n] < 0.5 * med}
    if len(dur) - len(drop) < 2:
        return stages
    return {k: v for k, v in stages.items() if v not in drop}


def _segment_frames(
    frames,  # List of Frame objects from sample_frames
    fps: float,
) -> Tuple[List[dict], List[float]]:
    """Segment frames into still/active runs. Returns (segments, diffs).

    Each segment dict: {start_frame, end_frame, start_sec, end_sec, is_still, min_diff_frame}
    """
    if len(frames) < 2:
        return [], []

    grays = [np.asarray(f.image.convert("L"), dtype=np.float32) / 255.0 for f in frames]

    diffs = [0.0]  # diff[0] = 0 (no previous)
    for i in range(1, len(grays)):
        d = float(np.mean(np.abs(grays[i] - grays[i - 1])))
        diffs.append(d)
    diffs = np.array(diffs)
    smoothed = _smooth(diffs, _SMOOTH_WINDOW)

    labels = (smoothed >= _STILL_THRESHOLD).astype(int)  # 1=active, 0=still

    # Find maximal runs
    segs = []
    start = 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or labels[i] != labels[start]:
            end = i - 1
            start_sec = frames[start].time_sec
            end_sec = frames[end].time_sec
            seg = {
                "start_frame": start,
                "end_frame": end,
                "start_sec": start_sec,
                "end_sec": end_sec,
                "is_active": bool(labels[start]),
                "diffs": smoothed[start : end + 1].tolist(),
            }
            segs.append(seg)
            if i < len(labels):
                start = i

    # Merge runs shorter than MIN_SEG_DUR into previous
    merged = []
    for seg in segs:
        dur = seg["end_sec"] - seg["start_sec"]
        if dur < _MIN_SEG_DUR and merged:
            prev = merged[-1]
            prev["end_frame"] = seg["end_frame"]
            prev["end_sec"] = seg["end_sec"]
            prev["diffs"] = prev["diffs"] + seg["diffs"]
        else:
            merged.append(seg)

    # Cap at MAX_SEGMENTS
    while len(merged) > _MAX_SEGMENTS:
        durs = [s["end_sec"] - s["start_sec"] for s in merged]
        min_idx = int(np.argmin(durs))
        # Merge with neighbour
        if min_idx + 1 < len(merged):
            merged[min_idx]["end_frame"] = merged[min_idx + 1]["end_frame"]
            merged[min_idx]["end_sec"] = merged[min_idx + 1]["end_sec"]
            merged[min_idx]["diffs"] = merged[min_idx]["diffs"] + merged[min_idx + 1]["diffs"]
            merged.pop(min_idx + 1)
        elif min_idx > 0:
            merged[min_idx - 1]["end_frame"] = merged[min_idx]["end_frame"]
            merged[min_idx - 1]["end_sec"] = merged[min_idx]["end_sec"]
            merged[min_idx - 1]["diffs"] = merged[min_idx - 1]["diffs"] + merged[min_idx]["diffs"]
            merged.pop(min_idx)
        else:
            break

    return merged, diffs.tolist()


def perceive_video(
    path: Path,
    mime: str,
    ctx: RunContext,
    *,
    source_id: str,
    asset_dir: Path,
    purpose: Literal["source", "attempt"],
    skill_hint: Optional[str] = None,
    want_specialists: bool = True,
) -> PerceptionRecord:
    """Perceive a video: deterministic segmentation, embeddings, vision_fast per batch."""
    from tracks.common.media import decode_audio, probe, sample_frames, sha256_file

    path = Path(path)
    sha = sha256_file(path)
    asset_dir = Path(asset_dir)
    asset_dir.mkdir(parents=True, exist_ok=True)

    info = probe(path)
    duration = info.duration_sec or 0.0
    has_audio = info.has_audio

    segments: List[Segment] = []
    observations: List[Observation] = []
    runs: List[str] = []
    warnings_list: List[str] = []
    specialists: Dict = {}

    obs_idx = 0

    def next_obs() -> str:
        nonlocal obs_idx
        oid = f"obs-{obs_idx:03d}"
        obs_idx += 1
        return oid

    # seg-000: whole video
    segments.append(Segment(segment_id="seg-000", kind="whole"))

    # ---- Step 1: sample frames over the WHOLE video (adaptive fps, <= _MAX_FRAMES) ----
    fps = min(1.0, _MAX_FRAMES / duration) if duration > 0 else 1.0
    frames = sample_frames(path, fps=fps, max_side=256, max_frames=_MAX_FRAMES)
    if not frames:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"no decodable video frames in {path.name}")
    grays = [np.asarray(f.image.convert("L"), dtype=np.float32) / 255.0 for f in frames]
    motion = [0.0] + [float(np.mean(np.abs(grays[i] - grays[i - 1]))) for i in range(1, len(grays))]
    smooth_m = _smooth(np.array(motion[1:] or [0.0]), _SMOOTH_WINDOW)
    active_fraction = float(np.mean(smooth_m >= _STILL_THRESHOLD)) if len(smooth_m) else 0.0
    per_sec_jpegs = [_resize_jpeg(f.image, 256) for f in frames]
    per_sec_times = [f.time_sec for f in frames]

    # ---- Step 2: one embedding per sampled frame (keyframes reuse their frame's row) ----
    vecs: Optional[np.ndarray] = None
    embeddings_file = None
    try:
        embed_result = ctx.gateway.embed(items=[ImagePart(j) for j in per_sec_jpegs], purpose=f"{purpose}_frames")
        runs.append(embed_result.metadata.replay_key)
        vecs = np.asarray(embed_result.vectors, dtype=np.float32)
        npy_name = f"emb_{sha[:12]}.npy"
        np.save(str(asset_dir / npy_name), vecs.astype(np.float16))
        embeddings_file = npy_name
        specialists["frames"] = {"times": per_sec_times, "rows": list(range(len(frames))), "fps": round(fps, 4),
                                 "motion": [round(m, 5) for m in motion]}
    except ModelError as e:
        warnings_list.append(f"embedding failed: {e.message}; falling back to motion-only segmentation")

    # ---- Step 3: visual-state segmentation (domain-agnostic; see tracks/common/segmentation.py) ----
    from tracks.common import segmentation as seg_lib

    if vecs is not None and len(vecs) == len(frames):
        feats = seg_lib.layout_features([f.image for f in frames], vecs)
        st_segs = seg_lib.segment_k(feats, seg_lib.default_k(len(frames)), motion)
        raw_segs = [{"start_frame": s.start, "end_frame": s.end, "keyframe": s.keyframe, "stability": s.cohesion,
                     "calm": s.calm_fraction} for s in st_segs]
        seg_method = "embedding+layout DP (segment_k)"
    else:
        raw_segs = []
        for s in _segment_frames(frames, fps)[0]:
            rng = list(range(s["start_frame"], s["end_frame"] + 1))
            kf = min(rng, key=lambda k: motion[k])
            raw_segs.append({"start_frame": s["start_frame"], "end_frame": s["end_frame"], "keyframe": kf,
                             "stability": max(0.0, min(1.0, 1.0 - float(np.mean([motion[k] for k in rng])))),
                             "calm": round(float(np.mean([motion[k] < _STILL_THRESHOLD for k in rng])), 4)})
        seg_method = "pixel motion (fallback)"

    for label, value, unit in (
        ("duration", round(duration, 3), "s"),
        ("segment_count", float(len(raw_segs)), None),
        ("active_fraction", round(active_fraction, 4), None),
        ("sample_fps", round(fps, 4), "fps"),
    ):
        observations.append(Observation(obs_id=next_obs(), segment_id="seg-000", kind="measurement", label=label,
                                        value=value, unit=unit, certainty="observed", producer="det:video_segment"))

    time_seg_objects: List[Segment] = []
    keyframe_jpegs: List[bytes] = []
    embedding_index: Dict[str, int] = {}
    for i, rs in enumerate(raw_segs):
        seg_id = f"seg-{i + 1:03d}"
        kf = frames[rs["keyframe"]]
        kf_name = f"kf_{seg_id}.jpg"
        # Keyframes are what judges and reviewers look at: re-decode at up to 512 px
        # (analysis frames are 256 px thumbnails).
        try:
            hi = sample_frames(path, fps=4.0, start_sec=kf.time_sec, end_sec=kf.time_sec + 0.5, max_side=512)
            kf_img = (hi[0].image if hi else kf.image).copy()
        except Exception:  # noqa: BLE001 - keep the analysis frame if the re-decode fails
            kf_img = kf.image.copy()
        kf_img.convert("RGB").save(str(asset_dir / kf_name), format="JPEG", quality=85)
        keyframe_jpegs.append(_resize_jpeg(kf_img, 384))
        seg_obj = Segment(
            segment_id=seg_id, kind="time",
            start_sec=round(frames[rs["start_frame"]].time_sec, 3),
            end_sec=round(frames[rs["end_frame"]].time_sec, 3),
            keyframe_sec=round(kf.time_sec, 3), keyframe_asset=kf_name,
            stability=round(float(rs["stability"]), 4),
        )
        segments.append(seg_obj)
        time_seg_objects.append(seg_obj)
        observations.append(Observation(obs_id=next_obs(), segment_id=seg_id, kind="measurement", label="calm_fraction",
                                        value=float(rs["calm"]), certainty="observed", producer="det:video_segment"))
        if vecs is not None:
            embedding_index[seg_id] = int(rs["keyframe"])
    specialists["segmentation"] = {"method": seg_method,
                                   "frames": [[r["start_frame"], r["end_frame"]] for r in raw_segs]}

    # ---- Step 4: ONE vision_fast call sees every keyframe in order: descriptions + stage grouping ----
    gate = {}
    if time_seg_objects:
        try:
            prompt_text, prompt_ver = load_prompt(_PROMPTS_DIR / _PROMPT_VERSION_FILE)
            parts = [ImagePart(j, label=f"Segment {s.segment_id} keyframe at t={s.keyframe_sec:.1f}s")
                     for s, j in zip(time_seg_objects, keyframe_jpegs)]
            result = ctx.gateway.generate_json(
                model_key="vision_fast", prompt_id=_PROMPT_ID, prompt_version=prompt_ver,
                prompt_text=prompt_text, schema=_FramesPerceptionDTO, parts=parts,
                expected_behavior="one entry per keyframe with a non-decreasing stage grouping",
            )
            runs.append(result.metadata.replay_key)
            dto = result.data
            gate = {
                "teachable": dto.teachable, "teachable_reason": dto.teachable_reason,
                "skill_kind": dto.skill_kind,
                "safety_categories": list(dict.fromkeys(dto.safety_categories or ["none"])),
            }
            by_id = {d.get("segment_id"): d for d in dto.segments if isinstance(d, dict)}
            known_ids = {s.segment_id for s in time_seg_objects}
            unknown = [k for k in by_id if k not in known_ids]
            if unknown:
                log.warning("perception returned unknown segment ids %s; ignoring", unknown)
            stages = _monotone_stages(time_seg_objects, by_id)
            stages = _drop_brief_in_progress(time_seg_objects, by_id, stages)
            for seg_obj in time_seg_objects:
                d = by_id.get(seg_obj.segment_id) or {}
                stage_name = stages.get(seg_obj.segment_id)
                if stage_name:
                    observations.append(Observation(obs_id=next_obs(), segment_id=seg_obj.segment_id, kind="state",
                                                    label=stage_name[:200], certainty="inferred", producer="model:vision_fast"))
                for kind, val in (("action", d.get("action")), ("property", d.get("state")), ("property", d.get("notes"))):
                    if val:
                        observations.append(Observation(obs_id=next_obs(), segment_id=seg_obj.segment_id, kind=kind,
                                                        label=str(val)[:200], certainty="inferred", producer="model:vision_fast"))
                for obj in (d.get("objects") or [])[:5]:
                    observations.append(Observation(obs_id=next_obs(), segment_id=seg_obj.segment_id, kind="object",
                                                    label=str(obj)[:200], certainty="inferred", producer="model:vision_fast"))
            missing = [s.segment_id for s in time_seg_objects if s.segment_id not in by_id]
            if missing:
                warnings_list.append(f"vision_fast gave no entry for segments {missing}; their stage was carried from the previous segment")
        except ModelError as e:
            warnings_list.append(f"vision_fast video perception failed: {e.message}")

    # ---- Audio track: perceive if present ----
    if has_audio:
        try:
            from tracks.common.media import decode_audio
            from .audio import perceive_audio

            x = decode_audio(path, sample_rate=16000)
            max_samples = int(60 * 16000)
            if len(x) > max_samples:
                x = x[:max_samples]

            audio_record = perceive_audio(
                path,
                "audio/wav",
                ctx,
                source_id=f"{source_id}:audio",
                asset_dir=asset_dir,
                purpose=purpose,
                skill_hint=skill_hint,
                want_specialists=want_specialists,
                audio_array=x,
            )
            specialists["audio_track"] = audio_record.model_dump(mode="json")
            runs.extend(audio_record.runs)
            # Merge audio safety categories
            audio_gate = audio_record.gates.get("intake", {})
            if audio_gate and gate:
                for cat in audio_gate.get("safety_categories", []):
                    existing = gate.get("safety_categories", ["none"])
                    if cat not in existing:
                        gate["safety_categories"] = existing + [cat]
        except Exception as e:
            warnings_list.append(f"audio track perception failed: {e}")

    record = PerceptionRecord(
        media=MediaInfoRecord(
            source_id=source_id,
            modality="video",
            sha256=sha,
            mime_type=mime,
            duration_sec=round(duration, 3),
            width=info.width,
            height=info.height,
            has_audio=has_audio,
        ),
        segments=segments,
        observations=observations,
        embeddings_file=embeddings_file,
        embedding_index=embedding_index,
        specialists=specialists,
        gates={"intake": gate} if (purpose == "source" and gate) else {},
        runs=runs,
        warnings=warnings_list,
    )
    return record
