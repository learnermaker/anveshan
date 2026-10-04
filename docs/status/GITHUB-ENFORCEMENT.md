# GitHub Merge Enforcement

## Repository reality

Anveshan is a private repository on a GitHub personal Free account. Do not depend on paid-only branch protection, rulesets, required reviews, or auto-merge.

## Canonical state

`main` is the canonical latest integrated state.

Short-lived branches are implementation workspaces, not alternate product states. Completed work should move through PR → CI → merge promptly.

## Minimum path

**Issue → branch → implementation → validation → PR → merge → verify main**

An agent may stop before merge only when:

- the user explicitly asked to wait for review;
- a genuine product/architecture/security decision remains unresolved;
- a real merge conflict or dependency makes merging unsafe;
- required validation is failing or unavailable;
- the agent lacks permission to merge.

If the agent lacks merge permission, that is an explicit tooling/permission blocker, not a normal workflow stage.

## Operating rule

After a PR is green and acceptance criteria are satisfied, merge it when permitted. Then verify that `main` contains the intended change.

The purpose of the workflow is not to accumulate open PRs. It is to keep `main` as the latest known-good integrated baseline for parallel work.

## Principle

Use automation and GitHub as the coordination system. Do not add meetings, ceremonies, or manual handoffs that do not protect a real decision boundary or improve product progress.
