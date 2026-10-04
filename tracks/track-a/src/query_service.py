from typing import List, NamedTuple
from tracks.common.schemas import EvidenceRef, KnowledgePackage
from models import FailureCategory, TrackAFailure


class QueryResult(NamedTuple):
    answer: str
    evidence_refs: List[EvidenceRef]


class EvidenceQueryService:
    """Adversarial evidence query service implementing Spec 5."""

    def answer_query(
        self,
        package: KnowledgePackage,
        question: str,
    ) -> QueryResult:
        """Domain-agnostic search over package claims and evidence locators.

        Returns answer and EvidenceRef list or raises MISSING_EVIDENCE with explicit refusal.
        """
        q_clean = question.strip().lower()
        stop_words = {"the", "a", "an", "is", "are", "what", "how", "why", "when", "where", "to", "of", "and", "or", "in", "on"}
        q_tokens = [t for t in q_clean.replace("?", "").replace(",", "").split() if t not in stop_words]

        if not q_tokens:
            raise TrackAFailure(
                FailureCategory.INVALID_INPUT,
                "Query contains no searchable content words.",
                {"question": question},
            )

        best_claim = None
        max_score = 0

        for claim in package.claims:
            claim_text = claim.statement.lower()
            excerpt_text = (claim.evidence_refs[0].cue_excerpt or "").lower() if claim.evidence_refs else ""
            combined = f"{claim_text} {excerpt_text}"

            score = 0
            for token in q_tokens:
                if token in combined:
                    score += 2 if token in claim_text else 1

            if score > max_score:
                max_score = score
                best_claim = claim

        # Strict refusal if insufficient evidence
        if not best_claim or max_score < 2:
            raise TrackAFailure(
                FailureCategory.MISSING_EVIDENCE,
                "INSUFFICIENT_EVIDENCE: The expert demonstration does not show or document this condition.",
                {"question": question, "package_id": package.package_id},
            )

        answer = f"Evidence from {best_claim.claim_id}: {best_claim.statement}"
        return QueryResult(answer=answer, evidence_refs=best_claim.evidence_refs)
