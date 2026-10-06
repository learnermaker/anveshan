"""Track A configuration: case -> modality map, confidence policy, grounding/query phrase lists.

These are documented policies, not calibration claims (docs/plans/track-a-spec.md §4.3).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Tuple

TRACK_A_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = TRACK_A_ROOT / "prompts"

# Hero cases run a modality goal builder. The shared manifest schema has no modality
# field, so the mapping lives here. Derived upload cases ``<base>~<sha12>`` inherit.
HERO_CASES: Dict[str, str] = {
    "kolam": "kolam_image",
    "origami": "origami_video",
    "tabla": "tabla_audio",
}

# Showcase cases: SYNTHETIC replay bundles only (no goal model, no builder).
SHOWCASE_CASES: Tuple[str, ...] = ("micrometer", "bicycle-repair", "handloom-weaving", "square-knot")

# Goal-conditioned modalities (final state only; no source-established process).
GOAL_CONDITIONED_MODALITIES = frozenset({"kolam_image"})

DERIVED_SEP = "~"

# Upload rules per modality.
UPLOAD_MIME_PREFIX: Dict[str, str] = {
    "kolam_image": "image/",
    "origami_video": "video/",
    "tabla_audio": "audio/",
}
UPLOAD_ROLE: Dict[str, str] = {
    "kolam_image": "target_image",
    "origami_video": "expert_video",
    "tabla_audio": "expert_audio",
}
UPLOAD_LICENSE = "user upload — rights asserted by uploader"
UPLOAD_CREATOR = "uploader"
DEFAULT_MAX_UPLOAD_MB = 50.0

# Confidence / observation policy (track-a-spec §4.3).
CONFIDENCE_POLICY: Dict[str, float] = {
    "observed_with_locator": 0.8,
    "partial": 0.5,
    "unknown": 0.3,
    "candidate_step": 0.4,
    "deterministic_from_artifact": 1.0,
}
INFERRED_STEP_MAX_CONFIDENCE = 0.5

# Passing score default: fraction of the rubric's max possible score.
DEFAULT_PASSING_FRACTION = 0.7

# Tolerance (seconds) when checking audio/video locators against the source duration.
DURATION_EPS_SEC = 0.05

# Creator-intent / history / meaning phrases that must never appear as claims (§5.5).
# A hit raises UNSUPPORTED_CLAIM. Phrased as assertions so that statements of what is
# *unknown* ("the original order is not established") do not trip them.
CREATOR_INTENT_PATTERNS: List[str] = [
    r"\bthe (artist|creator|author|drawer|maker|expert|performer)('s)? (intended|intention|meant|wanted|chose|was trying)\b",
    r"\b(intended|meant) to (represent|symboli[sz]e|express|convey|honou?r)\b",
    r"\boriginally (drawn|made|created|performed|folded|composed|played)\b",
    r"\bwas (first )?drawn (by|in|for|during)\b",
    r"\bsymboli[sz]es\b",
    r"\b(is|was) traditionally (drawn|made|performed|played) (to|for|during|on)\b",
    r"\bthe original (stroke )?order (was|is) (to|from|that|clockwise|anticlockwise|counter-?clockwise)\b",
]

# Query pre-check for goal-conditioned cases: questions the final state can never answer.
GOAL_CONDITIONED_UNANSWERABLE_PATTERNS: List[str] = [
    r"\bintend(ed|s|ing)?\b|\bintention\b|\bintent\b",
    r"\bwhy did (the )?(artist|creator|author|drawer|maker|she|he|they)\b",
    r"\bhistor(y|ical|ically)\b|\borigin(s|ated)?\b",
    r"\bmean(ing|s)?\b|\bsymbol(ic|ism|ise|ize|izes|ises)?\b|\bsignifican(ce|t)\b",
    r"\btradition(al|ally)?\b|\bcultur(e|al)\b|\britual\b|\bfestival\b",
    r"\boriginal(ly)? (stroke )?(order|sequence|direction)\b|\b(stroke|drawing) order\b|\bin what order\b|\bwhich order\b",
    r"\bwho (drew|made|created|designed|invented)\b",
]


def _compile(patterns: List[str]) -> List[Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


CREATOR_INTENT_RE = _compile(CREATOR_INTENT_PATTERNS)
UNANSWERABLE_RE = _compile(GOAL_CONDITIONED_UNANSWERABLE_PATTERNS)


def base_case_id(case_id: str) -> str:
    return case_id.split(DERIVED_SEP, 1)[0]


def is_derived(case_id: str) -> bool:
    return DERIVED_SEP in case_id


def modality_for(case_id: str) -> Optional[str]:
    """Goal modality for a hero case or a derived upload case; None for showcase cases."""
    return HERO_CASES.get(base_case_id(case_id))


def max_upload_bytes() -> int:
    raw = os.environ.get("ANVESHAN_MAX_UPLOAD_MB", "").split("#", 1)[0].strip()
    try:
        mb = float(raw) if raw else DEFAULT_MAX_UPLOAD_MB
    except ValueError:
        mb = DEFAULT_MAX_UPLOAD_MB
    return int(mb * 1024 * 1024)
