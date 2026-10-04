# Track A — Coding Agent Guide

## Mission

Prove that an authentic expert demonstration can become a **faithful, source-grounded, reviewable, bounded teaching input**.

The Track A proof is:

`authentic expert source → multimodal understanding → structured knowledge → evidence grounding → expert review → teaching/practice input`

Do not optimize for generic knowledge extraction. Optimize for fidelity and auditability.

## Before coding

Read:
1. `tracks/common/README.md`
2. `tracks/common/CONTRACT-USAGE.md`
3. `tracks/common/schemas/*.py`
4. `tracks/common/validator.py`
5. `tracks/common/tests/`
6. `docs/architecture/parallel-work-contract.md`
7. `docs/architecture/google-stack-integration.md`
8. `tracks/track-a/SUCCESS-CRITERIA.md`
9. `docs/product/mvp-contract.md` and `docs/product/novelty-boundary.md` as needed.

The final domain/skill is intentionally **not fixed yet**. Keep extraction and UI-independent logic domain-agnostic until M0 selects the bounded case.

## Authoritative outputs

Track A produces:
- `EvidenceRef`
- `KnowledgePackage`
- `RubricDefinition`
- `PracticeTask`

These are imported from `tracks.common.schemas`. Do not fork them.

Internal Gemini/model DTOs are acceptable:

`model response → normalization adapter → common contract → deterministic validation`

## What good Track A output looks like

A reviewer should be able to inspect a claim and answer:
- What exactly was observed?
- Where is it in the original source?
- Is this observation or inference?
- What is uncertain or missing?
- Did an expert review it?
- How did this become the bounded practice task?

Material claims need evidence. Missing evidence must remain missing.

## Domain-agnostic implementation rules

Do not hard-code:
- one profession;
- one physical tool;
- one camera setup;
- one video format;
- one evaluation domain;
- one vocabulary;
- one skill taxonomy.

Use configurable/adaptable extraction logic and small domain-specific fixtures.

## Gemini rules

Gemini may:
- inspect multimodal source material;
- extract candidate steps/cues/conditions/exceptions/failure modes;
- propose structured output;
- help locate timestamps;
- draft grounded teaching language.

Gemini must not be treated as the source of truth.

Before shipping model-backed behavior, retain:
- model/configuration;
- prompt/version;
- fixture/input;
- expected behavior;
- evaluation evidence.

CI/replay must not require a live model.

## Practice task generation

The task must be bounded, observable, and tied to:
- the `KnowledgePackage`;
- the `RubricDefinition`;
- observable learner criteria.

Do not turn source material into a generic course.

## Required negative tests

At minimum, prove rejection/handling of:
- invalid evidence intervals;
- unsupported/ungrounded claims;
- duplicate claim IDs;
- missing evidence;
- invalid contract relationships;
- accidental inference presented as observation.

## M0 gate

Do not claim M0 until the authentic selected case demonstrates:
- material fidelity;
- evidence grounding;
- explicit uncertainty;
- expert review;
- bounded teaching/practice output;
- deterministic replay without live Gemini.

## Integration handoff

Track B should be able to consume Track A outputs without importing Track A internals.

The handoff is:

`KnowledgePackage + EvidenceRef[] + RubricDefinition + PracticeTask`

Anything else is an implementation detail unless explicitly added to the shared seam.

## Stop conditions

Stop and narrow scope if:
- the source cannot support a claim;
- the extraction is too generic to distinguish the expert's technique;
- the evidence cannot be located;
- the selected skill is too broad;
- implementation requires platform infrastructure rather than improving the proof.

Do not solve uncertainty by adding architecture.
