"""Sample routes: ready-made attempts and example sources for the demo (K9-P4).

Routes (registered in anveshan_service.main create_app; no separate include_router needed):

  GET  /api/cases/{case_id}/samples
  GET  /api/cases/{case_id}/samples/{sample_id}/preview
  POST /api/sessions/{session_id}/attempts/sample/{sample_id}
  GET  /api/compose/samples
  GET  /api/compose/samples/{sample_id}/file
  POST /api/compose/sample/{sample_id}

See docs/kiro/specs/K9-P4-SAMPLES.md §4.2 for the detailed behaviour contract.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from anveshan_service import REPO_ROOT, adapters
from anveshan_service.deps import get_mode, get_settings
from anveshan_service.errors import invalid, not_found
from anveshan_service.paths import StoredUpload, base_case_id, case_dir, check_session_id, content_type
from anveshan_service.samples import SAMPLE_ID_RE, _raw_source_entry, load_pack, load_sources, public_view, sample_paths
from anveshan_service.settings import Settings
from anveshan_service.visitors import add_owner

router = APIRouter()

_SOURCES_DIR = REPO_ROOT / "tracks" / "samples" / "sources"


def _check_sample_id(sample_id: str) -> str:
    """Validate sample_id and reject path-traversal attempts."""
    if not SAMPLE_ID_RE.fullmatch(sample_id or ""):
        raise invalid("invalid sample_id", sample_id=sample_id[:64] if sample_id else sample_id)
    return sample_id


# ---------------------------------------------------------------------------
# GET /api/cases/{case_id}/samples
# ---------------------------------------------------------------------------

@router.get("/api/cases/{case_id}/samples")
def list_samples(case_id: str, settings: Settings = Depends(get_settings)) -> List[dict]:
    """Return the list of sample attempts for a case (SampleAttempt[])."""
    # Hero-derived cases use the base case's pack
    base = base_case_id(case_id)
    cdir = case_dir(settings, base)
    pack = load_pack(cdir)
    return [public_view(base, s) for s in pack]


# ---------------------------------------------------------------------------
# GET /api/cases/{case_id}/samples/{sample_id}/preview
# ---------------------------------------------------------------------------

@router.get("/api/cases/{case_id}/samples/{sample_id}/preview")
def get_sample_preview(
    case_id: str,
    sample_id: str,
    settings: Settings = Depends(get_settings),
) -> Any:
    """Serve the sample's preview media file."""
    _check_sample_id(sample_id)
    base = base_case_id(case_id)
    cdir = case_dir(settings, base)
    pack = load_pack(cdir)
    matched = next((s for s in pack if s.sample_id == sample_id), None)
    if matched is None:
        raise not_found(f"sample {sample_id!r} not found", case_id=case_id, sample_id=sample_id)
    preview_path = cdir / "samples" / (matched.preview or matched.file)
    if not preview_path.is_file():
        raise not_found("preview file missing", case_id=case_id, sample_id=sample_id)
    return FileResponse(preview_path, media_type=content_type(preview_path))


# ---------------------------------------------------------------------------
# POST /api/sessions/{session_id}/attempts/sample/{sample_id}
# ---------------------------------------------------------------------------

@router.post("/api/sessions/{session_id}/attempts/sample/{sample_id}")
def submit_sample_attempt(
    session_id: str,
    sample_id: str,
    settings: Settings = Depends(get_settings),
    mode: str = Depends(get_mode),
) -> Any:
    """Submit a committed sample file as the learner's attempt.

    Behaves identically to ``POST /api/sessions/{session_id}/attempts`` but the uploaded
    files come from the committed sample pack rather than a multipart upload.
    """
    _check_sample_id(sample_id)
    check_session_id(session_id)

    api = adapters.track_b()
    with adapters.session_lock(session_id):
        # Load the session
        try:
            session = api.load_session(session_id, settings.data_dir)
        except (FileNotFoundError, KeyError) as exc:
            raise not_found(f"unknown session {session_id}") from exc

        # Resolve the case dir and load the pack
        cdir = adapters.session_case_dir(session, settings)
        base = base_case_id(cdir.name)
        base_cdir = case_dir(settings, base)
        pack = load_pack(base_cdir)

        matched = next((s for s in pack if s.sample_id == sample_id), None)
        if matched is None:
            raise not_found(f"sample {sample_id!r} not found", sample_id=sample_id)

        primary_path, raster_path = sample_paths(base_cdir, matched)

        # Store the primary file in the uploads directory (mimic store_upload semantics)
        uploads = settings.data_dir / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        raw_bytes = primary_path.read_bytes()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        ext = primary_path.suffix.lower()
        dest = uploads / f"{digest}{ext}"
        if not dest.exists():
            dest.write_bytes(raw_bytes)
        mime = content_type(primary_path)
        primary_stored = StoredUpload(
            path=dest,
            sha256=digest,
            bytes=len(raw_bytes),
            mime_type=mime,
            filename=primary_path.name,
        )

        # Handle optional raster
        extras: Dict[str, StoredUpload] = {}
        if raster_path is not None and raster_path.is_file():
            raster_raw = raster_path.read_bytes()
            raster_digest = hashlib.sha256(raster_raw).hexdigest()
            raster_ext = raster_path.suffix.lower()
            raster_dest = uploads / f"{raster_digest}{raster_ext}"
            if not raster_dest.exists():
                raster_dest.write_bytes(raster_raw)
            extras["raster"] = StoredUpload(
                path=raster_dest,
                sha256=raster_digest,
                bytes=len(raster_raw),
                mime_type=content_type(raster_path),
                filename=raster_path.name,
            )

        ctx = adapters.run_context(settings, cdir, mode)
        with adapters.translated():
            media = adapters.make_attempt_media(
                matched.attempt_kind, primary_stored, extras, session=session, api=api
            )
            result = api.submit_attempt(session, media, ctx)
            api.save_session(session, settings.data_dir)

    # Optional insights recording (P1 adds this; check gracefully)
    _try_record_insights(session_id, sample_id)

    return adapters.to_json(result)


def _try_record_insights(session_id: str, sample_id: str) -> None:
    """Record a sample attempt event in insights (P1 is merged; guard removed at integration)."""
    try:
        from anveshan_service import insights  # noqa: PLC0415
        insights.record_attempt(session_id=session_id, sample_id=sample_id, source="sample")
    except Exception:  # noqa: BLE001
        pass  # insights errors must never break the attempt response


# ---------------------------------------------------------------------------
# GET /api/compose/samples
# ---------------------------------------------------------------------------

@router.get("/api/compose/samples")
def list_sample_sources(settings: Settings = Depends(get_settings)) -> List[dict]:
    """Return example sources for the composer (SampleSource[])."""
    return load_sources(REPO_ROOT)


# ---------------------------------------------------------------------------
# GET /api/compose/samples/{sample_id}/file
# ---------------------------------------------------------------------------

def _source_file(raw_entry: Dict[str, Any]) -> Path:
    """An example source's file: ``canonical_path`` (repo-root-relative, single-copy rule; AGENTS.md) or ``file``."""
    canonical = raw_entry.get("canonical_path", "")
    return REPO_ROOT / canonical if canonical else _SOURCES_DIR / raw_entry.get("file", "")


def _seed_example_draft(settings: Settings, file_path: Path) -> None:
    """Composer examples ship their finished draft (tracks/samples/sources/drafts/<id>), so they open at
    once and need no visitor key; create_draft then returns it unchanged. A new upload still needs the
    visitor's own key. The source file stays at its canonical path; the draft gets a working copy."""
    draft_id = hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]
    shipped = _SOURCES_DIR / "drafts" / draft_id
    dst = settings.data_dir / "drafts" / draft_id
    if not shipped.is_dir() or (dst / "draft.json").exists():
        return
    shutil.copytree(shipped, dst, dirs_exist_ok=True)
    source = dst / ("source" + file_path.suffix)
    shutil.copyfile(file_path, source)
    data = json.loads((dst / "draft.json").read_text(encoding="utf-8"))
    data["source_path"] = str(source)
    (dst / "draft.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


@router.get("/api/compose/samples/{sample_id}/file")
def get_sample_source_file(sample_id: str) -> Any:
    """Serve the source file for a composer example."""
    _check_sample_id(sample_id)
    raw_entry = _raw_source_entry(sample_id)
    if raw_entry is None:
        raise not_found(f"sample source {sample_id!r} not found", sample_id=sample_id)

    file_path = _source_file(raw_entry)
    file_name = file_path.name
    if not file_path.is_file():
        raise not_found(f"source file for {sample_id!r} not found", sample_id=sample_id)

    mime = raw_entry.get("mime_type") or content_type(file_path)
    return FileResponse(file_path, media_type=mime, filename=file_name)


# ---------------------------------------------------------------------------
# POST /api/compose/sample/{sample_id}
# ---------------------------------------------------------------------------

@router.post("/api/compose/sample/{sample_id}")
def analyze_sample_source(
    sample_id: str,
    settings: Settings = Depends(get_settings),
    mode: str = Depends(get_mode),
) -> Any:
    """Analyze a committed example source as if the user had uploaded it.

    Equivalent to ``POST /api/compose/analyze`` with the committed file and
    ``rights_confirmed=True``. The sample is CC0 or has its own credit.
    """
    _check_sample_id(sample_id)

    raw_entry = _raw_source_entry(sample_id)
    if raw_entry is None:
        raise not_found(f"sample source {sample_id!r} not found", sample_id=sample_id)

    file_path = _source_file(raw_entry)
    if not file_path.is_file():
        raise not_found(f"source file for {sample_id!r} not found", sample_id=sample_id)

    mime = raw_entry.get("mime_type") or content_type(file_path)
    title_hint = raw_entry.get("label", "")

    try:
        import importlib
        composer = importlib.import_module("track_a.composer")
    except ImportError as exc:
        from anveshan_service.errors import ServiceError
        raise ServiceError(
            503, "SERVICE_UNAVAILABLE",
            "Composer (track_a.composer) is not available in this build"
        ) from exc

    _seed_example_draft(settings, file_path)
    ctx = adapters.run_context(settings, settings.data_dir, mode)
    with adapters.resource_lock("sample_source", sample_id), adapters.translated():
        draft = composer.create_draft(
            settings.data_dir,
            file_path,
            mime,
            ctx,
            title_hint=title_hint,
            rights_confirmed=True,
        )

    view = draft.to_view()
    if isinstance(view, dict) and view.get("draft_id"):
        add_owner(settings.data_dir / "drafts" / str(view["draft_id"]))
    return view
