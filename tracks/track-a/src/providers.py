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
    """Live Google GenAI SDK provider adapter calling Gemini models (Spec 3)."""

    def __init__(
        self,
        cases_root: Path,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.cases_root = cases_root
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_id = model_id or os.environ.get("GEMINI_MODEL_ID", "gemini-2.5-flash")
        self._client: Optional[Any] = None

    def _ensure_client(self) -> Any:
        if not self.api_key:
            raise TrackAFailure(
                FailureCategory.MODEL_FAILURE,
                "GEMINI_API_KEY not configured. Set it in .env or environment.",
            )
        if self._client is None:
            try:
                from google import genai
                from google.genai import types

                self._client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(timeout=60_000),
                )
            except ImportError:
                raise TrackAFailure(
                    FailureCategory.MODEL_FAILURE,
                    "google-genai SDK not installed. Live mode requires google-genai.",
                )
            except Exception as exc:
                raise TrackAFailure(
                    FailureCategory.MODEL_FAILURE,
                    f"Failed to initialize google.genai Client: {exc}",
                ) from exc
        return self._client

    def extract_knowledge(
        self,
        case_id: str,
        prompt_version: str = "v1",
    ) -> ExtractionResponseDTO:
        """
        Live multimodal extraction via Google GenAI SDK:
        1. Discover and upload case source media via MediaService
        2. Load and render prompt template via PromptEngine
        3. Call Gemini with response_schema=GeminiExtractionResponse
        4. Map structured response to ExtractionResponseDTO with manifest context
        """
        from google.genai import types as genai_types
        from gemini_schemas import GeminiExtractionResponse
        from media_service import MediaService
        from prompt_engine import PromptEngine
        from gemini_retry import with_gemini_retry

        client = self._ensure_client()
        manifest: CaseManifest = load_manifest(self.cases_root, case_id)

        media_service = MediaService(self.cases_root, client=client)
        media_descriptor = media_service.discover_media(case_id)
        local_media_path = media_service.resolve_media_path(case_id, media_descriptor)

        # Upload media to Gemini Files API
        gemini_file = media_service.upload_to_gemini(
            local_media_path,
            mime_type=media_descriptor.mime_type,
        )

        try:
            prompt_engine = PromptEngine()
            rendered_prompt = prompt_engine.load_extraction_prompt(
                manifest, version=prompt_version
            )

            # Define the API call for retry execution
            def _call_gemini() -> Any:
                return client.models.generate_content(
                    model=self.model_id,
                    contents=[gemini_file, rendered_prompt],
                    config=genai_types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=GeminiExtractionResponse,
                        temperature=0.1,
                    ),
                )

            response = with_gemini_retry(_call_gemini)

            if getattr(response, "parsed", None) is None:
                raw_text = getattr(response, "text", "")
                raise TrackAFailure(
                    FailureCategory.MODEL_FAILURE,
                    "Gemini response could not be parsed into GeminiExtractionResponse schema.",
                    {"raw_text": raw_text[:500] if raw_text else None},
                )

            extracted: GeminiExtractionResponse = response.parsed

            # Map to ExtractionResponseDTO with envelope metadata
            return self._map_to_dto(
                extracted=extracted,
                case_id=case_id,
                manifest=manifest,
                prompt_version=prompt_version,
            )

        finally:
            # Always clean up temporary uploaded file from Gemini Files API
            if gemini_file and hasattr(gemini_file, "name"):
                media_service.cleanup(gemini_file.name)

    def _map_to_dto(
        self,
        extracted: Any,
        case_id: str,
        manifest: CaseManifest,
        prompt_version: str,
    ) -> ExtractionResponseDTO:
        """Map model-facing GeminiExtractionResponse to canonical ExtractionResponseDTO."""
        steps = [
            ExtractedStepDTO(
                index=s.index,
                title=s.title,
                description=s.description,
                start_sec=s.start_sec,
                end_sec=s.end_sec,
            )
            for s in extracted.steps
        ]

        cues = [
            ExtractedCueDTO(
                modality=c.modality,
                statement=c.statement,
                observable_indicator=c.observable_indicator,
                start_sec=c.start_sec,
                end_sec=c.end_sec,
                evidence_sufficiency=c.evidence_sufficiency,
            )
            for c in extracted.cues
        ]

        conditions = [
            ExtractedConditionDTO(
                statement=c.statement,
                tools_or_materials=c.tools_or_materials,
            )
            for c in extracted.conditions
        ]

        exceptions = [
            ExtractedExceptionDTO(
                condition_trigger=e.condition_trigger,
                alternative_action=e.alternative_action,
            )
            for e in extracted.exceptions
        ]

        failure_modes = [
            ExtractedFailureModeDTO(
                symptom=f.symptom,
                mistake_description=f.mistake_description,
                severity=f.severity,
            )
            for f in extracted.failure_modes
        ]

        target_properties = [
            ExtractedTargetPropertyDTO(
                property_id=t.property_id,
                description=t.description,
                evidence_sufficiency=t.evidence_sufficiency,
                measurement=t.measurement,
            )
            for t in extracted.target_properties
        ]

        divergences = [
            ExtractedDivergenceDTO(
                criterion_id=d.criterion_id,
                observed_behavior=d.observed_behavior,
                expected_behavior=d.expected_behavior,
                timestamp_sec=d.timestamp_sec,
                evidence_sufficiency=d.evidence_sufficiency,
            )
            for d in extracted.divergences
        ]

        run_meta = RunMetadataDTO(
            provider="gemini",
            model_id=self.model_id,
            prompt_id=f"{manifest.transmission_mode}_extraction",
            prompt_version=prompt_version,
            input_artifact_id=f"source_{case_id}",
            runtime_class="LIVE",
            run_id=f"run_live_{case_id}_{int(os.environ.get('TEST_SEED', 0)) or int(id(self))}",
            expected_behavior="Live multimodal extraction with structured JSON output",
            evaluation_reference=f"tracks/cases/{case_id}/source/",
        )

        return ExtractionResponseDTO(
            case_id=case_id,
            skill_id=f"skill_{case_id}",
            title=extracted.title or manifest.title,
            summary=extracted.summary or manifest.title,
            source_media_id=f"src-{case_id}-live",
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
        """
        Live evidence query using Gemini structured output:
        1. Formats verified claims as strict grounding context
        2. Prompts Gemini with response_schema=GeminiQueryResponse
        3. Enforces refusal if question probes undocumented conditions
        4. Resolves cited claim IDs to actual EvidenceRef locators
        """
        from google.genai import types as genai_types
        from gemini_schemas import GeminiQueryResponse
        from prompt_engine import PromptEngine
        from gemini_retry import with_gemini_retry

        client = self._ensure_client()
        prompt_engine = PromptEngine()
        query_prompt_template = prompt_engine.load_query_prompt()

        # Build claims context
        claims_lines = []
        claim_map: Dict[str, Any] = {}
        for c in package.claims:
            claim_map[c.claim_id] = c
            timestamps = []
            for r in c.evidence_refs:
                if r.start_sec is not None and r.end_sec is not None:
                    timestamps.append(f"[{r.start_sec:.1f}s - {r.end_sec:.1f}s]")
            ts_str = " ".join(timestamps)
            claims_lines.append(f"- {c.claim_id} ({c.claim_type.value}): {c.statement} {ts_str}")

        claims_context = "\n".join(claims_lines)
        full_prompt = (
            f"{query_prompt_template}\n\n"
            f"## Verified KnowledgePackage Claims\n{claims_context}\n\n"
            f"## Question\n{question}"
        )

        def _call_gemini() -> Any:
            return client.models.generate_content(
                model=self.model_id,
                contents=full_prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiQueryResponse,
                    temperature=0.0,
                ),
            )

        response = with_gemini_retry(_call_gemini)

        if getattr(response, "parsed", None) is None:
            raise TrackAFailure(
                FailureCategory.MODEL_FAILURE,
                "Gemini query response could not be parsed into GeminiQueryResponse schema.",
            )

        query_result: GeminiQueryResponse = response.parsed

        if not query_result.has_sufficient_evidence:
            raise TrackAFailure(
                FailureCategory.MISSING_EVIDENCE,
                "INSUFFICIENT_EVIDENCE: The expert demonstration does not show or document this condition.",
                {"question": question},
            )

        # Resolve cited claim IDs to real EvidenceRef objects
        matched_refs: List[EvidenceRef] = []
        for cid in query_result.cited_claim_ids:
            if cid in claim_map:
                matched_refs.extend(claim_map[cid].evidence_refs)

        if not matched_refs:
            # Fallback search if model cited by content rather than ID
            for c in package.claims:
                if any(w in c.statement.lower() for w in question.lower().split() if len(w) > 3):
                    matched_refs.extend(c.evidence_refs)
                    break

        if not matched_refs:
            raise TrackAFailure(
                FailureCategory.MISSING_EVIDENCE,
                "INSUFFICIENT_EVIDENCE: The expert demonstration does not show or document this condition.",
                {"question": question},
            )

        return query_result.answer, matched_refs
