"""Shared runtime context passed to goal builders (Track A) and evaluators (Track B)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from tracks.common.models import Mode, ModelGateway, ModelRegistry, RunStore


@dataclass
class RunContext:
    mode: Mode            # "live" | "recorded"
    gateway: ModelGateway
    case_dir: Path        # tracks/cases/<case_id>
    data_dir: Path        # runtime data root (uploads, sessions, ad-hoc runs); gitignored

    @staticmethod
    def create(
        case_dir: Path,
        data_dir: Path,
        mode: Mode,
        registry: Optional[ModelRegistry] = None,
        api_key: Optional[str] = None,
        client: Any = None,
    ) -> "RunContext":
        """Live runs are written to <data_dir>/runs/<case_id>. Replay searches the case pack's
        committed golden runs first, then the ad-hoc runs."""
        if mode == "recorded":
            store = RunStore([case_dir / "runs" / "golden", data_dir / "runs" / case_dir.name])
        else:
            store = RunStore([data_dir / "runs" / case_dir.name, case_dir / "runs" / "golden"])
        gw = ModelGateway(mode=mode, store=store, registry=registry, api_key=api_key, client=client)
        return RunContext(mode=mode, gateway=gw, case_dir=case_dir, data_dir=data_dir)
