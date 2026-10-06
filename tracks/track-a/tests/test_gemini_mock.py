"""
Unit tests for GeminiProviderAdapter with mocked Gemini SDK client (Phase 7).

Verifies extraction flow, DTO mapping, error handling, retries,
and query citation parsing without consuming real API tokens.
"""

from unittest.mock import MagicMock, patch
import pytest

from gemini_schemas import (
    GeminiCueSchema,
    GeminiExtractionResponse,
    GeminiQueryResponse,
    GeminiStepSchema,
)
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


@pytest.fixture
def mock_gemini_client():
    client = MagicMock()
    mock_file = MagicMock()
    mock_file.name = "files/test_file_123"
    mock_file.state = MagicMock()
    mock_file.state.name = "ACTIVE"
    client.files.upload.return_value = mock_file
    client.files.get.return_value = mock_file
    return client


def test_gemini_adapter_extract_knowledge_mocked(cases_root, mock_gemini_client, tmp_path):
    mock_response = MagicMock()
    mock_response.parsed = GeminiExtractionResponse(
        title="Fold Paper Crane",
        summary="A complete demonstration of folding a paper crane",
        steps=[
            GeminiStepSchema(
                index=0,
                title="Diagonal Crease",
                description="Valley fold diagonally across center",
                start_sec=10.0,
                end_sec=15.0,
            )
        ],
        cues=[
            GeminiCueSchema(
                modality="video",
                statement="Crisp crease alignment",
                observable_indicator="Fingernail burnish along fold line",
                start_sec=12.0,
                end_sec=14.0,
                evidence_sufficiency="OBSERVED",
            )
        ],
    )
    mock_gemini_client.models.generate_content.return_value = mock_response

    adapter = GeminiProviderAdapter(
        cases_root=cases_root,
        api_key="mock_key_123",
    )
    adapter._client = mock_gemini_client

    # Create dummy cached file so download is bypassed
    cache_dir = cases_root.parent / "track-a" / "data" / ".cache" / "origami"
    cache_dir.mkdir(parents=True, exist_ok=True)
    dummy_file = cache_dir / "OrigamiCrane.ogv.480p.webm"
    dummy_file.write_bytes(b"dummy_video_bytes")

    dto = adapter.extract_knowledge("origami")

    assert dto.case_id == "origami"
    assert dto.title == "Fold Paper Crane"
    assert len(dto.steps) == 1
    assert dto.steps[0].title == "Diagonal Crease"
    assert dto.run_metadata.runtime_class == "LIVE"
    assert dto.run_metadata.provider == "gemini"

    # Verify Gemini Files API upload and cleanup occurred
    assert mock_gemini_client.files.upload.called
    assert mock_gemini_client.files.delete.called


def test_gemini_adapter_extract_missing_media_raises(cases_root, mock_gemini_client):
    adapter = GeminiProviderAdapter(
        cases_root=cases_root,
        api_key="mock_key_123",
    )
    adapter._client = mock_gemini_client

    # Case micrometer has no source_media in manifest.json
    with pytest.raises(TrackAFailure) as exc_info:
        adapter.extract_knowledge("micrometer")

    assert exc_info.value.category == FailureCategory.INVALID_INPUT
    assert "No source media configured" in exc_info.value.message


def test_gemini_adapter_query_evidence_mocked(cases_root, mock_gemini_client):
    mock_response = MagicMock()
    mock_response.parsed = GeminiQueryResponse(
        answer="The paper is burnished with fingernail pressure at 12s.",
        cited_claim_ids=["CLM-01"],
        cited_timestamps=["00:12.0 - 00:14.0"],
        has_sufficient_evidence=True,
    )
    mock_gemini_client.models.generate_content.return_value = mock_response

    adapter = GeminiProviderAdapter(
        cases_root=cases_root,
        api_key="mock_key_123",
    )
    adapter._client = mock_gemini_client

    ev_ref = EvidenceRef(
        evidence_id="ev.origami.cue.01",
        source_id="src-origami-tavin-2010",
        modality=Modality.VIDEO,
        start_sec=12.0,
        end_sec=14.0,
        cue_excerpt="Fingernail burnish along fold line",
        verification_state=VerificationState.OBSERVED,
        confidence=1.0,
    )
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.CUE,
        statement="Crisp crease alignment",
        is_observed=True,
        evidence_refs=[ev_ref],
    )
    consent = ConsentMetadata(
        contributor_name="Tavin",
        consent_scope="public_research",
    )
    pkg = KnowledgePackage(
        package_id="kp.origami.1",
        skill_id="skill_origami",
        title="Origami Folding",
        summary="Folding crane",
        claims=[claim],
        consent=consent,
    )

    answer, refs = adapter.query_evidence(pkg, "How was the crease burnished?")
    assert "burnished with fingernail" in answer
    assert len(refs) == 1
    assert refs[0].evidence_id == "ev.origami.cue.01"


def test_gemini_adapter_query_insufficient_evidence_raises(cases_root, mock_gemini_client):
    mock_response = MagicMock()
    mock_response.parsed = GeminiQueryResponse(
        answer="INSUFFICIENT_EVIDENCE: The expert demonstration does not show or document this condition.",
        cited_claim_ids=[],
        cited_timestamps=[],
        has_sufficient_evidence=False,
    )
    mock_gemini_client.models.generate_content.return_value = mock_response

    adapter = GeminiProviderAdapter(
        cases_root=cases_root,
        api_key="mock_key_123",
    )
    adapter._client = mock_gemini_client

    ev_ref = EvidenceRef(
        evidence_id="ev.origami.step.01",
        source_id="src-origami-tavin-2010",
        modality=Modality.VIDEO,
        start_sec=0.0,
        end_sec=5.0,
        cue_excerpt="Initial position",
        verification_state=VerificationState.OBSERVED,
        confidence=1.0,
    )
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.STEP,
        statement="Square paper starting position",
        is_observed=True,
        evidence_refs=[ev_ref],
    )
    consent = ConsentMetadata(
        contributor_name="Tavin",
        consent_scope="public_research",
    )
    pkg = KnowledgePackage(
        package_id="kp.origami.1",
        skill_id="skill_origami",
        title="Origami Folding",
        summary="Folding crane",
        claims=[claim],
        consent=consent,
    )

    with pytest.raises(TrackAFailure) as exc_info:
        adapter.query_evidence(pkg, "What type of scissors were used?")

    assert exc_info.value.category == FailureCategory.MISSING_EVIDENCE
    assert "INSUFFICIENT_EVIDENCE" in exc_info.value.message
