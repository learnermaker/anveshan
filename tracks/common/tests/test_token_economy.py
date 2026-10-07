"""Token economy in the model gateway (docs/architecture/token-economy.md)."""

import io
import json

import pytest
from PIL import Image
from pydantic import BaseModel

from tracks.common.models import (
    ImagePart,
    ModelGateway,
    ModelRegistry,
    RunStore,
    max_output_tokens,
    media_resolution_for,
    replay_key,
)


class _DTO(BaseModel):
    answer: str


def _png(side: int) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (side, side // 2), (120, 80, 40)).save(buf, format="PNG")
    return buf.getvalue()


class _Usage:
    prompt_token_count = 900
    candidates_token_count = 40
    thoughts_token_count = 0
    total_token_count = 940


class _RecordingModels:
    def __init__(self, reject_resolution=False):
        self.calls, self.reject_resolution = [], reject_resolution

    def generate_content(self, model, contents, config):
        self.calls.append((contents, config))
        has_res = any(getattr(getattr(c, "media_resolution", None), "level", None) for c in contents)
        if self.reject_resolution and has_res:
            raise RuntimeError("400 INVALID_ARGUMENT: media_resolution is not supported for this model")
        return type("R", (), {"text": '{"answer": "ok"}', "usage_metadata": _Usage()})()


class _Client:
    def __init__(self, models):
        self.models = models


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for k in ("ANVESHAN_MEDIA_RESOLUTION", "ANVESHAN_MAX_OUTPUT_TOKENS"):
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("ANVESHAN_LIVE_CACHE", "0")


def test_auto_resolution_follows_image_size():
    g3 = "gemini-3.5-flash-lite"
    assert media_resolution_for(ImagePart(_png(256), "image/png"), g3) == "MEDIA_RESOLUTION_LOW"
    assert media_resolution_for(ImagePart(_png(384), "image/png"), g3) == "MEDIA_RESOLUTION_LOW"
    assert media_resolution_for(ImagePart(_png(768), "image/png"), g3) == "MEDIA_RESOLUTION_MEDIUM"
    assert media_resolution_for(ImagePart(_png(1024), "image/png"), g3) == "MEDIA_RESOLUTION_HIGH"


def test_resolution_only_for_gemini3_and_overridable(monkeypatch):
    small = ImagePart(_png(256), "image/png")
    assert media_resolution_for(small, "gemma-4-26b") is None
    assert media_resolution_for(ImagePart(_png(256), "image/png", resolution="high"), "gemini-3-x") == "MEDIA_RESOLUTION_HIGH"
    monkeypatch.setenv("ANVESHAN_MEDIA_RESOLUTION", "default")
    assert media_resolution_for(small, "gemini-3-x") is None
    monkeypatch.setenv("ANVESHAN_MEDIA_RESOLUTION", "medium")
    assert media_resolution_for(small, "gemini-3-x") == "MEDIA_RESOLUTION_MEDIUM"
    assert media_resolution_for(ImagePart(b"not an image", "image/png"), "gemini-3-x") == "MEDIA_RESOLUTION_MEDIUM"
    monkeypatch.setenv("ANVESHAN_MEDIA_RESOLUTION", "auto")
    assert media_resolution_for(ImagePart(b"not an image", "image/png"), "gemini-3-x") is None


def test_max_output_tokens_env(monkeypatch):
    assert max_output_tokens() == 4096
    monkeypatch.setenv("ANVESHAN_MAX_OUTPUT_TOKENS", "0")
    assert max_output_tokens() == 0
    monkeypatch.setenv("ANVESHAN_MAX_OUTPUT_TOKENS", "junk")
    assert max_output_tokens() == 4096


def test_replay_key_ignores_resolution():
    a = ImagePart(_png(256), "image/png")
    b = ImagePart(a.data, "image/png", resolution="high")
    assert replay_key("vision_fast", "p", "v1", "", [a, "x"]) == replay_key("vision_fast", "p", "v1", "", [b, "x"])


def test_gateway_sends_resolution_cap_and_records_usage(tmp_path):
    fake = _RecordingModels()
    gw = ModelGateway("live", RunStore([tmp_path]), ModelRegistry({"vision_fast": "gemini-3.5-flash-lite"}), client=_Client(fake))
    r = gw.generate_json(model_key="vision_fast", prompt_id="p", prompt_version="v1", prompt_text="hi",
                         schema=_DTO, parts=[ImagePart(_png(256), "image/png"), ImagePart(_png(600), "image/png")])
    contents, config = fake.calls[0]
    levels = [str(c.media_resolution.level) for c in contents if getattr(c, "media_resolution", None)]
    assert len(levels) == 2 and "LOW" in levels[0] and "MEDIUM" in levels[1]
    assert config.max_output_tokens == 4096
    assert "media_resolution=low,medium" in r.metadata.notes
    raw = json.loads((tmp_path / r.metadata.replay_key / "raw_response.json").read_text(encoding="utf-8"))
    assert raw["usage"]["prompt_token_count"] == 900 and raw["usage"]["total_token_count"] == 940


def test_gateway_retries_without_resolution_when_rejected(tmp_path):
    fake = _RecordingModels(reject_resolution=True)
    gw = ModelGateway("live", RunStore([tmp_path]), ModelRegistry({"vision_fast": "gemini-3-test"}), client=_Client(fake))
    r = gw.generate_json(model_key="vision_fast", prompt_id="p", prompt_version="v1", prompt_text="hi",
                         schema=_DTO, parts=[ImagePart(_png(256), "image/png")])
    assert r.data.answer == "ok"
    assert "media_resolution_unsupported_retried_without" in r.metadata.notes
    assert len(fake.calls) == 2 and fake.calls[1][1].response_mime_type == "application/json"
