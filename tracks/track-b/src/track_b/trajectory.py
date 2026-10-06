"""Interfaces between modality evaluators and the generic Track B core."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from tracks.common.schemas import EvidenceRef

AttemptKind = Literal["trace", "image", "audio", "video"]
PositionKind = Literal["time", "stroke", "beat", "frame"]


@dataclass
class AttemptMedia:
    kind: AttemptKind
    path: Path                 # trace JSON / image / audio / video
    source_id: str             # e.g. upload.<sha12> or src.attempt.<case>.<session>.<n>
    sha256: str
    mime_type: str
    extra: Dict[str, Path] = field(default_factory=dict)  # e.g. {"raster": png} or {"video": optional tabla video}


@dataclass
class MetricValue:
    value: Optional[float]                  # None => not computable => criterion UNCERTAIN
    finding: str                            # human-readable, includes the measured numbers
    evidence: Optional[EvidenceRef] = None  # learner-side locator for this metric's worst/defining point
    uncertain_reason: Optional[str] = None
    position: Optional[float] = None        # where in the trajectory (for first-divergence ordering)


@dataclass
class DivergenceEvent:
    metric: str                 # metric id this event degrades
    kind: str                   # e.g. "off_path_ink", "missing_state", "late_stroke", "bass_mismatch"
    position: float
    position_kind: PositionKind
    evidence: EvidenceRef
    detail: str
    severity: Literal["material", "minor"] = "material"


@dataclass
class TrajectoryResult:
    metrics: Dict[str, MetricValue]
    events: List[DivergenceEvent]           # sorted by position
    curve: List[Tuple[float, float]]        # (position, progress 0..1)
    curve_kind: PositionKind
    process_observable: bool                # False e.g. for a final photo
    final_state: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, Any] = field(default_factory=dict)  # derived data for the UI (onsets, frame labels...)
    run_keys: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
