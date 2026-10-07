"""Shared media helpers: probing, audio decoding, and video frame sampling.

PyAV bundles FFmpeg, so no system ffmpeg is needed on developer machines or
Cloud Run. These helpers are deterministic and model-free. They are a shared
utility module, not a contract.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import av
import numpy as np
from PIL import Image


@dataclass(frozen=True)
class MediaInfo:
    path: str
    duration_sec: Optional[float]
    has_audio: bool
    has_video: bool
    width: Optional[int]
    height: Optional[int]
    fps: Optional[float]


@dataclass(frozen=True)
class Frame:
    time_sec: float
    image: Image.Image  # RGB


def sha256_file(path: Path | str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(path: Path | str) -> MediaInfo:
    with av.open(str(path)) as c:
        v = c.streams.video[0] if c.streams.video else None
        duration = float(c.duration / av.time_base) if c.duration else None
        return MediaInfo(
            path=str(path),
            duration_sec=duration,
            has_audio=bool(c.streams.audio),
            has_video=v is not None,
            width=v.width if v is not None else None,
            height=v.height if v is not None else None,
            fps=float(v.average_rate) if v is not None and v.average_rate else None,
        )


def decode_audio(
    path: Path | str,
    sample_rate: int = 16000,
    start_sec: float = 0.0,
    end_sec: Optional[float] = None,
) -> np.ndarray:
    """Decode the first audio stream to mono float32 at ``sample_rate``.

    Corrupt packets are skipped (common in some Ogg files). Raises ValueError
    if the container has no audio stream or decodes to silence-length zero.
    """
    with av.open(str(path)) as c:
        if not c.streams.audio:
            raise ValueError(f"no audio stream in {path}")
        stream = c.streams.audio[0]
        resampler = av.AudioResampler(format="flt", layout="mono", rate=sample_rate)
        chunks: List[np.ndarray] = []
        for packet in c.demux(stream):
            try:
                for frame in packet.decode():
                    for out in resampler.resample(frame):
                        chunks.append(out.to_ndarray().ravel())
            except av.error.FFmpegError:
                continue
        for out in resampler.resample(None):
            chunks.append(out.to_ndarray().ravel())
    if not chunks:
        raise ValueError(f"audio stream in {path} decoded to nothing")
    x = np.concatenate(chunks).astype(np.float32)
    a = int(round(start_sec * sample_rate))
    b = None if end_sec is None else int(round(end_sec * sample_rate))
    return x[a:b]


def sample_frames(
    path: Path | str,
    fps: float = 1.0,
    start_sec: float = 0.0,
    end_sec: Optional[float] = None,
    max_side: int = 384,
    max_frames: Optional[int] = None,
) -> List[Frame]:
    """Sample RGB frames at ``fps`` within [start_sec, end_sec].

    Frames are chosen as the first decoded frame at or after each sampling
    instant, so output is deterministic for a given file.
    """
    if fps <= 0:
        raise ValueError("fps must be > 0")
    frames: List[Frame] = []
    step = 1.0 / fps
    next_t = start_sec
    with av.open(str(path)) as c:
        if not c.streams.video:
            raise ValueError(f"no video stream in {path}")
        stream = c.streams.video[0]
        for packet in c.demux(stream):
            try:
                decoded = packet.decode()
            except av.error.FFmpegError:
                continue
            for frame in decoded:
                if frame.pts is None:
                    continue
                t = float(frame.pts * stream.time_base)
                if end_sec is not None and t > end_sec:
                    return frames
                if t + 1e-6 < next_t:
                    continue
                img = frame.to_image().convert("RGB")
                img.thumbnail((max_side, max_side))
                frames.append(Frame(time_sec=round(t, 3), image=img))
                while next_t <= t + 1e-6:
                    next_t += step
                if max_frames is not None and len(frames) >= max_frames:
                    return frames
    return frames


def to_rgb(image: Image.Image) -> Image.Image:
    """RGB copy of any PIL image; transparency is composited on WHITE (not black), so
    screenshots and transparent PNG drawings look the same to models as on screen."""
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        return Image.alpha_composite(bg, rgba).convert("RGB")
    return image.convert("RGB")


def image_to_jpeg_bytes(image: Image.Image, quality: int = 85) -> bytes:
    import io

    buf = io.BytesIO()
    to_rgb(image).save(buf, format="JPEG", quality=quality)
    return buf.getvalue()
