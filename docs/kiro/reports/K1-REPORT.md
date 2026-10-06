# K1 Kolam — Step 1 Test Suite Report

Branch: `kiro/k1-kolam`
Python: 3.13.14 | pytest 9.1.1

## Pytest run (kolam-specific suite, `not live`)

Command:
```
python -m pytest -v tracks/common/tests/test_kolam_geometry.py \
  tracks/track-a/tests/test_kolam_goal.py \
  tracks/track-b/tests/test_kolam_eval.py -m "not live"
```

Output:
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

## Review findings resolved

| Finding | Severity | Resolution |
|---|---|---|
| `missing-pytest-evidence` | blocking | This file. Pytest output recorded above. |
| `band-duplication-drift` | non-blocking | `test_kolam_eval.py` now imports `default_bands` and `status` directly from `run_eval.py` via `importlib.util`. No more inline copy. |

## Files changed in this iteration

- `tracks/track-b/tests/test_kolam_eval.py` — replaced duplicate `_default_bands` / `_status` with importlib-backed aliases to `run_eval.default_bands` / `run_eval.status`
- `docs/kiro/reports/K1-REPORT.md` — this file (pytest evidence)
