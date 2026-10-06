"""Expert review -> new package version (track-a-spec §9).

Every action writes ``knowledge_package.v{N+1}`` (plus matching ``criterion_map`` and
``practice_task`` versions so ``package_id`` stays consistent). Earlier versions are never edited.
Confidence is never raised by review; approval lives only in ``ExpertReview``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from tracks.common.casedata import CriterionMap, latest_version, load_versioned, versioned_path, write_json
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import ExpertReview, KnowledgePackage, PracticeTask, ReviewStatus, RubricDefinition

from track_a import authoring

ACTIONS = ("approve", "revise_claim", "reject_claim", "reject_package")

M = TypeVar("M", bound=BaseModel)


def _invalid(msg: str, **details: Any) -> AnveshanFailure:
    return AnveshanFailure(FailureCategory.INVALID_INPUT, msg, details)


def find_by(case_dir: Path, stem: str, model: Type[M], pred: Callable[[M], bool], max_version: Optional[int] = None) -> Optional[tuple[int, M]]:
    """Latest version (<= max_version) of ``stem`` whose model satisfies ``pred``."""
    d = authoring.artifact_dir(case_dir, stem)
    top = latest_version(d, stem)
    if top is None:
        return None
    if max_version is not None:
        top = min(top, max_version)
    for v in range(top, 0, -1):
        p = versioned_path(d, stem, v)
        if not p.exists():
            continue
        obj = model.model_validate_json(p.read_text(encoding="utf-8"))
        if pred(obj):
            return v, obj
    return None


def apply(case_dir: Path, case_id: str, action: Dict[str, Any], now: Optional[Callable[[], str]] = None) -> int:
    """Apply a review action to the latest package version. Returns the new package version."""
    kind = action.get("action")
    if kind not in ACTIONS:
        raise _invalid(f"unknown review action {kind!r}; expected one of {ACTIONS}")
    reviewer = action.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise _invalid("review action needs a non-empty 'reviewer'")
    note = (action.get("note") or "").strip()

    kdir = authoring.artifact_dir(case_dir, "knowledge_package")
    cur_v = latest_version(kdir, "knowledge_package")
    if cur_v is None:
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"no knowledge package to review in {case_dir}")
    pkg = load_versioned(kdir, "knowledge_package", KnowledgePackage, cur_v)
    if pkg.expert_review is not None and pkg.expert_review.status == ReviewStatus.REJECTED:
        raise _invalid(f"{pkg.package_id} is rejected; rebuild the case before reviewing again")

    new_v = authoring.next_version(case_dir)
    new_pid = authoring.package_id(case_id, new_v)
    new_pkg = pkg.model_copy(deep=True)
    new_pkg.package_id = new_pid
    flagged: list[str] = []
    rejected_claim: Optional[str] = None

    if kind == "approve":
        status, body = ReviewStatus.APPROVED, note or "Approved."
    elif kind == "reject_package":
        status, body = ReviewStatus.REJECTED, note or "Package rejected."
    else:
        claim_id = action.get("claim_id")
        claim = next((c for c in new_pkg.claims if c.claim_id == claim_id), None)
        if claim is None:
            raise _invalid(f"claim {claim_id!r} not found in {pkg.package_id}", claim_id=claim_id)
        if kind == "revise_claim":
            new_statement = (action.get("new_statement") or "").strip()
            if not new_statement:
                raise _invalid("revise_claim needs a non-empty 'new_statement'")
            old = claim.statement
            claim.statement = new_statement
            status = ReviewStatus.REVISED
            body = f"{claim_id} revised: '{old}' -> '{new_statement}'" + (f". {note}" if note else "")
        else:  # reject_claim
            if len(new_pkg.claims) == 1:
                raise _invalid("cannot reject the only claim; use reject_package")
            new_pkg.claims = [c for c in new_pkg.claims if c.claim_id != claim_id]
            rejected_claim = claim_id
            status = ReviewStatus.REVISED
            body = f"{claim_id} rejected and removed (was: '{claim.statement}')" + (f". {note}" if note else "")
            rejected_evidence = {e.evidence_id for e in claim.evidence_refs}

    reviewed_at = action.get("reviewed_at") or (now() if now else datetime.now(timezone.utc).isoformat())

    # Dependent artifacts bound to the old package id.
    hit_map = find_by(case_dir, "criterion_map", CriterionMap, lambda m: m.package_id == pkg.package_id)
    hit_task = find_by(case_dir, "practice_task", PracticeTask, lambda t: t.package_id == pkg.package_id)
    if hit_map is None or hit_task is None:
        raise AnveshanFailure(
            FailureCategory.MISSING_EVIDENCE, f"criterion map / practice task for {pkg.package_id} not found"
        )
    cmap = hit_map[1].model_copy(deep=True)
    cmap.package_id = new_pid
    if rejected_claim is not None:
        for cid, entry in sorted(cmap.criteria.items()):
            if rejected_claim in entry.source_claim_ids or rejected_evidence.intersection(entry.reference_evidence_ids):
                entry.why_it_matters = f"[FLAGGED: {rejected_claim} rejected in expert review] {entry.why_it_matters}"
                flagged.append(cid)
        if flagged:
            body += f". Flagged criteria: {', '.join(flagged)}"
    task = hit_task[1].model_copy(update={"package_id": new_pid}, deep=True)

    new_pkg.expert_review = ExpertReview(
        reviewer_name=reviewer.strip(),
        status=status,
        reviewed_at=reviewed_at,
        notes=f"{body} (review of {pkg.package_id})",
    )
    try:
        new_pkg = KnowledgePackage.model_validate(new_pkg.model_dump(mode="json"))
        cmap = CriterionMap.model_validate(cmap.model_dump(mode="json"))
    except ValidationError as exc:
        raise AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, f"reviewed artifacts invalid: {exc}") from exc
    rubric_hit = find_by(case_dir, "rubric", RubricDefinition, lambda r: r.rubric_id == task.rubric_id)
    if rubric_hit is None:
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"rubric {task.rubric_id} not found")
    authoring.validate_contracts(new_pkg, rubric_hit[1], task)

    write_json(versioned_path(kdir, "knowledge_package", new_v), new_pkg)
    write_json(versioned_path(authoring.artifact_dir(case_dir, "criterion_map"), "criterion_map", new_v), cmap)
    write_json(versioned_path(authoring.artifact_dir(case_dir, "practice_task"), "practice_task", new_v), task)
    return new_v
