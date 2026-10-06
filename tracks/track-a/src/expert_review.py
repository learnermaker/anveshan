from datetime import datetime, timezone
from typing import Optional

from tracks.common.schemas import ExpertReview, KnowledgePackage, ReviewStatus
from case_registry import CaseManifest
from models import FailureCategory, TrackAFailure


class ExpertReviewService:
    """Human-in-the-loop expert review gate and markdown exporter implementing Spec 6."""

    def submit_for_review(
        self,
        package: KnowledgePackage,
        reviewer_name: str,
    ) -> KnowledgePackage:
        """Submit a candidate package for domain expert inspection (sets PENDING)."""
        package.expert_review = ExpertReview(
            reviewer_name=reviewer_name,
            status=ReviewStatus.PENDING,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
            notes="Submitted for expert fidelity audit.",
        )
        return package

    def approve_package(
        self,
        package: KnowledgePackage,
        reviewer_name: str,
        notes: Optional[str] = None,
    ) -> KnowledgePackage:
        """Approve package extraction fidelity."""
        package.expert_review = ExpertReview(
            reviewer_name=reviewer_name,
            status=ReviewStatus.APPROVED,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
            notes=notes or "Verified against authentic demonstration footage.",
        )
        return package

    def revise_claim(
        self,
        package: KnowledgePackage,
        claim_id: str,
        new_statement: str,
        reviewer_name: str,
        notes: Optional[str] = None,
    ) -> KnowledgePackage:
        """Correct or refine a specific claim statement."""
        matched = False
        for claim in package.claims:
            if claim.claim_id == claim_id:
                claim.statement = new_statement
                matched = True
                break

        if not matched:
            raise TrackAFailure(
                FailureCategory.INVALID_INPUT,
                f"Claim {claim_id} not found in package {package.package_id}",
                {"package_id": package.package_id, "claim_id": claim_id},
            )

        package.expert_review = ExpertReview(
            reviewer_name=reviewer_name,
            status=ReviewStatus.REVISED,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
            notes=notes or f"Claim {claim_id} revised by expert.",
        )
        return package

    def reject_package(
        self,
        package: KnowledgePackage,
        reviewer_name: str,
        reason: str,
    ) -> KnowledgePackage:
        """Reject package extraction."""
        package.expert_review = ExpertReview(
            reviewer_name=reviewer_name,
            status=ReviewStatus.REJECTED,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
            notes=reason,
        )
        return package

    def export_markdown(
        self,
        package: KnowledgePackage,
        manifest: Optional[CaseManifest] = None,
    ) -> str:
        """Produce clean, readable human expert inspection sheet."""
        lines = [
            f"# Expert Review Sheet: {package.title}",
            "",
            "## Case Metadata",
            f"- **Package ID:** `{package.package_id}`",
            f"- **Skill ID:** `{package.skill_id}`",
        ]
        if manifest:
            lines.extend(
                [
                    f"- **Domain:** {manifest.domain}",
                    f"- **Archetype:** `{manifest.archetype}`",
                    f"- **Transmission Mode:** `{manifest.transmission_mode}`",
                    f"- **Epistemic Status:** `{manifest.epistemic_status}`",
                    f"- **Runtime Class:** `{manifest.runtime_class}`",
                ]
            )

        lines.extend(
            [
                "",
                "## Contributor Consent",
                f"- **Expert:** {package.consent.contributor_name}",
                f"- **Scope:** `{package.consent.consent_scope}`",
                f"- **Revocable:** {package.consent.revocable}",
                f"- **Granted At:** {package.consent.granted_at or 'N/A'}",
                "",
                "## Review Status",
            ]
        )

        rev = package.expert_review
        if rev:
            lines.extend(
                [
                    f"- **Reviewer:** {rev.reviewer_name}",
                    f"- **Status:** `{rev.status.value.upper()}`",
                    f"- **Reviewed At:** {rev.reviewed_at or 'Pending'}",
                    f"- **Notes:** {rev.notes or 'None'}",
                ]
            )
        else:
            lines.append("- *Status: No review recorded*")

        lines.extend(
            [
                "",
                "## Extracted Knowledge Claims",
                "",
                "| ID | Type | Observation | Statement | Evidence Locators |",
                "|---|---|---|---|---|",
            ]
        )

        for c in package.claims:
            locs = []
            for ev in c.evidence_refs:
                time_str = (
                    f"[{ev.start_sec:.1f}s - {ev.end_sec:.1f}s]"
                    if ev.start_sec is not None and ev.end_sec is not None
                    else "[Static/Text]"
                )
                locs.append(f"`{ev.evidence_id}` {time_str} ({ev.verification_state.value})")
            loc_str = "<br>".join(locs)
            obs_str = "OBSERVED" if c.is_observed else "INFERRED"
            lines.append(
                f"| `{c.claim_id}` | `{c.claim_type.value}` | **{obs_str}** | {c.statement} | {loc_str} |"
            )

        lines.extend(
            [
                "",
                "---",
                "### Expert Signature & Verdict",
                "- [ ] **APPROVE** (Extraction faithfully represents demonstrated technique)",
                "- [ ] **REVISE** (Corrections noted above)",
                "- [ ] **REJECT** (Fundamental misunderstanding of physical procedure)",
                "",
                "Signature: __________________________  Date: _______________",
            ]
        )
        return "\n".join(lines)
