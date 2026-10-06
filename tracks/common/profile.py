"""Case profile (v2) for composed skills — case data, NOT a contract.

A composed case is produced by the universal pipeline (docs/plans/universal-pipeline.md):
intake gates -> perception -> proposed SkillModel -> user confirmation. The profile stores the
probe facts, gate results, the (editable) SkillModel proposal and the confirmation.
Stored at <case_dir>/knowledge/case_profile.v{N}.json. Composed cases use goal modality "universal".
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from tracks.common.skill_model import STRUCTURE_ATTEMPT_KINDS, SkillModel, Structure

LearnerKind = Literal["trace", "image", "audio", "video"]
COMPOSED_MODALITY = "universal"

STRUCTURE_LABEL: Dict[str, str] = {
    "final_state": "Reproduce a finished result (final state)",
    "procedure": "Follow a sequence of steps (procedure)",
    "temporal_pattern": "Reproduce a rhythm or timing pattern",
    "utterance": "Reproduce a spoken phrase",
}

SPECIALIST_LABEL: Dict[str, str] = {
    "line_art": "Line-drawing geometry (precise coverage, stray lines, dots, continuity)",
    "rhythm": "Rhythm analysis (tempo, timing, bass and stroke types)",
    "procedure_states": "Procedure state tracking (ordered states with keyframes)",
}

_ID_RE = re.compile(r"^[a-z0-9-]+~[0-9a-f]{12}$")


class ProbeFacts(BaseModel):
    modality: Literal["image", "video", "audio"]
    mime_type: str
    bytes: int
    sha256: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration_sec: Optional[float] = None
    has_audio: Optional[bool] = None
    metrics: Dict[str, float] = Field(default_factory=dict)
    structures_available: List[Structure]
    specialists_available: List[str] = Field(default_factory=list)
    reasons: Dict[str, str] = Field(default_factory=dict)   # per structure/specialist: why available or not


class IntakeResult(BaseModel):
    safety: Dict[str, Any]                 # tracks.common.policy.safety_decision(...) output
    teachable: Literal["yes", "no", "unclear"]
    teachable_reason: str = ""
    skill_kind: Optional[str] = None       # model's description of what kind of skill (INFERRED)


class CaseProfile(BaseModel):
    schema_version: Literal["2.0"] = "2.0"
    case_id: str
    title: str
    skill_summary: str
    domain: str
    transmission_mode: Literal["forward", "goal-conditioned", "corrective"]
    learner_input_kinds: List[LearnerKind]
    vocabulary: Dict[str, str] = Field(default_factory=dict)
    goal_hint: Optional[str] = None
    probe: ProbeFacts
    intake: IntakeResult
    skill_model: SkillModel
    perception_file: Optional[str] = None  # path (relative to case dir or draft dir) of the source PerceptionRecord
    model_proposal: Dict[str, Any] = Field(default_factory=dict)
    model_run_keys: List[str] = Field(default_factory=list)
    confirmed_by_user: bool = False
    confirmed_at: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "CaseProfile":
        if not _ID_RE.match(self.case_id):
            raise ValueError(f"case_id {self.case_id!r} must look like '<slug>~<sha12>'")
        if self.intake.safety.get("decision") == "refuse":
            raise ValueError("source refused by the safety gate")
        if self.intake.teachable == "no":
            raise ValueError("source refused by the teachability gate")
        bad_struct = [s for s in self.skill_model.structures if s not in self.probe.structures_available]
        if bad_struct:
            raise ValueError(f"structures {bad_struct} not available for this source")
        allowed: set = set()
        for s in self.skill_model.structures:
            allowed.update(STRUCTURE_ATTEMPT_KINDS[s])
        if "line_art" not in self.skill_model.specialists:
            allowed.discard("trace")
        bad = [k for k in self.learner_input_kinds if k not in allowed]
        if bad:
            raise ValueError(f"learner_input_kinds {bad} not accepted for structures {self.skill_model.structures}")
        if not self.learner_input_kinds:
            raise ValueError("at least one learner input kind is required")
        return self

    @property
    def modality(self) -> str:
        return COMPOSED_MODALITY


def slugify(title: str, max_len: int = 32) -> str:
    """Deterministic ASCII slug; 'skill' when nothing usable remains."""
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:max_len].strip("-")
    return s or "skill"


def composed_case_id(title: str, sha256: str) -> str:
    return f"{slugify(title)}~{sha256[:12].lower()}"
