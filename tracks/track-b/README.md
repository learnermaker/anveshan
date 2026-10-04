# Track B — Practice, Evaluation & Transmission

**Owner boundary:** learner practice, attempt representation, rubric-based evaluation, evidence-linked feedback, retry, transmission measurement, and lineage output.

## Start here
Read CODING-AGENT-GUIDE.md, SUCCESS-CRITERIA.md, tracks/common/README.md, tracks/common/CONTRACT-USAGE.md, tracks/common/schemas/, tracks/common/validator.py, docs/architecture/parallel-work-contract.md, and docs/architecture/google-stack-integration.md before coding.

Track A implementation is **not** a dependency. Work from frozen fixtures until integration.

## Objective
Prove that a learner can consume a bounded practice input, submit observable evidence, receive traceable feedback, retry, and show measurable criterion-level change.

## Boundary
Own practice-task consumption, learner baseline/attempt capture, observable evidence, criterion-level evaluation, evidence-linked feedback, retry, baseline→retry measurement, TransmissionRecord, lineage, and deterministic replay.

Do not own expert-source ingestion, knowledge extraction, claim grounding, expert authoring, Track A internals, or generalized LMS/analytics infrastructure.

## Authoritative inputs/outputs
Consumes KnowledgePackage, EvidenceRef, RubricDefinition, and PracticeTask. Produces LearnerAttempt, Evaluation, Feedback, and TransmissionRecord. Use the actual Pydantic contracts in tracks/common/; do not create parallel canonical schemas.

## Domain-agnostic rule
The evaluation engine must not assume an industry, profession, physical activity, tool, or modality. The selected domain supplies observable criteria and evidence interpretation; common logic supplies contract validation, criterion alignment, score integrity, deterministic gain, and lineage.

## Starter validation
Replay must prove: practice task → baseline attempt → evaluation → feedback → retry → retry evaluation → measured change. It must support criterion-level comparison and must not reduce evaluation to one unconstrained model score.

## Worktree
tracks/track-b/ contains README.md, CODING-AGENT-GUIDE.md, SUCCESS-CRITERIA.md, fixtures/, prompts/, src/, tests/, and notes/. Create implementation files only through bounded issues.

## Operational conventions

Before creating case-local artifacts, read:
- `tracks/common/CASE-DATA-CONVENTIONS.md`
- `tracks/common/MODEL-GATEWAY-CONVENTIONS.md`
- `tracks/cases/README.md`

Use `tracks/cases/<case_id>/manifest.json` as the entry point for implementation-ready cases. Do not infer validation status from folder presence.

## Worktree

`tracks/track-b/` contains README.md, CODING-AGENT-GUIDE.md, SUCCESS-CRITERIA.md, IMPLEMENTATION-READINESS.md, fixtures/, data/, prompts/, src/, tests/, and notes/. Create implementation files only through bounded issues.
