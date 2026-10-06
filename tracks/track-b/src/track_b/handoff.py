"""Read Track A's handoff artifacts from a case directory (track-b-spec §3.1).

Track B never imports the Track A package: it reads the versioned case files directly.

Version selection: the highest ``knowledge_package.vN`` whose expert review is
approved (or revised), else the highest non-rejected version. The other five artifacts
use the same ``N`` when present, else the highest version below ``N``. A session pins
the selected versions so a rebuild mid-session cannot change the rubric under it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from tracks.common.casedata import (
    CriterionMap,
    GoalModel,
    Observers,
    load_sources,
    versioned_path,
)
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import (
    EvidenceRef,
    KnowledgePackage,
    PracticeTask,
    ReviewStatus,
    RubricCriterion,
    RubricDefinition,
)
from tracks.common.validator import validate_practice_task_against_knowledge_and_rubric

M = TypeVar("M", bound=BaseModel)

# stem -> (sub-directory, model)
ARTIFACTS: Dict[str, tuple] = {
    "knowledge_package": ("knowledge", KnowledgePackage),
    "goal_model": ("knowledge", GoalModel),
    "criterion_map": ("knowledge", CriterionMap),
    "rubric": ("practice", RubricDefinition),
    "practice_task": ("practice", PracticeTask),
    "observers": ("practice", Observers),
}

_VER = re.compile(r"\.v(\d+)\.json$")

APPROVED_STATUSES = {ReviewStatus.APPROVED, ReviewStatus.REVISED}


@dataclass
class TrackBHandoff:
    case_id: str
    case_dir: Path
    goal: GoalModel
    package: KnowledgePackage
    rubric: RubricDefinition
    task: PracticeTask
    criterion_map: CriterionMap
    observers: Observers
    versions: Dict[str, int]
    review_status: str
    warnings: List[str] = field(default_factory=list)

    @property
    def approved(self) -> bool:
        return self.review_status in {s.value for s in APPROVED_STATUSES}

    def criterion(self, criterion_id: str) -> RubricCriterion:
        for c in self.rubric.criteria:
            if c.criterion_id == criterion_id:
                return c
        raise KeyError(criterion_id)

    def evidence_index(self) -> Dict[str, EvidenceRef]:
        """evidence_id -> EvidenceRef over every claim in the package (first occurrence wins)."""
        out: Dict[str, EvidenceRef] = {}
        for claim in self.package.claims:
            for ev in claim.evidence_refs:
                out.setdefault(ev.evidence_id, ev)
        return out

    def expert_evidence(self, criterion_id: str) -> Optional[EvidenceRef]:
        """The criterion map's first resolvable reference evidence for a criterion, else None."""
        entry = self.criterion_map.criteria.get(criterion_id)
        if entry is None:
            return None
        index = self.evidence_index()
        for ev_id in entry.reference_evidence_ids:
            if ev_id in index:
                return index[ev_id]
        return None


def _violation(message: str, **details) -> AnveshanFailure:
    return AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, message, details)


def _versions(directory: Path, stem: str) -> List[int]:
    if not directory.exists():
        return []
    return sorted(int(m.group(1)) for p in directory.glob(f"{stem}.v*.json") if (m := _VER.search(p.name)))


def _load(case_dir: Path, stem: str, version: int) -> BaseModel:
    sub, model = ARTIFACTS[stem]
    path = versioned_path(case_dir / sub, stem, version)
    try:
        return model.model_validate_json(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise _violation(f"missing case artifact {sub}/{path.name}", case_dir=str(case_dir))
    except (ValidationError, ValueError) as e:
        raise _violation(f"invalid case artifact {sub}/{path.name}: {e}", case_dir=str(case_dir))


def select_versions(case_dir: Path) -> Dict[str, int]:
    """Pick artifact versions: approved-else-latest knowledge package, others aligned to it."""
    pkg_versions = _versions(case_dir / "knowledge", "knowledge_package")
    if not pkg_versions:
        raise _violation(f"case {case_dir.name} has no knowledge/knowledge_package.vN.json (build the case first)")
    chosen: Optional[int] = None
    fallback: Optional[int] = None
    for v in reversed(pkg_versions):
        pkg = _load(case_dir, "knowledge_package", v)
        status = pkg.expert_review.status if pkg.expert_review else ReviewStatus.PENDING
        if status in APPROVED_STATUSES:
            chosen = v
            break
        if status != ReviewStatus.REJECTED and fallback is None:
            fallback = v
    if chosen is None:
        chosen = fallback
    if chosen is None:
        raise AnveshanFailure(
            FailureCategory.HUMAN_REVIEW_REQUIRED,
            f"every knowledge package version of {case_dir.name} was rejected by review",
        )
    out = {"knowledge_package": chosen}
    for stem, (sub, _model) in ARTIFACTS.items():
        if stem == "knowledge_package":
            continue
        candidates = [v for v in _versions(case_dir / sub, stem) if v <= chosen]
        if not candidates:
            raise _violation(f"case {case_dir.name} has no {sub}/{stem}.vN.json with N <= {chosen}")
        out[stem] = max(candidates)
    return out


def _case_id(case_dir: Path) -> str:
    return case_dir.name


def load_handoff(case_dir: Path, versions: Optional[Dict[str, int]] = None) -> TrackBHandoff:
    """Load and cross-validate the handoff. Any inconsistency raises CONTRACT_VIOLATION."""
    case_dir = Path(case_dir)
    versions = dict(versions) if versions else select_versions(case_dir)
    missing = set(ARTIFACTS) - set(versions)
    if missing:
        raise _violation(f"pinned versions missing artifacts: {sorted(missing)}")
    loaded = {stem: _load(case_dir, stem, versions[stem]) for stem in ARTIFACTS}
    package: KnowledgePackage = loaded["knowledge_package"]
    goal: GoalModel = loaded["goal_model"]
    cmap: CriterionMap = loaded["criterion_map"]
    rubric: RubricDefinition = loaded["rubric"]
    task: PracticeTask = loaded["practice_task"]
    observers: Observers = loaded["observers"]

    errors: List[str] = list(validate_practice_task_against_knowledge_and_rubric(task, package, rubric))
    if goal.package_id != package.package_id:
        errors.append(f"goal_model package_id {goal.package_id!r} != knowledge package {package.package_id!r}")
    if goal.modality != observers.modality:
        errors.append(f"goal_model modality {goal.modality!r} != observers modality {observers.modality!r}")
    if cmap.rubric_id != rubric.rubric_id:
        errors.append(f"criterion_map rubric_id {cmap.rubric_id!r} != rubric {rubric.rubric_id!r}")
    if cmap.package_id != package.package_id:
        errors.append(f"criterion_map package_id {cmap.package_id!r} != knowledge package {package.package_id!r}")
    if observers.rubric_id != rubric.rubric_id:
        errors.append(f"observers rubric_id {observers.rubric_id!r} != rubric {rubric.rubric_id!r}")

    rubric_ids = {c.criterion_id for c in rubric.criteria}
    for name, ids in (("criterion_map", set(cmap.criteria)), ("observers", set(observers.criteria))):
        for cid in sorted(rubric_ids - ids):
            errors.append(f"rubric criterion {cid} is missing from {name}")
        for cid in sorted(ids - rubric_ids):
            errors.append(f"{name} criterion {cid} is not in rubric {rubric.rubric_id}")

    claim_ids = {c.claim_id for c in package.claims}
    evidence_ids = {ev.evidence_id for c in package.claims for ev in c.evidence_refs}
    for cid, entry in sorted(cmap.criteria.items()):
        for claim_id in entry.source_claim_ids:
            if claim_id not in claim_ids:
                errors.append(f"criterion_map {cid} cites unknown claim {claim_id}")
        for ev_id in entry.reference_evidence_ids:
            if ev_id not in evidence_ids:
                errors.append(f"criterion_map {cid} references unknown evidence {ev_id}")

    if errors:
        raise _violation(f"case {case_dir.name} handoff is inconsistent", errors=errors)

    status = (package.expert_review.status if package.expert_review else ReviewStatus.PENDING).value
    warnings: List[str] = []
    if ReviewStatus(status) not in APPROVED_STATUSES:
        warnings.append(f"package not expert-approved (review status: {status})")
    warnings.extend(goal.warnings)
    return TrackBHandoff(
        case_id=_case_id(case_dir),
        case_dir=case_dir,
        goal=goal,
        package=package,
        rubric=rubric,
        task=task,
        criterion_map=cmap,
        observers=observers,
        versions=versions,
        review_status=status,
        warnings=warnings,
    )


def expert_id(handoff: TrackBHandoff) -> str:
    """Expert identity for the TransmissionRecord: consent contributor, else the source creator."""
    name = (handoff.package.consent.contributor_name or "").strip()
    if name:
        return name
    try:
        return load_sources(handoff.case_dir).primary().creator
    except (FileNotFoundError, KeyError, ValidationError, ValueError):
        raise _violation(f"case {handoff.case_id}: no consent contributor_name and no source creator for expert_id")
