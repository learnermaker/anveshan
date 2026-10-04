"""
Live integration tests for GeminiProviderAdapter calling real Google GenAI API (Phase 7).

Gated behind GEMINI_API_KEY environment variable. Only runs when explicitly requested.
"""

import os
import pytest

from models import FailureCategory, TrackAFailure
from providers import GeminiProviderAdapter
from tracks.common.schemas import (
    ClaimType,
    ConsentMetadata,
    EvidenceRef,
    KnowledgeClaim,
    KnowledgePackage,
    Modality,
    VerificationState,
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
pytestmark = pytest.mark.skipif(
    not GEMINI_API_KEY or "Ab8RN6Il" not in GEMINI_API_KEY,
    reason="Valid GEMINI_API_KEY required for live API integration tests.",
)


@pytest.mark.live
def test_live_gemini_extraction_origami(cases_root):
    """Executes real Gemini multimodal extraction on the origami video."""
    adapter = GeminiProviderAdapter(cases_root=cases_root)
    dto = adapter.extract_knowledge("origami")

    assert dto.case_id == "origami"
    assert dto.run_metadata.runtime_class == "LIVE"
    assert dto.run_metadata.provider == "gemini"
    assert len(dto.steps) > 0

    first_step = dto.steps[0]
    assert first_step.end_sec >= first_step.start_sec


@pytest.mark.live
def test_live_gemini_query_evidence(cases_root):
    """Executes real Gemini adversarial query grounding on a KnowledgePackage."""
    adapter = GeminiProviderAdapter(cases_root=cases_root)

    ev_ref = EvidenceRef(
        evidence_id="ev.origami.step.01",
        source_id="src-origami-tavin-2010",
        modality=Modality.VIDEO,
        start_sec=10.0,
        end_sec=15.0,
        cue_excerpt="Crease along diagonal with index finger",
        verification_state=VerificationState.OBSERVED,
        confidence=1.0,
    )
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.STEP,
        statement="Diagonal valley fold across paper square",
        is_observed=True,
        evidence_refs=[ev_ref],
    )
    pkg = KnowledgePackage(
        package_id="kp.origami.1",
        skill_id="skill_origami",
        title="Origami Crane",
        summary="Folding paper crane",
        claims=[claim],
        consent=ConsentMetadata(contributor_name="Tavin", consent_scope="research"),
    )

    # Legitimate question documented in package
    answer, refs = adapter.query_evidence(pkg, "What fold is made across the paper square?")
    assert answer
    assert len(refs) > 0
    assert refs[0].evidence_id == "ev.origami.step.01"

    # Adversarial question not documented in package
    with pytest.raises(TrackAFailure) as exc_info:
        adapter.query_evidence(pkg, "How is the welding torch ignited?")

    assert exc_info.value.category == FailureCategory.MISSING_EVIDENCE
