"""Compose routes: upload -> analyze -> draft -> create case (docs/plans/service-api.md §compose).

Prefix: /api/compose
POST /analyze                      -> Draft.to_view() (refused returns 200 with refused:true)
GET  /{draft_id}                   -> Draft.to_view()
POST /{draft_id}/refine            -> Draft.to_view()
POST /{draft_id}/create            -> case .to_view()
"""

from __future__ import annotations

import re
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, Form, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from anveshan_service import adapters
from anveshan_service.deps import get_mode, get_settings
from anveshan_service.errors import ServiceError, invalid, not_found
from anveshan_service.paths import store_upload
from anveshan_service.settings import Settings

router = APIRouter(prefix="/api/compose")

_DRAFT_ID_RE = re.compile(r"^[0-9a-f]{16}$")


def _check_draft_id(draft_id: str) -> str:
    if not _DRAFT_ID_RE.fullmatch(draft_id or ""):
        raise invalid("invalid draft id", draft_id=draft_id[:32] if draft_id else draft_id)
    return draft_id


class RefineBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)


class CreateBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Optional[str] = Field(default=None, max_length=200)
    skill_summary: Optional[str] = Field(default=None, max_length=1000)
    domain: Optional[str] = Field(default=None, max_length=100)
    transmission_mode: Optional[str] = None
    learner_input_kinds: Optional[list] = None
    goal_hint: Optional[str] = Field(default=None, max_length=500)
    skill_model: Optional[dict] = None


def _composer():
    """Lazy import of the composer module."""
    try:
        import importlib
        return importlib.import_module("track_a.composer")
    except ImportError as exc:
        raise ServiceError(
            503,
            "SERVICE_UNAVAILABLE",
            "Composer (track_a.composer) is not available in this build",
            {"module": "track_a.composer", "missing": getattr(exc, "name", None)},
        ) from exc


def _track_a():
    return adapters.track_a()


@router.post("/analyze")
def analyze_upload(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    description: Optional[str] = Form(default=None),
    rights_confirmed: bool = Form(default=False),
    settings: Settings = Depends(get_settings),
    mode: str = Depends(get_mode),
) -> Any:
    """Upload a file and create a draft. Returns 200 even for refused drafts (refused:true)."""
    composer = _composer()
    stored = store_upload(file, settings, "file")

    draft_dir = settings.data_dir / "drafts" / "tmp"  # ctx needs a case_dir; use data_dir
    ctx = adapters.run_context(settings, settings.data_dir, mode)

    with adapters.translated():
        draft = composer.create_draft(
            settings.data_dir,
            stored.path,
            stored.mime_type,
            ctx,
            title_hint=title,
            description=description,
            rights_confirmed=rights_confirmed,
        )
    return draft.to_view()


@router.get("/{draft_id}")
def get_draft(
    draft_id: str,
    settings: Settings = Depends(get_settings),
) -> Any:
    _check_draft_id(draft_id)
    composer = _composer()
    with adapters.translated():
        draft = composer.load_draft(settings.data_dir, draft_id)
    return draft.to_view()


@router.post("/{draft_id}/refine")
def refine_draft(
    draft_id: str,
    body: RefineBody,
    settings: Settings = Depends(get_settings),
    mode: str = Depends(get_mode),
) -> Any:
    _check_draft_id(draft_id)
    composer = _composer()
    ctx = adapters.run_context(settings, settings.data_dir, mode)
    with adapters.translated():
        draft = composer.refine_draft(
            settings.data_dir,
            draft_id,
            ctx,
            title=body.title,
            description=body.description,
        )
    return draft.to_view()


@router.post("/{draft_id}/create")
def create_case(
    draft_id: str,
    body: Optional[CreateBody] = Body(None),
    settings: Settings = Depends(get_settings),
    mode: str = Depends(get_mode),
) -> Any:
    _check_draft_id(draft_id)
    composer = _composer()
    track_a = _track_a()
    ctx = adapters.run_context(settings, settings.data_dir, mode)
    edits = body.model_dump(exclude_none=True) if body else {}
    with adapters.translated():
        case_dir = composer.create_case_from_draft(
            settings.cases_root,
            settings.data_dir,
            draft_id,
            edits,
        )
        handoff = track_a.build_case(case_dir, ctx)
    return handoff.to_view()
