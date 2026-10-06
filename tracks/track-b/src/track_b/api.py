"""Track B public API (docs/plans/service-api.md §3). The only module Integration imports.

    start_session(case_dir, learner_name, data_dir, *, clock=None, ids=None) -> Session
    submit_attempt(session, media, ctx) -> AttemptResult
    complete_session(session) -> SessionResult
    save_session(session, data_dir); load_session(session_id, data_dir) -> Session

Pipeline per attempt: modality evaluator (trajectory) -> deterministic scoring -> Evaluation
-> first divergence -> grounded feedback + drill (baseline and failed retries).
Track B never imports the Track A package.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from tracks.common.casedata import write_json
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.runtime import RunContext
from tracks.common.schemas import (
    AttemptType,
    Evaluation,
    EvidenceRef,
    Feedback,
    LearnerAttempt,
    Modality,
    ParticipantRef,
)

from track_b import evaluators
from track_b.clock import Clock, IdFactory, RandomIdFactory, SystemClock
from track_b.compare import compare_attempts
from track_b.divergence import find_first_divergence
from track_b.drill import build_drill
from track_b.evaluate import build_evaluation
from track_b.feedback import build_feedback
from track_b.handoff import load_handoff
from track_b.intake import build_attempt_media, media_duration_sec
from track_b.scoring import score_trajectory
from track_b.session import (
    COMPLETED,
    RETRY_EVALUATED,
    AttemptResult,
    Session,
    SessionResult,
    metrics_view,
    trajectory_view,
)
from track_b.transmission import build_transmission
from track_b.trajectory import AttemptMedia, TrajectoryResult

__all__ = [
    "AttemptMedia",
    "AttemptResult",
    "Session",
    "SessionResult",
    "start_session",
    "submit_attempt",
    "complete_session",
    "save_session",
    "load_session",
    "intake_attempt",
    "ACCEPTED_KINDS",
]

ACCEPTED_KINDS: Dict[str, tuple] = {
    "kolam_image": ("trace", "image"),
    "origami_video": ("video",),
    "tabla_audio": ("audio",),
}

EVIDENCE_MODALITY = {"trace": Modality.SENSOR, "image": Modality.IMAGE, "audio": Modality.AUDIO, "video": Modality.VIDEO}

_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def _invalid(message: str) -> AnveshanFailure:
    return AnveshanFailure(FailureCategory.INVALID_INPUT, message)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


def start_session(
    case_dir: Path,
    learner_name: str,
    data_dir: Path,
    *,
    clock: Optional[Clock] = None,
    ids: Optional[IdFactory] = None,
) -> Session:
    """Create a session pinned to the case's current (approved-else-latest) artifact versions."""
    name = (learner_name or "").strip()
    if not name:
        raise _invalid("Please enter your name to start a practice session.")
    clock = clock or SystemClock()
    ids = ids or RandomIdFactory()
    handoff = load_handoff(Path(case_dir))
    session_id = ids.new("sess")
    session = Session(
        session_id=session_id,
        case_id=handoff.case_id,
        case_dir=Path(case_dir).as_posix(),
        learner=ParticipantRef(participant_id=f"learner.{session_id}", name=name, role="learner").model_dump(mode="json"),
        versions=dict(handoff.versions),
        created_at=clock.now_iso(),
        clock=clock,
    )
    session._handoff = handoff
    return session


def intake_attempt(session: Session, path: Path, kind: str, extra: Optional[Dict[str, Path]] = None) -> AttemptMedia:
    """Validate an uploaded file for the session's next attempt (sets the canonical source id)."""
    return build_attempt_media(
        Path(path),
        kind,
        case_id=session.case_id,
        session_id=session.session_id,
        attempt_number=session.next_attempt_number,
        extra=extra,
    )


def runtime_class(ctx: RunContext, trajectory: TrajectoryResult) -> str:
    if not trajectory.run_keys:
        return "DETERMINISTIC"
    return "LIVE" if ctx.mode == "live" else "RECORDED_LIVE"


def submit_attempt(session: Session, media: AttemptMedia, ctx: RunContext) -> AttemptResult:
    session.require_can_submit()
    handoff = session.handoff()
    modality = handoff.goal.modality
    accepted = ACCEPTED_KINDS.get(modality, ())
    if media.kind not in accepted:
        raise _invalid(f"This case accepts {' or '.join(accepted)} attempts, not {media.kind}.")

    n = session.next_attempt_number
    attempt_type = AttemptType.BASELINE if n == 1 else AttemptType.RETRY
    stem = f"{session.case_id}.{session.session_id}"
    attempt_id = f"attempt.{stem}.{attempt_type.value}.{n}"

    evaluate = evaluators.get_evaluator(modality)
    trajectory: TrajectoryResult = evaluate(handoff.goal, media, ctx)

    scored = score_trajectory(handoff.rubric, handoff.observers, trajectory)
    duration = media_duration_sec(media)
    timed = duration is not None and media.kind in ("trace", "audio", "video")
    attempt = LearnerAttempt(
        attempt_id=attempt_id,
        task_id=handoff.task.task_id,
        learner=ParticipantRef.model_validate(session.learner),
        attempt_type=attempt_type,
        attempt_number=n,
        submitted_at=session.clock.now_iso(),
        evidence=EvidenceRef(
            evidence_id=f"ev.{attempt_id}",
            source_id=media.source_id,
            modality=EVIDENCE_MODALITY[media.kind],
            start_sec=0.0 if timed else None,
            end_sec=duration if timed else None,
            cue_excerpt=f"Learner {attempt_type.value} attempt {n} ({media.kind}, {media.mime_type})",
        ),
    )
    evaluation, eval_warnings = build_evaluation(
        evaluation_id=f"eval.{stem}.{n}",
        attempt_id=attempt_id,
        rubric=handoff.rubric,
        scored=scored,
        model_assisted=bool(trajectory.run_keys),
        evaluated_at=session.clock.now_iso(),
    )
    first = find_first_divergence(handoff, evaluation, scored, trajectory)

    feedback = drill = None
    if attempt_type == AttemptType.BASELINE or not evaluation.passed:
        feedback = build_feedback(
            feedback_id=f"fb.{stem}.{n}",
            handoff=handoff,
            evaluation=evaluation,
            first_divergence=first,
            attempt_kind=media.kind,
        )
        drill = build_drill(handoff, evaluation, first, media.kind)

    warnings = [*handoff.warnings, *trajectory.warnings, *eval_warnings]
    result = AttemptResult(
        {
            "attempt": attempt.model_dump(mode="json"),
            "evaluation": evaluation.model_dump(mode="json"),
            "trajectory": trajectory_view(trajectory),
            "metrics": metrics_view(trajectory),
            "first_divergence": first,
            "feedback": feedback.model_dump(mode="json") if feedback else None,
            "drill": drill,
            "runtime_class": runtime_class(ctx, trajectory),
            "warnings": warnings,
            "run_keys": list(trajectory.run_keys),
        }
    )
    session.record_attempt(
        result,
        {
            "kind": media.kind,
            "source_id": media.source_id,
            "sha256": media.sha256,
            "mime_type": media.mime_type,
            "path": Path(media.path).as_posix(),
            "extra": {k: Path(v).as_posix() for k, v in media.extra.items()},
        },
    )
    return result


def complete_session(session: Session) -> SessionResult:
    """Compare baseline with the last retry, build the TransmissionRecord and the validated bundle."""
    if session.state == COMPLETED and session.result is not None:
        return SessionResult(session.result)
    if session.state != RETRY_EVALUATED or len(session.attempts) < 2:
        raise _invalid("Submit a retry of the full task before completing the session.")
    handoff = session.handoff()
    base, last = session.attempts[0], session.attempts[-1]
    b_res, r_res = base["result"], last["result"]
    b_attempt = LearnerAttempt.model_validate(b_res["attempt"])
    r_attempt = LearnerAttempt.model_validate(r_res["attempt"])
    b_eval = Evaluation.model_validate(b_res["evaluation"])
    r_eval = Evaluation.model_validate(r_res["evaluation"])
    feedback = Feedback.model_validate(b_res["feedback"])

    comparison = compare_attempts(
        handoff.rubric,
        b_eval,
        r_eval,
        b_res["first_divergence"],
        b_res["trajectory"]["curve"],
        r_res["trajectory"]["curve"],
        recommended_retry_focus=feedback.recommended_retry_focus,
    )
    drill_criterion = (b_res.get("drill") or {}).get("criterion_id")
    tx = build_transmission(
        handoff=handoff,
        session_id=session.session_id,
        baseline_attempt=b_attempt,
        retry_attempt=r_attempt,
        baseline_eval=b_eval,
        retry_eval=r_eval,
        feedback=feedback,
        media_sha256=[base["media"]["sha256"], last["media"]["sha256"]],
        transitions=comparison["transitions"],
        drill_criterion=drill_criterion,
        recorded_at=session.clock.now_iso(),
    )
    data: Dict[str, Any] = {
        "bundle": tx["bundle"],
        "transmission_record": tx["transmission_record"],
        "comparison": comparison,
    }
    session.result = data
    session.state = COMPLETED
    return SessionResult(data)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _session_path(session_id: str, data_dir: Path) -> Path:
    if not _SESSION_ID.match(session_id or ""):
        raise _invalid(f"Invalid session id {session_id!r}.")
    return Path(data_dir) / "sessions" / f"{session_id}.json"


def save_session(session: Session, data_dir: Path) -> None:
    write_json(_session_path(session.session_id, data_dir), session.to_json())


def load_session(session_id: str, data_dir: Path, *, clock: Optional[Clock] = None) -> Session:
    path = _session_path(session_id, data_dir)
    if not path.exists():
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"Session {session_id} was not found.")
    return Session.from_json(json.loads(path.read_text(encoding="utf-8")), clock=clock)
