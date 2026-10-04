from pathlib import Path
import time
from typing import List, Literal, Optional, Tuple

from tracks.common.schemas import EvidenceRef, KnowledgePackage
from models import ExtractionResponseDTO, FailureCategory, TrackAFailure
from providers import BaseProviderAdapter, GeminiProviderAdapter, ReplayProviderAdapter


class ModelGateway:
    """Model Gateway isolating LLM extraction from canonical contracts per Spec 3."""

    def __init__(
        self,
        cases_root: Path,
        mode: Literal["replay", "live"] = "replay",
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.cases_root = cases_root
        self.mode = mode
        self.model_id = model_id

        if mode == "replay":
            self.adapter: BaseProviderAdapter = ReplayProviderAdapter(cases_root=cases_root)
        elif mode == "live":
            self.adapter = GeminiProviderAdapter(
                cases_root=cases_root,
                model_id=model_id,
                api_key=api_key,
            )
        else:
            raise TrackAFailure(
                FailureCategory.INVALID_INPUT,
                f"Unsupported gateway mode: {mode}. Must be 'replay' or 'live'.",
            )

    def extract_knowledge(
        self,
        case_id: str,
        prompt_version: str = "v1",
    ) -> ExtractionResponseDTO:
        """Route extraction call to configured adapter with execution telemetry."""
        start_t = time.perf_counter()
        try:
            dto = self.adapter.extract_knowledge(case_id, prompt_version=prompt_version)
            elapsed = time.perf_counter() - start_t
            # Ensure runtime metadata captures actual run ID
            if not dto.run_metadata.run_id:
                dto.run_metadata.run_id = f"run.{case_id}.{int(time.time())}"
            return dto
        except TrackAFailure:
            raise
        except Exception as exc:
            raise TrackAFailure(
                FailureCategory.MODEL_FAILURE,
                f"Model gateway extraction failed for case {case_id}: {exc}",
                {"case_id": case_id, "mode": self.mode},
            ) from exc

    def query_evidence(
        self,
        package: KnowledgePackage,
        question: str,
    ) -> Tuple[str, List[EvidenceRef]]:
        """Route evidence query to adapter."""
        try:
            return self.adapter.query_evidence(package, question)
        except TrackAFailure:
            raise
        except Exception as exc:
            raise TrackAFailure(
                FailureCategory.MODEL_FAILURE,
                f"Model gateway evidence query failed: {exc}",
                {"question": question},
            ) from exc
