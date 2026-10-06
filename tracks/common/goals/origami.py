"""Origami GoalModel payload (case data, not a contract).

The goal is the ordered list of paper states R_0 .. R_k recognised in the expert
video's skill window (docs/plans/evaluation-core.md §4.1). Each state carries the
visible properties that define it, its interval in the expert video, and a small
keyframe JPEG stored under ``knowledge/goal_assets/``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, model_validator


class OrigamiState(BaseModel):
    index: int = Field(ge=0)
    name: str = Field(min_length=1)
    properties: List[str] = Field(min_length=1)   # visible checklist that defines the state
    start_sec: float = Field(ge=0.0)              # expert video time (absolute, not window-relative)
    end_sec: float = Field(ge=0.0)
    keyframe_sec: float = Field(ge=0.0)
    keyframe_asset: str = Field(min_length=1)     # file name under knowledge/goal_assets/

    @model_validator(mode="after")
    def _times(self) -> "OrigamiState":
        if not (self.start_sec <= self.keyframe_sec <= self.end_sec):
            raise ValueError(f"state {self.index}: need start <= keyframe <= end")
        return self


class OrigamiGoal(BaseModel):
    window: List[float] = Field(min_length=2, max_length=2)   # [start, end] s in the expert video
    fps: float = Field(gt=0.0)                                 # frame sampling rate used to build the goal
    states: List[OrigamiState] = Field(min_length=2)
    final_state_index: int = Field(ge=1)
    key_state_index: Optional[int] = None    # state used by CRIT-ORI-KEYSTEP (rule recorded in built_with)

    @model_validator(mode="after")
    def _order(self) -> "OrigamiGoal":
        if self.window[1] <= self.window[0]:
            raise ValueError("window end must be after start")
        for i, s in enumerate(self.states):
            if s.index != i:
                raise ValueError(f"state indices must be 0..k in order (got {s.index} at {i})")
            if i and s.start_sec < self.states[i - 1].end_sec:
                raise ValueError(f"state {i} starts before state {i - 1} ends")
        if self.final_state_index != len(self.states) - 1:
            raise ValueError("final_state_index must be the last state")
        if self.key_state_index is not None and not 1 <= self.key_state_index <= self.final_state_index:
            raise ValueError("key_state_index must be in 1..k")
        return self

    @property
    def k(self) -> int:
        return self.final_state_index


PAYLOAD_MODEL = OrigamiGoal


def ui_view(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Small JSON for the app: ordered states with keyframe asset ids (served at
    ``/api/media/{case_id}/goal/{asset}``)."""
    g = OrigamiGoal.model_validate(payload)
    return {
        "kind": "origami_video",
        "window": list(g.window),
        "final_state_index": g.final_state_index,
        "key_state_index": g.key_state_index,
        "states": [
            {
                "index": s.index,
                "label": f"R{s.index}",
                "name": s.name,
                "properties": list(s.properties),
                "start_sec": s.start_sec,
                "end_sec": s.end_sec,
                "keyframe_sec": s.keyframe_sec,
                "keyframe_asset": s.keyframe_asset,
            }
            for s in g.states
        ],
    }
