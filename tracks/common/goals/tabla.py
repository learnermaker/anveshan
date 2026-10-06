"""TablaGoal: GoalModel.payload schema for ``tabla_audio`` (case data, not a contract).

All times in ``onsets`` / ``grid`` / ``beats`` are seconds relative to the start of the
skill window; ``window_sec`` holds the absolute window in the source media. See
docs/plans/evaluation-core.md §5 and tracks/common/tabla_dsp.py for the definitions of
stroke pulse, grid index, beat grouping and cycle.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TablaOnset(BaseModel):
    t: float = Field(ge=0.0)              # seconds from window start
    strength: float = Field(ge=0.0, le=1.0)
    low_ratio: float = Field(ge=0.0, le=1.0)
    bass: bool                            # low_ratio > bass_threshold (bayan proxy)
    grid_index: int = Field(ge=0)         # pulse slot


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
        "strokes": [{"i": i, "t": o.t, "bass": o.bass, "strength": o.strength} for i, o in enumerate(g.onsets)],
        "beats": [{"i": b.index, "t": b.t, "bass": b.bass} for b in g.beats],
        "bols": [b.model_dump() for b in g.bols] if g.bols else None,
        "bols_status": g.bols_status,
        "tolerances": g.tolerances.model_dump(),
    }
