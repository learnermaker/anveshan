"""Layer 2 — SkillModel: the common knowledge structure (GoalModel payload for modality "universal").

Case data, NOT a contract. Built deterministically from PerceptionRecord(s) + user intent;
mapped onto the 8 frozen contracts (claims, rubric, observers, criterion map) by Track A.
See docs/plans/universal-pipeline.md §5.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

Structure = Literal["final_state", "procedure", "temporal_pattern", "utterance"]
Certainty = Literal["observed", "inferred", "unverified"]
CheckKind = Literal[
    "final_similarity", "final_property",
    "step_coverage", "step_order", "off_path", "step_quality",
    "line_art", "rhythm",
    "utterance_match", "pace_match",
]
CheckMethod = Literal["deterministic", "model_status", "specialist"]

# Which check kinds belong to which structure (validation + UI grouping).
STRUCTURE_CHECKS: Dict[str, List[str]] = {
    "final_state": ["final_similarity", "final_property", "line_art"],
    "procedure": ["step_coverage", "step_order", "off_path", "step_quality", "final_property", "final_similarity"],
    "temporal_pattern": ["rhythm"],
    "utterance": ["utterance_match", "pace_match"],
}

# Learner attempt kinds accepted per structure (applicability matrix §6.1; trace needs line_art).
STRUCTURE_ATTEMPT_KINDS: Dict[str, List[str]] = {
    "final_state": ["image", "video", "trace"],
    "procedure": ["video", "image"],
    "temporal_pattern": ["audio", "video"],
    "utterance": ["audio", "video"],
}


class TargetProperty(BaseModel):
    prop_id: str                       # "prop-01"
    statement: str
    region: Optional[List[float]] = None   # [x,y,w,h] percent on the goal image/keyframe
    evidence: List[str] = Field(default_factory=list)   # obs_ids in the source PerceptionRecord
    certainty: Certainty
    keep: bool = True                  # user may drop it in the composer


class Step(BaseModel):
    step_id: str                       # "step-01"
    index: int
    name: str
    state_after: str
    action: Optional[str] = None
    start_sec: Optional[float] = None
    end_sec: Optional[float] = None
    keyframe_asset: Optional[str] = None
    segment_id: Optional[str] = None   # source perception segment
    evidence: List[str] = Field(default_factory=list)
    certainty: Certainty
    source_established: bool           # True only when demonstrated in the source (video)
    critical: bool = False


class Constraint(BaseModel):
    constraint_id: str                 # "con-01"
    statement: str
    evidence: List[str] = Field(default_factory=list)
    certainty: Certainty
    keep: bool = True


class Relevance(BaseModel):
    expected_kinds: List[str]
    min_similarity: float = 0.72       # attempt-vs-source embedding cosine gate
    ambiguous_band: float = 0.08       # [min, min+band) -> model yes/no relevance check
    reference_segment_ids: List[str] = Field(default_factory=list)


class Check(BaseModel):
    check_id: str                      # "CHK-01" (becomes the criterion id suffix)
    kind: CheckKind
    name: str
    observable_indicator: str
    targets: List[str] = Field(default_factory=list)   # prop/step/constraint ids
    metric_id: str                     # e.g. "u.final_property.prop-02", "u.step_order", "line_art:kolam.coverage"
    method: CheckMethod
    params: Dict[str, Any] = Field(default_factory=dict)
    weight: float = Field(default=2.0, ge=1.0, le=5.0)
    required: bool = False
    process: bool = False              # needs process evidence (UNCERTAIN for final-only attempts)
    enabled: bool = True


class SkillModel(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    skill_title: str
    summary: str
    source_modality: Literal["image", "video", "audio"]
    structures: List[Structure] = Field(min_length=1)
    goal_state: List[TargetProperty] = Field(default_factory=list)
    steps: List[Step] = Field(default_factory=list)
    order: Literal["strict", "partial", "none"] = "none"
    constraints: List[Constraint] = Field(default_factory=list)
    temporal: Optional[Dict[str, Any]] = None
    utterance: Optional[Dict[str, Any]] = None
    specialists: Dict[str, Any] = Field(default_factory=dict)   # line_art / rhythm / procedure_states payloads
    relevance: Relevance
    checks: List[Check] = Field(min_length=1)
    perception_file: Optional[str] = None                        # knowledge/perception_source.vN.json
    vocabulary: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _consistency(self) -> "SkillModel":
        ids = [c.check_id for c in self.checks]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate check ids")
        allowed = {k for s in self.structures for k in STRUCTURE_CHECKS[s]}
        for c in self.checks:
            if c.kind not in allowed:
                raise ValueError(f"{c.check_id}: kind {c.kind} not valid for structures {self.structures}")
            if c.kind == "line_art" and "line_art" not in self.specialists:
                raise ValueError(f"{c.check_id}: line_art check needs the line_art specialist payload")
            if c.kind == "rhythm" and "rhythm" not in self.specialists:
                raise ValueError(f"{c.check_id}: rhythm check needs the rhythm specialist payload")
        if self.order != "none" and not any(s.source_established for s in self.steps):
            raise ValueError("order strict/partial requires source-established steps")
        known = {p.prop_id for p in self.goal_state} | {s.step_id for s in self.steps} | {c.constraint_id for c in self.constraints}
        for c in self.checks:
            missing = [t for t in c.targets if t not in known]
            if missing:
                raise ValueError(f"{c.check_id}: unknown targets {missing}")
        return self


PAYLOAD_MODEL = SkillModel
