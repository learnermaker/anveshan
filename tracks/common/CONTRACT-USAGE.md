# Common Contract Usage Guide

**Status:** DECIDED guidance for Track A, Track B, UI, fixtures, and integration agents.

## Purpose

`tracks/common/` is the authoritative execution seam for the transmission MVP. The eight Pydantic contracts are intentionally small and **domain-agnostic**. They describe what must cross the Track A → Track B boundary, not which skill, industry, profession, or modality the team must choose.

## Frozen contracts

1. `EvidenceRef` — source/attempt evidence locator.
2. `KnowledgePackage` — structured expert-derived claims with provenance, consent, and optional expert review.
3. `RubricDefinition` — observable scoring criteria and scoring policy.
4. `PracticeTask` — bounded learner exercise tied to a package and rubric.
5. `LearnerAttempt` — observable learner submission; explicitly BASELINE or RETRY.
6. `Evaluation` — criterion-level observations and scores.
7. `Feedback` — evidence-grounded corrective guidance.
8. `TransmissionRecord` — immutable proof artifact with deterministic gain and lineage.

## Domain-agnostic rule

Do not encode assumptions such as soldering, cooking, sports, healthcare, manufacturing, or any particular tool into the shared schemas.

A selected domain may define its own:
- source-specific metadata;
- terminology;
- extraction prompts;
- modality adapters;
- task details;
- rubric criteria;
- evaluation heuristics;
- UI presentation.

Those belong in the owning track or an integration adapter. They must normalize into the common contracts.

## Contract direction

```
authentic source
  ↓
Track A extraction DTO / internal model
  ↓
normalize
  ↓
KnowledgePackage + EvidenceRef[] + RubricDefinition + PracticeTask
  ↓
Track B
  ↓
LearnerAttempt + Evaluation + Feedback + TransmissionRecord
```

Model/provider-specific JSON is never the authoritative domain model.

## Evidence rule

An evidence reference identifies what can be inspected. For media it may contain timestamps; for text/image/sensor evidence the locator semantics may differ.

Never manufacture a locator, observation, confidence, or verification state merely to make a fixture look complete.

Use:
- `OBSERVED` for source-backed observation;
- `INFERRED` only for an explicit interpretation;
- `UNVERIFIED` when the claim/evidence has not been established.

`confidence` is supporting metadata, not a substitute for evidence.

## Rubric rule

`RubricDefinition` is the scoring authority.

AI may locate/interpret evidence and propose criterion observations, but must not silently redefine:
- criteria;
- weights;
- passing semantics;
- transmission gain.

## Attempt/evaluation rule

Baseline and retry are distinct evidence events:
- BASELINE = attempt 1;
- RETRY = attempt 2 or later.

The same learner/task/rubric context must be retained for the MVP comparison.

## Transmission rule

`TransmissionRecord.transmission_gain` is deterministic:

`retry_score - baseline_score`

Never display or persist a model-generated gain as authoritative.

## UI and JSON adapter rule

The UI may consume a derived JSON/view-model representation for convenience. That representation is an **adapter**, not a new source of truth.

Preferred:

```
common contract → validated adapter/view-model JSON → UI
```

Avoid:

```
UI mock model → disconnected product model → later attempt to reconcile with common contracts
```

Every major UI object should be traceable to one or more common contract IDs.

## Validation

Run:

```bash
python -m pytest tracks/common/tests
python -m tracks.common.validator <fixture.json>
```

For the complete replay bundle:

```bash
python -m tracks.common.validator tracks/common/tests/fixtures/transmission_case_001/ --bundle
```

Tests and fixtures demonstrate engineering behavior. They do not by themselves validate the real-world product hypothesis.

## Change policy

Do not expand or reshape the eight contracts to make one track or UI implementation convenient.

If a genuinely missing cross-track invariant is discovered:
1. open an issue;
2. demonstrate why the existing seam cannot express it;
3. prefer an adapter before changing the shared contract;
4. update tests and documentation with the change;
5. treat the change as a cross-track architectural decision.

The goal is a **small stable seam**, not a generalized platform model.


## Parallel UI work — non-negotiable boundary
UI development may proceed in parallel with Track A and Track B. Track agents must not modify shared contracts merely to satisfy a UI shape, and UI code must not become an alternate canonical model.
For UI-facing data: start from a validated common contract; create a downstream adapter/view-model when needed; preserve stable contract IDs and lineage references; keep presentation state and UI-only fields out of canonical contracts; and raise an explicit cross-track issue if the seam genuinely cannot express a required invariant.
Track A/B agents should assume UI code may change independently. Do not import UI implementation modules into track logic or make tests depend on UI component structure.

## Agent operating rule
Before coding, identify the exact contract(s) owned by the change, the fixture that proves the behavior, and the boundary that must remain untouched. Prefer the smallest local adapter or deterministic helper over shared-schema changes.
