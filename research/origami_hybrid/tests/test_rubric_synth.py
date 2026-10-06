"""
Tests for RubricSynthesizer v1 (geometry-heuristic, offline).
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_COMMON = _REPO_ROOT / "tracks" / "common"
if str(_COMMON) not in sys.path:
    sys.path.insert(0, str(_COMMON))

from schemas.rubric import RubricDefinition, RubricCriterion
from schemas.practice import PracticeTask


def _load_checkpoints(tmp_path: Path):
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
        run_id="run_test",
    )
    return ad.load_checkpoints()


# ---------------------------------------------------------------------------
# TestRubricSynthesizer
# ---------------------------------------------------------------------------

class TestRubricSynthesizer:
    def test_synthesize_returns_rubric_definition(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        assert isinstance(rubric, RubricDefinition)

    def test_rubric_validates_against_pydantic(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        RubricDefinition.model_validate(rubric.model_dump())

    def test_exactly_five_criteria(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        assert len(rubric.criteria) == 5

    def test_criterion_ids_are_crit_hyb_n(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        ids = [c.criterion_id for c in rubric.criteria]
        assert ids == ["CRIT-HYB-1", "CRIT-HYB-2", "CRIT-HYB-3", "CRIT-HYB-4", "CRIT-HYB-5"]

    def test_no_canonical_criteria_ids(self, tmp_path: Path) -> None:
        """Must not use CRIT-CORNER-ALIGN, CRIT-VALLEY-FOLD, CRIT-BONE-CREASE."""
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        canonical = {"CRIT-CORNER-ALIGN", "CRIT-VALLEY-FOLD", "CRIT-BONE-CREASE"}
        ids = {c.criterion_id for c in rubric.criteria}
        assert ids.isdisjoint(canonical)

    def test_no_duplicate_criterion_ids(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        ids = [c.criterion_id for c in rubric.criteria]
        assert len(ids) == len(set(ids))

    def test_required_criteria_present(self, tmp_path: Path) -> None:
        """CRIT-HYB-1, 2, 5 are required; 3, 4 are optional."""
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        by_id = {c.criterion_id: c for c in rubric.criteria}
        assert by_id["CRIT-HYB-1"].required is True
        assert by_id["CRIT-HYB-2"].required is True
        assert by_id["CRIT-HYB-5"].required is True
        assert by_id["CRIT-HYB-3"].required is False
        assert by_id["CRIT-HYB-4"].required is False

    def test_weights_all_positive(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        for c in rubric.criteria:
            assert c.weight > 0.0

    def test_passing_score_le_max_score(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        assert rubric.passing_score is not None
        assert rubric.passing_score <= rubric.max_possible_score

    def test_passing_score_fraction(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer(passing_score_fraction=0.8).synthesize(cps)
        expected = round(rubric.max_possible_score * 0.8, 1)
        assert rubric.passing_score == pytest.approx(expected, abs=0.1)

    def test_observable_indicators_non_empty(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        for c in rubric.criteria:
            assert c.observable_indicator.strip() != ""

    def test_crit_hyb_2_mentions_mountain_or_valley(self, tmp_path: Path) -> None:
        """CRIT-HYB-2 observable indicator should reference M or V edges from geometry."""
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        by_id = {c.criterion_id: c for c in rubric.criteria}
        indicator = by_id["CRIT-HYB-2"].observable_indicator.lower()
        assert "mountain" in indicator or "valley" in indicator

    def test_crit_hyb_5_mentions_final_frame(self, tmp_path: Path) -> None:
        """CRIT-HYB-5 observable indicator should reference the final frame index."""
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps)
        by_id = {c.criterion_id: c for c in rubric.criteria}
        final_frame = cps[-1].frame_index
        assert str(final_frame) in by_id["CRIT-HYB-5"].observable_indicator

    def test_custom_rubric_id(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps, rubric_id="rubric.custom.1")
        assert rubric.rubric_id == "rubric.custom.1"

    def test_custom_skill_id(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        rubric = RubricSynthesizer().synthesize(cps, skill_id="skill-crane-test")
        assert rubric.skill_id == "skill-crane-test"

    def test_invalid_fraction_raises(self) -> None:
        from rubric_synth import RubricSynthesizer
        with pytest.raises(ValueError):
            RubricSynthesizer(passing_score_fraction=0.0)
        with pytest.raises(ValueError):
            RubricSynthesizer(passing_score_fraction=1.5)

    def test_empty_checkpoints_still_produces_rubric(self) -> None:
        """Synthesizer must not crash on empty checkpoint list."""
        from rubric_synth import RubricSynthesizer
        rubric = RubricSynthesizer().synthesize([])
        assert len(rubric.criteria) == 5
        RubricDefinition.model_validate(rubric.model_dump())


# ---------------------------------------------------------------------------
# TestPracticeTaskGenerator
# ---------------------------------------------------------------------------

class TestPracticeTaskGenerator:
    def test_generate_returns_practice_task(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        synth = RubricSynthesizer()
        rubric = synth.synthesize(cps)
        task = synth.generate_practice_task(rubric, package_id="kp.test.1")
        assert isinstance(task, PracticeTask)

    def test_task_validates_against_pydantic(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        synth = RubricSynthesizer()
        rubric = synth.synthesize(cps)
        task = synth.generate_practice_task(rubric, package_id="kp.test.1")
        PracticeTask.model_validate(task.model_dump())

    def test_task_package_id_matches(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        synth = RubricSynthesizer()
        rubric = synth.synthesize(cps)
        task = synth.generate_practice_task(rubric, package_id="kp.custom.1")
        assert task.package_id == "kp.custom.1"

    def test_task_rubric_id_matches(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        synth = RubricSynthesizer()
        rubric = synth.synthesize(cps)
        task = synth.generate_practice_task(rubric, package_id="kp.test.1")
        assert task.rubric_id == rubric.rubric_id

    def test_task_target_criteria_ids_all_present(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        synth = RubricSynthesizer()
        rubric = synth.synthesize(cps)
        task = synth.generate_practice_task(rubric, package_id="kp.test.1")
        rubric_ids = {c.criterion_id for c in rubric.criteria}
        assert set(task.target_criteria_ids) == rubric_ids

    def test_task_instructions_non_empty(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        synth = RubricSynthesizer()
        rubric = synth.synthesize(cps)
        task = synth.generate_practice_task(rubric, package_id="kp.test.1")
        assert task.instructions.strip() != ""

    def test_task_has_material_constraint(self, tmp_path: Path) -> None:
        from rubric_synth import RubricSynthesizer
        cps = _load_checkpoints(tmp_path)
        synth = RubricSynthesizer()
        rubric = synth.synthesize(cps)
        task = synth.generate_practice_task(rubric, package_id="kp.test.1")
        assert any(c.constraint_type == "material" for c in task.constraints)
