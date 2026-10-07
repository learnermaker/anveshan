"""Self-consistency of the two-pass reference step matcher."""
from track_b.evaluators.universal import combine_matches


def test_agreement_keeps_stronger_confidence():
    a = {"seg-001": (0, "medium"), "seg-002": (1, "high")}
    b = {"seg-001": (0, "high"), "seg-002": (1, "low")}
    assert combine_matches(a, b) == {"seg-001": (0, "high"), "seg-002": (1, "high")}


def test_disagreement_is_dropped():
    a = {"seg-001": (0, "high"), "seg-002": (2, "high"), "seg-003": (None, "medium")}
    b = {"seg-001": (1, "high"), "seg-002": (None, "low"), "seg-003": (None, "low")}
    assert combine_matches(a, b) == {"seg-003": (None, "medium")}


def test_missing_in_second_pass_is_dropped():
    assert combine_matches({"seg-001": (0, "high")}, {}) == {}


def test_match_dto_is_lenient():
    from track_b.evaluators.universal import _match_dto
    dto = _match_dto().model_validate({"matches": [
        {"segment_id": "seg-001", "step": "Expert step 2", "confidence": "HIGH"},
        {"segment_id": "seg-002", "step": "null", "confidence": None},
        {"segment_id": "seg-003", "step": 1.0},
    ]})
    assert [(m.step, m.confidence) for m in dto.matches] == [(2, "high"), (None, "low"), (1, "low")]
