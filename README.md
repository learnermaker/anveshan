# Anveshan

> Working project name: Anveshan  
> Product name: TBD  
> Hackathon: Google Cloud AI Builder Cup 2026  
> Research checkpoint: 2026-10-03

## Current thesis

Anveshan is exploring an AI-powered system for **making a specific piece of human expertise transmissible from one person to another, while preserving its source, evidence, uncertainty, and lineage**.

> **Anveshan turns an expert's authentic demonstration into source-grounded apprenticeship, observes the learner's attempt, provides evidence-linked feedback, measures whether performance improved, and records the transmission lineage.**

This is deliberately narrower than "preserve all human knowledge." The broad vision remains important, but the MVP must prove one complete transmission event.

### Core loop

**DEMONSTRATE → UNDERSTAND → GROUND → TEACH → PRACTICE → VERIFY → TRANSMIT → EVOLVE**

## What is and is not novel

Anveshan does **not** claim novelty for AI interviews, tacit-knowledge extraction, knowledge graphs, multimodal RAG, AI tutoring, apprenticeship assistance, learner video assessment, expert cognition modeling, or agentic workflows. These are active product/research areas.

The current differentiation hypothesis is the **knowledge transmission event**:

**authentic expert source → structured knowledge → evidence → teaching → learner attempt → evidence-based feedback → measurable improvement → lineage**

See docs/product/novelty-boundary.md.

## Current proof contract

The MVP must prove:

> **one real expert + one bounded skill + one authentic demonstration + one source-grounded knowledge representation + one learner + one practice task + one learner attempt + one evidence-grounded feedback loop + one retry + one measurable improvement + one transmission record + one lineage event**

See docs/product/mvp-contract.md.

## Current conceptual architecture

1. Capture authentic demonstrations and context.
2. Understand speech, actions, objects, sequence, conditions and cues.
3. Represent candidate knowledge and relationships.
4. Ground claims in source evidence.
5. Teach through a concise apprenticeship.
6. Practice a bounded task.
7. Verify against an explicit rubric/reference.
8. Record transmission.
9. Preserve evolution and lineage.

## Current AI architecture

### Knowledge Agent
Capture → extract → structure → retrieve.

### Evidence Agent
Ground → verify → cite → detect uncertainty and contradiction.

### Transmission Agent
Teach → create practice → evaluate attempts → provide feedback → update lineage.

These are logical responsibilities, not a requirement to create three autonomous agents. Deterministic services should handle ingestion, permissions, storage, indexing, auditability and evaluation.

## Current Google stack hypothesis

Current research supports a credible implementation using:

- Gemini 3.5 Transcribe;
- Gemini video understanding;
- Gemini Embedding 2;
- ADK;
- Cloud Run;
- agent evaluation.

Model names, feature compatibility, quotas, pricing and launch stages must be checked again immediately before implementation.

## Governance principle

The product must not turn human knowledge into unreviewed machine-generated authority.

Source statement, observed evidence, AI interpretation, community interpretation and unknown remain distinct.

Do not claim "community-owned" unless the relevant community actually governs the data and its use.

## Current status

**Research → Product Definition → Validation**

No core product hypothesis is marked validated yet.

The exact domain, skill, expert, learner and evaluation rubric remain open until authentic access is confirmed.

## Documentation

See docs/README.md for the complete map. The repository separates EXPLORED, DECIDED and IMPLEMENTED material so research does not silently become product scope.
