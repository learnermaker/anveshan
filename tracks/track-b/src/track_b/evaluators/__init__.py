"""Modality trajectory evaluators.

Each module exposes::

    def evaluate(goal: GoalModel, attempt: AttemptMedia, ctx: RunContext) -> TrajectoryResult

Metric ids must match the ``metric`` names used in practice/observers.vN.json.
"""

from __future__ import annotations

import importlib
from typing import Callable, Dict

EVALUATORS: Dict[str, str] = {
    "kolam_image": "track_b.evaluators.kolam:evaluate",
    "origami_video": "track_b.evaluators.origami:evaluate",
    "tabla_audio": "track_b.evaluators.tabla:evaluate",
    "rubric_vlm": "track_b.evaluators.rubric_vlm:evaluate",  # K7
}


def get_evaluator(modality: str) -> Callable:
    mod_name, fn = EVALUATORS[modality].split(":")
    return getattr(importlib.import_module(mod_name), fn)
