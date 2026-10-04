# Track A — Coding Agent Guide

## Mission

Prove that an appropriate source can become a **faithful, source-grounded, reviewable, bounded teaching input**.

The source may be a demonstration, desired target state/image, learner attempt, or combination. Do not invent a historical procedure from a final image.

The Track A proof is:

`authentic expert source → multimodal understanding → structured knowledge → evidence grounding → expert review → teaching/practice input`

Do not optimize for generic knowledge extraction. Optimize for fidelity and auditability.

## Before coding

Read:
1. `tracks/common/README.md`
2. `tracks/common/CONTRACT-USAGE.md`
3. `tracks/common/schemas/`
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


## Source-type flexibility

The selected capability does not have to begin with an expert demonstration video.

Track A must support three source patterns:

1. **Forward:** demonstration → structured knowledge;
2. **Goal-conditioned:** desired state/image → observable target structure + explicitly inferred candidate construction strategy;
3. **Corrective:** learner attempt → evidence of divergence → targeted teaching input.

For goal-conditioned cases such as Kolam, do not claim to recover an original procedure from a final image unless a source demonstration establishes it. Preserve target facts as OBSERVED and candidate construction steps as INFERRED.

The handoff remains the frozen common contracts. Source modality is not a reason to create a parallel contract.

See:
- docs/research/source-strategy-and-transmission-modes-2026-10-04.md
- docs/research/multimodal-capability-case-portfolio.md

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


## Parallel UI coexistence
UI work is happening independently. Track A must remain UI-agnostic. Do not couple extraction, grounding, review, or practice-task generation to React/component state, UI JSON, route structure, or presentation copy. If the UI needs a different shape, expose an adapter/view-model downstream of validated contracts.
Never change a common contract because a screen is inconvenient to render.

## Required implementation sequence
1. Contract map — identify common outputs and relationships.
2. Fixture first — define expected observations, evidence, uncertainty, and failure cases.
3. Deterministic core — implement normalization, provenance checks, relationships, and replay without a live model.
4. Model adapter — add Gemini/model calls only behind a replaceable DTO/adapter boundary.
5. Review state — make expert review explicit; never infer approval from model confidence.
6. Bounded teaching — generate only the lesson/practice surface needed for the selected case.
7. Negative tests — prove unsupported claims, bad evidence, invalid relationships, and uncertainty are handled safely.
8. Replay gate — run the full Track A replay without live Gemini.

## Evidence ledger requirement
For every material extracted claim, preserve: claim → evidence → locator → observation/inference state → uncertainty → review state.
If any link is unavailable, preserve the gap. Do not fabricate timestamps, confidence, source excerpts, expert approval, or domain facts.

## Model-output quarantine
Gemini/provider DTOs are untrusted intermediate outputs. Validate and normalize them before they cross into tracks.common. Do not pass raw model JSON directly to Track B or the UI as authoritative data.

## Domain selection guardrail
Until M0 explicitly selects the bounded case, reusable code must work from interfaces/configuration/fixtures rather than named professions, tools, physical techniques, or fixed vocabulary. Domain-specific prompts or fixtures are acceptable; domain-specific assumptions in reusable infrastructure are not.

## Handoff packet
Before integration, provide source identity and consent/review state; normalized EvidenceRef objects; KnowledgePackage; RubricDefinition; PracticeTask; expected uncertainty/unsupported claims; replay command and expected result; and model/prompt metadata when a model was used.
Track B must be able to consume this packet without importing Track A source modules.
