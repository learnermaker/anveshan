"""Steward console routes (prefix /api/steward).

All routes require ``require_steward`` dependency.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field

from anveshan_service import adapters
from anveshan_service import insights as insights_module
from anveshan_service import library as library_module
from anveshan_service.deps import get_settings
from anveshan_service.errors import not_found
from anveshan_service.housekeeping import _size
from anveshan_service.library import kind_of, load
from anveshan_service.paths import case_dir as _case_dir
from anveshan_service.settings import Settings
from anveshan_service.steward import require_steward
from tracks.common.models import DAILY_BUDGET, USAGE

router = APIRouter(prefix="/api/steward")

# Cache storage_bytes for 30 s
_storage_cache: Dict[str, Any] = {"value": 0, "at": 0.0}


def _storage_bytes(settings: Settings) -> int:
    now = time.monotonic()
    if now - _storage_cache["at"] > 30:
        try:
            _storage_cache["value"] = _size(settings.data_dir)
            _storage_cache["at"] = now
        except Exception:
            pass
    return _storage_cache["value"]


def _is_synthetic(summary: dict) -> bool:
    return summary.get("modality") is None


def _list_all_summaries(settings: Settings) -> List[dict]:
    """Return all case summaries that are not synthetic showcases."""
    try:
        api = adapters.track_a()
        with adapters.translated():
            summaries = api.list_cases(settings.cases_root, settings.data_dir)
    except Exception:
        summaries = []
    return [s for s in summaries if not _is_synthetic(s)]


def _case_dir_for(settings: Settings, case_id: str) -> Any:
    """Resolve a case directory (curated or community)."""
    if "~" in case_id:
        return settings.data_dir / "cases" / case_id
    return settings.cases_root / case_id


def _load_view(settings: Settings, case_id: str) -> Any:
    """Load the case view via Track A."""
    cdir = _case_dir_for(settings, case_id)
    api = adapters.track_a()
    try:
        with adapters.translated():
            return api.load_case(cdir).to_view()
    except Exception:
        return None


class DecideBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str
    note: Optional[str] = Field(default=None, max_length=500)


@router.post("/check", dependencies=[Depends(require_steward)])
def steward_check() -> dict:
    return {"ok": True}


@router.get("/overview", dependencies=[Depends(require_steward)])
def steward_overview(settings: Settings = Depends(get_settings)) -> Any:
    from anveshan_service.metrics import METRICS
    summaries = _list_all_summaries(settings)

    library_skills = 0
    waiting_review = 0
    attention: List[dict] = []
    curated_unchecked: List[dict] = []

    for s in summaries:
        cid = str(s.get("case_id", ""))
        cdir = _case_dir_for(settings, cid)
        k = kind_of(settings, cid)
        rec = load(settings, cid, cdir)
        # Skip private community/derived skills
        if k != "curated" and rec.status == "private":
            continue
        if rec.status == "published":
            library_skills += 1
        if rec.status == "submitted":
            waiting_review += 1
        # Curated unchecked
        if k == "curated" and rec.status == "published":
            rv = s.get("review_status", "pending")
            if rv not in ("approved", "revised"):
                curated_unchecked.append({"case_id": cid, "title": s.get("title", cid)})

    today_totals = insights_module.today_totals(settings)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # live_calls_today
    budget = DAILY_BUDGET.limit()
    used = DAILY_BUDGET.today_used()

    storage = _storage_bytes(settings)
    cap = int(settings.data_cap_mb * 1024 * 1024)

    # Build attention list
    if waiting_review > 0:
        n = waiting_review
        noun = "skill is" if n == 1 else "skills are"
        attention.append({
            "kind": "submissions_waiting",
            "text": f"{n} shared {noun} waiting for review",
            "case_id": None,
            "count": n,
        })
    for uc in curated_unchecked:
        attention.append({
            "kind": "curated_unchecked",
            "text": f"\"{uc['title']}\" has not been checked by an expert yet",
            "case_id": uc["case_id"],
            "count": 1,
        })
    if budget > 0 and used / budget >= 0.8:
        pct = int(round(used / budget * 100))
        attention.append({
            "kind": "budget_high",
            "text": f"{pct}% of today's AI budget is used",
            "case_id": None,
            "count": pct,
        })
    if cap > 0 and storage / cap >= 0.8:
        pct = int(round(storage / cap * 100))
        attention.append({
            "kind": "storage_high",
            "text": f"Storage is {pct}% full; old private data will be removed soon",
            "case_id": None,
            "count": pct,
        })

    return {
        "library_skills": library_skills,
        "waiting_review": waiting_review,
        "learners_today": today_totals["learners_today"],
        "attempts_today": today_totals["attempts_today"],
        "live_calls_today": used,
        "daily_budget": budget,
        "storage_bytes": storage,
        "storage_cap_bytes": cap,
        "attention": attention,
        "ephemeral": True,
    }


@router.get("/queue", dependencies=[Depends(require_steward)])
def steward_queue(settings: Settings = Depends(get_settings)) -> Any:
    summaries = _list_all_summaries(settings)
    queue: List[dict] = []
    for s in summaries:
        cid = str(s.get("case_id", ""))
        cdir = _case_dir_for(settings, cid)
        k = kind_of(settings, cid)
        rec = load(settings, cid, cdir)
        rv = s.get("review_status", "pending")

        if k != "curated" and rec.status == "submitted":
            # Load steps count (lazy)
            steps = 0
            try:
                view = _load_view(settings, cid)
                if isinstance(view, dict):
                    pkg = view.get("package") or {}
                    steps = len(pkg.get("claims") or [])
            except Exception:
                pass
            queue.append({
                "case_id": cid,
                "title": s.get("title", cid),
                "kind": "submission",
                "modality": s.get("modality") or "",
                "library_status": rec.status,
                "review_status": rv,
                "credit_name": rec.credit_name,
                "submitted_at": rec.submitted_at,
                "steps": steps,
            })
        elif k == "curated" and rec.status == "published" and rv not in ("approved", "revised"):
            steps = 0
            try:
                view = _load_view(settings, cid)
                if isinstance(view, dict):
                    pkg = view.get("package") or {}
                    steps = len(pkg.get("claims") or [])
            except Exception:
                pass
            queue.append({
                "case_id": cid,
                "title": s.get("title", cid),
                "kind": "curated_unchecked",
                "modality": s.get("modality") or "",
                "library_status": rec.status,
                "review_status": rv,
                "credit_name": rec.credit_name,
                "submitted_at": None,
                "steps": steps,
            })

    # Order: submissions (oldest submitted_at first), then curated by title
    submissions = [q for q in queue if q["kind"] == "submission"]
    curated_items = [q for q in queue if q["kind"] == "curated_unchecked"]
    submissions.sort(key=lambda x: x.get("submitted_at") or "")
    curated_items.sort(key=lambda x: x.get("title", ""))
    return submissions + curated_items


@router.get("/library", dependencies=[Depends(require_steward)])
def steward_library(settings: Settings = Depends(get_settings)) -> Any:
    summaries = _list_all_summaries(settings)
    rows: List[dict] = []
    for s in summaries:
        cid = str(s.get("case_id", ""))
        cdir = _case_dir_for(settings, cid)
        k = kind_of(settings, cid)
        rec = load(settings, cid, cdir)
        # Skip private community/derived skills
        if k != "curated" and rec.status == "private":
            continue
        act = insights_module.activity(settings, cid)
        rows.append({
            "case_id": cid,
            "title": s.get("title", cid),
            "modality": s.get("modality") or "",
            "collection": rec.collection,
            "library_status": rec.status,
            "review_status": s.get("review_status", "pending"),
            "credit_name": rec.credit_name,
            "licence": rec.licence,
            "learners": act["learners"],
            "attempts": act["attempts"],
            "last_activity": act["last_activity"],
        })
    return rows


@router.post("/library/{case_id}/decide", dependencies=[Depends(require_steward)])
def steward_decide(
    case_id: str,
    body: DecideBody,
    settings: Settings = Depends(get_settings),
) -> Any:
    cdir_path = _case_dir_for(settings, case_id)
    # Verify the case directory exists (raises 404 if not)
    if not cdir_path.is_dir():
        raise not_found(f"unknown case {case_id}", case_id=case_id)
    with adapters.resource_lock("case", case_id):
        rec = library_module.decide(settings, case_id, cdir_path, body.decision, body.note)
    return rec.model_dump()


@router.get("/consent", dependencies=[Depends(require_steward)])
def steward_consent(settings: Settings = Depends(get_settings)) -> Any:
    summaries = _list_all_summaries(settings)
    rows: List[dict] = []
    for s in summaries:
        cid = str(s.get("case_id", ""))
        cdir = _case_dir_for(settings, cid)
        k = kind_of(settings, cid)
        rec = load(settings, cid, cdir)
        if k != "curated" and rec.status == "private":
            continue
        sources = []
        try:
            view = _load_view(settings, cid)
            if isinstance(view, dict):
                for src in (view.get("sources") or []):
                    if src.get("access_level") in (None, "public") or src.get("runtime_label") in ("INTERNET_REFERENCE", "UPLOAD"):
                        sources.append({
                            "source_id": src.get("source_id", ""),
                            "attribution": src.get("attribution") or src.get("creator", ""),
                            "license": src.get("license") or src.get("licence", ""),
                            "url": src.get("url"),
                        })
        except Exception:
            pass
        rows.append({
            "case_id": cid,
            "title": s.get("title", cid),
            "collection": rec.collection,
            "library_status": rec.status,
            "credit_name": rec.credit_name,
            # curated skills have no library licence of their own: show their source's licence
            "licence": rec.licence or next((x["license"] for x in sources if x["license"]), None),
            "consent_scope": rec.consent_scope,
            "rights_confirmed": rec.rights_confirmed,
            "rights_confirmed_at": rec.rights_confirmed_at,
            "people_visible": rec.people_visible,
            "people_consented": rec.people_consented,
            "sources": sources,
            "history": [h.model_dump() for h in rec.history],
        })
    return rows


@router.get("/consent/export", dependencies=[Depends(require_steward)])
def steward_consent_export(settings: Settings = Depends(get_settings)) -> Response:
    rows = steward_consent(settings)
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "skills": rows,
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="anveshan-consent-{date_str}.json"'},
    )


@router.get("/usage", dependencies=[Depends(require_steward)])
def steward_usage(settings: Settings = Depends(get_settings)) -> Any:
    from anveshan_service.metrics import METRICS

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    budget = DAILY_BUDGET.limit()
    used = DAILY_BUDGET.today_used()
    storage = _storage_bytes(settings)
    cap = int(settings.data_cap_mb * 1024 * 1024)

    return {
        "started_at": METRICS.started_at,
        "uptime_s": METRICS.uptime_s(),
        "mode": settings.mode,
        "live_calls_today": used,
        "daily_budget": budget,
        "own_key_calls": USAGE.own_key_calls,
        "cache_hits": USAGE.cache_hits,
        "requests_by_class": METRICS.get("requests"),
        "rate_limited": METRICS.get("rate_limited"),
        "errors_by_category": METRICS.get("errors"),
        "attempts_today": METRICS.get("attempts_day").get(today, 0),
        "compose_today": METRICS.get("compose_day").get(today, 0),
        "storage_bytes": storage,
        "storage_cap_bytes": cap,
        "data_ttl_hours": settings.data_ttl_hours,
    }


@router.get("/review-export/{case_id}", dependencies=[Depends(require_steward)])
def steward_review_export(case_id: str, settings: Settings = Depends(get_settings)) -> Response:
    cdir = _case_dir_for(settings, case_id)
    if not cdir.is_dir():
        raise not_found(f"unknown case {case_id}", case_id=case_id)
    view = _load_view(settings, case_id)
    if not isinstance(view, dict):
        raise not_found(f"case view unavailable for {case_id}", case_id=case_id)
    pkg = view.get("package") or {}
    date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    payload = {
        "case_id": case_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "review_status": view.get("review_status", "pending"),
        "knowledge_package": pkg,
        "expert_review": pkg.get("expert_review"),
    }
    return Response(
        content=json.dumps(payload, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="anveshan-review-{case_id}-{date_str}.json"'},
    )
