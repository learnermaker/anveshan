# Metrics Framework

**Review checkpoint:** 2026-10-03

## Primary Outcome

### Transmission Gain

**Transmission Gain = post-transmission learner performance − baseline learner performance**

This is a candidate metric, not a validated universal measure.

It must use a skill-specific rubric.

## Criterion-Level Measures

### Knowledge Fidelity
Expert-reviewed extraction accuracy.

### Evidence Grounding Accuracy
Fraction of generated claims whose evidence actually supports them.

### Timestamp/Citation Accuracy
Fraction of evidence references pointing to the correct source segment.

### Evaluation Agreement
Agreement between Anveshan's criterion-level observations and independent expert assessment.

### Feedback Actionability
Fraction of feedback items judged specific, observable and useful.

### Learner Improvement
Change between baseline and subsequent attempt.

### Transmission Completion
Fraction completing the full defined loop.

### Time to Competency
Time/attempts to reach the predefined rubric threshold.

### Uncertainty Calibration
Whether uncertainty labels correlate with actual ambiguity/error.

### Contradiction Recall
Fraction of known material disagreements surfaced rather than silently merged.

## Metric Integrity Rules

- Never report a headline metric without its rubric.
- Never compare scores across unrelated skills without normalization.
- Never treat model confidence as ground truth.
- Report sample size.
- Report expert-review methodology.
- Preserve raw observations.
- Distinguish automated evaluation from human evaluation.

## Google AI Evaluation Alignment

Current Google Agent Platform evaluation uses trace-based evaluation with reference-based and reference-free metrics. Anveshan should use the same discipline: define eval cases, capture traces, score outputs, analyze failures and iterate.
