"""The only place the service touches Track A / Track B (docs/plans/service-api.md §2-§3).

Track modules are imported lazily on every call (cheap after the first import) so that
- the app starts and serves /api/health even when a track is not installed (routes answer 503);
- tests can substitute fakes via ``sys.modules``.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import threading
from contextlib import contextmanager
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path
from types import ModuleType
from typing import Any, Dict, Iterator

from tracks.common.models import FailureCategory
from tracks.common.runtime import RunContext

from anveshan_service.errors import ServiceError
from anveshan_service.paths import StoredUpload, case_dir
from anveshan_service.settings import Settings
from anveshan_service.userkey import current_key


def _module(name: str, label: str) -> ModuleType:
    try:
        return importlib.import_module(name)
    except ImportError as exc:
        raise ServiceError(
            503,
            "SERVICE_UNAVAILABLE",
            f"{label} ({name}) is not available in this build",
            {"module": name, "missing": getattr(exc, "name", None)},
        ) from exc


def track_a() -> ModuleType:
    return _module("track_a.api", "Track A")


def track_b() -> ModuleType:
    return _module("track_b.api", "Track B")


@contextmanager
def translated() -> Iterator[None]:
    """Convert track exceptions that mirror the shared taxonomy (e.g. ``TrackBFailure``) into
    ServiceErrors, and KeyError/FileNotFoundError from lookups into 404s."""
    try:
        yield
    except ServiceError:
        raise
    except Exception as exc:
        cat = getattr(exc, "category", None)
        value = getattr(cat, "value", cat)
        if isinstance(value, str) and value in FailureCategory.__members__:
            from anveshan_service.errors import failure_status

            raise ServiceError(
                failure_status(value), value, getattr(exc, "message", None) or str(exc), getattr(exc, "details", None) or {}
            ) from exc
        raise


def run_context(settings: Settings, cdir: Path, mode: str) -> RunContext:
    """A request with the visitor's own Gemini key runs live with that key (never stored)."""
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    key = current_key.get()
    if key:
        return RunContext.create(cdir, settings.data_dir, "live", api_key=key)
    return RunContext.create(cdir, settings.data_dir, mode)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Track B attempt media
# ---------------------------------------------------------------------------


def make_attempt_media(
    kind: str,
    primary: StoredUpload,
    extras: Dict[str, StoredUpload],
    session: Any = None,
    api: Any = None,
) -> Any:
    """Single adapter from uploaded files to ``AttemptMedia``.

    Uses ``track_b.api.intake_attempt(session, path, kind, extra)`` (Track B validation + canonical
    source id) when available; otherwise ``track_b.intake.from_upload``; otherwise builds
    ``track_b.trajectory.AttemptMedia`` directly (test fakes).
    """
    source_id = f"upload.{primary.sha256[:12]}"
    extra_paths = {k: v.path for k, v in extras.items()}
    if session is not None and api is not None and hasattr(api, "intake_attempt"):
        return api.intake_attempt(session, primary.path, kind, extra_paths or None)
    intake = sys.modules.get("track_b.intake")
    if intake is None and "track_b.intake" not in sys.modules:
        try:
            spec = importlib.util.find_spec("track_b.intake")
        except (ImportError, ValueError):
            spec = None
        if spec is not None:  # present: import errors inside Track B propagate (no silent fallback)
            intake = importlib.import_module("track_b.intake")
    if intake is not None and hasattr(intake, "from_upload"):
        return intake.from_upload(
            kind=kind,
            path=primary.path,
            mime_type=primary.mime_type,
            sha256=primary.sha256,
            source_id=source_id,
            extra=extra_paths,
        )
    try:
        trajectory = importlib.import_module("track_b.trajectory")
    except ImportError as exc:
        raise ServiceError(503, "SERVICE_UNAVAILABLE", "Track B (track_b.trajectory) is not available in this build") from exc
    return trajectory.AttemptMedia(
        kind=kind, path=primary.path, source_id=source_id, sha256=primary.sha256, mime_type=primary.mime_type, extra=extra_paths
    )


# ---------------------------------------------------------------------------
# Session helpers (Session is Track B's object; the service only reads a few attributes)
# ---------------------------------------------------------------------------

_session_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def session_lock(session_id: str) -> threading.Lock:
    with _locks_guard:
        return _session_locks.setdefault(session_id, threading.Lock())


def resource_lock(kind: str, key: str) -> threading.Lock:
    """One lock per draft/case directory, so concurrent requests (Cloud Run concurrency > 1) never
    interleave writes to the same directory while independent visitors still run in parallel."""
    return session_lock(f"{kind}:{key}")


def _plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def session_id_of(session: Any) -> str:
    sid = getattr(session, "session_id", None)
    if not sid:
        raise ServiceError(500, FailureCategory.CONTRACT_VIOLATION.value, "Track B session has no session_id")
    return str(sid)


def session_state_of(session: Any) -> Any:
    return _plain(getattr(session, "state", None))


def session_view(session: Any) -> Any:
    if hasattr(session, "to_json"):
        return session.to_json()
    if is_dataclass(session) and not isinstance(session, type):
        return asdict(session)
    if hasattr(session, "model_dump"):
        return session.model_dump(mode="json")
    return {"session_id": session_id_of(session), "state": session_state_of(session)}


def session_case_dir(session: Any, settings: Settings) -> Path:
    cdir = getattr(session, "case_dir", None)
    if cdir:
        p = Path(cdir)
        if p.is_dir():
            return p
    case_id = getattr(session, "case_id", None)
    if not case_id:
        raise ServiceError(500, FailureCategory.CONTRACT_VIOLATION.value, "Track B session has neither case_dir nor case_id")
    return case_dir(settings, str(case_id))


def to_json(result: Any) -> Any:
    return result.to_json() if hasattr(result, "to_json") else result
