# Track B — Coding Agent Guide

## Mission

Prove that grounded expertise actually transfers to a learner:

`practice task → baseline → observation → criterion evaluation → feedback → retry → measurable change → transmission record`

Track B makes “transmitted” measurable.

## Before coding

Read:
1. `tracks/common/README.md`
2. `tracks/common/CONTRACT-USAGE.md`
3. `tracks/common/schemas/`
4. `tracks/common/validator.py`
5. `tracks/common/tests/`
6. `docs/architecture/parallel-work-contract.md`
7. `docs/architecture/google-stack-integration.md`
8. `tracks/track-b/SUCCESS-CRITERIA.md`
9. `docs/product/mvp-contract.md` as needed.

Track A implementation is not a dependency. Work from frozen fixtures until integration.

## Authoritative inputs/outputs

Consumes:
- `KnowledgePackage`
- `EvidenceRef`
- `RubricDefinition`
- `PracticeTask`

Produces:
- `LearnerAttempt`
- `Evaluation`
- `Feedback`
- `TransmissionRecord`

Use the actual common Pydantic models. Do not invent a parallel learner/evaluation schema.

## Domain-agnostic rule

The evaluation engine must not assume a specific industry or skill.

The selected domain supplies:
- observable criteria;
- evidence interpretation;
- task-specific terminology;
- modality-specific observation logic.

The common engine supplies:
- contract validation;
- criterion alignment;
- attempt typing;
- deterministic score integrity;
- feedback linkage;
- transmission gain;
- lineage.

## Baseline and retry

Baseline:
- `attempt_type = BASELINE`
- `attempt_number = 1`

Retry:
- `attempt_type = RETRY`
- `attempt_number >= 2`

For the MVP:
`baseline → teaching → feedback → one retry`

The same learner, task, and rubric context must remain comparable.

## Evaluation rule

Never start with an unconstrained model score.

Evaluate criterion-by-criterion against the explicit `RubricDefinition`.

Each result should make clear:
- criterion;
- status;
- score;
- observed finding;
- relevant learner evidence;
- deviation from the reference where useful.

The common validator already protects important invariants. Extend it only when a real cross-contract invariant is missing.

## Gemini rules

Gemini may:
- locate relevant learner evidence;
- observe behavior;
- compare learner evidence to reference evidence;
- identify deviations;
- draft feedback.

Gemini must not redefine the rubric or authoritative metric.

If evidence is insufficient, use `UNCERTAIN` or request additional evidence/human review. Do not convert ambiguity into false precision.

## Feedback rule

Every meaningful feedback item should answer:
1. What did the learner do?
2. What differed?
3. What evidence supports that finding?
4. What should change on retry?

Feedback must link to evaluated criteria and evidence. “Practice more” is not sufficient.

## Transmission rule

Compute:

`gain = retry_score - baseline_score`

and preserve the underlying evaluations and criterion results.

A positive gain does not prove mastery, generalization, or causality beyond the observed case.

## Replay requirement

A deterministic replay must prove:

`PracticeTask → baseline attempt → evaluation → feedback → retry → retry evaluation → TransmissionRecord`

It must work without live Gemini.

At minimum test:
- baseline/retry typing;
- invalid attempt numbers;
- rubric criterion existence;
- score ≤ criterion weight;
- total score arithmetic;
- required criteria;
- feedback targeting;
- learner identity alignment;
- baseline/retry score alignment;
- deterministic gain;
- improved-criterion integrity;
- malformed bundle rejection.

## Domain selection

Do not select the domain merely because a model or tool supports it. The eventual domain must be:
- bounded;
- observable;
- safe to practice;
- capable of authentic expert evidence;
- measurable with a meaningful rubric.

## Integration

Replace frozen Track A fixtures with real Track A outputs only after Track B independently passes its replay gate.

Do not import Track A implementation modules.

## Stop conditions

Stop and narrow scope if:
- the learner evidence is not observable;
- criteria cannot be scored reliably;
- feedback is generic;
- identical replay inputs produce inconsistent deterministic results;
- gain cannot be reconstructed;
- the workflow becomes a generic LMS/tutoring system.

Do not add analytics/platform infrastructure to compensate for a weak proof.
