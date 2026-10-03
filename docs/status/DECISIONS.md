# Durable Decisions

This file records decisions that materially affect scope, architecture, validation, or agent behavior.

## Decision format
- Date
- Decision
- Status
- Context
- Evidence
- Alternatives considered
- Consequences
- Revisit trigger

## 2026-10-03 — Multi-agent operating system
**Status:** DECIDED

**Decision:** The repository is the durable coordination system for human and coding-agent work. Implementation is issue-driven; PRs are bounded by issue contracts; current scope is explicitly separated from research; scope expansion requires an explicit trade-off; governance-critical material is code-owned and CI-checked.

**Context:** Multiple people and agents work concurrently, so chat context is not a durable source of truth.

**Consequences:** Agents must stop rather than infer authorization from adjacent code, research, or model capability.

**Revisit trigger:** The repository collaboration model changes materially.

## 2026-10-03 — Current product scope remains validation-first
**Status:** DECIDED

**Decision:** The competition effort remains in research/product-definition/validation until the core product hypothesis is supported by recorded evidence.

**Context:** The exact domain, skill, expert, learner, and rubric remain open.

**Evidence:** docs/product/mvp-contract.md, docs/validation/, docs/product/open-questions.md.

**Consequences:** Agents must not invent a domain or build a large app before the validation gate.

**Revisit trigger:** A validation artifact records a supported bounded direction.
## 2026-10-03 — GitHub/agent operating standard
**Status:** DECIDED

**Decision:** Anveshan uses a low-ceremony, automation-first operating model for three concurrent people/agents. Root `AGENTS.md` is the cross-agent contract; `.github/copilot-instructions.md` supplies GitHub/Copilot-specific context; CI enforces machine-checkable repository and PR invariants; GitHub Free/private limitations are treated as hard constraints; paid-only branch protection, rulesets, required reviews, and native auto-merge are not dependencies.

**Operating path:** Issue → short-lived branch → implementation → PR → CI → merge. Agents make ordinary implementation decisions autonomously. Only product scope, material architecture/security/cost implications, ownership collisions, and unresolved cross-agent conflicts require human intervention.

**Context:** The repository is a hackathon project with three people working concurrently, mostly through coding agents. The objective is maximum parallelism with minimum coordination tax while preserving scope integrity, reproducibility, provenance, and integration safety.

**Revisit trigger:** Team size, GitHub plan, collaboration model, or product-development phase changes materially.
