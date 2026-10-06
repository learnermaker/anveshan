"""Anveshan HTTP service (FastAPI). See docs/plans/service-api.md §5.

Importing this package makes the repository root and the track ``src`` directories importable
(appended, so an explicit PYTHONPATH such as the container's always wins).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

for _p in (REPO_ROOT, REPO_ROOT / "tracks" / "track-a" / "src", REPO_ROOT / "tracks" / "track-b" / "src"):
    if _p.is_dir() and str(_p) not in sys.path:
        sys.path.append(str(_p))
