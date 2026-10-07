# MVP Contract

**Review date:** 2026-10-03

This document defines the minimum behavior that must work before additional features are considered MVP.

## The MVP

The prototype must demonstrate:

### 1. One Expert

A real person with authentic knowledge.

### 2. One Bounded Skill

A task that can be demonstrated and attempted within a short session.

### 3. One Accountable Source

The selected bounded case must have an accountable, authorized source/input that supports observable practice and measurable verification.

For the original expert-transfer validation wedge, this is a real expert demonstration (video and/or audio) showing the expert performing and/or explaining the task.

The source-flexible prototype may additionally exercise:
- a desired target state/image;
- a learner attempt;
- or a combination.

Those modes must preserve their evidence boundaries and do not automatically constitute validated expert-procedure recovery.

### 4. One Knowledge Representation

The system extracts:

- steps;
- conditions;
- one or more non-obvious cues;
- exceptions where applicable;
- source references.

### 5. One Evidence Query

A difficult question must return an answer tied to the relevant source evidence/timestamp.

### 6. One Teaching Experience

The learner receives a concise source-grounded explanation and demonstration.

### 7. One Practice Task

The learner performs the same or closely related bounded task.

### 8. One Learner Attempt

The learner submits observable evidence.

### 9. One Evaluation

The system identifies observable differences against an explicit rubric or reference demonstration.

### 10. One Evidence-Grounded Feedback Loop

Feedback must point to what the learner did, what differs, and why the difference matters according to the source/rubric.

### 11. One Retry

The learner attempts again.

### 12. One Measured Outcome

Baseline and second-attempt performance are compared.

### 13. One Transmission Record

The system records:

Expert → Knowledge → Evidence → Learner → Attempt → Feedback → Improvement.

### 14. One Lineage Event

The record identifies the source and learner and leaves room for a later adaptation.

## Source flexibility

The MVP transmission loop remains narrow, but its source can be multimodal and need not always be a demonstration video.

For a selected bounded case, the source may be:
- an authentic demonstration;
- a desired target state/image;
- a learner attempt;
- or a combination.

The chosen source must support an observable, reviewable practice task and measurable verification.

For target-first cases, generated procedure is a candidate inferred path, not an asserted reconstruction of the original creator's process.

This is a source/input clarification, not a relaxation of the MVP proof requirements.

## Product surfaces (DECIDED 2026-10-07)

The MVP loop is shown through three role surfaces (`docs/product/product-vision.md` §9A):
- **Learner:** the transmission loop in plain language.
- **Creator:** create, check what the AI understood, publish with credit, licence and consent, then per-skill learner insights.
- **Steward:** a demo-grade console covering the review queue, library curation and moderation, consent and licence ledger, per-skill insights, and usage against budget.

All three run without accounts. A visitor cookie identifies creators, and a server-configured access code identifies stewards. Runtime state is temporary on the demo server, and durable decisions are exported and committed.

Per-skill insights and the steward usage view are narrow operational views. They are not the "broad analytics dashboard" excluded below.

## MVP Non-Requirements

The following are explicitly not required to prove the thesis:

- generalized knowledge marketplace;
- community-wide social network;
- universal ontology;
- complex genealogy;
- dozens of agents;
- broad analytics dashboard;
- automated discovery of every expert;
- fully autonomous governance;
- multi-domain deployment.

## Acceptance Rule

The MVP is not complete because every screen exists.

It is complete when the end-to-end transmission loop works for the selected validation mode with the appropriate accountable evidence and survives the required review/verification gate.

A replay/synthetic fixture can demonstrate engineering behavior, contract integrity, and deterministic evaluation. It does not by itself satisfy real-world product validation.

