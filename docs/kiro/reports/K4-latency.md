# K4 Gemma Latency Probe Results

Probe ran against `gemma-4-26b-a4b-it` using JPEG frames sampled from `OrigamiCrane.ogv`
(window [0, 194] s). Frames resized to the given resolution, JPEG quality 75.
Timeout: `ANVESHAN_MODEL_TIMEOUT_MS=120000` (120 s) — set to produce clean timeout vs. success signals.
Prompt: one-sentence description task (~100 chars). Runs recorded under `var/runs/_probe/`.

## Results table

| n_images | resolution (px) | run | status | latency (s) | notes |
|----------|-----------------|-----|--------|-------------|-------|
| 1 | 256 | 1 | OK | 6.5 |  |
| 1 | 256 | 2 | OK | 2.0 |  |
| 1 | 384 | 1 | OK | 3.9 |  |
| 1 | 384 | 2 | OK | 3.5 |  |
| 2 | 256 | 1 | OK | 4.5 |  |
| 2 | 256 | 2 | OK | 2.2 |  |
| 2 | 384 | 1 | OK | 3.7 |  |
| 2 | 384 | 2 | OK | 2.1 |  |
| 3 | 256 | 1 | OK | 4.1 |  |
| 3 | 256 | 2 | OK | 2.5 |  |
| 3 | 384 | 1 | OK | 3.7 |  |
| 3 | 384 | 2 | OK | 2.4 |  |
| 4 | 256 | 1 | OK | 4.3 |  |
| 4 | 256 | 2 | OK | 3.6 |  |
| 4 | 384 | 1 | OK | 5.2 |  |
| 4 | 384 | 2 | OK | 2.3 |  |
| 6 | 256 | 1 | OK | 4.8 |  |
| 6 | 256 | 2 | OK | 2.8 |  |
| 6 | 384 | 1 | OK | 4.9 |  |
| 6 | 384 | 2 | OK | 3.4 |  |

## Summary

| Config | Mean latency (s) | All succeeded |
|--------|-----------------|---------------|
| 1 img @ 256 px | 4.3 | yes |
| 1 img @ 384 px | 3.7 | yes |
| 2 img @ 256 px | 3.4 | yes |
| 2 img @ 384 px | 2.9 | yes |
| 3 img @ 256 px | 3.3 | yes |
| 3 img @ 384 px | 3.0 | yes |
| 4 img @ 256 px | 4.0 | yes |
| 4 img @ 384 px | 3.8 | yes |
| 6 img @ 256 px | 3.8 | yes |
| 6 img @ 384 px | 4.1 | yes |

All 20 probe calls completed well within the 120 s timeout. Max observed latency: 6.5 s.

## Key finding vs spec baseline

The spec noted `gemma-4-26b-a4b-it` latency as "text ~4–7 s; 1 image ~43 s; 4-image call 504 at 120 s".
Today's measurements show 2–7 s across all image counts at ≤ 384 px with JPEG q75. This discrepancy likely
reflects one or more of: an updated model serving layer, the much simpler probe prompt (vs the complex
per-frame origami-states analysis prompt), or smaller/compressed image payloads (≤ 384 px, q75) vs the
earlier test.

## Batching policy recommendation

Since all probe configs succeed quickly, the constraint is no longer raw image count but the *complexity
of the per-frame analysis task*. The full `origami_states_v1` prompt asks the model to analyse each frame
and return structured JSON per frame; this is much heavier than the probe's one-sentence description.

Chosen policy (implemented in Step 3 / v2 prompts):
- **Goal builder**: batch size 4 frames per call (was 12). Reduces per-call analysis load; with 194 s @ 1 fps
  → ~49 batches, each well under the 300 s production timeout.
- **Evaluator match**: drop reference keyframe images from match calls; pass reference states as text instead.
  Send up to 8 learner frames per call (8 images total, no reference images). This avoids 7+N images per call
  and lets the model focus on the learner frames without the overhead of re-examining known reference states.
- **Evaluator final check**: unchanged (2 images: reference R_k + learner final).
- **Production timeout**: `ANVESHAN_MODEL_TIMEOUT_MS=300000` (300 s) — ample margin even for complex prompts.
