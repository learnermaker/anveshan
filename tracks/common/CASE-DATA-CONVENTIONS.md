# Case Data & Operational Conventions

**Status:** DECIDED execution convention for Track A, Track B, fixtures, and integration  
**Purpose:** Make cases, artifacts, replay runs, versions, failures, and review state discoverable and deterministic for coding agents.

## 1. Scope

This defines filesystem and metadata conventions around the eight frozen contracts. It does not create another product contract.
Do not introduce a database, service, or shared runtime merely to satisfy this convention.

## 2. Scalable case layout

**Canonical shared case content lives in `tracks/cases/<case_id>/`.**

Each case pack has a predictable cross-track layout:

    tracks/cases/
    ├── index.json
    └── <case_id>/
        ├── manifest.json
        ├── source/
        ├── knowledge/
        ├── practice/
        ├── replay/
        └── media/

The case pack is shared by Track A and Track B. Do not duplicate the same case definition under both tracks.

Track-local data may still exist when it is genuinely implementation-specific:

    tracks/track-a/data/   # Track A-only intermediate fixtures/adapters/tests
    tracks/track-b/data/   # Track B-only learner/evaluation fixtures

Track-local data must reference the canonical `case_id` and must not silently redefine the shared case manifest, rubric, practice task, or replay bundle.

Only create subdirectories a track actually needs. Empty directories do not need to be committed.

## 3. Case manifest

Every executable case pack must have `tracks/cases/<case_id>/manifest.json` with at least:

    case_id: <stable semantic slug>
    case_version: <version>
    status: CANDIDATE | ENGINEERING_FIXTURE | AUTHENTIC_SOURCE_READY | M0_VALIDATION | VALIDATED | INTEGRATED | REJECTED | SUPERSEDED
    source_mode: FORWARD | GOAL_CONDITIONED | CORRECTIVE
    runtime_class: LIVE | REPLAY | SYNTHETIC | ILLUSTRATIVE
    domain: <domain-or-null-before-selection>
    skill: <skill-or-null-before-selection>
    description/title: <short bounded purpose>

The manifest is the case entry point. Agents must not infer validation status from a directory name alone.

`tracks/cases/index.json` is the discovery registry. Add a case there when a new case pack is introduced.

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

Agents may create/change track-local fixtures, prompts, adapters, tests, implementation modules, and metadata.
Agents must not create/change without an explicit cross-track issue/decision: the eight common contracts, shared enum semantics, cross-track interfaces, product scope, deployment topology, or a database/service solely for future scalability.

Changes to `tracks/cases/` are cross-track data changes and should preserve manifest/replay validation.

## 10. Canonical replay expectation

Every implementation-ready case should document input artifact IDs, expected normalized outputs, negative cases, replay command, and expected pass/fail result.
This convention supports reproducibility; it is not evidence that the product hypothesis is validated.
