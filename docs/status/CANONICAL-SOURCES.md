# Anveshan — Canonical Source of Truth

## Purpose

This document tells humans and coding agents **where the current truth lives**.

GitHub `main` is the canonical latest integrated baseline.

Chat discussions, local notes, generated prompts, screenshots, PDFs, and research explorations are not canonical unless the decision is deliberately promoted into the appropriate repository document.

## Source-of-truth hierarchy

When documents disagree, use this order:

1. `AGENTS.md` — agent operating rules and source-of-truth hierarchy.
2. `README.md` — repository orientation/current status.
3. `docs/product/product-vision.md` — long-term product vision.
4. `docs/product/product-thesis.md` — current competition/MVP thesis and differentiation hypothesis.
5. `docs/product/mvp-contract.md` — minimum MVP behavior.
6. `docs/status/NOW.md` and `docs/status/project.yaml` — current execution scope/state.
7. `docs/validation/` — what has and has not actually been validated.
8. `docs/architecture/` — implementation architecture and boundaries.
9. `tracks/common/` — frozen common seam and validation rules.
10. `tracks/track-a/` and `tracks/track-b/` — track-specific execution guidance.
11. `app/` — current prototype/UI implementation and UI-specific decisions.
12. `docs/research/` — research findings and experiments; research is not implementation authorization unless explicitly promoted.
13. `docs/status/DECISIONS.md` — durable governance/decision record where applicable.
14. `docs/product/feature-universe.md` — possibility inventory, not scope.

Where two documents have different roles, both can remain true. For example, product vision can remain broad while the MVP contract is narrow.

## Current prototype research direction

The seven-case portfolio is a **capability test matrix**, not seven product verticals.

The current working transmission modes are:

### Forward

Demonstration → understanding → practice → verification.

### Goal-conditioned

Desired state/image → structure → plausible inferred path → practice → target verification.

### Corrective

Learner attempt → divergence → intervention → retry → verification.

**Goal-conditioned transmission and adaptive source-to-workspace composition are unvalidated hypotheses.**

## Seven-case prototype portfolio

| Case | Archetype | Primary source pattern | Workspace |
|---|---|---|---|
| Kolam | Spatial reconstruction | target image + optional authoritative/context source | Spatial Reconstruction Workspace |
| Bicycle repair | Diagnosis / decision | multimodal demonstration + learner attempt | Diagnostic Workspace |
| Micrometer | Precision / forensic evidence | controlled demonstration + attempt | Forensic Transmission Instrument |
| Handloom / weaving | State transition | controlled demonstration + attempt | State Transition Workspace |
| Tabla | Audio-visual temporal synchronization | audio/time alignment + optional video | Rhythm Practice Instrument |
| Origami | Sequential spatial transformation | demonstration + repeated attempts | Spatial Sequence Workspace |
| Square knot | First divergence / verification | attempt/reference + retry | First-Divergence Workspace |

## Source strategy

Do not force one dataset across all cases.

Preferred research/source posture:

- **Ego-Exo4D / ProSkill:** primary research evidence for procedural multimodal reasoning and bicycle repair.
- **EvoStruggle:** research evidence for origami/knot repeated attempts and struggle.
- **FoldingAgent:** research support for origami state reconstruction.
- **IIT Bombay Tabla dataset:** research support for audio/time-aligned rhythm understanding.
- **Kolam research/image sources:** support structured visual target analysis.
- **Anveshan-owned recordings/images:** preferred public prototype assets when research datasets have access or redistribution constraints.

See `docs/research/source-strategy-and-transmission-modes-2026-10-04.md` for detailed source notes and licensing/access posture.

## Prototype implementation posture

The prototype should demonstrate the following product claim:

> **The interface adapts because the structure of the capability and its evidence changes.**

Gemini should provide meaningful multimodal interpretation.

A deterministic layer remains authoritative for:

- common-contract integrity;
- rubric criteria and scoring;
- baseline/retry semantics;
- transmission gain;
- lineage/provenance structure.

The UI must preserve:

- evidence provenance;
- OBSERVED vs INFERRED vs UNKNOWN;
- research/replay vs live execution status;
- current Transmission Instrument strengths.

The current UI is a V0/reference workspace, not a disposable mock.

## Frozen common seam

The eight cross-track contracts remain:

1. `EvidenceRef`
2. `KnowledgePackage`
3. `RubricDefinition`
4. `PracticeTask`
5. `LearnerAttempt`
6. `Evaluation`
7. `Feedback`
8. `TransmissionRecord`

Different source modalities and generated workspaces do **not** justify common-contract expansion.

## Promotion rule

A new research idea becomes current product guidance only when it is:

1. explicitly decided;
2. documented in the appropriate product/architecture/status document;
3. reflected in implementation guidance where needed;
4. consistent with `docs/status/NOW.md`;
5. not described as validated until supporting evidence exists.

## Agent rule

Before coding, agents should inspect this document and then follow the linked canonical document for the specific decision they are implementing.

Do not reconstruct project truth from chat history when the repository already contains the relevant decision.

