"""Goal builders: final-state / demonstration source -> GoalModel + grounded claims + criterion templates.

Each modality module exposes::

    def build(source_path: Path, source: SourceRecord, ctx: RunContext, *,
              case_id: str, version: int) -> GoalBuildResult

Builders must be deterministic given the same source and recorded model runs.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List

from tracks.common.casedata import ObserverBinding
from tracks.common.schemas import KnowledgeClaim, TaskConstraint

BUILDERS: Dict[str, str] = {
    "kolam_image": "track_a.goals.kolam:build",
    "origami_video": "track_a.goals.origami:build",
    "tabla_audio": "track_a.goals.tabla:build",
    "rubric_vlm": "track_a.goals.rubric_vlm:build",  # K7
}


@dataclass
class CriterionTemplate:
    criterion_id: str
    name: str
    description: str
    observable_indicator: str
    weight: float
    required: bool
    order_index: int
    source_claim_ids: List[str]
    reference_evidence_ids: List[str]
    why_it_matters: str          # must cite one of source_claim_ids, e.g. "... (CLM-03)"
    drill_hint: str
    observer: ObserverBinding    # default binding written to practice/observers.vN.json


@dataclass
class GoalBuildResult:
    title: str
    summary: str
    goal_payload: Dict[str, Any]           # validated against tracks.common.goals.<modality>.PAYLOAD_MODEL
    claims: List[KnowledgeClaim]           # final ids CLM-01.., deterministic order, locators per spec
    criteria: List[CriterionTemplate]
    task_title: str
    task_instructions: str                 # numbered, cites [CLM-xx]
    task_constraints: List[TaskConstraint]
    warnings: List[str] = field(default_factory=list)
    run_keys: List[str] = field(default_factory=list)   # replay keys of model runs used
    built_with: Dict[str, Any] = field(default_factory=dict)


def get_builder(modality: str) -> Callable[..., GoalBuildResult]:
    mod_name, fn = BUILDERS[modality].split(":")
    return getattr(importlib.import_module(mod_name), fn)
