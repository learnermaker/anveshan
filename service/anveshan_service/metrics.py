"""Process-wide usage metrics for the steward usage view.

Groups:
- ``requests`` (key = route class): counted in RateLimitMiddleware or RouteCountMiddleware
- ``rate_limited`` (key = route class): counted when a 429 is returned
- ``errors`` (key = category): counted in errors.error_response
- ``attempts_day`` (key = UTC date): counted in submit_attempt success
- ``compose_day`` (key = UTC date): counted in analyze_upload success
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Dict


class Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, int]] = {}
        started = datetime.now(timezone.utc).isoformat()
        self.started_at = started

    def inc(self, group: str, key: str, n: int = 1) -> None:
        with self._lock:
            if group not in self._data:
                self._data[group] = {}
            self._data[group][key] = self._data[group].get(key, 0) + n

    def get(self, group: str) -> Dict[str, int]:
        with self._lock:
            return dict(self._data.get(group, {}))

    def uptime_s(self) -> float:
        started = datetime.fromisoformat(self.started_at)
        now = datetime.now(timezone.utc)
        return (now - started).total_seconds()


METRICS = Metrics()


class RouteCountMiddleware:
    """Minimal ASGI middleware to count requests by route class when rate limiting is off."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            from anveshan_service.limits import route_class
            name = route_class(scope.get("method", ""), scope.get("path", ""))
            if name:
                METRICS.inc("requests", name)
        await self.app(scope, receive, send)
