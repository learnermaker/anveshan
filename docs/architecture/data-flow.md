# End-to-End Data Flow — Anveshan

## Flow A — Expert Capture

Expert → Capture UI → Media Storage → Metadata → Multimodal Processing → Knowledge Agent → Candidate Knowledge → Evidence Agent → Expert Review → Approved Knowledge.

## Flow B — Knowledge Query

User Question → Permission Check → Semantic Retrieval → Knowledge Graph → Evidence Retrieval → Evidence Agent → Grounded Answer → Source/Timestamp View.

## Flow C — Teaching

Learner Profile → Validated Knowledge → Transmission Agent → Teaching Sequence → Source Demonstration → Explanation → Practice Task.

## Flow D — Practice

Learner → Practice Task → Video/Audio/Image/Text Submission → Media Processing → Observable Features → Transmission Agent → Comparison → Feedback → Retry.

## Flow E — Verification

Learner Attempt → Evidence Extraction → Reference Demonstration/Rubric → Comparison → Uncertainty Assessment → Evidence-Linked Feedback → Human Review if Required.

## Flow F — Transmission

Baseline → Attempt → Feedback → Retry → Outcome → Transmission Gain → Transmission Record → Lineage Graph.

## Flow G — Evolution

Learner Adaptation → Context + Evidence → Review → Variant → Version → New Transmission → Updated Lineage.

## Flow H — Knowledge Scout

Knowledge Graph → Coverage Analysis → Gap Detection → Candidate Knowledge Holder → Question Generation → Capture → Evidence → Graph Update.

## Permission Boundary

Every retrieval flow must check access before source content is passed to AI generation.

## Provenance Boundary

Every derived representation should preserve its relationship to source evidence.

## Failure Boundary

If source evidence is insufficient, the flow should stop at uncertainty rather than generate unsupported content.

## Case-pack boundary

Canonical shared case content lives under `tracks/cases/<case_id>/` and is discovered via `tracks/cases/index.json`.
Track-local `tracks/track-a/data/` and `tracks/track-b/data/` are implementation-specific fixtures/metadata only; they must not become duplicate case authorities.
Large media belongs in an appropriate object store when deployed; mutable runtime state belongs in a runtime datastore when deployment requirements justify one.

## Parallel development boundary

The two implementation tracks use a deliberately small handoff surface so they can build and validate independently:

- Track A produces source-grounded `KnowledgePackage` and `EvidenceRef` information plus a `RubricDefinition` and `PracticeTask`.
- Track B consumes a frozen replay version of those inputs and produces `LearnerAttempt`, `Evaluation`, `Feedback`, and `TransmissionRecord` information.
- The replay boundary is a test seam, not a requirement for a particular storage or service architecture.
- Real expert/learner evidence replaces fixtures only at the integration point.
- The common seam remains the eight frozen contracts in `tracks/common/schemas/`.

This boundary should remain contract-first and implementation-agnostic. The exact handoff is documented in `docs/architecture/parallel-work-contract.md`; shared contracts and integration adapters remain outside the two track ownership folders.

## 2026-10-04 Critical Path

The MVP critical path is explicitly:

**accountable source → source processing → candidate knowledge → evidence grounding → expert review → baseline learner attempt → grounded teaching → learner retry → criterion-level evaluation → evidence-linked feedback → measured change → transmission record → lineage**

The baseline is required because without it the product cannot distinguish initial performance from post-teaching improvement.

Replay fixtures may demonstrate engineering/capability behavior, but they do not by themselves establish product validation.