"""Attempt intake: uploaded file + declared kind -> validated ``AttemptMedia`` (track-b-spec §3).

Checks (all failures are ``INVALID_INPUT`` with a learner-readable message):

* every file: exists, non-empty, <= ANVESHAN_MAX_UPLOAD_MB (default 50);
* trace: canvas JSON (service-api §4), <= 2 MB, >= 1 stroke with >= 5 points;
* image: PNG / JPEG / WebP / GIF that Pillow can open;
* audio: decodable audio stream, 3-120 s;
* video: decodable video stream, <= 120 s.

The MIME type is sniffed from the bytes, never trusted from the client.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, field_validator

from tracks.common.media import sha256_file
from tracks.common.models import AnveshanFailure, FailureCategory

from track_b.trajectory import AttemptMedia

KINDS = ("trace", "image", "audio", "video")


@dataclass(frozen=True)
class IntakeLimits:
    max_upload_mb: float = field(default_factory=lambda: float(os.environ.get("ANVESHAN_MAX_UPLOAD_MB", "50")))
    max_trace_bytes: int = 2 * 1024 * 1024
    min_trace_points: int = 5
    min_audio_sec: float = 3.0
    max_audio_sec: float = 120.0
    max_video_sec: float = 120.0


class TraceCanvas(BaseModel):
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class TraceStroke(BaseModel):
    points: List[List[float]]

    @field_validator("points")
    @classmethod
    def _xyt(cls, pts: List[List[float]]) -> List[List[float]]:
        for p in pts:
            if len(p) != 3:
                raise ValueError("each point must be [x, y, t_ms]")
        return pts


class TraceDoc(BaseModel):
    canvas: TraceCanvas
    strokes: List[TraceStroke]
    goal_case_id: Optional[str] = None
    goal_version: Optional[int] = None
    duration_ms: Optional[float] = None


def _invalid(message: str, **details) -> AnveshanFailure:
    return AnveshanFailure(FailureCategory.INVALID_INPUT, message, details)


def attempt_source_id(case_id: str, session_id: str, attempt_number: int) -> str:
    return f"src.attempt.{case_id}.{session_id}.{attempt_number}"


# ---------------------------------------------------------------------------
# Sniffing
# ---------------------------------------------------------------------------


def sniff(head: bytes) -> Optional[str]:
    """Container family from magic bytes: png|jpeg|webp|gif|wav|mp3|ogg|flac|matroska|webm|mp4|quicktime|json."""
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if head.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if head.startswith(b"ID3") or (len(head) > 1 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return "mp3"
    if head.startswith(b"OggS"):
        return "ogg"
    if head.startswith(b"fLaC"):
        return "flac"
    if head.startswith(b"\x1a\x45\xdf\xa3"):
        return "webm" if b"webm" in head[:64] else "matroska"
    if head[4:8] == b"ftyp":
        brand = head[8:12]
        if brand == b"qt  ":
            return "quicktime"
        if brand in (b"M4A ", b"M4B "):
            return "m4a"
        return "mp4"
    stripped = head.lstrip(b"\xef\xbb\xbf \t\r\n")
    if stripped.startswith(b"{"):
        return "json"
    return None


IMAGE_MIME = {"png": "image/png", "jpeg": "image/jpeg", "webp": "image/webp", "gif": "image/gif"}
AUDIO_MIME = {
    "wav": "audio/wav", "mp3": "audio/mpeg", "ogg": "audio/ogg", "flac": "audio/flac",
    "webm": "audio/webm", "matroska": "audio/x-matroska", "mp4": "audio/mp4", "m4a": "audio/mp4",
}
VIDEO_MIME = {
    "mp4": "video/mp4", "quicktime": "video/quicktime", "webm": "video/webm",
    "matroska": "video/x-matroska", "ogg": "video/ogg",
}


# ---------------------------------------------------------------------------
# Per-kind checks
# ---------------------------------------------------------------------------


def _check_trace(path: Path, limits: IntakeLimits) -> str:
    size = path.stat().st_size
    if size > limits.max_trace_bytes:
        raise _invalid(f"The drawing file is {size / 1e6:.1f} MB; the limit is {limits.max_trace_bytes / 1e6:.0f} MB.")
    try:
        doc = TraceDoc.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _invalid("The drawing could not be read: it is not a valid drawing (JSON) file.")
    except ValidationError as e:
        raise _invalid("The drawing file is missing the canvas size or stroke points.", errors=str(e))
    longest = max((len(s.points) for s in doc.strokes), default=0)
    if longest < limits.min_trace_points:
        raise _invalid(
            f"The drawing is empty or too short: draw at least one stroke "
            f"(the longest stroke has {longest} points; at least {limits.min_trace_points} are needed)."
        )
    return "application/json"


def _check_image(path: Path, family: Optional[str]) -> str:
    if family not in IMAGE_MIME:
        raise _invalid("Please upload a photo as a PNG, JPEG, WebP or GIF image.")
    try:
        from PIL import Image

        with Image.open(path) as im:
            im.verify()
    except Exception:
        raise _invalid("The image file is damaged or could not be opened; please upload it again.")
    return IMAGE_MIME[family]


def _media_duration(path: Path, want: str) -> Optional[float]:
    """Duration (s) of the first ``want`` ('audio'|'video') stream. Raises INVALID_INPUT if absent."""
    import av

    try:
        with av.open(str(path)) as c:
            streams = c.streams.audio if want == "audio" else c.streams.video
            if not streams:
                raise _invalid(f"This file has no {want} track; please upload a {want} recording.")
            s = streams[0]
            if s.duration is not None and s.time_base is not None:
                return float(s.duration * s.time_base)
            if c.duration:
                return float(c.duration / av.time_base)
            # Browser recordings (e.g. WebM from MediaRecorder) often omit the duration:
            # scan packet timestamps without decoding.
            end = None
            for pkt in c.demux(s):
                if pkt.pts is not None and pkt.time_base is not None:
                    t = float((pkt.pts + (pkt.duration or 0)) * pkt.time_base)
                    end = t if end is None else max(end, t)
            return end
    except AnveshanFailure:
        raise
    except Exception:
        raise _invalid(f"The file could not be read as {want}; please upload a common {want} format.")


def _check_audio(path: Path, family: Optional[str], limits: IntakeLimits) -> str:
    if family not in AUDIO_MIME:
        raise _invalid("Please upload the recording as WAV, MP3, OGG, FLAC, WebM or M4A audio.")
    dur = _media_duration(path, "audio")
    if dur is None:
        raise _invalid("The recording length could not be determined; please upload it as WAV.")
    if dur < limits.min_audio_sec:
        raise _invalid(f"The recording is {dur:.1f} s; please record at least {limits.min_audio_sec:g} s.")
    if dur > limits.max_audio_sec:
        raise _invalid(f"The recording is {dur:.0f} s; please keep it under {limits.max_audio_sec:g} s.")
    return AUDIO_MIME[family]


def _check_video(path: Path, family: Optional[str], limits: IntakeLimits) -> str:
    if family not in VIDEO_MIME:
        raise _invalid("Please upload the video as MP4, MOV, WebM or OGV.")
    dur = _media_duration(path, "video")
    if dur is None:
        raise _invalid("The video length could not be determined; please upload it as MP4.")
    if dur > limits.max_video_sec:
        raise _invalid(f"The video is {dur:.0f} s; please keep it under {limits.max_video_sec:g} s.")
    return VIDEO_MIME[family]


def _check_common(path: Path, limits: IntakeLimits) -> bytes:
    if not path.exists() or not path.is_file():
        raise _invalid("The uploaded file was not received; please upload it again.")
    size = path.stat().st_size
    if size == 0:
        raise _invalid("The uploaded file is empty; please upload it again.")
    if size > limits.max_upload_mb * 1024 * 1024:
        raise _invalid(f"The file is {size / 1e6:.1f} MB; the upload limit is {limits.max_upload_mb:g} MB.")
    with open(path, "rb") as fh:
        return fh.read(64)


def check_file(path: Path, kind: str, limits: Optional[IntakeLimits] = None) -> str:
    """Validate one file for ``kind``; return the sniffed MIME type."""
    limits = limits or IntakeLimits()
    if kind not in KINDS:
        raise _invalid(f"Unknown attempt kind {kind!r}; expected one of {', '.join(KINDS)}.")
    head = _check_common(path, limits)
    family = sniff(head)
    if kind == "trace":
        return _check_trace(path, limits)
    if kind == "image":
        return _check_image(path, family)
    if kind == "audio":
        return _check_audio(path, family, limits)
    return _check_video(path, family, limits)


def build_attempt_media(
    path: Path,
    kind: str,
    *,
    case_id: str,
    session_id: str,
    attempt_number: int,
    extra: Optional[Dict[str, Path]] = None,
    limits: Optional[IntakeLimits] = None,
) -> AttemptMedia:
    """Validate an uploaded attempt and wrap it. ``extra``: {"raster": png} for traces,
    {"video": file} for tabla (accepted, not scored)."""
    path = Path(path)
    limits = limits or IntakeLimits()
    mime = check_file(path, kind, limits)
    checked_extra: Dict[str, Path] = {}
    for name, p in (extra or {}).items():
        p = Path(p)
        if name == "raster":
            check_file(p, "image", limits)
        elif name == "video":
            check_file(p, "video", limits)
        else:
            raise _invalid(f"Unexpected extra file {name!r}; only 'raster' and 'video' are accepted.")
        checked_extra[name] = p
    return AttemptMedia(
        kind=kind,  # type: ignore[arg-type]
        path=path,
        source_id=attempt_source_id(case_id, session_id, attempt_number),
        sha256=sha256_file(path),
        mime_type=mime,
        extra=checked_extra,
    )


def media_duration_sec(media: AttemptMedia) -> Optional[float]:
    """Best-effort duration for the attempt evidence (None when unknown or not timed)."""
    try:
        if media.kind == "trace":
            doc = json.loads(Path(media.path).read_text(encoding="utf-8-sig"))
            d = doc.get("duration_ms")
            if d is None:
                ts = [p[2] for s in doc.get("strokes", []) for p in s.get("points", []) if len(p) >= 3]
                d = max(ts) if ts else None
            return round(float(d) / 1000.0, 3) if d is not None else None
        if media.kind in ("audio", "video"):
            d = _media_duration(Path(media.path), media.kind)
            return round(d, 3) if d is not None else None
    except Exception:
        return None
    return None
