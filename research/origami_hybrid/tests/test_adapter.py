"""
Tests for FoldingAgentAdapter.

All tests are offline — no LLM calls, no network, no API keys.
Fixtures in tests/fixtures/ mirror the exact JSON that FoldingAgent writes.

Test layout
-----------
TestLoadCheckpoints    — parse checkpoints.json + attempt_tree.json
TestEvidenceRefs       — to_evidence_refs() epistemic mapping + field correctness
TestKnowledgeClaims    — to_knowledge_claims() field mapping + schema validity
TestKnowledgePackage   — build_knowledge_package() contract validity
TestEdgeCases          — missing files, empty ops, missing timestamps
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"


def _make_run_dir(tmp_path: Path) -> Path:
    """Copy sample fixtures into a FoldingAgent-shaped run directory."""
    run_dir = tmp_path / "run_test"
    logs_dir = run_dir / "logs"
    figs_dir = run_dir / "figs"
    logs_dir.mkdir(parents=True)
    figs_dir.mkdir(parents=True)

    # checkpoints.json at run root
    shutil.copy(FIXTURES / "sample_checkpoint.json", run_dir / "checkpoints.json")
    # attempt_tree.json under logs/
    shutil.copy(FIXTURES / "sample_attempt_tree.json", logs_dir / "attempt_tree.json")
    # frames.json at run root
    shutil.copy(FIXTURES / "sample_frames.json", run_dir / "frames.json")

    # Create stub PNG files so render_png_path references don't break path checks
    (figs_dir / "attempt_n0_render.png").write_bytes(b"PNG")
    (figs_dir / "attempt_n1_render.png").write_bytes(b"PNG")

    return run_dir


@pytest.fixture()
def run_dir(tmp_path: Path) -> Path:
    return _make_run_dir(tmp_path)


@pytest.fixture()
def video_meta(tmp_path: Path) -> Path:
    p = tmp_path / "video_meta.json"
    shutil.copy(FIXTURES / "video_meta.json", p)
    return p


@pytest.fixture()
def adapter(run_dir: Path, video_meta: Path):
    from adapter import FoldingAgentAdapter
    return FoldingAgentAdapter(
        fold_output_dir=run_dir,
        video_meta_path=video_meta,
        source_attribution="Test video, CC BY 3.0",
        run_id="run_test",
    )


# ---------------------------------------------------------------------------
# TestLoadCheckpoints
# ---------------------------------------------------------------------------

class TestLoadCheckpoints:
    def test_returns_two_checkpoints(self, adapter) -> None:
        cps = adapter.load_checkpoints()
        assert len(cps) == 2

    def test_sorted_by_frame_index(self, adapter) -> None:
        cps = adapter.load_checkpoints()
        indices = [cp.frame_index for cp in cps]
        assert indices == sorted(indices)

    def test_frame_indices_are_correct(self, adapter) -> None:
        cps = adapter.load_checkpoints()
        assert cps[0].frame_index == 1
        assert cps[1].frame_index == 2

    def test_raw_representation_loaded(self, adapter) -> None:
        cps = adapter.load_checkpoints()
        for cp in cps:
            assert isinstance(cp.raw_representation, dict)
            assert "vertices" in cp.raw_representation
            assert "edges" in cp.raw_representation

    def test_operations_loaded(self, adapter) -> None:
        cps = adapter.load_checkpoints()
        # frame 1 has no operations
        assert cps[0].operations == []
        # frame 2 has one fold operation
        assert len(cps[1].operations) == 1
        assert cps[1].operations[0]["function"] == "fold"

    def test_paper_colors_loaded(self, adapter) -> None:
        cps = adapter.load_checkpoints()
        for cp in cps:
            assert cp.paper_colors["front_color"] == "white"
            assert cp.paper_colors["back_color"] == "lightblue"

    def test_critic_verdict_match(self, adapter) -> None:
        cps = adapter.load_checkpoints()
        # Both checkpoints in fixture have MATCH
        assert cps[0].critic_verdict == "MATCH"
        assert cps[1].critic_verdict == "MATCH"

    def test_critic_analysis_populated(self, adapter) -> None:
        cps = adapter.load_checkpoints()
        assert "flat square" in cps[0].critic_analysis.lower()
        assert "fold" in cps[1].critic_analysis.lower()

    def test_selected_by_comparator_false_for_match(self, adapter) -> None:
        cps = adapter.load_checkpoints()
        assert cps[0].selected_by_comparator is False
        assert cps[1].selected_by_comparator is False

    def test_timestamps_computed_from_fps(self, adapter) -> None:
        """timestamp_sec = global_frame_index / fps; fixture has fps=24."""
        cps = adapter.load_checkpoints()
        # frames.json: ["…/000010.jpg", "…/000038.jpg"]
        # frame_index=1 → position 0 → global_idx=10 → 10/24 ≈ 0.417
        # frame_index=2 → position 1 → global_idx=38 → 38/24 ≈ 1.583
        assert cps[0].timestamp_sec == pytest.approx(10 / 24.0, abs=0.01)
        assert cps[1].timestamp_sec == pytest.approx(38 / 24.0, abs=0.01)

    def test_keyframe_global_index(self, adapter) -> None:
        cps = adapter.load_checkpoints()
        assert cps[0].keyframe_global_index == 10
        assert cps[1].keyframe_global_index == 38


# ---------------------------------------------------------------------------
# TestEvidenceRefs
# ---------------------------------------------------------------------------

class TestEvidenceRefs:
    def test_returns_four_refs(self, adapter) -> None:
        """2 checkpoints × 2 refs (IMAGE + VIDEO) = 4 total."""
        refs = adapter.to_evidence_refs()
        assert len(refs) == 4

    def test_image_ref_modality(self, adapter) -> None:
        from schemas.evidence import Modality
        refs = adapter.to_evidence_refs()
        image_refs = [r for r in refs if r.modality == Modality.IMAGE]
        assert len(image_refs) == 2

    def test_video_ref_modality(self, adapter) -> None:
        from schemas.evidence import Modality
        refs = adapter.to_evidence_refs()
        video_refs = [r for r in refs if r.modality == Modality.VIDEO]
        assert len(video_refs) == 2

    def test_match_verdict_gives_observed(self, adapter) -> None:
        from schemas.evidence import VerificationState
        refs = adapter.to_evidence_refs()
        for ref in refs:
            assert ref.verification_state == VerificationState.OBSERVED

    def test_match_verdict_gives_confidence_1(self, adapter) -> None:
        refs = adapter.to_evidence_refs()
        for ref in refs:
            assert ref.confidence == 1.0

    def test_comparator_verdict_gives_inferred(self, tmp_path: Path) -> None:
        """When critic_verdict != MATCH, verification_state must be INFERRED."""
        from adapter import FoldingAgentAdapter
        from schemas.evidence import VerificationState

        run_dir = _make_run_dir(tmp_path)
        video_meta = tmp_path / "video_meta.json"
        shutil.copy(FIXTURES / "video_meta.json", video_meta)

        # Patch attempt_tree: set frame 2's verdict to MISMATCH
        tree_path = run_dir / "logs" / "attempt_tree.json"
        tree = json.loads(tree_path.read_text())
        tree["nodes"]["n1"]["critic_verdict"] = "MISMATCH"
        tree_path.write_text(json.dumps(tree))

        ad = FoldingAgentAdapter(
            fold_output_dir=run_dir,
            video_meta_path=video_meta,
            run_id="run_test_mismatch",
        )
        ad.load_checkpoints()
        refs = ad.to_evidence_refs()

        # Frame 1 (MATCH) → OBSERVED; frame 2 (MISMATCH) → INFERRED
        frame2_refs = [r for r in refs if ".02" in r.evidence_id]
        for ref in frame2_refs:
            assert ref.verification_state == VerificationState.INFERRED

    def test_comparator_verdict_gives_confidence_0_5(self, tmp_path: Path) -> None:
        from adapter import FoldingAgentAdapter

        run_dir = _make_run_dir(tmp_path)
        video_meta = tmp_path / "video_meta.json"
        shutil.copy(FIXTURES / "video_meta.json", video_meta)

        tree_path = run_dir / "logs" / "attempt_tree.json"
        tree = json.loads(tree_path.read_text())
        tree["nodes"]["n1"]["critic_verdict"] = "MISMATCH"
        tree_path.write_text(json.dumps(tree))

        ad = FoldingAgentAdapter(
            fold_output_dir=run_dir,
            video_meta_path=video_meta,
            run_id="run_test_conf",
        )
        ad.load_checkpoints()
        refs = ad.to_evidence_refs()

        frame2_refs = [r for r in refs if ".02" in r.evidence_id]
        for ref in frame2_refs:
            assert ref.confidence <= 0.5

    def test_video_ref_timestamps_within_video_duration(self, adapter) -> None:
        from schemas.evidence import Modality
        refs = adapter.to_evidence_refs()
        video_refs = [r for r in refs if r.modality == Modality.VIDEO]
        for ref in video_refs:
            assert ref.start_sec is not None
            assert ref.end_sec is not None
            assert ref.end_sec >= ref.start_sec
            assert ref.start_sec >= 0.0
            assert ref.start_sec <= 335.0  # fixture duration_sec

    def test_image_ref_source_id_contains_run_id(self, adapter) -> None:
        from schemas.evidence import Modality
        refs = adapter.to_evidence_refs()
        image_refs = [r for r in refs if r.modality == Modality.IMAGE]
        for ref in image_refs:
            assert "run_test" in ref.source_id

    def test_evidence_ids_unique(self, adapter) -> None:
        refs = adapter.to_evidence_refs()
        ids = [r.evidence_id for r in refs]
        assert len(ids) == len(set(ids)), f"Duplicate evidence_ids: {ids}"

    def test_refs_validate_against_pydantic(self, adapter) -> None:
        """All EvidenceRef objects must pass schema validation (no exceptions)."""
        from schemas.evidence import EvidenceRef
        refs = adapter.to_evidence_refs()
        for ref in refs:
            assert isinstance(ref, EvidenceRef)
            # round-trip through model to confirm no hidden validation errors
            EvidenceRef.model_validate(ref.model_dump())


# ---------------------------------------------------------------------------
# TestKnowledgeClaims
# ---------------------------------------------------------------------------

class TestKnowledgeClaims:
    def test_returns_two_claims(self, adapter) -> None:
        claims = adapter.to_knowledge_claims()
        assert len(claims) == 2

    def test_claim_ids_sequential(self, adapter) -> None:
        claims = adapter.to_knowledge_claims()
        assert claims[0].claim_id == "CLM-01"
        assert claims[1].claim_id == "CLM-02"

    def test_all_claims_are_step_type(self, adapter) -> None:
        from schemas.knowledge import ClaimType
        claims = adapter.to_knowledge_claims()
        for claim in claims:
            assert claim.claim_type == ClaimType.STEP

    def test_match_claims_are_observed(self, adapter) -> None:
        claims = adapter.to_knowledge_claims()
        for claim in claims:
            assert claim.is_observed is True

    def test_each_claim_has_at_least_one_evidence_ref(self, adapter) -> None:
        claims = adapter.to_knowledge_claims()
        for claim in claims:
            assert len(claim.evidence_refs) >= 1

    def test_claim_statement_non_empty(self, adapter) -> None:
        claims = adapter.to_knowledge_claims()
        for claim in claims:
            assert claim.statement.strip() != ""

    def test_fold_operation_appears_in_statement(self, adapter) -> None:
        """Frame 2 has a fold operation — it should appear in the statement."""
        claims = adapter.to_knowledge_claims()
        clm2 = claims[1]
        assert "fold" in clm2.statement.lower()

    def test_claims_validate_against_pydantic(self, adapter) -> None:
        from schemas.knowledge import KnowledgeClaim
        claims = adapter.to_knowledge_claims()
        for claim in claims:
            KnowledgeClaim.model_validate(claim.model_dump())


# ---------------------------------------------------------------------------
# TestKnowledgePackage
# ---------------------------------------------------------------------------

class TestKnowledgePackage:
    def test_package_validates(self, adapter) -> None:
        from schemas.knowledge import KnowledgePackage
        pkg = adapter.build_knowledge_package()
        KnowledgePackage.model_validate(pkg.model_dump())

    def test_package_id_contains_run_id(self, adapter) -> None:
        pkg = adapter.build_knowledge_package()
        assert "run_test" in pkg.package_id

    def test_package_has_two_claims(self, adapter) -> None:
        pkg = adapter.build_knowledge_package()
        assert len(pkg.claims) == 2

    def test_consent_scope_is_research_prototype(self, adapter) -> None:
        pkg = adapter.build_knowledge_package()
        assert pkg.consent.consent_scope == "research_prototype"

    def test_expert_review_is_pending(self, adapter) -> None:
        from schemas.knowledge import ReviewStatus
        pkg = adapter.build_knowledge_package()
        assert pkg.expert_review is not None
        assert pkg.expert_review.status == ReviewStatus.PENDING

    def test_attribution_in_consent_notes(self, adapter) -> None:
        pkg = adapter.build_knowledge_package()
        assert "CC BY 3.0" in (pkg.consent.notes or "")

    def test_no_duplicate_claim_ids(self, adapter) -> None:
        pkg = adapter.build_knowledge_package()
        ids = [c.claim_id for c in pkg.claims]
        assert len(ids) == len(set(ids))

    def test_custom_package_id(self, adapter) -> None:
        pkg = adapter.build_knowledge_package(package_id="kp.test.custom")
        assert pkg.package_id == "kp.test.custom"

    def test_custom_skill_id(self, adapter) -> None:
        pkg = adapter.build_knowledge_package(skill_id="skill-crane-test")
        assert pkg.skill_id == "skill-crane-test"


# ---------------------------------------------------------------------------
# TestEdgeCases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_missing_attempt_tree_still_works(self, tmp_path: Path) -> None:
        """Adapter must work if logs/attempt_tree.json is absent (all INFERRED)."""
        from adapter import FoldingAgentAdapter
        from schemas.evidence import VerificationState

        run_dir = _make_run_dir(tmp_path)
        video_meta = tmp_path / "video_meta.json"
        shutil.copy(FIXTURES / "video_meta.json", video_meta)
        # Remove attempt tree
        (run_dir / "logs" / "attempt_tree.json").unlink()

        ad = FoldingAgentAdapter(
            fold_output_dir=run_dir,
            video_meta_path=video_meta,
            run_id="run_no_tree",
        )
        cps = ad.load_checkpoints()
        assert len(cps) == 2
        # Without attempt tree, verdict is UNKNOWN → selected_by_comparator=True → INFERRED
        for cp in cps:
            assert cp.selected_by_comparator is True

    def test_missing_frames_json_gives_none_timestamps(self, tmp_path: Path) -> None:
        """Without frames.json, timestamps must be None (not crash)."""
        from adapter import FoldingAgentAdapter

        run_dir = _make_run_dir(tmp_path)
        video_meta = tmp_path / "video_meta.json"
        shutil.copy(FIXTURES / "video_meta.json", video_meta)
        (run_dir / "frames.json").unlink()

        ad = FoldingAgentAdapter(
            fold_output_dir=run_dir,
            video_meta_path=video_meta,
            run_id="run_no_frames",
        )
        cps = ad.load_checkpoints()
        for cp in cps:
            assert cp.timestamp_sec is None

    def test_no_video_ref_when_timestamp_none(self, tmp_path: Path) -> None:
        """Without timestamps, to_evidence_refs() must return only IMAGE refs."""
        from adapter import FoldingAgentAdapter
        from schemas.evidence import Modality

        run_dir = _make_run_dir(tmp_path)
        video_meta = tmp_path / "video_meta.json"
        shutil.copy(FIXTURES / "video_meta.json", video_meta)
        (run_dir / "frames.json").unlink()

        ad = FoldingAgentAdapter(
            fold_output_dir=run_dir,
            video_meta_path=video_meta,
            run_id="run_no_ts",
        )
        refs = ad.to_evidence_refs()
        video_refs = [r for r in refs if r.modality == Modality.VIDEO]
        assert video_refs == []

    def test_missing_attribution_triggers_warning_in_notes(self, tmp_path: Path) -> None:
        """When source_attribution is empty, consent notes must warn."""
        from adapter import FoldingAgentAdapter

        run_dir = _make_run_dir(tmp_path)
        video_meta = tmp_path / "video_meta.json"
        shutil.copy(FIXTURES / "video_meta.json", video_meta)

        ad = FoldingAgentAdapter(
            fold_output_dir=run_dir,
            video_meta_path=video_meta,
            source_attribution="",
            run_id="run_no_attr",
        )
        pkg = ad.build_knowledge_package()
        notes = (pkg.consent.notes or "").lower()
        assert "attribution" in notes or "not set" in notes
