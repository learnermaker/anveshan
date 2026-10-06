# K1 Kolam — Final Report

Branch: `kiro/k1-kolam`
Completed: 2026-10-06
Python: 3.13.14 | pytest 9.1.1

---

## What was implemented

### 1. Three test files (Step 1)

**`tracks/common/tests/test_kolam_geometry.py`** — 6 tests covering:
- Dot detection and single closed loop on a synthetic raster image
- Two independent loops (`K = 2`) detection
- Fourfold rotation-order detection
- `split_stages` respects rotation order; fallback when no rotation
- `register_similarity` recovers a known rotation and scale

**`tracks/track-a/tests/test_kolam_goal.py`** — 9 tests covering:
- Registry points to the kolam builder
- Goal geometry from the real target (41 dots, K=1, 8-fold rotation)
- Claim IDs start with `CLM-01`
- Observed claims use `#xywh=percent:` locators with no times
- Inferred claims have confidence ≤ 0.5
- `why_it_matters` cites its claims
- Fake-gateway success path
- `ModelError` becomes a goal warning (never an override)
- Build is deterministic (two identical JSON outputs)

**`tracks/track-b/tests/test_kolam_eval.py`** — 13 tests covering:
- Registry points to the kolam evaluator
- 10 synthetic variants matched to expected criterion statuses
- Missing-stage coverage well below the 0.90 boundary (generator fixed to omit a stage further from crossings)
- Image-path process criteria are `uncertain`
- Band constants imported directly from `run_eval.py` (no inline copy drift)

### 2. Performance fix (Step 2)

`tracks/common/kolam_geometry.py` — `register_similarity`:
- Source point cap reduced from 800 → **400**
- Coarse rotation step widened from 2.0° → **4.0°**

Before: 3–4 s on the real target photo.
After: ≤ 3 s (target met; K1 spec acceptance criterion satisfied).
Eval results (10 synthetic variants, 50/50 criterion statuses) were unchanged by the change.

### 3. Evaluation-core §3.2 documentation update (Step 3)

`docs/plans/evaluation-core.md` §3.2 updated to record the K=1 degenerate band rules:
- CURVES: no partial band when K = 1 (only satisfied/unsatisfied).
- CONTINUITY: excess pen lifts = strokes − K; ≤ 1 → satisfied, ≤ max(K, 3) → partial.
- Two extra reported-only metrics added: `kolam.stages_completed_ratio` (always reported) and `kolam.first_divergence` (image path, always `uncertain`).

### 4. Golden run v1 artifacts (Step 4)

Live build via `RunContext.create(..., 'live')` → `build_case(Path('tracks/cases/kolam'), ctx)`.

Model: `gemma-4-26b-a4b-it` (provider: `google-genai`, model key: `text_image`)
Gemma latency: **13 805 ms** (well under the 45 s budget)
Replay key: `9b4f8eee473f4e3cb168c2bb93bfcfd2`

Gemma agreed with both deterministic values (`rotation_order`, `curve_count`); `goal.warnings` was empty.
`handoff.warnings` contained only the deterministic `"package not expert-approved"` string.

Reproducibility confirmed: `RunContext.create(..., 'recorded')` on a fresh case directory reproduced all six artifacts **byte-for-byte**.

### 5. End-to-end session test in recorded mode (Step 5)

`tracks/track-b/tests/test_kolam_session_e2e.py` — two flows, both `not live`:
- **Flow A** (trace path): stray-stroke baseline → perfect-trace retry → `complete_session`. Asserts transmission bundle validates, gain > 0, `CRIT-KOLAM-CONTINUITY` improves in `targeted_change`.
- **Flow B** (image path): stray-stroke baseline → raster-perfect image retry. Asserts `process_observable=False`, `CRIT-KOLAM-CONTINUITY` is `uncertain`, `kolam.pen_lifts_excess` has `value=None` with non-null `uncertain_reason`.

---

## Test output summary

### Core suite (Steps 1–2)

```
================= test session starts ==================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: .../anveshan-wt/k1-kolam

tracks/common/tests/test_kolam_geometry.py::test_dot_detection_and_single_closed_loop PASSED
tracks/common/tests/test_kolam_geometry.py::test_two_independent_loops_k_equals_2 PASSED
tracks/common/tests/test_kolam_geometry.py::test_fourfold_rotation_order PASSED
tracks/common/tests/test_kolam_geometry.py::test_split_stages_respects_rotation_order PASSED
tracks/common/tests/test_kolam_geometry.py::test_split_stages_fallback_when_no_rotation PASSED
tracks/common/tests/test_kolam_geometry.py::test_register_similarity_recovers_known_rotation_and_scale PASSED
tracks/track-a/tests/test_kolam_goal.py::test_registry_points_to_kolam_builder PASSED
tracks/track-a/tests/test_kolam_goal.py::test_goal_geometry_from_real_target PASSED
tracks/track-a/tests/test_kolam_goal.py::test_claim_ids_start_with_clm01 PASSED
tracks/track-a/tests/test_kolam_goal.py::test_observed_claims_have_xywh_locators_no_times PASSED
tracks/track-a/tests/test_kolam_goal.py::test_inferred_claims_confidence_at_most_0_5 PASSED
tracks/track-a/tests/test_kolam_goal.py::test_criterion_map_cites_claims PASSED
tracks/track-a/tests/test_kolam_goal.py::test_build_with_fake_gateway_success PASSED
tracks/track-a/tests/test_kolam_goal.py::test_build_model_error_becomes_warning PASSED
tracks/track-a/tests/test_kolam_goal.py::test_build_is_deterministic PASSED
tracks/track-b/tests/test_kolam_eval.py::test_registry_points_to_kolam_evaluator PASSED
tracks/track-b/tests/test_kolam_eval.py::test_evaluator_matches_expected_statuses[extra_pen_lifts] PASSED
tracks/track-b/tests/test_kolam_eval.py::test_evaluator_matches_expected_statuses[jittered] PASSED
tracks/track-b/tests/test_kolam_eval.py::test_evaluator_matches_expected_statuses[missing_stage] PASSED
tracks/track-b/tests/test_kolam_eval.py::test_evaluator_matches_expected_statuses[partial] PASSED
tracks/track-b/tests/test_kolam_eval.py::test_evaluator_matches_expected_statuses[perfect] PASSED
tracks/track-b/tests/test_kolam_eval.py::test_evaluator_matches_expected_statuses[raster_missing_stage_rotated] PASSED
tracks/track-b/tests/test_kolam_eval.py::test_evaluator_matches_expected_statuses[raster_perfect] PASSED
tracks/track-b/tests/test_kolam_eval.py::test_evaluator_matches_expected_statuses[raster_rotated_scaled] PASSED
tracks/track-b/tests/test_kolam_eval.py::test_evaluator_matches_expected_statuses[stray_stroke] PASSED
tracks/track-b/tests/test_kolam_eval.py::test_evaluator_matches_expected_statuses[wrong_dot_relation] PASSED
tracks/track-b/tests/test_kolam_eval.py::test_missing_stage_coverage_well_below_0_90_boundary PASSED
tracks/track-b/tests/test_kolam_eval.py::test_image_path_process_criteria_are_uncertain PASSED

================= 28 passed in 28.50s ==================
```

### End-to-end session test (Step 5)

```
================= test session starts ==================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: .../anveshan-wt/k1-kolam

tracks/track-b/tests/test_kolam_session_e2e.py::test_trace_stray_then_perfect PASSED [ 50%]
tracks/track-b/tests/test_kolam_session_e2e.py::test_image_retry_process_criteria_uncertain PASSED [100%]

================== 2 passed in 15.25s ==================
```

---

## Performance numbers

| Metric | Before | After |
|---|---|---|
| `register_similarity` source point cap | 800 pts | 400 pts |
| Coarse rotation search step | 2.0° | 4.0° |
| Photo-path wall time (real target) | 3–4 s | ≤ 3 s |
| Eval agreement (10 synthetic variants) | 50/50 | 50/50 (unchanged) |
| Gemma image call latency (golden run) | — | 13 805 ms |

---

## Golden run artifact locations

```
tracks/cases/kolam/
  runs/golden/
    9b4f8eee473f4e3cb168c2bb93bfcfd2/
      run_metadata.json       (model: gemma-4-26b-a4b-it, latency: 13 805 ms)
      raw_response.json
  knowledge/
    knowledge_package.v1.json    (11 557 bytes)
    goal_model.v1.json           (198 877 bytes)
    criterion_map.v1.json        (2 375 bytes)
  practice/
    practice_task.v1.json        (1 907 bytes)
    rubric.v1.json               (2 167 bytes)
    observers.v1.json            (2 150 bytes)
```

All six `*.v1.json` files reproduce byte-identically in `recorded` mode from the committed golden run folder.

---

## Open issues and decisions needed

### Gemma timeout behavior (PROPOSED, not yet encountered)

The K1 spec noted the Gemma call could time out (~45 s). In the actual run it completed in 13 805 ms. However, the `ANVESHAN_MODEL_TIMEOUT_MS` environment variable referenced in the spec was not present at runtime; if a future run hits a timeout the builder will fall back to the warning path. **Decision needed from Jim**: should a timeout ceiling be added now, or left until a timeout is actually observed?

### Gemma disagreement warning behavior (code path confirmed, not triggered)

The code raises a warning when Gemma's estimates disagree with computed geometry. In the golden run, Gemma agreed with both values so the warning path was not exercised in a live run (it is exercised in the fake-gateway unit test). **No action required** unless Jim wants a live disagreement exercise; if so, a fabricated image would be needed.

### Expert review gate

`handoff.warnings` contains `"package not expert-approved"` — this is the correct, expected output for a case that has not yet received expert review. The review gate is out of K1 scope and is tracked separately.

### `review_status: pending`

The case has `review_status = pending`. This is correct pre-expert-review state. No action required for K1.

---

## For Jim / Claude Code to decide

1. **Timeout ceiling**: add `ANVESHAN_MODEL_TIMEOUT_MS` guard to the kolam builder now, or defer until a timeout is observed in practice?
2. **Expert review scheduling**: the golden artifacts are ready; the review gate can be opened whenever an expert session is available.
3. **Missing-stage generator**: the synthetic generator now omits a stage further from the crossings (coverage 0.87, comfortably below the 0.90 boundary). If the real-world distribution of missing-stage errors is different, the boundary itself may need revisiting once real learner data is available.

---

## Commit sequence on `kiro/k1-kolam`

```
4cc44ff docs(kiro): K1-K5 specs for parallel Kiro sessions
7939fdf test(kolam): geometry, goal, and evaluator test suite
1041344 test(kolam): geometry, goal, and evaluator test suite
7ecc81a perf(kolam): speed up photo registration to <=3 s
4e4e0b8 docs(kolam): update evaluation-core 3.2 with K=1 degenerate bands
0aff291 feat(kolam): golden run v1 artifacts committed
3d7888a test(kolam): end-to-end session test in recorded mode
e5e6cac docs(kolam): add Step 5 pytest evidence to K1-REPORT (e2e session test)
```
