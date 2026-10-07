# Business Requirements Document — Anveshan

**Status:** Draft competition/MVP requirements  
**Scope:** This BRD defines the current prototype wedge, not the complete Anveshan product vision. See `docs/product/product-vision.md`.
**Product name:** TBD  
**Working project/team/repository:** Anveshan  
**Hackathon:** Google Cloud AI Builder Cup 2026

## 1. Purpose

This BRD converts the exploration into an explicit requirements framework without deleting the broader feature universe.

It defines the problem, users, product outcome, requirements, scope boundaries, success criteria, risks, and unresolved decisions.

It does not override the exploration record. It represents the current decision layer and should be updated as evidence changes.

## 2. Product Vision

Enable human knowledge to move from one person to another without losing the source, context, evidence, lineage, or ability to evolve.

## 3. Problem Statement

Valuable embodied and experiential knowledge often remains inside individuals and is difficult to transfer through conventional documents.

Existing systems commonly specialize in one of the following:

- memory capture
- oral history
- document search
- industrial instructions
- generic AI tutoring
- cultural archiving
- expert support

Anveshan explores the intersection where an appropriate source becomes source-grounded knowledge, adaptive transmission, learner practice, evidence-based verification, and lineage. A source may be a demonstration, desired target state, learner attempt, or combination.

## 4. Target Users

### 4.1 Knowledge Holder / Expert

A person with valuable practical, cultural, professional, local, or embodied knowledge.

Needs:

- easy capture
- ability to demonstrate rather than only explain
- control over interpretation
- source attribution
- correction
- access control
- ability to see what the system extracted
- ability to teach a learner.

### 4.2 Learner / Apprentice

A person trying to acquire the knowledge.

Needs:

- understandable instruction
- authentic expert demonstration
- context
- practice
- feedback
- retries
- progress
- evidence of competency.

### 4.3 Community / Knowledge Owner

A group whose knowledge is collective, contextual, restricted, or culturally sensitive.

Needs:

- governance
- consent
- access control
- contextualization
- variant preservation
- correction
- approval
- revocation.

### 4.4 Curator / Reviewer

A person responsible for validating source material and structured knowledge.

Needs:

- evidence views
- provenance
- review queues
- contradiction detection
- correction workflows.

### 4.5 Product roles (DECIDED 2026-10-07)

The users above map to three product roles (`docs/product/product-vision.md` §9A):

| Role | Covers | Surface |
|---|---|---|
| **Learner** | 4.2 | Library → Learn → Practise → Results, in plain language. No audit tooling. |
| **Creator** | 4.1 | "My skills": create from a demonstration, check what the AI understood, publish with credit, licence and consent, see how learners are doing |
| **Steward** | 4.3, 4.4 | Steward console: review queue, library curation and moderation, consent and licence ledger, learner insights, usage and cost |

Steward needs, in addition to 4.3 and 4.4:
- one queue for everything awaiting a decision;
- publish and unpublish;
- a consent and licence record per skill that can be exported;
- aggregate learner insights (never per-learner identities);
- AI usage against budget;
- a clear statement of what is temporary versus durable.

## 5. Primary Job to Be Done

> When valuable human expertise exists primarily in people and demonstrations, help us capture it faithfully, make it searchable and teachable, enable another person to practice it, evaluate the transmission, and preserve how the knowledge evolves.

## 6. Product Outcome

A completed knowledge transmission record.

Minimum conceptual record:

Expert → Knowledge → Evidence → Lesson → Learner → Attempt → Feedback → Retry → Transfer → Lineage

## 7. Primary User Journey

1. Expert begins a capture session.
2. Anveshan records voice/video/context.
3. AI transcribes and analyzes multimodal evidence.
4. AI extracts structured knowledge.
5. Evidence links are created.
6. Expert reviews and corrects the representation.
7. A learner is given a source-grounded transmission experience appropriate to the source mode.
8. Learner performs a bounded practice task.
9. Learner submits an attempt.
10. Anveshan evaluates observable differences.
11. Anveshan gives evidence-grounded feedback.
12. Learner retries.
13. Improvement is measured.
14. Transmission is recorded.
15. Adaptation and lineage are preserved.

## 8. Functional Requirements

### FR-01 Capture

The system shall support recording or importing authentic source material.

### FR-02 Multimodal analysis

The system shall analyze relevant audio, video, image, document, and textual inputs.

### FR-03 Structured extraction

The system shall convert source material into structured knowledge objects.

### FR-04 Tacit/conditional extraction

The system should identify observable conditional rules, exceptions, cues, judgments, sequences, and context.

### FR-05 Provenance

Important claims shall retain links to source evidence.

### FR-06 Uncertainty

The system shall distinguish known, inferred, disputed, and unknown information.

### FR-07 Contradiction

The system shall preserve material differences rather than silently merging them.

### FR-08 Expert review

The knowledge holder should be able to review and correct extracted knowledge before publication or teaching where appropriate.

### FR-09 Teaching

The system shall convert validated knowledge into a learner experience.

### FR-10 Practice

The learner shall have a concrete practice task.

### FR-11 Learner evidence

The learner shall be able to submit an observable attempt.

### FR-12 Evaluation

The system shall analyze the learner attempt against source evidence or an explicit rubric.

### FR-13 Feedback

Feedback shall identify observable differences and link to evidence where possible.

### FR-14 Retry

The learner should be able to retry after feedback.

### FR-15 Transmission record

The system shall record the transmission event.

### FR-16 Lineage

The system shall preserve who learned from whom and how the practice was adapted.

### FR-17 Governance

The system shall support access and consent controls appropriate to the knowledge.

### FR-18 Search

Users should be able to find knowledge through natural language and relevant multimodal queries.

### FR-19 Knowledge graph

The system should maintain relationships among people, practices, evidence, learners, and transmissions.

### FR-20 Knowledge Scout

Future versions should identify missing evidence, knowledge gaps, and potential knowledge holders.

## 9. Non-Functional Requirements

### NFR-01 Grounding

The system should minimize unsupported generation.

### NFR-02 Traceability

Important outputs should be traceable to source evidence.

### NFR-03 Privacy

Private or restricted knowledge must not become discoverable outside authorized access.

### NFR-04 Consent

Source contributors must understand and control appropriate uses of their material.

### NFR-05 Reliability

The system should fail safely when evidence is insufficient.

### NFR-06 Explainability

Users should understand the source and status of important claims.

### NFR-07 Performance

The prototype should provide a compelling interactive experience within a hackathon demo.

### NFR-08 Security

Data, credentials, and permissions must be handled using appropriate Google Cloud security controls.

### NFR-09 Deployability

The working prototype must satisfy the competition's Google Cloud deployment requirements.

## 10. MVP Boundary

The MVP should be intentionally narrow.

Required conceptual path:

**One accountable source → one bounded skill → one source-grounded representation → one learner → one attempt → one feedback loop → one improvement measurement → one transmission record.**

The original expert-transfer wedge uses one real expert as the accountable source. Goal-conditioned and corrective source modes are documented research extensions.

The exact domain and skill are not yet locked.

## 11. Out of Scope for MVP

Unless validation changes the decision, the MVP should not attempt:

- broad family genealogy
- full social network
- knowledge marketplace
- enterprise knowledge-management suite
- multi-domain universal ontology
- large-scale cultural archive
- high-stakes healthcare guidance
- emergency response system
- autonomous community governance
- complex credential marketplace
- fully general-purpose AI tutor
- synthetic deceased-person avatars
- exhaustive agent swarm.

## 12. Success Metrics

Primary:

- successful end-to-end transmission
- learner improvement
- expert agreement
- evidence-grounded answer quality
- feedback correctness.

Candidate flagship metric:

**Transmission Gain = post-transmission learner performance − baseline learner performance**

Secondary:

- extraction accuracy
- citation/timestamp accuracy
- contradiction detection
- source coverage
- time-to-learning
- completion rate
- learner retry improvement.

## 13. Critical Product Hypotheses

H1. Multimodal AI can extract meaningful knowledge from authentic demonstrations.

H2. The system can ground important answers in exact source evidence.

H3. Extracted knowledge can be transformed into useful teaching.

H4. The system can evaluate a bounded learner attempt.

H5. Evidence-grounded feedback can improve the learner's second attempt.

H6. The expert considers the representation faithful.

H7. The complete experience is compelling and understandable in a short demonstration.

## 14. Kill Criteria

Stop, simplify, or pivot if:

- expert fidelity is poor
- evidence retrieval is unreliable
- learner feedback is generic
- learner improvement cannot be measured
- authentic data cannot be obtained
- the experience looks like an ordinary tutor
- the demo requires excessive explanation.

## 15. Product Principles

- Evidence over eloquence.
- Source before summary.
- Interpretation is not source truth.
- Uncertainty is valid.
- Variants are knowledge.
- Community control matters.
- Transmission matters more than storage.
- Human expertise remains authoritative within context.
- Source evidence outranks generated explanation.
- No fabricated authority.
- The interface should adapt to the reasoning problem.

## 16. Dependencies

- authentic expert
- authentic learner
- authorized source evidence
- suitable bounded skill
- Gemini/Google AI capabilities
- Google Cloud deployment
- multimodal processing
- secure storage
- retrieval/indexing
- evaluation rubric.

## 17. Open Decisions

- initial domain
- exact skill
- expert
- learner
- practice task
- evaluation rubric
- graph storage technology
- agent boundaries
- persistence strategy
- UI flow
- final product name
- final visual identity.

## 18. Decision Rule

When a feature competes with the core transmission loop for build time, the team should prioritize the feature only if it improves:

1. knowledge fidelity,
2. evidence grounding,
3. learner transmission,
4. verification,
5. lineage,
6. judge-visible technical merit.

Everything else is secondary until the core loop works.
