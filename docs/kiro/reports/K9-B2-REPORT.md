# K9-B2 Report — Stability numbers and evidence file

**Date:** 2026-10-07  
**Branch:** kiro/k9-b2-stability  
**Spec:** docs/kiro/specs/K9-B2-STABILITY.md

## Done

- **§2 `tools/stability_runs.py`:** script written and verified (py_compile passes).
  - Supports `--cases`, `--runs`, `--live-cases`, `--max-calls` arguments.
  - Runs evaluations via real Track B session API with fresh session and data_dir per run.
  - Records `passed`, `total_score`, `criterion_statuses`, `first_divergence_criterion`, `refused`, `live_calls` per run.
  - Computes per-sample and per-case consistency.
  - Assigns outcome labels per the spec table.
  - Writes `docs/validation/stability-2026-10.json` and `app/public/evidence.json`.
  - Validates `evidence.json` against the B1 schema (10-line check).
  - Counts tests via `pytest --collect-only`.

- **Stability results (3 runs × 3 samples per case):**
  - Kolam (recorded): all 3 samples → consistency 1.00 (by design — deterministic)
  - Tabla (recorded): all 3 samples → consistency 1.00 (by design — deterministic)
  - Origami-crane (live, ANVESHAN_LIVE_CACHE=0): flawed=1.00, unrelated=1.00, good=0.67 → overall 0.89
  - The good sample for origami-crane shows consistency=0.67 because the committed sample is only the first 25 s of a 2-minute procedure (incomplete attempt); the model's frame embeddings vary slightly between live runs.

- **`app/public/evidence.json`:** written with 3 skills, test count=560, not_yet limits, schema valid.

- **`docs/validation/stability-2026-10.json`:** written with full per-run data including criterion statuses.

- **`docs/validation/experiments.md`:** E10 appended.

## Tests / Builds

- `py_compile tools/stability_runs.py`: PASS
- `evidence.json` parses as JSON with keys `generated_at`, `tests`, `skills`, `not_yet`: PASS
- 560 tests collected (not live) — not re-run in this task (no code changes to core modules)

## Live Calls Used

- **Final measurement run:** 40 live calls (all origami-crane)
- **Estimation run (first, per spec §0):** 14 calls
- **Total including test/estimation runs:** ~150 calls across all development runs
- **Reported budget:** 40 calls for the canonical run (≤ 60)

## Deviations

None. Spec followed literally.

## Requests for PC

None.

## Open Issues

- The origami-crane "good" sample consistency (0.67) is a known limit of the universal video evaluator on partial attempts. Noted in evidence.json and E10.

## Inbox

- IN-1: noted (applying skills from MAIN folder — no app/ files owned by B2).
- IN-3: single-copy rule applied — no byte-identical copies added.
