"""Deterministic grounding audit for authored Track A artifacts (track-a-spec §4, §5.5).

Raises ``AnveshanFailure`` (CONTRACT_VIOLATION / UNSUPPORTED_CLAIM); never repairs content.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional

from tracks.common import locators
from tracks.common.casedata import SourceRecord, SourceRegistry
from tracks.common.models import AnveshanFailure, FailureCategory
from tracks.common.schemas import ClaimType, EvidenceRef, KnowledgeClaim, KnowledgePackage, VerificationState

from track_a import config

_CLAIM_CITE = re.compile(r"\bCLM-\d+\b")


def _violation(msg: str, **details) -> AnveshanFailure:
    return AnveshanFailure(FailureCategory.CONTRACT_VIOLATION, msg, details)


def source_modality(record: SourceRecord) -> str:
    """EvidenceRef modality from the source MIME type (spec §4.4)."""
    major = record.mime_type.split("/", 1)[0].lower()
    if major in ("image", "audio", "video"):
        return major
    if major == "text":
        return "text"
    return "sensor"


def _source_for(ev: EvidenceRef, sources: SourceRegistry) -> Optional[SourceRecord]:
    base = locators.parse(ev.source_id).source
    for s in sources.sources:
        if s.source_id == base:
            return s
    return None


def check_evidence(claim: KnowledgeClaim, ev: EvidenceRef, sources: SourceRegistry) -> None:
    try:
        loc = locators.parse(ev.source_id)
    except ValueError as exc:
        raise _violation(f"{claim.claim_id}/{ev.evidence_id}: bad locator: {exc}", claim_id=claim.claim_id) from exc
    record = _source_for(ev, sources)
    if record is not None and (not record.used_by_system or record.role == "held_out_reference"):
        raise _violation(
            f"{claim.claim_id}/{ev.evidence_id}: cites held-out / unused source {record.source_id}",
            claim_id=claim.claim_id,
            source_id=record.source_id,
        )
    if ev.start_sec == 0.0 and ev.end_sec == 0.0:
        raise _violation(f"{claim.claim_id}/{ev.evidence_id}: placeholder 0.0/0.0 locator", claim_id=claim.claim_id)

    if ev.verification_state != VerificationState.OBSERVED:
        return
    # OBSERVED evidence must point at a registered system source with a modality-appropriate locator.
    if record is None:
        raise _violation(
            f"{claim.claim_id}/{ev.evidence_id}: OBSERVED evidence cites unknown source {loc.source}",
            claim_id=claim.claim_id,
        )
    kind = source_modality(record)
    if ev.modality.value != kind:
        raise _violation(
            f"{claim.claim_id}/{ev.evidence_id}: modality {ev.modality.value} != source modality {kind}",
            claim_id=claim.claim_id,
        )
    if kind == "image":
        if ev.start_sec is not None or ev.end_sec is not None:
            raise _violation(f"{claim.claim_id}/{ev.evidence_id}: image evidence must not carry times", claim_id=claim.claim_id)
        if loc.key != "xywh":
            raise _violation(
                f"{claim.claim_id}/{ev.evidence_id}: OBSERVED image evidence needs an #xywh region",
                claim_id=claim.claim_id,
            )
    elif kind in ("audio", "video"):
        if ev.start_sec is None or ev.end_sec is None:
            raise _violation(f"{claim.claim_id}/{ev.evidence_id}: {kind} evidence needs start_sec/end_sec", claim_id=claim.claim_id)
        dur = record.duration_sec
        if dur is not None and (ev.end_sec > dur + config.DURATION_EPS_SEC or ev.start_sec > dur + config.DURATION_EPS_SEC):
            raise _violation(
                f"{claim.claim_id}/{ev.evidence_id}: interval [{ev.start_sec}, {ev.end_sec}] outside source duration {dur}",
                claim_id=claim.claim_id,
            )


def check_claim(claim: KnowledgeClaim, sources: SourceRegistry) -> None:
    observed_refs = [e for e in claim.evidence_refs if e.verification_state == VerificationState.OBSERVED]
    if claim.is_observed and not observed_refs:
        raise _violation(f"{claim.claim_id}: is_observed=True but no OBSERVED evidence", claim_id=claim.claim_id)
    if not claim.is_observed and observed_refs:
        raise _violation(f"{claim.claim_id}: inferred claim carries OBSERVED evidence", claim_id=claim.claim_id)
    if claim.claim_type == ClaimType.STEP and not claim.is_observed:
        for ev in claim.evidence_refs:
            if ev.confidence > config.INFERRED_STEP_MAX_CONFIDENCE:
                raise _violation(
                    f"{claim.claim_id}: inferred STEP confidence {ev.confidence} > {config.INFERRED_STEP_MAX_CONFIDENCE}",
                    claim_id=claim.claim_id,
                )
    for ev in claim.evidence_refs:
        check_evidence(claim, ev, sources)


def check_no_creator_intent(texts: Iterable[tuple[str, str]]) -> None:
    for where, text in texts:
        if not text:
            continue
        for rx in config.CREATOR_INTENT_RE:
            if rx.search(text):
                raise AnveshanFailure(
                    FailureCategory.UNSUPPORTED_CLAIM,
                    f"{where}: creator-intent/history/meaning assertion is not supported by the source",
                    {"where": where, "pattern": rx.pattern, "text": text[:300]},
                )


def audit_package(package: KnowledgePackage, sources: SourceRegistry, modality: str) -> List[str]:
    """Run all grounding checks. Returns uncertainty notes (claim ids that are not observed)."""
    for claim in package.claims:
        check_claim(claim, sources)
    if modality in config.GOAL_CONDITIONED_MODALITIES:
        if not any(c.claim_type == ClaimType.STEP and not c.is_observed for c in package.claims):
            raise AnveshanFailure(
                FailureCategory.UNSUPPORTED_CLAIM,
                "goal-conditioned package has no inferred STEP claim (nothing to teach)",
                {"package_id": package.package_id},
            )
    texts = [("package.title", package.title), ("package.summary", package.summary)]
    for c in package.claims:
        texts.append((f"{c.claim_id}.statement", c.statement))
        texts.extend((f"{c.claim_id}/{e.evidence_id}.cue_excerpt", e.cue_excerpt or "") for e in c.evidence_refs)
    check_no_creator_intent(texts)
    return [f"{c.claim_id}: not directly observed" for c in package.claims if not c.is_observed]


def cited_claim_ids(text: str) -> List[str]:
    return _CLAIM_CITE.findall(text or "")
