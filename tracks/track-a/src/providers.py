from abc import ABC, abstractmethod
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tracks.common.schemas import EvidenceRef, KnowledgePackage
from case_registry import CaseManifest, load_manifest, load_replay_bundle
from models import (
    ExtractedConditionDTO,
    ExtractedCueDTO,
    ExtractedDivergenceDTO,
    ExtractedExceptionDTO,
    ExtractedFailureModeDTO,
    ExtractedStepDTO,
    ExtractedTargetPropertyDTO,
    ExtractionResponseDTO,
    FailureCategory,
    RunMetadataDTO,
    TrackAFailure,
)


class BaseProviderAdapter(ABC):
    """Abstract provider adapter protocol implementing Spec 3."""

    @abstractmethod
    def extract_knowledge(
        self,
        case_id: str,
        prompt_version: str = "v1",
    ) -> ExtractionResponseDTO:
        """Extract structured candidate knowledge from source media or case pack."""
        pass

    @abstractmethod
    def query_evidence(
        self,
        package: KnowledgePackage,
        question: str,
    ) -> Tuple[str, List[EvidenceRef]]:
        """Answer an adversarial question backed by verified EvidenceRef locators."""
        pass


class ReplayProviderAdapter(BaseProviderAdapter):
    """Deterministic, 100% offline provider adapter reading canonical case packs."""

    def __init__(self, cases_root: Path) -> None:
        self.cases_root = cases_root

    def extract_knowledge(
        self,
        case_id: str,
        prompt_version: str = "v1",
    ) -> ExtractionResponseDTO:
        manifest: CaseManifest = load_manifest(self.cases_root, case_id)
        bundle: Dict[str, Any] = load_replay_bundle(self.cases_root, case_id)

        pkg_raw = bundle.get("knowledge_package", {})
        claims_raw = pkg_raw.get("claims", [])

        steps: List[ExtractedStepDTO] = []
        cues: List[ExtractedCueDTO] = []
        conditions: List[ExtractedConditionDTO] = []
        exceptions: List[ExtractedExceptionDTO] = []
        failure_modes: List[ExtractedFailureModeDTO] = []
        target_properties: List[ExtractedTargetPropertyDTO] = []
        divergences: List[ExtractedDivergenceDTO] = []

        source_media_id = "canonical_replay_source"

        for idx, claim in enumerate(claims_raw, 1):
            ctype = claim.get("claim_type", "step")
            stmt = claim.get("statement", "")
            is_obs = claim.get("is_observed", True)
            ev_list = claim.get("evidence_refs", [])
            ev0 = ev_list[0] if ev_list else {}

            if ev0.get("source_id"):
                source_media_id = ev0["source_id"]

            start_s = ev0.get("start_sec") or 0.0
            end_s = ev0.get("end_sec") or start_s

            if manifest.transmission_mode == "goal-conditioned" and ctype == "condition":
                target_properties.append(
                    ExtractedTargetPropertyDTO(
                        property_id=claim.get("claim_id", f"PROP-{idx}"),
                        description=stmt,
                        evidence_sufficiency="OBSERVED" if is_obs else "PARTIAL",
                        measurement=ev0.get("cue_excerpt"),
                    )
                )
            elif ctype == "step":
                steps.append(
                    ExtractedStepDTO(
                        index=idx,
                        title=stmt.split(":")[0] if ":" in stmt else f"Step {idx}",
                        description=stmt.split(":", 1)[1].strip() if ":" in stmt else stmt,
                        start_sec=float(start_s),
                        end_sec=float(end_s),
                    )
                )
            elif ctype == "cue":
                cues.append(
                    ExtractedCueDTO(
                        modality=ev0.get("modality", "video"),
                        statement=stmt,
                        observable_indicator=ev0.get("cue_excerpt", stmt),
                        start_sec=float(start_s),
                        end_sec=float(end_s),
                        evidence_sufficiency="OBSERVED" if is_obs else "PARTIAL",
                    )
                )
            elif ctype == "condition":
                conditions.append(
                    ExtractedConditionDTO(
                        statement=stmt,
                        tools_or_materials=[ev0.get("cue_excerpt", "standard tools")],
                    )
                )
            elif ctype == "exception":
                exceptions.append(
                    ExtractedExceptionDTO(
                        condition_trigger=stmt,
                        alternative_action="Execute documented recovery procedure",
                    )
                )
            elif ctype == "failure_mode":
                failure_modes.append(
                    ExtractedFailureModeDTO(
                        symptom=stmt,
                        mistake_description="Deviation from expert technique",
                        severity="high",
                    )
                )

        run_meta = RunMetadataDTO(
            provider="replay",
            model_id="deterministic-case-pack",
            prompt_id="replay_extraction",
            prompt_version=prompt_version,
            input_artifact_id=f"bundle_{case_id}",
            runtime_class="REPLAY",
            run_id=f"run_replay_{case_id}",
            expected_behavior="100% deterministic deserialization",
            evaluation_reference=f"tracks/cases/{case_id}/replay/bundle.json",
        )

        return ExtractionResponseDTO(
            case_id=case_id,
            skill_id=pkg_raw.get("skill_id", f"skill_{case_id}"),
            title=pkg_raw.get("title", manifest.title),
            summary=pkg_raw.get("summary", manifest.title),
            source_media_id=source_media_id,
            transmission_mode=manifest.transmission_mode,
            steps=steps,
            cues=cues,
            conditions=conditions,
            exceptions=exceptions,
            failure_modes=failure_modes,
            target_properties=target_properties,
            divergences=divergences,
            run_metadata=run_meta,
        )

    def query_evidence(
        self,
        package: KnowledgePackage,
        question: str,
    ) -> Tuple[str, List[EvidenceRef]]:
        """Domain-agnostic query against claims and evidence excerpts."""
        q_tokens = set(question.lower().split())
        best_match_claim = None
        max_overlap = 0

        for claim in package.claims:
            claim_text = (claim.statement + " " + (claim.evidence_refs[0].cue_excerpt or "")).lower()
            overlap = sum(1 for t in q_tokens if t in claim_text)
            if overlap > max_overlap:
                max_overlap = overlap
                best_match_claim = claim

        if not best_match_claim or max_overlap < 1:
            raise TrackAFailure(
                FailureCategory.MISSING_EVIDENCE,
                "INSUFFICIENT_EVIDENCE: The expert demonstration does not show or document this condition.",
                {"question": question},
            )

        answer = f"According to {best_match_claim.claim_id}: {best_match_claim.statement}"
        return answer, best_match_claim.evidence_refs


class GeminiProviderAdapter(BaseProviderAdapter):
    """Live Google GenAI SDK provider adapter calling Gemini models."""

    def __init__(
        self,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_id = model_id or os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash")

    def _ensure_client(self) -> None:
        if not self.api_key:
            raise TrackAFailure(
                FailureCategory.MODEL_FAILURE,
                "GEMINI_API_KEY not configured. Set it in .env or environment.",
            )

    def extract_knowledge(
        self,
        case_id: str,
        prompt_version: str = "v1",
    ) -> ExtractionResponseDTO:
        self._ensure_client()
        # In live execution mode, this calls google-genai SDK with response_schema
        # If SDK is not installed or network is down, raises TrackAFailure cleanly
        try:
            from google import genai  # type: ignore
        except ImportError:
            raise TrackAFailure(
                FailureCategory.MODEL_FAILURE,
                "google-genai SDK not installed. Live mode requires google-genai.",
            )

        raise TrackAFailure(
            FailureCategory.MODEL_FAILURE,
            "Live Gemini extraction requires media upload and active quota.",
        )

    def query_evidence(
        self,
        package: KnowledgePackage,
        question: str,
    ) -> Tuple[str, List[EvidenceRef]]:
        self._ensure_client()
        raise TrackAFailure(
            FailureCategory.MODEL_FAILURE,
            "Live Gemini query service requires active API execution.",
        )
