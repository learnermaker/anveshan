# Parallel Track Workspaces

The `tracks/` directory is the implementation workspace boundary for the two parallel MVP tracks described by `docs/architecture/parallel-work-contract.md` and the current execution gates in `docs/status/NOW.md`.

## Ownership

- `tracks/common/` — **Track Common: The 8 Shared Contracts & Universal Validator**
- `tracks/track-a/` — **Track A: Expert Intelligence & Grounding**
- `tracks/track-b/` — **Track B: Practice, Evaluation & Transmission**

Track folders are intentionally disjoint. Shared contracts and cross-track utilities live in `tracks/common/` as the single authoritative source of truth.

## Independence rule

Each track must be runnable/testable against replay fixtures and frozen handoff contracts. Neither track should require the other track's implementation to make progress.

## Shared seam

The frozen 8-contract seam defined in `tracks/common/schemas/` is:

1. `EvidenceRef`
2. `KnowledgePackage`
3. `RubricDefinition`
4. `PracticeTask`
5. `LearnerAttempt`
6. `Evaluation`
7. `Feedback`
8. `TransmissionRecord`

## Integration

Real expert and learner evidence is joined only at the explicit integration point described by `docs/architecture/parallel-work-contract.md`. Keep integration-specific code outside the two ownership folders unless ownership is explicitly reassigned.

See `AGENTS.md`, `docs/status/NOW.md`, `docs/architecture/google-stack-integration.md`, `docs/architecture/data-flow.md`, and `docs/architecture/parallel-work-contract.md` before starting implementation.
