# System Design — Anveshan

**Review checkpoint:** 2026-10-03

## 1. Architectural Objective

Build a source-grounded multimodal system that can prove one complete transmission event:

**Capture → Understand → Structure → Ground → Teach → Practice → Verify → Measure → Transmit → Evolve**

## 2. Architecture

### Experience
- expert capture;
- learner teaching;
- practice submission;
- evidence view;
- verification/feedback;
- transmission/lineage view.

### Orchestration
- capture workflow;
- extraction workflow;
- evidence workflow;
- teaching workflow;
- practice workflow;
- verification workflow;
- transmission workflow;
- permission workflow.

### AI
- transcription;
- multimodal video/audio/image understanding;
- structured extraction;
- semantic retrieval;
- evidence reasoning;
- teaching;
- learner-attempt analysis;
- agent/tool orchestration.

### Knowledge
- source records;
- claims;
- evidence;
- people;
- practices;
- context;
- lessons;
- attempts;
- feedback;
- transmissions;
- variants;
- lineage;
- permissions.

### Infrastructure
- Cloud Run;
- source media storage;
- metadata/transactional store;
- semantic index;
- audit records;
- authentication/authorization;
- observability.

## 3. Current Google Mapping

### Gemini 3.5 Transcribe
Use for source speech transcription where appropriate.

Current documentation supports 85+ locales, code-switching, speaker diarization and word timestamps. It also documents incompatibilities between some timestamp/diarization configurations and custom vocabulary. The implementation must select a feature combination deliberately rather than assuming all features compose.

### Gemini Video Understanding
Use for timestamp-grounded source inspection, action/context extraction and difficult evidence queries.

Current documentation supports timestamp references and multimodal audio/video analysis. Current video processing has static and agentic modes; fast action can be degraded by low frame sampling in static mode, so bounded demonstrations should be designed accordingly.

### Gemini Embedding 2
Use for cross-modal retrieval where needed. It supports a unified embedding space across text, image, video, audio and documents.

### ADK
Use only where agentic orchestration adds measurable value.

### Cloud Run
Use for the deployed prototype. Current Google documentation supports Cloud Run services, jobs and worker pools for different AI workloads and direct ADK deployment.

## 4. Core Logical Components

### Knowledge Agent

- inspect source;
- extract candidate knowledge;
- identify conditions, sequence, cues and exceptions;
- structure relationships;
- retrieve related knowledge.

### Evidence Agent

- retrieve source evidence;
- locate timestamps;
- support claims;
- identify contradictions;
- assess sufficiency;
- expose uncertainty.

### Transmission Agent

- create teaching sequence;
- create practice task;
- analyze learner evidence;
- compare against explicit rubric/reference;
- generate feedback;
- record outcome and lineage.

These are logical boundaries, not necessarily separate deployed services.

## 5. Deterministic Services

Keep these deterministic where possible:

- authentication;
- authorization;
- consent;
- media upload;
- source identifiers;
- storage;
- indexing;
- permission filtering;
- audit logging;
- evaluation case management;
- metric calculation.

## 6. Source Hierarchy

**Original source → observed evidence → structured claim → AI interpretation → generated teaching**

A derived object must never overwrite the source.

## 7. Evidence Model

A claim should carry:

- source ID;
- timestamp;
- speaker;
- modality;
- context;
- original language;
- support/contradiction state;
- verification state.

## 8. Learner Evaluation Architecture

Do not ask a general-purpose model to return an unconstrained "skill score."

Instead:

1. define a domain-specific rubric;
2. identify observable criteria;
3. collect learner evidence;
4. identify relevant segments;
5. compare against reference evidence/rubric;
6. return criterion-level observations;
7. attach evidence;
8. mark ambiguous criteria uncertain;
9. optionally route to expert review;
10. aggregate only after criterion-level results exist.

This is a critical architectural boundary.

## 9. Evaluation Infrastructure

Every major AI workflow should have evaluation cases.

Track:

- input;
- expected behavior;
- model output;
- evidence;
- tool calls;
- latency;
- cost where relevant;
- human rating;
- automated rating;
- failure category.

Current Google Agent Platform evaluation supports trace-based evaluation, reference-based and reference-free metrics, and iterative optimization. Anveshan should adopt the same principle even if the final implementation uses a simpler local harness.

## 10. Security Boundary

Permission checks must happen before source retrieval and before model context construction.

Technical model access is not authorization to disclose.

## 11. Failure Handling

If evidence is missing:
- state insufficiency;
- identify missing evidence;
- ask for the next source/question.

If sources conflict:
- preserve both;
- identify the conflict;
- do not silently merge.

If learner evidence is ambiguous:
- mark uncertain;
- request another observation or human review.

## 12. MVP Architecture

The first implementation should contain:

- one capture flow;
- one multimodal ingestion path;
- one source-grounded knowledge representation;
- one evidence retrieval path;
- one teaching flow;
- one practice submission;
- one criterion-level evaluation path;
- one feedback loop;
- one retry;
- one transmission record.

Do not build a generalized platform first.
