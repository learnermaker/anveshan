"""GET /api/health — liveness plus the configured model registry (never keys)."""

from __future__ import annotations

import os

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
        "mode_override": settings.allow_mode_override,
        "own_key_supported": True,
        "server_key_configured": bool(os.environ.get("GEMINI_API_KEY")),
        "curated_review_open": settings.curated_review_open or bool(settings.review_token),
        "steward_enabled": settings.steward_enabled,
        "steward_open": settings.steward_open,
        "data_ttl_hours": settings.data_ttl_hours,
        "models": {
            "text_image": registry.model_id("text_image"),
            "video_frames": registry.model_id("video_frames"),
            "vision_fast": registry.model_id("vision_fast"),
            "embedding": registry.model_id("embedding"),
            "audio_enabled": registry.enabled("audio"),
        },
    }
