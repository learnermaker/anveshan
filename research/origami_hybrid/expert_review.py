"""
HybridRunMetadataWriter and HybridExpertReviewExporter.

Mirrors the Track A run_pipeline.py convention:
  - run_metadata.json  → HybridRunMetadata (analogous to RunMetadataDTO)
  - expert_review_sheet.md  → Markdown inspection sheet (same format as
      ExpertReviewService.export_markdown in tracks/track-a/src/expert_review.py)

This module does NOT import from tracks/track-a/src/.
It does NOT import RunMetadataDTO (that class requires Track A models).
Instead it defines HybridRunMetadata, a Pydantic model with the same
documented fields that make sense for the hybrid pipeline.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Schema imports (frozen seam only)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMON = _REPO_ROOT / "tracks" / "common"
if str(_COMMON) not in sys.path:
    sys.path.insert(0, str(_COMMON))

from schemas.knowledge import KnowledgePackage  # noqa: E402


# ---------------------------------------------------------------------------
# HybridRunMetadata
# ---------------------------------------------------------------------------

class HybridRunMetadata(BaseModel):
    """
    Run metadata for the hybrid origami pipeline.

    Mirrors the fields of tracks/track-a/src/models.py::RunMetadataDTO
    that are applicable to the hybrid pipeline.  Written to run_metadata.json.
    """

    provider: str = Field(..., min_length=1, description="LLM provider used by FoldingAgent (e.g. 'google', 'anthropic')")
    model_id: str = Field(..., min_length=1, description="Model ID used by FoldingAgent (e.g. 'gemini-3.1-pro-preview')")
    prompt_id: str = Field(..., min_length=1, description="Prompt identifier (e.g. 'hybrid_pipeline_v1')")
    prompt_version: str = Field(..., min_length=1, description="Prompt version string (e.g. 'v1')")
    input_artifact_id: str = Field(..., min_length=1, description="Source identifier (e.g. video path or stable source ID)")
    runtime_class: Literal["LIVE", "REPLAY", "SYNTHETIC", "ILLUSTRATIVE"] = Field(
        default="LIVE",
        description="LIVE = real FoldingAgent run; REPLAY = from pre-existing checkpoints",
    )
    run_id: str = Field(..., min_length=1, description="Unique run ID (matches fold_output_dir name)")
    fold_output_dir: str = Field(..., description="Absolute path to the FoldingAgent run directory")
    package_id: str = Field(..., description="ID of the produced KnowledgePackage")
    claim_count: int = Field(..., ge=0, description="Number of claims in the produced KnowledgePackage")
    grounding_violations: int = Field(default=0, ge=0, description="Number of grounding violations (0 = passed)")
    uncertainty_flag_count: int = Field(default=0, ge=0, description="Number of INFERRED claims")
    pipeline_version: str = Field(default="hybrid_v1", description="Version of the hybrid pipeline")
    produced_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp when this run metadata was produced",
    )
    source_attribution: str = Field(default="", description="Attribution string for the input video")
    expected_behavior: Optional[str] = Field(
        default=None,
        description="Description of expected pipeline behaviour for this run",
    )


# ---------------------------------------------------------------------------
# HybridRunMetadataWriter
# ---------------------------------------------------------------------------

class HybridRunMetadataWriter:
    """Writes run_metadata.json to the output directory."""

    def write(
        self,
        metadata: HybridRunMetadata,
        output_dir: Path,
    ) -> Path:
        """
        Serialize HybridRunMetadata to <output_dir>/run_metadata.json.

        Returns the path of the written file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "run_metadata.json"
        path.write_text(metadata.model_dump_json(indent=2), encoding="utf-8")
        return path


# ---------------------------------------------------------------------------
# HybridExpertReviewExporter
# ---------------------------------------------------------------------------

class HybridExpertReviewExporter:
    """
    Produces expert_review_sheet.md from a KnowledgePackage.

    Output format mirrors ExpertReviewService.export_markdown() from
    tracks/track-a/src/expert_review.py.  Additional hybrid-specific
    section added: FoldingAgent run provenance.
    """

    def export_markdown(
        self,
        package: KnowledgePackage,
        run_metadata: HybridRunMetadata | None = None,
    ) -> str:
        """Return the full Markdown inspection sheet as a string."""
        lines: list[str] = [
            f"# Expert Review Sheet: {package.title}",
            "",
            "## Case Metadata",
            f"- **Package ID:** `{package.package_id}`",
            f"- **Skill ID:** `{package.skill_id}`",
            f"- **Pipeline:** `{run_metadata.pipeline_version if run_metadata else 'hybrid_v1'}`",
        ]

        if run_metadata:
            lines.extend([
                f"- **Model:** `{run_metadata.model_id}` (provider: `{run_metadata.provider}`)",
                f"- **Runtime class:** `{run_metadata.runtime_class}`",
                f"- **Run ID:** `{run_metadata.run_id}`",
                f"- **Source attribution:** {run_metadata.source_attribution or '_not set — add before use_'}",
                f"- **Produced at:** {run_metadata.produced_at}",
            ])

        lines.extend([
            "",
            "## Contributor Consent",
            f"- **Contributor:** {package.consent.contributor_name}",
            f"- **Scope:** `{package.consent.consent_scope}`",
            f"- **Revocable:** {package.consent.revocable}",
            f"- **Notes:** {package.consent.notes or 'None'}",
            "",
            "## Review Status",
        ])

        rev = package.expert_review
        if rev:
            lines.extend([
                f"- **Reviewer:** {rev.reviewer_name}",
                f"- **Status:** `{rev.status.value.upper()}`",
                f"- **Reviewed At:** {rev.reviewed_at or 'Pending'}",
                f"- **Notes:** {rev.notes or 'None'}",
            ])
        else:
            lines.append("- *Status: No review recorded*")

        lines.extend([
            "",
            "## Extracted Knowledge Claims",
            "",
            "| ID | Type | Observation | Statement | Evidence Locators |",
            "|---|---|---|---|---|",
        ])

        for c in package.claims:
            locs = []
            for ev in c.evidence_refs:
                time_str = (
                    f"[{ev.start_sec:.1f}s\u2013{ev.end_sec:.1f}s]"
                    if ev.start_sec is not None and ev.end_sec is not None
                    else "[Static/Image]"
                )
                locs.append(f"`{ev.evidence_id}` {time_str} ({ev.verification_state.value})")
            loc_str = "<br>".join(locs)
            obs_str = "OBSERVED" if c.is_observed else "INFERRED"
            lines.append(
                f"| `{c.claim_id}` | `{c.claim_type.value}` "
                f"| **{obs_str}** | {c.statement[:120]} | {loc_str} |"
            )

        if run_metadata:
            lines.extend([
                "",
                "## FoldingAgent Run Provenance",
                f"- **Fold output directory:** `{run_metadata.fold_output_dir}`",
                f"- **Claims produced:** {run_metadata.claim_count}",
                f"- **Grounding violations:** {run_metadata.grounding_violations}",
                f"- **Uncertainty flags (INFERRED claims):** {run_metadata.uncertainty_flag_count}",
            ])

        lines.extend([
            "",
            "---",
            "### Expert Signature & Verdict",
            "- [ ] **APPROVE** (Extraction faithfully represents demonstrated technique)",
            "- [ ] **REVISE** (Corrections noted above)",
            "- [ ] **REJECT** (Fundamental misunderstanding of physical procedure)",
            "",
            "Signature: __________________________  Date: _______________",
        ])

        return "\n".join(lines)

    def write(
        self,
        package: KnowledgePackage,
        output_dir: Path,
        run_metadata: HybridRunMetadata | None = None,
    ) -> Path:
        """
        Write expert_review_sheet.md to <output_dir>.

        Returns the path of the written file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "expert_review_sheet.md"
        path.write_text(self.export_markdown(package, run_metadata), encoding="utf-8")
        return path
