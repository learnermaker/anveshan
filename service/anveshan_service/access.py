"""Access control and visibility for cases.

Determines whether the current visitor can see a case, and builds the ``CaseAccess`` dict
that is added to every case summary and case view.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from anveshan_service.library import PUBLIC_STATUSES, blockers, kind_of, load
from anveshan_service.settings import Settings
from anveshan_service.steward import current_steward
from anveshan_service.visitors import _owners, current_visitor


def is_owner(case_dir: Path) -> bool:
    """True when the current visitor is the owner of this case dir (or no owners file exists)."""
    owners = _owners(case_dir)
    if owners is None:
        return True  # legacy dir (before isolation) or local dev
    vid = current_visitor.get()
    return bool(vid) and vid in owners


def can_view(settings: Settings, case_id: str, case_dir: Path) -> bool:
    """True when the current request may see this case."""
    # Tolerate missing directories (fakes in tests)
    if not Path(case_dir).is_dir():
        # Curated cases (no ~) are always visible; others default to private
        return "~" not in case_id

    k = kind_of(settings, case_id)
    if k == "curated":
        return True
    if is_owner(case_dir):
        return True
    rec = load(settings, case_id, case_dir)
    if rec.status in PUBLIC_STATUSES:
        return True
    if current_steward.get() and rec.status != "private":
        return True
    return False


def access_view(
    settings: Settings,
    case_id: str,
    case_dir: Path,
    review_status: str,
) -> Dict[str, Any]:
    """Build the CaseAccess dict for a case summary or view."""
    from anveshan_service.library import LibraryRecord

    # Tolerate missing directories (fakes in tests)
    if not Path(case_dir).is_dir():
        k: str = "curated" if "~" not in case_id else "community"
        steward = current_steward.get()
        default_rec = LibraryRecord(
            case_id=case_id,
            status="published" if k == "curated" else "private",
            collection=k,  # type: ignore[arg-type]
        )
        bl = blockers(k, default_rec, review_status)  # type: ignore[arg-type]
        return {
            "owner": False,
            "steward": steward,
            "library_status": default_rec.status,
            "collection": k,
            "credit_name": None,
            "licence": None,
            "can_edit": steward,
            "can_submit": False,
            "submit_blockers": bl,
            "steward_note": None,
        }

    k = kind_of(settings, case_id)
    rec = load(settings, case_id, case_dir)
    steward = current_steward.get()
    owner = k != "curated" and is_owner(case_dir)
    can_edit = owner or steward
    bl = blockers(k, rec, review_status) if owner else []
    can_submit = owner and not bl

    return {
        "owner": owner,
        "steward": steward,
        "library_status": rec.status,
        "collection": rec.collection,
        "credit_name": rec.credit_name,
        "licence": rec.licence,
        "can_edit": can_edit,
        "can_submit": can_submit,
        "submit_blockers": bl,
        "steward_note": rec.steward_note,
    }
