# K9-P4 Report — Sample attempts and example sources

## Done

- `tools/make_samples.py`: deterministic generator (seed=7). Generates all sample media, calibrates expected values by running the real Track B evaluator in recorded mode, writes `samples.json` files.
- `tracks/cases/kolam/samples/`: 3 trace samples (good, flawed, unrelated). Flawed skips 35-70% of arc to fail CRIT-KOLAM-COVERAGE (required).
- `tracks/cases/tabla/samples/`: 3 audio WAV samples (good, flawed, unrelated). Flawed drifts tempo +12% after midpoint and drops a stroke.
- `tracks/samples/sources/`: `sources.json`, `kolam_photo.png` (512px rendered from goal curve), `tabla_rhythm.wav` (copy of tabla good.wav).
- `service/anveshan_service/samples.py`: `Sample` model, `load_pack`, `public_view`, `sample_paths`, `load_sources`.
- `service/anveshan_service/routes/samples.py`: 6 routes — list samples, preview, submit sample attempt, list sources, get source file, analyze source.
- `service/tests/test_k9_samples.py`: 21 tests, all pass. Includes real-evaluator regression guard.
- `.github/scripts/check_case_packs.py`: extended with `validate_samples_dir` to validate `samples/` directories.

## Sample table

| case  | id        | file              | size (bytes) | expected result             |
|-------|-----------|-------------------|-------------|-----------------------------|
| kolam | good      | good.trace.json   | 36,411      | passed=True                 |
| kolam | flawed    | flawed.trace.json | 23,514      | passed=False, first_off_track=CRIT-KOLAM-COVERAGE |
| kolam | unrelated | unrelated.trace.json | 349      | passed=False, first_off_track=CRIT-KOLAM-PRECISION |
| tabla | good      | good.wav          | 400,044     | passed=True                 |
| tabla | flawed    | flawed.wav        | 400,044     | passed=False, first_off_track=CRIT-TABLA-COMPLETE |
| tabla | unrelated | unrelated.wav     | 256,044     | refused=True                |

## Tests

- All 21 K9-P4 tests pass.
- Full non-live suite: 501 passed, 2 deselected, 0 failed.
- `check_case_packs.py`: PASS (7 packs).

## Deviations

- Kolam flawed skip widened from 45-55% to 35-70% (35% of arc) so CRIT-KOLAM-COVERAGE (required) fails. Logged per spec §3 calibration instruction "widen the skipped region".
- `samples.py` places `REPO_ROOT` from `anveshan_service.__init__` (worktree root), not a hardcoded path.
- Tabla unrelated sample uses a 220Hz hum; the tabla evaluator catches it via `percussive_contrast` check and raises `AnveshanFailure` (refused).

## Requests for PC

1. Register the samples router in `service/anveshan_service/main.py` (one line in `create_app`, owned by P1): `for module in (health, key, cases, sessions, media, compose, samples): app.include_router(module.router)`.
2. In P1's `compute()` / insights, add a filter so attempts with `source="sample"` are excluded from learner counts (the `source` field is already written by the samples route via `_try_record_insights`).

## Open issues

None. All acceptance criteria met.

## Live calls used

0
