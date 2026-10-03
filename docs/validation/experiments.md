# Experiment Log

## Experiment Record Template

### Experiment

Name:

### Date

YYYY-MM-DD

### Hypothesis

What do we believe will be true?

### Input

What real source material or user data was used?

### Procedure

What was tested?

### Expected Result

What would support the hypothesis?

### Actual Result

What happened?

### Human Evaluation

Who evaluated it and how?

### Metrics

Relevant quantitative measures.

### Evidence

Links, screenshots, recordings, outputs, or commits.

### Finding

- validated
- partially validated
- invalidated
- inconclusive.

### Decision

What changes as a result?

### Follow-up

What must be tested next?

---

## Current Planned Experiments

1. Real expert video → tacit/conditional extraction.
2. Ten difficult evidence-grounding questions.
3. Practice-task generation.
4. Learner attempt evaluation.
5. Expert fidelity review.
6. Baseline vs second attempt.
7. Short demo comprehension.

No experiment should be marked successful without evidence.
# Experiment Log

**Status:** experimental record. Planned experiments must not be described as results.

## Experiment Record Template

### Experiment
Name:

### Date
YYYY-MM-DD

### Hypothesis
What do we believe will be true?

### Candidate Thesis
Which product phenomenon is being tested? Examples: first divergence, recovery, intervention verification, demonstration compiler, variant mining, transmission.

### Input
What real source material, benchmark case or self-recorded data was used?

### Dataset / Case IDs
List exact cases.

### Model / Version
Exact model name and release stage.

### Prompt Version
Repository prompt path + version.

### Configuration
Sampling/temperature if applicable, tools, video mode, context limits and other material settings.

### Quota Budget
Maximum intended model calls and media-processing budget.

### Procedure
What was tested?

### Expected Result
What would support the hypothesis?

### Actual Result
What happened?

### Metrics
Relevant quantitative measures.

### Human Evaluation
Who evaluated it, blind/unblind status where relevant, rubric, and adjudication method.

### Evidence
Links/paths to outputs, screenshots, recordings, run summaries and commits.

### Failure Categories
Record temporal error, unsupported claim, wrong state, wrong action, missed event, false positive, uncertainty failure, latency/quota failure, etc.

### Finding
- validated
- partially validated
- invalidated
- inconclusive.

### Decision
What changes as a result?

### Follow-up
What must be tested next?

---

## Planned Experiments

1. Real/self-recorded procedural video → state/action/outcome extraction.
2. First meaningful divergence between reference and attempt.
3. Recovery sequence identification.
4. Intervention verification: before state → action → after state.
5. Expert commentary/evidence grounding.
6. Demonstration-to-state-model compilation.
7. Multiple-expert invariant/variant mining.
8. Transmission baseline → teaching → retry → improvement, only if the transmission thesis survives the earlier gates.
9. Short demo comprehension.

## Evidence Rule

A plan is not a result. A prototype feature is not validated merely because it runs. Every validation finding must point to reproducible evidence and a dated run record.
