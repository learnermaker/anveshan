# K1 Step 5: end-to-end session test for the kolam evaluator

`tracks/track-b/tests/test_kolam_session_e2e.py` — two tests, both in RECORDED mode, no API key required.

The test exercises the full Track B session lifecycle for the kolam case using committed synthetic fixtures. Flow A covers the primary success path: stray-stroke baseline → perfect-trace retry → `complete_session`, validating the transmission bundle, checking a positive gain, and asserting that `targeted_change` reflects the CONTINUITY criterion improving. Flow B covers the image-modality path: same baseline, raster-image retry, confirming that process criteria are marked `uncertain` and `process_observable` is `False`.

Watch for: *(confirmed)* the RECORDED mode claim rests on the kolam evaluator being fully deterministic — if any future evaluator change introduced a model call, the test would pass incorrectly without needing real golden runs in `data_dir`; the golden run files committed to `tracks/cases/kolam/runs/golden/` serve the Track A build path, not Track B evaluation.

**Verdict**: APPROVED

---

## High-level view

The two tests map precisely to the two sub-requirements in the K1 Step 5 spec. The fixture inputs are grounded against committed `label.json` files: `stray_stroke/label.json` records `CRIT-KOLAM-CONTINUITY: partially_satisfied`, `perfect/label.json` records `satisfied`, and `raster_perfect/label.json` records `uncertain` with `process_observable: false`. Every hardcoded string in the assertions (`"partially_satisfied"`, `"satisfied"`, `"uncertain"`, `"CRIT-KOLAM-CONTINUITY"`) is independently verifiable against those files, so the test is self-evidencing rather than just asserting a value the evaluator happened to produce.

The RECORDED mode choice is correct but carries a latent assumption: the kolam evaluator makes no model calls, so `RunContext("recorded")` acts solely as a live-call guard. The test runs against the real handoff artifacts (`knowledge/`, `practice/`) committed to `tracks/cases/kolam/`, not against the golden run files in `runs/golden/`. The golden runs are consumed only by the Track A `build_case` path and are irrelevant to Track B evaluation.

`test_image_retry_process_criteria_uncertain` stops after the retry result and does not call `complete_session`. The spec only requires confirming that process criteria are `uncertain` on the image path; the spec does not mandate a full session cycle for Flow B. The test satisfies the requirement as stated.

The `tracks/common/schemas/` directory is untouched on the branch — confirmed by `git diff main..kiro/k1-kolam -- tracks/common/schemas/` producing no output.

---

<details>
<summary>Issues (0)</summary>

No blocking or advisory findings.

</details>

---

<details>
<summary>Details</summary>

## Spec requirement coverage

The spec lists five observable outcomes for the e2e test. Each is confirmed:

| Spec requirement | Where asserted | Evidence |
|---|---|---|
| `validate_transmission_bundle` passes | `test_trace_stray_then_perfect` L74–75 | `CriterionStatus` enum values and all 9 required bundle keys validated by the full cross-contract checker |
| `transmission_gain > 0` | L79 | `TransmissionRecord.transmission_gain` is a schema-validated field with a `@model_validator` enforcing `retry_score − baseline_score`; since perfect trace scores higher than stray-stroke, gain is positive by construction |
| `targeted_change` shows first-divergence criterion improved | L84–98 | `criterion_id == "CRIT-KOLAM-CONTINUITY"`, `before == "partially_satisfied"`, `after == "satisfied"`, `improved is True` |
| Image-path retry → UNCERTAIN process criteria | `test_image_retry_process_criteria_uncertain` L138–151 | `process_observable is False`, `CRIT-KOLAM-CONTINUITY status == "uncertain"`, `kolam.pen_lifts_excess value is None` and `uncertain_reason is not None` |
| RECORDED mode, no API key or live call | `_ctx(case_dir, data_dir)` with `"recorded"` | Kolam evaluator is deterministic; `RunContext("recorded")` blocks any live call that might be added later |

## Fixture grounding

The hardcoded criterion IDs, statuses, and first-divergence assertions are directly backed by committed label files:

- `stray_stroke/label.json`: `CRIT-KOLAM-CONTINUITY: partially_satisfied`, `expected_first_divergence.kind: off_path_ink` — matches `tc["before"]` and `fd["criterion_id"]` assertions.
- `perfect/label.json`: `CRIT-KOLAM-CONTINUITY: satisfied`, `expected_first_divergence: null` — matches `tc["after"]` and the `r_json["first_divergence"] is None` assertion.
- `raster_perfect/label.json`: `CRIT-KOLAM-CONTINUITY: uncertain`, `process_observable: false` — matches the image-path assertions exactly.

The `PROCESS_CRITERIA = {"CRIT-KOLAM-CONTINUITY"}` constant is correct: it is the only criterion marked `uncertain` in the raster_perfect fixture (COVERAGE, CURVES, DOTS, and PRECISION are all `satisfied` from the image path).

## RECORDED mode assumption

The test comment is accurate: the kolam evaluator runs on pure geometry (numpy/Pillow, no `ModelGateway` calls), so `RunContext` mode does not affect evaluation output — it only prevents accidental live calls. The committed golden runs in `tracks/cases/kolam/runs/golden/9b4f8eee473f4e3cb168c2bb93bfcfd2/` are for the Track A `build_case` path (one Gemma image call) and are not read during Track B session evaluation. The test correctly relies on `tracks/cases/kolam/knowledge/*.v1.json` and `practice/*.v1.json` which are committed artifacts.

## Session state machine traversal

Both tests traverse the state machine correctly. After the stray-stroke baseline, `record_attempt` transitions to `FEEDBACK_READY` (not `BASELINE_EVALUATED`) because `submit_attempt` always generates feedback for a baseline. `require_can_submit` only blocks `BASELINE_EVALUATED` and `COMPLETED`, so the retry proceeds without error. Flow A reaches `RETRY_EVALUATED` before `complete_session`, which requires exactly that state with at least two attempts.

## Test coverage shape

The test covers: baseline-only flow (implicitly, through assertions on `b_res`), full baseline-to-retry cycle with transmission validation, and image-modality observability gap. Not covered: a retry that still fails (no-gain case), `complete_session` called on an image-retry session, and multiple retries. These are not required by the K1 spec and are out of scope.

## Pytest evidence

From K1-REPORT.md Step 5 section:
```
tracks/track-b/tests/test_kolam_session_e2e.py::test_trace_stray_then_perfect PASSED [ 50%]
tracks/track-b/tests/test_kolam_session_e2e.py::test_image_retry_process_criteria_uncertain PASSED [100%]
================== 2 passed in 15.25s ==================
```
Platform: win32, Python 3.13.14, pytest 9.1.1.

</details>

---

<details>
<summary>File map</summary>

| File | Change |
|---|---|
| `tracks/track-b/tests/test_kolam_session_e2e.py` | New: 166-line e2e session test, two test functions |

The diff is entirely new file addition (commit `3d7888a`). The subsequent commit `e5e6cac` only adds the Step 5 section to `docs/kiro/reports/K1-REPORT.md`.

Schemas unchanged: `git diff main..kiro/k1-kolam -- tracks/common/schemas/` produces no output.

</details>
