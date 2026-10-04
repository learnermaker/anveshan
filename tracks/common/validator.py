"""Deterministic validator utility for Anveshan contract schemas.

Validates:
1. Single JSON contracts against their individual Pydantic schemas.
2. Cross-contract invariants (Evaluation vs. Rubric, Feedback vs. Evaluation, Transmission vs. Attempts).
3. End-to-end transmission bundles (the complete 8-contract replay graph).

CLI Usage:
    # Single contract validation
    python -m tracks.common.validator path/to/rubric.json --type RubricDefinition

    # End-to-end replay bundle validation
    python -m tracks.common.validator path/to/bundle.json --bundle
    python -m tracks.common.validator path/to/fixture_directory/ --bundle
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Type, Union
from pydantic import BaseModel, ValidationError

from tracks.common.schemas import (
    EvidenceRef,
    KnowledgePackage,
    RubricDefinition,
    PracticeTask,
    LearnerAttempt,
    AttemptType,
    Evaluation,
    CriterionStatus,
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


# ---------------------------------------------------------------------------
# Cross-Contract Invariant Validators
# ---------------------------------------------------------------------------

def validate_evaluation_against_rubric(
    evaluation: Evaluation, rubric: RubricDefinition
) -> List[str]:
    """Validate cross-contract invariants between Evaluation and RubricDefinition."""
    errors = []

    if evaluation.rubric_id != rubric.rubric_id:
        errors.append(
            f"Evaluation rubric_id '{evaluation.rubric_id}' does not match RubricDefinition '{rubric.rubric_id}'"
        )

    rubric_criteria_map = {c.criterion_id: c for c in rubric.criteria}
    eval_criteria_ids = {cr.criterion_id for cr in evaluation.criterion_results}

    # 1. Unknown criteria in evaluation
    for cr in evaluation.criterion_results:
        if cr.criterion_id not in rubric_criteria_map:
            errors.append(
                f"Evaluation contains unknown criterion_id '{cr.criterion_id}' not found in RubricDefinition '{rubric.rubric_id}'"
            )
        else:
            rubric_crit = rubric_criteria_map[cr.criterion_id]
            # 2. Score must not exceed criterion weight (maximum points)
            if cr.score > rubric_crit.weight:
                errors.append(
                    f"Criterion '{cr.criterion_id}' score ({cr.score}) exceeds rubric max points ({rubric_crit.weight})"
                )

    # 3. All required criteria must be represented in evaluation
    for crit_id, crit in rubric_criteria_map.items():
        if crit.required and crit_id not in eval_criteria_ids:
            errors.append(
                f"Required rubric criterion '{crit_id}' ({crit.name}) is missing from Evaluation"
            )

    # 4. Passing status consistency
    if rubric.passing_score is not None:
        if evaluation.passed and evaluation.total_score < rubric.passing_score:
            errors.append(
                f"Evaluation.passed is True, but total_score ({evaluation.total_score}) is below rubric passing_score ({rubric.passing_score})"
            )

    # If any required criterion is explicitly NOT_SATISFIED, cannot be marked passed
    for cr in evaluation.criterion_results:
        if cr.criterion_id in rubric_criteria_map:
            if rubric_criteria_map[cr.criterion_id].required and cr.status == CriterionStatus.NOT_SATISFIED:
                if evaluation.passed:
                    errors.append(
                        f"Evaluation.passed is True, but required criterion '{cr.criterion_id}' is NOT_SATISFIED"
                    )

    return errors


def validate_practice_task_against_knowledge_and_rubric(
    task: PracticeTask, pkg: KnowledgePackage, rubric: RubricDefinition
) -> List[str]:
    """Validate cross-contract invariants between PracticeTask, KnowledgePackage, and Rubric."""
    errors = []

    if task.package_id != pkg.package_id:
        errors.append(
            f"PracticeTask package_id '{task.package_id}' does not match KnowledgePackage '{pkg.package_id}'"
        )
    if task.rubric_id != rubric.rubric_id:
        errors.append(
            f"PracticeTask rubric_id '{task.rubric_id}' does not match RubricDefinition '{rubric.rubric_id}'"
        )

    rubric_crit_ids = {c.criterion_id for c in rubric.criteria}
    for target_id in task.target_criteria_ids:
        if target_id not in rubric_crit_ids:
            errors.append(
                f"PracticeTask target_criteria_id '{target_id}' does not exist in RubricDefinition '{rubric.rubric_id}'"
            )

    return errors


def validate_feedback_against_evaluation(
    feedback: Feedback, evaluation: Evaluation
) -> List[str]:
    """Validate cross-contract invariants between Feedback and Evaluation."""
    errors = []

    if feedback.evaluation_id != evaluation.evaluation_id:
        errors.append(
            f"Feedback evaluation_id '{feedback.evaluation_id}' does not match Evaluation '{evaluation.evaluation_id}'"
        )
    if feedback.attempt_id != evaluation.attempt_id:
        errors.append(
            f"Feedback attempt_id '{feedback.attempt_id}' does not match Evaluation attempt_id '{evaluation.attempt_id}'"
        )

    eval_crit_ids = {cr.criterion_id for cr in evaluation.criterion_results}
    for item in feedback.items:
        if item.criterion_id not in eval_crit_ids:
            errors.append(
                f"Feedback item references criterion '{item.criterion_id}' not evaluated in Evaluation '{evaluation.evaluation_id}'"
            )

    for focus_id in feedback.recommended_retry_focus:
        if focus_id not in eval_crit_ids:
            errors.append(
                f"Feedback recommended_retry_focus references criterion '{focus_id}' not evaluated in Evaluation"
            )

    return errors


def validate_transmission_record_invariants(
    record: TransmissionRecord,
    task: PracticeTask,
    rubric: RubricDefinition,
    baseline_attempt: LearnerAttempt,
    retry_attempt: LearnerAttempt,
    baseline_eval: Evaluation,
    retry_eval: Evaluation,
) -> List[str]:
    """Validate full cross-contract integrity of the TransmissionRecord against underlying objects."""
    errors = []

    if record.package_id != task.package_id:
        errors.append(
            f"TransmissionRecord package_id '{record.package_id}' does not match PracticeTask package_id '{task.package_id}'"
        )
    if record.rubric_id != rubric.rubric_id:
        errors.append(
            f"TransmissionRecord rubric_id '{record.rubric_id}' does not match RubricDefinition '{rubric.rubric_id}'"
        )

    # Attempt type checks
    if baseline_attempt.attempt_type != AttemptType.BASELINE:
        errors.append(
            f"baseline_attempt '{baseline_attempt.attempt_id}' must have attempt_type BASELINE, got '{baseline_attempt.attempt_type}'"
        )
    if retry_attempt.attempt_type != AttemptType.RETRY:
        errors.append(
            f"retry_attempt '{retry_attempt.attempt_id}' must have attempt_type RETRY, got '{retry_attempt.attempt_type}'"
        )

    # Distinct attempt IDs
    if baseline_attempt.attempt_id == retry_attempt.attempt_id:
        errors.append("baseline_attempt_id and retry_attempt_id must be distinct")

    if record.baseline_attempt_id != baseline_attempt.attempt_id:
        errors.append(
            f"TransmissionRecord baseline_attempt_id '{record.baseline_attempt_id}' does not match baseline_attempt '{baseline_attempt.attempt_id}'"
        )
    if record.retry_attempt_id != retry_attempt.attempt_id:
        errors.append(
            f"TransmissionRecord retry_attempt_id '{record.retry_attempt_id}' does not match retry_attempt '{retry_attempt.attempt_id}'"
        )

    # Learner identity alignment
    if baseline_attempt.learner.participant_id != retry_attempt.learner.participant_id:
        errors.append(
            f"Learner ID mismatch between baseline '{baseline_attempt.learner.participant_id}' and retry '{retry_attempt.learner.participant_id}'"
        )
    if record.learner_id != baseline_attempt.learner.participant_id:
        errors.append(
            f"TransmissionRecord learner_id '{record.learner_id}' does not match attempt learner '{baseline_attempt.learner.participant_id}'"
        )

    # Score alignment
    if abs(record.baseline_score - baseline_eval.total_score) > 1e-4:
        errors.append(
            f"TransmissionRecord baseline_score ({record.baseline_score}) does not match baseline_eval total_score ({baseline_eval.total_score})"
        )
    if abs(record.retry_score - retry_eval.total_score) > 1e-4:
        errors.append(
            f"TransmissionRecord retry_score ({record.retry_score}) does not match retry_eval total_score ({retry_eval.total_score})"
        )

    # Criteria improved validation
    baseline_scores = {cr.criterion_id: cr.score for cr in baseline_eval.criterion_results}
    retry_scores = {cr.criterion_id: cr.score for cr in retry_eval.criterion_results}
    for crit_id in record.criteria_improved:
        b_score = baseline_scores.get(crit_id, 0.0)
        r_score = retry_scores.get(crit_id, 0.0)
        if r_score <= b_score:
            errors.append(
                f"Criterion '{crit_id}' listed in criteria_improved, but retry_score ({r_score}) <= baseline_score ({b_score})"
            )

    return errors


# ---------------------------------------------------------------------------
# End-to-End Bundle Validator
# ---------------------------------------------------------------------------

def validate_transmission_bundle(
    bundle_data: Dict[str, Any]
) -> Tuple[bool, List[str]]:
    """Validate a complete replay fixture bundle containing all transmission objects."""
    errors = []

    required_keys = [
        "knowledge_package",
        "rubric",
        "practice_task",
        "baseline_attempt",
        "baseline_evaluation",
        "feedback",
        "retry_attempt",
        "retry_evaluation",
        "transmission_record",
    ]
    for k in required_keys:
        if k not in bundle_data:
            errors.append(f"Missing required bundle key: '{k}'")

    if errors:
        return False, errors

    try:
        pkg = KnowledgePackage.model_validate(bundle_data["knowledge_package"])
        rubric = RubricDefinition.model_validate(bundle_data["rubric"])
        task = PracticeTask.model_validate(bundle_data["practice_task"])
        base_attempt = LearnerAttempt.model_validate(bundle_data["baseline_attempt"])
        base_eval = Evaluation.model_validate(bundle_data["baseline_evaluation"])
        feedback = Feedback.model_validate(bundle_data["feedback"])
        retry_attempt = LearnerAttempt.model_validate(bundle_data["retry_attempt"])
        retry_eval = Evaluation.model_validate(bundle_data["retry_evaluation"])
        record = TransmissionRecord.model_validate(bundle_data["transmission_record"])
    except ValidationError as ve:
        return False, [f"Contract schema validation error: {ve}"]

    # Run all cross-contract checks
    errors.extend(validate_practice_task_against_knowledge_and_rubric(task, pkg, rubric))
    errors.extend(validate_evaluation_against_rubric(base_eval, rubric))
    errors.extend(validate_evaluation_against_rubric(retry_eval, rubric))
    errors.extend(validate_feedback_against_evaluation(feedback, base_eval))
    errors.extend(
        validate_transmission_record_invariants(
            record, task, rubric, base_attempt, retry_attempt, base_eval, retry_eval
        )
    )

    return len(errors) == 0, errors


def load_bundle_from_directory(dir_path: Path) -> Dict[str, Any]:
    """Load individual JSON contract files from a directory into a bundle dictionary."""
    bundle: Dict[str, Any] = {}
    key_mapping = {
        "knowledge_package": ["knowledge_package.json", "knowledge.json"],
        "rubric": ["rubric.json", "rubric_definition.json"],
        "practice_task": ["practice_task.json", "task.json"],
        "baseline_attempt": ["baseline_attempt.json"],
        "baseline_evaluation": ["baseline_evaluation.json"],
        "feedback": ["feedback.json"],
        "retry_attempt": ["retry_attempt.json"],
        "retry_evaluation": ["retry_evaluation.json"],
        "transmission_record": ["transmission_record.json", "transmission.json"],
    }
    for key, file_names in key_mapping.items():
        found = False
        for fn in file_names:
            fp = dir_path / fn
            if fp.exists():
                bundle[key] = json.loads(fp.read_text(encoding="utf-8"))
                found = True
                break
        if not found:
            raise FileNotFoundError(
                f"Missing contract JSON for '{key}' in directory '{dir_path}'. Expected one of {file_names}"
            )
    return bundle


def validate_fixture_file(
    path: Path, expected_type: Optional[str] = None, is_bundle: bool = False
) -> Tuple[bool, str, Optional[Any]]:
    """Validate a JSON file or directory against contracts or bundle schema."""
    if not path.exists():
        return False, f"Path not found: {path}", None

    if is_bundle or path.is_dir():
        try:
            if path.is_dir():
                bundle_data = load_bundle_from_directory(path)
            else:
                bundle_data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            return False, f"Failed to load bundle: {e}", None

        valid, errs = validate_transmission_bundle(bundle_data)
        if valid:
            return True, f"Replay Bundle Valid ({path.name})", bundle_data
        else:
            return False, "Bundle validation errors:\n" + "\n".join(f" - {e}" for e in errs), None

    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except Exception as e:
        return False, f"Failed to parse JSON in {path}: {e}", None

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

    return False, "Validation failed:\n" + "\n".join(errors), None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate JSON fixtures against Anveshan schemas.")
    parser.add_argument("path", type=Path, help="Path to JSON file or fixture directory")
    parser.add_argument(
        "--type",
        "-t",
        choices=list(CONTRACT_REGISTRY.keys()),
        help="Expected contract type. If omitted, attempts auto-detection.",
    )
    parser.add_argument(
        "--bundle",
        "-b",
        action="store_true",
        help="Validate as a full transmission replay bundle or directory.",
    )
    args = parser.parse_args()

    success, message, _ = validate_fixture_file(
        args.path, expected_type=args.type, is_bundle=args.bundle
    )
    if success:
        print(f"PASS: {args.path} -> {message}")
        return 0
    else:
        print(f"FAIL: {args.path}\n{message}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
