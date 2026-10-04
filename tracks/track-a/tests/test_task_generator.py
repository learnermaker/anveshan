import pytest
from tracks.common.schemas import (
    ClaimType,
    ConsentMetadata,
    EvidenceRef,
    KnowledgeClaim,
    KnowledgePackage,
    Modality,
    PracticeTask,
    RubricDefinition,
)
from task_generator import TaskGenerator


@pytest.fixture
def sample_package() -> KnowledgePackage:
    ev1 = EvidenceRef(
        evidence_id="ev_01",
        source_id="video.mp4",
        modality=Modality.VIDEO,
        start_sec=4.5,
        end_sec=12.0,
        cue_excerpt="Single continuous wipe",
    )
    ev2 = EvidenceRef(
        evidence_id="ev_02",
        source_id="video.mp4",
        modality=Modality.AUDIO,
        start_sec=18.0,
        end_sec=22.5,
        cue_excerpt="3 uniform clicks",
    )
    return KnowledgePackage(
        package_id="kp.micrometer.1",
        skill_id="SKILL-OPT-CALIB",
        title="Micrometer Calibration",
        summary="Zeroing micrometer",
        claims=[
            KnowledgeClaim(
                claim_id="CLM-01",
                claim_type=ClaimType.STEP,
                statement="Clean anvil surfaces",
                is_observed=True,
                evidence_refs=[ev1],
            ),
            KnowledgeClaim(
                claim_id="CLM-02",
                claim_type=ClaimType.CUE,
                statement="Turn ratchet thimble until 3 clicks",
                is_observed=True,
                evidence_refs=[ev2],
            ),
        ],
        consent=ConsentMetadata(
            contributor_name="Marcus Vance",
            consent_scope="engineering_replay_only",
        ),
    )


def test_generate_rubric_and_task(sample_package: KnowledgePackage) -> None:
    gen = TaskGenerator()
    rubric = gen.generate_rubric(sample_package, case_id="micrometer")
    assert isinstance(rubric, RubricDefinition)
    assert rubric.rubric_id == "rubric.micrometer.1"
    assert len(rubric.criteria) == 2
    assert "source_claim_id: CLM-01" in rubric.criteria[0].description
    assert "source_claim_id: CLM-02" in rubric.criteria[1].description
    assert rubric.passing_score is not None
    assert rubric.passing_score <= rubric.max_possible_score

    task = gen.generate_practice_task(sample_package, rubric, case_id="micrometer")
    assert isinstance(task, PracticeTask)
    assert task.task_id == "task.micrometer.1"
    assert task.package_id == sample_package.package_id
    assert task.rubric_id == rubric.rubric_id
    assert set(task.target_criteria_ids) == {c.criterion_id for c in rubric.criteria}
