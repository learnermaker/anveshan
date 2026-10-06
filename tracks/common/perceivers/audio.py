"""Layer 1 audio perceiver.

Implements K6 §2.3: deterministic DSP measurements, time-segment splitting on silence,
and the audio model perception call. No embeddings for audio.
"""

from __future__ import annotations

import io
import logging
import wave
from pathlib import Path
from typing import List, Literal, Optional

import numpy as np
from pydantic import BaseModel, Field

from tracks.common.models import AnveshanFailure, AudioPart, FailureCategory, ModelError, load_prompt
from tracks.common.perception import MediaInfoRecord, Observation, PerceptionRecord, Segment
from tracks.common.runtime import RunContext

log = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"
_PROMPT_ID = "perceive_audio"
_PROMPT_VERSION_FILE = "perceive_audio_v1.txt"

_SAMPLE_RATE = 16000
_MAX_DUR_SEC = 60.0
_SILENCE_ENERGY_FRAC = 0.10
_SILENCE_GAP_SEC = 0.4
_MAX_SEGMENTS = 20
_AUDIO_MAX_WAV_SEC = 30.0


class _AudioPerceptionDTO(BaseModel):
    audio_kind: str = "environment"
    transcript: Optional[str] = None
    language: Optional[str] = None
    events: List[dict] = Field(default_factory=list)
    instrument: Optional[str] = None
    safety_categories: List[str] = Field(default_factory=lambda: ["none"])
    teachable: str = "unclear"
    teachable_reason: str = ""
    skill_kind: str = ""


def _wav_bytes(x: np.ndarray, sr: int) -> bytes:
    """Convert float32 array to WAV bytes."""
    buf = io.BytesIO()
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def _frame_energy(x: np.ndarray, frame_size: int) -> np.ndarray:
    """Compute RMS energy in non-overlapping frames."""
    n_frames = len(x) // frame_size
    if n_frames == 0:
        return np.array([float(np.sqrt(np.mean(x**2)))])
    frames = x[: n_frames * frame_size].reshape(n_frames, frame_size)
    return np.sqrt(np.mean(frames**2, axis=1))


def _silence_segments(x: np.ndarray, sr: int) -> List[tuple]:
    """Return list of (start_sec, end_sec) for silence gaps."""
    frame_size = int(0.02 * sr)  # 20ms frames
    energy = _frame_energy(x, frame_size)
    if len(energy) == 0:
        return []
    median_e = float(np.median(energy[energy > 0])) if (energy > 0).any() else 1e-9
    threshold = median_e * _SILENCE_ENERGY_FRAC
    is_silence = energy < threshold
    gaps = []
    in_gap = False
    gap_start = 0
    for i, s in enumerate(is_silence):
        if s and not in_gap:
            in_gap = True
            gap_start = i
        elif not s and in_gap:
            in_gap = False
            dur = (i - gap_start) * frame_size / sr
            if dur >= _SILENCE_GAP_SEC:
                gaps.append((gap_start * frame_size / sr, i * frame_size / sr))
    if in_gap:
        dur = (len(is_silence) - gap_start) * frame_size / sr
        if dur >= _SILENCE_GAP_SEC:
            gaps.append((gap_start * frame_size / sr, len(x) / sr))
    return gaps


def perceive_audio(
    path: Path,
    mime: str,
    ctx: RunContext,
    *,
    source_id: str,
    asset_dir: Path,
    purpose: Literal["source", "attempt"],
    skill_hint: Optional[str] = None,
    want_specialists: bool = True,
    audio_array: Optional[np.ndarray] = None,  # pre-decoded array (for video audio track)
) -> PerceptionRecord:
    """Perceive audio: DSP measurements, time segments, audio model call."""
    from tracks.common.media import decode_audio, sha256_file
    from tracks.common.onsets import detect_onsets
    from tracks.common.tabla_dsp import percussive_contrast, estimate_pulse

    path = Path(path)
    sha = sha256_file(path)
    asset_dir = Path(asset_dir)
    asset_dir.mkdir(parents=True, exist_ok=True)

    # Decode
    if audio_array is not None:
        x = audio_array.astype(np.float32)
    else:
        try:
            x = decode_audio(path, sample_rate=_SAMPLE_RATE)
        except Exception as e:
            raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"could not decode audio: {e}")

    # Truncate to max duration
    max_samples = int(_MAX_DUR_SEC * _SAMPLE_RATE)
    if len(x) > max_samples:
        x = x[:max_samples]
    duration = len(x) / _SAMPLE_RATE

    segments: List[Segment] = []
    observations: List[Observation] = []
    runs: List[str] = []
    warnings_list: List[str] = []

    obs_idx = 0

    def next_obs() -> str:
        nonlocal obs_idx
        oid = f"obs-{obs_idx:03d}"
        obs_idx += 1
        return oid

    # seg-000: whole audio
    segments.append(Segment(segment_id="seg-000", kind="whole"))

    # ---- Step 1: Deterministic measurements ----
    rms = float(np.sqrt(np.mean(x**2))) if len(x) > 0 else 0.0
    clipping_frac = float(np.mean(np.abs(x) >= 0.99)) if len(x) > 0 else 0.0

    # Onsets
    onsets = detect_onsets(x, _SAMPLE_RATE)
    onset_count = len(onsets)
    onset_rate = float(onset_count / duration) if duration > 0 else 0.0

    # Percussive contrast
    try:
        perc_contrast_val = float(percussive_contrast(x, _SAMPLE_RATE))
    except Exception:
        perc_contrast_val = 0.0

    # Speech-likeness: spectral flatness mean
    def spectral_flatness(signal: np.ndarray, n_fft: int = 1024, hop: int = 256) -> float:
        from numpy.lib.stride_tricks import sliding_window_view
        if len(signal) < n_fft:
            signal = np.pad(signal, (0, n_fft - len(signal)))
        frames = sliding_window_view(signal, n_fft)[::hop] * np.hanning(n_fft)
        S = np.abs(np.fft.rfft(frames, axis=1)) + 1e-10
        geo = np.exp(np.mean(np.log(S), axis=1))
        arith = np.mean(S, axis=1)
        flatness = geo / (arith + 1e-10)
        return float(np.mean(flatness))

    def modulation_energy_ratio(signal: np.ndarray, sr: int = _SAMPLE_RATE) -> float:
        """4 Hz modulation energy: power at 3-6 Hz / power at 0.5-20 Hz of the envelope."""
        frame_size = int(0.02 * sr)  # 20ms
        energy = _frame_energy(signal, frame_size)
        if len(energy) < 8:
            return 0.0
        fps = sr / frame_size  # frames per second
        fft = np.abs(np.fft.rfft(energy - energy.mean()))
        freqs = np.fft.rfftfreq(len(energy), 1.0 / fps)
        low_mask = (freqs >= 0.5) & (freqs <= 20.0)
        band_mask = (freqs >= 3.0) & (freqs <= 6.0)
        total = float(fft[low_mask].sum()) + 1e-10
        band = float(fft[band_mask].sum())
        return band / total

    flatness_val = spectral_flatness(x)
    mod_ratio = modulation_energy_ratio(x)

    # Pulse estimate
    pulse_sec = None
    if onset_count >= 8:
        try:
            pulse_sec, _ = estimate_pulse(onsets.times_sec)
        except Exception:
            pulse_sec = None

    meas_defs = [
        ("duration", round(duration, 3), "s"),
        ("rms", round(rms, 5), None),
        ("clipping_fraction", round(clipping_frac, 5), None),
        ("onset_count", float(onset_count), None),
        ("onset_rate", round(onset_rate, 4), "/s"),
        ("percussive_contrast", round(perc_contrast_val, 4), None),
        ("spectral_flatness_mean", round(flatness_val, 4), None),
        ("modulation_energy_ratio", round(mod_ratio, 4), None),
    ]
    if pulse_sec is not None:
        meas_defs.append(("pulse_sec", round(pulse_sec, 4), "s"))

    for label, value, unit in meas_defs:
        obs = Observation(
            obs_id=next_obs(),
            segment_id="seg-000",
            kind="measurement",
            label=label,
            value=value,
            unit=unit,
            certainty="observed",
            producer="det:audio_signal",
        )
        observations.append(obs)

    # Time segments: split at silence gaps (≥ 0.4s, energy < 10% of median)
    silence_gaps = _silence_segments(x, _SAMPLE_RATE)
    # Build time segments from silence boundaries
    time_boundaries = [0.0]
    for gap_start, gap_end in silence_gaps:
        time_boundaries.append((gap_start + gap_end) / 2)  # midpoint of gap
    time_boundaries.append(duration)

    time_segs = []
    for i in range(len(time_boundaries) - 1):
        start = time_boundaries[i]
        end = time_boundaries[i + 1]
        if end - start > 0.01:  # skip trivially short segments
            time_segs.append((start, end))

    # Cap at max segments by merging short adjacent
    while len(time_segs) > _MAX_SEGMENTS:
        # merge the shortest pair of adjacent segments
        durs = [e - s for s, e in time_segs]
        min_idx = int(np.argmin(durs))
        if min_idx + 1 < len(time_segs):
            merged = (time_segs[min_idx][0], time_segs[min_idx + 1][1])
            time_segs = time_segs[:min_idx] + [merged] + time_segs[min_idx + 2:]
        else:
            break

    for i, (start, end) in enumerate(time_segs):
        seg_id = f"seg-{i + 1:03d}"
        segments.append(Segment(
            segment_id=seg_id,
            kind="time",
            start_sec=round(start, 3),
            end_sec=round(end, 3),
        ))

    # ---- Step 3: Audio model perception call ----
    gate = {}
    audio_kind = "environment"

    if ctx.gateway.registry.enabled("audio"):
        try:
            # Clip to 30s for the model call
            clip_samples = int(_AUDIO_MAX_WAV_SEC * _SAMPLE_RATE)
            x_clip = x[:clip_samples]
            wav_data = _wav_bytes(x_clip, _SAMPLE_RATE)

            prompt_text, prompt_ver = load_prompt(_PROMPTS_DIR / _PROMPT_VERSION_FILE)
            result = ctx.gateway.generate_json(
                model_key="audio",
                prompt_id=_PROMPT_ID,
                prompt_version=prompt_ver,
                prompt_text=prompt_text,
                schema=_AudioPerceptionDTO,
                parts=[AudioPart(wav_data)],
            )
            runs.append(result.metadata.replay_key)
            dto = result.data
            audio_kind = dto.audio_kind

            # Transcript -> speech observation on seg-000
            if dto.transcript:
                observations.append(Observation(
                    obs_id=next_obs(),
                    segment_id="seg-000",
                    kind="speech",
                    label=dto.transcript[:500],
                    certainty="inferred",
                    producer="model:audio",
                ))

            # Events -> observations on time segments
            for event in dto.events[:10]:
                ev_label = str(event.get("label", "event"))
                approx_sec = event.get("approx_sec")
                # Find the containing segment
                seg_id = "seg-000"
                if approx_sec is not None:
                    for seg in segments:
                        if seg.kind == "time" and seg.start_sec is not None:
                            if seg.start_sec <= approx_sec < (seg.end_sec or float("inf")):
                                seg_id = seg.segment_id
                                break
                observations.append(Observation(
                    obs_id=next_obs(),
                    segment_id=seg_id,
                    kind="event",
                    label=ev_label,
                    certainty="inferred",
                    producer="model:audio",
                ))

            # Instrument -> object observation
            if dto.instrument:
                observations.append(Observation(
                    obs_id=next_obs(),
                    segment_id="seg-000",
                    kind="object",
                    label=dto.instrument,
                    certainty="inferred",
                    producer="model:audio",
                ))

            if purpose == "source":
                gate = {
                    "audio_kind": dto.audio_kind,
                    "teachable": dto.teachable,
                    "teachable_reason": dto.teachable_reason,
                    "skill_kind": dto.skill_kind,
                    "safety_categories": dto.safety_categories,
                }

        except ModelError as e:
            warnings_list.append(f"audio perception failed: {e.message}")
    else:
        warnings_list.append("audio model disabled (no model id configured); skipping audio perception")

    # Add audio_kind as an observation if we have it
    if audio_kind:
        observations.append(Observation(
            obs_id=next_obs(),
            segment_id="seg-000",
            kind="state",
            label=f"audio_kind: {audio_kind}",
            certainty="inferred" if gate else "observed",
            producer="model:audio" if gate else "det:audio_signal",
        ))

    from tracks.common.media import sha256_file as _sha_fn

    record = PerceptionRecord(
        media=MediaInfoRecord(
            source_id=source_id,
            modality="audio",
            sha256=sha,
            mime_type=mime,
            duration_sec=round(duration, 3),
        ),
        segments=segments,
        observations=observations,
        embeddings_file=None,
        embedding_index={},
        gates={"intake": gate} if (purpose == "source" and gate) else {},
        runs=runs,
        warnings=warnings_list,
    )
    return record
