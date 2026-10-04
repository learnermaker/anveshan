"""
Pydantic schemas passed to Gemini as response_schema (Phase 1).

These are lean, model-facing schemas containing only the fields Gemini
should extract. Envelope metadata (case_id, skill_id, run_metadata, etc.)
is added by the adapter post-extraction to avoid hallucination and token waste.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class GeminiStepSchema(BaseModel):
    """A procedural step extracted from demonstration media."""

    index: int = Field(description="Zero-based step index in chronological order")
    title: str = Field(description="Concise step title (3-8 words)")
    description: str = Field(description="Detailed physical action description")
    start_sec: float = Field(description="Start timestamp in seconds (0.1s resolution)")
    end_sec: float = Field(description="End timestamp in seconds (0.1s resolution)")


class GeminiCueSchema(BaseModel):
    """A sensory cue observed during the demonstration."""

    modality: Literal["video", "audio", "tactile", "text"] = Field(
        default="video", description="Sensory modality of the cue"
    )
    statement: str = Field(description="What the cue indicates")
    observable_indicator: str = Field(
        description="Concrete physical indicator (e.g. click sound at spindle lock)"
    )
    start_sec: float = Field(description="Start timestamp in seconds")
    end_sec: float = Field(description="End timestamp in seconds")
    evidence_sufficiency: Literal["OBSERVED", "PARTIAL", "UNKNOWN"] = Field(
        default="OBSERVED",
        description="OBSERVED if directly visible/audible, PARTIAL if partly visible, UNKNOWN if inferred",
    )


class GeminiConditionSchema(BaseModel):
    """A precondition or material constraint for the procedure."""

    statement: str = Field(description="Precondition statement")
    tools_or_materials: List[str] = Field(
        default_factory=list, description="List of tools or materials required"
    )


class GeminiExceptionSchema(BaseModel):
    """A documented exception or workaround in the procedure."""

    condition_trigger: str = Field(description="Condition that triggers the exception")
    alternative_action: str = Field(description="Alternative action to take")


class GeminiFailureModeSchema(BaseModel):
    """A common failure mode with observable symptoms."""

    symptom: str = Field(description="Observable symptom of the failure")
    mistake_description: str = Field(description="What went wrong")
    severity: Literal["low", "moderate", "high", "critical"] = Field(
        default="moderate", description="Severity of the failure"
    )


class GeminiTargetPropertySchema(BaseModel):
    """An observable target property (Goal-Conditioned mode)."""

    property_id: str = Field(
        description="Unique property identifier (e.g. symmetry_axes, grid_spacing)"
    )
    description: str = Field(description="Description of the visible target property")
    evidence_sufficiency: Literal["OBSERVED", "PARTIAL", "UNKNOWN"] = Field(
        default="OBSERVED", description="OBSERVED for directly visible properties"
    )
    measurement: Optional[str] = Field(
        None, description="Quantitative measurement if visible (e.g. 5x5 grid spacing)"
    )


class GeminiDivergenceSchema(BaseModel):
    """A divergence from expected technique (Corrective mode)."""

    criterion_id: str = Field(description="Rubric criterion ID this divergence maps to")
    observed_behavior: str = Field(description="What the learner actually did")
    expected_behavior: str = Field(description="What was expected per rubric")
    timestamp_sec: Optional[float] = Field(
        None, description="Timestamp of the divergence"
    )
    evidence_sufficiency: Literal["OBSERVED", "PARTIAL", "UNKNOWN"] = Field(
        default="OBSERVED", description="OBSERVED for directly visible divergences"
    )


class GeminiExtractionResponse(BaseModel):
    """
    Top-level response schema sent to Gemini via response_schema.

    Contains only model-extractable fields. Envelope metadata
    (case_id, skill_id, run_metadata, source_media_id) is added by the adapter.
    """

    title: str = Field(description="Concise title for the extracted skill/procedure")
    summary: str = Field(description="2-3 sentence summary of the demonstration")
    steps: List[GeminiStepSchema] = Field(
        default_factory=list,
        description="Chronological procedural steps (Forward mode)",
    )
    cues: List[GeminiCueSchema] = Field(
        default_factory=list,
        description="Sensory cues observed during the demonstration",
    )
    conditions: List[GeminiConditionSchema] = Field(
        default_factory=list,
        description="Preconditions and material constraints",
    )
    exceptions: List[GeminiExceptionSchema] = Field(
        default_factory=list,
        description="Documented exceptions and workarounds",
    )
    failure_modes: List[GeminiFailureModeSchema] = Field(
        default_factory=list,
        description="Common failure modes and symptoms",
    )
    target_properties: List[GeminiTargetPropertySchema] = Field(
        default_factory=list,
        description="Observable target properties (Goal-Conditioned mode)",
    )
    divergences: List[GeminiDivergenceSchema] = Field(
        default_factory=list,
        description="Divergences from expected behavior (Corrective mode)",
    )


class GeminiQueryResponse(BaseModel):
    """Response schema for adversarial evidence queries."""

    answer: str = Field(description="Direct answer citing claim IDs and timestamps")
    cited_claim_ids: List[str] = Field(
        default_factory=list,
        description="List of Claim IDs supporting the answer (e.g. ['CLM-01', 'CLM-02'])",
    )
    cited_timestamps: List[str] = Field(
        default_factory=list,
        description="Timestamp intervals cited (e.g. ['00:18.0 - 00:22.5'])",
    )
    has_sufficient_evidence: bool = Field(
        description="False if the question asks about undocumented conditions or missing evidence"
    )
