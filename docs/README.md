# Anveshan Documentation

**Repository review checkpoint:** 2026-10-03

## Start Here

Read in this order:

1. `README.md` — repository orientation and current status.
2. `docs/product/product-vision.md` — **canonical long-term product vision**.
3. `docs/product/product-thesis.md` — **current competition/MVP wedge**.
4. `docs/product/BRD.md` — MVP requirements.
5. `docs/product/mvp-contract.md` — implementation boundary.
6. `docs/validation/` — what has actually been validated.
7. `docs/architecture/` — implementation design.
8. `docs/research/` and `EXPLORATION.md` — research and historical reasoning.
9. `docs/product/feature-universe.md` — exhaustive possibility inventory, not scope.

For coding-agent operating rules, read `AGENTS.md` first.

## Product

- Product Thesis
- BRD
- MVP Contract
- Novelty Boundary
- Feature Universe
- Risk Register
- User Journeys
- Open Questions

## Research

- Exploration Dossier
- Panel Review
- Competitive Landscape
- Rejected Directions
- Research Sources

## Architecture

- System Design
- Knowledge Model
- AI Agent Architecture
- Data Flow
- Parallel Work Contract
- Google Ecosystem & Gemini Integration Guide
- Architecture Decision Records

## Parallel implementation workspaces

- `tracks/` — starter workspaces for concurrent transmission tracks.
- `tracks/common/` — **The 8 Shared Contracts & Universal Validator (Track 3 / Common Seam)**.
- `tracks/track-a/` — Expert Intelligence & Grounding (Track 1).
- `tracks/track-b/` — Practice, Evaluation & Transmission (Track 2).


## Validation

- Validation Plan
- Metrics
- Experiments
- Findings

## Governance

- Ethics and Consent
- Provenance
- Access Control

## Hackathon

- AI Builder Cup
- Judging Strategy
- Judge Q&A
- Demo Story
- Submission Checklist

## Documentation Rule

The repository has a strict source-of-truth hierarchy. Do not infer implementation scope from research or feature inventories.

The repository separates:

- **EXPLORED** — possibilities and research.
- **DECIDED** — explicit decisions.
- **IMPLEMENTED** — actual code and working behavior.

A feature in the universe is not automatically an MVP feature. The MVP Contract controls implementation scope. The Validation Plan controls whether claims can be called validated.

## Review Rule

Every time-sensitive competitor, model, platform or competition claim must be rechecked before submission.

## Repository Readiness Audit — 2026-10-03

Current state: **active development toward the M1 vertical slice; not submission-complete**.

The repository now contains active implementation across the frontend, shared contracts, case packs, CI, and parallel Track A/Track B workspaces. Engineering fixtures and replay tests provide deterministic development evidence; they do **not** by themselves constitute real-world product validation. Real benchmark/validation artifacts, production deployment hardening, and final submission assets remain outstanding.

### Remaining development and validation artifacts

- complete the M1 vertical slice across the current bounded implementation work;
- model gateway implementation with recorded-response/replay mode where required;
- real benchmark run artifacts and summarized results;
- approved authentic MVP fixture media and provenance metadata;
- skill-specific rubric and independent expert-review records;
- evidence/citation examples produced by the actual system;
- Google Cloud deployment configuration and deployment smoke-test record when deployment is in scope;
- continued deterministic CI/replay/evaluation coverage;
- final architecture diagram exported as an artifact;
- final proposal/deck PDF and public three-minute demo link before submission;
- final submission evidence mapping each judging criterion to working prototype behavior.

### Current scope rule

The canonical product direction is defined by:

- `docs/product/product-vision.md` — long-term vision;
- `docs/product/product-thesis.md` — current competition/MVP wedge;
- `docs/product/BRD.md` and `docs/product/mvp-contract.md` — current implementation boundary;
- `docs/validation/` — evidence that can promote a hypothesis to validated status.

Alternative directions in research, including operational state/action/outcome concepts, remain research unless explicitly promoted into the current thesis.
