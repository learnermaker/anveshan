"""Safe resolution of case/session ids and streamed upload storage."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from anveshan_service.errors import ServiceError, invalid, not_found
from anveshan_service.settings import Settings

CASE_ID_RE = re.compile(r"^[a-z0-9-]+(~[0-9a-f]{12})?$")
SESSION_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ASSET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_EXT_RE = re.compile(r"^\.[a-z0-9]{1,8}$")

mimetypes.add_type("video/ogg", ".ogv")
mimetypes.add_type("audio/ogg", ".oga")
mimetypes.add_type("audio/ogg", ".ogg")
mimetypes.add_type("video/webm", ".webm")
mimetypes.add_type("audio/wav", ".wav")
mimetypes.add_type("image/webp", ".webp")


def within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def check_case_id(case_id: str) -> str:
    if not CASE_ID_RE.fullmatch(case_id or ""):
        raise invalid("invalid case id", case_id=case_id[:80] if case_id else case_id)
    return case_id


def base_case_id(case_id: str) -> str:
    return check_case_id(case_id).split("~", 1)[0]


def case_dir(settings: Settings, case_id: str) -> Path:
    """Hero/showcase cases live under cases_root; derived upload cases under <data_dir>/cases."""
    check_case_id(case_id)
    root = settings.data_dir / "cases" if "~" in case_id else settings.cases_root
    d = root / case_id
    if not within(d, root) or not d.is_dir():
        raise not_found(f"unknown case {case_id}", case_id=case_id)
    return d


def check_session_id(session_id: str) -> str:
    if not SESSION_ID_RE.fullmatch(session_id or "") or ".." in session_id:
        raise invalid("invalid session id")
    return session_id


def check_asset(name: str) -> str:
    if not ASSET_RE.fullmatch(name or "") or ".." in name:
        raise invalid("invalid asset name")
    return name


def content_type(path: Path, declared: Optional[str] = None) -> str:
    if declared and declared != "application/octet-stream":
        return declared
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "application/octet-stream"


@dataclass(frozen=True)
class StoredUpload:
    path: Path
    sha256: str
    bytes: int
    mime_type: str
    filename: str


def _extension(upload: UploadFile) -> str:
    ext = Path(upload.filename or "").suffix.lower()
    if _EXT_RE.fullmatch(ext):
        return ext
    guessed = mimetypes.guess_extension((upload.content_type or "").split(";")[0].strip()) or ""
    return guessed if _EXT_RE.fullmatch(guessed) else ".bin"


def store_upload(upload: UploadFile, settings: Settings, field: str = "file") -> StoredUpload:
    """Stream an upload to <data_dir>/uploads/<sha256><ext>, enforcing the size limit (413)."""
    limit = settings.max_upload_bytes
    uploads = settings.data_dir / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    ext = _extension(upload)
    tmp = uploads / f".part-{uuid.uuid4().hex}"
    h = hashlib.sha256()
    size = 0
    try:
        upload.file.seek(0)
        with open(tmp, "wb") as out:
            while True:
                chunk = upload.file.read(1 << 20)
                if not chunk:
                    break
                size += len(chunk)
                if size > limit:
                    raise ServiceError(
                        413,
                        "INVALID_INPUT",
                        f"upload '{field}' exceeds the {settings.max_upload_mb:g} MB limit",
                        {"field": field, "limit_bytes": limit},
                    )
                h.update(chunk)
                out.write(chunk)
        if size == 0:
            raise invalid(f"upload '{field}' is empty", field=field)
        digest = h.hexdigest()
        dest = uploads / f"{digest}{ext}"
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()
    declared = (upload.content_type or "").split(";")[0].strip() or None
    return StoredUpload(dest, digest, size, content_type(dest, declared), upload.filename or dest.name)
