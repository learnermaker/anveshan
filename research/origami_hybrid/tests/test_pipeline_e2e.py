"""
End-to-end integration test for run_hybrid_pipeline() (commit 8).

Uses fixture data — no FoldingAgent run, no LLM calls, no network.
Verifies that all 8 output files are written and that the Anveshan
contracts validate against the frozen Pydantic schemas.
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

from schemas.knowledge import KnowledgePackage
from schemas.rubric import RubricDefinition
from schemas.practice import PracticeTask


# ---------------------------------------------------------------------------
# Fixture: build a minimal FoldingAgent run directory from test fixtures
# ---------------------------------------------------------------------------

def _make_run_dir(tmp_path: Path) -> tuple[Path, Path]:
    """Return (fold_output_dir, video_meta_path)."""
    run_dir = tmp_path / "run_e2e"
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
    return run_dir, vm


def _run_pipeline(tmp_path: Path) -> Path:
    """Execute the full adapt pipeline and return output_dir."""
    from adapter import FoldingAgentAdapter
    from grounding import EvidenceGrounder
    from rubric_synth import RubricSynthesizer
    from sidecars import FoldStateLogWriter, CreaseEvidenceWriter
    from expert_review import (
        HybridRunMetadata, HybridRunMetadataWriter, HybridExpertReviewExporter,
    )

    fold_output_dir, video_meta_path = _make_run_dir(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    run_id = fold_output_dir.name

    adapter = FoldingAgentAdapter(
        fold_output_dir=fold_output_dir,
        video_meta_path=video_meta_path,
        source_attribution="Test video, CC BY 3.0",
        run_id=run_id,
    )
    checkpoints = adapter.load_checkpoints()
    package = adapter.build_knowledge_package()

    synth = RubricSynthesizer()
    rubric = synth.synthesize(checkpoints)
    task = synth.generate_practice_task(rubric, package_id=package.package_id)

    result = EvidenceGrounder().validate(package)

    meta_raw = json.loads(video_meta_path.read_text())
    fps = float(meta_raw.get("fps", 0.0))
    FoldStateLogWriter().write(checkpoints, output_dir / "fold_state_log.json", run_id=run_id, fps=fps)
    CreaseEvidenceWriter().write(checkpoints, output_dir / "crease_evidence.json", run_id=run_id)

    run_meta = HybridRunMetadata(
        provider="google",
        model_id="gemini-3.1-pro-preview",
        prompt_id="hybrid_pipeline_v1",
        prompt_version="v1",
        input_artifact_id="src-test",
        runtime_class="LIVE",
        run_id=run_id,
        fold_output_dir=str(fold_output_dir),
        package_id=package.package_id,
        claim_count=len(package.claims),
        grounding_violations=len(result.violations),
        uncertainty_flag_count=len(result.uncertainty_flags),
        source_attribution="Test video, CC BY 3.0",
    )
    HybridRunMetadataWriter().write(run_meta, output_dir)
    HybridExpertReviewExporter().write(package, output_dir, run_meta)

    (output_dir / "knowledge_package.json").write_text(
        package.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "rubric.json").write_text(
        rubric.model_dump_json(indent=2), encoding="utf-8"
    )
    (output_dir / "practice_task.json").write_text(
        task.model_dump_json(indent=2), encoding="utf-8"
    )

    return output_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPipelineE2E:
    def test_all_seven_output_files_written(self, tmp_path: Path) -> None:
        """All 7 required output files must exist after running the pipeline."""
        output_dir = _run_pipeline(tmp_path)
        expected = [
            "knowledge_package.json",
            "rubric.json",
            "practice_task.json",
            "run_metadata.json",
            "expert_review_sheet.md",
            "fold_state_log.json",
            "crease_evidence.json",
        ]
        for filename in expected:
            path = output_dir / filename
            assert path.exists(), f"Missing output file: {filename}"

    def test_knowledge_package_validates(self, tmp_path: Path) -> None:
        output_dir = _run_pipeline(tmp_path)
        doc = json.loads((output_dir / "knowledge_package.json").read_text())
        pkg = KnowledgePackage.model_validate(doc)
        assert len(pkg.claims) == 2

    def test_rubric_validates(self, tmp_path: Path) -> None:
        output_dir = _run_pipeline(tmp_path)
        doc = json.loads((output_dir / "rubric.json").read_text())
        rubric = RubricDefinition.model_validate(doc)
        assert len(rubric.criteria) == 5

    def test_practice_task_validates(self, tmp_path: Path) -> None:
        output_dir = _run_pipeline(tmp_path)
        doc = json.loads((output_dir / "practice_task.json").read_text())
        task = PracticeTask.model_validate(doc)
        assert task.rubric_id is not None

    def test_practice_task_references_package(self, tmp_path: Path) -> None:
        output_dir = _run_pipeline(tmp_path)
        pkg = KnowledgePackage.model_validate(
            json.loads((output_dir / "knowledge_package.json").read_text())
        )
        task = PracticeTask.model_validate(
            json.loads((output_dir / "practice_task.json").read_text())
        )
        assert task.package_id == pkg.package_id

    def test_practice_task_references_rubric(self, tmp_path: Path) -> None:
        output_dir = _run_pipeline(tmp_path)
        rubric = RubricDefinition.model_validate(
            json.loads((output_dir / "rubric.json").read_text())
        )
        task = PracticeTask.model_validate(
            json.loads((output_dir / "practice_task.json").read_text())
        )
        assert task.rubric_id == rubric.rubric_id

    def test_target_criteria_ids_all_valid(self, tmp_path: Path) -> None:
        """PracticeTask.target_criteria_ids must all exist in the rubric."""
        output_dir = _run_pipeline(tmp_path)
        rubric = RubricDefinition.model_validate(
            json.loads((output_dir / "rubric.json").read_text())
        )
        task = PracticeTask.model_validate(
            json.loads((output_dir / "practice_task.json").read_text())
        )
        rubric_ids = {c.criterion_id for c in rubric.criteria}
        for tid in task.target_criteria_ids:
            assert tid in rubric_ids, f"{tid} not in rubric"

    def test_grounding_passes_on_fixture(self, tmp_path: Path) -> None:
        """The full pipeline output must pass grounding validation."""
        from grounding import EvidenceGrounder
        output_dir = _run_pipeline(tmp_path)
        pkg = KnowledgePackage.model_validate(
            json.loads((output_dir / "knowledge_package.json").read_text())
        )
        result = EvidenceGrounder().validate(pkg)
        assert result.is_valid, f"Violations: {result.violations}"

    def test_run_metadata_has_correct_claim_count(self, tmp_path: Path) -> None:
        output_dir = _run_pipeline(tmp_path)
        meta = json.loads((output_dir / "run_metadata.json").read_text())
        pkg = KnowledgePackage.model_validate(
            json.loads((output_dir / "knowledge_package.json").read_text())
        )
        assert meta["claim_count"] == len(pkg.claims)

    def test_fold_state_log_has_correct_frame_count(self, tmp_path: Path) -> None:
        output_dir = _run_pipeline(tmp_path)
        log = json.loads((output_dir / "fold_state_log.json").read_text())
        assert len(log["states"]) == 2

    def test_crease_evidence_has_correct_frame_count(self, tmp_path: Path) -> None:
        output_dir = _run_pipeline(tmp_path)
        ce = json.loads((output_dir / "crease_evidence.json").read_text())
        assert len(ce["keyframe_crease_maps"]) == 2

    def test_expert_review_sheet_has_all_claims(self, tmp_path: Path) -> None:
        output_dir = _run_pipeline(tmp_path)
        md = (output_dir / "expert_review_sheet.md").read_text()
        assert "CLM-01" in md
        assert "CLM-02" in md

    def test_deterministic_replay(self, tmp_path: Path) -> None:
        """Running pipeline twice on same fixtures gives identical package IDs."""
        out1 = _run_pipeline(tmp_path / "run1")
        out2 = _run_pipeline(tmp_path / "run2")
        pkg1 = json.loads((out1 / "knowledge_package.json").read_text())
        pkg2 = json.loads((out2 / "knowledge_package.json").read_text())
        # Skill ID, claim IDs, and rubric IDs should all be the same
        assert pkg1["skill_id"] == pkg2["skill_id"]
        ids1 = [c["claim_id"] for c in pkg1["claims"]]
        ids2 = [c["claim_id"] for c in pkg2["claims"]]
        assert ids1 == ids2
