"""Specialist and structure availability probes.

All logic is deterministic (no model calls). Reads measurement observations and embeddings
from an already-built PerceptionRecord to decide which specialists and structures are available.
See docs/plans/universal-pipeline.md §3.3 and K6 §2.5.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from tracks.common.perception import PerceptionRecord

# Thresholds (from universal-pipeline §3.3)
_LINE_ART_SEPARATION = 0.25
_LINE_ART_INK_MIN = 0.01    # 1%
_LINE_ART_INK_MAX = 0.40    # 40%
_LINE_ART_SKELETON_RATIO = 0.5
_LINE_ART_MAX_COMPONENTS = 6

_RHYTHM_ONSET_RATE = 1.5   # /s
_RHYTHM_MIN_DUR = 6.0       # s
_RHYTHM_PERC_CONTRAST = 1.5

_PROC_MIN_STILL = 2
_PROC_EMBED_DIST = 0.08     # 1 - cosine similarity

# Speech-likeness heuristics for utterance detection
_SPEECH_FLATNESS_MAX = 0.35
_SPEECH_MODULATION_MIN = 0.20


def _measurements(record: PerceptionRecord) -> Dict[str, Any]:
    """Collect measurement observations from seg-000."""
    result: Dict[str, Any] = {}
    for obs in record.observations:
        if obs.segment_id == "seg-000" and obs.kind == "measurement":
            result[obs.label] = obs.value
    return result


def _segment_measurements(record: PerceptionRecord) -> Dict[str, Dict[str, Any]]:
    """Per-segment measurements."""
    result: Dict[str, Dict[str, Any]] = {}
    for obs in record.observations:
        if obs.kind == "measurement":
            result.setdefault(obs.segment_id, {})[obs.label] = obs.value
    return result


def available_specialists(
    record: PerceptionRecord, path: Path
) -> Dict[str, Tuple[bool, str]]:
    """Returns {specialist_name: (available, reason)}."""
    results: Dict[str, Tuple[bool, str]] = {}
    m = _measurements(record)
    modality = record.media.modality

    # ---- line_art ----
    if modality == "image":
        separation = float(m.get("otsu_separation", 0.0) or 0.0)
        ink = float(m.get("ink_fraction", 0.0) or 0.0)
        skeleton_ratio = float(m.get("skeleton_length_ratio", 0.0) or 0.0)
        components = int(m.get("component_count", 999) or 999)
        ok = (
            separation >= _LINE_ART_SEPARATION
            and _LINE_ART_INK_MIN <= ink <= _LINE_ART_INK_MAX
            and skeleton_ratio >= _LINE_ART_SKELETON_RATIO
            and components <= _LINE_ART_MAX_COMPONENTS
        )
        if ok:
            results["line_art"] = (True, "image binarises cleanly with line-art characteristics")
        else:
            reasons = []
            if separation < _LINE_ART_SEPARATION:
                reasons.append(f"separation {separation:.2f} < {_LINE_ART_SEPARATION}")
            if not (_LINE_ART_INK_MIN <= ink <= _LINE_ART_INK_MAX):
                reasons.append(f"ink_fraction {ink:.2f} outside [{_LINE_ART_INK_MIN}, {_LINE_ART_INK_MAX}]")
            if skeleton_ratio < _LINE_ART_SKELETON_RATIO:
                reasons.append(f"skeleton_ratio {skeleton_ratio:.2f} < {_LINE_ART_SKELETON_RATIO}")
            if components > _LINE_ART_MAX_COMPONENTS:
                reasons.append(f"components {components} > {_LINE_ART_MAX_COMPONENTS}")
            results["line_art"] = (False, "; ".join(reasons) or "image does not meet line-art thresholds")

    # ---- rhythm ----
    # Check audio or video's audio track
    audio_m = m
    if modality == "video":
        audio_track = record.specialists.get("audio_track", {})
        if audio_track:
            # Get measurements from the audio track record
            audio_m = {}
            for obs in audio_track.get("observations", []):
                if obs.get("segment_id") == "seg-000" and obs.get("kind") == "measurement":
                    audio_m[obs["label"]] = obs.get("value")

    if modality in ("audio", "video"):
        onset_rate = float(audio_m.get("onset_rate", 0.0) or 0.0)
        duration = float(audio_m.get("duration", 0.0) or 0.0)
        perc_contrast = float(audio_m.get("percussive_contrast", 0.0) or 0.0)
        ok = (
            onset_rate >= _RHYTHM_ONSET_RATE
            and duration >= _RHYTHM_MIN_DUR
            and perc_contrast >= _RHYTHM_PERC_CONTRAST
        )
        if ok:
            results["rhythm"] = (True, "sufficient onset rate, duration, and percussive contrast")
        else:
            reasons = []
            if onset_rate < _RHYTHM_ONSET_RATE:
                reasons.append(f"onset_rate {onset_rate:.2f} < {_RHYTHM_ONSET_RATE}/s")
            if duration < _RHYTHM_MIN_DUR:
                reasons.append(f"duration {duration:.1f}s < {_RHYTHM_MIN_DUR}s")
            if perc_contrast < _RHYTHM_PERC_CONTRAST:
                reasons.append(f"percussive_contrast {perc_contrast:.2f} < {_RHYTHM_PERC_CONTRAST}")
            results["rhythm"] = (False, "; ".join(reasons) or "insufficient rhythm characteristics")

    # ---- procedure_states ----
    if modality == "video":
        # Need ≥ 2 still segments with embedding cosine distance ≥ 0.08
        still_segs = []
        for seg in record.segments:
            if seg.kind == "time" and seg.stability is not None:
                # A "still" segment has high stability (low activity)
                still_segs.append(seg.segment_id)

        if len(still_segs) >= _PROC_MIN_STILL and record.embeddings_file is not None:
            # Load embeddings and check distance
            asset_dir = path.parent if path.is_file() else path
            emb_path = None
            if record.embeddings_file:
                # Try to find the file
                candidates = [
                    asset_dir / record.embeddings_file,
                    asset_dir / "assets" / record.embeddings_file,
                ]
                for c in candidates:
                    if c.exists():
                        emb_path = c
                        break

            if emb_path is not None:
                try:
                    vecs = np.load(str(emb_path)).astype(np.float32)
                    # Get indices for still segments
                    indices = [record.embedding_index.get(sid) for sid in still_segs]
                    indices = [i for i in indices if i is not None and i < len(vecs)]
                    if len(indices) >= 2:
                        # Check if any pair has cosine distance >= threshold
                        found_pair = False
                        for i in range(len(indices)):
                            for j in range(i + 1, len(indices)):
                                a, b = vecs[indices[i]], vecs[indices[j]]
                                na, nb = np.linalg.norm(a), np.linalg.norm(b)
                                if na > 0 and nb > 0:
                                    cos_sim = float(np.dot(a / na, b / nb))
                                    dist = 1.0 - cos_sim
                                    if dist >= _PROC_EMBED_DIST:
                                        found_pair = True
                                        break
                            if found_pair:
                                break
                        if found_pair:
                            results["procedure_states"] = (True, ">=2 visually distinct still segments found")
                        else:
                            results["procedure_states"] = (False, f"still segments too similar (cosine dist < {_PROC_EMBED_DIST})")
                    else:
                        results["procedure_states"] = (False, "not enough still segments with embeddings")
                except Exception as e:
                    results["procedure_states"] = (False, f"could not load embeddings: {e}")
            else:
                # No embeddings loaded; just check segment count
                if len(still_segs) >= _PROC_MIN_STILL:
                    results["procedure_states"] = (True, f"≥{_PROC_MIN_STILL} still segments (embeddings not loaded)")
                else:
                    results["procedure_states"] = (False, "fewer than 2 still segments")
        elif len(still_segs) < _PROC_MIN_STILL:
            results["procedure_states"] = (False, f"only {len(still_segs)} still segments (need ≥{_PROC_MIN_STILL})")
        else:
            results["procedure_states"] = (False, "no embeddings available for distance check")

    return results


def available_structures(
    record: PerceptionRecord,
    specialists: Dict[str, Tuple[bool, str]],
) -> Dict[str, Tuple[bool, str]]:
    """Returns {structure: (available, reason)} based on modality and specialist results."""
    results: Dict[str, Tuple[bool, str]] = {}
    modality = record.media.modality
    m = _measurements(record)

    # ---- final_state ----
    if modality == "image":
        results["final_state"] = (True, "image source")
    elif modality == "video":
        # Available if the video has at least one still segment (the last one)
        has_still = any(s.kind == "time" and s.stability is not None for s in record.segments)
        if has_still:
            results["final_state"] = (True, "video has stable still segment for final state")
        else:
            results["final_state"] = (False, "no stable still segment found in video")
    else:
        results["final_state"] = (False, f"modality {modality} does not support final_state")

    # ---- procedure ----
    if modality == "video":
        time_segs = [s for s in record.segments if s.kind == "time"]
        if len(time_segs) >= 2:
            results["procedure"] = (True, f"video has {len(time_segs)} time segments")
        else:
            results["procedure"] = (False, f"only {len(time_segs)} time segments (need ≥2)")
    else:
        results["procedure"] = (False, f"modality {modality} does not support procedure")

    # ---- temporal_pattern ----
    rhythm_ok, rhythm_reason = specialists.get("rhythm", (False, "rhythm specialist not checked"))
    results["temporal_pattern"] = (rhythm_ok, rhythm_reason)

    # ---- utterance ----
    # Check audio or video audio track
    is_speech = False
    speech_reason = ""

    if modality == "audio":
        # Check if the audio_kind observation is speech
        for obs in record.observations:
            if obs.kind == "speech":
                is_speech = True
                speech_reason = "speech observation found"
                break

        if not is_speech:
            # Check heuristics: spectral flatness + modulation energy
            flatness = float(m.get("spectral_flatness_mean", 1.0) or 1.0)
            modulation = float(m.get("modulation_energy_ratio", 0.0) or 0.0)
            if flatness < _SPEECH_FLATNESS_MAX and modulation > _SPEECH_MODULATION_MIN:
                is_speech = True
                speech_reason = f"speech-like heuristics (flatness={flatness:.2f}, modulation={modulation:.2f})"

        if is_speech:
            results["utterance"] = (True, speech_reason)
        else:
            results["utterance"] = (False, "no speech detected in audio")

    elif modality == "video":
        audio_track = record.specialists.get("audio_track", {})
        if audio_track:
            # Check observations in the audio track
            for obs in audio_track.get("observations", []):
                if obs.get("kind") == "speech":
                    is_speech = True
                    speech_reason = "speech in video audio track"
                    break
            if not is_speech:
                audio_m: Dict[str, Any] = {}
                for obs in audio_track.get("observations", []):
                    if obs.get("segment_id") == "seg-000" and obs.get("kind") == "measurement":
                        audio_m[obs["label"]] = obs.get("value")
                flatness = float(audio_m.get("spectral_flatness_mean", 1.0) or 1.0)
                modulation = float(audio_m.get("modulation_energy_ratio", 0.0) or 0.0)
                if flatness < _SPEECH_FLATNESS_MAX and modulation > _SPEECH_MODULATION_MIN:
                    is_speech = True
                    speech_reason = f"speech-like heuristics in audio track"

        if is_speech:
            results["utterance"] = (True, speech_reason)
        else:
            results["utterance"] = (False, "no speech in video audio track")
    else:
        results["utterance"] = (False, f"modality {modality} does not support utterance directly")

    return results
