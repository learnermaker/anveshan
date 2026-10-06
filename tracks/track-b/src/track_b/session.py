"""Serialisable learner session and the attempt/session result view models (track-b-spec §10.1).

State machine::

    CREATED -> BASELINE_EVALUATED -> FEEDBACK_READY -> RETRY_EVALUATED -> COMPLETED
                                                       (further retries stay RETRY_EVALUATED)

* the first submission is the BASELINE (attempt_number 1); later ones are RETRYs (n >= 2);
* a retry before feedback exists raises INVALID_INPUT;
* ``complete`` uses the baseline and the LAST retry.

The session is plain JSON data (``to_json``/``from_json``). Runtime-only helpers (the clock
and the cached handoff) are not serialised; the artifact versions are pinned instead.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from tracks.common.models import AnveshanFailure, FailureCategory

from track_b.clock import Clock, SystemClock
from track_b.handoff import TrackBHandoff, load_handoff
from track_b.trajectory import TrajectoryResult

CREATED = "CREATED"
BASELINE_EVALUATED = "BASELINE_EVALUATED"
FEEDBACK_READY = "FEEDBACK_READY"
RETRY_EVALUATED = "RETRY_EVALUATED"
COMPLETED = "COMPLETED"
STATES = (CREATED, BASELINE_EVALUATED, FEEDBACK_READY, RETRY_EVALUATED, COMPLETED)


def jsonable(obj: Any) -> Any:
    """Convert evaluator output (numpy, Paths, pydantic, dataclasses, NaN) into plain JSON data."""
    if isinstance(obj, Enum):
        return jsonable(obj.value)
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    if isinstance(obj, Path):
        return obj.as_posix()
    if hasattr(obj, "tolist"):  # numpy arrays and scalars
        return jsonable(obj.tolist())
    return str(obj)


def trajectory_view(t: TrajectoryResult) -> Dict[str, Any]:
    return {
        "curve": [[jsonable(p), jsonable(v)] for p, v in t.curve],
        "curve_kind": t.curve_kind,
        "events": [jsonable(e) for e in t.events],
        "process_observable": bool(t.process_observable),
        "artifacts": jsonable(t.artifacts),
        "final_state": jsonable(t.final_state),
    }


def metrics_view(t: TrajectoryResult) -> Dict[str, Any]:
    return {
        mid: {"value": jsonable(m.value), "finding": m.finding, "uncertain_reason": m.uncertain_reason}
        for mid, m in t.metrics.items()
    }


@dataclass
class AttemptResult:
    """Everything the UI needs for one evaluated attempt. ``to_json`` is the service-api §3 shape."""

    data: Dict[str, Any]

    def to_json(self) -> Dict[str, Any]:
        return self.data

    @property
    def evaluation(self) -> Dict[str, Any]:
        return self.data["evaluation"]

    @property
    def attempt(self) -> Dict[str, Any]:
        return self.data["attempt"]


@dataclass
class SessionResult:
    data: Dict[str, Any]

    def to_json(self) -> Dict[str, Any]:
        return self.data


@dataclass
class Session:
    session_id: str
    case_id: str
    case_dir: str
    learner: Dict[str, Any]
    versions: Dict[str, int]
    created_at: str
    state: str = CREATED
    attempts: List[Dict[str, Any]] = field(default_factory=list)  # [{"result": AttemptResult json, "media": {...}}]
    result: Optional[Dict[str, Any]] = None                       # SessionResult json once COMPLETED
    clock: Clock = field(default_factory=SystemClock, repr=False, compare=False)
    _handoff: Optional[TrackBHandoff] = field(default=None, repr=False, compare=False)

    # -- handoff -----------------------------------------------------------
    def handoff(self) -> TrackBHandoff:
        if self._handoff is None:
            self._handoff = load_handoff(Path(self.case_dir), self.versions)
        return self._handoff

    # -- state -------------------------------------------------------------
    @property
    def next_attempt_number(self) -> int:
        return len(self.attempts) + 1

    def require_can_submit(self) -> None:
        if self.state == COMPLETED:
            raise AnveshanFailure(FailureCategory.INVALID_INPUT, "This session is already complete; start a new session.")
        if self.state == BASELINE_EVALUATED:
            raise AnveshanFailure(
                FailureCategory.INVALID_INPUT, "Feedback for the first attempt is not ready yet; read it before retrying."
            )

    def record_attempt(self, result: AttemptResult, media: Dict[str, Any]) -> None:
        n = self.next_attempt_number
        self.attempts.append({"result": result.to_json(), "media": media})
        if n == 1:
            self.state = BASELINE_EVALUATED
            if result.to_json().get("feedback") is not None:
                self.state = FEEDBACK_READY
        else:
            self.state = RETRY_EVALUATED

    # -- serialisation -----------------------------------------------------
    def to_json(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "case_id": self.case_id,
            "case_dir": self.case_dir,
            "learner": self.learner,
            "versions": self.versions,
            "created_at": self.created_at,
            "state": self.state,
            "attempts": self.attempts,
            "result": self.result,
        }

    @staticmethod
    def from_json(data: Dict[str, Any], clock: Optional[Clock] = None) -> "Session":
        if data.get("state") not in STATES:
            raise AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, f"unknown session state {data.get('state')!r}")
        return Session(
            session_id=data["session_id"],
            case_id=data["case_id"],
            case_dir=data["case_dir"],
            learner=data["learner"],
            versions={k: int(v) for k, v in data["versions"].items()},
            created_at=data["created_at"],
            state=data["state"],
            attempts=list(data.get("attempts", [])),
            result=data.get("result"),
            clock=clock or SystemClock(),
        )
