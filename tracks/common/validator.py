"""Deterministic validator utility for Anveshan contract schemas.

Validates JSON dictionaries or fixture files against the authoritative 8 contracts.
Can be used programmatically or run directly as a CLI tool:

    python -m tracks.common.validator path/to/fixture.json --type KnowledgePackage
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Type
from pydantic import BaseModel, ValidationError

from tracks.common.schemas import (
    EvidenceRef,
    KnowledgePackage,
    RubricDefinition,
    PracticeTask,
    LearnerAttempt,
    Evaluation,
    Feedback,
    TransmissionRecord,
)

CONTRACT_REGISTRY: Dict[str, Type[BaseModel]] = {
    "EvidenceRef": EvidenceRef,
    "KnowledgePackage": KnowledgePackage,
    "RubricDefinition": RubricDefinition,
    "PracticeTask": PracticeTask,
    "LearnerAttempt": LearnerAttempt,
    "Evaluation": Evaluation,
    "Feedback": Feedback,
    "TransmissionRecord": TransmissionRecord,
}


def get_contract_class(contract_name: str) -> Type[BaseModel]:
    """Retrieve contract class by name."""
    if contract_name not in CONTRACT_REGISTRY:
        valid_names = ", ".join(sorted(CONTRACT_REGISTRY.keys()))
        raise ValueError(f"Unknown contract type '{contract_name}'. Valid contracts: {valid_names}")
    return CONTRACT_REGISTRY[contract_name]


def validate_contract(data: Dict[str, Any], contract_type: str) -> BaseModel:
    """Validate a Python dict against a specified contract schema."""
    cls = get_contract_class(contract_type)
    return cls.model_validate(data)


def validate_fixture_file(
    file_path: Path, expected_type: Optional[str] = None
) -> Tuple[bool, str, Optional[BaseModel]]:
    """Validate a JSON file on disk against a contract schema.

    Returns:
        (is_valid, message, parsed_instance)
    """
    if not file_path.exists():
        return False, f"File not found: {file_path}", None

    try:
        content = file_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except Exception as e:
        return False, f"Failed to parse JSON in {file_path}: {e}", None

    if expected_type:
        target_types = [expected_type]
    else:
        target_types = list(CONTRACT_REGISTRY.keys())

    errors = []
    for t_name in target_types:
        cls = CONTRACT_REGISTRY[t_name]
        try:
            instance = cls.model_validate(data)
            return True, f"Valid {t_name}", instance
        except ValidationError as ve:
            errors.append(f"[{t_name}]: {ve}")

    return False, f"Validation failed:\n" + "\n".join(errors), None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate JSON fixtures against Anveshan schemas.")
    parser.add_argument("file", type=Path, help="Path to JSON file to validate")
    parser.add_argument(
        "--type",
        "-t",
        choices=list(CONTRACT_REGISTRY.keys()),
        help="Expected contract type. If omitted, attempts to auto-detect.",
    )
    args = parser.parse_args()

    success, message, _ = validate_fixture_file(args.file, args.type)
    if success:
        print(f"PASS: {args.file} -> {message}")
        return 0
    else:
        print(f"FAIL: {args.file}\n{message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
