# K4: Origami live model runs, tuning and evaluation

Read `docs/kiro/specs/00-COMMON.md` first. Folder: `...\anveshan-wt\k4-origami`, branch `kiro/k4-origami`. **Needs the API key:** copy `.env` into your worktree root (never print it).

## Context
The Origami case is fully implemented and unit-tested with fake model responses, but it has **never run against the real model**:
- Goal builder: `tracks/track-a/src/track_a/goals/origami.py`
- Evaluator: `tracks/track-b/src/track_b/evaluators/origami.py` and `origami_trajectory.py`
- Payload schema: `tracks/common/goals/origami.py`
- Prompts: `tracks/track-a/prompts/origami_states_v1.txt`, `tracks/track-b/prompts/origami_match_v1.txt`, `origami_final_v1.txt`
- Eval: `tracks/track-b/eval/origami/` (`README.md`, `make_synthetic.py`, `run_eval.py`, `labels/`)
- Source registry: `tracks/cases/origami/source/source.json`. The expert window is `[0, 194]` s.

The Track A core (`track_a/api.py`: `build_case`, `load_case`) and the Track B core (`track_b/api.py`) are merged.

**Known model behaviour:** a single image takes about 43 s; 4 images timed out at 120 s. The current code sends up to 16 images per call (7 reference keyframes plus 9 learner frames). **This will time out and must be tuned first.**

**Known data fact:** `Crane.ogv`, the "learner" video, is the same performance as the expert video, re-encoded. Treat it only as a positive control.

## Files you own
- `tracks/common/models.py`: only to add a configurable timeout, via env `ANVESHAN_MODEL_TIMEOUT_MS` (default 300000), and a single retry on 504/DEADLINE_EXCEEDED/UNAVAILABLE that is recorded in `RunMetadata.notes`. Update `.env.example` to document the variable, and extend `tracks/common/tests/test_foundation.py`.
- Everything Origami: `tracks/track-a/src/track_a/goals/origami*.py`, `tracks/track-b/src/track_b/evaluators/origami*.py`, `tracks/common/goals/origami.py`, the origami prompts, `tracks/track-b/eval/origami/**`, the origami tests.
- `tracks/cases/origami/**`: golden runs, built artifacts and goal assets.
- New: `tools/probe_gemma_latency.py`.

## Steps
1. **Latency probe.** Write `tools/probe_gemma_latency.py`. It uses the real gateway and records runs under `var/runs/_probe`. Measure latency and success for 1, 2, 3, 4 and 6 images at 256 and 384 px (JPEG q75), with a short JSON task. Run each config twice. Write a table to `docs/kiro/reports/K4-latency.md`. Spend at most about 25 calls.
2. **Choose a batching policy** from the measurements: images per call (including reference keyframes), resolution, timeout and retry. Options to consider:
   - compare learner frames against reference states described in **text** (state names plus property checklists from the goal model) instead of sending all keyframe images every call;
   - send only the 1–2 most relevant reference keyframes;
   - lower the learner frame rate (for example 1 frame / 3 s, giving about 65 frames for 194 s) and use a coarse-to-fine pass;
   - parallel calls with a concurrency limit, if the API allows (stay within free-tier rate limits).

   Implement the chosen policy in the Origami builder and evaluator, keeping the deterministic trajectory rules unchanged. Update the prompt versions (`*_v2.txt`; keep v1). Update the tests (fake gateway) so they cover the new batching.
3. **Real goal build.** Make a small script or CLI call:
   ```python
   from track_a.api import build_case
   from tracks.common.runtime import RunContext
   from pathlib import Path
   ctx = RunContext.create(Path('tracks/cases/origami'), Path('var'), 'live')
   h = build_case(Path('tracks/cases/origami'), ctx)
   ```
   Inspect the result: number of states, names, intervals and keyframe JPEGs in `tracks/cases/origami/knowledge/goal_assets/`. Compare against `tracks/track-b/eval/origami/labels/expert_window_labels.json` (7 states R0–R6). If the model output is poor, iterate on the prompt (v2/v3) and **record the attempts** in your report. Aim for 5–8 sensible ordered states ending at the bird base.
4. **Promote golden runs.** Copy the run folders of the accepted build from `var/runs/origami/<replay_key>/` to `tracks/cases/origami/runs/golden/<replay_key>/`. Then confirm `RunContext.create(..., 'recorded')` + `build_case` reproduces **byte-identical** artifacts. Commit the built `knowledge/*.v1.json`, `practice/*.v1.json` and `goal_assets/*.jpg` (small).
5. **Synthetic attempts.** Run `make_synthetic.py` (outputs go to gitignored `var/eval/origami/`). Then `run_eval.py` in live mode for: perfect, missing_state, swapped_order, truncated, real_learner. Expect about 5 attempts × a few calls each; stay within the free tier. Promote the evaluator golden runs for these attempts, so the eval replays in recorded mode.
6. **Write `tracks/track-b/eval/origami/RESULTS.md`** with real numbers:
   - goal-state agreement (count, order, median boundary error vs labels);
   - per attempt: frame-label accuracy, detected missing states and order violations, final match, first-divergence type and time error vs ground truth, and the criterion statuses.

   Be honest about failures.
7. If any band thresholds in the Origami observers produce clearly wrong statuses on these known cases, adjust them. Document the rule and the before/after.

## Acceptance
- A live goal build succeeded and is reproducible from the committed golden runs in recorded mode.
- All 5 synthetic/control attempts evaluated, with results in `RESULTS.md`.
- No single model call exceeds the timeout in the final configuration (the latency table proves it).
- The Definition of Done in 00-COMMON.md is met. Report: `docs/kiro/reports/K4-REPORT.md`.
