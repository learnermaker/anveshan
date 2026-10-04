# Track A — Coding Agent Guide

## Mission

Prove that an appropriate source can become a **faithful, source-grounded, reviewable, bounded teaching input**.

The source may be a demonstration, desired target state/image, learner attempt, or combination. Do not invent a historical procedure from a final image.

The Track A proof depends on the selected transmission mode:

- **Forward:** `expert demonstration → multimodal understanding → structured knowledge → evidence grounding → expert review → teaching/practice input`
- **Goal-conditioned:** `desired target → observable target structure → explicitly inferred candidate procedure → bounded practice input`
- **Corrective:** `learner attempt → grounded divergence evidence → targeted teaching/practice input`

For the original expert-transfer validation wedge, the accountable source must be an authentic expert source. Goal-conditioned and corrective modes are supported product hypotheses and must preserve their different evidence boundaries.

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


## Current prototype alignment — 2026-10-04

The current frontend is a reference implementation of the adaptive transmission loop. Track A agents must remain independent of its React/component structure, but they should understand the semantics the UI now expects from validated data.

### Adaptive workspace composition

The prototype demonstrates that the interface changes with the capability archetype and evidence structure. Track A should expose enough validated, domain-agnostic information for a downstream adapter to determine characteristics such as:

- evidence modalities available;
- forward / goal-conditioned / corrective mode;
- observable state structure;
- temporal, spatial, diagnostic, rhythmic, or state-transition characteristics;
- uncertainty/unknown regions;
- candidate intervention-relevant findings.

Do not create a Workspace common contract merely to satisfy the UI. If needed, derive a UI/workspace view model downstream from KnowledgePackage, EvidenceRef[], RubricDefinition, and the selected transmission mode.

### Epistemic presentation

The prototype intentionally separates:

- **OBSERVED / SOURCE-DERIVED FACT** — supported by evidence;
- **INFERRED** — model interpretation or candidate procedure;
- **UNKNOWN / UNVERIFIED** — not established by the available source.

The current common VerificationState values are OBSERVED, INFERRED, and UNVERIFIED. A UI may render UNVERIFIED as UNKNOWN, but must not silently promote it to observed fact.

### Replay/live discipline

The prototype supports replay fixtures and a live Gemini path. Track A model outputs are always intermediate and untrusted until normalized and validated. Never label fixture-derived extraction as live Gemini output, authentic expert validation, or real-world product validation.

### Target-first Kolam guardrail

For a target image, extract visible target properties separately from inferred construction strategy. A final image does not prove original creator sequence, intent, cultural meaning, or hand motion. Preserve the inference boundary in the data handed downstream.

## Case data and model-run discipline

Before implementing a case, read:
- `tracks/common/CASE-DATA-CONVENTIONS.md`
- `tracks/common/MODEL-GATEWAY-CONVENTIONS.md`

Use `tracks/track-a/data/cases/<case_id>/manifest.yaml` as the case entry point. Keep source artifacts, expected outputs, and metadata organized under that case; keep generic engineering fixtures under `fixtures/`.

Every materially outcome-affecting model run must retain model/configuration, prompt ID/version, input fixture/artifact, runtime class, run ID, and expected behavior. Provider output remains quarantined until normalization and deterministic validation.

Use the shared failure taxonomy for structured failures. Escalate to `HUMAN_REVIEW_REQUIRED` instead of guessing when evidence is materially insufficient/conflicting or expert review is required.

Do not silently overwrite materially changed source, extraction, rubric, prompt/model configuration, or normalized knowledge. Version the artifact so prior replay/review remains reconstructable.
