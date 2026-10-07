"""Per-client rate limits for the expensive (model-calling) routes of a public demo.

A token bucket per (client, route class), in memory: the service runs as one instance, so no shared
store is needed. Over the limit the client gets HTTP 429 ``RATE_LIMITED`` with ``retry_after_s``.
"""

from __future__ import annotations

import re
import threading
import time
from typing import Dict, Optional, Tuple

from anveshan_service.errors import error_response

# (method, path regex) -> route class
_ROUTES = (
    ("POST", re.compile(r"^/api/compose/analyze$"), "compose"),
    ("POST", re.compile(r"^/api/compose/[^/]+/(refine|create)$"), "compose_step"),
    ("POST", re.compile(r"^/api/cases/[^/]+/build$"), "compose"),
    ("POST", re.compile(r"^/api/cases/[^/]+/sources$"), "compose"),
    ("POST", re.compile(r"^/api/sessions/[^/]+/attempts(/sample/[^/]+)?$"), "attempt"),
    ("POST", re.compile(r"^/api/cases/[^/]+/query$"), "query"),
)

_MESSAGES = {
    "compose": "You have analysed a lot of uploads in the last hour. Please wait a little, or try a sample.",
    "compose_step": "Too many skill edits in the last hour. Please wait a little.",
    "attempt": "You have submitted a lot of attempts in the last hour. Please wait a little, or try a sample.",
    "query": "Too many questions in the last hour. Please wait a little.",
}


def route_class(method: str, path: str) -> Optional[str]:
    for m, rx, name in _ROUTES:
        if method == m and rx.match(path):
            return name
    return None


class TokenBucket:
    def __init__(self, per_hour: int, clock=time.monotonic) -> None:
        self.capacity = max(1, per_hour)
        self.rate = self.capacity / 3600.0
        self.clock = clock
        self._state: Dict[str, Tuple[float, float]] = {}
        self._lock = threading.Lock()

    def take(self, key: str) -> Tuple[bool, float]:
        """Consume one token; returns (allowed, seconds until the next token)."""
        now = self.clock()
        with self._lock:
            tokens, last = self._state.get(key, (float(self.capacity), now))
            tokens = min(self.capacity, tokens + (now - last) * self.rate)
            if tokens >= 1.0:
                self._state[key] = (tokens - 1.0, now)
                return True, 0.0
            self._state[key] = (tokens, now)
            return False, (1.0 - tokens) / self.rate


def client_key(scope) -> str:
    for name, value in scope.get("headers", []):
        if name == b"x-forwarded-for":
            return value.decode("latin-1").split(",")[0].strip() or "unknown"
    client = scope.get("client")
    return client[0] if client else "unknown"


class RateLimitMiddleware:
    def __init__(self, app, limits: Dict[str, int], clock=time.monotonic) -> None:
        self.app = app
        self.buckets = {name: TokenBucket(n, clock) for name, n in limits.items() if n > 0}

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            name = route_class(scope.get("method", ""), scope.get("path", ""))
            bucket = self.buckets.get(name) if name else None
            if bucket is not None:
                ok, wait = bucket.take(client_key(scope))
                if not ok:
                    resp = error_response(429, "RATE_LIMITED", _MESSAGES[name], {"retry_after_s": int(wait) + 1, "limit": name})
                    resp.headers["Retry-After"] = str(int(wait) + 1)
                    await resp(scope, receive, send)
                    return
        await self.app(scope, receive, send)
