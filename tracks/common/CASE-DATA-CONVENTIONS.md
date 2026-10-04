# Case Data & Operational Conventions

**Status:** DECIDED execution convention for Track A, Track B, fixtures, and integration
**Purpose:** Make cases, artifacts, replay runs, versions, failures, and review state discoverable and deterministic for coding agents.

## 1. Scope

This defines filesystem and metadata conventions around the eight frozen contracts. It does not create another product contract.
Do not introduce a database, service, or shared runtime merely to satisfy this convention.

## 2. Scalable case layout

Each track may organize case-local data as:

    tracks/<track>/data/
    └── cases/
        └── <case_id>/
            ├── manifest.yaml
            ├── source/       # Track A: source assets/metadata
            ├── expected/     # expected normalized outputs/replay assertions
            ├── attempts/     # Track B: learner evidence/attempt fixtures
            └── metadata/     # run/review/supporting metadata

Only create subdirectories a case needs. Empty directories do not need to be committed.
The same case_id should identify the corresponding Track A and Track B case when they represent one integrated proof.

## 3. Case manifest

Every executable case must have manifest.yaml with at least:

    case_id: <stable-case-id>
    case_version: <semver-or-vN>
    status: CANDIDATE | ENGINEERING_FIXTURE | AUTHENTIC_SOURCE_READY | M0_VALIDATION | VALIDATED | INTEGRATED | REJECTED | SUPERSEDED
    source_mode: FORWARD | GOAL_CONDITIONED | CORRECTIVE
    runtime_class: LIVE | REPLAY | SYNTHETIC | ILLUSTRATIVE
    domain: <domain-or-null-before-selection>
    skill: <skill-or-null-before-selection>
    description: <short bounded purpose>

The manifest is the case entry point. Agents must not infer case status from a directory name alone.

## 4. Artifact identity and versioning

Use stable IDs and explicit versions. Recommended patterns:

    case.<slug>.<number>
    src.<case-id>.<version>
    kp.<case-id>.<version>
    rubric.<case-id>.<version>
    task.<case-id>.<version>
    attempt.<case-id>.<type>.<number>
    eval.<case-id>.<attempt>
    feedback.<case-id>.<attempt>
    tx.<case-id>.<version>

Do not silently overwrite a materially changed artifact. Create a new version when source, extraction semantics, rubric semantics, or materially outcome-affecting prompt/model configuration changes.
Historical evaluations and transmission records must remain reconstructable.

## 5. Runtime/replay metadata

Model-backed operations must retain model/provider, configuration, prompt ID/version, input artifact/fixture ID, runtime class, run ID, and expected behavior/evaluation reference.
Replay must not require a network/model call. Replay results are never authentic validation.

## 6. Failure taxonomy

Use these categories where a structured failure is needed:
- INVALID_INPUT
- MISSING_EVIDENCE
- AMBIGUOUS_EVIDENCE
- UNSUPPORTED_CLAIM
- CONTRACT_VIOLATION
- MODEL_FAILURE
- MODEL_TIMEOUT
- REPLAY_MISMATCH
- HUMAN_REVIEW_REQUIRED

Track-local detail may be added, but do not create synonyms for the core categories without a reason.

## 7. Human-review escalation

Automation must stop or explicitly escalate when a material claim lacks adequate evidence, evidence conflicts materially, a criterion cannot be observed reliably, model interpretation conflicts with evidence, an expert rejects/corrects a claim, or the system would otherwise need to guess.
Human review is an explicit state transition. Model confidence is never equivalent to approval.

## 8. Source and consent discipline

For authentic source material, preserve source identity and applicable consent/authorization metadata. Avoid unnecessary duplication of sensitive source media.
Case metadata should reference stable source artifacts rather than copying them into multiple track folders when possible.

## 9. Agent write boundaries

Agents may create/change track-local case fixtures, prompts, adapters, tests, implementation modules, and metadata.
Agents must not create/change without an explicit cross-track issue/decision: the eight common contracts, shared enum semantics, cross-track interfaces, product scope, deployment topology, or a database/service solely for future scalability.

## 10. Canonical replay expectation

Every implementation-ready case should document input artifact IDs, expected normalized outputs, negative cases, replay command, and expected pass/fail result.
This convention supports reproducibility; it is not evidence that the product hypothesis is validated.