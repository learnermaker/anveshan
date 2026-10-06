"""Validate the cross-track capability case-pack layer.

Case packs are data, not a new contract seam. This check enforces stable IDs,
predictable pack structure, manifest/index parity, canonical manifest metadata,
and the presence of an atomic replay bundle.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tracks.common.schemas import (  # noqa: E402
    Evaluation,
    Feedback,
    KnowledgePackage,
    LearnerAttempt,
    PracticeTask,
    RubricDefinition,
    TransmissionRecord,
)

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "tracks" / "cases"
INDEX = CASES / "index.json"
MANIFEST_SCHEMA = CASES / "manifest.schema.json"

REQUIRED_BUNDLE = {
    "case_id",
    "domain",
    "skill",
    "knowledge_package",
    "rubric",
    "practice_task",
    "baseline_attempt",
    "baseline_evaluation",
    "feedback",
    "retry_attempt",
    "retry_evaluation",
    "transmission_record",
}


def validate_manifest(manifest: dict[str, Any], case_id: str, schema: dict[str, Any]) -> list[str]:
    """Validate the manifest subset needed by the repository's case-pack gate.

    This intentionally implements the small JSON-Schema subset used by the
    canonical manifest schema without adding a runtime dependency on a schema
    library. The schema remains the single source of truth for vocabulary.
    """
    failures: list[str] = []
    required = schema.get("required", [])
    missing = sorted(set(required) - set(manifest))
    if missing:
        failures.append(f"{case_id}: manifest missing {missing}")

    properties = schema.get("properties", {})
    unknown = sorted(set(manifest) - set(properties))
    if unknown:
        failures.append(f"{case_id}: manifest has unknown field(s) {unknown}")

    for field, definition in properties.items():
        if field not in manifest:
            continue
        value = manifest[field]
        expected_type = definition.get("type")
        if expected_type == "string" and not isinstance(value, str):
            failures.append(f"{case_id}: manifest.{field} must be a string")
            continue
        if isinstance(value, str):
            if "minLength" in definition and len(value) < definition["minLength"]:
                failures.append(f"{case_id}: manifest.{field} must not be empty")
            if "pattern" in definition:
                import re
                if not re.fullmatch(definition["pattern"], value):
                    failures.append(f"{case_id}: manifest.{field} has invalid format: {value!r}")
        if "const" in definition and value != definition["const"]:
            failures.append(
                f"{case_id}: manifest.{field}={value!r} must equal {definition['const']!r}"
            )
        if "enum" in definition and value not in definition["enum"]:
            allowed = ", ".join(repr(item) for item in definition["enum"])
            failures.append(
                f"{case_id}: manifest.{field}={value!r} is invalid; allowed values: {allowed}; "
                f"source: tracks/cases/manifest.schema.json"
            )

    if manifest.get("case_id") != case_id:
        failures.append(f"{case_id}: manifest.case_id mismatch")

    if manifest.get("runtime_class") == "REPLAY" and manifest.get("status") == "AUTHENTIC_SOURCE_READY":
        failures.append(
            f"{case_id}: manifest status AUTHENTIC_SOURCE_READY contradicts runtime_class REPLAY; "
            "replay is not authentic expert validation"
        )

    if manifest.get("status") == "AUTHENTIC_SOURCE_READY":
        if manifest.get("source_posture") != "authentic_expert":
            failures.append(
                f"{case_id}: status AUTHENTIC_SOURCE_READY requires "
                "source_posture=authentic_expert"
            )
        if manifest.get("runtime_class") != "AUTHENTIC":
            failures.append(
                f"{case_id}: status AUTHENTIC_SOURCE_READY requires runtime_class=AUTHENTIC"
            )

    if manifest.get("runtime_class") == "AUTHENTIC" and manifest.get("status") == "ENGINEERING_FIXTURE":
        failures.append(
            f"{case_id}: runtime_class AUTHENTIC contradicts status ENGINEERING_FIXTURE"
        )

    if manifest.get("source_posture") == "synthetic_replay":
        if manifest.get("runtime_class") != "REPLAY" or manifest.get("status") != "ENGINEERING_FIXTURE":
            failures.append(
                f"{case_id}: source_posture=synthetic_replay requires runtime_class=REPLAY and status=ENGINEERING_FIXTURE"
            )

    return failures


def main() -> int:
    failures: list[str] = []
    if not INDEX.exists():
        failures.append("missing tracks/cases/index.json")
        print("\n".join(failures))
        return 1
    if not MANIFEST_SCHEMA.exists():
        failures.append("missing tracks/cases/manifest.schema.json")
        print("\n".join(failures))
        return 1

    index = json.loads(INDEX.read_text(encoding="utf-8"))
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    ids = index.get("cases")
    if not isinstance(ids, list) or not ids or not all(isinstance(x, str) for x in ids):
        failures.append("index.json: cases must be a non-empty string list")
        ids = []

    if len(ids) != len(set(ids)):
        failures.append("index.json: duplicate case IDs")

    for case_id in ids:
        pack = CASES / case_id
        if not pack.is_dir():
            failures.append(f"{case_id}: missing case directory")
            continue

        manifest_path = pack / "manifest.json"
        bundle_path = pack / "replay" / "bundle.json"
        for required in (
            pack / "source" / "README.md",
            pack / "knowledge" / "README.md",
            pack / "practice" / "README.md",
            pack / "media" / "README.md",
        ):
            if not required.exists():
                failures.append(f"{case_id}: missing {required.relative_to(pack)}")

        if not manifest_path.exists():
            failures.append(f"{case_id}: missing manifest.json")
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        failures.extend(validate_manifest(manifest, case_id, schema))

        if not bundle_path.exists():
            failures.append(f"{case_id}: missing replay/bundle.json")
            continue

        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        missing = REQUIRED_BUNDLE - set(bundle)
        if missing:
            failures.append(f"{case_id}: replay bundle missing {sorted(missing)}")
        if bundle.get("case_id") is None:
            failures.append(f"{case_id}: replay bundle missing case_id")
        if manifest.get("bundle_case_id") != bundle.get("case_id"):
            failures.append(f"{case_id}: manifest.bundle_case_id does not match replay bundle.case_id")

        model_checks = [
            ("knowledge_package", KnowledgePackage),
            ("rubric", RubricDefinition),
            ("practice_task", PracticeTask),
            ("baseline_attempt", LearnerAttempt),
            ("baseline_evaluation", Evaluation),
            ("feedback", Feedback),
            ("retry_attempt", LearnerAttempt),
            ("retry_evaluation", Evaluation),
            ("transmission_record", TransmissionRecord),
        ]
        for field_name, model in model_checks:
            try:
                model.model_validate(bundle[field_name])
            except Exception as exc:
                failures.append(f"{case_id}: {field_name} fails canonical validation: {exc}")

    if failures:
        print("CASE PACKS: FAIL")
        print("\n".join(f"- {item}" for item in failures))
        return 1

    print(f"CASE PACKS: PASS ({len(ids)} packs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
