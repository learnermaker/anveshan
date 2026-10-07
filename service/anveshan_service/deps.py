"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import Query, Request

from anveshan_service.settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_mode(request: Request, mode: Optional[Literal["live", "recorded"]] = Query(None)) -> str:
    """``?mode=live|recorded`` override (when allowed); the default is ANVESHAN_MODE."""
    settings = get_settings(request)
    if mode and settings.allow_mode_override:
        return mode
    return settings.mode
