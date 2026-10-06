"""Media routes: case sources the system uses, and goal assets. Never held-out material.

Starlette's FileResponse answers ``Range`` requests (206) itself, which audio/video seeking needs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from tracks.common.casedata import load_sources, resolve_media

from anveshan_service.deps import get_settings
from anveshan_service.errors import not_found
from anveshan_service.paths import case_dir, check_asset, content_type, within
from anveshan_service.settings import Settings

router = APIRouter(prefix="/api/media")

SERVABLE_ACCESS = {"public", "approved_learners"}


def _file(path, media_type: str) -> FileResponse:
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})


@router.get("/{case_id}/goal/{asset}")
def goal_asset(case_id: str, asset: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    cdir = case_dir(settings, case_id)
    check_asset(asset)
    root = cdir / "knowledge" / "goal_assets"
    path = root / asset
    if not within(path, root) or not path.is_file():
        raise not_found(f"unknown goal asset {asset}")
    return _file(path, content_type(path))


@router.get("/{case_id}/{source_id}")
def source_media(case_id: str, source_id: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    cdir = case_dir(settings, case_id)
    check_asset(source_id)
    missing = not_found(f"no servable media {source_id} in case {case_id}")
    try:
        record = load_sources(cdir).get(source_id)
    except (FileNotFoundError, KeyError):
        raise missing from None
    # Held-out validation material and research-only sources are never served (same 404 as unknown).
    if not record.used_by_system or record.role == "held_out_reference" or record.access_level not in SERVABLE_ACCESS:
        raise missing
    try:
        path = resolve_media(cdir, record)
    except FileNotFoundError:
        raise not_found(f"media for {source_id} is not cached on this server", source_id=source_id) from None
    if not (within(path, cdir) or within(path, settings.data_dir)) or not path.is_file():
        raise missing
    return _file(path, content_type(path, record.mime_type))
