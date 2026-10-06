"""TablaGoal: GoalModel.payload schema for ``tabla_audio`` (case data, not a contract).

All times in ``onsets`` / ``grid`` / ``beats`` are seconds relative to the start of the
skill window; ``window_sec`` holds the absolute window in the source media. See
docs/plans/evaluation-core.md §5 and tracks/common/tabla_dsp.py for the definitions of
stroke pulse, grid index, beat grouping and cycle.

``payload_from_audio`` is the canonical implementation that both Track A builder and the
universal pipeline call; it returns (payload_dict, built_with_dict).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class TablaOnset(BaseModel):
    t: float = Field(ge=0.0)              # seconds from window start
    strength: float = Field(ge=0.0, le=1.0)
    low_ratio: float = Field(ge=0.0, le=1.0)
    bass: bool                            # low_ratio > bass_threshold (bayan proxy)
    grid_index: int = Field(ge=0)         # pulse slot
    timbre_class: Optional[int] = None    # v2: assigned class index (-1 = outlier), None = v1 goal


class TablaGridSlot(BaseModel):
    index: int = Field(ge=0)
    t: float                              # fitted slot time (window-relative)
    stroke: Optional[int] = None          # onset index on this slot, if any
    bass: Optional[bool] = None           # bass flag of that stroke


class TablaBeat(BaseModel):
    index: int = Field(ge=0)
    t: float
    bass: bool                            # any bass stroke within this beat


class TablaTolerances(BaseModel):
    timing_ms: float = 50.0               # per-stroke deviation that counts as a divergence
    tempo_pct: float = 5.0                # tempo error that counts as a divergence


class TablaBol(BaseModel):
    t: float
    bol: str


class TablaClassDisplay(BaseModel):
    """Display name and inferred bol for one timbre class."""
    class_: int = Field(alias="class")
    label: str
    source: str  # "deterministic" | "inferred"

    model_config = {"populate_by_name": True}


class TablaGoal(BaseModel):
    sample_rate: int
    window_sec: List[float] = Field(min_length=2, max_length=2)
    duration_sec: float
    onset_params: Dict[str, Any] = Field(default_factory=dict)
    onsets: List[TablaOnset] = Field(min_length=3)
    bass_threshold: float
    bass_centres: List[float] = Field(min_length=2, max_length=2)   # [no-bass centre, bass centre]
    bass_fraction: float
    stroke_pulse_sec: float = Field(gt=0)
    pulse_fit_score: float
    grid_residual_median_ms: float
    beat_pulses: int = Field(ge=1)
    beat_rule: str
    beat_period_sec: float = Field(gt=0)
    tempo_bpm: float = Field(gt=0)        # counted beats per minute (beat = beat_pulses pulses)
    strokes_per_min: float = Field(gt=0)  # pulse rate
    ioi_cv: Optional[float] = None        # pulse-normalised IOI CV of the source itself
    cycle_length_pulses: Optional[int] = None
    cycle_length_beats: Optional[float] = None
    cycle_confidence: float = 0.0
    cycle_note: Optional[str] = None
    grid: List[TablaGridSlot]
    beats: List[TablaBeat]
    tolerances: TablaTolerances = Field(default_factory=TablaTolerances)
    bols: Optional[List[TablaBol]] = None           # only when the optional audio model ran (INFERRED)
    bols_status: str = "audio_model_disabled"        # audio_model_disabled | inferred | model_failed
    # v2 timbre fields (None for v1 goals; backward-compatible)
    timbre: Optional[Dict[str, Any]] = None          # TimbreModel serialized
    class_display: Optional[List[Dict[str, Any]]] = None   # [{class, label, source}]


PAYLOAD_MODEL = TablaGoal


def ui_view(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Small JSON for the timeline UI: strokes with bass flags, beats, tempo and cycle."""
    g = TablaGoal.model_validate(payload)
    return {
        "modality": "tabla_audio",
        "window_sec": g.window_sec,
        "duration_sec": g.duration_sec,
        "tempo_bpm": round(g.tempo_bpm, 1),
        "strokes_per_min": round(g.strokes_per_min, 1),
        "stroke_pulse_sec": round(g.stroke_pulse_sec, 4),
        "beat_pulses": g.beat_pulses,
        "cycle_length_pulses": g.cycle_length_pulses,
        "cycle_length_beats": g.cycle_length_beats,
        "strokes": [{"i": i, "t": o.t, "bass": o.bass, "strength": o.strength,
                     "timbre_class": o.timbre_class} for i, o in enumerate(g.onsets)],
        "beats": [{"i": b.index, "t": b.t, "bass": b.bass} for b in g.beats],
        "bols": [b.model_dump() for b in g.bols] if g.bols else None,
        "bols_status": g.bols_status,
        "tolerances": g.tolerances.model_dump(),
        "class_display": g.class_display,
    }


_PROMPT_V2: Optional[Path] = None
_SR = 16000


def _get_prompt_v2() -> Path:
    global _PROMPT_V2
    if _PROMPT_V2 is None:
        # Path(__file__) = tracks/common/goals/tabla.py → parents[1] = tracks/common/
        _PROMPT_V2 = Path(__file__).resolve().parents[1] / "prompts" / "tabla_bols_v2.txt"
    return _PROMPT_V2


def payload_from_audio(
    path: Path,
    window: Optional[Tuple[float, Optional[float]]],
    ctx: Optional[Any] = None,  # RunContext | None
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Canonical tabla payload builder: decode audio, run deterministic analysis + timbre classes.

    Bol labelling via the audio model only when ``ctx`` is given and the audio model is enabled.
    Returns ``(payload_dict, built_with_dict)``. Raises AnveshanFailure on unusable input.
    """
    from tracks.common import tabla_dsp as dsp
    from tracks.common.media import decode_audio
    from tracks.common.models import AnveshanFailure, AudioPart, FailureCategory, ModelError, load_prompt
    from tracks.common.onsets import OnsetParams

    w0 = window[0] if window else 0.0
    w1 = window[1] if window else None
    try:
        x = decode_audio(path, _SR, start_sec=w0, end_sec=w1)
    except ValueError as exc:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"cannot decode audio from {path}: {exc}") from exc
    if w1 is None:
        w1 = w0 + len(x) / _SR

    try:
        payload = dsp.analyze_goal_audio(x, _SR)
    except dsp.GoalAnalysisError as exc:
        cat = FailureCategory.INVALID_INPUT if exc.kind == "too_few_strokes" else FailureCategory.AMBIGUOUS_EVIDENCE
        raise AnveshanFailure(cat, f"expert window: {exc}") from exc
    payload["window_sec"] = [float(w0), float(w1)]
    payload["bols"] = None
    payload["bols_status"] = "audio_model_disabled"

    # --- Timbre classes (deterministic) ---
    onset_times = [o["t"] for o in payload["onsets"]]
    feats = dsp.stroke_features(x, _SR, onset_times)
    timbre_warning: Optional[str] = None
    if feats.shape[0] >= 3:
        model = dsp.fit_timbre_classes(feats)
        timbre_warning = model.warning
        labels, _ = dsp.assign(model, feats)
        for i, onset in enumerate(payload["onsets"]):
            onset["timbre_class"] = int(labels[i])
        # Class display: ordered by descending low-band ratio (centroid feature 14 in z-scored space)
        low_idx = 14
        order = sorted(range(model.k), key=lambda c: -float(model.centroids[c, low_idx]))
        class_letters = "ABCDEF"
        class_display = []
        for rank, class_idx in enumerate(order):
            label = f"Class {class_letters[rank]}" if rank < len(class_letters) else f"Class {rank}"
            class_display.append({"class": int(class_idx), "label": label, "source": "deterministic"})
        payload["timbre"] = model.to_dict()
        payload["class_display"] = class_display
    else:
        for onset in payload["onsets"]:
            onset["timbre_class"] = None
        payload["timbre"] = None
        payload["class_display"] = None
        model = None

    # --- Bol labelling via audio model (optional) ---
    warnings: List[str] = []
    run_keys: List[str] = []
    if timbre_warning:
        warnings.append(f"Timbre fitting: {timbre_warning}")

    audio_enabled = False
    if ctx is not None:
        try:
            audio_enabled = ctx.gateway.registry.enabled("audio")
        except Exception:
            pass

    if audio_enabled and ctx is not None:
        prompt_path = _get_prompt_v2()
        prompt, version = load_prompt(
            prompt_path,
            n_strokes=str(len(onset_times)),
            duration_sec=f"{payload['duration_sec']:.2f}",
            onset_times=", ".join(f"{v:.3f}" for v in onset_times),
        )
        try:
            res = ctx.gateway.generate_json(
                model_key="audio",
                prompt_id="tabla_bols_v2",
                prompt_version=version,
                prompt_text=prompt,
                schema=dsp.BolsV2DTO,
                parts=[AudioPart(dsp.wav_bytes(x, _SR))],
                expected_behavior="one bol label per listed onset in order; no taal named",
            )
        except ModelError as exc:
            payload["bols_status"] = "model_failed"
            warnings.append(
                f"audio model bol naming failed ({exc.category.value}): {exc.message}; "
                "bol class labels stay deterministic"
            )
        else:
            run_keys.append(res.metadata.replay_key)
            bol_seq = res.data.bols
            # Align bol sequence to onset sequence
            dummy = [f"s{i}" for i in range(len(onset_times))]
            pairs = dsp.align_sequences(dummy, bol_seq)
            onset_to_bol: Dict[int, str] = {i: bol_seq[j] for i, j in pairs}
            payload["bols"] = [{"t": onset_times[i], "bol": onset_to_bol[i]}
                               for i in range(len(onset_times)) if i in onset_to_bol]
            payload["bols_status"] = "inferred" if payload["bols"] else "model_failed"
            # Update class_display with majority bol labels
            if model is not None and payload["bols_status"] == "inferred":
                from collections import Counter
                class_bol_votes: Dict[int, List[str]] = {}
                for onset_i, o in enumerate(payload["onsets"]):
                    c = o.get("timbre_class") if isinstance(o, dict) else None
                    b = onset_to_bol.get(onset_i)
                    if c is not None and c >= 0 and b and b != "?":
                        class_bol_votes.setdefault(int(c), []).append(b)
                for entry in payload["class_display"]:
                    c = entry["class"]
                    votes = class_bol_votes.get(int(c), [])
                    if votes:
                        majority = Counter(votes).most_common(1)[0][0]
                        old_label = entry["label"]  # e.g. "Class A"
                        entry["label"] = f"{old_label} (mostly '{majority}', inferred)"
                        entry["source"] = "inferred"

    built_with: Dict[str, Any] = {
        "dsp": dsp.ALGO_VERSION,
        "sample_rate": _SR,
        "onset_params": OnsetParams().__dict__.copy(),
        "audio_model_enabled": audio_enabled,
        "timbre_k": payload["timbre"]["k"] if payload.get("timbre") else None,
        "timbre_silhouette": payload["timbre"]["silhouette"] if payload.get("timbre") else None,
    }
    return payload, built_with, warnings, run_keys
