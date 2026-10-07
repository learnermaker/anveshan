"""Sample pack helpers: load committed sample attempts and example sources (K9-P4).

``load_pack`` reads ``tracks/cases/<case_id>/samples/samples.json``.
``load_sources`` reads ``tracks/samples/sources/sources.json``.
Both validate the data against the spec's field rules and enforce the repo file-size limit.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from anveshan_service import REPO_ROOT
from anveshan_service.errors import ServiceError

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE_ID_RE = re.compile(r"^[a-z0-9-]{1,40}$")
MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB repo limit

_VALID_QUALITY = {"good", "flawed", "unrelated"}
_VALID_KINDS = {"trace", "image", "audio", "video"}


# ---------------------------------------------------------------------------
# Internal model (one row of samples.json)
# ---------------------------------------------------------------------------

class Sample(BaseModel):
    """Mirrors one entry in a case's ``samples/samples.json``."""
    model_config = ConfigDict(extra="forbid")

    sample_id: str = Field(min_length=1, max_length=40)
    label: str = Field(min_length=1, max_length=200)
    quality: str
    attempt_kind: str
    file: str = Field(min_length=1, max_length=200)
    raster: Optional[str] = None
    description: str = Field(default="", max_length=500)
    preview: Optional[str] = None
    synthetic: bool = True
    credit: Optional[str] = None
    licence: str = Field(min_length=1, max_length=100)
    expected: Optional[Dict] = None   # calibration metadata; not exposed to clients

    @model_validator(mode="after")
    def _validate_fields(self) -> "Sample":
        if not SAMPLE_ID_RE.fullmatch(self.sample_id):
            raise ValueError(f"sample_id {self.sample_id!r} does not match ^[a-z0-9-]{{1,40}}$")
        if self.quality not in _VALID_QUALITY:
            raise ValueError(f"quality {self.quality!r} must be one of {sorted(_VALID_QUALITY)}")
        if self.attempt_kind not in _VALID_KINDS:
            raise ValueError(f"attempt_kind {self.attempt_kind!r} must be one of {sorted(_VALID_KINDS)}")
        return self


# ---------------------------------------------------------------------------
# Pack loader
# ---------------------------------------------------------------------------

def load_pack(case_dir: Path) -> List[Sample]:
    """Load and validate a case's sample pack.

    Returns an empty list when no ``samples/`` directory exists. Raises
    ``ServiceError(500, ...)`` when the pack is malformed or files exceed 2 MB.
    """
    import json

    samples_dir = case_dir / "samples"
    if not samples_dir.is_dir():
        return []

    manifest_path = samples_dir / "samples.json"
    if not manifest_path.is_file():
        return []

    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ServiceError(500, "CONTRACT_VIOLATION", f"samples.json is not valid JSON: {exc}") from exc

    raw_samples = data.get("samples", [])
    if not isinstance(raw_samples, list):
        raise ServiceError(500, "CONTRACT_VIOLATION", "samples.json: 'samples' must be a list")

    result: List[Sample] = []
    for entry in raw_samples:
        try:
            s = Sample.model_validate(entry)
        except Exception as exc:
            sid = entry.get("sample_id", "?") if isinstance(entry, dict) else "?"
            raise ServiceError(
                500, "CONTRACT_VIOLATION", f"samples.json: entry {sid!r} invalid: {exc}"
            ) from exc

        # Validate the primary file exists and is within the size limit
        file_path = samples_dir / s.file
        if not file_path.is_file():
            raise ServiceError(
                500, "CONTRACT_VIOLATION",
                f"sample {s.sample_id!r}: file {s.file!r} not found in samples dir"
            )
        sz = file_path.stat().st_size
        if sz > MAX_FILE_BYTES:
            raise ServiceError(
                500, "CONTRACT_VIOLATION",
                f"sample {s.sample_id!r}: file {s.file!r} is {sz} bytes (limit {MAX_FILE_BYTES})"
            )

        # Validate raster file if present
        if s.raster is not None:
            raster_path = samples_dir / s.raster
            if not raster_path.is_file():
                raise ServiceError(
                    500, "CONTRACT_VIOLATION",
                    f"sample {s.sample_id!r}: raster {s.raster!r} not found in samples dir"
                )

        result.append(s)

    return result


# ---------------------------------------------------------------------------
# Public view (SampleAttempt shape matching app/src/api/types-product.ts)
# ---------------------------------------------------------------------------

def public_view(case_id: str, s: Sample) -> dict:
    """Convert an internal Sample to the SampleAttempt wire shape."""
    preview_url = None
    if s.preview is not None:
        preview_url = f"/api/cases/{case_id}/samples/{s.sample_id}/preview"
    return {
        "sample_id": s.sample_id,
        "label": s.label,
        "quality": s.quality,
        "attempt_kind": s.attempt_kind,
        "description": s.description,
        "preview_url": preview_url,
        "synthetic": s.synthetic,
        "credit": s.credit,
    }


# ---------------------------------------------------------------------------
# Sample file paths
# ---------------------------------------------------------------------------

def sample_paths(case_dir: Path, s: Sample) -> Tuple[Path, Optional[Path]]:
    """Return (primary_file_path, raster_path_or_None) for a sample."""
    samples_dir = case_dir / "samples"
    primary = samples_dir / s.file
    raster: Optional[Path] = None
    if s.raster is not None:
        raster = samples_dir / s.raster
    return primary, raster


# ---------------------------------------------------------------------------
# Example sources loader
# ---------------------------------------------------------------------------


def load_sources(repo_root: Path = REPO_ROOT) -> List[dict]:
    """Load example sources for the composer (``tracks/samples/sources/sources.json``).

    Returns a list of SampleSource-shaped dicts (as in app/src/api/types-product.ts).
    Returns an empty list when the file is absent.
    """
    import json

    path = repo_root / "tracks" / "samples" / "sources" / "sources.json"
    if not path.is_file():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    sources = data.get("sources", [])
    if not isinstance(sources, list):
        return []

    result = []
    for s in sources:
        if not isinstance(s, dict):
            continue
        sid = s.get("sample_id", "")
        if not SAMPLE_ID_RE.fullmatch(sid):
            continue
        result.append({
            "sample_id": sid,
            "label": s.get("label", ""),
            "description": s.get("description", ""),
            "mime_type": s.get("mime_type", "application/octet-stream"),
            "preview_url": f"/api/compose/samples/{sid}/file",
            "credit": s.get("credit", ""),
            "licence": s.get("licence", ""),
        })

    return result


def _raw_source_entry(sample_id: str, repo_root: Path = REPO_ROOT) -> Optional[Dict]:
    """Return the raw ``sources.json`` entry for *sample_id*, or ``None`` if absent.

    Use this when the caller needs the ``file`` field that :func:`load_sources` strips
    from the normalised public view.  Having a single reader here eliminates the
    double-read pattern that would otherwise appear in routes that serve or analyse
    a source file.
    """
    import json

    path = repo_root / "tracks" / "samples" / "sources" / "sources.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return next(
        (s for s in data.get("sources", []) if isinstance(s, dict) and s.get("sample_id") == sample_id),
        None,
    )
