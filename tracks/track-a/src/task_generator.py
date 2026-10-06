from typing import List, Optional

from tracks.common.schemas import (
    ClaimType,
    KnowledgePackage,
    PracticeTask,
    RubricCriterion,
    RubricDefinition,
    TaskConstraint,
)
from tracks.common.validator import validate_practice_task_against_knowledge_and_rubric
from models import generate_rubric_id, generate_task_id


class TaskGenerator:
    """Domain-agnostic rubric and practice task synthesizer implementing Spec 7.

    Derives observable criteria directly from structured claims in the KnowledgePackage
    and embeds source_claim_id for Track B comparative feedback clip matching.
    """

    def generate_rubric(
        self,
        package: KnowledgePackage,
        rubric_id: Optional[str] = None,
        case_id: Optional[str] = None,
        version: int = 1,
    ) -> RubricDefinition:
        """Synthesize a RubricDefinition from knowledge claims."""
        r_id = rubric_id or (generate_rubric_id(case_id, version) if case_id else f"rubric.{package.package_id}")
        criteria: List[RubricCriterion] = []

        # Derive criteria from steps, cues, and observable conditions
        crit_index = 1
        for claim in package.claims:
            if claim.claim_type in (ClaimType.STEP, ClaimType.CUE, ClaimType.CONDITION):
                # Weight cues and steps slightly higher
                weight = 3.0 if claim.claim_type == ClaimType.CUE else 2.0
                obs_indicator = claim.statement
                if claim.evidence_refs and claim.evidence_refs[0].cue_excerpt:
                    obs_indicator = claim.evidence_refs[0].cue_excerpt

                desc = f"{claim.statement} [source_claim_id: {claim.claim_id}]"
                criteria.append(
                    RubricCriterion(
                        criterion_id=f"CRIT-{crit_index:02d}",
                        name=f"Criterion for {claim.claim_id}",
                        description=desc,
                        observable_indicator=obs_indicator,
                        weight=weight,
                        required=True,
                    )
                )
                crit_index += 1

        # Fallback if no step/cue claims
        if not criteria:
            c0 = package.claims[0]
            criteria.append(
                RubricCriterion(
                    criterion_id="CRIT-01",
                    name=f"Primary execution of {package.title}",
                    description=f"{c0.statement} [source_claim_id: {c0.claim_id}]",
                    observable_indicator=c0.statement,
                    weight=1.0,
                    required=True,
                )
            )

        max_score = sum(c.weight for c in criteria)
        passing = round(max_score * 0.7, 1)

        rubric = RubricDefinition(
            rubric_id=r_id,
            skill_id=package.skill_id,
            title=f"Rubric: {package.title}",
            description=f"Observable rubric synthesized for {package.skill_id}",
            criteria=criteria,
            passing_score=passing,
        )
        return rubric

    def generate_practice_task(
        self,
        package: KnowledgePackage,
        rubric: RubricDefinition,
        task_id: Optional[str] = None,
        case_id: Optional[str] = None,
        constraints: Optional[List[TaskConstraint]] = None,
        version: int = 1,
    ) -> PracticeTask:
        """Synthesize a PracticeTask bound to package and rubric."""
        t_id = task_id or (generate_task_id(case_id, version) if case_id else f"task.{package.package_id}")
        target_ids = [c.criterion_id for c in rubric.criteria]

        task = PracticeTask(
            task_id=t_id,
            package_id=package.package_id,
            rubric_id=rubric.rubric_id,
            title=f"Practice: {package.title}",
            instructions=f"Demonstrate mastery of {package.title} adhering strictly to observed conditions and cues.",
            constraints=constraints or [
                TaskConstraint(
                    constraint_type="environment",
                    description="Standard physical observation environment",
                )
            ],
            target_criteria_ids=target_ids,
        )

        # Enforce cross-contract alignment with common validator
        validate_practice_task_against_knowledge_and_rubric(task, package, rubric)
        return task
