"""Library routes: GET/submit/withdraw for skills (prefix /api/library).

GET /api/library/{case_id}              owner or steward; others get 404
POST /api/library/{case_id}/submit      owner only
POST /api/library/{case_id}/withdraw    owner only
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from anveshan_service import adapters
from anveshan_service import access as access_module
from anveshan_service.deps import get_settings
from anveshan_service.errors import ServiceError, not_found
from anveshan_service.library import load, submit, withdraw
from anveshan_service.paths import case_dir as _case_dir
from anveshan_service.settings import Settings
from anveshan_service.steward import current_steward

router = APIRouter(prefix="/api/library")


class SubmitBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    credit_name: str = Field(min_length=1, max_length=60)
    licence: str
    consent_scope: str = "public_practice"
    rights_confirmed: bool
    people_visible: bool = False
    people_consented: bool = False
    note: Optional[str] = Field(default=None, max_length=500)


def _require_owner_or_steward(case_id: str, cdir, *, steward: bool) -> None:
    """Raise 404 for non-owners so private records do not leak."""
    if steward:
        return
    if not access_module.is_owner(cdir):
        raise not_found(f"unknown case {case_id}", case_id=case_id)


@router.get("/{case_id}")
def get_library(case_id: str, settings: Settings = Depends(get_settings)) -> Any:
    cdir = _case_dir(settings, case_id)
    steward = current_steward.get()
    _require_owner_or_steward(case_id, cdir, steward=steward)
    rec = load(settings, case_id, cdir)
    return rec.model_dump()


@router.post("/{case_id}/submit")
def submit_library(
    case_id: str,
    body: SubmitBody,
    settings: Settings = Depends(get_settings),
) -> Any:
    cdir = _case_dir(settings, case_id)
    # Owner only (not steward)
    if not access_module.is_owner(cdir):
        raise ServiceError(403, "NOT_OWNER", "Only the creator can publish this skill.")

    # Get the current review_status from Track A
    review_status = "pending"
    try:
        api = adapters.track_a()
        with adapters.translated():
            view = api.load_case(cdir).to_view()
        if isinstance(view, dict):
            review_status = view.get("review_status", "pending")
    except Exception:
        pass

    body_dict = {
        "credit_name": body.credit_name,
        "licence": body.licence,
        "consent_scope": body.consent_scope,
        "rights_confirmed": body.rights_confirmed,
        "people_visible": body.people_visible,
        "people_consented": body.people_consented,
        "note": body.note,
    }
    with adapters.resource_lock("case", case_id):
        rec = submit(settings, case_id, cdir, body_dict, review_status)
    return rec.model_dump()


@router.post("/{case_id}/withdraw")
def withdraw_library(
    case_id: str,
    settings: Settings = Depends(get_settings),
) -> Any:
    cdir = _case_dir(settings, case_id)
    if not access_module.is_owner(cdir):
        raise ServiceError(403, "NOT_OWNER", "Only the creator can withdraw this skill.")
    with adapters.resource_lock("case", case_id):
        rec = withdraw(settings, case_id, cdir)
    return rec.model_dump()
