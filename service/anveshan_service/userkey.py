"""Bring-your-own Gemini API key, scoped to one request.

The browser may send ``X-Gemini-Api-Key``. The key lives only in a context variable for the
duration of that request: it is never written to disk, logged, echoed in responses or stored in
the run store (run records hold model ids and digests, never credentials). Error text is redacted
against it (``errors._redact``). Calls made with a user key run in live mode and do not count
against the shared daily budget; per-client rate limits still apply.
"""

from __future__ import annotations

import contextvars
import re
from typing import Optional

HEADER = b"x-gemini-api-key"
# Same shape as app/src/api/userKey.ts looksLikeKey: "AIza..." keys and the newer "AQ." keys
# (base64url with dots). Anything else is rejected outright.
_KEY_RE = re.compile(r"^[A-Za-z0-9_.+/=\-]{20,250}$")

current_key: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("anveshan_user_key", default=None)


def valid_shape(key: str) -> bool:
    return bool(_KEY_RE.fullmatch(key or ""))


class UserKeyMiddleware:
    """Read the optional user key header into ``current_key`` (malformed keys are ignored)."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        key = None
        for name, value in scope.get("headers", []):
            if name == HEADER:
                candidate = value.decode("latin-1").strip()
                key = candidate if valid_shape(candidate) else None
                break
        token = current_key.set(key)
        try:
            await self.app(scope, receive, send)
        finally:
            current_key.reset(token)
