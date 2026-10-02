# System Design — Anveshan

## 1. Architectural Objective

Build a source-grounded multimodal system that can move through:

**Capture → Understand → Structure → Ground → Teach → Practice → Verify → Transmit → Evolve**

The architecture must support a narrow MVP while leaving room for future knowledge domains.

## 2. High-Level Architecture

### Experience Layer

- Expert capture interface
- Learner interface
- Knowledge exploration/search
- Evidence view
- Teaching/apprenticeship view
- Practice submission
- Verification/feedback view
- Lineage view
- Governance/review interface

### Application / Orchestration Layer

- session orchestration
- capture workflows
- knowledge extraction workflow
- evidence workflow
- teaching workflow
- practice workflow
- verification workflow
- transmission workflow
- permissions workflow.

### AI Layer

- multimodal model inference
- transcription
- translation
- video understanding
- semantic embeddings
- retrieval
- reasoning
- structured extraction
- agentic orchestration.

### Knowledge Layer

- knowledge graph
- source records
- claims
- evidence
- people
- practices
- context
- lessons
- attempts
- feedback
- lineage
- versions
- permissions.

### Storage / Infrastructure

- source media storage
- structured data store
- graph representation
- vector/semantic index
- metadata store
- audit records
- secrets and credentials
- observability.

## 3. Core Logical Components

### Knowledge Agent

Purpose:
Convert multimodal source material into useful, structured, searchable knowledge.

Responsibilities:

- inspect source material
- transcribe
- identify speakers
- identify objects/actions
- extract claims
- extract steps
- extract conditions
- extract exceptions
- extract cues
- extract context
- build/modify knowledge relationships
- answer knowledge questions.

### Evidence Agent

Purpose:
Ensure that important answers and generated teaching material remain grounded.

Responsibilities:

- retrieve source evidence
- locate timestamps
- link claims to evidence
- identify support
- identify contradiction
- assess evidence sufficiency
- expose uncertainty
- distinguish source from inference
- generate evidence-aware answers.

### Transmission Agent

Purpose:
Move knowledge from expert representation to learner capability.

Responsibilities:

- understand learner level
- select source material
- create teaching sequence
- generate practice task
- inspect learner attempt
- compare against source evidence/rubric
- provide feedback
- support retry
- record transmission outcome
- create lineage event.

## 4. Deterministic Services

Not every capability should be agentic.

Deterministic or infrastructure services should handle:

- authentication
- authorization
- consent
- media upload
- storage
- transcription invocation
- indexing
- metadata persistence
- permission filtering
- audit logging
- evaluation logging
- deployment
- monitoring.

## 5. Source of Truth

Original source media should remain authoritative for source content.

Structured knowledge is a derived representation.

AI-generated explanations are derived representations.

A recommended hierarchy is:

**Original source → observed evidence → structured claim → AI interpretation → generated teaching**

Each layer should retain its relationship to the previous layer.

## 6. End-to-End Data Flow

1. Expert starts a capture session.
2. Source audio/video/images/documents enter the ingestion service.
3. Source files receive stable identifiers and metadata.
4. Speech is transcribed where applicable.
5. Video/image/document analysis extracts multimodal observations.
6. Knowledge Agent structures candidate knowledge objects.
7. Evidence Agent links claims to exact source material.
8. Knowledge representation is stored.
9. Expert reviews candidate representation.
10. Approved knowledge becomes available according to permissions.
11. Transmission Agent creates a learner experience.
12. Learner completes a practice task.
13. Learner evidence is ingested.
14. Transmission Agent evaluates observable performance.
15. Evidence Agent links feedback to source/rubric.
16. Learner retries.
17. Improvement is measured.
18. Transmission event is stored.
19. Lineage graph is updated.
20. New adaptations can later become new knowledge variants.

## 7. Knowledge Lifecycle

**Discover → Capture → Extract → Structure → Ground → Review → Govern → Teach → Practice → Verify → Transmit → Adapt → Preserve Lineage → Rediscover**

## 8. Security Boundary

Source material may be more sensitive than generated summaries.

Access checks should occur before retrieval and before generation.

A generated answer must not reveal restricted source material merely because the model can technically retrieve it.

## 9. Failure Handling

When evidence is missing:

- do not invent.
- say evidence is insufficient.
- identify what is missing.
- recommend the next evidence or question.

When sources conflict:

- preserve both.
- identify the conflict.
- explain contextual differences if evidence supports them.
- do not silently merge.

When learner evidence is ambiguous:

- mark uncertain.
- ask for another angle, recording, or measurement where appropriate.
- avoid overconfident competency judgments.

## 10. MVP Architecture Principle

The first implementation should be small.

A practical MVP can be:

- one capture flow
- one multimodal ingestion pipeline
- one knowledge representation
- one evidence retrieval path
- one teaching flow
- one practice upload
- one evaluation flow
- one feedback loop
- one lineage record.

Do not build a generalized platform before the end-to-end loop works.

## 11. Google Cloud Alignment

The final implementation should use current supported Google Cloud and Google AI capabilities appropriate to the hackathon.

Candidate technologies researched include:

- Gemini multimodal models
- Gemini transcription
- Gemini Live
- Gemini video understanding
- Gemini Embedding 2
- ADK
- Cloud Run
- agent evaluation tooling
- managed memory where justified.

Exact model names and API details must be verified against current documentation immediately before implementation.

