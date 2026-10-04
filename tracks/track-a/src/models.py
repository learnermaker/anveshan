from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from tracks.common.schemas import (
    ClaimType,
    ConsentMetadata,
    EvidenceRef,
    ExpertReview,
    KnowledgeClaim,
    KnowledgePackage,
    Modality,
    ReviewStatus,
    VerificationState,
)


# ---------------------------------------------------------------------------
# Spec 2: Standardized 9-Class Failure Taxonomy
# ---------------------------------------------------------------------------


class FailureCategory(str, Enum):
    """Standardized failure categories per tracks/common/CASE-DATA-CONVENTIONS.md."""

    INVALID_INPUT = "INVALID_INPUT"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    AMBIGUOUS_EVIDENCE = "AMBIGUOUS_EVIDENCE"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    MODEL_FAILURE = "MODEL_FAILURE"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    REPLAY_MISMATCH = "REPLAY_MISMATCH"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class TrackAFailure(Exception):
    """Exception class capturing structured failure details across Track A operations."""

    def __init__(
        self,
        category: FailureCategory,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(f"[{category.value}] {message}")
        self.category = category
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# Spec 1: Extraction DTOs & Run Metadata Spec
# ---------------------------------------------------------------------------


class ExtractedStepDTO(BaseModel):
    index: int = Field(..., ge=0)
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    start_sec: float = Field(..., ge=0.0)
    end_sec: float = Field(..., ge=0.0)


class ExtractedCueDTO(BaseModel):
    modality: str = Field(default="video")
    statement: str = Field(..., min_length=1)
    observable_indicator: str = Field(..., min_length=1)
    start_sec: float = Field(..., ge=0.0)
    end_sec: float = Field(..., ge=0.0)
    evidence_sufficiency: Literal["OBSERVED", "PARTIAL", "UNKNOWN"] = Field(
        default="OBSERVED"
    )


class ExtractedConditionDTO(BaseModel):
    statement: str = Field(..., min_length=1)
    tools_or_materials: List[str] = Field(default_factory=list)


class ExtractedExceptionDTO(BaseModel):
    condition_trigger: str = Field(..., min_length=1)
    alternative_action: str = Field(..., min_length=1)


class ExtractedFailureModeDTO(BaseModel):
    symptom: str = Field(..., min_length=1)
    mistake_description: str = Field(..., min_length=1)
    severity: str = Field(default="moderate")


class ExtractedTargetPropertyDTO(BaseModel):
    """For Goal-Conditioned transmission mode (e.g. geometric lattices, target photos)."""

    property_id: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    evidence_sufficiency: Literal["OBSERVED", "PARTIAL", "UNKNOWN"] = Field(
        default="OBSERVED"
    )
    measurement: Optional[str] = None


class ExtractedDivergenceDTO(BaseModel):
    """For Corrective transmission mode (e.g. learner error identification)."""

    criterion_id: str = Field(..., min_length=1)
    observed_behavior: str = Field(..., min_length=1)
    expected_behavior: str = Field(..., min_length=1)
    timestamp_sec: Optional[float] = Field(None, ge=0.0)
    evidence_sufficiency: Literal["OBSERVED", "PARTIAL", "UNKNOWN"] = Field(
        default="OBSERVED"
    )


class RunMetadataDTO(BaseModel):
    provider: str = Field(..., min_length=1)
    model_id: str = Field(..., min_length=1)
    prompt_id: str = Field(..., min_length=1)
    prompt_version: str = Field(..., min_length=1)
    input_artifact_id: str = Field(..., min_length=1)
    runtime_class: Literal["LIVE", "REPLAY", "SYNTHETIC", "ILLUSTRATIVE"] = Field(
        default="REPLAY"
    )
    run_id: str = Field(..., min_length=1)
    expected_behavior: Optional[str] = None
    evaluation_reference: Optional[str] = None


class ExtractionResponseDTO(BaseModel):
    """Envelope containing extracted structured knowledge and execution telemetry."""

    case_id: str
    skill_id: str
    title: str
    summary: str
    source_media_id: str
    transmission_mode: Literal["forward", "goal-conditioned", "corrective"] = "forward"
    steps: List[ExtractedStepDTO] = Field(default_factory=list)
    cues: List[ExtractedCueDTO] = Field(default_factory=list)
    conditions: List[ExtractedConditionDTO] = Field(default_factory=list)
    exceptions: List[ExtractedExceptionDTO] = Field(default_factory=list)
    failure_modes: List[ExtractedFailureModeDTO] = Field(default_factory=list)
    target_properties: List[ExtractedTargetPropertyDTO] = Field(default_factory=list)
    divergences: List[ExtractedDivergenceDTO] = Field(default_factory=list)
    run_metadata: RunMetadataDTO


# ---------------------------------------------------------------------------
# Spec 9: Artifact ID Patterns & Normalizer
# ---------------------------------------------------------------------------


def generate_package_id(case_id: str, version: int = 1) -> str:
    return f"kp.{case_id}.{version}"


def generate_rubric_id(case_id: str, version: int = 1) -> str:
    return f"rubric.{case_id}.{version}"


def generate_task_id(case_id: str, version: int = 1) -> str:
    return f"task.{case_id}.{version}"


def generate_evidence_id(case_id: str, prefix: str, seq: int) -> str:
    return f"ev.{case_id}.{prefix}.{seq:02d}"


def normalize_dto_to_knowledge_package(
    dto: ExtractionResponseDTO,
    consent: ConsentMetadata,
    expert_review: Optional[ExpertReview] = None,
    package_id: Optional[str] = None,
    version: int = 1,
) -> KnowledgePackage:
    """Normalize model DTO to canonical KnowledgePackage across transmission modes."""
    pkg_id = package_id or generate_package_id(dto.case_id, version)
    claims: List[KnowledgeClaim] = []
    claim_counter = 1

    # Map modality string to enum
    def parse_modality(mod_str: str) -> Modality:
        try:
            return Modality(mod_str.lower())
        except ValueError:
            return Modality.VIDEO

    # 1. Forward Mode / Steps
    for step in dto.steps:
        ev_ref = EvidenceRef(
            evidence_id=generate_evidence_id(dto.case_id, "step", step.index),
            source_id=dto.source_media_id,
            modality=Modality.VIDEO,
            start_sec=step.start_sec,
            end_sec=step.end_sec,
            cue_excerpt=step.description,
            verification_state=VerificationState.OBSERVED,
            confidence=1.0,
        )
        claims.append(
            KnowledgeClaim(
                claim_id=f"CLM-{claim_counter:02d}",
                claim_type=ClaimType.STEP,
                statement=f"{step.title}: {step.description}",
                is_observed=True,
                evidence_refs=[ev_ref],
            )
        )
        claim_counter += 1

    # 2. Cues
    for idx, cue in enumerate(dto.cues, 1):
        is_obs = cue.evidence_sufficiency == "OBSERVED"
        v_state = (
            VerificationState.OBSERVED
            if is_obs
            else VerificationState.INFERRED
        )
        ev_ref = EvidenceRef(
            evidence_id=generate_evidence_id(dto.case_id, "cue", idx),
            source_id=dto.source_media_id,
            modality=parse_modality(cue.modality),
            start_sec=cue.start_sec,
            end_sec=cue.end_sec,
            cue_excerpt=cue.observable_indicator,
            verification_state=v_state,
            confidence=1.0 if is_obs else 0.5,
        )
        claims.append(
            KnowledgeClaim(
                claim_id=f"CLM-{claim_counter:02d}",
                claim_type=ClaimType.CUE,
                statement=f"{cue.statement} (Observable: {cue.observable_indicator})",
                is_observed=is_obs,
                evidence_refs=[ev_ref],
            )
        )
        claim_counter += 1

    # 3. Goal-Conditioned Mode (Target Properties vs Inferred Procedures)
    for idx, prop in enumerate(dto.target_properties, 1):
        is_obs = prop.evidence_sufficiency == "OBSERVED"
        ev_ref = EvidenceRef(
            evidence_id=generate_evidence_id(dto.case_id, "target", idx),
            source_id=dto.source_media_id,
            modality=Modality.IMAGE,
            start_sec=0.0,
            end_sec=0.0,
            cue_excerpt=f"{prop.description} (Measurement: {prop.measurement})",
            verification_state=VerificationState.OBSERVED if is_obs else VerificationState.INFERRED,
            confidence=1.0 if is_obs else 0.5,
        )
        claims.append(
            KnowledgeClaim(
                claim_id=f"CLM-{claim_counter:02d}",
                claim_type=ClaimType.CONDITION,
                statement=f"Target Property: {prop.description}",
                is_observed=is_obs,
                evidence_refs=[ev_ref],
            )
        )
        claim_counter += 1

    # 4. Conditions
    for idx, cond in enumerate(dto.conditions, 1):
        ev_ref = EvidenceRef(
            evidence_id=generate_evidence_id(dto.case_id, "cond", idx),
            source_id=dto.source_media_id,
            modality=Modality.TEXT,
            start_sec=None,
            end_sec=None,
            cue_excerpt=f"Required tools/materials: {', '.join(cond.tools_or_materials)}",
            verification_state=VerificationState.OBSERVED,
            confidence=1.0,
        )
        claims.append(
            KnowledgeClaim(
                claim_id=f"CLM-{claim_counter:02d}",
                claim_type=ClaimType.CONDITION,
                statement=cond.statement,
                is_observed=True,
                evidence_refs=[ev_ref],
            )
        )
        claim_counter += 1

    # 5. Exceptions
    for idx, exc in enumerate(dto.exceptions, 1):
        ev_ref = EvidenceRef(
            evidence_id=generate_evidence_id(dto.case_id, "exc", idx),
            source_id=dto.source_media_id,
            modality=Modality.TEXT,
            start_sec=None,
            end_sec=None,
            cue_excerpt=f"Trigger: {exc.condition_trigger} -> Action: {exc.alternative_action}",
            verification_state=VerificationState.INFERRED,
            confidence=0.5,
        )
        claims.append(
            KnowledgeClaim(
                claim_id=f"CLM-{claim_counter:02d}",
                claim_type=ClaimType.EXCEPTION,
                statement=f"If {exc.condition_trigger}, then {exc.alternative_action}",
                is_observed=False,
                evidence_refs=[ev_ref],
            )
        )
        claim_counter += 1

    # 6. Failure Modes / Divergences
    for idx, fm in enumerate(dto.failure_modes, 1):
        ev_ref = EvidenceRef(
            evidence_id=generate_evidence_id(dto.case_id, "fail", idx),
            source_id=dto.source_media_id,
            modality=Modality.TEXT,
            start_sec=None,
            end_sec=None,
            cue_excerpt=f"Symptom: {fm.symptom} | Severity: {fm.severity}",
            verification_state=VerificationState.INFERRED,
            confidence=0.5,
        )
        claims.append(
            KnowledgeClaim(
                claim_id=f"CLM-{claim_counter:02d}",
                claim_type=ClaimType.FAILURE_MODE,
                statement=f"Failure: {fm.symptom} ({fm.mistake_description})",
                is_observed=False,
                evidence_refs=[ev_ref],
            )
        )
        claim_counter += 1

    # Fallback if DTO produced no items
    if not claims:
        raise TrackAFailure(
            FailureCategory.UNSUPPORTED_CLAIM,
            "DTO extraction yielded zero claims",
            {"dto": dto.model_dump()},
        )

    # Default review status: pending per fixture conventions
    review = expert_review or ExpertReview(
        reviewer_name="Track A Automated Review Gate",
        status=ReviewStatus.PENDING,
        notes="Awaiting domain expert inspection.",
    )

    return KnowledgePackage(
        package_id=pkg_id,
        skill_id=dto.skill_id,
        title=dto.title,
        summary=dto.summary,
        claims=claims,
        consent=consent,
        expert_review=review,
    )
