# NOW — Current Execution Scope

This is the shortest current-scope contract for humans and coding agents.

## Current phase

**ACTIVE DEVELOPMENT — M1 VERTICAL SLICE**

Implementation is now authorized and underway. Product validation continues in parallel; implemented engineering behavior must not be described as validated product evidence.

## Current MVP wedge

Anveshan helps an expert transmit a bounded piece of real-world expertise to another person, grounded in authentic evidence, with observable practice and verification of whether the knowledge transferred.

## Hero cases (decided 2026-10-06)

Live, end to end, on Cloud Run:

| Case | Input (source) | Learner attempt | Evaluation core |
|---|---|---|---|
| Kolam | final image only (goal-conditioned) | canvas trace or photo upload | goal-trajectory verification over the image-derived goal model |
| Origami | demonstration video (forward) | video upload | Gemma frame-state recognition + deterministic trajectory |
| Tabla | audio (forward; optional video displayed only) | audio upload | deterministic onsets/tempo/bayan alignment (optional audio model for bols) |

Micrometer, bicycle repair, handloom and square knot are **SYNTHETIC replay showcase only** (scope trade for the hero cases).
Sources are licensed internet media and user uploads; no human recordings are required for the hackathon build.
See `docs/plans/track-plan-review-2026-10-06.md` §9 and `docs/plans/evaluation-core.md`.

**Universal pipeline (IMPLEMENTED 2026-10-07, priority over tuning single hero media):** any uploaded image, video or audio skill is composed (Perception → SkillModel → deterministic evaluation) and learner attempts are verified against it. Evidence: `docs/validation/experiments.md` E6; design and known limits: `docs/plans/universal-pipeline.md` §12. Cloud Run deployment is pending (`docs/deploy/DEPLOY-CHECKLIST.md`). Remaining work and order: `docs/plans/NEXT-STEPS.md`.

**Product roles and surfaces (IMPLEMENTED 2026-10-08, branch `k9/integration`, pending merge to main):**
- **Learner:** plain language with no audit tooling.
- **Creator:** "My skills": check what the AI understood, publish, insights.
- **Steward:** console for the review queue, library, consent and licences, insights, and usage.

Product definition: `docs/product/product-vision.md` §9A and `docs/product/user-journeys.md` Journeys 7–8. Build spec: `docs/kiro/specs/K9-ORCHESTRATOR.md`. Gate evidence: `docs/validation/experiments.md` E-K9.

Scope trades for this change:
- **Deferred to NEXT:**
  - universal-path robustness (technical-panel plan WS6);
  - accounts, persistent storage and a full admin console.
- **Still deferred:** the `universal.py` split (WI-8.3).

## Scope firewall

1. Research does not authorize implementation.
2. Technical capability does not authorize a product feature.
3. Feature-universe entries are not MVP commitments.
4. Every implementation task requires a bounded issue.
5. Every PR requires an issue link, explicit scope, acceptance criteria, and validation evidence.
6. Adding scope requires removing, reducing, or deferring other work.
7. If work is not necessary for the current gate, stop and create a research or scope-change issue.
8. Prefer automation over ceremony.
9. Completed implementation work should be merged into `main` promptly; `main` is the canonical latest integrated baseline.

## Operating target

Reach the first credible product proof with the **minimum coordination overhead**:

**validate the capability → lock a bounded use case → build the smallest vertical slice → measure transmission → harden only what the evidence requires → demo → submit**

## Canonical decision references

For current research/product/prototype direction, use `docs/status/CANONICAL-SOURCES.md` as the index into the authoritative documents.

Current promoted prototype research includes:
- seven-case capability portfolio;
- forward, goal-conditioned, and corrective transmission modes;
- target-image-first Kolam as a proposed goal-conditioned case;
- research-source vs shippable-asset distinction;
- adaptive source-to-workspace composition as an unvalidated GenUI hypothesis.

These do not change the frozen common seam or, by themselves, authorize unrelated implementation.

## Gates

- M0 — Capability validation — completed as the authorization point for implementation
- M1 — Vertical slice — current
- M2 — Productization
- M3 — Reliability
- M4 — Demo
- M5 — Submission

Do not spend materially on a later gate while an earlier gate is failing unless the work is explicitly exploratory.

## Team execution rule

Three people and their agents may work in parallel when ownership boundaries are clear. Optimize for independent workstreams, short integration loops, and early evidence rather than formal ceremonies.

For two-developer parallel delivery: Track A owns expert intelligence and grounding; Track B owns practice, evaluation, and transmission. Both work against frozen cross-track contracts and replay fixtures, so neither track requires the other's implementation to make progress. Integration occurs only after both tracks have independent proof.

The shared seam is intentionally small: `KnowledgePackage`, `EvidenceRef`, `RubricDefinition`, `PracticeTask`, `LearnerAttempt`, `Evaluation`, `Feedback`, and `TransmissionRecord`. These names describe the execution boundary, not a commitment to implement every object immediately.

## Scope buckets

- **NOW:** required for the current gate or explicitly approved MVP work.
- **NEXT:** post-gate possibilities; not implementation-authorized.
- **EXPLORE:** research only.
- **REJECTED/SUPERSEDED:** do not resurrect without a new explicit decision.
