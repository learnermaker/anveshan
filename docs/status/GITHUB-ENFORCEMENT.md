# GitHub Enforcement Configuration

## Repository reality

Anveshan is a **private repository on a GitHub personal Free account**.

For private repositories, GitHub Free does not provide protected branches/branch rulesets or pull-request auto-merge; those capabilities are available for private repositories on paid plans. (Verified against current GitHub documentation.)

Therefore the project must not depend on paid repository controls.

The repository contains agent-level and CI-level governance. GitHub repository administration must additionally enforce the merge boundary.

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

AGENTS.md governs agent behavior, issue forms standardize work intake, CODEOWNERS identifies ownership, and CI validates machine-checkable invariants. Under the current GitHub plan, the final merge boundary is human discipline rather than paid branch protection.

## Current repository owner

@learnermaker
