"""Bound the runtime data directory (on Cloud Run ``/tmp`` is in-memory and counts against RAM).

Deletes uploads, drafts, upload/composed cases and sessions older than a TTL, then evicts the oldest
entries until the directory is under a size cap. Committed case packs (``cases_root``) are never
touched; only ``data_dir`` children are.
"""

from __future__ import annotations

import logging
import shutil
import threading
import time
from pathlib import Path
from typing import Iterable, List, Tuple

log = logging.getLogger("anveshan_service")

SWEPT = ("uploads", "drafts", "cases", "sessions", "attempts", "runs")
_lock = threading.Lock()


def _size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    total = 0
    for f in p.rglob("*"):
        try:
            if f.is_file():
                total += f.stat().st_size
        except OSError:
            pass
    return total


def _mtime(p: Path) -> float:
    """Newest mtime inside an entry (a draft touched recently is in use)."""
    newest = p.stat().st_mtime
    if p.is_dir():
        for f in p.rglob("*"):
            try:
                newest = max(newest, f.stat().st_mtime)
            except OSError:
                pass
    return newest


def _entries(data_dir: Path, subdirs: Iterable[str]) -> List[Tuple[float, int, Path]]:
    out = []
    for sub in subdirs:
        root = data_dir / sub
        if not root.is_dir():
            continue
        for child in root.iterdir():
            if child.name.startswith(".part-"):
                continue
            try:
                out.append((_mtime(child), _size(child), child))
            except OSError:
                pass
    return out


def _remove(p: Path) -> None:
    if p.is_dir():
        shutil.rmtree(p, ignore_errors=True)
    else:
        p.unlink(missing_ok=True)


def sweep(data_dir: Path, ttl_hours: float, cap_bytes: int, now: float | None = None) -> List[Path]:
    """Remove expired entries, then the oldest until under ``cap_bytes``. Returns removed paths."""
    data_dir = Path(data_dir)
    if not data_dir.is_dir():
        return []
    now = time.time() if now is None else now
    removed: List[Path] = []
    with _lock:
        entries = _entries(data_dir, SWEPT)
        keep = []
        for mtime, size, p in entries:
            if ttl_hours > 0 and now - mtime > ttl_hours * 3600:
                _remove(p)
                removed.append(p)
            else:
                keep.append((mtime, size, p))
        total = sum(s for _, s, _ in keep)
        for mtime, size, p in sorted(keep):
            if cap_bytes <= 0 or total <= cap_bytes:
                break
            _remove(p)
            removed.append(p)
            total -= size
    if removed:
        log.info("housekeeping removed %d entries from %s", len(removed), data_dir)
    return removed


class SweepEvery:
    """Run ``sweep`` at most once per ``interval_s`` (called after expensive requests)."""

    def __init__(self, data_dir: Path, ttl_hours: float, cap_bytes: int, interval_s: float = 300.0) -> None:
        self.args = (Path(data_dir), ttl_hours, cap_bytes)
        self.interval = interval_s
        self._last = 0.0

    def maybe(self) -> None:
        now = time.monotonic()
        if now - self._last < self.interval:
            return
        self._last = now
        try:
            sweep(*self.args)
        except Exception:  # housekeeping must never fail a request
            log.exception("housekeeping sweep failed")
