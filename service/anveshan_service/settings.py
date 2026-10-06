"""Service settings from the environment (and an optional repo-root ``.env``)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from tracks.common.models import load_dotenv

from anveshan_service import REPO_ROOT

MODES = ("live", "recorded")


def _path(value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (REPO_ROOT / p)


@dataclass(frozen=True)
class Settings:
    mode: str = "recorded"
    cases_root: Path = REPO_ROOT / "tracks" / "cases"
    data_dir: Path = REPO_ROOT / "var"
    max_upload_mb: float = 50.0
    cors_origins: List[str] = field(default_factory=list)
    static_dir: Optional[Path] = REPO_ROOT / "app" / "dist"

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"ANVESHAN_MODE must be one of {MODES}, got {self.mode!r}")
        if self.max_upload_mb <= 0:
            raise ValueError("ANVESHAN_MAX_UPLOAD_MB must be > 0")

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @classmethod
    def from_env(cls, env_file: Optional[Path] = REPO_ROOT / ".env") -> "Settings":
        if env_file is not None:
            load_dotenv(env_file)
        env = os.environ
        origins = [o.strip() for o in env.get("ANVESHAN_CORS_ORIGINS", "").split(",") if o.strip()]
        static = env.get("ANVESHAN_STATIC_DIR", "app/dist")
        return cls(
            mode=env.get("ANVESHAN_MODE", "recorded").strip() or "recorded",
            cases_root=_path(env.get("ANVESHAN_CASES_ROOT", "tracks/cases")),
            data_dir=_path(env.get("ANVESHAN_DATA_DIR", "var")),
            max_upload_mb=float(env.get("ANVESHAN_MAX_UPLOAD_MB", "50") or 50),
            cors_origins=origins,
            static_dir=_path(static) if static else None,
        )
