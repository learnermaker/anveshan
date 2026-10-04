from pathlib import Path
import pytest

from tracks.common.schemas import KnowledgePackage, PracticeTask, RubricDefinition
from tracks.common.validator import validate_practice_task_against_knowledge_and_rubric
from pipeline import TrackAOutputBundle, TrackAPipeline


def test_pipeline_e2e_all_seven_cases(cases_root: Path, case_index: list[str]) -> None:
    """E2E verification of TrackAPipeline across all 7 registered case packs."""
    pipeline = TrackAPipeline(cases_root=cases_root, mode="replay")

    for case_id in case_index:
        bundle = pipeline.run(case_id=case_id)
        assert isinstance(bundle, TrackAOutputBundle)

        # 1. Output contract types
        assert isinstance(bundle.package, KnowledgePackage)
        assert isinstance(bundle.rubric, RubricDefinition)
        assert isinstance(bundle.practice_task, PracticeTask)

        # 2. Case manifest alignment
        assert bundle.manifest.case_id == case_id
        assert bundle.package.skill_id is not None
        assert len(bundle.package.claims) > 0

        # 3. Cross-contract validation
        errs = validate_practice_task_against_knowledge_and_rubric(
            bundle.practice_task, bundle.package, bundle.rubric
        )
        assert not errs, f"Cross-contract errors in case {case_id}: {errs}"

        # 4. Handoff packet completeness
        assert bundle.consent_summary.contributor_name is not None
        assert isinstance(bundle.uncertainty_summary, list)
        assert "run_pipeline.py" in bundle.replay_command
        assert bundle.run_metadata.runtime_class == "REPLAY"


def test_pipeline_enforce_approved_flag(cases_root: Path) -> None:
    pipeline = TrackAPipeline(cases_root=cases_root, mode="replay")
    # Default fixture review status is PENDING, so enforce_approved=True must raise HUMAN_REVIEW_REQUIRED
    from models import FailureCategory, TrackAFailure

    with pytest.raises(TrackAFailure) as exc:
        pipeline.run(case_id="micrometer", enforce_approved=True)
    assert exc.value.category == FailureCategory.HUMAN_REVIEW_REQUIRED
