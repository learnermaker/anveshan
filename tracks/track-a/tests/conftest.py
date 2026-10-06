"""Pytest fixtures for Track A core tests (helpers live in ta_helpers.py). No network."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Callable, Optional

import pytest

from tracks.common.casedata import SourceRecord, SourceRegistry, write_json
from tracks.common.media import sha256_file
from tracks.common.models import ModelRegistry
from tracks.common.runtime import RunContext

import track_a.goals as goals
from track_a.goals import GoalBuildResult

from ta_helpers import REAL_CASES, SRC_ID, FakeClient, FakeModels, kolam_claims, kolam_result, write_png


@pytest.fixture
def cases_root(tmp_path: Path) -> Path:
    """A temp cases root with a kolam hero case (image + held-out source), and the showcase cases copied."""
    root = tmp_path / "cases"
    kolam = root / "kolam"
    kolam.mkdir(parents=True)
    shutil.copyfile(REAL_CASES / "kolam" / "manifest.json", kolam / "manifest.json")
    write_png(kolam / "source" / "target.png")
    write_png(kolam / "source" / "held_out" / "diagram.png", size=(32, 32))
    reg = SourceRegistry(
        case_id="kolam",
        sources=[
            SourceRecord(
                source_id=SRC_ID,
                role="target_image",
                mime_type="image/png",
                sha256=sha256_file(kolam / "source" / "target.png"),
                bytes=(kolam / "source" / "target.png").stat().st_size,
                path="source/target.png",
                dimensions=[64, 48],
                creator="Test Creator",
                license="Public domain",
                attribution="test image, public domain",
                runtime_label="INTERNET_REFERENCE",
            ),
            SourceRecord(
                source_id="src.kolam.held_out.v1",
                role="held_out_reference",
                mime_type="image/png",
                sha256=sha256_file(kolam / "source" / "held_out" / "diagram.png"),
                bytes=(kolam / "source" / "held_out" / "diagram.png").stat().st_size,
                path="source/held_out/diagram.png",
                creator="Test Creator",
                license="Public domain",
                attribution="held out",
                runtime_label="INTERNET_REFERENCE",
                used_by_system=False,
            ),
        ],
    )
    write_json(kolam / "source" / "source.json", reg)
    for cid in ("micrometer", "bicycle-repair", "handloom-weaving", "square-knot", "origami", "tabla"):
        shutil.copytree(REAL_CASES / cid, root / cid, ignore=shutil.ignore_patterns("cache"))
    shutil.copyfile(REAL_CASES / "index.json", root / "index.json")
    return root


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    d = tmp_path / "var"
    d.mkdir()
    return d


@pytest.fixture
def fake_builder(monkeypatch):
    """Register a fake builder for every modality. Returns a list of recorded calls; set
    ``state['result']`` to change what the builder returns."""
    state = {"calls": [], "result": None}

    def build(source_path: Path, source: SourceRecord, ctx, *, case_id: str, version: int) -> GoalBuildResult:
        state["calls"].append({"path": source_path, "source_id": source.source_id, "case_id": case_id, "version": version})
        res = state["result"] or kolam_result(kolam_claims(source.source_id))
        return res

    monkeypatch.setattr(goals, "get_builder", lambda modality: build)
    return state


@pytest.fixture
def make_ctx(data_dir: Path) -> Callable[..., RunContext]:
    def _make(case_dir: Path, response: Optional[dict] = None, models: Optional[FakeModels] = None) -> RunContext:
        fm = models or FakeModels(json.dumps(response or {"answer": "ok", "cited_claim_ids": [], "sufficient": False}))
        return RunContext.create(
            case_dir, data_dir, "live", registry=ModelRegistry({"text_image": "gemma-test"}), client=FakeClient(fm)
        )

    return _make

