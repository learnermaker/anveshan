"""Insights routes: GET /api/insights/{case_id} (owner or steward)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from anveshan_service import access as access_module
from anveshan_service import insights as insights_module
from anveshan_service.deps import get_settings
from anveshan_service.errors import ServiceError
from anveshan_service.paths import case_dir as _case_dir
from anveshan_service.settings import Settings
from anveshan_service.steward import current_steward

router = APIRouter()


@router.get("/api/insights/{case_id}")
def get_insights(case_id: str, settings: Settings = Depends(get_settings)) -> Any:
    cdir = _case_dir(settings, case_id)
    steward = current_steward.get()
    owner = access_module.is_owner(cdir)
    if not owner and not steward:
        raise ServiceError(
            403,
            "NOT_OWNER",
            "Only the creator or a steward can see how learners are doing.",
        )
    return insights_module.compute(settings, case_id)
