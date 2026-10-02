# Validation Plan

## Objective

Prove the core thesis before expanding the feature set:

> Can Anveshan help one human successfully pass a piece of real-world expertise to another human while preserving evidence and lineage?

## Experiment 1 — Multimodal Knowledge Extraction

### Hypothesis

A real expert demonstration contains useful procedural, conditional, sensory, contextual, and exception knowledge that multimodal AI can extract.

### Input

- authentic expert video
- expert audio
- contextual metadata
- optional artifact/document images.

### Test

Ask the system to identify:

- steps
- sequence
- tools
- materials
- conditions
- exceptions
- sensory cues
- timing
- failure modes
- rationale.

### Human evaluation

Expert marks each extracted item:

- correct
- incomplete
- incorrect
- invented
- context missing.

### Success signal

The majority of high-value extracted knowledge is accepted by the expert with limited correction.

### Kill signal

The representation consistently mischaracterizes the practice.

## Experiment 2 — Evidence Grounding

### Hypothesis

Anveshan can answer difficult questions using exact source evidence.

### Test

Create 10 questions designed to expose hallucination.

Questions should include:

- "Why?"
- "When would you not do this?"
- "What changes if condition X occurs?"
- "Where in the demonstration is this shown?"
- "What did the expert actually say?"
- "Which parts are inferred?"

### Success signal

Answers are traceable to correct source evidence and timestamps.

### Kill signal

The system produces fluent but weakly grounded answers.

## Experiment 3 — Practice Task Generation

### Hypothesis

Validated knowledge can be transformed into a useful bounded practice task.

### Test

Ask the system to generate:

- objective
- prerequisites
- tools/materials
- steps
- constraints
- success criteria
- common mistakes.

### Human evaluation

Expert and learner rate usefulness.

## Experiment 4 — Learner Attempt Evaluation

### Hypothesis

Anveshan can identify meaningful observable differences between expert demonstration and learner attempt.

### Test

Record learner performing the same bounded task.

Evaluate:

- sequence
- timing
- tool handling
- technique
- observable cues
- output.

### Success signal

Expert agrees that feedback identifies real issues.

### Kill signal

Feedback is generic, speculative, or not grounded in observable evidence.

## Experiment 5 — Transmission Gain

### Hypothesis

Evidence-grounded feedback improves learner performance.

### Protocol

1. learner performs baseline attempt;
2. capture attempt;
3. Anveshan teaches;
4. learner performs second attempt;
5. Anveshan evaluates;
6. expert independently scores both attempts.

### Metric

**Transmission Gain = post-training score − baseline score**

Use a domain-specific rubric.

## Experiment 6 — Expert Fidelity

### Hypothesis

The knowledge representation accurately reflects the expert's practice.

### Test

Show expert:

- transcript
- extracted knowledge
- claims
- conditions
- lesson
- generated practice task.

Ask for:

- correct
- incomplete
- incorrect
- misleading
- missing context.

## Experiment 7 — Demo Comprehension

### Hypothesis

A judge can understand the product and its differentiation quickly.

### Test

Show a short end-to-end demo to someone unfamiliar with the project.

Ask:

- What did the product do?
- What is different from an AI tutor?
- Where did the knowledge come from?
- Did the learner improve?
- What would you use it for?

## Kill Criteria

- no authentic expert access
- extraction fidelity too low
- evidence grounding unreliable
- feedback generic
- learner evaluation unreliable
- improvement unmeasurable
- expert disagreement too high
- demo requires excessive narration
- product indistinguishable from existing AI tutoring.

## Validation Order

1. Access authentic data.
2. Prove extraction.
3. Prove grounding.
4. Prove practice task.
5. Prove learner evaluation.
6. Prove improvement.
7. Prove short demo.
8. Only then expand product surface.
