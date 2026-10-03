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

## Parallel development boundary

The two implementation tracks use a deliberately small handoff surface so they can build and validate independently:

- Track A produces source-grounded `KnowledgePackage` and `EvidenceRef` information plus a `PracticeTask`.
- Track B consumes a frozen replay version of those inputs and produces `LearnerAttempt`, `Evaluation`, `Feedback`, and `TransmissionRecord` information.
- The replay boundary is a test seam, not a requirement for a particular storage or service architecture.
- Real expert/learner evidence replaces fixtures only at the integration point.

This boundary should remain contract-first and implementation-agnostic until the bounded domain and actual interfaces are decided.

## 2026-10-03 Critical Path

The MVP flow is explicitly: expert demonstration → source processing → candidate knowledge → evidence grounding → expert review → baseline learner attempt → teaching → second attempt → criterion-level evaluation → evidence-linked feedback → retry → measured change → transmission record → lineage.

The baseline is important because without it the product cannot distinguish teaching from evaluation or claim transmission gain.
