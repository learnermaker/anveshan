# K1 Step 1 test suite — Kolam geometry, goal builder, and evaluator

Three test files (179 + 218 + 193 LOC, all new additions) cover the Kolam geometry pipeline, Track A goal builder claim structure, and Track B evaluator variant agreement. The diff also regenerates the `missing_stage` synthetic fixture with two stages (C1.S3 + C1.S4) omitted, moving coverage from 0.899 to ~0.79. The prior `band-duplication-drift` finding from an earlier pass is resolved: `test_kolam_eval.py` now imports `default_bands` and `status` directly from `run_eval.py` via `importlib.util` instead of duplicating them. All 28 tests are recorded green in K1-REPORT.md (28 passed in 28.50 s, Python 3.13 / pytest 9.1.1). `tracks/common/schemas/` has zero diff. No test in any of the three files calls a live model or carries `@pytest.mark.live`.

Watch for: tolerance bounds in the registration test are generous enough to let a moderately degraded algorithm through without triggering failure; the `importlib.util` coupling creates a subtle collection-time dependency on `run_eval.py`.

**Verdict**: APPROVED

---

## High-level view

`test_kolam_geometry.py` is a pure unit test over synthetic Pillow images. It covers dot detection, K-count, closed-curve flags, fourfold rotation order, `split_stages` under both normal and fallback conditions, and `register_similarity` recovering a known 20°/0.8× transform on a diamond shape. The tolerance bounds are the main concern: 0.12 absolute scale error (≈10% relative on the expected 1.25) and 12° rotation tolerance are loose enough that a moderately regressed algorithm would pass silently.

`test_kolam_goal.py` builds from the real JPEG once via a module-scoped fixture and runs eight independent assertions. The `why_it_matters` citation requirement is validated indirectly but correctly: `CriterionMap` carries a `@model_validator` that raises `ValueError` if any `why_it_matters` does not contain one of its `source_claim_ids`, so constructing the map is a real proof-of-correctness, not just a smoke test. The error path in the fake-gateway tests triggers `ModelError` via Pydantic schema validation failure (empty JSON `{}`), covering the schema-fail subcategory but not the network-timeout or API-failure subcategories.

`test_kolam_eval.py` runs the evaluator against all 10 synthetic variants parametrically and adds a standalone guard asserting coverage for `missing_stage` is between 0.70 and 0.88. Importing band logic from `run_eval.py` at module level means a syntax or import error in that script blocks collection of the entire test file rather than causing a single test failure.

---

<details>
<summary>Issues (3)</summary>

1. **Generous registration tolerances** — `test_register_similarity_recovers_known_rotation_and_scale` allows |scale − 1.25| < 0.12 (≈10% relative error) and ≤12° rotation error. A moderately regressed implementation could pass without detection. Consider tightening to ≤0.05 / ≤5° in a follow-up once the real-image suite gives calibration data, or add a comment explaining why these margins are intentional.

2. **ModelError path covers schema-validation failure only** — `test_build_model_error_becomes_warning` fires `ModelError` by feeding an empty JSON object that fails `KolamDescribeDTO` validation. The `TIMEOUT` and API-level-failure categories of `ModelError` are not tested. Noting for future work to add a timeout-simulation variant.

3. **importlib.util coupling blocks collection on run_eval.py errors** — `test_kolam_eval.py` imports `run_eval.py` at module import time (during collection). A syntax error or broken import in `run_eval.py` surfaces as a collection error on the test file, not a single test failure.

</details>

<details>
<summary>Details</summary>

### Geometry unit tests — tolerance calibration for registration

`test_register_similarity_recovers_known_rotation_and_scale` applies a 20° rotation and 0.8× scale to a 4-point diamond, then asserts the recovered inverse falls within ±0.12 and ±12°. The diamond is a worst-case input because four equidistant compass-direction dots produce a flat cost surface when the true rotation is near a multiple of 90°. The 12° tolerance reflects the test author's observation about flat-top scoring inside the tau band. With the real 41-dot kolam target the algorithm would recover to within 3–5°, so the test catches only gross regressions on the synthetic shape.

The scale recovery comment in the test calls the method "very accurate" (RMS-ratio on dot coordinates), but the assertion allows 0.12 — about four times wider than the comment's confidence claim. The comment and the assertion are misaligned.

### Fake-gateway ModelError path — which error category is exercised

The fake reply `"{}"` triggers `ValidationError` inside `ModelGateway.generate()` on `schema.model_validate(extract_json(raw_text))`, which the gateway wraps as `ModelError(FailureCategory.MODEL_FAILURE, ...)`. The kolam builder's `except ModelError` appends `"kolam_describe model call unavailable (model_failure); built deterministically without model wording"`. The `FailureCategory.MODEL_TIMEOUT` path (504 gateway timeout) is not exercised.

### importlib.util band import — collection-time risk

```python
_run_eval_path = Path(__file__).resolve().parents[1] / "eval" / "kolam" / "run_eval.py"
_run_eval_spec = _ilu.spec_from_file_location("run_eval_kolam", _run_eval_path)
_run_eval_mod = _ilu.module_from_spec(_run_eval_spec)
_run_eval_spec.loader.exec_module(_run_eval_mod)
_default_bands = _run_eval_mod.default_bands
_status = _run_eval_mod.status
```

This runs at module-level during pytest collection. The coupling is intentional: threshold drift in `run_eval.py` automatically propagates to the test, directly eliminating the prior `band-duplication-drift` finding. The risk is that if `run_eval.py` gains a broken import, `test_kolam_eval.py` fails to collect rather than producing a single test failure.

</details>

---

<details>
<summary>File map</summary>

| File | What changed |
|---|---|
| `tracks/common/tests/test_kolam_geometry.py` | New: 6 unit tests on synthetic Pillow images (dot detection, K, rotation order, split_stages, register_similarity) |
| `tracks/track-a/tests/test_kolam_goal.py` | New: 9 tests — real-target geometry facts, claim-locator/confidence rules, criterion citation, fake-gateway success/error, determinism |
| `tracks/track-b/tests/test_kolam_eval.py` | New: 13 tests — registry, 10 parametrized variant status+divergence+event checks, missing-stage robustness guard, image-path UNCERTAIN check |
| `tracks/track-b/eval/kolam/synthetic/missing_stage/label.json` | Regenerated: two stages (C1.S3+C1.S4) omitted, coverage ~0.79 |
| `tracks/track-b/eval/kolam/synthetic/missing_stage/trace.json` | Regenerated: new synthetic trace with two stages absent |

Full diff: `git diff main -- tracks/common/tests/test_kolam_geometry.py tracks/track-a/tests/test_kolam_goal.py tracks/track-b/tests/test_kolam_eval.py tracks/track-b/eval/kolam/synthetic/missing_stage/`

</details>
