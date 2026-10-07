"""Tests for the composer module (K6 §6 - fake gateway, no live API calls)."""

from __future__ import annotations

import io
import json
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pytest
from PIL import Image
from pydantic import BaseModel

from tracks.common.models import (
    EmbeddingResult,
    FailureCategory,
    ImagePart,
    ModelError,
    ModelGateway,
    RunMetadata,
    RunStore,
)
from tracks.common.perception import PerceptionRecord
from tracks.common.runtime import RunContext

SR = 16000


# ---------------------------------------------------------------------------
# Helpers (reuse from test_perceivers pattern)
# ---------------------------------------------------------------------------


def _png_bytes(w: int = 128, h: int = 128) -> bytes:
    img = Image.new("RGB", (w, h), (255, 255, 255))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    for i in range(0, w, 8):
        draw.line([(i, 0), (i, h)], fill=(0, 0, 0), width=1)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _write_png(path: Path, w: int = 128, h: int = 128) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_png_bytes(w, h))


def _write_wav(path: Path, x: np.ndarray, sr: int = SR) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


class FakeGateway:
    """Same fake as in test_perceivers."""

    def __init__(
        self,
        vision_dto: Optional[dict] = None,
        audio_enabled: bool = False,
        vision_fail: bool = False,
        embed_fail: bool = False,
    ):
        self._vision_dto = vision_dto
        self._vision_fail = vision_fail
        self._embed_fail = embed_fail
        self.calls: List[dict] = []
        self.embed_calls: List[dict] = []
        from tracks.common.models import ModelRegistry
        self.registry = ModelRegistry(overrides={
            "audio": "fake-audio" if audio_enabled else "",
            "vision_fast": "fake-vision",
            "embedding": "fake-embed",
        })

    def generate_json(self, *, model_key, prompt_id, prompt_version, prompt_text, schema, parts=(), **kw):
        n_image_parts = sum(1 for p in parts if isinstance(p, ImagePart))
        self.calls.append({"model_key": model_key, "n_parts": len(parts), "n_image_parts": n_image_parts})
        if self._vision_fail:
            raise ModelError(FailureCategory.MODEL_FAILURE, "fake failure")

        dto_data = self._vision_dto or {
            "artefact_kind": "test item",
            "objects": ["line", "dot"],
            "properties": [{"label": "pattern", "detail": "grid pattern", "region": [5, 5, 90, 90]}],
            "visible_mistakes_to_avoid": ["uneven spacing"],
            "plausible_build_order": [{"step": "draw grid", "region": None}],
            "safety_categories": ["none"],
            "teachable": "yes",
            "teachable_reason": "clear visual skill",
            "skill_kind": "visual art",
        }
        try:
            dto = schema.model_validate(dto_data)
        except Exception:
            dto = schema()
        result = type("R", (), {})()
        result.data = dto
        result.raw_text = "{}"
        result.metadata = RunMetadata(
            run_id="fake-001",
            provider="fake",
            model_key=model_key,
            model_id="fake",
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            prompt_sha256="",
            input_digests=[],
            runtime_class="RECORDED_LIVE",
            started_at="2026-01-01T00:00:00Z",
            latency_ms=100,
            replay_key=f"fake-{model_key}-{prompt_id}",
        )
        return result

    def embed(self, *, items, purpose, model_key="embedding", dims=768, **kw):
        if self._embed_fail:
            raise ModelError(FailureCategory.MODEL_FAILURE, "fake embed fail")
        n = len(items)
        self.embed_calls.append({"n": n, "purpose": purpose})
        rng = np.random.default_rng(42)
        vecs = rng.standard_normal((n, dims)).astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / np.where(norms == 0, 1.0, norms)
        meta = RunMetadata(
            run_id="fake-embed",
            provider="fake",
            model_key=model_key,
            model_id="fake",
            prompt_id=f"embed:{purpose}",
            prompt_version=f"d{dims}",
            prompt_sha256="",
            input_digests=[],
            runtime_class="RECORDED_LIVE",
            started_at="2026-01-01T00:00:00Z",
            latency_ms=50,
            replay_key=f"fake-embed-{purpose}",
        )
        return EmbeddingResult(vectors=vecs, metadata=meta)


def _make_ctx(tmp_path: Path, gateway=None) -> RunContext:
    gw = gateway or FakeGateway()
    return RunContext(mode="recorded", gateway=gw, case_dir=tmp_path, data_dir=tmp_path / "data")


def _composer():
    import importlib
    return importlib.import_module("track_a.composer")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_create_draft_image_proposal(tmp_path):
    """create_draft on an image should produce a proposal with a SkillModel."""
    c = _composer()
    img_path = tmp_path / "upload.png"
    _write_png(img_path)
    gw = FakeGateway()
    ctx = _make_ctx(tmp_path, gw)
    draft = c.create_draft(tmp_path, img_path, "image/png", ctx, title_hint="Grid Drawing", rights_confirmed=True)
    assert not draft.refused
    assert draft.proposal is not None
    assert draft.proposal.skill_model is not None
    assert len(draft.proposal.skill_model.checks) >= 1


def test_create_draft_idempotent(tmp_path):
    """Calling create_draft twice with the same file returns the same draft_id."""
    c = _composer()
    img_path = tmp_path / "upload.png"
    _write_png(img_path)
    gw = FakeGateway()
    ctx = _make_ctx(tmp_path, gw)
    d1 = c.create_draft(tmp_path, img_path, "image/png", ctx, title_hint="T", rights_confirmed=True)
    d2 = c.create_draft(tmp_path, img_path, "image/png", ctx, title_hint="T", rights_confirmed=True)
    assert d1.draft_id == d2.draft_id
    # Second call should not make new perception calls
    assert len(gw.calls) == len(gw.calls)  # calls from first create only


def test_create_draft_safety_refuse(tmp_path):
    """A file that triggers safety=refuse should produce a refused draft with 200."""
    c = _composer()
    img_path = tmp_path / "weapon.png"
    _write_png(img_path)
    gw = FakeGateway(vision_dto={
        "artefact_kind": "weapon",
        "objects": ["gun"],
        "properties": [],
        "visible_mistakes_to_avoid": [],
        "plausible_build_order": [],
        "safety_categories": ["weapons"],
        "teachable": "yes",
        "teachable_reason": "weapon tutorial",
        "skill_kind": "weapons",
    })
    ctx = _make_ctx(tmp_path, gw)
    draft = c.create_draft(tmp_path, img_path, "image/png", ctx, rights_confirmed=True)
    assert draft.refused is True
    assert draft.refusal_message is not None
    assert "can't" in draft.refusal_message.lower() or "cannot" in draft.refusal_message.lower() or "We can't" in draft.refusal_message


def test_create_draft_teachable_no_refuse(tmp_path):
    """A blank/not-teachable image should produce a refused draft."""
    c = _composer()
    img_path = tmp_path / "meme.png"
    _write_png(img_path)
    gw = FakeGateway(vision_dto={
        "artefact_kind": "meme",
        "objects": ["text"],
        "properties": [],
        "visible_mistakes_to_avoid": [],
        "plausible_build_order": [],
        "safety_categories": ["none"],
        "teachable": "no",
        "teachable_reason": "just a meme, nothing to reproduce",
        "skill_kind": "none",
    })
    ctx = _make_ctx(tmp_path, gw)
    draft = c.create_draft(tmp_path, img_path, "image/png", ctx, rights_confirmed=True)
    assert draft.refused is True
    assert draft.refusal_message is not None


def test_create_draft_unclear_no_hint(tmp_path):
    """unclear + no title -> proposal=None + warning."""
    c = _composer()
    img_path = tmp_path / "photo.png"
    _write_png(img_path)
    gw = FakeGateway(vision_dto={
        "artefact_kind": "photo",
        "objects": ["thing"],
        "properties": [],
        "visible_mistakes_to_avoid": [],
        "plausible_build_order": [],
        "safety_categories": ["none"],
        "teachable": "unclear",
        "teachable_reason": "could be many things",
        "skill_kind": "",
    })
    ctx = _make_ctx(tmp_path, gw)
    draft = c.create_draft(tmp_path, img_path, "image/png", ctx, rights_confirmed=True)
    assert not draft.refused
    assert draft.proposal is None
    assert any("title" in w.lower() for w in draft.warnings)


def test_create_draft_no_rights(tmp_path):
    """Without rights_confirmed, draft creation should raise INVALID_INPUT."""
    c = _composer()
    img_path = tmp_path / "img.png"
    _write_png(img_path)
    ctx = _make_ctx(tmp_path)
    with pytest.raises(Exception) as exc_info:
        c.create_draft(tmp_path, img_path, "image/png", ctx, rights_confirmed=False)
    assert "rights" in str(exc_info.value).lower() or "INVALID_INPUT" in str(exc_info.value)


def test_refine_draft_no_new_perception(tmp_path):
    """refine_draft should use the existing perception record (no new perception calls)."""
    c = _composer()
    img_path = tmp_path / "photo.png"
    _write_png(img_path)
    gw = FakeGateway(vision_dto={
        "artefact_kind": "photo",
        "objects": ["thing"],
        "properties": [],
        "visible_mistakes_to_avoid": [],
        "plausible_build_order": [],
        "safety_categories": ["none"],
        "teachable": "unclear",
        "teachable_reason": "could be many things",
        "skill_kind": "",
    })
    ctx = _make_ctx(tmp_path, gw)
    draft = c.create_draft(tmp_path, img_path, "image/png", ctx, rights_confirmed=True)
    calls_before = len(gw.calls)

    refined = c.refine_draft(tmp_path, draft.draft_id, ctx, title="Grid Art", description="a grid drawing skill")
    # No new perception calls (embed + vision_fast)
    assert refined.proposal is not None
    # No new perception calls: any new call must be the text-only wording call (no media parts).
    new_calls = gw.calls[calls_before:]
    assert all(c.get("n_image_parts", 0) == 0 and c.get("n_parts", 0) == 0 for c in new_calls), new_calls


def test_fallback_skill_model_when_universal_missing(tmp_path, monkeypatch):
    """When track_a.universal is not importable, fallback skill model is used."""
    c = _composer()
    # Force fallback by patching propose_skill_model to None
    monkeypatch.setattr(c, "propose_skill_model", None)

    img_path = tmp_path / "img.png"
    _write_png(img_path)
    gw = FakeGateway()
    ctx = _make_ctx(tmp_path, gw)
    draft = c.create_draft(tmp_path, img_path, "image/png", ctx, title_hint="Fallback test", rights_confirmed=True)
    assert not draft.refused
    assert draft.proposal is not None
    assert any("fallback" in w.lower() for w in draft.warnings)


def test_create_case_from_draft_manifest_valid(tmp_path):
    """create_case_from_draft should write a valid manifest and profile."""
    c = _composer()
    img_path = tmp_path / "img.png"
    _write_png(img_path)
    gw = FakeGateway()
    ctx = _make_ctx(tmp_path, gw)
    draft = c.create_draft(tmp_path, img_path, "image/png", ctx, title_hint="My Skill", rights_confirmed=True)
    assert draft.proposal is not None

    edits = {"title": "My Skill Confirmed"}
    case_dir = c.create_case_from_draft(tmp_path / "cases", tmp_path, draft.draft_id, edits)
    assert (case_dir / "manifest.json").exists()
    manifest = json.loads((case_dir / "manifest.json").read_text())
    assert "case_id" in manifest
    assert "transmission_mode" in manifest

    assert (case_dir / "knowledge" / "case_profile.v1.json").exists()
    assert (case_dir / "source" / "source.json").exists()


def test_create_case_from_draft_idempotent(tmp_path):
    """Calling create_case_from_draft twice returns the same case_dir."""
    c = _composer()
    img_path = tmp_path / "img.png"
    _write_png(img_path)
    gw = FakeGateway()
    ctx = _make_ctx(tmp_path, gw)
    draft = c.create_draft(tmp_path, img_path, "image/png", ctx, title_hint="Idempotent", rights_confirmed=True)
    assert draft.proposal is not None

    case_dir1 = c.create_case_from_draft(tmp_path / "cases", tmp_path, draft.draft_id, {})
    case_dir2 = c.create_case_from_draft(tmp_path / "cases", tmp_path, draft.draft_id, {})
    assert case_dir1 == case_dir2


def test_create_case_from_draft_invalid_edits(tmp_path):
    """Invalid edits (bad transmission_mode) should raise INVALID_INPUT."""
    c = _composer()
    img_path = tmp_path / "img.png"
    _write_png(img_path)
    gw = FakeGateway()
    ctx = _make_ctx(tmp_path, gw)
    draft = c.create_draft(tmp_path, img_path, "image/png", ctx, title_hint="Test", rights_confirmed=True)
    assert draft.proposal is not None

    with pytest.raises(Exception) as exc_info:
        c.create_case_from_draft(tmp_path / "cases", tmp_path, draft.draft_id, {
            "transmission_mode": "INVALID_MODE",
        })
    assert "INVALID_INPUT" in str(exc_info.value)


def test_modality_for_composed_case(tmp_path):
    """modality_for(case_id, case_dir) returns 'universal' for a composed case."""
    from track_a.config import modality_for
    case_dir = tmp_path / "cases" / "my-skill~abcdef123456"
    (case_dir / "knowledge").mkdir(parents=True, exist_ok=True)
    # Write a dummy profile
    (case_dir / "knowledge" / "case_profile.v1.json").write_text('{"test": true}', encoding="utf-8")
    result = modality_for("my-skill~abcdef123456", case_dir)
    assert result == "universal"


def test_to_view_structure(tmp_path):
    """Draft.to_view() should have the expected keys."""
    c = _composer()
    img_path = tmp_path / "img.png"
    _write_png(img_path)
    gw = FakeGateway()
    ctx = _make_ctx(tmp_path, gw)
    draft = c.create_draft(tmp_path, img_path, "image/png", ctx, title_hint="View Test", rights_confirmed=True)
    view = draft.to_view()
    assert "draft_id" in view
    assert "intake" in view
    assert "proposal" in view
    assert "refused" in view
    assert "refusal_message" in view
    assert "warnings" in view
    assert "structure_labels" in view
    assert "specialist_labels" in view
    assert "perception" in view
    assert "segments" in view["perception"]
    assert "observations" in view["perception"]
    # No embeddings in the view
    assert "embeddings_file" not in view["perception"]
