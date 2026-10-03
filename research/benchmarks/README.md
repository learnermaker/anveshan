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
