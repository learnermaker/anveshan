"""Track A: Expert Intelligence & Grounding.

Exports public symbols for models, registry, gateway, services, and pipeline.
"""

from .models import (
    FailureCategory,
    TrackAFailure,
    ExtractedStepDTO,
    ExtractedCueDTO,
    ExtractedConditionDTO,
    ExtractedExceptionDTO,
    ExtractedFailureModeDTO,
    ExtractedTargetPropertyDTO,
    ExtractedDivergenceDTO,
    RunMetadataDTO,
    ExtractionResponseDTO,
    normalize_dto_to_knowledge_package,
    generate_package_id,
    generate_rubric_id,
    generate_task_id,
    generate_evidence_id,
)
from .case_registry import (
    CaseManifest,
    discover_cases,
    load_manifest,
    load_replay_bundle,
    validate_manifest_semantics,
)

__all__ = [
    "FailureCategory",
    "TrackAFailure",
    "ExtractedStepDTO",
    "ExtractedCueDTO",
    "ExtractedConditionDTO",
    "ExtractedExceptionDTO",
    "ExtractedFailureModeDTO",
    "ExtractedTargetPropertyDTO",
    "ExtractedDivergenceDTO",
    "RunMetadataDTO",
    "ExtractionResponseDTO",
    "normalize_dto_to_knowledge_package",
    "generate_package_id",
    "generate_rubric_id",
    "generate_task_id",
    "generate_evidence_id",
    "CaseManifest",
    "discover_cases",
    "load_manifest",
    "load_replay_bundle",
    "validate_manifest_semantics",
]
