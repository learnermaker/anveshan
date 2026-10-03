# Track B Replay Case 001

Placeholder case for contract development.

## Required inputs

- `PracticeTask`;
- reference/evidence identifiers;
- learner baseline attempt;
- second attempt;
- rubric definition.

## Expected outputs

- `LearnerAttempt`;
- `Evaluation`;
- `Feedback`;
- `TransmissionRecord`.

## Assertions

At minimum:

- baseline and post-training states are distinct;
- evaluation uses observable rubric criteria;
- feedback points to evidence/criteria;
- retry is represented explicitly;
- measurable change is reproducible from recorded inputs;
- lineage identifies source, learner, and transmission event.

This case is intentionally domain-agnostic until M0 selects the bounded use case.
