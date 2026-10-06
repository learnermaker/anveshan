"""Turn a ``GoalBuildResult`` into the next versioned set of case artifacts.

Writes (all at the same version N, status PENDING):
  knowledge/goal_model.vN.json        GoalModel
  knowledge/knowledge_package.vN.json KnowledgePackage   (contract)
  knowledge/criterion_map.vN.json     CriterionMap
  practice/rubric.vN.json             RubricDefinition   (contract)
  practice/practice_task.vN.json      PracticeTask       (contract)
  practice/observers.vN.json          Observers

Everything is validated (contracts, cross-contract invariants, grounding) before anything is
written. Output is deterministic: no timestamps, sorted JSON.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from tracks.common import validator
from tracks.common.casedata import (
    CriterionMap,
    CriterionMapEntry,
    GoalModel,
    Observers,
    SourceRecord,
    SourceRegistry,
    latest_version,
    versioned_path,
    write_json,
)
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import (
    ConsentMetadata,
    ExpertReview,
    KnowledgePackage,
    PracticeTask,
    ReviewStatus,
    RubricCriterion,
    RubricDefinition,
)

from track_a import config, grounding
from track_a.goals import GoalBuildResult

# stem -> sub-directory of the case pack
ARTIFACTS: Dict[str, str] = {
    "goal_model": "knowledge",
    "knowledge_package": "knowledge",
    "criterion_map": "knowledge",
    "rubric": "practice",
    "practice_task": "practice",
    "observers": "practice",
}

PENDING_REVIEWER = "unassigned"


@dataclass
class AuthoredCase:
    version: int
    goal: GoalModel
    package: KnowledgePackage
    rubric: RubricDefinition
    task: PracticeTask
    criterion_map: CriterionMap
    observers: Observers
    uncertainty: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    paths: Dict[str, Path] = field(default_factory=dict)


def artifact_dir(case_dir: Path, stem: str) -> Path:
    return case_dir / ARTIFACTS[stem]


def next_version(case_dir: Path) -> int:
    return max((latest_version(artifact_dir(case_dir, s), s) or 0) for s in ARTIFACTS) + 1


def package_id(case_id: str, version: int) -> str:
    return f"kp.{case_id}.{version}"


def rubric_id(case_id: str, version: int) -> str:
    return f"rubric.{case_id}.{version}"


def task_id(case_id: str, version: int) -> str:
    return f"task.{case_id}.{version}"


def skill_id_for(case_id: str, manifest: Dict[str, Any]) -> str:
    for key in ("skill_id", "skill"):
        v = manifest.get(key)
        if isinstance(v, str) and v:
            return v
    return f"skill.{config.base_case_id(case_id)}"


def consent_for(source: SourceRecord) -> ConsentMetadata:
    if source.runtime_label == "UPLOAD":
        return ConsentMetadata(
            contributor_name=source.creator,
            consent_scope="user upload",
            revocable=True,
            notes=source.attribution,
        )
    return ConsentMetadata(
        contributor_name=source.creator,
        consent_scope=f"public licence: {source.license}",
        revocable=False,
        notes=source.attribution,
    )


def _contract(msg: str, **details: Any) -> AnveshanFailure:
    return AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, msg, details)


def validate_goal_payload(modality: str, payload: Dict[str, Any]) -> List[str]:
    """Validate the payload against tracks.common.goals.<m>.PAYLOAD_MODEL when available."""
    mod_name = f"tracks.common.goals.{modality.split('_', 1)[0]}"
    try:
        mod = importlib.import_module(mod_name)
    except ImportError:
        return [f"goal payload not schema-checked: {mod_name} unavailable"]
    model = getattr(mod, "PAYLOAD_MODEL", None)
    if model is None:
        return [f"goal payload not schema-checked: {mod_name}.PAYLOAD_MODEL missing"]
    try:
        model.model_validate(payload)
    except ValidationError as exc:
        raise _contract(f"goal payload fails {model.__name__}: {exc}") from exc
    return []


def compose(
    *,
    case_id: str,
    manifest: Dict[str, Any],
    sources: SourceRegistry,
    source: SourceRecord,
    result: GoalBuildResult,
    modality: str,
    version: int,
) -> AuthoredCase:
    """Pure: build and validate all six artifacts in memory."""
    pid, rid, tid = package_id(case_id, version), rubric_id(case_id, version), task_id(case_id, version)
    skill = skill_id_for(case_id, manifest)
    warnings: List[str] = list(result.warnings)
    warnings.extend(validate_goal_payload(modality, result.goal_payload))

    try:
        package = KnowledgePackage(
            package_id=pid,
            skill_id=skill,
            title=result.title,
            summary=result.summary,
            claims=[c.model_copy(deep=True) for c in result.claims],
            consent=consent_for(source),
            expert_review=ExpertReview(reviewer_name=PENDING_REVIEWER, status=ReviewStatus.PENDING),
        )
    except ValidationError as exc:
        raise _contract(f"knowledge package invalid: {exc}") from exc

    claim_ids = {c.claim_id for c in package.claims}
    evidence_ids = {e.evidence_id for c in package.claims for e in c.evidence_refs}
    if not result.criteria:
        raise _contract("goal builder produced no criterion templates")
    templates = sorted(result.criteria, key=lambda t: (t.order_index, t.criterion_id))
    for t in templates:
        missing = [c for c in t.source_claim_ids if c not in claim_ids]
        if missing:
            raise _contract(f"{t.criterion_id}: source_claim_ids {missing} not in package", criterion_id=t.criterion_id)
        missing_ev = [e for e in t.reference_evidence_ids if e not in evidence_ids]
        if missing_ev:
            raise _contract(
                f"{t.criterion_id}: reference_evidence_ids {missing_ev} not in package", criterion_id=t.criterion_id
            )

    try:
        criteria = [
            RubricCriterion(
                criterion_id=t.criterion_id,
                name=t.name,
                description=t.description,
                observable_indicator=t.observable_indicator,
                weight=t.weight,
                required=t.required,
            )
            for t in templates
        ]
        max_score = sum(c.weight for c in criteria)
        passing = result.built_with.get("passing_score")
        passing_score = float(passing) if passing is not None else round(config.DEFAULT_PASSING_FRACTION * max_score, 4)
        rubric = RubricDefinition(
            rubric_id=rid,
            skill_id=skill,
            title=f"{result.title} — rubric",
            description=(
                f"Criteria authored from goal model v{version} ({modality}). Metric bands live in "
                f"practice/observers.v{version}.json; scores come only from the deterministic band policy."
            ),
            criteria=criteria,
            passing_score=passing_score,
        )
        task = PracticeTask(
            task_id=tid,
            package_id=pid,
            rubric_id=rid,
            title=result.task_title,
            instructions=result.task_instructions,
            constraints=[c.model_copy(deep=True) for c in result.task_constraints],
            target_criteria_ids=[c.criterion_id for c in criteria],
        )
        cmap = CriterionMap(
            rubric_id=rid,
            package_id=pid,
            criteria={
                t.criterion_id: CriterionMapEntry(
                    order_index=t.order_index,
                    source_claim_ids=list(t.source_claim_ids),
                    reference_evidence_ids=list(t.reference_evidence_ids),
                    why_it_matters=t.why_it_matters,
                    drill_hint=t.drill_hint,
                )
                for t in templates
            },
        )
        observers = Observers(
            rubric_id=rid,
            modality=modality,
            version=version,
            criteria={t.criterion_id: t.observer.model_copy(deep=True) for t in templates},
        )
        built_with = dict(result.built_with)
        built_with["run_keys"] = list(result.run_keys)
        goal = GoalModel(
            case_id=case_id,
            version=version,
            modality=modality,
            source_ids=[source.source_id],
            package_id=pid,
            built_with=built_with,
            payload=result.goal_payload,
            warnings=list(result.warnings),
        )
    except (ValidationError, ValueError) as exc:
        raise _contract(f"authored artifact invalid: {exc}") from exc

    validate_contracts(package, rubric, task)

    bad_cites = [c for c in grounding.cited_claim_ids(task.instructions) if c not in claim_ids]
    if bad_cites:
        raise _contract(f"task instructions cite unknown claims {sorted(set(bad_cites))}")
    uncertainty = grounding.audit_package(package, sources, modality)
    texts: List[Tuple[str, str]] = [("task.instructions", task.instructions), ("task.title", task.title)]
    for t in templates:
        texts += [(f"{t.criterion_id}.why_it_matters", t.why_it_matters), (f"{t.criterion_id}.drill_hint", t.drill_hint)]
    grounding.check_no_creator_intent(texts)

    return AuthoredCase(
        version=version,
        goal=goal,
        package=package,
        rubric=rubric,
        task=task,
        criterion_map=cmap,
        observers=observers,
        uncertainty=uncertainty,
        warnings=warnings,
    )


def validate_contracts(package: KnowledgePackage, rubric: RubricDefinition, task: PracticeTask) -> None:
    """Round-trip each contract through tracks.common.validator and check cross-contract invariants."""
    try:
        validator.validate_contract(package.model_dump(mode="json"), "KnowledgePackage")
        validator.validate_contract(rubric.model_dump(mode="json"), "RubricDefinition")
        validator.validate_contract(task.model_dump(mode="json"), "PracticeTask")
    except ValidationError as exc:
        raise _contract(f"contract validation failed: {exc}") from exc
    errors = validator.validate_practice_task_against_knowledge_and_rubric(task, package, rubric)
    if errors:
        raise _contract("cross-contract validation failed: " + "; ".join(errors), errors=errors)


def write(case_dir: Path, authored: AuthoredCase) -> Dict[str, Path]:
    v = authored.version
    objs = {
        "goal_model": authored.goal,
        "knowledge_package": authored.package,
        "criterion_map": authored.criterion_map,
        "rubric": authored.rubric,
        "practice_task": authored.task,
        "observers": authored.observers,
    }
    for stem in objs:
        p = versioned_path(artifact_dir(case_dir, stem), stem, v)
        if p.exists():
            raise _contract(f"refusing to overwrite existing {p.name}", path=str(p))
    paths: Dict[str, Path] = {}
    for stem, obj in objs.items():
        p = versioned_path(artifact_dir(case_dir, stem), stem, v)
        write_json(p, obj)
        paths[stem] = p
    authored.paths = paths
    return paths


def author_case(
    case_dir: Path,
    *,
    case_id: str,
    manifest: Dict[str, Any],
    sources: SourceRegistry,
    source: SourceRecord,
    result: GoalBuildResult,
    modality: str,
    version: Optional[int] = None,
) -> AuthoredCase:
    v = version if version is not None else next_version(case_dir)
    authored = compose(
        case_id=case_id, manifest=manifest, sources=sources, source=source, result=result, modality=modality, version=v
    )
    write(case_dir, authored)
    return authored
