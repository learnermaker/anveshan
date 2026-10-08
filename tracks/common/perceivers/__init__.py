"""Layer 1 Perception public API.

Exact signatures as defined in K6 §2:

    perceive(path, mime, ctx, *, source_id, asset_dir, purpose, skill_hint, want_specialists) -> PerceptionRecord
    load_embeddings(record, record_dir) -> np.ndarray
    save_record(record, path) -> None
    load_record(path) -> PerceptionRecord

All model calls go through ctx.gateway. Embeddings are stored as a sidecar .npy
(float16, unit rows) next to the JSON record file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Optional

import numpy as np

from tracks.common.perception import PerceptionRecord
from tracks.common.runtime import RunContext


def perceive(
    path: Path,
    mime: str,
    ctx: RunContext,
    *,
    source_id: str,
    asset_dir: Path,
    purpose: Literal["source", "attempt"],
    skill_hint: Optional[str] = None,
    want_specialists: bool = True,
) -> PerceptionRecord:
    """Dispatch to the modality perceiver, run the intake screen for source files."""
    path = Path(path)
    mime = (mime or "").split(";", 1)[0].strip().lower()

    if mime.startswith("image/"):
        from tracks.common.perceivers.image import perceive_image as _perceive
        record = _perceive(
            path, mime, ctx,
            source_id=source_id,
            asset_dir=asset_dir,
            purpose=purpose,
            skill_hint=skill_hint,
            want_specialists=want_specialists,
        )
    elif mime.startswith("video/"):
        from tracks.common.perceivers.video import perceive_video as _perceive
        record = _perceive(
            path, mime, ctx,
            source_id=source_id,
            asset_dir=asset_dir,
            purpose=purpose,
            skill_hint=skill_hint,
            want_specialists=want_specialists,
        )
    elif mime.startswith("audio/"):
        from tracks.common.perceivers.audio import perceive_audio as _perceive
        record = _perceive(
            path, mime, ctx,
            source_id=source_id,
            asset_dir=asset_dir,
            purpose=purpose,
            skill_hint=skill_hint,
            want_specialists=want_specialists,
        )
    else:
        from tracks.common.models import AnveshanFailure, FailureCategory
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT,
            "This kind of file can't be used. Try a photo (JPG or PNG), a video (MP4 or WebM) or a sound recording (WAV or MP3).",
            {"mime": mime},
        )

    # Run the intake screen for source files and store the result
    if purpose == "source":
        from tracks.common.perceivers.screen import intake_from_perception
        intake = intake_from_perception(record)
        # Merge intake result back into the gate (the perceiver may have written a partial gate)
        record.gates["intake"] = record.gates.get("intake", {})
        record.gates["intake"].update({
            "safety": intake.safety,
            "teachable": intake.teachable,
            "teachable_reason": intake.teachable_reason,
            "skill_kind": intake.skill_kind,
        })

    return record


def load_embeddings(record: PerceptionRecord, record_dir: Path) -> np.ndarray:
    """Load the sidecar .npy embeddings as float32. Rows are aligned to record.embedding_index."""
    record_dir = Path(record_dir)
    if record.embeddings_file is None:
        raise FileNotFoundError(f"no embeddings_file in this PerceptionRecord")
    npy_path = record_dir / record.embeddings_file
    if not npy_path.exists():
        # also look in assets subdirectory
        npy_path = record_dir / "assets" / record.embeddings_file
    return np.load(str(npy_path)).astype(np.float32)


def save_record(record: PerceptionRecord, path: Path) -> None:
    """Write PerceptionRecord as JSON. The .npy must already sit next to the record file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.model_dump_json(indent=2), encoding="utf-8")


def load_record(path: Path) -> PerceptionRecord:
    """Load a PerceptionRecord from its JSON file."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return PerceptionRecord.model_validate(data)
