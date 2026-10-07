"""Case routes -> Track A public API (docs/plans/service-api.md §2, §5)."""

from __future__ import annotations

import hmac
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, File, Header, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from anveshan_service import adapters
from anveshan_service.deps import get_mode, get_settings
from anveshan_service.errors import ServiceError, invalid
from anveshan_service.paths import base_case_id, case_dir, store_upload
from anveshan_service.settings import Settings
from anveshan_service.visitors import add_owner, visible

router = APIRouter(prefix="/api/cases")


class BuildBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: Optional[str] = Field(default=None, max_length=200)


class QueryBody(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


REVIEW_ACTIONS = {"approve", "revise_claim", "reject_claim", "reject_package"}


@router.get("")
def list_cases(settings: Settings = Depends(get_settings)) -> Any:
    api = adapters.track_a()
    with adapters.translated():
        cases = api.list_cases(settings.cases_root, settings.data_dir)
    if not settings.isolate_visitors:
        return cases
    upload_root = settings.data_dir / "cases"
    return [c for c in cases if "~" not in str(c.get("case_id", "")) or visible(upload_root / str(c["case_id"]))]


@router.get("/{case_id}")
def get_case(case_id: str, settings: Settings = Depends(get_settings)) -> Any:
    cdir = case_dir(settings, case_id)
    api = adapters.track_a()
    with adapters.translated():
        return api.load_case(cdir).to_view()


@router.post("/{case_id}/sources")
def upload_source(case_id: str, file: UploadFile = File(...), settings: Settings = Depends(get_settings)) -> Dict[str, str]:
    base = base_case_id(case_id)
    case_dir(settings, base)  # the base case must exist under cases_root
    api = adapters.track_a()
    stored = store_upload(file, settings, "file")
    with adapters.resource_lock("case", base), adapters.translated():
        derived = api.create_upload_case(settings.cases_root, settings.data_dir, base, stored.path, stored.mime_type)
    add_owner(derived)
    return {"case_id": derived.name}


@router.post("/{case_id}/build")
def build_case(
    case_id: str,
    body: Optional[BuildBody] = Body(None),
    settings: Settings = Depends(get_settings),
    mode: str = Depends(get_mode),
) -> Any:
    cdir = case_dir(settings, case_id)
    api = adapters.track_a()
    ctx = adapters.run_context(settings, cdir, mode)
    with adapters.resource_lock("case", case_id), adapters.translated():
        return api.build_case(cdir, ctx, source_id=body.source_id if body else None).to_view()


@router.post("/{case_id}/query")
def query_case(
    case_id: str,
    body: QueryBody,
    settings: Settings = Depends(get_settings),
    mode: str = Depends(get_mode),
) -> Any:
    question = body.question.strip()
    if not question:
        raise invalid("question must not be blank")
    cdir = case_dir(settings, case_id)
    api = adapters.track_a()
    ctx = adapters.run_context(settings, cdir, mode)
    with adapters.translated():
        return api.answer_query(cdir, question, ctx)


@router.post("/{case_id}/review")
def review_case(
    case_id: str,
    action: Dict[str, Any] = Body(...),
    settings: Settings = Depends(get_settings),
    x_review_token: Optional[str] = Header(default=None),
) -> Any:
    if action.get("action") not in REVIEW_ACTIONS:
        raise invalid(f"review action must be one of {sorted(REVIEW_ACTIONS)}")
    cdir = case_dir(settings, case_id)
    curated = "~" not in case_id
    if curated and not settings.curated_review_open:
        if not settings.review_token or not hmac.compare_digest(x_review_token or "", settings.review_token):
            raise ServiceError(
                403,
                "REVIEW_DISABLED",
                "Expert review of the curated cases is by invitation in this public demo. "
                "You can review skills you composed yourself.",
            )
    api = adapters.track_a()
    with adapters.resource_lock("case", case_id), adapters.translated():
        return api.apply_review(cdir, action).to_view()
