"""Regression tests for case-pack manifest metadata validation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import check_case_packs


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "tracks" / "cases" / "manifest.schema.json").read_text(encoding="utf-8"))


def manifest(**overrides):
    value = {
        "schema_version": "1.0",
        "case_id": "example-case",
        "bundle_case_id": "example_case_001",
        "title": "Example",
        "domain": "Example domain",
        "archetype": "example",
        "workspace_type": "example",
        "transmission_mode": "forward",
        "source_posture": "synthetic_replay",
        "epistemic_status": "REPLAY_FIXTURE_NOT_AUTHENTIC_VALIDATION",
        "data_status": "prototype_replay",
        "pack_version": "1.0",
        "case_version": "1.0",
        "status": "ENGINEERING_FIXTURE",
        "source_mode": "FORWARD",
        "runtime_class": "REPLAY",
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize(
    "posture",
    ["synthetic_replay", "external_reference", "owned_source", "authentic_expert"],
)
def test_allowed_source_postures(posture):
    value = manifest(source_posture=posture)
    if posture == "authentic_expert":
        value.update(status="ENGINEERING_FIXTURE", runtime_class="REPLAY")
    assert check_case_packs.validate_manifest(value, "example-case", SCHEMA) == []


def test_historical_invalid_source_posture_is_rejected():
    failures = check_case_packs.validate_manifest(
        manifest(source_posture="external_source_plus_replay_fixture"),
        "example-case",
        SCHEMA,
    )
    assert any("source_posture" in failure and "external_source_plus_replay_fixture" in failure for failure in failures)


def test_replay_cannot_claim_authentic_source_ready():
    failures = check_case_packs.validate_manifest(
        manifest(source_posture="external_reference", status="AUTHENTIC_SOURCE_READY"),
        "example-case",
        SCHEMA,
    )
    assert any("AUTHENTIC_SOURCE_READY" in failure and "REPLAY" in failure for failure in failures)


def test_authentic_source_ready_requires_authentic_expert_and_non_replay():
    failures = check_case_packs.validate_manifest(
        manifest(source_posture="authentic_expert", status="AUTHENTIC_SOURCE_READY", runtime_class="REPLAY"),
        "example-case",
        SCHEMA,
    )
    assert any("runtime_class" in failure for failure in failures)


def test_schema_unknown_field_is_rejected():
    failures = check_case_packs.validate_manifest(manifest(unknown_field="x"), "example-case", SCHEMA)
    assert any("unknown field" in failure for failure in failures)
