# Anveshan

> Working project name: Anveshan  
> Product name: TBD  
> Hackathon: Google Cloud AI Builder Cup 2026  
> Research checkpoint: 2026-10-03

## Product vision

Anveshan is a **living intelligence layer for human expertise, experience, and memory**.

Its long-term purpose is to make human knowledge **discoverable, preservable, transferable, verifiable, and continuously evolving** across people, generations, communities, and organizations.

The product is not defined by video, a chatbot, an LMS, a family archive, or an enterprise knowledge base. Those are possible applications and interfaces. The underlying system supports:

**CAPTURE → UNDERSTAND → GROUND → TRANSMIT → PRACTICE → VERIFY → EVOLVE**

### Core layers

**Memory** — What happened?  
**Expertise** — What does someone know, and how did they come to know it?  
**Capability** — Can another person actually use it?

### Product surfaces

- **Personal** — accumulated individual knowledge;
- **Social / Family / Elders** — intergenerational memory and living knowledge;
- **Community / Culture** — community-held practices, traditions, languages, and local knowledge;
- **Education / Apprenticeship** — teaching, practice, and skill transfer;
- **Enterprise** — institutional expertise, expert-to-worker transfer, and knowledge continuity;
- **Research** — exploration and synthesis of accumulated human experience.

### Multimodality

**Video is one modality, not the product.**

Anveshan can combine video, audio, text, images, documents, conversations, demonstrations, simulations, operational data, and learner attempts.

### Long-term vision

> **Anveshan makes human expertise discoverable, preservable, transferable, verifiable, and continuously evolving across people, generations, communities, and organizations.**

See `docs/product/product-vision.md` for the full product vision.

## Current competition thesis

For the Google Cloud AI Builder Cup 2026, the broad product vision is being narrowed into a single demonstrable use case.

The current working direction remains:

> **Anveshan helps an expert transmit a bounded piece of real-world expertise to another person, grounded in authentic evidence, with observable practice and verification of whether the knowledge transferred.**

This is a prototype wedge, not the definition of the company.

### Prototype loop

**DEMONSTRATE → UNDERSTAND → GROUND → TEACH → PRACTICE → VERIFY → EVOLVE**

The exact domain and skill remain open until authentic access and feasibility validation are confirmed.

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

See docs/README.md for the complete map. The repository separates EXPLORED, DECIDED, VALIDATED and IMPLEMENTED material so research does not silently become product scope. See `AGENTS.md` for the source-of-truth hierarchy used by coding agents.

## Implementation Status

The repository is currently a **research/validation workspace**, not yet the runnable competition prototype. Application source, deployment configuration and CI are intentionally added only after the capability-validation gate produces a supported product direction.

For contributors, treat:
- `docs/research/` as exploration and competitive/technical evidence;
- `docs/validation/` as experiment protocol and results;
- `research/benchmarks/` as reproducible evaluation infrastructure;
- `docs/product/` as hypotheses and scope contracts pending validation;
- `docs/hackathon/` as submission/readiness material.
