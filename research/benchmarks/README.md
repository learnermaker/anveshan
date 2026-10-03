# Benchmark Harness

This directory is deliberately separate from application code.

The harness evaluates multimodal model outputs against human/benchmark annotations. It does not call a model itself.

## Layout

- `egoexo/` — benchmark-derived metadata/annotation material; do not commit large video files.
- `fixtures/` — tiny local cases with human-written ground truth.
- `prompts/` — versioned prompts.
- `results/` — generated run results; raw model outputs should be retained outside git unless explicitly approved.
- `scripts/` — deterministic selection, normalization and scoring utilities.

## Design rules

1. Ground truth is created before model evaluation.
2. Model confidence is never treated as truth.
3. Every model claim should carry evidence/timestamps where the task requires it.
4. UNKNOWN is a valid prediction.
5. Scoring code must be deterministic.
6. Benchmark licenses must be checked before redistributing media.
7. Final demos should prefer self-recorded media.
# Benchmark Harness

This directory is deliberately separate from application code.

The harness evaluates multimodal model outputs against human/benchmark annotations. It does not call a model itself.

## Layout

- `egoexo/` — benchmark-derived metadata/annotation material; do not commit large video files.
- `fixtures/` — tiny local cases with human-written ground truth.
- `prompts/` — versioned prompts.
- `results/` — generated run results; raw model outputs should be retained outside git unless explicitly approved.
- `scripts/` — deterministic selection, normalization and scoring utilities.

## Minimum Run Package

Every serious experiment should produce, outside or alongside approved lightweight fixtures:

1. case manifest;
2. exact model/version;
3. prompt version;
4. input references/checksums;
5. normalized model output;
6. deterministic score output;
7. human-review output where applicable;
8. failure-category summary;
9. quota/cost/latency summary;
10. run timestamp.

## Design Rules

1. Ground truth is created before model evaluation.
2. Model confidence is never treated as truth.
3. Every model claim should carry evidence/timestamps where the task requires it.
4. UNKNOWN is a valid prediction.
5. Scoring code must be deterministic.
6. Benchmark licenses must be checked before redistributing media.
7. Final demos should prefer self-recorded media.
8. No benchmark result becomes a product claim until the evaluation population and rubric are documented.
9. Keep model execution separate from scoring so cached/replayed outputs can be evaluated offline.
