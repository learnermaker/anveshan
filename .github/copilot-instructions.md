# Anveshan — GitHub/Copilot Agent Context

Use the repository root `AGENTS.md` as the authoritative cross-agent operating contract.

## Repository orientation

Anveshan is a research/validation workspace for the Google Cloud AI Builder Cup 2026. The canonical product hierarchy is:

- `docs/product/product-vision.md` — long-term product vision
- `docs/product/product-thesis.md` — current competition/MVP wedge
- `docs/product/BRD.md` and `docs/product/mvp-contract.md` — current requirements/scope
- `docs/validation/` — evidence and validation state
- `docs/architecture/` — implementation architecture (including `docs/architecture/google-stack-integration.md` for Gemini SDK/Cloud Run standards)
- `docs/status/NOW.md` — shortest current execution scope
- `docs/status/DECISIONS.md` — durable decisions

Read `AGENTS.md` and `docs/status/NOW.md` before meaningful implementation. Search for conflicting or superseded definitions before introducing new behavior.

## Build / test

The repository is currently a research/validation workspace; do not invent a runnable application or deployment path before the current validation gate authorizes it.

Existing CI validation is defined in `.github/workflows/checks.yml`. Preserve reproducibility and add focused tests/evaluations with behavior changes.

## Agent execution

Work on one bounded GitHub issue at a time. Keep changes small, avoid unrelated cleanup, respect ownership boundaries, and stop when the acceptance criteria are satisfied.

AI/model/prompt/config changes need evaluation evidence. Preserve provenance, uncertainty, and source-vs-inference distinctions.

Do not infer product authorization from research findings, available APIs/models, or adjacent code.

## Pull requests

PRs should link the issue with `Closes/Fixes/Resolves #N`, state one bounded outcome, identify included/excluded scope, and report validation. Do not add ceremony or duplicate information already enforced by CI.


## Completion rule

Use the minimum lifecycle:

**Issue → branch → implement → validate → PR → merge → verify main**

A PR is an intermediate state, not completion. When acceptance criteria and validation pass and no real decision remains unresolved, merge the PR if permitted. Then verify `main` contains the change.

Keep `main` as the latest completed integrated baseline for parallel agents.

## Canonical case-pack boundary

For capability-case work, the shared case authority is `tracks/cases/<case_id>/`, discovered through `tracks/cases/index.json`, with `manifest.json` as the case entry point. Track-local `tracks/track-a/data/` and `tracks/track-b/data/` are implementation-specific only and must not duplicate canonical case definitions.

Read `tracks/cases/README.md` and `docs/architecture/case-packs.md` before changing case fixtures, replay bundles, or case registries.
