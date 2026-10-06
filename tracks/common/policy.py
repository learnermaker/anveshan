"""Intake safety/teachability policy (versioned). See docs/plans/universal-pipeline.md §4."""

from __future__ import annotations

from typing import Dict, List

POLICY_VERSION = "policy_v1"

# Categories that are refused outright when the perception screen reports them.
REFUSE_CATEGORIES: Dict[str, str] = {
    "weapons": "making or using weapons or explosives",
    "self_harm": "self-harm",
    "medical_procedure": "medical or invasive procedures",
    "sexual_content": "sexual content",
    "illegal_activity": "illegal activity",
    "hazardous_work": "dangerous chemical, electrical or high-risk physical work",
}

# Categories that are allowed with a notice.
FLAG_CATEGORIES: Dict[str, str] = {
    "identifiable_faces": "identifiable people are visible; only upload media you have the right to use",
    "minors_visible": "children may be visible; make sure you have permission",
}

TEACHABILITY_VALUES: List[str] = ["yes", "no", "unclear"]

REFUSE_TEACHABILITY_MESSAGE = (
    "We couldn't find a learnable, observable skill in this file: {reason}. "
    "Try a video of someone doing it, a clear photo of a finished piece, or a recording of the sound to reproduce."
)


def safety_decision(categories: List[str]) -> Dict[str, object]:
    """Deterministic decision from screen categories reported by perception."""
    refuse = [c for c in categories if c in REFUSE_CATEGORIES]
    flags = [c for c in categories if c in FLAG_CATEGORIES]
    unknown = [c for c in categories if c not in REFUSE_CATEGORIES and c not in FLAG_CATEGORIES and c != "none"]
    if refuse:
        return {"decision": "refuse", "reasons": [REFUSE_CATEGORIES[c] for c in refuse], "policy": POLICY_VERSION}
    return {
        "decision": "flag" if flags else "ok",
        "notices": [FLAG_CATEGORIES[c] for c in flags],
        "ignored_categories": unknown,
        "policy": POLICY_VERSION,
    }
