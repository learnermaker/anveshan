"""Case profile for composed (user-uploaded, entirely new) skills — case data, NOT a contract.

Stored at <case_dir>/knowledge/case_profile.v{N}.json. See docs/plans/case-composer.md §5.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

Family = Literal["image_target", "video_states", "audio_rhythm", "rubric_vlm"]
LearnerKind = Literal["trace", "image", "audio", "video"]

FAMILY_MODALITY: Dict[str, str] = {
    "image_target": "kolam_image",
    "video_states": "origami_video",
    "audio_rhythm": "tabla_audio",
    "rubric_vlm": "rubric_vlm",
}

FAMILY_LABEL: Dict[str, str] = {
    "image_target": "Final-image line drawing (goal-trajectory)",
    "video_states": "Sequential procedure from video (state trajectory)",
    "audio_rhythm": "Percussive rhythm from audio (onset alignment)",
    "rubric_vlm": "General rubric review (lower confidence)",
}

FAMILY_INPUT_KINDS: Dict[str, List[str]] = {
    "image_target": ["trace", "image"],
    "video_states": ["video"],
    "audio_rhythm": ["audio"],
    "rubric_vlm": ["image", "video", "audio"],
}

_ID_RE = re.compile(r"^[a-z0-9-]+~[0-9a-f]{12}$")


class CriterionSuggestion(BaseModel):
    criterion_id: str
    name: str
    observable_indicator: str
    weight: float = Field(default=2.0, ge=1.0, le=5.0)
    required: bool = False
    method: Literal["engine_default", "vlm_status"] = "engine_default"


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
    allowed_families: List[Family]
    family_reasons: Dict[str, str] = Field(default_factory=dict)


class CaseProfile(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    case_id: str
    title: str
    skill_summary: str
    domain: str
    family: Family
    transmission_mode: Literal["forward", "goal-conditioned", "corrective"]
    learner_input_kinds: List[LearnerKind]
    vocabulary: Dict[str, str] = Field(default_factory=dict)
    goal_hint: Optional[str] = None
    criteria: List[CriterionSuggestion] = Field(default_factory=list)
    probe: ProbeFacts
    model_proposal: Dict = Field(default_factory=dict)
    model_run_keys: List[str] = Field(default_factory=list)
    confirmed_by_user: bool = False
    confirmed_at: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check(self) -> "CaseProfile":
        if not _ID_RE.match(self.case_id):
            raise ValueError(f"case_id {self.case_id!r} must look like '<slug>~<sha12>'")
        if self.family not in self.probe.allowed_families:
            raise ValueError(f"family {self.family} not in allowed_families {self.probe.allowed_families}")
        bad = [k for k in self.learner_input_kinds if k not in FAMILY_INPUT_KINDS[self.family]]
        if bad:
            raise ValueError(f"learner_input_kinds {bad} not accepted by family {self.family}")
        ids = [c.criterion_id for c in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate criterion ids in profile")
        return self

    @property
    def modality(self) -> str:
        return FAMILY_MODALITY[self.family]


def slugify(title: str, max_len: int = 32) -> str:
    """Deterministic ASCII slug; 'skill' when nothing usable remains."""
    s = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:max_len].strip("-")
    return s or "skill"


def composed_case_id(title: str, sha256: str) -> str:
    return f"{slugify(title)}~{sha256[:12].lower()}"
