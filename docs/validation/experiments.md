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
Which product phenomenon is being tested? Use the current competition/MVP thesis unless the experiment is explicitly marked exploratory.

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
Record extraction error, evidence error, evaluation error, uncertainty failure, latency/quota failure, etc.

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

## Current Planned Experiments — Transmission Thesis

These experiments validate the current competition/MVP wedge defined in `docs/product/product-thesis.md` and bounded by `docs/product/mvp-contract.md`.

1. Authentic expert demonstration → structured knowledge extraction.
2. Ten difficult evidence-grounding questions.
3. Expert review of knowledge fidelity.
4. Source-grounded teaching and practice-task generation.
5. Learner baseline attempt.
6. Learner attempt evaluation against a skill-specific rubric.
7. Evidence-grounded feedback.
8. Learner retry and measurable improvement.
9. End-to-end transmission record and lineage.
10. Short demo comprehension.

### Exploratory state/action/outcome work

The repository also contains research on state → action → outcome, first divergence, recovery, intervention verification, demonstration compilation, and related physical-world intelligence concepts.

Those experiments are **research-only** unless an explicit product decision promotes them into the current thesis. They must not be treated as active MVP scope or as a reason to rewrite the current transmission validation plan.

## Evidence Rule

A plan is not a result. A prototype feature is not validated merely because it runs. Every validation finding must point to reproducible evidence and a dated run record.

## Promotion Rule

A research experiment may change the current product direction only when:
1. the result is recorded with reproducible evidence;
2. the product implications are documented;
3. direct competitive overlap is rechecked;
4. the relevant product/architecture decision is explicitly updated in a canonical document or ADR.
