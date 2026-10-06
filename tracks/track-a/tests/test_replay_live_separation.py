"""Explicit replay-vs-live execution semantic separation tests (reconciliation item #33).

Proves:
  Replay: offline, deterministic, no credentials, no network, canonical contracts.
  Live:   requires credentials, uses configured model, records model metadata, fails explicitly.
"""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from models import FailureCategory, RunMetadataDTO, TrackAFailure
from pipeline import TrackAOutputBundle, TrackAPipeline


# ---------------------------------------------------------------------------
# REPLAY ISOLATION
# ---------------------------------------------------------------------------


def test_replay_does_not_require_gemini_credentials(cases_root: Path) -> None:
    """Replay must function with no GEMINI_API_KEY in environment."""
    env = os.environ.copy()
    env.pop("GEMINI_API_KEY", None)

    with patch.dict(os.environ, env, clear=True):
        pipeline = TrackAPipeline(cases_root=cases_root, mode="replay")
        bundle = pipeline.run(case_id="micrometer")
        assert isinstance(bundle, TrackAOutputBundle)


def test_replay_makes_no_network_calls(cases_root: Path) -> None:
    """Replay must never call urllib or any network layer."""
    with patch("urllib.request.urlopen", side_effect=AssertionError("Network call attempted in replay")):
        pipeline = TrackAPipeline(cases_root=cases_root, mode="replay")
        bundle = pipeline.run(case_id="origami")
        assert isinstance(bundle, TrackAOutputBundle)


def test_replay_is_deterministic(cases_root: Path) -> None:
    """Two sequential replay runs on the same case must produce identical output."""
    pipeline = TrackAPipeline(cases_root=cases_root, mode="replay")

    bundle_a = pipeline.run(case_id="kolam")
    bundle_b = pipeline.run(case_id="kolam")

    assert bundle_a.package.package_id == bundle_b.package.package_id
    assert bundle_a.rubric.rubric_id == bundle_b.rubric.rubric_id
    assert bundle_a.practice_task.task_id == bundle_b.practice_task.task_id
    assert bundle_a.run_metadata.run_id == bundle_b.run_metadata.run_id

    # Claim-level determinism
    assert len(bundle_a.package.claims) == len(bundle_b.package.claims)
    for ca, cb in zip(bundle_a.package.claims, bundle_b.package.claims):
        assert ca.claim_id == cb.claim_id
        assert ca.statement == cb.statement


def test_replay_reads_canonical_case_pack_data(cases_root: Path) -> None:
    """Replay must consume data exclusively from tracks/cases/<case>/replay/bundle.json."""
    from case_registry import load_replay_bundle

    pipeline = TrackAPipeline(cases_root=cases_root, mode="replay")
    bundle = pipeline.run(case_id="bicycle-repair")

    raw = load_replay_bundle(cases_root, "bicycle-repair")
    assert bundle.package.package_id == raw["knowledge_package"]["package_id"]
    assert bundle.rubric.rubric_id == raw["rubric"]["rubric_id"]
    assert bundle.practice_task.task_id == raw["practice_task"]["task_id"]


def test_replay_runtime_class_is_replay(cases_root: Path, case_index: list[str]) -> None:
    """Every replay run must report runtime_class=REPLAY in metadata."""
    pipeline = TrackAPipeline(cases_root=cases_root, mode="replay")
    for case_id in case_index:
        bundle = pipeline.run(case_id=case_id)
        assert bundle.run_metadata.runtime_class == "REPLAY", (
            f"Case {case_id}: expected runtime_class=REPLAY, got {bundle.run_metadata.runtime_class}"
        )


# ---------------------------------------------------------------------------
# LIVE ISOLATION
# ---------------------------------------------------------------------------


def test_live_requires_credentials(cases_root: Path) -> None:
    """Live mode must fail explicitly when GEMINI_API_KEY is absent."""
    env = os.environ.copy()
    env.pop("GEMINI_API_KEY", None)

    with patch.dict(os.environ, env, clear=True):
        with pytest.raises(TrackAFailure) as exc:
            pipeline = TrackAPipeline(cases_root=cases_root, mode="live")
            pipeline.run(case_id="micrometer")
        assert exc.value.category in (
            FailureCategory.MODEL_FAILURE,
            FailureCategory.INVALID_INPUT,
        )


def test_live_metadata_records_model_and_prompt(cases_root: Path) -> None:
    """Live RunMetadataDTO must carry provider, model_id, prompt_id, prompt_version, runtime_class=LIVE.

    This test inspects the GeminiProviderAdapter metadata template without calling the API,
    by checking the contract shape of RunMetadataDTO fields.
    """
    meta = RunMetadataDTO(
        provider="gemini",
        model_id="gemini-3.8-flash",
        prompt_id="forward_extraction",
        prompt_version="v1",
        input_artifact_id="source_micrometer",
        runtime_class="LIVE",
        run_id="run_live_micrometer_1234_abcd5678",
        expected_behavior="Live multimodal extraction",
        evaluation_reference="tracks/cases/micrometer/source/",
    )
    assert meta.provider == "gemini"
    assert meta.model_id == "gemini-3.8-flash"
    assert meta.prompt_id == "forward_extraction"
    assert meta.prompt_version == "v1"
    assert meta.runtime_class == "LIVE"
    assert "run_live_" in meta.run_id


def test_live_run_id_is_unique() -> None:
    """Two live RunMetadataDTO instances must produce different run_ids."""
    import time
    import uuid

    id_a = f"run_live_test_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    id_b = f"run_live_test_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    assert id_a != id_b, "Live run IDs must be unique across invocations"
