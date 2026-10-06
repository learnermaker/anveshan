# Experiment Log

**Status:** experimental record. Planned experiments must not be described as results.

## Experiment Record Template

### Experiment
Name:

### Date
YYYY-MM-DD

### Hypothesis
What do we believe will be true?

### Candidate Thesis
Which product phenomenon is being tested? Use the current competition/MVP thesis unless the experiment is explicitly marked exploratory.

### Input
What real source material, benchmark case or self-declared data was used?

### Dataset / Case IDs
List exact cases.

### Model / Version
Exact model name and release stage.

### Prompt Version
Repository prompt path + version.

### Configuration
Sampling/temperature if applicable, tools, video mode, context limits and other material settings.

### Quota Budget
Maximum intended model calls and media-processing budget.

### Procedure
What was tested?

### Expected Result
What would support the hypothesis?

### Actual Result
What happened?

### Metrics
Relevant quantitative measures.

### Human Evaluation
Who evaluated it, blind/unblind status where relevant, rubric, and adjudication method.

### Evidence
Links/paths to outputs, screenshots, recordings, run summaries and commits.

### Failure Categories
Record extraction error, evidence error, evaluation error, uncertainty failure, latency/quota failure, etc.

### Finding
- validated
- partially validated
- invalidated
- inconclusive.

### Decision
What changes as a result?

### Follow-up
What must be tested next?

---

## E1 — Kolam goal-conditioned path validation (synthetic)

### Date
2026-10-06

### Hypothesis
A deterministic geometry-based evaluator can correctly classify 10 synthetic trace and image
attempts against a single Kolam goal model without model calls.

### Input
SYNTHETIC perturbations of the goal line (seeded RNG). No real learner data. No photos of
human-drawn kolams (only SYNTHETIC rasters derived from the goal geometry).

### Dataset / Case IDs
`tracks/cases/kolam` (K1 golden run, K1 evaluation script, synthetic attempts in
`tracks/track-b/eval/kolam/synthetic/`).

### Model / Version
No model. Kolam evaluator is deterministic (geometry only).

### Prompt Version
Not applicable.

### Configuration
Recorded mode (no API key required).

### Quota Budget
0 model calls.

### Procedure
10 synthetic attempts (6 trace, 4 raster image) evaluated by `track_b.evaluators.kolam.evaluate`
against the built goal model. Ground truth is exact by construction from perturbation scripts.

### Actual Result
- Criterion status agreement: **50/50** (100%)
- First-divergence agreement: **10/10** (100%)
- Photo-path registration: 3/3 raster attempts correctly registered (scale + rotation)
- Process criteria (`CRIT-KOLAM-CONTINUITY`) are `uncertain` for all raster attempts by design

### Metrics

| Metric | Value |
|---|---|
| Criterion status agreement | 50/50 (100%) |
| First-divergence agreement | 10/10 (100%) |
| Photo-path registration (3 rasters) | 3/3 |

### Human Evaluation
None. Ground truth is computed from exact perturbation parameters.

### Evidence
`tracks/track-b/eval/kolam/RESULTS.md` · commit `3d7888a` (branch `kiro/k1-kolam`)

### Finding
**Engineering validation.** The evaluator correctly classifies synthetic perturbations with
exact ground truth. No human-drawn attempts evaluated; no human-learner improvement measured.

### Decision
Kolam evaluator is IMPLEMENTED and deterministically correct on synthetic data. Real
learner data collection is deferred (not MVP scope).

---

## E2 — Tabla synthetic evaluation and timbre classification

### Date
2026-10-06

### Hypothesis
The tabla evaluator (onset detection + timbre MFCC classes) correctly measures tempo, timing,
bass accuracy, and stroke-class accuracy on synthetic perturbations of a recorded tabla window.

### Input
Real tabla recording: `src.tabla.demo.v1` (Wikimedia, CC-licensed, freely licensed track from
Yavagal performer). 7 SYNTHETIC perturbations of the 12-second goal window. 1 live Flash-Lite
audio call for bol labels.

### Dataset / Case IDs
`tracks/cases/tabla` (WP4/K2b golden run).

### Model / Version
`gemini-3.5-flash-lite` (Google AI Studio) for bol labels only. All scoring is deterministic.

### Prompt Version
`tracks/common/prompts/tabla_bols_v2.txt`

### Configuration
1 live audio call (bol labels). Timbre classification: k=3 clusters, silhouette=0.2529.

### Quota Budget
1 model call; < $0.001.

### Procedure
7 synthetic attempts evaluated. Bol labels are INFERRED and do not affect scores.

### Actual Result
- Onset F1 mean over 7 attempts: **0.999** (min 0.991)
- Criterion status agreement: **49/49** (100%)
- First-divergence agreement: **7/7** (100%)
- Bol quality: all 3 timbre classes labelled "mostly Ge" (low quality — expected for this
  freely-licensed recording)

### Metrics

| Metric | Value |
|---|---|
| Onset F1 (mean) | 0.999 |
| Criterion status agreement | 49/49 (100%) |
| First-divergence agreement | 7/7 (100%) |
| Timbre classes | k=3, silhouette=0.2529 |

### Human Evaluation
None. Ground truth is exact by construction.

### Evidence
`tracks/track-b/eval/tabla/RESULTS.md` · commit `5a85be6` (branch `kiro/wp4-tabla`)

### Finding
**Engineering validation.** Deterministic scoring is accurate on synthetic data. Bol labels
are correctly marked INFERRED and do not affect criterion statuses. No real learner attempts
or human judges involved.

### Decision
Tabla evaluator is IMPLEMENTED. Bol labelling is a low-confidence enrichment, not a score
input.

---

## E3 — Origami goal build and synthetic evaluation

### Date
2026-10-06

### Hypothesis
The origami goal builder can extract a valid state sequence from a demonstration video and the
evaluator can distinguish attempt quality on synthetic video variants.

### Input
Real origami crane demonstration video: `OrigamiCrane.ogv` (~25 MB, Wikimedia CC).
5 SYNTHETIC video attempts. 25 live Flash-Lite calls (goal build) + 65 evaluator calls.

### Dataset / Case IDs
`tracks/cases/origami` (K4 golden run).

### Model / Version
`gemini-4-26b-a4b-it` (Gemma local API) replaced by `gemini-3.5-flash-lite` for K4 live runs.

### Prompt Version
`origami_states_v3.txt`, `origami_match_v2.txt`, `origami_final_v1.txt`

### Configuration
FPS=0.5, BATCH_SIZE=4, inter_batch_sleep=12 s to manage rate limits.

### Quota Budget
25 goal-build calls + 65 evaluator calls. < 100 total.

### Procedure
Live goal build (5 states from 194 s video). 5 synthetic attempt variants evaluated.

### Actual Result
Goal model: **5 states** (R0–R4, 7-state expert labels). Missing: R5 (petal fold), R6 (bird base).
`CRIT-ORI-FINAL` = `partially_satisfied` on all attempts (goal incomplete, final_match ≤ 0.5).
`CRIT-ORI-KEYSTEP` = `not_satisfied` (key state = R1 which is brief and poorly bounded).

### Metrics

| Metric | Value |
|---|---|
| States extracted | 5 / 7 (expert) |
| Build latency (25 calls) | ~160 s total |
| Attempt eval latency (13 calls/variant) | ~3 min / variant |
| frame_state_accuracy (5-state goal vs 7-state labels) | 10.5% — baseline |

### Human Evaluation
Expert label comparison (7 states, manually annotated). Build disagreements on R1, R5, R6.

### Evidence
`tracks/track-b/eval/origami/RESULTS.md` · `docs/kiro/reports/K4-REPORT.md` · commit range on `kiro/k4-origami`

### Finding
**Engineering validation, partial.** The evaluator is technically functional. The goal model
is incomplete (missing 2 of 7 states including the critical petal fold). No real learner
attempts evaluated. Human-learner improvement is NOT measured.

### Known issues
- R5 (petal fold) and R6 (bird base) not detected
- R1 boundary severely off (40–42 s built vs 8–28 s labeled)
- flash-lite model at lower latency than Gemma; full video at FPS=1.0 would improve coverage

---

## E4 — Universal pipeline live checks

### Date
2026-10-06

### Hypothesis
The universal composer pipeline can perceive, propose, and evaluate arbitrary image and video
skills without specialist knowledge about the specific skill.

### Input
1. `kolam_8_mayoo.png` (real Kolam photograph, dark background, Wikimedia CC)
2. Half-erased version (right half whitened, synthetic)
3. Synthetic gradient image (solid gradient, unrelated)
4. Synthetic rangoli PNG (Pillow-generated line drawing, novel skill)
5. `tabla_chanderi_1.webm` (real tabla video, Wikimedia CC)
6. `tabla_chanderi_2.webm` (different performance, same skill)

### Dataset / Case IDs
`var/kiro/media/kolam/`, `var/kiro/media/tabla/`

### Model / Version
`gemini-3.5-flash-lite` (vision_fast) + `gemini-embedding-2` (embedding)

### Prompt Version
`perceive_image_v1.txt`, `perceive_audio_v1.txt`, `structure_skill_v1.txt`, `judge_final_v1.txt`

### Configuration
Live mode. Recorded results saved to `var/runs/wp5_live_checks/results.json` (gitignored).

### Quota Budget
≤ 30 model calls for WP5 step 3 checks.

### Procedure
For each source: compose (perceive + propose + build), then evaluate 1–2 attempts.

### Actual Result

| Check | Status | Notes |
|---|---|---|
| kolam compose | BUILT | structures=['final_state'], ~6 s |
| kolam: same image | PASS | similarity=1.00, property=1.00 |
| kolam: half-erased | PASS | similarity=0.96 (lower, expected) |
| kolam: gradient | REFUSED | blur_score=0.0 < 0.002 (quality gate) |
| rangoli compose | BUILT | structures=['final_state'], ~5 s |
| rangoli: cropped learner | PASS | similarity=0.98 |
| tabla_chanderi compose | BUILT | structures=['procedure','temporal_pattern'], ~20 s |
| tabla_chanderi: chanderi_2 | PASS | step_coverage=0.00 (different performance, expected) |

### Metrics

| Metric | Value |
|---|---|
| Kolam same-image similarity | 1.00 |
| Kolam half-erased similarity | 0.96 |
| Rangoli learner similarity | 0.98 |
| Perceived compose latency (image) | ~6 s |
| Perceived compose latency (video) | ~20 s |

### Human Evaluation
None. Similarity thresholds are deterministic. Property judgements are AI-generated
(marked AI-JUDGED in the evaluator).

### Evidence
`tools/live_checks_wp5.py` · `var/runs/wp5_live_checks/results.json` (gitignored, local run)

### Finding
**Engineering / capability validation.** The universal pipeline composes and evaluates novel
image skills without skill-specific code. Video skills are composed but step alignment is weak
when two performances differ substantially.

No human-learner data was used. No human judges were involved. This is engineering evidence
on internet and synthetic data only.

### Decision
Universal pipeline is IMPLEMENTED. The `min_similarity` and quality gate thresholds have been
calibrated (see `docs/plans/universal-pipeline.md` §11).

---

## E5 — Model latency probe

### Date
2026-10-06

### Hypothesis
`gemini-3.5-flash-lite` satisfies the latency budget (case build < 45 s, attempt < 30 s).

### Input
Real media from `var/kiro/media/` and `var/scratch/media/`.

### Actual Result

| Operation | Model | Calls | Elapsed |
|---|---|---|---|
| Kolam image perceive | vision_fast + embedding | 2 | ~6 s |
| Kolam universal evaluate | vision_fast + embedding | 2–3 | ~5–6 s |
| Rangoli image perceive | vision_fast + embedding | 2 | ~5 s |
| Tabla audio 12 s (build) | audio | 1 | 2.3 s |
| Origami goal build (25 calls) | vision_fast | 25 | ~160 s total (~6 s/call) |
| Tabla chanderi video compose | vision_fast + embedding + audio | 3–5 | ~20 s |

Gemma latency (K1 run): 13 805 ms for a single image call. K4 replaced Gemma with Flash-Lite
giving 2–7 s per image call.

### Finding
**Capability evidence.** Flash-Lite meets the per-call latency budget. Origami goal builds
exceed 45 s total due to the number of calls (25 batches at FPS=0.5). A single attempt
evaluation is well within budget.

---

## Current Planned Experiments — Transmission Thesis

These experiments validate the current competition/MVP wedge defined in `docs/product/product-thesis.md` and bounded by `docs/product/mvp-contract.md`.

1. Authentic expert demonstration → structured knowledge extraction.
2. Ten difficult evidence-grounding questions.
3. Expert review of knowledge fidelity.
4. Source-grounded teaching and practice-task generation.
5. Learner baseline attempt.
6. Learner attempt evaluation against a skill-specific rubric.
7. Evidence-grounded feedback.
8. Learner retry and measurable improvement.
9. End-to-end transmission record and lineage.
10. Short demo comprehension.

### Exploratory state/action/outcome work

The repository also contains research on state → action → outcome, first divergence, recovery, intervention verification, demonstration compilation, and related physical-world intelligence concepts.

Those experiments are **research-only** unless an explicit product decision promotes them into the current thesis. They must not be treated as active MVP scope or as a reason to rewrite the current transmission validation plan.

## Evidence Rule

A plan is not a result. A prototype feature is not validated unless an experiment produces evidence.

## Promotion Rule

A research experiment may change the current product direction only when:
1. the result is recorded with reproducible evidence;
2. the product implications are documented;
3. direct competitive overlap is rechecked;
4. the relevant product/architecture decision is explicitly updated in a canonical document or ADR.
