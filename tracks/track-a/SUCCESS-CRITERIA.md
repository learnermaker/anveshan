# Track A — Definition of Done & Success Criteria

**Status:** DECIDED execution contract  
**Purpose:** Define exactly what “Track A is correctly done” means for Anveshan’s current MVP and M0→M1 path.

## 1. Mission

Track A — **Expert Intelligence & Grounding** owns the expert-side half of the transmission proof.

The objective is not to build a generic knowledge platform. The objective is to prove that an appropriate source can be transformed into a **faithful, source-grounded, reviewable teaching input** that another person can practice.

Track A must support the three currently documented source/interaction modes:

1. **Forward:** authentic expert demonstration → grounded knowledge → bounded teaching/practice input;
2. **Goal-conditioned:** desired target state/image → observable target structure + explicitly inferred candidate construction strategy → bounded practice input;
3. **Corrective:** learner attempt → evidence of divergence → targeted teaching/practice input.

For the original expert-transfer validation wedge, the accountable source remains a real expert. Goal-conditioned and corrective modes extend the transmission hypothesis but are not automatically validated merely because the engineering flow works.

Track A is successful only when it preserves the appropriate evidence chain for the selected mode.

The implementation must support Anveshan’s original long-term direction:

**CAPTURE → UNDERSTAND → GROUND → TRANSMIT → PRACTICE → VERIFY → EVOLVE**

For this track, the concrete MVP proof surface is:

**DEMONSTRATE → UNDERSTAND → GROUND → TEACH**

Track A is therefore a provenance-and-fidelity system first, and an AI-generation system second.

---

## 2. Non-negotiable boundaries

Track A **must** own:

- source/media representation and ingestion;
- multimodal source understanding;
- extraction of steps, sequence, cues, conditions, exceptions, and failure modes;
- claim-to-source evidence linkage;
- explicit observed vs inferred distinction;
- uncertainty handling;
- expert-review representation;
- grounded lesson/teaching material generation;
- bounded practice-task generation;
- deterministic contract/provenance validation;
- replayable evidence without requiring live model calls.

Track A **must not** own:

- learner attempt scoring;
- final learner feedback/retry orchestration;
- transmission-gain calculation;
- generalized learner analytics;
- production infrastructure merely for architectural completeness;
- an unconstrained knowledge graph/platform;
- domain selection that has not been authorized by M0;
- silent invention of facts not supported by the source.

The frozen cross-track seam is the shared contract boundary in `tracks/common/`.

---

## 3. Required outputs

For one bounded use case, Track A must be capable of producing valid:

1. `EvidenceRef`
2. `KnowledgePackage`
3. `RubricDefinition`
4. `PracticeTask`

The authoritative contracts live in:

`tracks/common/schemas/`

The Track A implementation may use additional internal DTOs, helper structures, prompt schemas, or adapters, but these must normalize into the shared contracts rather than replace them.

---

## 4. Source fidelity criteria

### 4.1 Source-mode fidelity

**Forward validation:**
- source must be a real accountable expert demonstration;
- permission/consent must be documented;
- source identity must be stable and auditable;
- material claims must be reviewable by the expert.

**Goal-conditioned validation:**
- target asset identity must be stable and authorized;
- visible target properties must be distinguished from inferred construction strategy;
- inferred steps must remain explicitly inferred;
- no original creator process/intent may be asserted without independent evidence.

**Corrective validation:**
- learner attempt evidence must be observable;
- the divergence claim must be tied to learner evidence and rubric criteria;
- the resulting intervention must be grounded in the identified divergence.

Synthetic/replay fixtures are acceptable for engineering replay, but they are **not product validation**.

### 4.2 Structured extraction

Track A must represent, where present in the source:

- action/step;
- correct ordering;
- preconditions;
- context/conditions;
- observable cues;
- exceptions;
- failure modes;
- important safety or tool/material constraints.

Missing information must remain missing. The system must not fill gaps merely because a model can plausibly infer them.

### 4.3 Evidence grounding

Every material claim must have one or more `EvidenceRef` entries that identify the supporting source location.

Evidence must preserve, where applicable:

- source ID;
- modality;
- time interval or other locator;
- observable excerpt/description;
- verification state;
- uncertainty/confidence.

A claim without adequate evidence is not considered grounded.

### 4.4 Observed vs inferred

The representation must distinguish:

- directly observed/source-backed content;
- model-derived interpretation;
- unresolved or unverified information.

The system must never silently convert inference into source truth.

### 4.5 Temporal correctness

For timestamped media:

- intervals must be non-negative;
- `end_sec >= start_sec`;
- timestamps must point to the relevant source segment rather than merely the approximate location of the overall demonstration;
- uncertain localization must be explicitly represented.

---

## 5. Expert-review criteria

Before a real claim is treated as validated product knowledge:

- the source contribution has appropriate consent;
- the extracted representation can be inspected by the expert;
- material inaccuracies can be corrected without rewriting the original source;
- review state is explicit;
- rejected/revised content remains distinguishable from the original evidence.

The minimum viable review loop is:

**extract → inspect → correct/approve → preserve provenance**

A model's confidence score is not a substitute for expert review.

---

## 6. Rubric criteria

Track A is responsible for the bounded evaluation input, but Track B owns learner evaluation.

The rubric must therefore be:

- domain-specific once M0 selects the use case;
- criterion-based;
- observable;
- sufficiently granular to diagnose improvement;
- explicit about criterion weighting/max points;
- explicit about passing semantics;
- stable enough that baseline and retry can be compared using the same rubric.

A criterion should be something an evaluator could actually observe in the learner evidence.

Bad criterion:

> “Learner understands the technique.”

Good criterion:

> “Learner performs the demonstrated positioning step within the accepted physical range.”

The rubric is the source of truth for scoring. Gemini may assist with observation/comparison, but it must not invent the scoring framework.

---

## 7. Teaching/practice criteria

The Track A output must enable a bounded learner task.

A valid `PracticeTask` must:

- reference the correct `KnowledgePackage`;
- reference the correct `RubricDefinition`;
- tell the learner what to do;
- specify relevant constraints;
- target the observable criteria needed to demonstrate the skill;
- avoid introducing unsupported instructions that were not justified by the source or an explicitly authorized teaching adaptation.

The teaching material should preserve the chain:

**expert evidence → structured explanation → practice instruction**

not:

**generic model knowledge → plausible lesson**.

---

## 8. Google stack usage criteria

The current Google/Gemini integration guide is a **proposed implementation playbook**, not an authorization to build every listed service.

Use the Google stack only where it improves the actual proof.

The expected separation is:

**Gemini model call → extraction DTO → normalization → Anveshan shared contract → validator → replay/integration**

Model-specific prompts or response schemas should remain focused on the task at hand.

For multimodal understanding, the Google guide should be consulted for:

- Gemini video understanding;
- timestamp-grounded inspection;
- structured output;
- Google `google-genai` SDK usage;
- File API media handling;
- replay/mock patterns.

Before shipping a model-backed change, record:

- model;
- model/configuration;
- prompt/version;
- input fixture;
- expected behavior;
- evaluation evidence.

Do not make a model choice a product decision merely because the model is available.

---

## 9. Replay and test criteria

Track A is **not done** when the code merely runs once against a live model.

It is done when a deterministic replay can demonstrate:

`source fixture → knowledge package → evidence links → rubric → practice task`

At minimum, the replay suite must prove:

- valid contracts deserialize;
- invalid evidence intervals fail;
- ungrounded/missing evidence is represented as such;
- duplicate identifiers are rejected;
- contract relationships remain intact;
- output remains distinguishable as observed/inferred/uncertain;
- Google-model invocation can be bypassed in CI;
- the same fixture yields repeatable validation results.

The canonical shared replay case lives under `tracks/common/tests/fixtures/transmission_case_001/`.

Track A may create richer track-local fixtures, but it should remain compatible with the common case.

---

## 10. M0 success criteria

Track A has passed M0 capability validation only when the selected authentic case demonstrates:

### Fidelity
The expert agrees that high-value extracted steps/cues/conditions are materially faithful and that important invented claims are absent.

### Grounding
Material answers/claims can be traced to correct evidence, including relevant timestamps where temporal grounding is required.

### Uncertainty
Ambiguous or unsupported information is explicitly marked rather than guessed.

### Reviewability
The expert can inspect and correct the derived representation.

### Bounded teaching
A learner-facing lesson/practice input can be generated from the grounded package without becoming generic tutoring.

### Replayability
The same core behavior can be reproduced from stored fixtures without paid/live model calls.

A fixture passing validation is evidence of engineering correctness, **not** evidence that the product hypothesis is validated.

---

## 11. M1 integration readiness

Track A is ready to hand off to Track B when all of the following are true:

- the exact bounded skill has been selected;
- the authentic expert source has been authorized;
- `KnowledgePackage` is source-grounded;
- `EvidenceRef` coverage is complete for material claims;
- `RubricDefinition` contains observable criteria;
- `PracticeTask` references package and rubric correctly;
- expert review status is explicit;
- uncertainty is preserved;
- Track A replay passes;
- no production runtime dependency on Track B exists.

The handoff must be possible using frozen contracts.

Track B must not need Track A internals to begin its own implementation or replay validation.

---

## 12. Kill criteria

Track A should stop or trigger reconsideration if:

- authentic expert access fails;
- the source is too ambiguous to ground;
- extraction quality is materially poor;
- the system invents meaningful domain facts;
- evidence localization is unreliable;
- expert review reveals the representation is not faithful;
- teaching output becomes generic rather than source-derived;
- the capability provides no defensible advantage over direct summarization/tutoring;
- implementation complexity grows substantially without improving the validation question.

The correct response to failure is evidence and scope reduction, not architectural expansion.

---

## 13. “Done” statement

Track A is correctly done when an independent reviewer can take the selected authentic expert demonstration and answer **yes** to all of these:

- Can I see exactly what source the knowledge came from?
- Can I distinguish what was observed from what the model inferred?
- Can I locate the evidence supporting each material claim?
- Can I see where uncertainty remains?
- Can the expert review and correct the derived representation?
- Does the representation preserve steps, cues, conditions, exceptions, and failure modes that matter?
- Can a bounded learner exercise be generated from this grounded knowledge?
- Is the rubric explicit enough for Track B to evaluate observable behavior?
- Can the whole Track A proof be replayed without a live model?
- Can Track B consume the outputs without depending on Track A implementation details?

That is the minimum bar for Track A to claim **READY FOR INTEGRATION**, not merely “code complete.”


## 20. Current prototype / GenUI integration context

The current prototype demonstrates an adaptive workspace compiler. Track A does not implement the UI, but its outputs should make the following downstream decisions possible without adding a common contract:

    source mode + evidence modalities + capability characteristics + uncertainty
            ↓
    downstream workspace composition adapter
            ↓
    case-specific practice workspace

Representative workspaces include:
- Kolam → Spatial Practice Canvas;
- Micrometer → Forensic Transmission Instrument;
- Bicycle repair → Diagnostic Workspace;
- Tabla → Rhythm Practice Instrument;
- Weaving → State Transition Workspace;
- Origami → Spatial Sequence Workspace;
- Knot → First-Divergence Workspace.

These are capability archetypes, not seven separate product architectures.

Track A must never fabricate evidence, timestamps, expert approval, calibration, certification, or live-model status to make a workspace appear complete. Replay/synthetic data must remain explicitly labeled downstream.

For target-first cases, the UI may render UNVERIFIED as UNKNOWN, but the underlying evidence semantics must remain unchanged.
