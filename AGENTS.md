# Anveshan Repository Instructions

This repository is developed with heavy use of coding agents. Treat the repository documentation as an executable specification.

## Source-of-truth hierarchy

When documents disagree, use this order:

1. `AGENTS.md` — agent operating rules.
2. `README.md` — repository-level orientation and current status.
3. `docs/product/product-vision.md` — canonical long-term product vision.
4. `docs/product/product-thesis.md` — current competition/MVP wedge only.
5. `docs/product/BRD.md` and `docs/product/mvp-contract.md` — current MVP requirements and scope.
6. `docs/validation/` — evidence about what has actually been validated.
7. `docs/architecture/` — implementation architecture, subject to product and validation constraints.
8. `docs/research/` and `EXPLORATION.md` — research, alternatives, and historical reasoning; not implementation authority unless explicitly promoted into a current decision.
9. `docs/product/feature-universe.md` — exhaustive possibility inventory; never treat presence as commitment.

## Product hierarchy

Anveshan has three distinct levels:

- **Vision:** a living intelligence layer for human expertise, experience, and memory.
- **Platform lifecycle:** CAPTURE → UNDERSTAND → GROUND → TRANSMIT → PRACTICE → VERIFY → EVOLVE.
- **Competition wedge:** a narrow, validated demonstration of human expertise transfer.

Do not collapse the competition wedge into the company/product vision.

## Status discipline

Use explicit status language:

- `EXPLORATION` — candidate idea; do not implement solely because it exists.
- `PROPOSED` — recommended but not yet validated.
- `DECIDED` — explicitly selected for implementation.
- `VALIDATED` — supported by recorded evidence.
- `IMPLEMENTED` — working code exists and is tested.
- `SUPERSEDED` — retained for history but no longer current.

Do not silently promote research into product scope.

## Agent workflow

Before implementing a feature:

1. Read this file.
2. Read the relevant canonical product documents.
3. Check `docs/validation/` for evidence.
4. Search the repository for conflicting or superseded definitions.
5. Confirm the feature is `DECIDED` or explicitly requested.
6. Implement the smallest coherent change.
7. Add or update tests.
8. Update the relevant decision/status documentation when implementation changes a product assumption.

## Documentation rules

- Prefer one canonical statement over duplicated statements.
- If a document is historical, label it historical/superseded rather than rewriting history.
- Never describe an unvalidated hypothesis as a fact.
- Never describe a feature in `feature-universe.md` as MVP scope unless the MVP contract says so.
- Keep research findings separate from decisions.
- Record important product or architecture decisions in a durable document rather than only in chat.
- Avoid speculative architecture before the product boundary is decided.

## Engineering rules

- Prefer deterministic logic for permissions, provenance, evaluation, scoring, state transitions, and other auditable behavior.
- Use AI where multimodal understanding, reasoning, generation, or orchestration provides measurable value.
- Every AI component should have a defined job and an evaluation method.
- Preserve source evidence and uncertainty; do not silently convert inference into source truth.
- Build replayable tests and recorded-response paths wherever model calls would otherwise make tests nondeterministic.
- Do not introduce infrastructure merely because it is architecturally interesting.

## Current repository state

The repository is currently a research/validation workspace. Do not assume a runnable application exists unless the current tree and implementation-status documents show it.

The current competition domain, skill, expert, learner, and evaluation rubric remain open until the validation gate records a decision.
