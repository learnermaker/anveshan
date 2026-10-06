"""Intake screen: combine safety + teachability results from a PerceptionRecord.

This is deterministic logic over the perception results; no new model calls.
See docs/plans/universal-pipeline.md §4.
"""

from __future__ import annotations

import logging
import warnings as _warnings
from typing import Any, Dict, List, Optional

from tracks.common.perception import PerceptionRecord
from tracks.common.policy import safety_decision
from tracks.common.profile import IntakeResult

log = logging.getLogger(__name__)

# Deterministic override thresholds
_BLANK_CONTRAST = 0.03
_BLANK_INK = 0.002
_SILENCE_RMS = 0.005
_STATIC_ACTIVE_FRAC = 0.05


def _measurements(record: PerceptionRecord) -> Dict[str, Any]:
    """Return measurement observation values from seg-000."""
    result: Dict[str, Any] = {}
    for obs in record.observations:
        if obs.segment_id == "seg-000" and obs.kind == "measurement":
            result[obs.label] = obs.value
    return result


def intake_from_perception(record: PerceptionRecord) -> IntakeResult:
    """Build an IntakeResult from a source PerceptionRecord (after perceive(..., purpose='source')).

    Combines the model-reported safety/teachability (stored in record.gates["intake"]) with
    deterministic overrides for blank images, silence, and near-static video.
    """
    gate = record.gates.get("intake", {})
    safety_categories: List[str] = gate.get("safety_categories", ["none"])
    teachable: str = gate.get("teachable", "unclear")
    teachable_reason: str = gate.get("teachable_reason", "")
    skill_kind: Optional[str] = gate.get("skill_kind")

    # Deterministic overrides —————————————————————————————————————————————
    m = _measurements(record)
    modality = record.media.modality

    if modality == "image":
        contrast = m.get("rms_contrast", 1.0)
        ink_fraction = m.get("ink_fraction", 1.0)
        if contrast is not None and ink_fraction is not None:
            if float(contrast) < _BLANK_CONTRAST or float(ink_fraction) < _BLANK_INK:
                teachable = "no"
                teachable_reason = "blank or near-blank image"

    elif modality == "audio":
        rms = m.get("rms", 1.0)
        if rms is not None and float(rms) < _SILENCE_RMS:
            teachable = "no"
            teachable_reason = "silence"

    elif modality == "video":
        active_frac = m.get("active_fraction", 1.0)
        seg_count = m.get("segment_count", 2.0)
        if active_frac is not None and seg_count is not None:
            if float(active_frac) < _STATIC_ACTIVE_FRAC and float(seg_count) <= 1:
                if teachable != "no":  # only override to unclear, not refuse
                    teachable = "unclear"
                    teachable_reason = "nothing visibly changes"

    # If model gate was absent (call failed or disabled)
    if not gate:
        teachable = "unclear"
        teachable_reason = "AI screen unavailable"
        safety_categories = ["none"]

    safety = safety_decision(safety_categories)
    return IntakeResult(
        safety=safety,
        teachable=teachable,
        teachable_reason=teachable_reason,
        skill_kind=skill_kind,
    )
