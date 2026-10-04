# Anveshan Product Thesis

**Review checkpoint:** 2026-10-03  
**Status:** Current competition/MVP thesis; validation pending. The broader company/product vision is defined in `docs/product/product-vision.md`. This document must not be interpreted as the complete Anveshan vision.

## 1. Executive Thesis

**Anveshan helps one person transmit a real piece of expertise to another person.**

It starts from an authentic expert demonstration, uses multimodal AI to structure observable knowledge, preserves source evidence, turns the result into a concise apprenticeship, observes the learner's attempt, provides evidence-linked feedback, measures improvement, and records transmission lineage.

### Core loop

**DEMONSTRATE → UNDERSTAND → GROUND → TEACH → PRACTICE → VERIFY → TRANSMIT → EVOLVE**

## 2. Problem

Some expertise is difficult to transfer through conventional documents because it includes timing, sensory/visual cues, conditional rules, exceptions, decision thresholds, sequence, tool/material interaction, environmental context and failure recognition.

A transcript can preserve words while losing physical context. A video can preserve action while being difficult to search or teach from. A generic AI tutor can personalize instruction without preserving a particular expert's practice. A static archive can preserve information without producing a learner.

Anveshan connects these layers.

## 3. Actionable Problem

> **When a person has valuable expertise but the expertise is difficult to explain, search, teach or verify, the next learner may not receive the parts that matter most.**

The first domain is intentionally not fixed.

## 4. Product Insight

Human expertise has a transmission lifecycle:

**source → representation → teaching → attempt → feedback → improvement → lineage**

Anveshan makes that lifecycle explicit.

## 4A. Source-flexible transmission hypothesis

The MVP thesis should not assume that every transmission begins with an expert demonstration video.

Three source/interaction directions are now documented as a product hypothesis:

1. **Forward:** demonstration → capability;
2. **Goal-conditioned:** desired state/image → plausible capability path;
3. **Corrective:** learner attempt → divergence → intervention → retry.

The second and third forms extend the expression of the core thesis; they do not replace the MVP's requirement for measurable transmission.

**Status:** unvalidated. See `docs/research/source-strategy-and-transmission-modes-2026-10-04.md`.

For target-first cases, visible target properties must remain distinct from inferred candidate procedures. An image alone must not be represented as evidence of an original creator's exact construction sequence or intent.

## 5. What It Does

Anveshan aims to make observable expertise capturable, structured, searchable, source-grounded, explainable, teachable, practiceable, verifiable, permission-aware, traceable and transmissible.

It distinguishes:

1. source statement;
2. demonstrated evidence;
3. AI interpretation;
4. community interpretation;
5. external evidence;
6. unknown.

## 6. What It Does Not Claim

Anveshan does not claim to solve tacit knowledge generally.

It makes **observable parts of context-sensitive expertise explicit and source-grounded**.

It does not claim that one expert is universally correct, that one video can always establish competency, or that AI can infer invisible reasoning with certainty.

## 7. Product Unit: Transmission

A Transmission connects:

- expert;
- knowledge/practice;
- source evidence;
- lesson;
- learner;
- practice task;
- learner attempt;
- feedback;
- outcome;
- adaptation;
- lineage.

## 8. Differentiation Boundary

Current research shows that AI interviews, tacit-knowledge extraction, knowledge graphs, multimodal RAG, AI tutoring, apprenticeship assistance, learner video assessment and expert cognition modeling are all active areas.

The current differentiation hypothesis is:

> **authentic expert source → grounded representation → adaptive teaching → learner attempt → evidence-linked verification → measurable improvement → lineage**

This is a hypothesis, not a market-wide claim of uniqueness.

## 9. MVP

The first proof should use one real expert, one bounded skill, one authentic demonstration, one learner, one practice task, one baseline attempt, one teaching interaction, one feedback loop, one retry, one measurable improvement, one transmission record and one lineage event.

The exact skill must be selected from authentic access, observability, safety and judge comprehension.

## 10. Candidate Domains

- traditional craft;
- culinary technique;
- agriculture;
- local ecological practice;
- music/dance;
- skilled trades;
- practical professional expertise.

The domain is a proof context, not the product definition.

## 11. Flagship Metric

Candidate:

**Transmission Gain = post-transmission learner performance − baseline learner performance**

This is not validated. It must use a skill-specific rubric and should be compared with independent expert assessment.

## 12. Technical Hypothesis

Three logical responsibilities:

### Knowledge Agent
Multimodal extraction, structuring, retrieval.

### Evidence Agent
Grounding, citation, contradiction, uncertainty, evidence sufficiency.

### Transmission Agent
Teaching, practice, attempt analysis, feedback, transmission record.

Every AI component must have a measurable job.

## 13. Google Technical Fit

Current research supports Gemini 3.5 Transcribe, Gemini video understanding, Gemini Embedding 2, ADK, Cloud Run and agent evaluation.

Important current constraints must influence implementation. For example, current transcription documentation records feature incompatibilities between timestamps/diarization and custom vocabulary, and current video processing has different static/agentic modes. These are engineering choices, not marketing details.

## 14. Governance

Human knowledge must not become unreviewed machine-generated authority.

For culturally sensitive or community knowledge, consent, contextual governance, access control, review and community authority must be real rather than merely described.

## 15. North Star

> **Can Anveshan help one human successfully pass a piece of real-world expertise to another human, while preserving evidence and lineage?**

If not, additional agents, dashboards or archive features do not solve the core problem.
