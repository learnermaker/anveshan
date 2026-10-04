# Track Common — The 8 Shared Contracts

**Status:** DECIDED & IMPLEMENTED frozen contract seam
**Scope:** Shared execution contracts for the current transmission MVP.

> This seam is deliberately **domain-agnostic and small**. It describes the proof boundary, not a particular skill, industry, framework, or deployment architecture.

## Start here
Track A, Track B, UI, fixture, and integration agents should read README.md, CONTRACT-USAGE.md, schemas/, validator.py, tests/, and tests/fixtures/transmission_case_001/.

## The 8 contracts
1. EvidenceRef — source/attempt evidence locator.
2. KnowledgePackage — structured expert-derived claims with provenance, consent, and review.
3. RubricDefinition — observable criteria and scoring policy.
4. PracticeTask — bounded learner exercise tied to package and rubric.
5. LearnerAttempt — observable learner submission; explicitly BASELINE or RETRY.
6. Evaluation — criterion-level observations and scores.
7. Feedback — evidence-grounded corrective guidance.
8. TransmissionRecord — proof artifact with deterministic gain and lineage.

## Domain-agnostic boundary
Do not put domain-specific assumptions into these schemas. Domain code may define terminology, source/media adapters, extraction prompts, observable criteria, modality-specific observation logic, task instructions, and UI presentation. Those details normalize into the shared contracts.

If a proposed change only makes one domain or one UI easier to implement, prefer an adapter instead of changing the seam.

## Authoritative data flow
source/evidence → track-local DTO or Gemini response → normalization adapter → tracks.common contract → deterministic validation → replay/integration/UI

Provider-specific JSON is not the canonical Anveshan model.

## UI / derived JSON rule
A UI may consume a derived JSON/view-model representation, but it remains downstream of validated common contracts. Preferred flow: common contract → adapter/view-model JSON → UI. Every major UI object should be traceable to common-contract identifiers.

## Offline validation
python -m pytest tracks/common/tests
python -m tracks.common.validator path/to/fixture.json
python -m tracks.common.validator tracks/common/tests/fixtures/transmission_case_001/ --bundle

Live Gemini is never required for deterministic contract/replay tests.

## Change policy
Do not reshape the eight contracts for convenience. If a genuine cross-track invariant is missing, open an issue, prove an adapter is insufficient, propose the smallest change, update tests/docs, and treat it as an explicit cross-track architecture decision.

See CONTRACT-USAGE.md for detailed guidance.

## Current prototype alignment — 2026-10-04

The frontend now demonstrates an adaptive workspace compiler, first-divergence inspection, adaptive micro-practice, deterministic gain, and lineage. These are downstream uses of the frozen seam, not new contracts.

The current workspace archetypes include Spatial Practice, Forensic Multimodal, Diagnostic, Rhythm, State Transition, Spatial Sequence, and First-Divergence workspaces. The common seam remains domain-agnostic.

Runtime/epistemic states are also downstream concerns. Replay fixtures may be labeled REPLAY, SYNTHETIC, or ILLUSTRATIVE; live Gemini may be labeled LIVE. Never encode UI-only runtime state into the eight contracts.

For target-first cases, EvidenceRef may point to a target image and its derived evidence. Visible target properties and inferred candidate procedures must remain distinguishable. The common seam does not assert creator intent or historical procedure.
