"""Evidence query: citations validated, no fallback, deterministic refusal for goal-conditioned intent questions."""

import json

import pytest

from tracks.common.models import AnveshanFailure, FailureCategory, ModelError, RunStore
from tracks.common.runtime import RunContext

from track_a import api

from ta_helpers import FakeModels, REAL_CASES


@pytest.fixture
def built(cases_root, fake_builder, make_ctx):
    case_dir = cases_root / "kolam"
    api.build_case(case_dir, make_ctx(case_dir))
    return case_dir


def test_valid_citations_return_evidence(built, make_ctx):
    fm = FakeModels(json.dumps({"answer": "Keep clear of every dot (CLM-02).", "cited_claim_ids": ["CLM-02"], "sufficient": True}))
    r = api.answer_query(built, "How close can the line get to a dot?", make_ctx(built, models=fm))
    assert r["sufficient"] is True and r["cited_claim_ids"] == ["CLM-02"]
    assert [e["evidence_id"] for e in r["evidence"]] == ["ev.kolam.target.02"]
    assert r["run"]["runtime_class"] == "LIVE" and r["run"]["prompt_id"] == "evidence_query"
    assert r["run"]["package_id"] == "kp.kolam.1"
    assert len(fm.calls) == 1
    prompt = fm.calls[0]["contents"][-1]
    assert "CLM-02" in prompt and "How close can the line get to a dot?" in prompt


def test_answer_is_recorded_and_replayable(built, make_ctx, data_dir):
    fm = FakeModels(json.dumps({"answer": "Two curves (CLM-03).", "cited_claim_ids": ["CLM-03"], "sufficient": True}))
    q = "How many curves are there?"
    live = api.answer_query(built, q, make_ctx(built, models=fm))
    rec_ctx = RunContext.create(built, data_dir, "recorded")
    rec = api.answer_query(built, q, rec_ctx)
    assert rec["answer"] == live["answer"] and rec["run"]["runtime_class"] == "RECORDED_LIVE"
    with pytest.raises(ModelError) as e:
        api.answer_query(built, "A different question?", rec_ctx)
    assert e.value.category == FailureCategory.REPLAY_MISMATCH


def test_invalid_citation_is_insufficient(built, make_ctx):
    fm = FakeModels(json.dumps({"answer": "See CLM-77.", "cited_claim_ids": ["CLM-77"], "sufficient": True}))
    r = api.answer_query(built, "What colour is the powder?", make_ctx(built, models=fm))
    assert r["sufficient"] is False and r["cited_claim_ids"] == [] and r["evidence"] == []
    assert r["answer"].startswith("INSUFFICIENT_EVIDENCE:") and "CLM-77" in r["answer"]


def test_sufficient_without_citations_is_insufficient(built, make_ctx):
    fm = FakeModels(json.dumps({"answer": "Rice flour.", "cited_claim_ids": [], "sufficient": True}))
    r = api.answer_query(built, "What material is used?", make_ctx(built, models=fm))
    assert r["sufficient"] is False and r["answer"].startswith("INSUFFICIENT_EVIDENCE:")


def test_model_refusal_passes_through(built, make_ctx):
    fm = FakeModels(json.dumps({"answer": "INSUFFICIENT_EVIDENCE: the source does not show or document this.", "cited_claim_ids": [], "sufficient": False}))
    r = api.answer_query(built, "What material is used?", make_ctx(built, models=fm))
    assert r == {
        "answer": "INSUFFICIENT_EVIDENCE: the source does not show or document this.",
        "cited_claim_ids": [],
        "evidence": [],
        "sufficient": False,
        "run": r["run"],
    }


@pytest.mark.parametrize(
    "q",
    [
        "What did the artist intend with this pattern?",
        "What is the cultural meaning of this kolam?",
        "What is the history of this design?",
        "What was the original stroke order?",
        "Who drew this?",
    ],
)
def test_intent_questions_refused_without_model_call(built, make_ctx, q):
    fm = FakeModels("{}")
    r = api.answer_query(built, q, make_ctx(built, models=fm))
    assert r["sufficient"] is False and r["answer"].startswith("INSUFFICIENT_EVIDENCE:")
    assert r["run"]["runtime_class"] == "DETERMINISTIC"
    assert fm.calls == []


def test_forward_case_does_not_precheck(cases_root, make_ctx):
    case = cases_root / "micrometer"  # forward showcase: question goes to the model
    fm = FakeModels(json.dumps({"answer": "INSUFFICIENT_EVIDENCE: no.", "cited_claim_ids": [], "sufficient": False}))
    api.answer_query(case, "What is the history of micrometers?", make_ctx(case, models=fm))
    assert len(fm.calls) == 1


def test_empty_question_and_model_failure(built, make_ctx):
    with pytest.raises(AnveshanFailure) as e:
        api.answer_query(built, "   ", make_ctx(built))
    assert e.value.category == FailureCategory.INVALID_INPUT
    with pytest.raises(ModelError) as e:
        api.answer_query(built, "How many dots?", make_ctx(built, models=FakeModels("not json")))
    assert e.value.category == FailureCategory.MODEL_FAILURE
