"""Injectable clock and id factory (track-b-spec §8.3).

Logic modules never call ``datetime.now()`` or ``uuid4()`` directly; they receive a
``Clock`` and an ``IdFactory``. Tests use ``FixedClock`` + ``SequentialIdFactory`` so the
same inputs produce byte-identical bundles.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, Protocol


class Clock(Protocol):
    def now_iso(self) -> str: ...


class IdFactory(Protocol):
    def new(self, prefix: str) -> str: ...


class SystemClock:
    """UTC wall clock, second precision, ``Z`` suffix."""

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class FixedClock:
    """Always returns the same timestamp (deterministic tests and replays)."""

    def __init__(self, iso: str = "2026-10-06T00:00:00Z") -> None:
        self.iso = iso

    def now_iso(self) -> str:
        return self.iso


class RandomIdFactory:
    """Production ids: ``<prefix>-<12 hex>``. Safe for file names and dotted ids."""

    def new(self, prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12]}"


class SequentialIdFactory:
    """Deterministic ids: ``<prefix>-0001``, ``<prefix>-0002`` ... per prefix."""

    def __init__(self) -> None:
        self._counters: Dict[str, int] = {}

    def new(self, prefix: str) -> str:
        n = self._counters.get(prefix, 0) + 1
        self._counters[prefix] = n
        return f"{prefix}-{n:04d}"
