# Anveshan Repository Instructions

This repository is developed with heavy use of coding agents. Treat the repository documentation as an executable specification.

## Source-of-truth hierarchy

When documents disagree, use this order:

1. AGENTS.md — agent operating rules.
2. README.md — repository-level orientation and current status.
3. docs/product/product-vision.md — canonical long-term product vision.
4. docs/product/product-thesis.md — current competition/MVP wedge only.
5. docs/product/BRD.md and docs/product/mvp-contract.md — current MVP requirements and scope.
6. docs/validation/ — evidence about what has actually been validated.
7. docs/architecture/ — implementation architecture, subject to product and validation constraints.
8. docs/research/ and EXPLORATION.md — research, alternatives, and historical reasoning; not implementation authority unless explicitly promoted into a current decision.
9. docs/product/feature-universe.md — exhaustive possibility inventory; never treat presence as commitment.
10. docs/status/NOW.md and docs/status/project.yaml — concise execution state derived from the hierarchy above; they do not override it.
11. docs/status/DECISIONS.md — durable governance decisions.

## Product hierarchy

Anveshan has three distinct levels:

- Vision: a living intelligence layer for human expertise, experience, and memory.
- Platform lifecycle: CAPTURE → UNDERSTAND → GROUND → TRANSMIT → PRACTICE → VERIFY → EVOLVE.
- Competition wedge: a narrow, validated demonstration of human expertise transfer.

Do not collapse the competition wedge into the company/product vision.

## Status discipline

Use explicit status language:

- EXPLORATION — candidate idea; do not implement solely because it exists.
- PROPOSED — recommended but not yet validated.
- DECIDED — explicitly selected for implementation.
- VALIDATED — supported by recorded evidence.
- IMPLEMENTED — working code exists and is tested.
- SUPERSEDED — retained for history but no longer current.

Work state is separate:

- BACKLOG → READY → IN_PROGRESS → IN_REVIEW → VALIDATING → DONE
- BLOCKED / DEFERRED / REJECTED / SUPERSEDED are terminal or exceptional states as appropriate.

Do not silently promote research into product scope.

## Hackathon operating principle

Optimize for **maximum parallel execution with minimum coordination tax**.

The team is three people working concurrently, mostly through coding agents. GitHub is the durable coordination system; chat is not.

Agents should make ordinary implementation decisions autonomously. Humans step in for product-scope changes, materially different architecture/security/cost implications, ownership collisions, or unresolved product/architecture conflicts.

Do not add process merely because a larger software organization might use it.

## Mandatory agent operating contract

Every coding agent MUST obey these rules:

1. **Issue before implementation.** Do not start meaningful implementation work without a GitHub issue unless the user explicitly directs a one-off repository repair. Tiny local repairs may use the same issue rather than creating multiple issues. If the request is not bounded, create or request a bounded issue first.
2. **One issue, one outcome.** Do not bundle unrelated features, refactors, cleanup, migrations, or abstractions.
3. **Read before edit.** Read AGENTS.md, docs/status/NOW.md, the relevant canonical product documents, and relevant validation evidence before changing behavior.
4. **Search before deciding.** Search the repository for conflicting, duplicate, or superseded definitions before introducing a new concept.
5. **Scope is explicit.** Every implementation issue and PR must state included and excluded work plus acceptance criteria.
6. **No free scope.** Adding work requires removing, reducing, or deferring other work. Use the Scope Change issue form.
7. **Research is not authorization.** EXPLORE/RESEARCH findings never authorize implementation by themselves.
8. **Capability is not scope.** A new Gemini/model/API capability is not an Anveshan feature until product relevance, MVP relevance, and scope authorization are established.
9. **No speculative architecture.** Do not add services, agents, abstractions, databases, or infrastructure merely because they might be useful later.
10. **Smallest coherent change.** Prefer the minimum implementation that satisfies the issue acceptance criteria.
11. **No unrelated edits.** If unrelated improvement is discovered, record it separately rather than folding it into the current change.
12. **Evidence follows claims.** Validation claims require a durable evidence artifact. AI behavior changes require model/prompt/config/fixture information and evaluation evidence.
13. **Deterministic where auditable.** Permissions, provenance, scoring, evaluation aggregation, state transitions, and audit behavior must not depend on unconstrained model output.
14. **Update durable docs.** If a change alters product scope, architecture, evaluation semantics, or agent rules, update the canonical document/ADR in the same change.
15. **Stop conditions matter.** Stop when acceptance criteria are met. Do not keep expanding the task because adjacent work is interesting.
16. **Do not bypass governance.** Do not push directly to main as part of normal development, falsify CI evidence, or weaken governance files to make a change easier.

## Required work lifecycle

For implementation:

1. BACKLOG — issue exists but is not ready.
2. READY — objective, scope, acceptance criteria, dependencies, and owner are clear.
3. IN_PROGRESS — one owner/agent is actively changing it.
4. IN_REVIEW — PR opened and scope frozen.
5. VALIDATING — tests/evaluations/manual verification are being run.
6. DONE — acceptance criteria and required checks pass.

Use BLOCKED when external work prevents progress. Use DEFERRED when consciously postponed. Use REJECTED when the proposed work is not accepted. Use SUPERSEDED when another decision replaces it.

For decisions:

EXPLORATION → PROPOSED → DECIDED → VALIDATED → IMPLEMENTED

A validation result can invalidate a proposal; it does not automatically authorize unrelated implementation.

## Parallel-agent rules

- Parallelize independent issues, not overlapping edits.
- One active owner per file/module at a time.
- Before editing a file another agent may be touching, inspect current branch/PR state and coordinate rather than overwrite.
- Prefer disjoint directories and clear ownership boundaries.
- Agents must leave durable handoff information in the issue/PR, not only in chat.
- For parallel implementation, use a stable contract boundary and replay fixtures so independent workstreams can build and validate without waiting on another implementation.
- Cross-track dependencies must be explicit; do not create hidden synchronization through shared files or runtime assumptions.
- If two agents reach conflicting product or architecture conclusions, stop implementation and create/update a decision record.
- Merge order must follow dependency order; do not resolve conflicts by silently choosing whichever branch is newest.

## PR contract

Every implementation PR must:

- link a GitHub issue using Closes/Fixes/Resolves #N;
- state one bounded outcome;
- state included and excluded scope;
- identify product/MVP/architecture alignment;
- report tests and validation evidence;
- disclose AI/model/prompt/config changes;
- state whether NOW scope changed;
- identify an explicit trade if scope changed;
- update durable documentation when required.

The repository PR template and CI governance check enforce these expectations where technically possible.

## Scope firewall

Current execution scope is defined in docs/status/NOW.md.

Use these buckets:

- NOW — build/validate now.
- NEXT — plausible later work; not implementation-authorized.
- EXPLORE — research only.
- REJECTED/SUPERSEDED — do not resurrect silently.

If work cannot be justified as necessary to the current gate, stop. Create a research issue or scope-change issue instead.

## GitHub plan constraint

This repository is currently private and uses a GitHub personal Free account.

Do **not** assume paid-only repository controls such as protected branches, rulesets, required reviews, or auto-merge. The operating model must remain safe and useful without them.

GitHub Actions CI, issue/PR templates, CODEOWNERS, explicit issue/PR linkage, and human merge discipline are the primary enforcement mechanisms under the current plan.

## Progress tracking

Do not measure progress primarily by issue count, commits, lines of code, or number of agents.

Measure progress by product capability and evidence:

- capability required;
- decision state;
- work state;
- owner;
- issue/PR;
- validation artifact;
- evidence quality;
- remaining blocker;
- gate status.

The current machine-readable state is docs/status/project.yaml.

## Documentation rules

- Prefer one canonical statement over duplicated statements.
- If a document is historical, label it historical/superseded rather than rewriting history.
- Never describe an unvalidated hypothesis as a fact.
- Never describe a feature in feature-universe.md as MVP scope unless the MVP contract says so.
- Keep research findings separate from decisions.
- Record important product or architecture decisions in durable documents rather than only in chat.
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
