from pathlib import Path
import pytest

from case_registry import load_replay_bundle
from tracks.common.schemas import KnowledgePackage, PracticeTask, RubricDefinition
from tracks.common.validator import (
    validate_practice_task_against_knowledge_and_rubric,
    validate_transmission_bundle,
)
from pipeline import TrackAOutputBundle, TrackAPipeline


def test_pipeline_e2e_all_seven_cases(cases_root: Path, case_index: list[str]) -> None:
    """E2E verification of TrackAPipeline across all 7 registered case packs in replay mode.

    Verifies:
    1. Canonical contract preservation: IDs match bundle.json directly (not regenerated).
    2. Output contract schemas and cross-contract invariants pass.
    3. Canonical replay bundle itself passes complete 8-contract validation.
    4. Manifest alignment and epistemic runtime classification.
    """
    pipeline = TrackAPipeline(cases_root=cases_root, mode="replay")

    for case_id in case_index:
        bundle = pipeline.run(case_id=case_id)
        assert isinstance(bundle, TrackAOutputBundle)

        # 1. Output contract types
        assert isinstance(bundle.package, KnowledgePackage)
        assert isinstance(bundle.rubric, RubricDefinition)
        assert isinstance(bundle.practice_task, PracticeTask)

        # 2. Canonical ID and semantic preservation (reconciliation item #3, #4, #5)
        raw_bundle = load_replay_bundle(cases_root, case_id)
        raw_pkg = raw_bundle["knowledge_package"]
        raw_rubric = raw_bundle["rubric"]
        raw_task = raw_bundle["practice_task"]

        assert bundle.package.package_id == raw_pkg["package_id"], (
            f"Case {case_id}: package_id must match canonical fixture {raw_pkg['package_id']}, got {bundle.package.package_id}"
        )
        assert bundle.rubric.rubric_id == raw_rubric["rubric_id"], (
            f"Case {case_id}: rubric_id must match canonical fixture {raw_rubric['rubric_id']}, got {bundle.rubric.rubric_id}"
        )
        assert bundle.practice_task.task_id == raw_task["task_id"], (
            f"Case {case_id}: task_id must match canonical fixture {raw_task['task_id']}, got {bundle.practice_task.task_id}"
        )

        # 3. Canonical replay bundle full 8-contract validation (reconciliation item #21)
        valid, errs = validate_transmission_bundle(raw_bundle)
        assert valid, f"Canonical bundle for {case_id} failed transmission bundle validation: {errs}"

        # 4. Case manifest alignment
        assert bundle.manifest.case_id == case_id
        assert bundle.package.skill_id is not None
        assert len(bundle.package.claims) > 0

        # 5. Cross-contract validation between Track A handoff outputs
        errs = validate_practice_task_against_knowledge_and_rubric(
            bundle.practice_task, bundle.package, bundle.rubric
        )
        assert not errs, f"Cross-contract errors in case {case_id}: {errs}"

        # 6. Handoff packet completeness
        assert bundle.consent_summary.contributor_name is not None
        assert isinstance(bundle.uncertainty_summary, list)
        assert "run_pipeline.py" in bundle.replay_command
        assert bundle.run_metadata.runtime_class == "REPLAY"


def test_pipeline_enforce_approved_flag(cases_root: Path) -> None:
    pipeline = TrackAPipeline(cases_root=cases_root, mode="replay")
    from models import FailureCategory, TrackAFailure

    with pytest.raises(TrackAFailure) as exc:
        pipeline.run(case_id="micrometer", enforce_approved=True)
    assert exc.value.category == FailureCategory.HUMAN_REVIEW_REQUIRED


def test_goal_conditioned_epistemic_invariants(cases_root: Path) -> None:
    """Reconciliation item #9: Kolam goal-conditioned mode preserves epistemic distinction.

    Observed target property != recovered original procedure.
    """
    pipeline = TrackAPipeline(cases_root=cases_root, mode="replay")
    bundle = pipeline.run(case_id="kolam")

    assert bundle.manifest.transmission_mode == "goal-conditioned"
    assert bundle.manifest.status == "ENGINEERING_FIXTURE"
    assert bundle.manifest.runtime_class == "REPLAY"

    # All claims in package must have valid evidence references
    for claim in bundle.package.claims:
        assert len(claim.evidence_refs) > 0
        for ev in claim.evidence_refs:
            if not claim.is_observed:
                assert ev.verification_state.value != "observed"
                assert ev.confidence <= 0.5


def test_canonical_data_drift_guard(repo_root: Path) -> None:
    """Reconciliation item #34: Prevent Track A from shadowing canonical case packs.

    tracks/cases/ is authoritative. Any Track A data/runs artifacts must remain
    purely implementation-specific execution traces, never authoritative case definitions.
    """
    cases_dir = repo_root / "tracks" / "cases"
    assert cases_dir.exists(), "Authoritative tracks/cases/ directory must exist"
    index_file = cases_dir / "index.json"
    assert index_file.exists(), "Case registry tracks/cases/index.json must exist"

    # Verify each case has manifest and bundle
    for case_id in ["micrometer", "kolam", "bicycle-repair", "handloom-weaving", "tabla", "origami", "square-knot"]:
        manifest_p = cases_dir / case_id / "manifest.json"
        bundle_p = cases_dir / case_id / "replay" / "bundle.json"
        assert manifest_p.exists(), f"Canonical manifest missing for {case_id}"
        assert bundle_p.exists(), f"Canonical bundle missing for {case_id}"

