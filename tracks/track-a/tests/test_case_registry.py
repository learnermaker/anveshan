from pathlib import Path
import pytest
from case_registry import (
    CaseManifest,
    discover_cases,
    load_manifest,
    load_replay_bundle,
    validate_manifest_semantics,
)


def test_discover_cases(cases_root: Path) -> None:
    cases = discover_cases(cases_root)
    assert len(cases) == 7
    expected = [
        "micrometer",
        "kolam",
        "bicycle-repair",
        "handloom-weaving",
        "tabla",
        "origami",
        "square-knot",
    ]
    assert cases == expected


def test_load_all_manifests(cases_root: Path, case_index: list[str]) -> None:
    for case_id in case_index:
        manifest = load_manifest(cases_root, case_id)
        assert isinstance(manifest, CaseManifest)
        assert manifest.case_id == case_id
        assert manifest.schema_version == "1.0"
        assert manifest.runtime_class in ("REPLAY", "AUTHENTIC")
        assert manifest.transmission_mode in ("forward", "goal-conditioned", "corrective")


def test_manifest_semantic_rules_violations() -> None:
    # Rule 1: runtime_class=REPLAY with status=AUTHENTIC_SOURCE_READY
    manifest_r1 = CaseManifest(
        schema_version="1.0",
        case_id="test",
        bundle_case_id="test_001",
        title="Test",
        domain="Test",
        archetype="test",
        workspace_type="test",
        transmission_mode="forward",
        source_posture="authentic_expert",
        epistemic_status="test",
        data_status="test",
        pack_version="1.0",
        case_version="1.0",
        status="AUTHENTIC_SOURCE_READY",
        source_mode="FORWARD",
        runtime_class="REPLAY",
    )
    failures_r1 = validate_manifest_semantics(manifest_r1)
    assert any("semantic rule 1" in f for f in failures_r1)

    # Rule 4: source_posture=synthetic_replay requires runtime_class=REPLAY and status=ENGINEERING_FIXTURE
    manifest_r4 = CaseManifest(
        schema_version="1.0",
        case_id="test",
        bundle_case_id="test_001",
        title="Test",
        domain="Test",
        archetype="test",
        workspace_type="test",
        transmission_mode="forward",
        source_posture="synthetic_replay",
        epistemic_status="test",
        data_status="test",
        pack_version="1.0",
        case_version="1.0",
        status="ENGINEERING_FIXTURE",
        source_mode="FORWARD",
        runtime_class="AUTHENTIC",
    )
    failures_r4 = validate_manifest_semantics(manifest_r4)
    assert any("semantic rule 4" in f for f in failures_r4)


def test_load_replay_bundles(cases_root: Path, case_index: list[str]) -> None:
    for case_id in case_index:
        bundle = load_replay_bundle(cases_root, case_id)
        assert isinstance(bundle, dict)
        assert "case_id" in bundle
        assert "knowledge_package" in bundle
        assert "rubric" in bundle
        assert "practice_task" in bundle
