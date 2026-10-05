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
        """Execute Track A pipeline for a given case.

        Replay mode loads and validates authoritative canonical contracts directly
        from tracks/cases/<case_id>/replay/bundle.json, preserving canonical IDs and semantics.
        Live mode routes via ModelGateway -> normalizer -> grounding -> TaskGenerator.
        """
        manifest = load_manifest(self.cases_root, case_id)

        if self.mode == "replay":
            # -------------------------------------------------------------
            # REPLAY PATH: Load canonical contracts directly from bundle
            # -------------------------------------------------------------
            bundle_raw = load_replay_bundle(self.cases_root, case_id)
            pkg_raw = bundle_raw.get("knowledge_package")
            rubric_raw = bundle_raw.get("rubric")
            task_raw = bundle_raw.get("practice_task")

            if not pkg_raw or not rubric_raw or not task_raw:
                raise TrackAFailure(
                    FailureCategory.MISSING_EVIDENCE,
                    f"Canonical replay bundle for {case_id} missing required Track A contracts",
                )

            package = KnowledgePackage.model_validate(pkg_raw)
            rubric = RubricDefinition.model_validate(rubric_raw)
            practice_task = PracticeTask.model_validate(task_raw)

            # Grounding check on canonical package
            uncertainty = self.grounding.validate_package_grounding(
                package,
                transmission_mode=manifest.transmission_mode,
            )

            run_metadata = RunMetadataDTO(
                provider="replay",
                model_id="canonical-replay-fixture",
                prompt_id=f"{manifest.transmission_mode}_replay",
                prompt_version="canonical",
                input_artifact_id=f"bundle_{case_id}",
                runtime_class="REPLAY",
                run_id=f"run_replay_{case_id}",
                expected_behavior="Authoritative canonical contract preservation",
                evaluation_reference=f"tracks/cases/{case_id}/replay/bundle.json",
            )
        else:
            # -------------------------------------------------------------
            # LIVE PATH: Model extraction -> normalize -> ground -> generate
            # -------------------------------------------------------------
            dto = self.gateway.extract_knowledge(case_id)

            consent = ConsentMetadata(
                contributor_name=f"Expert for {case_id}",
                consent_scope="placeholder_no_real_consent",
            )

            package = normalize_dto_to_knowledge_package(dto=dto, consent=consent)

            uncertainty = self.grounding.validate_package_grounding(
                package,
                transmission_mode=manifest.transmission_mode,
            )

            rubric = self.task_generator.generate_rubric(package, case_id=case_id)
            practice_task = self.task_generator.generate_practice_task(package, rubric, case_id=case_id)
            run_metadata = dto.run_metadata

        # -----------------------------------------------------------------
        # Shared Review Status Gate
        # -----------------------------------------------------------------
        if enforce_approved:
            if not package.expert_review or package.expert_review.status != ReviewStatus.APPROVED:
                raise TrackAFailure(
                    FailureCategory.HUMAN_REVIEW_REQUIRED,
                    f"Production handoff requires ReviewStatus.APPROVED for case {case_id} (current: {package.expert_review.status if package.expert_review else 'NONE'})",
                    {"case_id": case_id, "status": package.expert_review.status if package.expert_review else None},
                )

        # -----------------------------------------------------------------
        # Cross-Contract Invariant Verification Before Handoff
        # -----------------------------------------------------------------
        errs = validate_practice_task_against_knowledge_and_rubric(practice_task, package, rubric)
        if errs:
            raise TrackAFailure(
                FailureCategory.CONTRACT_VIOLATION,
                f"Cross-contract alignment errors: {'; '.join(errs)}",
            )

        replay_cmd = f"python tracks/track-a/src/run_pipeline.py --case {case_id} --mode replay"

        return TrackAOutputBundle(
            package=package,
            rubric=rubric,
            practice_task=practice_task,
            run_metadata=run_metadata,
            manifest=manifest,
            consent_summary=package.consent,
            uncertainty_summary=uncertainty,
            replay_command=replay_cmd,
        )
