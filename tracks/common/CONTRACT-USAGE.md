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


## Source-type flexibility

The common seam intentionally does not require a video demonstration as the source.

A normalized transmission flow may originate from:
- a demonstration;
- a desired state/image;
- a learner attempt;
- or a combination.

This does not change the eight frozen contracts. Source modality and UI composition remain upstream/downstream concerns.

For target-first cases, preserve the evidence distinction between visible target facts and inferred candidate procedures. Do not manufacture historical procedure, intent, provenance, or cultural meaning from a final image.


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


## Current prototype boundary — 2026-10-04

The current UI demonstrates three useful downstream behaviors:

1. **Workspace composition** — choose a capability-specific interaction model from validated evidence/mode characteristics;
2. **First divergence** — focus the UI on the earliest meaningful criterion/evidence mismatch;
3. **Adaptive retry** — derive a bounded micro-practice from the failed criterion.

None requires a new common contract. Use downstream adapters/view models and retain the stable IDs from the eight contracts.

### Epistemic state mapping

The common evidence enum is:

OBSERVED | INFERRED | UNVERIFIED

A UI may display UNVERIFIED as UNKNOWN, but this is a presentation mapping, not a new canonical state.

### Replay/live mapping

LIVE, REPLAY, SYNTHETIC, and ILLUSTRATIVE are runtime/fixture labels, not common-contract fields. Keep them in test metadata, model gateway state, or UI view models.

### Target-first rule

For a desired-state/image source:
- observable target properties may become source-grounded evidence;
- candidate construction strategy is explicitly inferred;
- original creator process, intent, or provenance must not be invented.

### Transmission result rule

The common seam can prove deterministic improvement in the configured rubric frame. It cannot, by itself, prove real-world mastery, generalization, certification, or causal transfer.

## Proof levels — mandatory interpretation

Do not conflate three different kinds of success:

1. **Engineering proof** — contracts, normalization, validation, replay, failure handling, and deterministic aggregation work correctly.
2. **Capability proof** — a bounded case demonstrates that the relevant multimodal grounding, observation, reasoning, or adaptation capability works on appropriate evidence.
3. **Product proof** — an authentic accountable expert-to-learner transmission event demonstrates grounded teaching, observable practice, evidence-linked correction, retry, and measured change.

A replay/synthetic fixture can satisfy engineering proof and support capability development. It cannot by itself satisfy product proof or justify claims of real-world knowledge transmission.

For goal-conditioned or corrective cases, capability success does not automatically establish the original expert-transfer wedge. Those cases need an appropriate accountable source and evidence path before being treated as product validation.

## Improvement versus transmission claim

`TransmissionRecord.transmission_gain` measures change within the configured rubric frame. It is an observed outcome, not by itself proof of mastery, generalization, or causal transfer from the expert.

A stronger product claim requires the surrounding provenance chain: accountable source → grounded knowledge/practice input → learner baseline → evidence-grounded intervention → comparable retry → observed change → lineage.

## Adaptive retry comparability

A downstream retry may narrow practice to a failed criterion, but it must remain comparable to the baseline under the same rubric and must not create artificial gain by materially lowering evaluation difficulty. The system should preserve what changed in scope and evidence between attempts.

## Uncertainty versus improvement

A transition such as `UNCERTAIN → SATISFIED` may reflect improved observability rather than improved skill. Do not automatically characterize such a change as skill improvement without sufficient comparable evidence.

## Intervention traceability

When feedback targets a criterion, the retry evaluation should preserve that criterion so the system can determine whether the targeted deficiency changed. This supports the prototype's first-divergence → micro-practice → retry loop without adding a UI-specific contract.
