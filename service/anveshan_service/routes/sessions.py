"""Session routes -> Track B public API (docs/plans/service-api.md §3, §5)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field

from anveshan_service import adapters
from anveshan_service.deps import get_mode, get_settings
from anveshan_service.errors import invalid, not_found
from anveshan_service.paths import StoredUpload, case_dir, check_session_id, store_upload
from anveshan_service.settings import Settings

router = APIRouter(prefix="/api/sessions")

ATTEMPT_KINDS = ("trace", "image", "audio", "video")


class StartBody(BaseModel):
    case_id: str = Field(min_length=1, max_length=80)
    learner_name: str = Field(min_length=1, max_length=100)


def _load(api: Any, session_id: str, settings: Settings) -> Any:
    check_session_id(session_id)
    try:
        with adapters.translated():
            return api.load_session(session_id, settings.data_dir)
    except (FileNotFoundError, KeyError) as exc:
        raise not_found(f"unknown session {session_id}") from exc


@router.post("")
def start_session(body: StartBody, settings: Settings = Depends(get_settings)) -> Dict[str, Any]:
    learner = body.learner_name.strip()
    if not learner:
        raise invalid("learner_name must not be blank")
    cdir = case_dir(settings, body.case_id)
    api = adapters.track_b()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with adapters.translated():
        session = api.start_session(cdir, learner, settings.data_dir)
        api.save_session(session, settings.data_dir)
    return {"session_id": adapters.session_id_of(session), "state": adapters.session_state_of(session)}


@router.get("/{session_id}")
def get_session(session_id: str, settings: Settings = Depends(get_settings)) -> Any:
    api = adapters.track_b()
    session = _load(api, session_id, settings)
    return adapters.session_view(session)


@router.post("/{session_id}/attempts")
def submit_attempt(
    session_id: str,
    kind: str = Form(...),
    file: UploadFile = File(...),
    raster: Optional[UploadFile] = File(None),
    video: Optional[UploadFile] = File(None),
    settings: Settings = Depends(get_settings),
    mode: str = Depends(get_mode),
) -> Any:
    if kind not in ATTEMPT_KINDS:
        raise invalid(f"kind must be one of {list(ATTEMPT_KINDS)}", kind=kind[:40])
    api = adapters.track_b()
    check_session_id(session_id)
    with adapters.session_lock(session_id):
        session = _load(api, session_id, settings)
        cdir = adapters.session_case_dir(session, settings)
        primary = store_upload(file, settings, "file")
        extras: Dict[str, StoredUpload] = {}
        for name, upload in (("raster", raster), ("video", video)):
            if upload is not None and (upload.filename or upload.size):
                extras[name] = store_upload(upload, settings, name)
        ctx = adapters.run_context(settings, cdir, mode)
        with adapters.translated():
            media = adapters.make_attempt_media(kind, primary, extras, session=session, api=api)
            result = api.submit_attempt(session, media, ctx)
            api.save_session(session, settings.data_dir)
    return adapters.to_json(result)


@router.post("/{session_id}/complete")
def complete_session(session_id: str, settings: Settings = Depends(get_settings)) -> Any:
    api = adapters.track_b()
    check_session_id(session_id)
    with adapters.session_lock(session_id):
        session = _load(api, session_id, settings)
        with adapters.translated():
            result = api.complete_session(session)
            api.save_session(session, settings.data_dir)
    return adapters.to_json(result)
