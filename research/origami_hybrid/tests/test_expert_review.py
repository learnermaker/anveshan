"""
Tests for HybridRunMetadataWriter and HybridExpertReviewExporter (commit 7).

All offline — no LLM, no network.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMMON = _REPO_ROOT / "tracks" / "common"
if str(_COMMON) not in sys.path:
    sys.path.insert(0, str(_COMMON))

from schemas.knowledge import (
    ClaimType, ConsentMetadata, ExpertReview, KnowledgeClaim,
    KnowledgePackage, ReviewStatus,
)
from schemas.evidence import EvidenceRef, Modality, VerificationState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_metadata(**overrides):
    from expert_review import HybridRunMetadata
    defaults = dict(
        provider="google",
        model_id="gemini-3.1-pro-preview",
        prompt_id="hybrid_pipeline_v1",
        prompt_version="v1",
        input_artifact_id="src-hybrid-video",
        runtime_class="LIVE",
        run_id="run_test",
        fold_output_dir="/fake/out/run_test",
        package_id="kp.origami-hybrid.run_test",
        claim_count=2,
        grounding_violations=0,
        uncertainty_flag_count=0,
        source_attribution="Test video, CC BY 3.0",
    )
    defaults.update(overrides)
    return HybridRunMetadata(**defaults)


def _make_package() -> KnowledgePackage:
    ev = EvidenceRef(
        evidence_id="ev.fa.img.01",
        source_id="src-fa-run_test",
        modality=Modality.IMAGE,
        verification_state=VerificationState.OBSERVED,
        confidence=1.0,
    )
    claim = KnowledgeClaim(
        claim_id="CLM-01",
        claim_type=ClaimType.STEP,
        statement="Initial flat square.",
        is_observed=True,
        evidence_refs=[ev],
    )
    return KnowledgePackage(
        package_id="kp.origami-hybrid.run_test",
        skill_id="skill-origami-hybrid",
        title="Test Origami Package",
        summary="Test summary.",
        claims=[claim],
        consent=ConsentMetadata(
            contributor_name="FoldingAgent Hybrid Pipeline",
            consent_scope="research_prototype",
            notes="Test CC BY 3.0",
        ),
        expert_review=ExpertReview(
            reviewer_name="Pending",
            status=ReviewStatus.PENDING,
        ),
    )


def _adapter_package(tmp_path: Path) -> KnowledgePackage:
    from adapter import FoldingAgentAdapter
    run_dir = tmp_path / "run_test"
    logs_dir = run_dir / "logs"
    figs_dir = run_dir / "figs"
    logs_dir.mkdir(parents=True)
    figs_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / "sample_checkpoint.json", run_dir / "checkpoints.json")
    shutil.copy(FIXTURES / "sample_attempt_tree.json", logs_dir / "attempt_tree.json")
    shutil.copy(FIXTURES / "sample_frames.json", run_dir / "frames.json")
    (figs_dir / "attempt_n0_render.png").write_bytes(b"PNG")
    (figs_dir / "attempt_n1_render.png").write_bytes(b"PNG")
    vm = tmp_path / "video_meta.json"
    shutil.copy(FIXTURES / "video_meta.json", vm)
    ad = FoldingAgentAdapter(
        fold_output_dir=run_dir,
        video_meta_path=vm,
        source_attribution="Test CC BY 3.0",
        run_id="run_test",
    )
    return ad.build_knowledge_package()


# ---------------------------------------------------------------------------
# TestHybridRunMetadata
# ---------------------------------------------------------------------------

class TestHybridRunMetadata:
    def test_valid_metadata_constructs(self) -> None:
        meta = _make_metadata()
        assert meta.run_id == "run_test"

    def test_validates_with_pydantic(self) -> None:
        from expert_review import HybridRunMetadata
        meta = _make_metadata()
        HybridRunMetadata.model_validate(meta.model_dump())

    def test_produced_at_is_iso_timestamp(self) -> None:
        meta = _make_metadata()
        from datetime import datetime
        # Should parse without error
        datetime.fromisoformat(meta.produced_at.replace("Z", "+00:00"))

    def test_runtime_class_default_live(self) -> None:
        meta = _make_metadata()
        assert meta.runtime_class == "LIVE"

    def test_runtime_class_replay(self) -> None:
        meta = _make_metadata(runtime_class="REPLAY")
        assert meta.runtime_class == "REPLAY"

    def test_pipeline_version_default(self) -> None:
        meta = _make_metadata()
        assert meta.pipeline_version == "hybrid_v1"


# ---------------------------------------------------------------------------
# TestHybridRunMetadataWriter
# ---------------------------------------------------------------------------

class TestHybridRunMetadataWriter:
    def test_file_written(self, tmp_path: Path) -> None:
        from expert_review import HybridRunMetadataWriter
        meta = _make_metadata()
        HybridRunMetadataWriter().write(meta, tmp_path)
        assert (tmp_path / "run_metadata.json").exists()

    def test_json_valid(self, tmp_path: Path) -> None:
        from expert_review import HybridRunMetadataWriter
        meta = _make_metadata()
        HybridRunMetadataWriter().write(meta, tmp_path)
        doc = json.loads((tmp_path / "run_metadata.json").read_text())
        assert doc["run_id"] == "run_test"
        assert doc["provider"] == "google"

    def test_all_required_fields_present(self, tmp_path: Path) -> None:
        from expert_review import HybridRunMetadataWriter
        meta = _make_metadata()
        HybridRunMetadataWriter().write(meta, tmp_path)
        doc = json.loads((tmp_path / "run_metadata.json").read_text())
        required = {
            "provider", "model_id", "prompt_id", "prompt_version",
            "input_artifact_id", "runtime_class", "run_id",
            "fold_output_dir", "package_id", "claim_count",
            "grounding_violations", "uncertainty_flag_count",
            "pipeline_version", "produced_at",
        }
        assert required.issubset(doc.keys())

    def test_creates_output_dir_if_missing(self, tmp_path: Path) -> None:
        from expert_review import HybridRunMetadataWriter
        nested = tmp_path / "deep" / "nested" / "output"
        HybridRunMetadataWriter().write(_make_metadata(), nested)
        assert (nested / "run_metadata.json").exists()

    def test_returns_path(self, tmp_path: Path) -> None:
        from expert_review import HybridRunMetadataWriter
        path = HybridRunMetadataWriter().write(_make_metadata(), tmp_path)
        assert path == tmp_path / "run_metadata.json"


# ---------------------------------------------------------------------------
# TestHybridExpertReviewExporter
# ---------------------------------------------------------------------------

class TestHybridExpertReviewExporter:
    def test_export_markdown_returns_string(self) -> None:
        from expert_review import HybridExpertReviewExporter
        md = HybridExpertReviewExporter().export_markdown(_make_package())
        assert isinstance(md, str)

    def test_markdown_has_title(self) -> None:
        from expert_review import HybridExpertReviewExporter
        md = HybridExpertReviewExporter().export_markdown(_make_package())
        assert "# Expert Review Sheet" in md

    def test_markdown_has_claim_table(self) -> None:
        from expert_review import HybridExpertReviewExporter
        md = HybridExpertReviewExporter().export_markdown(_make_package())
        assert "CLM-01" in md
        assert "OBSERVED" in md

    def test_markdown_has_signature_block(self) -> None:
        from expert_review import HybridExpertReviewExporter
        md = HybridExpertReviewExporter().export_markdown(_make_package())
        assert "APPROVE" in md
        assert "Signature:" in md

    def test_markdown_includes_run_metadata_section(self) -> None:
        from expert_review import HybridExpertReviewExporter
        md = HybridExpertReviewExporter().export_markdown(
            _make_package(), _make_metadata()
        )
        assert "FoldingAgent Run Provenance" in md
        assert "run_test" in md

    def test_markdown_pending_review_status(self) -> None:
        from expert_review import HybridExpertReviewExporter
        md = HybridExpertReviewExporter().export_markdown(_make_package())
        assert "PENDING" in md

    def test_missing_attribution_shows_warning(self) -> None:
        from expert_review import HybridExpertReviewExporter
        meta = _make_metadata(source_attribution="")
        md = HybridExpertReviewExporter().export_markdown(_make_package(), meta)
        assert "not set" in md.lower() or "add before use" in md.lower()

    def test_write_creates_file(self, tmp_path: Path) -> None:
        from expert_review import HybridExpertReviewExporter
        HybridExpertReviewExporter().write(_make_package(), tmp_path)
        assert (tmp_path / "expert_review_sheet.md").exists()

    def test_write_returns_path(self, tmp_path: Path) -> None:
        from expert_review import HybridExpertReviewExporter
        p = HybridExpertReviewExporter().write(_make_package(), tmp_path)
        assert p == tmp_path / "expert_review_sheet.md"

    def test_adapter_package_review_sheet(self, tmp_path: Path) -> None:
        """Full adapter package produces a valid review sheet."""
        from expert_review import HybridExpertReviewExporter
        pkg = _adapter_package(tmp_path)
        md = HybridExpertReviewExporter().export_markdown(pkg)
        assert "CLM-01" in md
        assert "CLM-02" in md
        assert "APPROVE" in md
