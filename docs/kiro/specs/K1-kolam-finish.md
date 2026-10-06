# K1: Kolam finish (tests, real build, golden run, end-to-end session)

Read `docs/kiro/specs/00-COMMON.md` first. Folder `...\anveshan-wt\k1-kolam`, branch `kiro/k1-kolam`. **Needs the API key** for one optional Gemma call: copy `.env` into the worktree root (never print it).

## Current state (merged)
- `tracks/common/kolam_geometry.py`: dots, skeleton, curve decomposition, symmetry, photo registration. Numpy + Pillow only.
- `tracks/common/goals/kolam.py`: the `KolamGoal` payload, `ui_view`, `payload_from_image(path) -> (payload, built_with)`, `goal_samples`, `dense_goal`.
- `tracks/track-a/src/track_a/goals/kolam.py`: `build()`. Claims CLM-01..05 are OBSERVED, the stage STEPs are INFERRED at confidence 0.4, and there are 5 criterion templates. The optional Gemma description uses the prompt `tracks/track-a/prompts/kolam_describe_v1.txt`.
- `tracks/track-b/src/track_b/evaluators/kolam.py`: two paths, trace (process plus outcome) and image (outcome only; process criteria are UNCERTAIN).
- Results on the real target (`tracks/cases/kolam/source/ithayakkamalam_target.jpg`): 41 dots (1 centre, 8 rays × 5), K = 1 closed line, 32 crossings, 8-fold rotation, no mirror axes. Builds in about 1.4 s.
- Eval: `tracks/track-b/eval/kolam/` has 10 synthetic variants. 50/50 criterion statuses and 10/10 first divergences agree. Held-out validation (`tracks/track-a/eval/KOLAM_PATH_VALIDATION.md`): 99.3% / 99.8% route overlap.
- **Gap: there are no Kolam pytest tests.**

## Files you own
All Kolam files listed above, plus:
- `tracks/common/tests/test_kolam_geometry.py`, `tracks/track-a/tests/test_kolam_goal.py`, `tracks/track-b/tests/test_kolam_eval.py`;
- `tracks/track-b/eval/kolam/**`;
- `tracks/cases/kolam/**` (built artifacts, golden runs);
- the Kolam table in `docs/plans/evaluation-core.md` §3.2 only.

## Steps
1. **Write the tests.**
   - Geometry: small synthetic images, e.g. two crossing loops through dots drawn with Pillow. Assert dot count, K, closed loops, rotation order, `split_stages`, and `register_similarity` recovering a known rotation and scale.
   - Goal: build on the real target and assert 41 dots, K = 1, rotation 8. Check that claim ids are CLM-01..; that OBSERVED claims use `#xywh=percent:` locators with no times and inferred claims have confidence ≤ 0.5; and that each `why_it_matters` cites its claims. Add fake-gateway tests for the success path and for a ModelError turning into a warning. Assert determinism (identical JSON from two builds).
   - Eval: run the evaluator on the `synthetic/*` variants and assert statuses using the bands in `run_eval.py`.

   The missing-stage coverage sits at 0.899, right at the 0.90 band edge. Make the synthetic generator omit a stage further from the crossings so the test isn't fragile, and regenerate the files.
2. **Speed up the photo path** to ≤ 3 s (it is 3–4 s now) by narrowing the coarse rotation search or subsampling points. Keep the eval results unchanged.
3. **Update evaluation-core §3.2:** the bands degenerate when K = 1. Record the as-built rule (CURVES has no partial band when K = 1; CONTINUITY uses excess pen lifts = strokes − K, with ≤ 1 satisfied and ≤ max(K, 3) partial) and the two extra metrics (`kolam.stages_completed_ratio`, reported only; `kolam.first_divergence`, image path, always UNCERTAIN).
4. **Real build with golden runs:**
   ```python
   from pathlib import Path
   from track_a.api import build_case
   from tracks.common.runtime import RunContext
   ctx = RunContext.create(Path('tracks/cases/kolam'), Path('var'), 'live')
   h = build_case(Path('tracks/cases/kolam'), ctx)
   ```
   This makes one Gemma image call, which takes about 45 s. If it times out, set `ANVESHAN_MODEL_TIMEOUT_MS` if that variable exists by then (another session may add it); otherwise accept the warning path. Then:
   - Inspect the warnings: any Gemma disagreement should be a warning, never an override.
   - Copy the new run folder(s) from `var/runs/kolam/` to `tracks/cases/kolam/runs/golden/`.
   - Confirm that `RunContext.create(..., 'recorded')` followed by `build_case` reproduces byte-identical artifacts. Delete the duplicate version it writes before committing; commit only v1.
   - Commit `knowledge/*.v1.json` and `practice/*.v1.json`.
5. **End-to-end session (no service):**
   - Use `track_b.api`: `start_session` → `intake_attempt` + `submit_attempt` with a flawed synthetic trace (e.g. the stray-stroke variant) as the baseline → then the perfect trace as the retry → `complete_session`.
   - Assert the bundle passes `tracks.common.validator.validate_transmission_bundle`, that the gain is positive, and that `targeted_change` shows the first-divergence criterion improved.
   - Add this as a test, `tracks/track-b/tests/test_kolam_session_e2e.py`, in recorded mode using the committed golden runs (it must not need the key).
   - Also run it with the image-path (photo) attempt as the retry, and confirm the process criteria show UNCERTAIN.

## Acceptance
- The three test files and the e2e test exist and pass.
- v1 artifacts and golden runs are committed and reproduce in recorded mode.
- The photo path runs in ≤ 3 s.
- The Definition of Done in 00-COMMON.md is met. Report: `docs/kiro/reports/K1-REPORT.md`.
