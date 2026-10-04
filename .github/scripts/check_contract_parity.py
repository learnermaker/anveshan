"""Mechanical parity check: canonical Pydantic schemas -> frontend TypeScript mirror.

The Python schemas under tracks/common/schemas/ are authoritative. This script
checks that app/src/types/contracts.ts preserves their model names, fields,
required/optional semantics, field shapes, and enum values.
"""
from __future__ import annotations

import importlib
import re
from enum import Enum
from pathlib import Path
from typing import Union, get_args, get_origin

ROOT = Path(__file__).resolve().parents[2]
TS_PATH = ROOT / "app" / "src" / "types" / "contracts.ts"

MODEL_MAP = {
    "EvidenceRef": ("tracks.common.schemas.evidence", "EvidenceRef"),
    "KnowledgePackage": ("tracks.common.schemas.knowledge", "KnowledgePackage"),
    "ConsentMetadata": ("tracks.common.schemas.knowledge", "ConsentMetadata"),
    "ExpertReview": ("tracks.common.schemas.knowledge", "ExpertReview"),
    "KnowledgeClaim": ("tracks.common.schemas.knowledge", "KnowledgeClaim"),
    "RubricDefinition": ("tracks.common.schemas.rubric", "RubricDefinition"),
    "RubricCriterion": ("tracks.common.schemas.rubric", "RubricCriterion"),
    "PracticeTask": ("tracks.common.schemas.practice", "PracticeTask"),
    "TaskConstraint": ("tracks.common.schemas.practice", "TaskConstraint"),
    "LearnerAttempt": ("tracks.common.schemas.attempt", "LearnerAttempt"),
    "ParticipantRef": ("tracks.common.schemas.attempt", "ParticipantRef"),
    "Evaluation": ("tracks.common.schemas.evaluation", "Evaluation"),
    "CriterionResult": ("tracks.common.schemas.evaluation", "CriterionResult"),
    "Feedback": ("tracks.common.schemas.feedback", "Feedback"),
    "FeedbackItem": ("tracks.common.schemas.feedback", "FeedbackItem"),
    "TransmissionRecord": ("tracks.common.schemas.transmission", "TransmissionRecord"),
    "LineageMetadata": ("tracks.common.schemas.transmission", "LineageMetadata"),
}

ENUM_MAP = {
    "Modality": ("tracks.common.schemas.evidence", "Modality"),
    "VerificationState": ("tracks.common.schemas.evidence", "VerificationState"),
    "ClaimType": ("tracks.common.schemas.knowledge", "ClaimType"),
    "ReviewStatus": ("tracks.common.schemas.knowledge", "ReviewStatus"),
    "AttemptType": ("tracks.common.schemas.attempt", "AttemptType"),
    "CriterionStatus": ("tracks.common.schemas.evaluation", "CriterionStatus"),
    "EvaluatorType": ("tracks.common.schemas.evaluation", "EvaluatorType"),
}

ROOT_CONTRACTS = (
    "EvidenceRef",
    "KnowledgePackage",
    "RubricDefinition",
    "PracticeTask",
    "LearnerAttempt",
    "Evaluation",
    "Feedback",
    "TransmissionRecord",
)


def unwrap_optional(annotation):
    args = get_args(annotation)
    origin = get_origin(annotation)
    if origin in (Union,):
        non_none = tuple(a for a in args if a is not type(None))
        if len(non_none) == 1 and len(args) == 2:
            return non_none[0], True
    return annotation, False


def py_shape(annotation) -> str:
    annotation, _ = unwrap_optional(annotation)
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is list:
        return f"{py_shape(args[0])}[]"
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation.__name__
    if isinstance(annotation, type):
        if annotation.__name__ in MODEL_MAP:
            return annotation.__name__
        return {
            str: "string",
            float: "number",
            int: "number",
            bool: "boolean",
        }.get(annotation, annotation.__name__)
    return str(annotation)


def load_canonical():
    models = {}
    for name, (module_name, attr) in MODEL_MAP.items():
        module = importlib.import_module(module_name)
        models[name] = getattr(module, attr)
    enums = {}
    for name, (module_name, attr) in ENUM_MAP.items():
        module = importlib.import_module(module_name)
        enums[name] = getattr(module, attr)
    return models, enums


def parse_ts(source: str):
    interfaces = {}
    for match in re.finditer(r"export interface (\w+)\s*\{(.*?)\n\}", source, re.S):
        fields = {}
        for line in match.group(2).splitlines():
            field = re.match(r"\s*(\w+)(\?)?\s*:\s*(.+?)\s*;\s*$", line)
            if field:
                fields[field.group(1)] = (
                    field.group(2) is not None,
                    field.group(3).strip(),
                )
        interfaces[match.group(1)] = fields

    aliases = {}
    for match in re.finditer(
        r"export type (\w+)\s*=\s*((?:\n\s*\|\s*[^;]+)+|[^;]+);",
        source,
    ):
        aliases[match.group(1)] = re.findall(r"'([^']+)'", match.group(2))
    return interfaces, aliases


def ts_shape(type_expr: str) -> str:
    expr = re.sub(r"\s+", " ", type_expr.strip())
    expr = re.sub(r"\s*\|\s*null\b", "", expr).strip()
    expr = re.sub(r"\s*\|\s*undefined\b", "", expr).strip()
    if expr.endswith("[]"):
        return f"{ts_shape(expr[:-2])}[]"
    return {
        "string": "string",
        "number": "number",
        "boolean": "boolean",
    }.get(expr, expr)


def main() -> int:
    if not TS_PATH.exists():
        print(f"CONTRACT PARITY: FAIL — missing {TS_PATH}")
        return 1

    interfaces, aliases = parse_ts(TS_PATH.read_text(encoding="utf-8"))
    models, enums = load_canonical()
    failures = []

    for root in ROOT_CONTRACTS:
        if root not in interfaces:
            failures.append(f"missing root interface: {root}")

    for name, model in models.items():
        if name not in interfaces:
            failures.append(f"missing interface: {name}")
            continue

        py_fields = model.model_fields
        ts_fields = interfaces[name]

        if set(py_fields) != set(ts_fields):
            failures.append(
                f"{name}: field set drift; "
                f"python={sorted(py_fields)} ts={sorted(ts_fields)}"
            )

        for field_name, field in py_fields.items():
            if field_name not in ts_fields:
                continue
            ts_optional, ts_expr = ts_fields[field_name]
            py_required = field.is_required()
            if py_required == ts_optional:
                failures.append(
                    f"{name}.{field_name}: requiredness drift "
                    f"(python required={py_required}, ts optional={ts_optional})"
                )

            expected = py_shape(field.annotation)
            actual = ts_shape(ts_expr)
            if expected != actual:
                failures.append(
                    f"{name}.{field_name}: shape drift "
                    f"(python={expected}, ts={actual})"
                )

    for name, enum in enums.items():
        expected = [member.value for member in enum]
        actual = aliases.get(name)
        if actual is None:
            failures.append(f"missing enum alias: {name}")
        elif expected != actual:
            failures.append(
                f"{name}: enum drift (python={expected}, ts={actual})"
            )

    if failures:
        print("CONTRACT PARITY: FAIL")
        print("\n".join(f"- {item}" for item in failures))
        return 1

    print("CONTRACT PARITY: PASS")
    print(
        f"Checked {len(ROOT_CONTRACTS)} root contracts, "
        f"{len(MODEL_MAP)} interfaces, {len(ENUM_MAP)} enums."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
