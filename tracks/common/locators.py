"""Evidence locator convention: an optional fragment suffix on ``EvidenceRef.source_id``.

    <stable source id>[#<key>=<value>]

Supported keys:
    xywh=percent:x,y,w,h   image region in percent of width/height (W3C Media Fragments)
    stroke=i[-j]           stroke indices in a drawing-trace artifact
    onset=i[-j]            onset indices in an audio-onset artifact
    step=i                 state/step index in a goal model
    frame=t                learner/expert video frame at time t seconds

Time intervals stay in EvidenceRef.start_sec/end_sec. This is a helper, not a contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

_KEYS = {"xywh", "stroke", "onset", "step", "frame"}


@dataclass(frozen=True)
class Locator:
    source: str
    key: Optional[str] = None
    value: Optional[str] = None

    def __str__(self) -> str:
        return self.source if self.key is None else f"{self.source}#{self.key}={self.value}"


def parse(source_id: str) -> Locator:
    if "#" not in source_id:
        return Locator(source_id)
    base, frag = source_id.split("#", 1)
    if "=" not in frag:
        raise ValueError(f"malformed locator fragment: {source_id!r}")
    key, value = frag.split("=", 1)
    if key not in _KEYS:
        raise ValueError(f"unknown locator key {key!r} in {source_id!r}")
    if key == "xywh":
        region(Locator(base, key, value))  # validates
    return Locator(base, key, value)


def region(loc: Locator) -> Tuple[float, float, float, float]:
    if loc.key != "xywh" or loc.value is None or not loc.value.startswith("percent:"):
        raise ValueError(f"not a percent xywh locator: {loc}")
    parts = [float(p) for p in loc.value[len("percent:"):].split(",")]
    if len(parts) != 4 or any(p < 0 or p > 100 for p in parts) or parts[0] + parts[2] > 100.0001 or parts[1] + parts[3] > 100.0001:
        raise ValueError(f"xywh out of range: {loc}")
    return parts[0], parts[1], parts[2], parts[3]


def with_region(source: str, x: float, y: float, w: float, h: float) -> str:
    """Format a percent region, clamped to the image."""
    x = min(max(x, 0.0), 100.0)
    y = min(max(y, 0.0), 100.0)
    w = min(max(w, 0.0), 100.0 - x)
    h = min(max(h, 0.0), 100.0 - y)
    return f"{source}#xywh=percent:{x:.2f},{y:.2f},{w:.2f},{h:.2f}"


def with_index(source: str, key: str, start: int, end: Optional[int] = None) -> str:
    if key not in {"stroke", "onset", "step"}:
        raise ValueError(key)
    return f"{source}#{key}={start}" if end is None or end == start else f"{source}#{key}={start}-{end}"


def with_frame(source: str, time_sec: float) -> str:
    return f"{source}#frame={time_sec:.3f}"
