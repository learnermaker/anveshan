"""Track A public API (docs/plans/service-api.md §2). The only module Integration imports.

Hero cases (kolam / origami / tabla) and derived upload cases ``<base>~<sha12>`` run a modality
goal builder and produce versioned case artifacts. The four showcase cases are SYNTHETIC replay
bundles: they load their committed ``replay/bundle.json`` and have no goal model.
"""

from __future__ import annotations

import importlib
import json
import logging
import mimetypes
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from tracks.common.casedata import (
    CriterionMap,
    GoalModel,
    Observers,
    SourceRecord,
    SourceRegistry,
    latest_version,
    load_sources,
    load_versioned,
    resolve_media,
    versioned_path,
    write_json,
)
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.runtime import RunContext
from tracks.common.schemas import KnowledgePackage, PracticeTask, ReviewStatus, RubricDefinition

from track_a import authoring, config, query, review
from track_a import goals as goal_builders

log = logging.getLogger(__name__)

NOT_APPROVED_WARNING = "package not expert-approved"
GOOD_STATUSES = ("approved", "revised")


@dataclass
class CaseHandoff:
    case_id: str
    case_dir: Path
    manifest: dict
    sources: SourceRegistry
    goal: Optional[GoalModel]                 # None for SYNTHETIC showcase / unbuilt cases
    package: KnowledgePackage
    rubric: RubricDefinition
    task: PracticeTask
    criterion_map: Optional[CriterionMap]     # None for SYNTHETIC showcase / unbuilt cases
    observers: Optional[Observers]            # None for SYNTHETIC showcase / unbuilt cases
    review_status: str                        # pending|approved|revised|rejected
    runtime_label: str                        # INTERNET_REFERENCE|UPLOAD|SYNTHETIC|OWNED_CONSENTED
    warnings: List[str] = field(default_factory=list)
    versions: Dict[str, int] = field(default_factory=dict)

    @property
    def modality(self) -> Optional[str]:
        return config.modality_for(self.case_id, self.case_dir)

    def to_view(self) -> dict:
        """JSON for GET /api/cases/{id}. Never exposes held-out or unused sources."""
        warnings = list(self.warnings)
        goal_view: Optional[dict] = None
        if self.goal is not None:
            goal_view = {
                "case_id": self.goal.case_id,
                "modality": self.goal.modality,
                "version": self.goal.version,
                "package_id": self.goal.package_id,
                "source_ids": list(self.goal.source_ids),
                "warnings": list(self.goal.warnings),
                "ui_view": _goal_ui_view(self.goal, warnings),
            }

        # Load CaseProfile for composed cases (universal modality)
        profile_view = None
        if self.modality == "universal":
            profile_view = _load_profile_view(self.case_dir)

        return {
            "case_id": self.case_id,
            "title": self.manifest.get("title", self.case_id),
            "modality": self.modality,
            "hero": self.case_id in config.HERO_CASES,
            "derived_from": config.base_case_id(self.case_id) if config.is_derived(self.case_id) else None,
            "manifest": self.manifest,
            "sources": public_sources(self.case_id, self.sources),
            "goal": goal_view,
            "package": self.package.model_dump(mode="json"),
            "rubric": self.rubric.model_dump(mode="json"),
            "task": self.task.model_dump(mode="json"),
            "criterion_map": self.criterion_map.model_dump(mode="json") if self.criterion_map else None,
            "observers": self.observers.model_dump(mode="json") if self.observers else None,
            "review_status": self.review_status,
            "runtime_label": self.runtime_label,
            "warnings": warnings,
            "versions": dict(self.versions),
            "lesson": lesson_outline(self),
            "profile": profile_view,
        }


# ---------------------------------------------------------------------------
# View helpers
# ---------------------------------------------------------------------------


def media_url(case_id: str, source_id: str) -> str:
    return f"/api/media/{case_id}/{source_id}"


def _load_profile_view(case_dir: Path) -> Optional[dict]:
    """Load a CaseProfile dict from case_dir/knowledge/case_profile.v*.json."""
    try:
        from tracks.common.profile import CaseProfile
        profile_files = sorted(case_dir.glob("knowledge/case_profile.v*.json"))
        if not profile_files:
            return None
        profile = CaseProfile.model_validate(
            json.loads(profile_files[-1].read_text(encoding="utf-8"))
        )
        return profile.model_dump(mode="json")
    except Exception as e:
        log.warning("could not load profile from %s: %s", case_dir, e)
        return None


def public_sources(case_id: str, sources: SourceRegistry) -> List[dict]:
    out = []
    for s in sources.sources:
        if not s.used_by_system or s.role == "held_out_reference":
            continue
        out.append(
            {
                "source_id": s.source_id,
                "role": s.role,
                "mime_type": s.mime_type,
                "sha256": s.sha256,
                "bytes": s.bytes,
                "duration_sec": s.duration_sec,
                "dimensions": s.dimensions,
                "window_sec": s.window_sec,
                "creator": s.creator,
                "license": s.license,
                "attribution": s.attribution,
                "access_level": s.access_level,
                "runtime_label": s.runtime_label,
                "media_url": media_url(case_id, s.source_id),
            }
        )
    return out


def _goal_ui_view(goal: GoalModel, warnings: List[str]) -> Optional[dict]:
    mod_name = f"tracks.common.goals.{goal.modality.split('_', 1)[0]}"
    try:
        mod = importlib.import_module(mod_name)
    except ImportError:
        msg = f"goal ui_view unavailable: {mod_name} not importable"
        log.warning(msg)
        warnings.append(msg)
        return None
    fn = getattr(mod, "ui_view", None)
    if fn is None:
        warnings.append(f"goal ui_view unavailable: {mod_name}.ui_view missing")
        return None
    return fn(goal.payload)


def lesson_outline(h: CaseHandoff) -> dict:
    """Deterministic teaching order: STEP claims in claim order, criteria by criterion_map order_index."""
    claims = {c.claim_id: c for c in h.package.claims}

    def claim_view(cid: str) -> Optional[dict]:
        c = claims.get(cid)
        if c is None:
            return None
        return {
            "claim_id": c.claim_id,
            "claim_type": c.claim_type.value,
            "statement": c.statement,
            "is_observed": c.is_observed,
            "evidence": [e.model_dump(mode="json") for e in c.evidence_refs],
        }

    steps = [claim_view(c.claim_id) for c in h.package.claims if c.claim_type.value == "step"]
    criteria = []
    rubric_order = {c.criterion_id: i for i, c in enumerate(h.rubric.criteria)}
    for crit in h.rubric.criteria:
        entry = h.criterion_map.criteria.get(crit.criterion_id) if h.criterion_map else None
        criteria.append(
            {
                "criterion_id": crit.criterion_id,
                "name": crit.name,
                "required": crit.required,
                "order_index": entry.order_index if entry else rubric_order[crit.criterion_id],
                "why_it_matters": entry.why_it_matters if entry else None,
                "drill_hint": entry.drill_hint if entry else None,
                "reference_evidence_ids": list(entry.reference_evidence_ids) if entry else [],
                "claims": [v for v in (claim_view(c) for c in (entry.source_claim_ids if entry else [])) if v],
            }
        )
    criteria.sort(key=lambda c: (c["order_index"], c["criterion_id"]))
    return {"title": h.task.title, "instructions": h.task.instructions, "steps": steps, "criteria": criteria}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _read_manifest(case_dir: Path) -> dict:
    p = case_dir / "manifest.json"
    if not p.exists():
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"no manifest.json in {case_dir}")
    return json.loads(p.read_text(encoding="utf-8"))


def _package_versions(case_dir: Path) -> List[int]:
    d = authoring.artifact_dir(case_dir, "knowledge_package")
    top = latest_version(d, "knowledge_package")
    if top is None:
        return []
    return [v for v in range(top, 0, -1) if versioned_path(d, "knowledge_package", v).exists()]


def _status(pkg: KnowledgePackage) -> str:
    return pkg.expert_review.status.value if pkg.expert_review else ReviewStatus.PENDING.value


def select_package_version(case_dir: Path) -> tuple[Optional[int], List[str]]:
    """Latest approved/revised version newer than the most recent rejection, else the latest
    such version with a warning. If the latest version itself is rejected, return it."""
    d = authoring.artifact_dir(case_dir, "knowledge_package")
    versions = _package_versions(case_dir)
    if not versions:
        return None, []
    live: List[tuple[int, str]] = []
    for v in versions:
        st = _status(load_versioned(d, "knowledge_package", KnowledgePackage, v))
        if st == ReviewStatus.REJECTED.value:
            break
        live.append((v, st))
    if not live:
        return versions[0], ["package rejected by expert review; rebuild required"]
    for v, st in live:
        if st in GOOD_STATUSES:
            return v, []
    return live[0][0], [NOT_APPROVED_WARNING]


def _sources_or_empty(case_dir: Path, case_id: str) -> SourceRegistry:
    try:
        return load_sources(case_dir)
    except FileNotFoundError:
        return SourceRegistry(case_id=case_id, sources=[])


def _runtime_label(sources: SourceRegistry) -> str:
    try:
        return sources.primary().runtime_label
    except KeyError:
        return "SYNTHETIC"


def _load_built(case_dir: Path, manifest: dict, version: int, warnings: List[str]) -> CaseHandoff:
    case_id = manifest.get("case_id", case_dir.name)
    pkg = load_versioned(authoring.artifact_dir(case_dir, "knowledge_package"), "knowledge_package", KnowledgePackage, version)
    pid = pkg.package_id
    task_hit = review.find_by(case_dir, "practice_task", PracticeTask, lambda t: t.package_id == pid)
    map_hit = review.find_by(case_dir, "criterion_map", CriterionMap, lambda m: m.package_id == pid)
    if task_hit is None or map_hit is None:
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"practice task / criterion map for {pid} not found")
    task = task_hit[1]
    rubric_hit = review.find_by(case_dir, "rubric", RubricDefinition, lambda r: r.rubric_id == task.rubric_id)
    if rubric_hit is None:
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"rubric {task.rubric_id} not found")
    rubric_v, rubric = rubric_hit
    obs_hit = review.find_by(case_dir, "observers", Observers, lambda o: o.rubric_id == rubric.rubric_id)
    if obs_hit is None:
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"observers for {rubric.rubric_id} not found")
    goal_hit = review.find_by(case_dir, "goal_model", GoalModel, lambda g: True, max_version=rubric_v)
    if goal_hit is None:
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"goal model for {rubric.rubric_id} not found")
    sources = _sources_or_empty(case_dir, case_id)
    cmap = map_hit[1]

    warnings = list(warnings)
    warnings.extend(goal_hit[1].warnings)
    claim_ids = {c.claim_id for c in pkg.claims}
    evidence_ids = {e.evidence_id for c in pkg.claims for e in c.evidence_refs}
    for cid, entry in sorted(cmap.criteria.items()):
        dangling = [c for c in entry.source_claim_ids if c not in claim_ids]
        dangling += [e for e in entry.reference_evidence_ids if e not in evidence_ids]
        if dangling:
            warnings.append(f"criterion {cid} cites rejected/missing {dangling}")
    status = _status(pkg)
    if status not in GOOD_STATUSES and NOT_APPROVED_WARNING not in warnings and status != "rejected":
        warnings.append(NOT_APPROVED_WARNING)
    return CaseHandoff(
        case_id=case_id,
        case_dir=case_dir,
        manifest=manifest,
        sources=sources,
        goal=goal_hit[1],
        package=pkg,
        rubric=rubric,
        task=task,
        criterion_map=cmap,
        observers=obs_hit[1],
        review_status=status,
        runtime_label=_runtime_label(sources),
        warnings=list(dict.fromkeys(warnings)),
        versions={
            "knowledge_package": version,
            "practice_task": task_hit[0],
            "criterion_map": map_hit[0],
            "rubric": rubric_v,
            "observers": obs_hit[0],
            "goal_model": goal_hit[0],
        },
    )


def _load_bundle(case_dir: Path, manifest: dict, warnings: List[str]) -> CaseHandoff:
    case_id = manifest.get("case_id", case_dir.name)
    p = case_dir / "replay" / "bundle.json"
    if not p.exists():
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"{case_id}: no built artifacts and no replay bundle")
    bundle = json.loads(p.read_text(encoding="utf-8"))
    try:
        pkg = KnowledgePackage.model_validate(bundle["knowledge_package"])
        rubric = RubricDefinition.model_validate(bundle["rubric"])
        task = PracticeTask.model_validate(bundle["practice_task"])
    except (KeyError, ValidationError) as exc:
        raise AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, f"{case_id}: invalid replay bundle: {exc}") from exc
    return CaseHandoff(
        case_id=case_id,
        case_dir=case_dir,
        manifest=manifest,
        sources=_sources_or_empty(case_dir, case_id),
        goal=None,
        package=pkg,
        rubric=rubric,
        task=task,
        criterion_map=None,
        observers=None,
        review_status=_status(pkg),
        runtime_label="SYNTHETIC",
        warnings=warnings,
        versions={},
    )


def load_case(case_dir: Path) -> CaseHandoff:
    """Latest approved-else-latest built versions; SYNTHETIC replay bundle for showcase/unbuilt cases."""
    case_dir = Path(case_dir)
    manifest = _read_manifest(case_dir)
    case_id = manifest.get("case_id", case_dir.name)
    if config.modality_for(case_id, case_dir) is None:
        return _load_bundle(case_dir, manifest, ["SYNTHETIC replay showcase: no goal model"])
    version, warnings = select_package_version(case_dir)
    if version is None:
        return _load_bundle(case_dir, manifest, ["case not built yet: showing its SYNTHETIC replay bundle"])
    return _load_built(case_dir, manifest, version, warnings)


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------


def _summary(case_dir: Path, *, hero: bool, derived_from: Optional[str] = None) -> dict:
    manifest = _read_manifest(case_dir)
    case_id = manifest.get("case_id", case_dir.name)
    modality = config.modality_for(case_id, case_dir)
    built = False
    review_status = "pending"
    runtime_label = "SYNTHETIC"
    if modality is not None:
        version, _ = select_package_version(case_dir)
        if version is not None:
            built = True
            pkg = load_versioned(authoring.artifact_dir(case_dir, "knowledge_package"), "knowledge_package", KnowledgePackage, version)
            review_status = _status(pkg)
        runtime_label = _runtime_label(_sources_or_empty(case_dir, case_id))
    else:
        p = case_dir / "replay" / "bundle.json"
        if p.exists():
            kp = json.loads(p.read_text(encoding="utf-8")).get("knowledge_package", {})
            review_status = (kp.get("expert_review") or {}).get("status", "pending")
    title = manifest.get("title", case_id)
    if derived_from:
        title = f"{title} (upload)"
    out = {
        "case_id": case_id,
        "title": title,
        "modality": modality,
        "hero": hero,
        "runtime_label": runtime_label,
        "review_status": review_status,
        "built": built,
    }
    if derived_from:
        out["derived_from"] = derived_from
    return out


def upload_cases_root(data_dir: Path) -> Path:
    return Path(data_dir) / "cases"


def _summary_composed(case_dir: Path) -> dict:
    """Summary entry for a composed (universal) case."""
    manifest = _read_manifest(case_dir)
    case_id = manifest.get("case_id", case_dir.name)
    title = manifest.get("title", case_id)
    review_status = "pending"
    built = False
    structures: List[str] = []

    # Try to read profile
    profile_files = sorted(case_dir.glob("knowledge/case_profile.v*.json"))
    if profile_files:
        try:
            from tracks.common.profile import CaseProfile
            profile = CaseProfile.model_validate(
                json.loads(profile_files[-1].read_text(encoding="utf-8"))
            )
            title = profile.title
            structures = list(profile.skill_model.structures)
            built = profile.confirmed_by_user
            review_status = "pending"
        except Exception:
            pass

    return {
        "case_id": case_id,
        "title": title,
        "modality": "universal",
        "hero": False,
        "runtime_label": "UPLOAD",
        "composed": True,
        "structures": structures,
        "review_status": review_status,
        "built": built,
    }


def list_cases(cases_root: Path, data_dir: Path) -> List[dict]:
    """Hero cases, then derived upload cases (hero-derived + composed), then SYNTHETIC showcase cases."""
    cases_root, data_dir = Path(cases_root), Path(data_dir)
    out: List[dict] = []
    for cid in config.HERO_CASES:
        if (cases_root / cid / "manifest.json").exists():
            out.append(_summary(cases_root / cid, hero=True))
    up = upload_cases_root(data_dir)
    if up.exists():
        for d in sorted(p for p in up.iterdir() if p.is_dir() and config.DERIVED_SEP in p.name):
            if (d / "manifest.json").exists():
                # Hero-derived (e.g. kolam~sha12)
                if config.modality_for(d.name):
                    out.append(_summary(d, hero=False, derived_from=config.base_case_id(d.name)))
                # Composed universal cases (have a case_profile)
                elif list(d.glob("knowledge/case_profile.v*.json")):
                    out.append(_summary_composed(d))
    index_path = cases_root / "index.json"
    indexed = json.loads(index_path.read_text(encoding="utf-8")).get("cases", []) if index_path.exists() else []
    for cid in indexed:
        if cid in config.SHOWCASE_CASES and (cases_root / cid / "manifest.json").exists():
            out.append(_summary(cases_root / cid, hero=False))
    return out


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def _select_source(sources: SourceRegistry, source_id: Optional[str]) -> SourceRecord:
    try:
        src = sources.get(source_id) if source_id else sources.primary()
    except KeyError as exc:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"source {source_id or '(primary)'} not found") from exc
    if not src.used_by_system or src.role in ("held_out_reference", "learner_attempt"):
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"source {src.source_id} is not a system source ({src.role})")
    if src.access_level == "research_only":
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"source {src.source_id} is research_only")
    return src


def build_case(case_dir: Path, ctx: RunContext, source_id: Optional[str] = None) -> CaseHandoff:
    """Run the modality goal builder and write the NEXT version of all six artifacts (PENDING).

    For modality 'universal': loads the latest knowledge/case_profile.v*.json and passes it
    as ``profile=`` to the builder (using inspect.signature so other builders are unaffected).
    """
    import inspect
    from tracks.common.media import sha256_file

    case_dir = Path(case_dir)
    manifest = _read_manifest(case_dir)
    case_id = manifest.get("case_id", case_dir.name)
    modality = config.modality_for(case_id, case_dir)
    if modality is None:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"{case_id} is a SYNTHETIC showcase case; it has no goal builder")
    try:
        sources = load_sources(case_dir)
    except FileNotFoundError as exc:
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"{case_id}: no source/source.json") from exc
    source = _select_source(sources, source_id)
    try:
        path = resolve_media(case_dir, source)
    except FileNotFoundError as exc:
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, str(exc), {"source_id": source.source_id}) from exc
    digest = sha256_file(path)
    if digest != source.sha256:
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT,
            f"sha256 mismatch for {source.source_id}",
            {"expected": source.sha256, "actual": digest, "path": str(path)},
        )
    try:
        builder = goal_builders.get_builder(modality)
    except (ImportError, AttributeError, KeyError) as exc:
        raise AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, f"goal builder for {modality} unavailable: {exc}") from exc

    version = authoring.next_version(case_dir)

    # For universal modality: load the latest case profile and pass it to the builder
    extra_kwargs: dict = {}
    if modality == "universal":
        from tracks.common.casedata import latest_version, versioned_path
        from tracks.common.profile import CaseProfile
        kn_dir = case_dir / "knowledge"
        profile_version = latest_version(kn_dir, "case_profile")
        if profile_version is None:
            raise AnveshanFailure(
                FailureCategory.MISSING_EVIDENCE,
                f"{case_id}: no knowledge/case_profile.v*.json found; run the composer first",
            )
        profile_path = versioned_path(kn_dir, "case_profile", profile_version)
        try:
            profile = CaseProfile.model_validate_json(profile_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise AnveshanFailure(
                FailureCategory.CONTRACT_VIOLATION,
                f"{case_id}: invalid case_profile.v{profile_version}.json: {exc}",
            ) from exc
        # Only pass profile= if the builder accepts it (use inspect.signature for safety)
        sig = inspect.signature(builder)
        if "profile" in sig.parameters:
            extra_kwargs["profile"] = profile

    result = builder(path, source, ctx, case_id=case_id, version=version, **extra_kwargs)
    authored = authoring.author_case(
        case_dir,
        case_id=case_id,
        manifest=manifest,
        sources=sources,
        source=source,
        result=result,
        modality=modality,
        version=version,
    )
    handoff = _load_built(case_dir, manifest, version, [])
    handoff.warnings = list(dict.fromkeys(handoff.warnings + authored.warnings))
    return handoff


# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------


def _ext_for(file_path: Path, mime: str) -> str:
    ext = file_path.suffix.lower()
    if ext and len(ext) <= 6 and ext[1:].isalnum():
        return ext
    return mimetypes.guess_extension(mime) or ".bin"


def create_upload_case(cases_root: Path, data_dir: Path, base_case_id: str, file_path: Path, mime: str) -> Path:
    """Create ``<data_dir>/cases/<base>~<sha12>/`` with a copied manifest and an UPLOAD source."""
    from tracks.common.media import sha256_file

    cases_root, data_dir, file_path = Path(cases_root), Path(data_dir), Path(file_path)
    base = config.base_case_id(base_case_id)
    modality = config.modality_for(base)
    if modality is None:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"{base_case_id} does not accept source uploads")
    mime = (mime or "").split(";", 1)[0].strip().lower()
    prefix = config.UPLOAD_MIME_PREFIX[modality]
    if not mime.startswith(prefix):
        raise AnveshanFailure(
            FailureCategory.INVALID_INPUT, f"{base} expects {prefix}* media, got {mime or 'no mime type'}", {"mime": mime}
        )
    if not file_path.is_file():
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"upload file not found: {file_path}")
    size = file_path.stat().st_size
    if size == 0:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, "upload is empty")
    limit = config.max_upload_bytes()
    if size > limit:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"upload is {size} bytes; limit is {limit}", {"bytes": size})
    base_manifest_path = cases_root / base / "manifest.json"
    if not base_manifest_path.exists():
        raise AnveshanFailure(FailureCategory.MISSING_EVIDENCE, f"base case {base} not found under {cases_root}")

    digest = sha256_file(file_path)
    sha12 = digest[:12]
    case_id = f"{base}{config.DERIVED_SEP}{sha12}"
    case_dir = upload_cases_root(data_dir) / case_id
    rel = f"source/upload.{sha12}{_ext_for(file_path, mime)}"
    if (case_dir / "source" / "source.json").exists() and (case_dir / "manifest.json").exists():
        return case_dir  # same content -> same derived case (idempotent)

    (case_dir / "source").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(file_path, case_dir / rel)

    duration, dims = None, None
    try:
        if modality == "kolam_image":
            from PIL import Image

            with Image.open(case_dir / rel) as im:
                dims = [int(im.width), int(im.height)]
        else:
            from tracks.common.media import probe

            info = probe(case_dir / rel)
            duration = info.duration_sec
            if info.width and info.height:
                dims = [int(info.width), int(info.height)]
    except Exception as exc:  # unreadable media: reject rather than register an unusable source
        shutil.rmtree(case_dir, ignore_errors=True)
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"upload is not readable {prefix}* media: {exc}") from exc

    manifest = json.loads(base_manifest_path.read_text(encoding="utf-8"))
    manifest["case_id"] = case_id
    manifest["source_media"] = {"type": "local_file", "path": rel, "mime_type": mime, "attribution": "user upload"}
    record = SourceRecord(
        source_id=f"src.{base}.upload.{sha12}",
        role=config.UPLOAD_ROLE[modality],
        mime_type=mime,
        sha256=digest,
        bytes=size,
        path=rel,
        duration_sec=duration,
        dimensions=dims,
        creator=config.UPLOAD_CREATOR,
        license=config.UPLOAD_LICENSE,
        attribution="Uploaded by the user; rights asserted by the uploader.",
        access_level="approved_learners",
        runtime_label="UPLOAD",
        used_by_system=True,
        notes=f"Derived upload case of {base}.",
    )
    write_json(case_dir / "source" / "source.json", SourceRegistry(case_id=case_id, sources=[record]))
    write_json(case_dir / "manifest.json", manifest)
    return case_dir


# ---------------------------------------------------------------------------
# Query and review
# ---------------------------------------------------------------------------


def answer_query(case_dir: Path, question: str, ctx: RunContext) -> dict:
    """{answer, cited_claim_ids, evidence: [EvidenceRef], sufficient, run}"""
    h = load_case(Path(case_dir))
    goal_conditioned = (h.modality in config.GOAL_CONDITIONED_MODALITIES) or (
        h.manifest.get("transmission_mode") == "goal-conditioned"
    )
    return query.answer(
        h.package,
        question,
        ctx,
        case_title=h.manifest.get("title", h.case_id),
        transmission_mode=h.manifest.get("transmission_mode", "forward"),
        goal_conditioned=goal_conditioned,
    )


def apply_review(case_dir: Path, action: dict) -> CaseHandoff:
    """approve | revise_claim | reject_claim | reject_package -> package v(N+1); returns that version."""
    case_dir = Path(case_dir)
    manifest = _read_manifest(case_dir)
    case_id = manifest.get("case_id", case_dir.name)
    if config.modality_for(case_id, case_dir) is None:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"{case_id} is a SYNTHETIC showcase case; not reviewable")
    if not isinstance(action, dict):
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, "review action must be an object")
    new_v = review.apply(case_dir, case_id, action)
    status_warnings: List[str] = []
    if action.get("action") == "reject_package":
        status_warnings.append("package rejected by expert review; rebuild required")
    return _load_built(case_dir, manifest, new_v, status_warnings)
