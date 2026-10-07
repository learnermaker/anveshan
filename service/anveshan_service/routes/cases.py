"""Case routes -> Track A public API (docs/plans/service-api.md §2, §5)."""

from __future__ import annotations

import hmac
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, Depends, File, Header, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from anveshan_service import adapters
from anveshan_service import access as access_module
from anveshan_service.deps import get_mode, get_settings
from anveshan_service.errors import ServiceError, invalid
from anveshan_service.paths import base_case_id, case_dir, store_upload
from anveshan_service.settings import Settings
from anveshan_service.steward import current_steward
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
        # Add access info to each case
        result = []
        for c in cases:
            cid = str(c.get("case_id", ""))
            cdir_path = (settings.data_dir / "cases" / cid) if "~" in cid else (settings.cases_root / cid)
            rv = c.get("review_status", "pending")
            c = dict(c)
            c["access"] = access_module.access_view(settings, cid, cdir_path, rv)
            result.append(c)
        return result
    upload_root = settings.data_dir / "cases"
    result = []
    for c in cases:
        cid = str(c.get("case_id", ""))
        if "~" in cid:
            cdir_path = upload_root / cid
            if not access_module.can_view(settings, cid, cdir_path):
                continue
        else:
            cdir_path = settings.cases_root / cid
        # Drop unlisted curated cases from non-steward views
        if "~" not in cid:
            from anveshan_service.library import kind_of, load
            k = kind_of(settings, cid)
            if k == "curated" and not current_steward.get():
                rec = load(settings, cid, cdir_path)
                if rec.status == "unlisted":
                    continue
        rv = c.get("review_status", "pending")
        c = dict(c)
        c["access"] = access_module.access_view(settings, cid, cdir_path, rv)
        result.append(c)
    return result


@router.get("/{case_id}")
def get_case(case_id: str, settings: Settings = Depends(get_settings)) -> Any:
    cdir = case_dir(settings, case_id)
    api = adapters.track_a()
    with adapters.translated():
        view = api.load_case(cdir).to_view()
    if isinstance(view, dict):
        rv = view.get("review_status", "pending")
        view["access"] = access_module.access_view(settings, case_id, cdir, rv)
    return view


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

    if curated:
        # Curated case: token/open check, and also allow steward request
        if not settings.curated_review_open and not current_steward.get():
            if not settings.review_token or not hmac.compare_digest(x_review_token or "", settings.review_token):
                raise ServiceError(
                    403,
                    "REVIEW_DISABLED",
                    "Expert review of the curated cases is by invitation in this public demo. "
                    "You can review skills you composed yourself.",
                )
    else:
        # Community or derived: only owner or steward
        if not access_module.is_owner(cdir) and not current_steward.get():
            raise ServiceError(
                403,
                "NOT_OWNER",
                "Only the creator or a steward can change these steps.",
            )

    api = adapters.track_a()
    with adapters.resource_lock("case", case_id), adapters.translated():
        return api.apply_review(cdir, action).to_view()
