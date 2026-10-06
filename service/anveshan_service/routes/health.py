"""GET /api/health — liveness plus the configured model registry (never keys)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from tracks.common.models import ModelRegistry

from anveshan_service.deps import get_settings
from anveshan_service.settings import Settings

router = APIRouter()


@router.get("/api/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    registry = ModelRegistry()
    return {
        "ok": True,
        "mode": settings.mode,
        "models": {
            "text_image": registry.model_id("text_image"),
            "video_frames": registry.model_id("video_frames"),
            "audio_enabled": registry.enabled("audio"),
        },
    }
