"""Evidence query over a knowledge package (track-a-spec §10).

Gemma (``model_key="text_image"``) answers only from the package claims. Cited ids are validated;
there is no keyword fallback. Goal-conditioned cases refuse intent / history / meaning / original
order questions deterministically, without a model call.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from tracks.common.models import AnveshanFailure, FailureCategory, load_prompt
from tracks.common.runtime import RunContext
from tracks.common.schemas import KnowledgePackage

from track_a import config

PROMPT_PATH = config.PROMPTS_DIR / "evidence_query_v1.txt"
PROMPT_ID = "evidence_query"
INSUFFICIENT = "INSUFFICIENT_EVIDENCE"
MAX_QUESTION_CHARS = 1000


class QueryDTO(BaseModel):
    answer: str
    cited_claim_ids: List[str] = Field(default_factory=list)
    sufficient: bool


def claims_payload(package: KnowledgePackage) -> List[Dict[str, Any]]:
    return [
        {
            "claim_id": c.claim_id,
            "claim_type": c.claim_type.value,
            "is_observed": c.is_observed,
            "statement": c.statement,
            "evidence": [
                {
                    "evidence_id": e.evidence_id,
                    "source_id": e.source_id,
                    "modality": e.modality.value,
                    "start_sec": e.start_sec,
                    "end_sec": e.end_sec,
                    "verification_state": e.verification_state.value,
                }
                for e in c.evidence_refs
            ],
        }
        for c in package.claims
    ]


def precheck_unanswerable(question: str, goal_conditioned: bool) -> bool:
    return goal_conditioned and any(rx.search(question) for rx in config.UNANSWERABLE_RE)


def _insufficient(reason: str, run: Dict[str, Any]) -> Dict[str, Any]:
    return {"answer": f"{INSUFFICIENT}: {reason}", "cited_claim_ids": [], "evidence": [], "sufficient": False, "run": run}


def answer(
    package: KnowledgePackage,
    question: str,
    ctx: RunContext,
    *,
    case_title: str,
    transmission_mode: str,
    goal_conditioned: bool,
) -> Dict[str, Any]:
    q = (question or "").strip()
    if not q:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, "question is empty")
    if len(q) > MAX_QUESTION_CHARS:
        raise AnveshanFailure(FailureCategory.INVALID_INPUT, f"question longer than {MAX_QUESTION_CHARS} characters")

    if precheck_unanswerable(q, goal_conditioned):
        return _insufficient(
            "a finished final state cannot establish creator intent, history, meaning or the original order of actions.",
            {"runtime_class": "DETERMINISTIC", "rule": "goal_conditioned_precheck", "package_id": package.package_id},
        )

    prompt_text, version = load_prompt(
        PROMPT_PATH,
        question=q,
        case_title=case_title,
        transmission_mode=transmission_mode,
        claims_json=json.dumps(claims_payload(package), indent=1, sort_keys=True, ensure_ascii=False),
    )
    gen = ctx.gateway.generate_json(
        model_key="text_image",
        prompt_id=PROMPT_ID,
        prompt_version=version,
        prompt_text=prompt_text,
        schema=QueryDTO,
        expected_behavior="answer only from package claims with valid claim-id citations, else INSUFFICIENT_EVIDENCE",
    )
    run = gen.metadata.to_dict()
    run["package_id"] = package.package_id
    dto: QueryDTO = gen.data  # type: ignore[assignment]

    by_id = {c.claim_id: c for c in package.claims}
    cited = list(dict.fromkeys(dto.cited_claim_ids))
    unknown = [c for c in cited if c not in by_id]
    if unknown:
        return _insufficient(f"the model cited claim ids not in the package ({', '.join(unknown)}).", run)
    if not dto.sufficient:
        text = dto.answer.strip()
        reason = text.split(":", 1)[1].strip() if text.startswith(INSUFFICIENT) and ":" in text else "the source does not show or document this."
        return _insufficient(reason, run)
    if not cited:
        return _insufficient("the answer cited no claims.", run)
    evidence = [e.model_dump(mode="json") for cid in cited for e in by_id[cid].evidence_refs]
    return {"answer": dto.answer.strip(), "cited_claim_ids": cited, "evidence": evidence, "sufficient": True, "run": run}
