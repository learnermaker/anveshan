"""Case-pack sidecar data models (case data, NOT one of the eight contracts).

Files under tracks/cases/<case_id>/:
  source/source.json                      SourceRegistry       (Track A)
  knowledge/goal_model.v{N}.json          GoalModel            (Track A)
  knowledge/knowledge_package.v{N}.json   KnowledgePackage     (Track A, common contract)
  knowledge/criterion_map.v{N}.json       CriterionMap         (Track A)
  practice/rubric.v{N}.json               RubricDefinition     (Track A, common contract)
  practice/practice_task.v{N}.json        PracticeTask         (Track A, common contract)
  practice/observers.v{N}.json            Observers            (Track B)
  runs/golden/<replay_key>/               recorded model runs  (either track)

See docs/plans/evaluation-core.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Type, TypeVar

from pydantic import BaseModel, Field, model_validator

M = TypeVar("M", bound=BaseModel)

GoalModality = Literal["kolam_image", "origami_video", "tabla_audio", "universal"]
RuntimeLabel = Literal["INTERNET_REFERENCE", "OWNED_CONSENTED", "SYNTHETIC", "UPLOAD"]
Status = Literal["satisfied", "partially_satisfied", "not_satisfied", "uncertain"]


class SourceRecord(BaseModel):
    source_id: str
    role: Literal["target_image", "expert_demonstration", "expert_audio", "expert_video", "held_out_reference", "learner_attempt"]
    mime_type: str
    sha256: str
    bytes: int
    path: Optional[str] = None        # repo-relative committed path, or cache path under media/cache/
    url: Optional[str] = None         # download URL for uncommitted media
    duration_sec: Optional[float] = None
    dimensions: Optional[List[int]] = None
    window_sec: Optional[List[float]] = None  # [start, end] of the skill segment within the media
    creator: str
    license: str
    attribution: str
    access_level: Literal["public", "approved_learners", "research_only"] = "public"
    runtime_label: RuntimeLabel
    used_by_system: bool = True       # False for held-out validation material
    notes: Optional[str] = None

    @model_validator(mode="after")
    def _where(self) -> "SourceRecord":
        if not self.path and not self.url:
            raise ValueError(f"source {self.source_id} needs a path or url")
        return self


class SourceRegistry(BaseModel):
    case_id: str
    sources: List[SourceRecord]

    def get(self, source_id: str) -> SourceRecord:
        for s in self.sources:
            if s.source_id == source_id:
                return s
        raise KeyError(source_id)

    def primary(self) -> SourceRecord:
        for s in self.sources:
            if s.used_by_system and s.role != "held_out_reference":
                return s
        raise KeyError(f"no primary source for {self.case_id}")


class GoalModel(BaseModel):
    """Envelope for a modality-specific goal model. ``payload`` schema per modality lives in
    tracks/common/goals/<modality>.py (KolamGoal, OrigamiGoal, TablaGoal)."""

    schema_version: str = "1.0"
    case_id: str
    version: int = Field(ge=1)
    modality: GoalModality
    source_ids: List[str]
    package_id: str
    built_with: Dict[str, Any] = Field(default_factory=dict)  # algorithm versions, params, run replay keys
    payload: Dict[str, Any]
    warnings: List[str] = Field(default_factory=list)


class CriterionMapEntry(BaseModel):
    order_index: int
    source_claim_ids: List[str] = Field(min_length=1)
    reference_evidence_ids: List[str] = Field(default_factory=list)
    why_it_matters: str
    drill_hint: str


class CriterionMap(BaseModel):
    rubric_id: str
    package_id: str
    criteria: Dict[str, CriterionMapEntry]

    @model_validator(mode="after")
    def _cites(self) -> "CriterionMap":
        for cid, e in self.criteria.items():
            if not any(c in e.why_it_matters for c in e.source_claim_ids):
                raise ValueError(f"{cid}: why_it_matters must cite one of {e.source_claim_ids}")
        return self


class Band(BaseModel):
    status: Status
    min: Optional[float] = None
    max: Optional[float] = None


class ObserverBinding(BaseModel):
    metric: str                                    # metric id produced by the modality evaluator
    direction: Literal["higher_is_better", "lower_is_better"]
    bands: List[Band] = Field(min_length=1)         # checked in order; first match wins
    otherwise: Status = "not_satisfied"
    process: bool = False                           # True = needs process evidence (UNCERTAIN for final-state-only inputs)


class Observers(BaseModel):
    rubric_id: str
    modality: GoalModality
    score_policy: Literal["score_policy_v1"] = "score_policy_v1"
    version: int = Field(ge=1)
    criteria: Dict[str, ObserverBinding]


# ---------------------------------------------------------------------------
# Versioned file helpers
# ---------------------------------------------------------------------------

_VER = re.compile(r"\.v(\d+)\.json$")


def versioned_path(directory: Path, stem: str, version: int) -> Path:
    return directory / f"{stem}.v{version}.json"


def latest_version(directory: Path, stem: str) -> Optional[int]:
    if not directory.exists():
        return None
    versions = [int(m.group(1)) for p in directory.glob(f"{stem}.v*.json") if (m := _VER.search(p.name))]
    return max(versions) if versions else None


def load_versioned(directory: Path, stem: str, model: Type[M], version: Optional[int] = None) -> M:
    v = version if version is not None else latest_version(directory, stem)
    if v is None:
        raise FileNotFoundError(f"no {stem}.v*.json in {directory}")
    return model.model_validate_json(versioned_path(directory, stem, v).read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    """Deterministic JSON (sorted keys, 2-space indent, trailing newline)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, BaseModel):
        data = data.model_dump(mode="json")
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_sources(case_dir: Path) -> SourceRegistry:
    return SourceRegistry.model_validate_json((case_dir / "source" / "source.json").read_text(encoding="utf-8"))


def resolve_media(case_dir: Path, record: SourceRecord) -> Path:
    """Local path for a source record (committed file or fetched cache). Raises if missing."""
    if record.path:
        p = (case_dir / record.path) if not Path(record.path).is_absolute() else Path(record.path)
        if p.exists():
            return p
    cache = case_dir / "media" / "cache"
    if cache.exists():
        for p in cache.iterdir():
            if p.stem == record.source_id or p.name.startswith(record.source_id + "."):
                return p
    raise FileNotFoundError(
        f"media for {record.source_id} not found; run `python tools/fetch_media.py {case_dir.name}`"
    )
