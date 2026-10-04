"""Validate the cross-track capability case-pack layer.

Case packs are data, not a new contract seam. This check enforces stable IDs,
predictable pack structure, manifest/index parity, and the presence of an
atomic replay bundle.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "tracks" / "cases"
INDEX = CASES / "index.json"

REQUIRED_MANIFEST = {
    "schema_version",
    "case_id",
    "title",
    "domain",
    "archetype",
    "workspace_type",
    "transmission_mode",
    "source_posture",
    "epistemic_status",
    "data_status",
    "pack_version",\n    "bundle_case_id",
}
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


def main() -> int:
    failures: list[str] = []
    if not INDEX.exists():
        failures.append("missing tracks/cases/index.json")
        print("\n".join(failures))
        return 1

    index = json.loads(INDEX.read_text(encoding="utf-8"))
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
        missing = REQUIRED_MANIFEST - set(manifest)
        if missing:
            failures.append(f"{case_id}: manifest missing {sorted(missing)}")
        if manifest.get("case_id") != case_id:
            failures.append(f"{case_id}: manifest.case_id mismatch")
        if manifest.get("source_posture") not in {"synthetic_replay", "external_reference", "owned_source", "authentic_expert"}:
            failures.append(f"{case_id}: invalid source_posture")

        if not bundle_path.exists():
            failures.append(f"{case_id}: missing replay/bundle.json")
            continue

        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        missing = REQUIRED_BUNDLE - set(bundle)
        if missing:
            failures.append(f"{case_id}: replay bundle missing {sorted(missing)}")
        if bundle.get("case_id") is None:
            failures.append(f"{case_id}: replay bundle missing case_id")

    if failures:
        print("CASE PACKS: FAIL")
        print("\n".join(f"- {item}" for item in failures))
        return 1

    print(f"CASE PACKS: PASS ({len(ids)} packs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
