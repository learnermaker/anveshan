"""Authoring: GoalBuildResult -> versioned, validated case artifacts."""

import json

import pytest

from tracks.common import validator
from tracks.common.casedata import CriterionMap, GoalModel, Observers
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import KnowledgePackage, PracticeTask, RubricDefinition

from track_a import api, authoring
from track_a.authoring import ARTIFACTS

from ta_helpers import kolam_result


def _files(case_dir, version):
    return {stem: case_dir / sub / f"{stem}.v{version}.json" for stem, sub in ARTIFACTS.items()}


def test_build_writes_all_six_artifacts_and_validates(cases_root, fake_builder, make_ctx):
    case_dir = cases_root / "kolam"
    h = api.build_case(case_dir, make_ctx(case_dir))
    files = _files(case_dir, 1)
    assert all(p.exists() for p in files.values())
    assert fake_builder["calls"][0]["version"] == 1 and fake_builder["calls"][0]["case_id"] == "kolam"

    pkg = KnowledgePackage.model_validate_json(files["knowledge_package"].read_text(encoding="utf-8"))
    rubric = RubricDefinition.model_validate_json(files["rubric"].read_text(encoding="utf-8"))
    task = PracticeTask.model_validate_json(files["practice_task"].read_text(encoding="utf-8"))
    cmap = CriterionMap.model_validate_json(files["criterion_map"].read_text(encoding="utf-8"))
    obs = Observers.model_validate_json(files["observers"].read_text(encoding="utf-8"))
    goal = GoalModel.model_validate_json(files["goal_model"].read_text(encoding="utf-8"))
    assert validator.validate_practice_task_against_knowledge_and_rubric(task, pkg, rubric) == []

    assert pkg.package_id == "kp.kolam.1" and rubric.rubric_id == "rubric.kolam.1" and task.task_id == "task.kolam.1"
    assert pkg.skill_id == "skill.kolam" and rubric.skill_id == "skill.kolam"
    assert pkg.expert_review.status.value == "pending"
    assert pkg.consent.contributor_name == "Test Creator"
    assert pkg.consent.consent_scope == "public licence: Public domain"
    assert pkg.consent.revocable is False and pkg.consent.notes == "test image, public domain"
    assert rubric.passing_score == pytest.approx(0.7 * 5)
    assert [c.criterion_id for c in rubric.criteria] == ["CRIT-KOLAM-COVERAGE", "CRIT-KOLAM-DOTS"]
    assert task.target_criteria_ids == ["CRIT-KOLAM-COVERAGE", "CRIT-KOLAM-DOTS"]
    assert cmap.package_id == pkg.package_id and cmap.rubric_id == rubric.rubric_id
    assert obs.modality == "kolam_image" and obs.version == 1 and set(obs.criteria) == set(cmap.criteria)
    assert goal.modality == "kolam_image" and goal.source_ids == ["src.kolam.target.v1"]
    assert goal.built_with["run_keys"] == ["abc123"]

    assert h.review_status == "pending" and api.NOT_APPROVED_WARNING in h.warnings
    assert "test warning" in h.warnings
    assert h.runtime_label == "INTERNET_REFERENCE"


def test_versions_increment_and_earlier_versions_untouched(cases_root, fake_builder, make_ctx):
    case_dir = cases_root / "kolam"
    api.build_case(case_dir, make_ctx(case_dir))
    v1 = {k: p.read_bytes() for k, p in _files(case_dir, 1).items()}
    h2 = api.build_case(case_dir, make_ctx(case_dir))
    assert h2.package.package_id == "kp.kolam.2"
    assert fake_builder["calls"][1]["version"] == 2
    assert all(p.exists() for p in _files(case_dir, 2).values())
    assert {k: p.read_bytes() for k, p in _files(case_dir, 1).items()} == v1


def test_authoring_is_byte_deterministic(tmp_path, cases_root, fake_builder, make_ctx):
    import shutil

    other = tmp_path / "other" / "kolam"
    shutil.copytree(cases_root / "kolam", other)
    api.build_case(cases_root / "kolam", make_ctx(cases_root / "kolam"))
    api.build_case(other, make_ctx(other))
    for stem, p in _files(cases_root / "kolam", 1).items():
        assert p.read_bytes() == _files(other, 1)[stem].read_bytes(), stem
    text = _files(other, 1)["knowledge_package"].read_text(encoding="utf-8")
    assert text.endswith("\n") and json.loads(text)["package_id"] == "kp.kolam.1"


def test_passing_score_override_from_built_with(cases_root, fake_builder, make_ctx):
    fake_builder["result"] = kolam_result(built_with={"passing_score": 4.0})
    h = api.build_case(cases_root / "kolam", make_ctx(cases_root / "kolam"))
    assert h.rubric.passing_score == 4.0


def test_unknown_claim_in_template_is_contract_violation(cases_root, fake_builder, make_ctx):
    r = kolam_result()
    r.criteria[0].source_claim_ids = ["CLM-99"]
    fake_builder["result"] = r
    with pytest.raises(AnveshanFailure) as e:
        api.build_case(cases_root / "kolam", make_ctx(cases_root / "kolam"))
    assert e.value.category == FailureCategory.CONTRACT_VIOLATION
    assert not (cases_root / "kolam" / "knowledge" / "knowledge_package.v1.json").exists()


def test_task_citing_unknown_claim_is_rejected(cases_root, fake_builder, make_ctx):
    fake_builder["result"] = kolam_result(task_instructions="1. Do the thing [CLM-42].")
    with pytest.raises(AnveshanFailure) as e:
        api.build_case(cases_root / "kolam", make_ctx(cases_root / "kolam"))
    assert e.value.category == FailureCategory.CONTRACT_VIOLATION


def test_build_rejects_showcase_and_held_out_and_sha_mismatch(cases_root, fake_builder, make_ctx):
    with pytest.raises(AnveshanFailure) as e:
        api.build_case(cases_root / "micrometer", make_ctx(cases_root / "micrometer"))
    assert e.value.category == FailureCategory.INVALID_INPUT
    kolam = cases_root / "kolam"
    with pytest.raises(AnveshanFailure) as e:
        api.build_case(kolam, make_ctx(kolam), source_id="src.kolam.held_out.v1")
    assert e.value.category == FailureCategory.INVALID_INPUT
    (kolam / "source" / "target.png").write_bytes(b"tampered")
    with pytest.raises(AnveshanFailure) as e:
        api.build_case(kolam, make_ctx(kolam))
    assert e.value.category == FailureCategory.INVALID_INPUT
    assert fake_builder["calls"] == []


def test_next_version_spans_all_stems(cases_root, fake_builder, make_ctx):
    kolam = cases_root / "kolam"
    assert authoring.next_version(kolam) == 1
    api.build_case(kolam, make_ctx(kolam))
    assert authoring.next_version(kolam) == 2
