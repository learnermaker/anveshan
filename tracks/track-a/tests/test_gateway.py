from pathlib import Path
import pytest
from gateway import ModelGateway
from models import ExtractionResponseDTO, FailureCategory, TrackAFailure


def test_model_gateway_replay_all_seven_cases(cases_root: Path, case_index: list[str]) -> None:
    gateway = ModelGateway(cases_root=cases_root, mode="replay")
    for case_id in case_index:
        dto = gateway.extract_knowledge(case_id)
        assert isinstance(dto, ExtractionResponseDTO)
        assert dto.case_id == case_id
        assert dto.run_metadata.runtime_class == "REPLAY"
        assert dto.run_metadata.provider == "replay"
        assert len(dto.steps) > 0 or len(dto.target_properties) > 0 or len(dto.conditions) > 0


def test_model_gateway_invalid_mode(cases_root: Path) -> None:
    with pytest.raises(TrackAFailure) as exc:
        ModelGateway(cases_root=cases_root, mode="unknown")  # type: ignore
    assert exc.value.category == FailureCategory.INVALID_INPUT


def test_model_gateway_live_mode_missing_api_key(cases_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    gateway = ModelGateway(cases_root=cases_root, mode="live", api_key=None)
    with pytest.raises(TrackAFailure) as exc:
        gateway.extract_knowledge("micrometer")
    assert exc.value.category == FailureCategory.MODEL_FAILURE
    assert "GEMINI_API_KEY not configured" in str(exc.value)
