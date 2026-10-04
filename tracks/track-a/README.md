# Track A — Expert Intelligence & Grounding

**Owner boundary:** source understanding, structured knowledge, evidence grounding, and generation of the bounded teaching/practice inputs.

## Objective

Prove that an authentic expert demonstration can be transformed into a source-grounded knowledge representation and a bounded teaching/practice input without material invention.

## Work boundary

In scope for this track:

1. source/media ingestion representation;
2. multimodal understanding;
3. structured procedure, cues, conditions, exceptions, and failure modes;
4. claim → evidence references;
5. grounded explanation/lesson generation;
6. practice-task generation as an output contract;
7. expert-review/replay support;
8. deterministic validation of provenance and contract conformance.

Out of scope:

- learner attempt evaluation;
- learner feedback/retry logic;
- transmission-gain calculation;
- production integration with the learner runtime.

## Expected contract outputs

Track A may produce:

- `KnowledgePackage`
- `EvidenceRef`
- `PracticeTask`

Use frozen fixtures when Track B is not integrated.

## Starter validation

The initial replay fixture should contain a synthetic-but-structurally-realistic source package and expected evidence links. It must distinguish:

- observed/source-backed content;
- derived interpretation;
- uncertainty;
- missing evidence.

The fixture is scaffolding only; it is not validation of the product hypothesis.

## Suggested worktree

```text
tracks/track-a/
├── README.md
├── fixtures/
│   └── replay/
├── prompts/
├── src/
├── tests/
└── notes/
```

Create implementation files only through bounded issues. See `docs/architecture/google-stack-integration.md` for Gemini File API, Agentic Video Understanding, and Pydantic structured output patterns.
