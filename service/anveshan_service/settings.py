"""Service settings from the environment (and an optional repo-root ``.env``)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from tracks.common.models import load_dotenv

from anveshan_service import REPO_ROOT

MODES = ("live", "recorded")
CLOUD_RATE_LIMITS = {"compose": 6, "compose_step": 30, "attempt": 30, "query": 30, "auth": 10}


def _flag(env, name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _num(env, name: str, default: float) -> float:
    raw = env.get(name)
    try:
        return float(raw) if raw and raw.strip() else default
    except ValueError:
        return default


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
    # Public-demo protections (docs/plans/technical-panel-plan-2026-10-07.md WS1). Defaults suit local
    # development; ``from_env`` switches to the strict defaults on Cloud Run (K_SERVICE is set there).
    allow_mode_override: bool = True        # honour ?mode=live|recorded
    isolate_visitors: bool = True           # composed/upload cases and drafts are private to their visitor
    review_token: Optional[str] = None      # when set, reviewing a curated case needs X-Review-Token
    curated_review_open: bool = True        # False: curated case review needs the token (403 otherwise)
    rate_limits: Dict[str, int] = field(default_factory=dict)  # route class -> requests per hour (0/absent = off)
    data_ttl_hours: float = 0.0             # housekeeping TTL for data_dir entries (0 = off)
    data_cap_mb: float = 0.0                # housekeeping size cap for data_dir (0 = off)
    secure_cookies: bool = False
    steward_token: Optional[str] = None     # ANVESHAN_STEWARD_TOKEN (falls back to ANVESHAN_REVIEW_TOKEN)
    steward_open: bool = False              # no code needed (local development only)
    insights_max_events: int = 5000         # per-skill event log cap

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"ANVESHAN_MODE must be one of {MODES}, got {self.mode!r}")
        if self.max_upload_mb <= 0:
            raise ValueError("ANVESHAN_MAX_UPLOAD_MB must be > 0")

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def steward_enabled(self) -> bool:
        return self.steward_open or bool(self.steward_token)

    @classmethod
    def from_env(cls, env_file: Optional[Path] = REPO_ROOT / ".env") -> "Settings":
        if env_file is not None:
            load_dotenv(env_file)
        env = os.environ
        origins = [o.strip() for o in env.get("ANVESHAN_CORS_ORIGINS", "").split(",") if o.strip()]
        static = env.get("ANVESHAN_STATIC_DIR", "app/dist")
        cloud = bool(env.get("K_SERVICE"))
        limits = dict(CLOUD_RATE_LIMITS) if cloud else {}
        for name in CLOUD_RATE_LIMITS:
            limits[name] = int(_num(env, f"ANVESHAN_RATE_{name.upper()}_PER_HOUR", limits.get(name, 0)))
        token = (env.get("ANVESHAN_REVIEW_TOKEN") or "").strip() or None
        steward = (env.get("ANVESHAN_STEWARD_TOKEN") or "").strip() or token
        return cls(
            mode=env.get("ANVESHAN_MODE", "recorded").strip() or "recorded",
            cases_root=_path(env.get("ANVESHAN_CASES_ROOT", "tracks/cases")),
            data_dir=_path(env.get("ANVESHAN_DATA_DIR", "var")),
            max_upload_mb=float(env.get("ANVESHAN_MAX_UPLOAD_MB", "50") or 50),
            cors_origins=origins,
            static_dir=_path(static) if static else None,
            allow_mode_override=_flag(env, "ANVESHAN_ALLOW_MODE_OVERRIDE", not cloud),
            isolate_visitors=_flag(env, "ANVESHAN_ISOLATE_VISITORS", True),
            review_token=token,
            curated_review_open=_flag(env, "ANVESHAN_CURATED_REVIEW_OPEN", not cloud),
            rate_limits={k: v for k, v in limits.items() if v > 0},
            data_ttl_hours=_num(env, "ANVESHAN_DATA_TTL_H", 6.0 if cloud else 0.0),
            data_cap_mb=_num(env, "ANVESHAN_DATA_CAP_MB", 600.0 if cloud else 0.0),
            secure_cookies=cloud,
            steward_token=steward,
            steward_open=_flag(env, "ANVESHAN_STEWARD_OPEN", (not cloud) and steward is None),
            insights_max_events=int(_num(env, "ANVESHAN_INSIGHTS_MAX_EVENTS", 5000)),
        )
