"""Tests for shared foundation helpers: media, onsets, locators, model gateway, case data."""

import json
import wave
from pathlib import Path

import av
import numpy as np
import pytest
from pydantic import BaseModel

from tracks.common import locators
from tracks.common.casedata import (
    CriterionMap,
    GoalModel,
    latest_version,
    load_versioned,
    versioned_path,
    write_json,
)
from tracks.common.media import decode_audio, probe, sample_frames, sha256_file
from tracks.common.models import (
    FailureCategory,
    ModelError,
    ModelGateway,
    ModelRegistry,
    RunStore,
    extract_json,
)
from tracks.common.onsets import detect_onsets, two_means_threshold

SR = 16000


def click_track(times, sr=SR, dur=None, bass_at=()):
    dur = dur or (max(times) + 1.0)
    x = np.zeros(int(dur * sr), dtype=np.float32)
    rng = np.random.default_rng(0)
    for i, t in enumerate(times):
        a = int(t * sr)
        n = int(0.05 * sr)
        env = np.exp(-np.linspace(0, 8, n))
        burst = rng.standard_normal(n).astype(np.float32) * env * 0.5
        if i in bass_at:
            tt = np.arange(n) / sr
            burst = burst * 0.2 + 0.8 * np.sin(2 * np.pi * 90 * tt).astype(np.float32) * env
        x[a : a + n] += burst
    return x


def write_wav(path: Path, x: np.ndarray, sr=SR):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())


def test_onsets_click_track_and_bass_flag():
    times = [0.5 + i * 0.5 for i in range(8)]
    x = click_track(times, bass_at={0, 4})
    on = detect_onsets(x, SR)
    assert len(on) == 8
    assert np.allclose(on.times_sec, times, atol=0.03)
    thr = two_means_threshold(on.low_ratio)
    bass = [i for i, r in enumerate(on.low_ratio) if r > thr]
    assert bass == [0, 4]


def test_onsets_silence_is_empty():
    assert len(detect_onsets(np.zeros(SR, dtype=np.float32), SR)) == 0


def test_decode_audio_wav_roundtrip(tmp_path):
    x = click_track([0.25, 0.75], dur=1.0)
    p = tmp_path / "a.wav"
    write_wav(p, x)
    y = decode_audio(p, sample_rate=SR)
    assert abs(len(y) - len(x)) < 50
    info = probe(p)
    assert info.has_audio and not info.has_video
    assert len(sha256_file(p)) == 64


def test_sample_frames_deterministic(tmp_path):
    p = tmp_path / "v.mp4"
    with av.open(str(p), "w") as c:
        s = c.add_stream("mpeg4", rate=10)
        s.width, s.height, s.pix_fmt = 64, 48, "yuv420p"
        for i in range(30):
            img = np.full((48, 64, 3), i * 8, dtype=np.uint8)
            for pk in s.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
                c.mux(pk)
        for pk in s.encode():
            c.mux(pk)
    f1 = sample_frames(p, fps=2.0)
    f2 = sample_frames(p, fps=2.0)
    assert [f.time_sec for f in f1] == [f.time_sec for f in f2]
    assert 5 <= len(f1) <= 7
    assert f1[0].image.size[0] <= 384


def test_locators_roundtrip_and_validation():
    s = locators.with_region("src.kolam.target.v1", 10, 20, 30, 40)
    loc = locators.parse(s)
    assert loc.source == "src.kolam.target.v1" and locators.region(loc) == (10, 20, 30, 40)
    assert str(locators.parse(locators.with_index("t", "stroke", 2, 3))) == "t#stroke=2-3"
    with pytest.raises(ValueError):
        locators.parse("x#xywh=percent:90,0,20,10")
    with pytest.raises(ValueError):
        locators.parse("x#bogus=1")


def test_extract_json_variants():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": [1,2]} done') == {"a": [1, 2]}
    with pytest.raises(ValueError):
        extract_json("no json here")


class _DTO(BaseModel):
    answer: str


class _FakeModels:
    def __init__(self, text, fail_json_mode=False):
        self.text, self.fail_json_mode, self.calls = text, fail_json_mode, []

    def generate_content(self, model, contents, config):
        self.calls.append((model, getattr(config, "response_mime_type", None)))
        if self.fail_json_mode and getattr(config, "response_mime_type", None):
            raise RuntimeError("400 INVALID_ARGUMENT: response_mime_type not supported")
        return type("R", (), {"text": self.text})()


class _FakeClient:
    def __init__(self, models):
        self.models = models


def test_gateway_timeout_reads_env(tmp_path, monkeypatch):
    """ANVESHAN_MODEL_TIMEOUT_MS is picked up when no explicit timeout_ms is given."""
    monkeypatch.setenv("ANVESHAN_MODEL_TIMEOUT_MS", "60000")
    gw = ModelGateway("live", RunStore([tmp_path]))
    assert gw._timeout_ms == 60000


def test_gateway_timeout_default(tmp_path, monkeypatch):
    """Default timeout is 300 000 ms when env var is absent."""
    monkeypatch.delenv("ANVESHAN_MODEL_TIMEOUT_MS", raising=False)
    gw = ModelGateway("live", RunStore([tmp_path]))
    assert gw._timeout_ms == 300_000


def test_gateway_timeout_explicit_overrides_env(tmp_path, monkeypatch):
    """An explicit timeout_ms arg takes precedence over the env var."""
    monkeypatch.setenv("ANVESHAN_MODEL_TIMEOUT_MS", "60000")
    gw = ModelGateway("live", RunStore([tmp_path]), timeout_ms=9_000)
    assert gw._timeout_ms == 9_000


def test_gateway_504_retry_succeeds(tmp_path):
    """A 504 error on the first attempt triggers one retry and records the note."""

    class _FailOnceThenOk:
        def __init__(self):
            self.calls = 0

        def generate_content(self, model, contents, config):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("HTTP 504 gateway timeout deadline_exceeded")
            return type("R", (), {"text": '{"answer": "ok"}'})()

    fake = _FailOnceThenOk()
    gw = ModelGateway("live", RunStore([tmp_path]), ModelRegistry({"text_image": "gemma-test"}),
                      client=_FakeClient(fake))
    r = gw.generate_json(model_key="text_image", prompt_id="p", prompt_version="v1", prompt_text="hi", schema=_DTO)
    assert r.data.answer == "ok"
    assert fake.calls == 2  # first attempt failed (504), second succeeded
    assert any("retried_once_after" in n for n in r.metadata.notes)


def test_gateway_504_does_not_retry_twice(tmp_path):
    """Two consecutive 504s raise ModelError without a third attempt."""

    class _AlwaysFail504:
        def __init__(self):
            self.calls = 0

        def generate_content(self, model, contents, config):
            self.calls += 1
            raise RuntimeError("HTTP 504 gateway timeout unavailable")

    fake = _AlwaysFail504()
    gw = ModelGateway("live", RunStore([tmp_path]), ModelRegistry({"text_image": "gemma-test"}),
                      client=_FakeClient(fake))
    with pytest.raises(ModelError) as e:
        gw.generate_json(model_key="text_image", prompt_id="p", prompt_version="v1", prompt_text="hi", schema=_DTO)
    assert e.value.category in (FailureCategory.MODEL_FAILURE, FailureCategory.MODEL_TIMEOUT)
    # 2 api_attempts × up to 2 json_mode attempts = at most 4, but json_mode=False
    # won't be attempted if the exception doesn't look like a mime error, so exactly 2
    assert fake.calls == 2


def test_gateway_non_retryable_error_not_retried(tmp_path):
    """Non-retryable errors (e.g. quota exceeded) are NOT retried by the 504 path."""

    class _QuotaFail:
        def __init__(self):
            self.calls = 0

        def generate_content(self, model, contents, config):
            self.calls += 1
            raise RuntimeError("quota exceeded 429 resource_exhausted")

    fake = _QuotaFail()
    gw = ModelGateway("live", RunStore([tmp_path]), ModelRegistry({"text_image": "gemma-test"}),
                      client=_FakeClient(fake))
    with pytest.raises(ModelError):
        gw.generate_json(model_key="text_image", prompt_id="p", prompt_version="v1", prompt_text="hi", schema=_DTO)
    # json_mode retry may kick in, but 504 retry must NOT → calls stay at ≤ 2
    assert fake.calls <= 2


def test_gateway_live_records_then_replays(tmp_path):
    fake = _FakeModels('{"answer": "ok"}', fail_json_mode=True)
    store = RunStore([tmp_path])
    gw = ModelGateway("live", store, ModelRegistry({"text_image": "gemma-test"}), client=_FakeClient(fake))
    r = gw.generate_json(model_key="text_image", prompt_id="p", prompt_version="v1", prompt_text="hi", schema=_DTO)
    assert r.data.answer == "ok" and r.metadata.runtime_class == "LIVE"
    assert "json_mode_unsupported_retried_without" in r.metadata.notes
    assert [c[1] for c in fake.calls] == ["application/json", None]
    rec = ModelGateway("recorded", store)
    r2 = rec.generate_json(model_key="text_image", prompt_id="p", prompt_version="v1", prompt_text="hi", schema=_DTO)
    assert r2.data.answer == "ok" and r2.metadata.runtime_class == "RECORDED_LIVE"
    with pytest.raises(ModelError) as e:
        rec.generate_json(model_key="text_image", prompt_id="p", prompt_version="v1", prompt_text="other", schema=_DTO)
    assert e.value.category == FailureCategory.REPLAY_MISMATCH


def test_gateway_invalid_output_and_disabled_model(tmp_path):
    gw = ModelGateway("live", RunStore([tmp_path]), ModelRegistry({"text_image": "m"}), client=_FakeClient(_FakeModels("nope")))
    with pytest.raises(ModelError) as e:
        gw.generate_json(model_key="text_image", prompt_id="p", prompt_version="v1", prompt_text="x", schema=_DTO)
    assert e.value.category == FailureCategory.MODEL_FAILURE
    gw2 = ModelGateway("live", RunStore([tmp_path]), ModelRegistry({"audio": ""}), client=_FakeClient(_FakeModels("{}")))
    with pytest.raises(ModelError):
        gw2.generate_json(model_key="audio", prompt_id="p", prompt_version="v1", prompt_text="x", schema=_DTO)


def test_casedata_versioning(tmp_path):
    g = GoalModel(case_id="k", version=2, modality="kolam_image", source_ids=["s"], package_id="kp.k.2", payload={"a": 1})
    write_json(versioned_path(tmp_path, "goal_model", 1), g.model_copy(update={"version": 1}))
    write_json(versioned_path(tmp_path, "goal_model", 2), g)
    assert latest_version(tmp_path, "goal_model") == 2
    assert load_versioned(tmp_path, "goal_model", GoalModel).version == 2
    assert json.loads(versioned_path(tmp_path, "goal_model", 2).read_text())["payload"] == {"a": 1}


def test_criterion_map_requires_citation():
    with pytest.raises(ValueError):
        CriterionMap.model_validate(
            {"rubric_id": "r", "package_id": "p", "criteria": {"C": {"order_index": 0, "source_claim_ids": ["CLM-01"], "why_it_matters": "no cite", "drill_hint": "d"}}}
        )
