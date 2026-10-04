# Branch Cleanup

This note records branch hygiene without making branch deletion part of the development workflow.

## Safe to delete

These branches have no current integrated-development role and are confirmed stale from the current branch comparison:

- `docs/track-guidance-hardening-2026-10-04`
- `feat/stitch-photorealistic-assets`
- `feat/timestamped-screenshots`
- `feat/transmission-workbench-ui`
- `fix/devtools-lineage-and-audit`
- `fix/harden-common-contracts`

Deleting these branches does not remove their integrated work from `main`.

## Keep / investigate

Do not delete these without an explicit commit/content check because they contain commits that are not represented by identical ancestry in `main`, or may correspond to parallel development:

- `chore/pr-contract-preflight`
- `docs/active-development-status`
- `docs/canonical-sources-and-prototype-decision`
- `docs/multimodal-case-portfolio`
- `docs/reconcile-stale-product-prototype-language`
- `docs/reconcile-stale-product-prototype-language-final`
- `docs/reconcile-stale-product-prototype-language-v2`
- `docs/research-root-readme`
- `docs/strengthen-track-agent-guidance`
- `docs/strengthen-track-agent-guidance-v2`
- `feat/akarsh-track-b`
- `feat/scalable-case-packs`
- `fix/case-pack-manifest-v2`
- `fix/case-pack-manifest-validation`
- `fix/contract-parity-browser-assertions`
- `fix/prototype-authority-signals-2026-10-04`
- `fix/ui-contract-parity`
- `research/source-strategy-goal-conditioned-transmission`

## Rule

`main` is the canonical integrated branch. A branch being listed as safe to delete means its useful work is already represented in `main` or intentionally superseded. Branch cleanup is optional housekeeping, not a development gate.

When in doubt, keep the branch until its commits/content have been explicitly checked.
