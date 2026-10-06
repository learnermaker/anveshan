# K4 Report: Origami Live Model Runs, Tuning and Evaluation

Branch: `kiro/k4-origami`. Date: 2026-10-06.

## Done

| Step | Status | Notes |
|------|--------|-------|
| 1 Latency probe | DONE | All 20 probes (1–6 imgs, 256/384 px) succeeded in 2–7 s |
| 2 Batching policy | DONE | 4 frames/call goal-builder; evaluator uses text refs (no keyframe imgs) + 8 learner frames |
| 3 Real goal build | DONE | 5 states built (R0–R4); see `knowledge/goal_model.v1.json` |
| 4 Promote goal golden runs | DONE | 25 run folders in `tracks/cases/origami/runs/golden/` |
| 5 Synthetic attempts | DONE | 4/5 variants evaluated live; `real_learner` blocked by 429 quota |
| 6 RESULTS.md | DONE | `tracks/track-b/eval/origami/RESULTS.md` |
| 7 Band review | DONE | No adjustments made (see below) |

## Tests

`pytest -q ... -m "not live"` in worktree: **288 passed, 2 deselected, 1 warning**.
`check_case_packs.py`: PASS (7 packs). `check_governance.py`: PASS. `check_contract_parity.py`: PASS.

## Live Results (4 of 5 variants)

Goal-vs-labels: 5 goal states vs 7 labelled. Median boundary error 11.01 s.
Matched label indices: [0, 2, 2, 4, 5] (label 2 matched by two goal states; labels 1, 3, 6 missed).

| Variant | frame_acc | missing_det | order_det | final_agrees |
|---------|-----------|-------------|-----------|--------------|
| perfect | 10.5% | uncertain | FAIL (2 violations in expert) | true |
| missing_state | 11.1% | FAIL (0 found, R2 cut missed) | partial (1) | true |
| swapped_order | 7.7% | OK (0) | FAIL (0 detected, expected ≥1) | true |
| truncated | 14.3% | FAIL (0 found, goal R4 reached before cut) | partial (1) | false |
| real_learner | quota-exhausted | — | — | — |

All variants show `final_match=0.5` (partially_satisfied): the pairwise final-state check
never confirms a full match even for the positive control.

## Band Review (Step 7)

No band adjustments made. The five observer criteria (ORDER/COMPLETE/CLEAN/KEYSTEP/FINAL) are
logically correct. Quality failures trace to three root causes, not band miscalibration:
- Goal model captured 5 of 7 states; truncation/swap edits at label boundaries outside goal scope
  are invisible to the evaluator.
- R1 keyframe window (40–42 s, 2 s) is below the stable-run filter threshold in the positive
  control; adjusting the band would not fix the 2-second window.
- `origami_final_v1` pairwise prompt consistently returns partial match (0.5). Widening the
  SATISFIED band to 0.5 would make CRIT-ORI-FINAL trivially always satisfied.

## Deviations

- `real_learner` variant not completed: Gemini free-tier daily quota (429) exhausted at
  ~120 calls during evaluation session. Quota reset required (next calendar day).
- Goal builder produced 5 states, not the 7 in expert labels. States R1 (book-fold) and
  R5/R6 (final crane details) were not robustly captured.
- `ANVESHAN_VIDEO_FRAMES_MODEL` env var (set to `gemini-3.5-flash-lite`) was documented but the
  model used for all actual runs is `gemma-4-26b-a4b-it` (the gateway's default).

## Open Issues

1. **real_learner not run**: needs one fresh live call after quota reset.
2. **Goal model scope**: R1 (book-fold, 2 s window) and R5/R6 (final crane steps) not captured.
   A second goal build attempt or prompt tuning might recover these states.
3. **Pairwise final check**: `origami_final_v1` prompt returns 0.5 for all attempts including
   the positive control. Prompt v2 or a relaxed match criterion would be needed.
4. **Frame-label accuracy (8–14%)**: limited by goal/label index mismatch and high "transition"
   model output frequency. Acceptable for a prototype; needs improvement for production.
