# Track B Replay Case 001: Sikku Kolam Multimodal Video Replay

**Skill:** `sikku-kolam-symmetry` (Sikku Kolam 3x3 Continuous Loop Mastery)  
**Modality:** Multimodal Video (`video` with audio cues & timestamp locators)  
**Expert Source:** Meenakshi Ammal (`expert-meenakshi`, `expert_kolam_master.mp4`)  
**Learner:** Akash (`learner-akash`, `att-kolam-baseline-001` and `att-kolam-retry-002`)

## Contract Artifacts

This replay case contains all 8 shared seam contracts required for independent Track B evaluation and replay:

1. `knowledge_package.json`: Structured expert demonstration claims (`CLM-01` to `CLM-03`) with video timestamp evidence.
2. `rubric.json`: Observable rubric definition with 3 criteria:
   - `C01`: Dot Grid Setup (Weight: 20.0, Required: True)
   - `C02`: Continuous Loop Enclosure (Weight: 40.0, Required: True)
   - `C03`: Bilateral Symmetry (Weight: 40.0, Required: False)
   - Passing threshold: 75.0 / 100.0
3. `practice_task.json`: Assignment instructions and 60-second execution constraints.
4. `baseline_attempt.json`: Baseline Attempt #1 (`attempt_type: baseline`, `attempt_number: 1`).
5. `baseline_evaluation.json`: Criterion-level grading (Total: 45.0, Passed: False, C02 not satisfied).
6. `feedback.json`: Grounded coaching linking to `C02` (Dot #4 intersection) and `C03` (arc asymmetry).
7. `retry_attempt.json`: Post-coaching Retry Attempt #2 (`attempt_type: retry`, `attempt_number: 2`).
8. `retry_evaluation.json`: Re-evaluation on identical rubric (Total: 95.0, Passed: True, C02 & C03 satisfied).
9. `transmission_record.json`: Deterministic transmission proof ($\Delta \text{Gain} = 95.0 - 45.0 = 50.0$).
10. `bundle.json`: Unified bundle for single-file validator execution.

## Verification

Validate this fixture with the universal validator:
```bash
python -m tracks.common.validator tracks/track-b/fixtures/replay/case-001/ --bundle
```
