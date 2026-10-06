import pytest

from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import ReviewStatus

from track_b.handoff import expert_id, load_handoff, select_versions

from core_fixtures import make_case


def test_loads_consistent_case(tmp_path):
    h = load_handoff(make_case(tmp_path))
    assert h.case_id == "fakecase" and h.approved and h.warnings == []
    assert h.versions["rubric"] == 1
    assert h.expert_evidence("CRIT-A").evidence_id == "ev.ref.1"
    assert h.expert_evidence("CRIT-C") is None
    assert expert_id(h) == "Test Source (SYNTHETIC)"


def test_prefers_latest_approved_over_newer_pending(tmp_path):
    make_case(tmp_path, version=1, review=ReviewStatus.APPROVED)
    make_case(tmp_path, version=2, review=ReviewStatus.PENDING)
    assert select_versions(tmp_path / "fakecase")["knowledge_package"] == 1


def test_falls_back_to_latest_when_nothing_approved(tmp_path):
    make_case(tmp_path, version=1, review=ReviewStatus.PENDING)
    make_case(tmp_path, version=2, review=ReviewStatus.PENDING)
    h = load_handoff(tmp_path / "fakecase")
    assert h.versions["knowledge_package"] == 2
    assert not h.approved and any("not expert-approved" in w for w in h.warnings)


def test_all_rejected_requires_review(tmp_path):
    make_case(tmp_path, review=ReviewStatus.REJECTED)
    with pytest.raises(AnveshanFailure) as e:
        load_handoff(tmp_path / "fakecase")
    assert e.value.category == FailureCategory.HUMAN_REVIEW_REQUIRED


def _drop(key):
    def f(d):
        del d["criteria"][key]
    return f


@pytest.mark.parametrize("mutate", [
    {"observers": _drop("CRIT-B")},
    {"criterion_map": _drop("CRIT-C")},
    {"observers": lambda d: d.update(rubric_id="rubric.other.1")},
    {"criterion_map": lambda d: d["criteria"]["CRIT-A"].update(reference_evidence_ids=["ev.nope"])},
    {"criterion_map": lambda d: d["criteria"].update(EXTRA=dict(d["criteria"]["CRIT-A"]))},
    {"practice_task": lambda d: d.update(package_id="kp.other.1")},
    {"goal_model": lambda d: d.update(modality="tabla_audio")},
])
def test_inconsistent_case_is_contract_violation(tmp_path, mutate):
    case = make_case(tmp_path, mutate=mutate)
    with pytest.raises(AnveshanFailure) as e:
        load_handoff(case)
    assert e.value.category == FailureCategory.CONTRACT_VIOLATION


def test_missing_case_is_contract_violation(tmp_path):
    with pytest.raises(AnveshanFailure) as e:
        load_handoff(tmp_path / "nothing")
    assert e.value.category == FailureCategory.CONTRACT_VIOLATION
