from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Literal


@dataclass(frozen=True)
class CaseManifest:
    """Strongly typed representation of a case pack manifest.json."""

    schema_version: str
    case_id: str
    bundle_case_id: str
    title: str
    domain: str
    archetype: str
    workspace_type: str
    transmission_mode: Literal["forward", "goal-conditioned", "corrective"]
    source_posture: str
    epistemic_status: str
    data_status: str
    pack_version: str
    case_version: str
    status: Literal["ENGINEERING_FIXTURE", "AUTHENTIC_SOURCE_READY"]
    source_mode: Literal["FORWARD", "GOAL_CONDITIONED", "CORRECTIVE"]
    runtime_class: Literal["REPLAY", "AUTHENTIC"]


def discover_cases(cases_root: Path) -> List[str]:
    """Load case slugs from tracks/cases/index.json."""
    index_path = cases_root / "index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"Case registry index not found: {index_path}")
    data = json.loads(index_path.read_text(encoding="utf-8"))
    cases = data.get("cases", [])
    if not isinstance(cases, list):
        raise ValueError(f"Malformed cases list in {index_path}")
    return cases


def load_manifest(cases_root: Path, case_id: str) -> CaseManifest:
    """Load and parse manifest.json for a given case_id."""
    manifest_path = cases_root / case_id / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Case manifest not found: {manifest_path}")

    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = CaseManifest(
        schema_version=raw["schema_version"],
        case_id=raw["case_id"],
        bundle_case_id=raw["bundle_case_id"],
        title=raw["title"],
        domain=raw["domain"],
        archetype=raw["archetype"],
        workspace_type=raw["workspace_type"],
        transmission_mode=raw["transmission_mode"],
        source_posture=raw["source_posture"],
        epistemic_status=raw["epistemic_status"],
        data_status=raw["data_status"],
        pack_version=raw["pack_version"],
        case_version=raw["case_version"],
        status=raw["status"],
        source_mode=raw["source_mode"],
        runtime_class=raw["runtime_class"],
    )
    semantic_failures = validate_manifest_semantics(manifest)
    if semantic_failures:
        raise ValueError("\n".join(semantic_failures))
    return manifest


def validate_manifest_semantics(manifest: CaseManifest) -> List[str]:
    """Enforce the 4 cross-field semantic rules defined in manifest.schema.json."""
    failures: List[str] = []

    # Rule 1: runtime_class=REPLAY must not use status=AUTHENTIC_SOURCE_READY
    if manifest.runtime_class == "REPLAY" and manifest.status == "AUTHENTIC_SOURCE_READY":
        failures.append(
            f"Case {manifest.case_id} violates manifest semantic rule 1: "
            "runtime_class=REPLAY cannot have status=AUTHENTIC_SOURCE_READY"
        )

    # Rule 2: status=AUTHENTIC_SOURCE_READY requires source_posture=authentic_expert and runtime_class=AUTHENTIC
    if manifest.status == "AUTHENTIC_SOURCE_READY":
        if manifest.source_posture != "authentic_expert":
            failures.append(
                f"Case {manifest.case_id} violates manifest semantic rule 2: "
                "status=AUTHENTIC_SOURCE_READY requires source_posture=authentic_expert"
            )
        if manifest.runtime_class != "AUTHENTIC":
            failures.append(
                f"Case {manifest.case_id} violates manifest semantic rule 2: "
                "status=AUTHENTIC_SOURCE_READY requires runtime_class=AUTHENTIC"
            )

    # Rule 3: runtime_class=AUTHENTIC must not use status=ENGINEERING_FIXTURE
    if manifest.runtime_class == "AUTHENTIC" and manifest.status == "ENGINEERING_FIXTURE":
        failures.append(
            f"Case {manifest.case_id} violates manifest semantic rule 3: "
            "runtime_class=AUTHENTIC cannot have status=ENGINEERING_FIXTURE"
        )

    # Rule 4: source_posture=synthetic_replay requires runtime_class=REPLAY and status=ENGINEERING_FIXTURE
    if manifest.source_posture == "synthetic_replay":
        if manifest.runtime_class != "REPLAY" or manifest.status != "ENGINEERING_FIXTURE":
            failures.append(
                f"Case {manifest.case_id} violates manifest semantic rule 4: "
                "source_posture=synthetic_replay requires runtime_class=REPLAY and status=ENGINEERING_FIXTURE"
            )

    return failures


def load_replay_bundle(cases_root: Path, case_id: str) -> Dict[str, Any]:
    """Load the replay bundle JSON for a given case_id."""
    bundle_path = cases_root / case_id / "replay" / "bundle.json"
    if not bundle_path.exists():
        raise FileNotFoundError(f"Replay bundle not found: {bundle_path}")
    return json.loads(bundle_path.read_text(encoding="utf-8"))
