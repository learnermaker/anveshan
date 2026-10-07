"""Steward identity: middleware, context var and FastAPI dependency.

A steward request is one whose ``X-Steward-Token`` header matches ``settings.steward_token``
(checked with ``hmac.compare_digest`` to resist timing attacks), or any request when
``settings.steward_open`` is true (local development only, never in production).
"""

from __future__ import annotations

import contextvars
import hmac
from typing import Optional

from fastapi import Depends

from anveshan_service.errors import ServiceError
from anveshan_service.settings import Settings
from anveshan_service.deps import get_settings

_STEWARD_HEADER = b"x-steward-token"

current_steward: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "anveshan_steward", default=False
)


def token_matches(settings: Settings, token: Optional[str]) -> bool:
    """Return True when the request should be treated as a steward request."""
    if settings.steward_open:
        return True
    if not settings.steward_token or not token:
        return False
    return hmac.compare_digest(token, settings.steward_token)


class StewardMiddleware:
    """Pure ASGI middleware: read ``X-Steward-Token`` and set ``current_steward`` for the request."""

    def __init__(self, app, settings: Settings) -> None:
        self.app = app
        self.settings = settings

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        header_value: Optional[str] = None
        for name, value in scope.get("headers", []):
            if name == _STEWARD_HEADER:
                # Never log or echo this value
                header_value = value.decode("latin-1")
                break
        is_steward = token_matches(self.settings, header_value)
        tok = current_steward.set(is_steward)
        try:
            await self.app(scope, receive, send)
        finally:
            current_steward.reset(tok)


def require_steward(settings: Settings = Depends(get_settings)) -> None:
    """FastAPI dependency: raise appropriate errors when a steward operation is not permitted."""
    if not settings.steward_enabled:
        raise ServiceError(
            403,
            "STEWARD_DISABLED",
            "The steward console isn't enabled on this server.",
        )
    if not current_steward.get():
        raise ServiceError(
            401,
            "STEWARD_REQUIRED",
            "Enter the steward access code to use the steward console.",
        )
