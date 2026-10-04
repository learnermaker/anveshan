from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal, Optional

from tracks.common.schemas import (
    ConsentMetadata,
    KnowledgePackage,
    PracticeTask,
    ReviewStatus,
    RubricDefinition,
)
from tracks.common.validator import validate_practice_task_against_knowledge_and_rubric
from case_registry import CaseManifest, load_manifest, load_replay_bundle
from expert_review import ExpertReviewService
from gateway import ModelGateway
from grounding import GroundingService
from models import (
    FailureCategory,
    RunMetadataDTO,
    TrackAFailure,
    normalize_dto_to_knowledge_package,
)
from task_generator import TaskGenerator


@dataclass
class TrackAOutputBundle:
    """Canonical handoff bundle emitted by TrackAPipeline for Track B and UI."""

    package: KnowledgePackage
    rubric: RubricDefinition
    practice_task: PracticeTask
    run_metadata: RunMetadataDTO
    manifest: CaseManifest
    consent_summary: ConsentMetadata
    uncertainty_summary: List[str]
    replay_command: str


class TrackAPipeline:
    """Track A execution pipeline orchestrating Spec 1-9 across all 3 transmission modes."""

    def __init__(
        self,
        cases_root: Path,
        mode: Literal["replay", "live"] = "replay",
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.cases_root = cases_root
        self.mode = mode
        self.gateway = ModelGateway(cases_root=cases_root, mode=mode, model_id=model_id, api_key=api_key)
        self.grounding = GroundingService()
        self.expert_review_service = ExpertReviewService()
        self.task_generator = TaskGenerator()

    def run(
        self,
        case_id: str,
        enforce_approved: bool = False,
    ) -> TrackAOutputBundle:
        """Execute full Track A pipeline for a given case."""
        manifest = load_manifest(self.cases_root, case_id)

        # 1. Gateway extraction (DTO isolation)
        dto = self.gateway.extract_knowledge(case_id)

        # 2. Consent loading
        if self.mode == "replay":
            bundle_raw = load_replay_bundle(self.cases_root, case_id)
            pkg_raw = bundle_raw.get("knowledge_package", {})
            consent_raw = pkg_raw.get("consent", {})
            consent = ConsentMetadata(
                contributor_name=consent_raw.get("contributor_name", "Reference Expert (Synthetic Fixture)"),
                consent_scope=consent_raw.get("consent_scope", "engineering_replay_only"),
                revocable=consent_raw.get("revocable", True),
                granted_at=consent_raw.get("granted_at"),
                notes=consent_raw.get("notes"),
            )
        else:
            consent = ConsentMetadata(
                contributor_name=f"Expert for {case_id}",
                consent_scope="prototype_demonstration",
            )

        # 3. Normalization into canonical KnowledgePackage
        package = normalize_dto_to_knowledge_package(dto=dto, consent=consent)

        # 4. Mode-aware Epistemological Grounding
        uncertainty = self.grounding.validate_package_grounding(
            package,
            transmission_mode=manifest.transmission_mode,
        )

        # 5. Expert Review gate
        if enforce_approved:
            if not package.expert_review or package.expert_review.status != ReviewStatus.APPROVED:
                raise TrackAFailure(
                    FailureCategory.HUMAN_REVIEW_REQUIRED,
                    f"Production handoff requires ReviewStatus.APPROVED for case {case_id} (current: {package.expert_review.status if package.expert_review else 'NONE'})",
                    {"case_id": case_id, "status": package.expert_review.status if package.expert_review else None},
                )

        # 6. Synthesize Rubric & PracticeTask
        rubric = self.task_generator.generate_rubric(package, case_id=case_id)
        task = self.task_generator.generate_practice_task(package, rubric, case_id=case_id)

        # Enforce cross-contract validity before handoff
        errs = validate_practice_task_against_knowledge_and_rubric(task, package, rubric)
        if errs:
            raise TrackAFailure(
                FailureCategory.CONTRACT_VIOLATION,
                f"Cross-contract alignment errors: {'; '.join(errs)}",
            )

        replay_cmd = f"python tracks/track-a/src/run_pipeline.py --case {case_id} --mode replay"

        return TrackAOutputBundle(
            package=package,
            rubric=rubric,
            practice_task=task,
            run_metadata=dto.run_metadata,
            manifest=manifest,
            consent_summary=package.consent,
            uncertainty_summary=uncertainty,
            replay_command=replay_cmd,
        )
