# Parallel Track Workspaces

The `tracks/` directory is the implementation workspace boundary for the two parallel MVP tracks described by `docs/diagrams/DP-01-parallel-development-roadmap.mmd`.

## Ownership

- `tracks/track-a/` — **Track A: Expert Intelligence & Grounding**
- `tracks/track-b/` — **Track B: Practice, Evaluation & Transmission**

Track folders are intentionally disjoint. Do not place shared contracts, cross-track utilities, or integration code inside a track folder unless the relevant issue explicitly assigns ownership.

## Independence rule

Each track must be runnable/testable against replay fixtures and frozen handoff contracts. Neither track should require the other track's implementation to make progress.

## Shared seam

The current conceptual handoff surface is:

- `KnowledgePackage`
- `EvidenceRef`
- `PracticeTask`
- `LearnerAttempt`
- `Evaluation`
- `Feedback`
- `TransmissionRecord`

These are contract names, not authorization to implement every object immediately.

## Integration

Real expert and learner evidence is joined only at the explicit integration point described in DP-01. Keep integration-specific code outside the two ownership folders unless ownership is explicitly reassigned.

See `AGENTS.md`, `docs/status/NOW.md`, `docs/architecture/data-flow.md`, and DP-01 before starting implementation.
