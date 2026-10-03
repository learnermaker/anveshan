# Validation Plan

**Review checkpoint:** 2026-10-03

## Objective

Prove:

> **Can Anveshan help one human successfully pass a bounded piece of real-world expertise to another human while preserving source evidence and lineage?**

## Gate 0 — Authentic Access

Confirm:

- real expert;
- real learner;
- authentic source media;
- permission to prototype;
- bounded skill;
- safe practice task;
- expert availability for review.

If this gate fails, do not invent a synthetic domain.

## Gate 1 — Knowledge Fidelity

### Test

Give Anveshan an authentic demonstration.

Extract:
- steps;
- sequence;
- conditions;
- cues;
- exceptions;
- failure modes.

### Expert rubric

Each item:
- correct;
- incomplete;
- incorrect;
- invented;
- missing context.

### Pass condition

High-value extracted items receive strong expert agreement and no material invented claims.

### Track A evidence

Track A can establish this gate with replayable source fixtures before real integration. Its independent proof is knowledge fidelity, evidence linkage, and expert-review usability.

## Gate 2 — Evidence Grounding

Create at least 10 adversarial questions.

Include:
- why;
- when not to;
- condition changes;
- exact wording;
- evidence location;
- inferred vs observed.

### Pass condition

Answers point to correct evidence/timestamps and identify uncertainty where appropriate.

### Track A evidence

Track A owns the grounding proof and should preserve claim → evidence references in its fixtures/replay cases.

## Gate 3 — Teaching Quality

Generate a bounded lesson and practice task.

Expert and learner rate:
- usefulness;
- fidelity;
- clarity;
- appropriateness;
- source linkage.

### Shared boundary

Track A produces the lesson/practice-task inputs. Track B may consume frozen versions of those inputs while building its learner loop; neither implementation should block the other.

## Gate 4 — Learner Evaluation

Use a domain-specific rubric with observable criteria.

Do not evaluate with a single unconstrained model score.

Compare:
- expert demonstration;
- learner baseline;
- learner second attempt.

### Pass condition

Expert judges criterion-level feedback materially useful and not misleading.

### Track B evidence

Track B owns attempt representation, rubric application, feedback traceability, retry handling, and replay validation of evaluation behavior.

## Gate 5 — Transmission Gain

Protocol:

1. baseline attempt;
2. Anveshan teaching;
3. learner attempt;
4. feedback;
5. retry;
6. independent expert scoring.

Metric:

**Transmission Gain = post-training score − baseline score**

Also record the full score distribution, not only the headline metric.

### Track B evidence

Track B owns the measurement path and must demonstrate gain against replay fixtures before real integration.

## Gate 6 — Competitive Falsification

Attempt to reproduce the complete MVP using the strongest direct/adjacent competitors.

If the complete loop is already available, revisit positioning.

## Gate 7 — Demo Comprehension

Show the prototype without explanation.

Ask an unfamiliar reviewer:
- What happened?
- Where did the knowledge come from?
- What did AI actually do?
- Did the learner improve?
- Why is this different from a tutor/archive?

## Kill Criteria

- no authentic access;
- poor expert fidelity;
- weak evidence grounding;
- generic feedback;
- unreliable learner evaluation;
- no measurable improvement;
- high competitive overlap;
- demo indistinguishable from existing products.

## Validation Rule

Research can invalidate a novelty hypothesis.

Only real prototype evidence can validate product performance.
