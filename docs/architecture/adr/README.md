# Architecture Decision Records

This directory contains explicit technical decisions. Exploratory ideas should not be treated as decisions until recorded here.

## Canonical product boundary

Architecture decisions are subordinate to:
1. `docs/product/product-vision.md`;
2. `docs/product/product-thesis.md`;
3. `docs/product/BRD.md`;
4. `docs/product/mvp-contract.md`;
5. `docs/validation/`.

Research documents can propose alternatives, but they do not silently change implementation scope.

## ADR-001 — Keep Source and Derived Knowledge Separate

**Status:** Accepted as design principle.

**Decision:** Original source material remains distinct from structured knowledge and AI-generated interpretation.

**Reason:** Supports provenance, correction, auditability, and trust.

## ADR-002 — Use Transmission as the Core Product Unit

**Status:** Accepted as current product/architecture hypothesis, bounded by the MVP Contract.

**Decision:** Model knowledge transfer between people as a first-class event.

**Reason:** Makes transmission measurable and differentiates the current MVP from static preservation workflows.

## ADR-003 — Prefer Three Logical AI Responsibilities

**Status:** Proposed.

**Decision:** Start with Knowledge, Evidence, and Transmission responsibilities.

**Reason:** Provides meaningful agent boundaries without unnecessary agent proliferation.

## ADR-004 — Preserve Variants Rather Than Flattening Them

**Status:** Accepted as product principle.

**Decision:** Different expert, regional, historical, or learner versions can coexist.

**Reason:** Living knowledge legitimately evolves.

## ADR-005 — Evidence Before Unsupported Generation

**Status:** Accepted as product principle.

**Decision:** If evidence is insufficient, the system should express uncertainty instead of inventing an answer.

**Reason:** Source integrity is central to the product.

## ADR-006 — MVP Must Prove One Complete Transmission Loop

**Status:** Accepted.

**Decision:** One expert, one bounded skill, one learner, one practice attempt, one feedback loop, and one measurable outcome before broad expansion.

**Reason:** Reduces scope and directly tests the current MVP hypothesis.

## ADR-007 — Criterion-Level Learner Evaluation

**Status:** Accepted as MVP architecture principle.

Do not use an unconstrained model-generated skill score. Evaluate explicit observable criteria and preserve evidence for each judgment.

## ADR-008 — Transmission Requires a Baseline

**Status:** Accepted as validation principle.

A transmission claim requires a baseline and a subsequent attempt wherever the task permits. Without a baseline, improvement cannot be attributed to the intervention.

## ADR-009 — Community Sovereignty Must Not Be Simulated

**Status:** Accepted as governance principle.

The product may provide contributor controls by default, but community sovereignty is claimed only when the relevant community actually governs the data and its use.
