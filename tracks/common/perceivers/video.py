"""Layer 1 video perceiver.

Implements K6 §2.2: deterministic segmentation, keyframe extraction, embeddings
(keyframes + per-second frames), vision_fast batched perception, optional audio track.
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

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_PROMPT_ID = "perceive_frames"
_PROMPT_VERSION_FILE = "perceive_frames_v1.txt"

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

    # ---- Step 1: Deterministic segmentation ----
    fps = 1.0
    frames = sample_frames(path, fps=fps, max_side=256, max_frames=120)

    raw_segs, diffs = _segment_frames(frames, fps)
    all_diffs = np.array(diffs)

    # Compute active fraction from the diffs
    active_diffs = all_diffs[1:] if len(all_diffs) > 1 else all_diffs
    smooth_diffs = _smooth(active_diffs, _SMOOTH_WINDOW)
    active_count = int(np.sum(smooth_diffs >= _STILL_THRESHOLD))
    active_fraction = float(active_count / max(len(smooth_diffs), 1))

    # Add whole-video measurements
    meas_defs = [
        ("duration", round(duration, 3), "s"),
        ("segment_count", float(len(raw_segs)), None),
        ("active_fraction", round(active_fraction, 4), None),
    ]
    for label, value, unit in meas_defs:
        observations.append(Observation(
            obs_id=next_obs(),
            segment_id="seg-000",
            kind="measurement",
            label=label,
            value=value,
            unit=unit,
            certainty="observed",
            producer="det:video_segment",
        ))

    # Build time segments (seg-001...)
    time_seg_objects: List[Segment] = []
    keyframe_jpegs: List[bytes] = []

    for i, seg in enumerate(raw_segs):
        seg_id = f"seg-{i + 1:03d}"
        start_sec = seg["start_sec"]
        end_sec = seg["end_sec"]
        seg_diffs = np.array(seg["diffs"])

        # Keyframe = frame with minimum diff inside the segment
        start_frame = seg["start_frame"]
        end_frame = seg["end_frame"]
        frame_range = frames[start_frame : end_frame + 1]
        if frame_range:
            seg_diff_range = all_diffs[start_frame : end_frame + 1]
            kf_local = int(np.argmin(seg_diff_range))
            kf_frame = frame_range[kf_local]
            kf_sec = kf_frame.time_sec
            stability = float(1.0 - np.mean(seg_diff_range))
            stability = max(0.0, min(1.0, stability))

            # Save keyframe (max side 384)
            kf_name = f"kf_{seg_id}.jpg"
            kf_path = asset_dir / kf_name
            kf_img = kf_frame.image.copy()
            kf_img.thumbnail((384, 384), Image.LANCZOS)
            kf_img.save(str(kf_path), format="JPEG", quality=85)
            kf_jpeg = _resize_jpeg(kf_frame.image, 384)
            keyframe_jpegs.append(kf_jpeg)
        else:
            kf_sec = (start_sec + end_sec) / 2
            stability = 0.5
            kf_name = None
            keyframe_jpegs.append(b"")

        seg_obj = Segment(
            segment_id=seg_id,
            kind="time",
            start_sec=round(start_sec, 3),
            end_sec=round(end_sec, 3),
            keyframe_sec=round(kf_sec, 3),
            keyframe_asset=kf_name if kf_name else None,
            stability=round(stability, 4),
        )
        segments.append(seg_obj)
        time_seg_objects.append(seg_obj)

    # ---- Step 2: Embeddings ----
    # Keyframes (one per segment) + per-second frames (all sampled)
    per_sec_jpegs = [_resize_jpeg(f.image, 256) for f in frames]
    per_sec_times = [f.time_sec for f in frames]

    all_embed_items = (
        [ImagePart(j) for j in keyframe_jpegs if j]
        + [ImagePart(j) for j in per_sec_jpegs]
    )

    embedding_index: Dict[str, int] = {}
    embeddings_file = None

    if all_embed_items:
        try:
            embed_result = ctx.gateway.embed(
                items=all_embed_items,
                purpose=f"{purpose}_frames",
            )
            runs.append(embed_result.metadata.replay_key)
            vecs = embed_result.vectors

            # First N rows = keyframe rows (one per non-empty segment)
            kf_idx = 0
            for seg_obj in time_seg_objects:
                if seg_obj.segment_id in [f"seg-{i + 1:03d}" for i in range(len(raw_segs))]:
                    seg_num = int(seg_obj.segment_id.split("-")[1]) - 1
                    if seg_num < len(keyframe_jpegs) and keyframe_jpegs[seg_num]:
                        embedding_index[seg_obj.segment_id] = kf_idx
                        kf_idx += 1

            n_kf = kf_idx
            # Frame rows start after keyframes
            frame_rows = list(range(n_kf, n_kf + len(per_sec_jpegs)))
            specialists["frames"] = {
                "times": per_sec_times,
                "rows": frame_rows,
            }

            # Save
            npy_name = f"emb_{sha[:12]}.npy"
            npy_path = asset_dir / npy_name
            np.save(str(npy_path), vecs.astype(np.float16))
            embeddings_file = npy_name

        except ModelError as e:
            warnings_list.append(f"embedding failed: {e.message}")

    # ---- Step 3: Perception calls (vision_fast, batches of ≤4) ----
    gate = {}
    all_safety_categories: List[str] = []

    if time_seg_objects and any(keyframe_jpegs):
        try:
            prompt_text, prompt_ver = load_prompt(_PROMPTS_DIR / _PROMPT_VERSION_FILE)

            # Build (segment_id, jpeg) pairs for non-empty keyframes
            kf_pairs = []
            for i, seg_obj in enumerate(time_seg_objects):
                if i < len(keyframe_jpegs) and keyframe_jpegs[i]:
                    kf_pairs.append((seg_obj.segment_id, keyframe_jpegs[i], seg_obj.keyframe_sec or 0.0))

            first_batch = True
            for batch_start in range(0, len(kf_pairs), 4):
                batch = kf_pairs[batch_start : batch_start + 4]
                batch_parts = [
                    ImagePart(jpeg, label=f"Segment {seg_id} keyframe at t={kf_sec:.1f}s")
                    for seg_id, jpeg, kf_sec in batch
                ]

                result = ctx.gateway.generate_json(
                    model_key="vision_fast",
                    prompt_id=_PROMPT_ID,
                    prompt_version=prompt_ver,
                    prompt_text=prompt_text,
                    schema=_FramesPerceptionDTO,
                    parts=batch_parts,
                )
                runs.append(result.metadata.replay_key)
                dto = result.data

                # Merge safety categories from all batches
                if first_batch and dto.safety_categories:
                    all_safety_categories.extend(dto.safety_categories)
                    gate = {
                        "teachable": dto.teachable,
                        "teachable_reason": dto.teachable_reason,
                        "skill_kind": dto.skill_kind,
                        "safety_categories": dto.safety_categories,
                    }
                    first_batch = False
                elif dto.safety_categories:
                    for cat in dto.safety_categories:
                        if cat not in all_safety_categories:
                            all_safety_categories.append(cat)

                # Map segment observations
                batch_seg_ids = {seg_id for seg_id, _, _ in batch}
                for seg_data in dto.segments:
                    seg_id = seg_data.get("segment_id", "")
                    if seg_id not in batch_seg_ids:
                        if seg_id:
                            log.warning("perception returned unknown segment_id %s; ignoring", seg_id)
                        continue

                    state = seg_data.get("state")
                    action = seg_data.get("action")
                    notes = seg_data.get("notes")
                    objects = seg_data.get("objects", [])

                    if state:
                        observations.append(Observation(
                            obs_id=next_obs(),
                            segment_id=seg_id,
                            kind="state",
                            label=state[:200],
                            certainty="inferred",
                            producer="model:vision_fast",
                        ))
                    if action:
                        observations.append(Observation(
                            obs_id=next_obs(),
                            segment_id=seg_id,
                            kind="action",
                            label=action[:200],
                            certainty="inferred",
                            producer="model:vision_fast",
                        ))
                    for obj in (objects or [])[:5]:
                        observations.append(Observation(
                            obs_id=next_obs(),
                            segment_id=seg_id,
                            kind="object",
                            label=obj[:200],
                            certainty="inferred",
                            producer="model:vision_fast",
                        ))
                    if notes:
                        observations.append(Observation(
                            obs_id=next_obs(),
                            segment_id=seg_id,
                            kind="property",
                            label=notes[:200],
                            certainty="inferred",
                            producer="model:vision_fast",
                        ))

            # Update gate with merged safety
            if all_safety_categories and gate:
                gate["safety_categories"] = list(dict.fromkeys(all_safety_categories))

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
