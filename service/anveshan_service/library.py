"""Library lifecycle management for skills (curated and community).

Curated skills: status stored in <data_dir>/library/<case_id>.json (overlay; absence = published).
Community/derived skills: status stored in <case_dir>/.library.json.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from glob import glob
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel

from anveshan_service.errors import ServiceError
from anveshan_service.settings import Settings

STATUSES = ("private", "submitted", "published", "returned", "rejected", "unlisted")
LICENCES = ("CC-BY-4.0", "CC-BY-SA-4.0", "CC0-1.0", "PRACTICE-ONLY")
CONSENT_SCOPES = ("public_practice",)
PUBLIC_STATUSES = {"published"}
HISTORY_MAX = 50

_LIBRARY_FILE = ".library.json"


class HistoryEntry(BaseModel):
    at: str
    actor: Literal["creator", "steward", "system"]
    action: str
    note: Optional[str] = None


class LibraryRecord(BaseModel):
    case_id: str
    status: str = "private"
    collection: Literal["curated", "community"] = "community"
    credit_name: Optional[str] = None
    licence: Optional[str] = None
    consent_scope: str = "public_practice"
    rights_confirmed: bool = False
    rights_confirmed_at: Optional[str] = None
    people_visible: bool = False
    people_consented: bool = False
    submitted_at: Optional[str] = None
    decided_at: Optional[str] = None
    steward_note: Optional[str] = None
    history: List[HistoryEntry] = []


def kind_of(settings: Settings, case_id: str) -> Literal["curated", "community", "derived"]:
    """Determine whether a case is curated, community-composed, or hero-derived."""
    if "~" not in case_id:
        return "curated"
    case_dir = settings.data_dir / "cases" / case_id
    if list(case_dir.glob("knowledge/case_profile.v*.json")):
        return "community"
    return "derived"


def _read_source_credit(case_dir: Path) -> Optional[str]:
    """Try to read credit_name from source/source.json in the case directory."""
    src_path = Path(case_dir) / "source" / "source.json"
    if not src_path.is_file():
        return None
    try:
        data = json.loads(src_path.read_text(encoding="utf-8"))
        sources = data.get("sources", [])
        for s in sources:
            if s.get("used_by_system") is False:
                continue
            if s.get("role") == "held_out_reference":
                continue
            return s.get("attribution") or s.get("creator") or None
    except Exception:
        pass
    return None


def _curated_overlay_path(settings: Settings, case_id: str) -> Path:
    return settings.data_dir / "library" / f"{case_id}.json"


def load(settings: Settings, case_id: str, case_dir: Path) -> LibraryRecord:
    """Load the library record for a case; returns sensible defaults when no file exists."""
    k = kind_of(settings, case_id)
    if k == "curated":
        overlay = _curated_overlay_path(settings, case_id)
        if overlay.is_file():
            try:
                data = json.loads(overlay.read_text(encoding="utf-8"))
                return LibraryRecord.model_validate(data)
            except Exception:
                pass
        # Default for curated: published, credit from source
        credit = _read_source_credit(case_dir)
        return LibraryRecord(
            case_id=case_id,
            status="published",
            collection="curated",
            credit_name=credit,
            consent_scope="public_practice",
        )
    else:
        lib_file = Path(case_dir) / _LIBRARY_FILE
        if lib_file.is_file():
            try:
                data = json.loads(lib_file.read_text(encoding="utf-8"))
                return LibraryRecord.model_validate(data)
            except Exception:
                pass
        return LibraryRecord(
            case_id=case_id,
            status="private",
            collection="community",
        )


def save(settings: Settings, rec: LibraryRecord, case_dir: Path) -> None:
    """Write the library record atomically."""
    k = kind_of(settings, rec.case_id)
    if k == "curated":
        dest = _curated_overlay_path(settings, rec.case_id)
        dest.parent.mkdir(parents=True, exist_ok=True)
    else:
        dest = Path(case_dir) / _LIBRARY_FILE
    tmp = dest.parent / f".library_tmp_{os.getpid()}.json"
    tmp.write_text(rec.model_dump_json(), encoding="utf-8")
    os.replace(tmp, dest)


def create_initial(settings: Settings, case_dir: Path, case_id: str) -> LibraryRecord:
    """Called by compose create. Writes an initial private record with rights_confirmed=True."""
    now = datetime.now(timezone.utc).isoformat()
    rec = LibraryRecord(
        case_id=case_id,
        status="private",
        collection="community",
        rights_confirmed=True,
        rights_confirmed_at=now,
        history=[HistoryEntry(at=now, actor="system", action="created")],
    )
    save(settings, rec, case_dir)
    return rec


def blockers(
    kind: Literal["curated", "community", "derived"],
    rec: LibraryRecord,
    review_status: str,
) -> List[str]:
    """Return plain-language reasons why a creator cannot submit this skill."""
    result: List[str] = []
    if kind == "derived":
        result.append("Uploads made from a featured skill can't be published. Share your own skill instead.")
        return result
    if kind == "curated":
        result.append("Featured skills are managed by stewards.")
        return result
    if review_status not in ("approved", "revised"):
        result.append("Check what the AI understood and confirm the steps first.")
    if rec.status not in ("private", "returned"):
        result.append(f"This skill has already been sent to the library.")
    return result


def submit(
    settings: Settings,
    case_id: str,
    case_dir: Path,
    body: Dict[str, Any],
    review_status: str,
) -> LibraryRecord:
    """Creator submits a skill for review."""
    rec = load(settings, case_id, case_dir)
    k = kind_of(settings, case_id)

    # Validate transition conditions
    bl = blockers(k, rec, review_status)
    # Override check: only community, status private/returned
    extra_bl: List[str] = []
    if k != "community":
        extra_bl.extend(bl)
    else:
        if review_status not in ("approved", "revised"):
            extra_bl.append("Check what the AI understood and confirm the steps first.")
        if rec.status not in ("private", "returned"):
            extra_bl.append(f"This skill is already {rec.status}.")

    credit_name = (body.get("credit_name") or "").strip()
    if not credit_name:
        extra_bl.append("Provide a credit name.")
    elif len(credit_name) > 60:
        extra_bl.append("Credit name must be 60 characters or fewer.")

    licence = body.get("licence")
    if licence not in LICENCES:
        raise ServiceError(400, "INVALID_INPUT", f"Licence must be one of {list(LICENCES)}.",
                           {"blockers": [f"Licence must be one of {list(LICENCES)}."]})

    if body.get("people_visible") and not body.get("people_consented"):
        extra_bl.append("Confirm that people shown have given consent.")

    if extra_bl:
        raise ServiceError(400, "INVALID_INPUT", "Cannot submit this skill.", {"blockers": extra_bl})

    now = datetime.now(timezone.utc).isoformat()
    rec = LibraryRecord(
        case_id=rec.case_id,
        status="submitted",
        collection=rec.collection,
        credit_name=credit_name,
        licence=licence,
        consent_scope=body.get("consent_scope", "public_practice"),
        rights_confirmed=body.get("rights_confirmed", rec.rights_confirmed),
        rights_confirmed_at=rec.rights_confirmed_at,
        people_visible=body.get("people_visible", False),
        people_consented=body.get("people_consented", False),
        submitted_at=now,
        decided_at=rec.decided_at,
        steward_note=rec.steward_note,
        history=list(rec.history) + [HistoryEntry(at=now, actor="creator", action="submitted")],
    )
    rec = LibraryRecord.model_validate({
        **rec.model_dump(),
        "history": rec.history[-HISTORY_MAX:],
    })
    save(settings, rec, case_dir)
    return rec


def withdraw(settings: Settings, case_id: str, case_dir: Path) -> LibraryRecord:
    """Creator withdraws a skill back to private."""
    rec = load(settings, case_id, case_dir)
    # Any status can be withdrawn to private per spec
    if rec.status == "private":
        raise ServiceError(409, "INVALID_INPUT", "This skill is already private.")
    now = datetime.now(timezone.utc).isoformat()
    new_history = list(rec.history) + [HistoryEntry(at=now, actor="creator", action="withdrawn")]
    rec = LibraryRecord.model_validate({
        **rec.model_dump(),
        "status": "private",
        "history": new_history[-HISTORY_MAX:],
    })
    save(settings, rec, case_dir)
    return rec


def decide(
    settings: Settings,
    case_id: str,
    case_dir: Path,
    decision: str,
    note: Optional[str],
) -> LibraryRecord:
    """Steward decides on a submission."""
    rec = load(settings, case_id, case_dir)
    k = kind_of(settings, case_id)

    _TRANSITIONS: Dict[str, tuple] = {
        "publish": ("submitted", "published"),
        "return": ("submitted", "returned"),
        "reject": ("submitted", "rejected"),
        "unlist": ("published", "unlisted"),
        "republish": ("unlisted", "published"),
    }
    if decision not in _TRANSITIONS:
        raise ServiceError(400, "INVALID_INPUT", f"Unknown decision {decision!r}.")

    expected_from, new_status = _TRANSITIONS[decision]
    if rec.status != expected_from:
        raise ServiceError(
            409, "INVALID_INPUT",
            f"Cannot {decision} a skill that is {rec.status}."
        )

    # Note required for return, reject and unlist
    if decision in ("return", "reject", "unlist") and not (note or "").strip():
        raise ServiceError(400, "INVALID_INPUT", f"A note is required when you {decision} a skill.")

    now = datetime.now(timezone.utc).isoformat()
    new_history = list(rec.history) + [
        HistoryEntry(at=now, actor="steward", action=decision, note=note or None)
    ]
    rec = LibraryRecord.model_validate({
        **rec.model_dump(),
        "status": new_status,
        "decided_at": now,
        "steward_note": note or None,
        "history": new_history[-HISTORY_MAX:],
    })
    save(settings, rec, case_dir)
    return rec
