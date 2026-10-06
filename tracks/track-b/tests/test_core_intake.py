"""Intake limits: every rejection is INVALID_INPUT with a learner-readable message. SYNTHETIC media."""

import json
import wave

import av
import numpy as np
import pytest
from PIL import Image

from tracks.common.models import AnveshanFailure, FailureCategory

from track_b.intake import IntakeLimits, build_attempt_media, media_duration_sec, sniff


def _wav(path, seconds, sr=16000):
    t = np.arange(int(seconds * sr)) / sr
    pcm = (0.3 * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


def _video(path, frames=20, rate=10):
    with av.open(str(path), "w") as c:
        s = c.add_stream("mpeg4", rate=rate)
        s.width, s.height, s.pix_fmt = 64, 48, "yuv420p"
        for i in range(frames):
            img = np.full((48, 64, 3), i * 8, dtype=np.uint8)
            for pkt in s.encode(av.VideoFrame.from_ndarray(img, format="rgb24")):
                c.mux(pkt)
        for pkt in s.encode():
            c.mux(pkt)
    return path


def _trace(path, n_points=6, **extra):
    doc = {"canvas": {"width": 492, "height": 499}, "goal_case_id": "kolam", "goal_version": 1,
           "strokes": [{"points": [[i, i, i * 50] for i in range(n_points)]}], "duration_ms": 1234, **extra}
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def _build(path, kind, limits=None, **kw):
    return build_attempt_media(path, kind, case_id="kolam", session_id="sess-0001", attempt_number=2, limits=limits, **kw)


def _rejects(path, kind, fragment, limits=None, **kw):
    with pytest.raises(AnveshanFailure) as e:
        _build(path, kind, limits, **kw)
    assert e.value.category == FailureCategory.INVALID_INPUT
    assert fragment in e.value.message, e.value.message


def test_valid_trace(tmp_path):
    m = _build(_trace(tmp_path / "t.json"), "trace")
    assert m.source_id == "src.attempt.kolam.sess-0001.2"
    assert m.mime_type == "application/json" and len(m.sha256) == 64
    assert media_duration_sec(m) == 1.234


def test_trace_rejections(tmp_path):
    _rejects(_trace(tmp_path / "short.json", n_points=4), "trace", "at least 5")
    (tmp_path / "bad.json").write_text("{not json", encoding="utf-8")
    _rejects(tmp_path / "bad.json", "trace", "not a valid drawing")
    (tmp_path / "nocanvas.json").write_text(json.dumps({"strokes": []}), encoding="utf-8")
    _rejects(tmp_path / "nocanvas.json", "trace", "canvas size")
    big = _trace(tmp_path / "big.json", pad="x" * (2 * 1024 * 1024 + 10))
    _rejects(big, "trace", "limit is 2 MB")


def test_empty_and_oversize_files(tmp_path):
    (tmp_path / "empty.wav").write_bytes(b"")
    _rejects(tmp_path / "empty.wav", "audio", "empty")
    _rejects(tmp_path / "missing.wav", "audio", "not received")
    wav = _wav(tmp_path / "a.wav", 5)
    _rejects(wav, "audio", "upload limit", limits=IntakeLimits(max_upload_mb=0.01))


def test_image(tmp_path):
    Image.new("RGB", (20, 10), "white").save(tmp_path / "p.png")
    m = _build(tmp_path / "p.png", "image")
    assert m.mime_type == "image/png"
    _rejects(_wav(tmp_path / "a.wav", 4), "image", "PNG, JPEG")
    damaged = tmp_path / "d.png"
    damaged.write_bytes((tmp_path / "p.png").read_bytes()[:30])
    _rejects(damaged, "image", "damaged")


def test_audio_limits(tmp_path):
    m = _build(_wav(tmp_path / "ok.wav", 4), "audio")
    assert m.mime_type == "audio/wav" and media_duration_sec(m) == pytest.approx(4.0, abs=0.01)
    _rejects(_wav(tmp_path / "short.wav", 1.5), "audio", "at least 3 s")
    _rejects(_wav(tmp_path / "long.wav", 5), "audio", "under 4 s", limits=IntakeLimits(max_audio_sec=4))
    _rejects(_trace(tmp_path / "t.json"), "audio", "WAV, MP3")


def test_video_limits(tmp_path):
    v = _video(tmp_path / "v.mp4")
    m = _build(v, "video")
    assert m.mime_type == "video/mp4" and media_duration_sec(m) == pytest.approx(2.0, abs=0.2)
    _rejects(v, "video", "under 1 s", limits=IntakeLimits(max_video_sec=1))
    _rejects(_wav(tmp_path / "a.wav", 4), "video", "MP4")


def test_extra_files(tmp_path):
    Image.new("RGB", (8, 8)).save(tmp_path / "r.png")
    m = _build(_trace(tmp_path / "t.json"), "trace", extra={"raster": tmp_path / "r.png"})
    assert m.extra == {"raster": tmp_path / "r.png"}
    _rejects(_trace(tmp_path / "t2.json"), "trace", "Unexpected extra", extra={"other": tmp_path / "r.png"})


def test_unknown_kind(tmp_path):
    _rejects(_trace(tmp_path / "t.json"), "smell", "Unknown attempt kind")


def test_sniff_families():
    assert sniff(b"\x1a\x45\xdf\xa3....webm") == "webm"
    assert sniff(b"\x00\x00\x00\x18ftypisom") == "mp4"
    assert sniff(b"OggS\x00") == "ogg"
    assert sniff(b"ID3\x03") == "mp3"
    assert sniff(b"  {\"a\":1}") == "json"
    assert sniff(b"hello") is None
