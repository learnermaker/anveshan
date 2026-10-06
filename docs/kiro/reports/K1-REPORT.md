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

---

# K1 Kolam — Step 4 Golden Run Report

Branch: `kiro/k1-kolam`
Date: 2026-10-06

## Live build

Model: `gemma-4-26b-a4b-it` (via `google-genai`, `text_image` model key)
Latency: 13 805 ms (well under the 45 s budget)
Replay key: `9b4f8eee473f4e3cb168c2bb93bfcfd2`

```
build_case(Path('tracks/cases/kolam'), RunContext.create(..., 'live'))
  case_id:        kolam
  review_status:  pending   (expected — no expert review yet)
  runtime_label:  INTERNET_REFERENCE
  versions:       knowledge_package=1, practice_task=1, criterion_map=1,
                  rubric=1, observers=1, goal_model=1
  goal.warnings:  []  (no Gemma disagreements)
  handoff.warnings: ["package not expert-approved"]  (deterministic status only)
```

## Gemma disagreement confirmation

`goal.warnings` is empty. The kolam builder code raises warnings **only** when
`dto.rotation_order_estimate != sym.rotation_order` or
`dto.curve_count_estimate != k`. In this run Gemma agreed with both computed
values, so no disagreement warning fired. The code path is confirmed: even when
a disagreement is present, it becomes a warning and the **computed value is always
kept**; Gemma never overrides deterministic geometry.

## Golden run folder

```
tracks/cases/kolam/runs/golden/
  9b4f8eee473f4e3cb168c2bb93bfcfd2/
    run_metadata.json
    raw_response.json
```

## Artifacts committed

| File | Bytes |
|---|---|
| `knowledge/knowledge_package.v1.json` | 11 557 |
| `knowledge/goal_model.v1.json` | 198 877 |
| `knowledge/criterion_map.v1.json` | 2 375 |
| `practice/practice_task.v1.json` | 1 907 |
| `practice/rubric.v1.json` | 2 167 |
| `practice/observers.v1.json` | 2 150 |

## Reproducibility

Ran `RunContext.create(clean_case_dir, tmp_data_dir, 'recorded')` → `build_case(...)` on a
fresh copy of the case directory (no prior artifacts, golden run folder as the only RunStore
source). All six `*.v1.json` files were **BYTE-IDENTICAL** to the live-build artifacts.

| Artifact | Result |
|---|---|
| `knowledge_package.v1.json` | BYTE-IDENTICAL |
| `goal_model.v1.json` | BYTE-IDENTICAL |
| `criterion_map.v1.json` | BYTE-IDENTICAL |
| `practice_task.v1.json` | BYTE-IDENTICAL |
| `rubric.v1.json` | BYTE-IDENTICAL |
| `observers.v1.json` | BYTE-IDENTICAL |

