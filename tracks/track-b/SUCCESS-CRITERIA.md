# Track B — Definition of Done & Success Criteria

**Status:** DECIDED execution contract  
**Purpose:** Define exactly what “Track B is correctly done” means for Anveshan’s current MVP and the proof of successful knowledge transmission.

## 1. Mission

Track B — **Practice, Evaluation & Transmission** owns the learner-side half of the transmission proof.

The objective is not to build a generic learning-management system or analytics product.

The objective is to prove that a learner can:

**consume a bounded expert-grounded practice input → perform → submit observable evidence → be evaluated against an explicit rubric → receive evidence-grounded feedback → retry → improve measurably → produce a transmission record**

This is the concrete realization of the product wedge:

> Anveshan helps an expert transmit a bounded piece of real-world expertise to another person, grounded in authentic evidence, with observable practice and verification of whether the knowledge transferred.

Track B therefore exists to make the word **“transmitted”** measurable rather than rhetorical.

---

## 2. Non-negotiable boundaries

Track B **must** own:

- practice-task consumption;
- learner baseline capture;
- learner attempt representation;
- criterion-level evaluation;
- evidence-linked observations;
- uncertainty handling;
- feedback generation/representation;
- explicit retry;
- baseline-to-retry measurement;
- deterministic transmission-gain calculation;
- transmission record creation;
- lineage output;
- replayable evaluation without live model dependence.

Track B **must not** own:

- expert-source ingestion;
- knowledge extraction;
- claim grounding;
- expert authoring;
- final source interpretation;
- a generalized learner analytics platform;
- a single unconstrained model score as the authoritative outcome;
- unbounded retry loops for the MVP;
- production infrastructure before the proof requires it.

Track B consumes the frozen contracts from `tracks/common/`.

---

## 3. Required inputs

For one bounded proof case, Track B must accept:

- `KnowledgePackage`
- `EvidenceRef`
- `RubricDefinition`
- `PracticeTask`

The implementation may consume internal DTOs or adapters, but the authoritative handoff remains the shared contract seam.

The selected rubric must be the **same rubric** used for baseline and retry so measured change remains attributable to a common measurement frame.

---

## 4. Learner attempt criteria

### 4.1 Baseline

The baseline is the learner's pre-training attempt.

It must be represented explicitly as:

- `attempt_type = BASELINE`;
- `attempt_number = 1`;
- observable evidence attached to the attempt.

Baseline is required because without it Anveshan cannot distinguish:

- initial ability;
- teaching;
- post-teaching improvement.

### 4.2 Retry

The retry is the learner's post-feedback attempt.

It must be represented explicitly as:

- `attempt_type = RETRY`;
- `attempt_number >= 2`;
- evidence attached to the attempt;
- same learner;
- same bounded task/rubric context.

For the MVP, the primary proof is:

**baseline → teaching → feedback → one retry**

The contract can represent additional attempts, but the MVP should not drift into an adaptive-learning platform.

---

## 5. Observable evidence criteria

A learner attempt must contain evidence that an evaluator can inspect.

Depending on the chosen skill, this can be:

- video;
- audio;
- image;
- text;
- sensor/measurement data.

For media evidence:

- preserve source identity;
- preserve relevant timestamps/locators where applicable;
- retain uncertainty where the evidence is insufficient;
- do not manufacture observations from absent evidence.

An evaluation that cannot point to observable learner evidence is incomplete.

---

## 6. Evaluation criteria

### 6.1 Rubric-first

Every evaluation must use the explicit `RubricDefinition`.

Do not start with:

> “Give this learner a score from 0–100.”

Start with:

**Which observable criteria does the learner satisfy, partially satisfy, fail, or leave uncertain?**

Each `CriterionResult` should provide:

- criterion identifier;
- status;
- score;
- observed finding;
- deviation analysis when useful;
- learner evidence reference when available.

### 6.2 Criterion integrity

The validator must ensure:

- criterion IDs exist in the rubric;
- required criteria are represented;
- criterion scores do not exceed criterion maximum points;
- total score equals the sum of criterion scores;
- pass/fail semantics remain consistent with the rubric;
- uncertain criteria remain explicit.

### 6.3 Model role

Gemini may assist with:

- locating relevant evidence;
- observing learner behavior;
- comparing learner behavior to the reference;
- identifying deviations;
- drafting feedback.

Gemini must **not** silently redefine:

- the rubric;
- the scoring scale;
- the authoritative transmission metric.

Where a model is uncertain, the result should become `UNCERTAIN` or require more evidence/human review.

---

## 7. Feedback criteria

Feedback exists to enable the retry, not merely to generate encouraging text.

Each meaningful feedback item should answer:

1. What did the learner actually do?
2. What differed from the expected/reference behavior?
3. What evidence supports that observation?
4. What specific change should the learner make on the next attempt?

Feedback should be linked to:

- an evaluation;
- an attempt;
- criterion IDs;
- expert/reference evidence when useful;
- learner evidence where available.

Generic advice such as “practice more” is not sufficient.

The feedback loop should preserve the causal chain:

**learner evidence → criterion finding → evidence → corrective action → retry**

---

## 8. Retry criteria

The MVP retry must:

- be explicitly linked to the prior task;
- use the same rubric;
- represent the same learner;
- occur after feedback;
- create a new observable evidence record;
- permit criterion-by-criterion comparison.

The implementation should preserve exactly what changed between the baseline and retry.

For example:

| Criterion | Baseline | Retry | Interpretation |
|---|---:|---:|---|
| C1 | 0.5 | 1.0 | improved |
| C2 | 2.0 | 2.0 | unchanged |
| C3 | uncertain | 1.0 | now observable/satisfied |

Do not report only the aggregate score when criterion-level evidence exists.

---

## 9. Transmission-gain criteria

The authoritative metric is deterministic:

**Transmission Gain = Retry Score − Baseline Score**

The value must be reproducible from recorded evaluation inputs.

The shared contract already enforces:

`transmission_gain == retry_score - baseline_score`

No model-generated headline number may override this.

The system must retain the underlying scores and criterion results so a reviewer can reconstruct the metric.

### 9.1 Do not manufacture success

A positive transmission gain is evidence of improvement, but it is not by itself proof that:

- the learner mastered the skill;
- the effect generalizes beyond the single attempt;
- the system caused all observed improvement.

The product claim should remain proportional to the evidence.

### 9.2 Distribution matters

Where multiple participants become available, preserve the score distribution rather than only reporting a single average.

For the first MVP proof, one learner is sufficient to validate the end-to-end mechanism; broader causal claims require broader evidence.

---

## 10. TransmissionRecord criteria

A valid `TransmissionRecord` must preserve:

- transmission ID;
- skill ID;
- knowledge package ID;
- rubric ID;
- expert identity/reference;
- learner identity/reference;
- baseline attempt;
- retry attempt;
- baseline score;
- retry score;
- deterministic transmission gain;
- improved criteria;
- lineage metadata.

The record should allow an independent reviewer to reconstruct:

**who taught what to whom, from which source, under which rubric, with what observed change.**

The record is the proof artifact for the MVP, not merely an event log.

---

## 11. Lineage criteria

Anveshan's long-term differentiation depends on knowledge remaining traceable as it moves between people.

For the MVP, lineage should preserve enough information to answer:

- who was the source expert?
- what knowledge package was transmitted?
- what learner practiced it?
- what evidence did the learner provide?
- what feedback was delivered?
- what retry occurred?
- what changed?
- when was the transmission recorded?
- was there an adaptation or review?

Do not require a full lineage graph database for the MVP.

A compact, auditable lineage record is sufficient.

---

## 12. Google stack usage criteria

The current Google/Gemini integration guide is a **proposed implementation playbook**.

Use it to guide:

- Gemini model selection;
- `google-genai` SDK usage;
- multimodal learner evidence analysis;
- structured model outputs;
- timestamp-grounded comparison;
- replay/mock patterns.

The architectural boundary must remain:

**Gemini observation/comparison → normalized criterion results → deterministic validation/aggregation → transmission measurement**

The model must never become the hidden owner of the scoring system.

Before shipping a model-backed behavior change, record:

- model;
- configuration;
- prompt/version;
- rubric;
- fixture;
- expected behavior;
- evaluation evidence.

Live model calls are additive to replay tests, not a replacement for them.

---

## 13. Replay and test criteria

Track B is not done when a single happy-path demo works.

It is done when deterministic replay proves:

**PracticeTask → baseline attempt → evaluation → feedback → retry attempt → retry evaluation → transmission record**

At minimum, tests must demonstrate:

- baseline/retry typing is enforced;
- invalid attempt numbering is rejected;
- evaluation total is deterministic;
- unknown rubric criteria are rejected;
- score-over-weight is rejected;
- required criteria cannot silently disappear;
- feedback cannot target unevaluated criteria;
- transmission IDs and learner identity are aligned;
- baseline/retry scores match recorded evaluations;
- transmission gain is deterministic;
- improved criteria are evidence-backed;
- complete replay bundle passes;
- malformed/inconsistent bundles fail loudly.

The canonical shared replay fixture is:

`tracks/common/tests/fixtures/transmission_case_001/`

Track B should build its local proof against that frozen seam before integration.

---

## 14. M0 success criteria

Track B has passed M0 capability validation when the system can demonstrate:

### Practice
A learner can receive and perform a bounded task derived from expert-grounded knowledge.

### Observation
The learner's behavior can be represented as observable evidence.

### Evaluation
The evaluation is criterion-level, rubric-constrained, evidence-linked, and explicit about uncertainty.

### Feedback
The learner receives specific, actionable correction tied to what was actually observed.

### Retry
The learner performs one meaningful retry after feedback.

### Improvement
The retry produces a measurable change under the same rubric.

### Transmission proof
The system creates a valid `TransmissionRecord` whose gain can be recomputed independently.

### Replayability
The complete loop can run against fixtures without live model calls.

A successful replay proves engineering behavior. It does **not** establish real-world learner improvement until the authentic validation case is run.

---

## 15. M1 integration readiness

Track B is ready to integrate with Track A when:

- it can consume frozen Track A-compatible contracts;
- baseline and retry evidence are represented correctly;
- rubric validation passes;
- criterion-level evaluation works;
- feedback is traceable;
- one retry is supported;
- transmission gain is deterministic;
- lineage is emitted;
- common replay passes;
- no Track A implementation internals are required.

Integration then replaces the frozen fixtures with the selected authentic expert/learner evidence.

---

## 16. Failure and uncertainty criteria

When evidence is insufficient:

- do not guess;
- mark the criterion uncertain or insufficient;
- identify what evidence is missing;
- request another observation or human review.

When evidence conflicts:

- preserve the conflicting observations;
- do not silently merge them;
- record the conflict where the implementation supports it.

When feedback cannot be grounded:

- do not present the feedback as fact.

When the evaluator cannot determine a criterion reliably:

- uncertainty is a valid result;
- uncertainty must not be turned into false precision.

---

## 17. Competitive and product-fit criteria

Track B must support the product thesis, not merely demonstrate a competent evaluator.

An independent reviewer should be able to see the difference between:

- a generic tutor that gives advice;
- a static archive that stores knowledge;
- and Anveshan, where knowledge comes from an authentic expert source, is grounded in evidence, is practiced by another person, and results in an observable transmission event.

The core proof is:

**source-grounded expertise → learner practice → verification → measurable change → lineage**

If the resulting experience is indistinguishable from ordinary tutoring, the track has not demonstrated the intended product wedge.

---

## 18. Kill criteria

Track B should stop or trigger reconsideration if:

- learner evidence cannot be observed reliably;
- rubric criteria are too vague to score;
- evaluation changes unpredictably between identical replay inputs;
- model feedback is generic or misleading;
- criterion-level results cannot be reconstructed;
- baseline/retry comparison is invalid;
- gain cannot be recomputed deterministically;
- positive changes are too small or inconsistent to support the transmission hypothesis;
- the workflow requires broad infrastructure that does not improve the core proof;
- the experience is functionally indistinguishable from existing tutoring/evaluation tools.

The correct response is to narrow the skill, improve evidence quality, or revise the hypothesis—not to add architecture.

---

## 19. “Done” statement

Track B is correctly done when an independent reviewer can take the selected bounded practice case and answer **yes** to all of these:

- Did the learner start with an explicit baseline?
- Was the task derived from expert-grounded knowledge?
- Is the rubric explicit and observable?
- Can every important evaluation claim be traced to learner evidence?
- Is uncertainty preserved instead of guessed away?
- Is the feedback tied to concrete criterion-level observations?
- Did the learner perform a real retry?
- Can I see what changed by criterion?
- Can transmission gain be independently recomputed?
- Does the TransmissionRecord preserve the source/learner/event lineage?
- Can the entire learner loop replay without a live model?
- Can Track B operate independently of Track A implementation internals?
- Does the result demonstrate knowledge transmission rather than merely tutoring?

That is the minimum bar for Track B to claim **READY FOR INTEGRATION**, not merely “tests pass.”


## 20. Current prototype / adaptive transmission context

The current prototype makes the evaluation loop visible through capability-specific workspaces. Track B does not own the UI, but its validated outputs must remain sufficient for a downstream adapter to compose those views.

### Capability-specific evaluation views

| Capability | Workspace | Evaluation emphasis |
|---|---|---|
| Kolam | Spatial Practice Canvas | target geometry, topology, symmetry, trajectory |
| Micrometer | Forensic Transmission Instrument | synchronized visual/audio/numeric evidence |
| Bicycle repair | Diagnostic Workspace | state → diagnosis → corrective sequence |
| Tabla | Rhythm Practice Instrument | onset/timing/acoustic alignment |
| Weaving | State Transition Workspace | discrete material-state transitions |
| Origami | Spatial Sequence Workspace | ordered fold/state transformations |
| Knot | First-Divergence Workspace | topology, first divergence, load behavior |

These are capability archetypes, not separate evaluation engines. Domain-specific observation logic belongs in explicit adapters/fixtures; common evaluation remains criterion-first.

### First-divergence inspector

The downstream UI may expose a first-divergence inspector. Track B should preserve enough validated information to reconstruct:

- criterion ID and rubric description;
- learner evidence locator;
- observed finding;
- model-assisted interpretation when present;
- deterministic consequence/criterion status;
- uncertainty or insufficient evidence;
- feedback/corrective action.

Do not store presentation copy as the authoritative finding.

### Adaptive micro-practice

If a criterion is the first meaningful divergence, a bounded retry may focus on that criterion. The retry remains a normal PracticeTask/LearnerAttempt/Evaluation flow; do not create a UI-specific retry contract.

### Replay honesty

The current prototype deliberately distinguishes replay fixtures from live Gemini. Track B must preserve that distinction in test metadata and handoff documentation. A deterministic replay may prove scoring/retry mechanics, but it does not prove that a real learner acquired a real-world skill.

### Goal-conditioned evaluation

For target-first cases such as Kolam, the rubric should evaluate observable target properties. If the system proposes a candidate construction path, that path is an inference and must not become hidden ground truth unless independently validated.

### Demo result semantics

A result surface may report:

baseline → retry → deterministic gain → criteria improved → lineage

For replay, describe this as a replay/configured-rubric result. Do not use the result to imply certification, mastery, or verified real-world transfer.

## M0 interpretation — measured improvement versus transmission claim

Track B engineering replay proves the practice/evaluation/retry machinery is executable and deterministic. A bounded capability case can prove that the evaluator and intervention mechanism work. **Product validation of the original transmission wedge additionally requires an authentic accountable expert/source path connected to the learner event.**

A positive `retry_score - baseline_score` is an observed improvement within the configured rubric frame. It must not be described as causal transfer, mastery, certification, or generalization on its own.

## Intervention-to-retry traceability

When feedback targets a specific failed or uncertain criterion, the retry evaluation must retain that criterion so the system can determine whether the targeted deficiency changed. This is a core proof of the adaptive transmission mechanism, not a UI concern.

## Adaptive retry comparability

A narrowed micro-practice is allowed, but the baseline and retry must remain interpretable under the same rubric. Record the scope change; do not use an easier retry or altered scoring semantics to manufacture gain.

## Observability change versus skill improvement

Treat `UNCERTAIN → SATISFIED` or similar evidence-quality transitions cautiously. Improved observability alone is not sufficient to label the criterion as skill improvement. Preserve the evidence state and distinguish observability change from substantive performance change where the data permits.

## Model-independent success

Track B success is defined by evidence-linked criterion evaluation, deterministic scoring/gain, and reproducible lineage—not by Gemini-specific behavior. Provider/model choices are implementation details behind the bounded gateway.
