"""
Tests for KeyframeExtractor.

Uses a synthetic video created with PyAV (colour frames, known FPS) so that
no real origami footage is required.  All tests are offline — no API keys,
no network calls.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_synthetic_video(path: Path, fps: int = 24, n_frames: int = 50) -> None:
    """Write a minimal MP4 with `n_frames` solid-colour frames at `fps`."""
    av = pytest.importorskip("av")
    from PIL import Image as PILImage  # type: ignore[import-untyped]
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    container = av.open(str(path), mode="w", format="mp4")
    stream = container.add_stream("libx264", rate=fps)
    stream.width = 64
    stream.height = 64
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "30"}  # fast encode

    for i in range(n_frames):
        # cycle through hue so each frame is visually distinct
        hue = int((i / n_frames) * 180)
        img = PILImage.fromarray(
            np.full((64, 64, 3), [hue, 200, 200], dtype="uint8"), mode="RGB"
        )
        frame = av.VideoFrame.from_image(img)
        for packet in stream.encode(frame):
            container.mux(packet)

    for packet in stream.encode():  # flush
        container.mux(packet)

    container.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def synthetic_video(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A 50-frame 24-fps MP4 written once for the whole module."""
    p = tmp_path_factory.mktemp("video") / "test_input.mp4"
    _make_synthetic_video(p, fps=24, n_frames=50)
    return p


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestKeyframeExtractor:
    def test_run_produces_frames_dir(self, synthetic_video: Path, tmp_path: Path) -> None:
        """extract-frames must create output/frames/ directory."""
        from extractor import KeyframeExtractor

        ex = KeyframeExtractor(video_path=synthetic_video, output_dir=tmp_path, step=5)
        ex.run()
        assert (tmp_path / "frames").is_dir()

    def test_frame_files_have_correct_naming(self, synthetic_video: Path, tmp_path: Path) -> None:
        """Written frames must match FoldingAgent's FRAME_NAME_RE: NNNNNN.jpg"""
        import re
        from extractor import KeyframeExtractor

        FRAME_NAME_RE = re.compile(r"^(?P<index>\d+)\.(?:png|jpe?g)$", re.IGNORECASE)

        ex = KeyframeExtractor(video_path=synthetic_video, output_dir=tmp_path, step=5)
        ex.run()

        frames = sorted((tmp_path / "frames").iterdir())
        assert len(frames) > 0
        for f in frames:
            assert FRAME_NAME_RE.match(f.name), f"Bad filename: {f.name}"

    def test_step_controls_frame_count(self, synthetic_video: Path, tmp_path: Path) -> None:
        """With step=10 on a 50-frame video we expect ~5 frames (indices 0,10,20,30,40)."""
        from extractor import KeyframeExtractor

        ex = KeyframeExtractor(video_path=synthetic_video, output_dir=tmp_path, step=10)
        result = ex.run()

        assert result["frame_count"] == 5

    def test_max_frames_cap(self, synthetic_video: Path, tmp_path: Path) -> None:
        """max_frames=3 must stop after writing 3 frames."""
        from extractor import KeyframeExtractor

        ex = KeyframeExtractor(
            video_path=synthetic_video, output_dir=tmp_path, step=1, max_frames=3
        )
        result = ex.run()

        assert result["frame_count"] == 3
        assert len(list((tmp_path / "frames").iterdir())) == 3

    def test_video_meta_json_written(self, synthetic_video: Path, tmp_path: Path) -> None:
        """video_meta.json must exist and contain fps, duration_sec, width, height."""
        from extractor import KeyframeExtractor

        ex = KeyframeExtractor(video_path=synthetic_video, output_dir=tmp_path, step=10)
        ex.run()

        meta_path = tmp_path / "video_meta.json"
        assert meta_path.exists(), "video_meta.json not written"
        meta = json.loads(meta_path.read_text())

        assert "fps" in meta
        assert "duration_sec" in meta
        assert "width" in meta
        assert "height" in meta
        assert meta["fps"] > 0
        assert meta["duration_sec"] > 0

    def test_fps_is_accurate(self, synthetic_video: Path, tmp_path: Path) -> None:
        """Probed FPS must be within 1 fps of the encoded rate (24)."""
        from extractor import KeyframeExtractor

        ex = KeyframeExtractor(video_path=synthetic_video, output_dir=tmp_path, step=10)
        ex.run()

        meta = json.loads((tmp_path / "video_meta.json").read_text())
        assert abs(meta["fps"] - 24.0) <= 1.0, f"FPS probe inaccurate: {meta['fps']}"

    def test_keyframes_json_written(self, synthetic_video: Path, tmp_path: Path) -> None:
        """keyframes.json must be a valid FoldingAgent manifest."""
        from extractor import KeyframeExtractor

        ex = KeyframeExtractor(
            video_path=synthetic_video,
            output_dir=tmp_path,
            step=10,
            front_color="white",
            back_color="red",
        )
        ex.run()

        kf_path = tmp_path / "keyframes.json"
        assert kf_path.exists(), "keyframes.json not written"
        kf = json.loads(kf_path.read_text())

        # Required FoldingAgent fields
        assert "name" in kf
        assert "frames" in kf
        assert kf["frames"] == "frames"
        assert "front_color" in kf and kf["front_color"] == "white"
        assert "back_color" in kf and kf["back_color"] == "red"
        assert "keyframes" in kf
        assert isinstance(kf["keyframes"], list)
        assert len(kf["keyframes"]) > 0

    def test_keyframes_indices_match_written_files(
        self, synthetic_video: Path, tmp_path: Path
    ) -> None:
        """Every index in keyframes.json must have a matching NNNNNN.jpg file."""
        from extractor import KeyframeExtractor

        ex = KeyframeExtractor(video_path=synthetic_video, output_dir=tmp_path, step=10)
        ex.run()

        kf = json.loads((tmp_path / "keyframes.json").read_text())
        frames_dir = tmp_path / "frames"

        for idx in kf["keyframes"]:
            expected = frames_dir / f"{idx:06d}.jpg"
            assert expected.exists(), f"Frame {expected.name} missing"

    def test_annotations_have_timestamps(self, synthetic_video: Path, tmp_path: Path) -> None:
        """_annotations in keyframes.json must have timestamp_sec for each index."""
        from extractor import KeyframeExtractor

        ex = KeyframeExtractor(video_path=synthetic_video, output_dir=tmp_path, step=10)
        ex.run()

        kf = json.loads((tmp_path / "keyframes.json").read_text())
        meta = json.loads((tmp_path / "video_meta.json").read_text())
        fps = meta["fps"]

        annotations = kf.get("_annotations", [])
        assert len(annotations) == len(kf["keyframes"])

        for ann in annotations:
            assert "frame_index" in ann
            assert "timestamp_sec" in ann
            expected_ts = round(ann["frame_index"] / fps, 3)
            assert abs(ann["timestamp_sec"] - expected_ts) < 0.01

    def test_result_dict_keys(self, synthetic_video: Path, tmp_path: Path) -> None:
        """run() must return all documented keys."""
        from extractor import KeyframeExtractor

        ex = KeyframeExtractor(video_path=synthetic_video, output_dir=tmp_path, step=10)
        result = ex.run()

        required = {"fps", "duration_sec", "width", "height",
                    "total_frame_count", "frame_count", "keyframe_count", "output_dir"}
        assert required.issubset(result.keys())

    def test_missing_video_path_raises(self, tmp_path: Path) -> None:
        """KeyframeExtractor.run() must raise if the video file does not exist."""
        from extractor import KeyframeExtractor

        ex = KeyframeExtractor(
            video_path=tmp_path / "nonexistent.mp4",
            output_dir=tmp_path / "out",
        )
        with pytest.raises(Exception):
            ex.run()
