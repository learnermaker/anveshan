# K4 Report: Origami live model runs, tuning and evaluation

**Branch:** kiro/k4-origami  
**Date:** 2026-10-06  
**Status:** IMPLEMENTED

---

## Summary

All 10 K4 steps executed. The origami goal builder and evaluator ran live against `gemma-4-26b-a4b-it` for the first time. The live goal build produced a 5-state goal (R0–R4) from the expert video. All 5 synthetic/control attempts were evaluated and results are committed. The pipeline is fully recorded and replays byte-identically.

---

## Step-by-step results

### Step 1: Configurable timeout and 504 retry (`feat(models)`)
- Added `ANVESHAN_MODEL_TIMEOUT_MS` env var (default 300 000 ms) to `ModelGateway`.
- Added single retry on 504 / DEADLINE_EXCEEDED / UNAVAILABLE, recorded in `RunMetadata.notes`.
- Updated `.env.example` to document the variable.
- 7 new tests in `test_foundation.py`; all pass.

### Step 2: Latency probe (`feat(origami): latency probe`)
- Tool: `tools/probe_gemma_latency.py`
- 20 calls: 5 n_image configs × 2 resolutions × 2 runs at `ANVESHAN_MODEL_TIMEOUT_MS=120000`
- Results: all 20 succeeded at **2–7 s** for 1–6 images at 256–384 px.

**Key finding:** The spec documented "1 image ≈ 43 s; 4-image call 504 at 120 s". Today's measurements show 2–7 s across all image counts at ≤ 384 px with JPEG q75, likely because the probe used a simple one-sentence prompt vs the complex per-frame analysis prompts. Full results in `docs/kiro/reports/K4-latency.md`.

| Config | Mean latency (s) | Succeeded |
|--------|-----------------|-----------|
| 1 img @ 256 px | 4.3 | 2/2 |
| 2 img @ 256 px | 3.4 | 2/2 |
| 4 img @ 256 px | 4.0 | 2/2 |
| 4 img @ 384 px | 3.8 | 2/2 |
| 6 img @ 384 px | 4.1 | 2/2 |

### Step 3: Batching policy (`feat(origami): implement batching policy`)

**Chosen policy:** The probe showed all image counts succeed quickly with simple prompts. The bottleneck is complex per-frame analysis prompts that exhaust the per-minute input token quota (16 000 tokens/min for `gemma-4-26b`). Chosen policy:

- **Goal builder**: `BATCH_SIZE=4` (was 12), `FPS=0.5` (was 1.0), `inter_batch_sleep_s=12` in live mode.
- **Evaluator match**: text-only reference states (no reference keyframe images), `MAX_IMAGES_PER_CALL=8` learner frames, `inter_batch_sleep_s=20` in live mode. Prompt version: `origami_match_v2`.
- **Evaluator final**: unchanged (2 images: reference R_k + final frame), prompt `origami_final_v1`.

**Why this drove the decision:** Sending 7 reference images + 9 learner images per call (v1 design) would use ~8 000–16 000 tokens/call, exhausting the per-minute quota after 1 call. Text-only references reduce the image count to just learner frames, staying within quota.

New prompt files created: `origami_states_v3.txt`, `origami_match_v2.txt`.

### Step 4: Real goal build (`feat(origami): real goal build golden runs`)

3 live attempts before a good result:
- **Attempt 1 (v2 prompt, FPS=1.0)**: succeeded but only 3 states. Model over-grouped: mapped square base and kite form to "folded triangle".
- **Attempt 2 (v3 prompt, FPS=0.5 in code)**: hit 429 rate limit on first call; prompt was too verbose.
- **Attempt 3 (v3 compact prompt, FPS=0.5, keyframe evidence fix)**: succeeded with **5 states**.

Fixed `FrameStateDTO.t` validator to accept `"12.0s"` strings (model returns timestamp with "s" suffix). Fixed keyframe evidence interval to avoid `0.0/0.0` locator for R0.

**Final build result (5 states):**
```
R0  flat square              [0–2 s]   ['flat', 'single layer', 'square shape']
R1  book-folded rectangle    [40–42 s] ['rectangular shape', 'folded in half']
R2  diagonal-folded triangle [46–98 s] ['triangular shape', 'folded along diagonal', 'flat']
R3  square base              [102–104 s] ['compact diamond', 'multiple layers']
R4  kite form                [130–188 s] ['arrowhead shape', 'taller than wide']
Final state: R4 (kite form)  |  Key state: R1
```

**Compared to 7-state expert labels (R0–R6):**
- R0 ✓, R2 ✓ (boundary wide), R3 ✓ (boundary off), R4 ✓ (boundary off)
- R1 boundary significantly off: built [40–42 s] vs label [8–28 s]
- R5 (petal fold one side) and R6 (bird base) not detected

Target was 5–8 states. 5 states with correct origami vocabulary is within spec.

### Step 5: Promote golden runs (`feat(origami): promote goal build golden runs`)
- 25 goal-build runs promoted to `tracks/cases/origami/runs/golden/`.
- Recorded replay verified byte-identical: all 5 JPEGs and 3 JSON artifacts matched.

### Step 6: Synthetic attempts evaluation (`feat(origami): synthetic attempt evaluations`)
- `make_synthetic.py` generated 5 videos.
- Ran all 5 variants live (`origami_match@v2`, `origami_final@v1`).
- 20s inter-batch sleep used to stay within rate limits. Each variant: ~12 match calls + 1 final = 13 live calls.
- 13 new evaluator runs promoted to golden; 52 shared across variants.

### Step 7: RESULTS.md (`docs(origami): evaluation RESULTS.md`)
Written at `tracks/track-b/eval/origami/RESULTS.md`.

### Step 8: Observer threshold review
No threshold changes made. Observer bands are correct for the intended semantics. The low scores (final_match=0.5 for all variants) reflect the incomplete 5-state goal (missing R5, R6), not wrong thresholds. Adjusting thresholds would mask the real issue. Documented in RESULTS.md.

### Step 9: Final verification
```
tracks/common/tests: 43 passed
tracks/track-a/tests: 79 passed (1 deselected @live)
tracks/track-b/tests + service/tests: 166 passed (1 deselected @live, 1 warning)
check_case_packs.py: PASS (7 packs)
check_governance.py: PASS
check_contract_parity.py: PASS (8 root contracts, 17 interfaces, 7 enums)
```
Total: **288 non-live tests pass, 0 fail**.

---

## Open issues for Jim / Claude Code to decide

1. **Goal quality: 5 states vs 7.** The goal model misses the petal fold (R5) and bird base (R6). These are important: the petal fold is the critical step of the crane. A better goal model would require improved prompting or a multi-pass approach (e.g., second pass over frames [120–194 s] to find R5/R6). This is not a code bug — it's a model guidance issue.

2. **R1 boundary severely off.** Book-folded rectangle detected at [40–42 s] instead of [8–28 s]. The model sees the later re-fold sequence (t=40s) rather than the initial fold (t=8s). This likely needs a prompt that tells the model to look for the FIRST occurrence, or a coarser initial pass followed by fine-grained boundary detection.

3. **Rate limit (429) sensitivity.** The free-tier paid-tier input token quota (16 000 tokens/min for `gemma-4-26b`) is hit easily with complex per-frame analysis prompts and 4 images/call. Added 12–20 s inter-batch sleep workarounds in live mode. A cleaner solution would be exponential backoff in the ModelGateway on 429 (not in scope for K4; documented here for K5).

4. **`FPS=0.5` in goal builder.** Changed from 1.0 to reduce token usage. With 97 frames and batch_size=4, this gives 25 batches per build. Re-running the build with FPS=1.0 would give better state coverage (194 frames) but more API calls and higher rate-limit risk.

5. **Observer thresholds vs goal completeness.** CRIT-ORI-FINAL is permanently `partially_satisfied` (final_match=0.5) until the goal includes R6 (bird base). CRIT-ORI-KEYSTEP is `not_satisfied` on all attempts because the key state is R1 (brief, often uncertain) rather than R5 (the intended critical step). These are goal quality issues, not threshold issues.

---

## Acceptance criteria status

| Criterion | Status |
|-----------|--------|
| Live goal build succeeded | ✓ |
| Reproducible from committed golden runs in recorded mode | ✓ (byte-identical verified) |
| All 5 synthetic/control attempts evaluated | ✓ |
| Results in RESULTS.md | ✓ |
| No single model call exceeds timeout in final config | ✓ (all calls 3–11 s; timeout=300 s) |
| Non-live pytest suite green | ✓ (288 passed) |
| check_case_packs.py, check_governance.py, check_contract_parity.py pass | ✓ |
| Branch kiro/k4-origami, never merged/pushed/switched | ✓ |
