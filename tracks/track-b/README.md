# Track B — Practice, Evaluation & Transmission

**Owner boundary:** learner practice, attempt representation, rubric-based evaluation, evidence-linked feedback, retry, transmission measurement, and lineage output.

## Objective

Prove that a learner can consume a bounded practice input, submit observable evidence, receive traceable feedback, retry, and show measurable criterion-level change.

## Work boundary

In scope for this track:

1. practice-task consumption;
2. learner baseline and attempt capture;
3. observable attempt representation;
4. domain-specific rubric interface;
5. evaluation logic;
6. evidence-linked feedback;
7. retry/second-attempt flow;
8. baseline → post-attempt measurement;
9. `TransmissionRecord` and lineage output;
10. deterministic replay validation.

Out of scope:

- expert-source ingestion;
- knowledge extraction;
- claim grounding;
- expert-side knowledge authoring;
- production integration with Track A internals.

## Expected contract inputs/outputs

Consumes frozen:

- `KnowledgePackage`;
- `EvidenceRef`;
- `PracticeTask`.

Produces:

- `LearnerAttempt`;
- `Evaluation`;
- `Feedback`;
- `TransmissionRecord`.

Use replay fixtures when Track A is not integrated.

## Starter validation

A replay case should contain:

`practice task → baseline attempt → second attempt → rubric observations → feedback → measured change`

The fixture should allow comparison against expected criterion-level outcomes and must not reduce evaluation to one unconstrained model score.

## Suggested worktree

```text
tracks/track-b/
├── README.md
├── fixtures/
│   └── replay/
├── prompts/
├── src/
├── tests/
└── notes/
```

Create implementation files only through bounded issues.
