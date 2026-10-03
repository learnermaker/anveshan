# GitHub Enforcement Configuration

## Repository reality

Anveshan is a **private repository on a GitHub personal Free account**.

For private repositories, GitHub Free does not provide protected branches/branch rulesets or pull-request auto-merge; those capabilities are available for private repositories on paid plans. (Verified against current GitHub documentation.)

Therefore the project must not depend on paid repository controls.

The repository contains agent-level and CI-level governance. GitHub repository administration must additionally enforce the merge boundary.

## Required main-branch rules

Configure a branch protection rule or ruleset targeting main with:

1. Require a pull request before merging.
2. Require at least 1 approving review.
3. Require review from Code Owners.
4. Require status checks before merging.
5. Require the CI check named repo-checks.
6. Require the PR issue-link check named pr-governance.
7. Require branches to be up to date before merging when practical.
8. Block force pushes.
9. Block branch deletion.
10. Do not allow bypass for coding agents.

GitHub documents these controls under protected branches and rulesets. Apply them in the repository GitHub settings.

## What remains manual

Only controls that GitHub Free/private cannot enforce remain manual:

- final human merge into `main`;
- product-scope decisions;
- architectural conflict resolution;
- acceptance of scope trades.

This is intentional. Do not create ceremonies to compensate for unavailable GitHub features.

## Agent operating model

Normal path:

**Issue → short-lived branch → implementation → PR → CI → human merge**

Agents must not intentionally push directly to `main` as part of normal development.

## Principle

AGENTS.md governs agent behavior, issue forms standardize work intake, CODEOWNERS assigns review ownership, and CI validates machine-checkable invariants. Branch protection is the final enforcement boundary that prevents an agent from bypassing those controls by pushing directly to main.

## Current repository owner

@learnermaker

## Operational rule

If the required GitHub protection is not active, treat main as administratively unsafe for autonomous agent work. Agents should continue using branches and PRs, but maintainers should enable the rules above before delegating unrestricted repository write access.
