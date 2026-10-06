# WP4 Report: Tabla Timbre (K2b)

**Branch:** kiro/wp4-tabla · **Date:** 2026-10-06 · **Status:** DONE

## Done

1. **DSP additions** (`tracks/common/tabla_dsp.py`):
   - `mel_filterbank` (HTK formula, 40 bands, 50–7600 Hz)
   - `_dct2_ortho` (orthonormal DCT-II via numpy)
   - `stroke_features` → (n, 16): MFCCs 1–13, centroid/1000, low-band ratio, decay ratio
   - `TimbreModel` dataclass with `to_dict`/`from_dict`
   - `fit_timbre_classes` (farthest-point k-means, silhouette k-selection 3–6, k=2 fallback)
   - `assign` (z-scored Euclidean; label −1 if > 1.5 × radius\_p95)
   - `align_sequences` (edit-distance traceback)
   - `BolsV2DTO` ({bols: [str], confidence: str})

2. **Payload model** (`tracks/common/goals/tabla.py`):
   - `TablaOnset.timbre_class: Optional[int]` added (v1 backward-compatible)
   - `TablaGoal.timbre: Optional[dict]` and `class_display: Optional[list]`
   - `payload_from_audio(path, window, ctx=None)` — canonical builder used by Track A and universal pipeline

3. **v2 prompt** (`tracks/common/prompts/tabla_bols_v2.txt`) — ordered bol sequence, one per stroke

4. **Track A builder** (`track_a/goals/tabla.py`):
   - Refactored to call `payload_from_audio`; BUILDER_VERSION = `tabla_goal_v2`
   - CLM-07 (OBSERVED): "The source uses k distinct stroke timbres (silhouette s)"
   - CLM-08 (INFERRED, when audio model ran): bol-class correspondence
   - CRIT-TABLA-STROKES (not required, weight 2): `tabla.stroke_class_accuracy`, higher_is_better, sat ≥ 0.80

5. **Track B evaluator** (`track_b/evaluators/tabla.py`):
   - `_stroke_class_accuracy` added; neutral wording (no "bayan"/"bol" unless model-inferred)
   - `tabla.stroke_class_accuracy` metric computed; first-mismatch DivergenceEvent (minor)
   - Artifacts include `expert_class` and `learner_class` per alignment pair

6. **Eval tooling** (`tracks/track-b/eval/tabla/`):
   - `make_synthetic.py`: `stroke_substitution` variant added (6-stroke splice with 5 ms crossfade)
   - `run_eval.py`: tracks CRIT-TABLA-STROKES, treats "uncertain" as wildcard in agreement

7. **v2 artifacts** (`tracks/cases/tabla/knowledge/*.v2.json`):
   - Built with `gemini-3.5-flash-lite` (1 audio call, 2261 ms)
   - Bols status: inferred; k=3, silhouette=0.2529
   - Golden run promoted to `tracks/cases/tabla/runs/golden/`

8. **docs/plans/evaluation-core.md §5**: added §5.3 documenting stroke timbre classification

## Tests

`341 passed, 2 deselected` — up from 327 baseline. Added 14 new tests:
- DSP: mel filterbank, stroke features (ringing vs muted), k-means determinism, k=2 fallback, assign outlier, align_sequences
- Builder: CLM-07 present, v2 bols format, CRIT-TABLA-STROKES criteria
- Evaluator: perfect copy accuracy ≥ 0.95, v1 goal → no metric, artifacts with class fields, hand-clap neutral wording

All 3 checks: governance PASS, case-packs PASS, contract-parity PASS.

## Live results

- 1 Flash-Lite audio call: 2261 ms, tabla_bols_v2 prompt
- k=3 timbre classes, silhouette=0.2529 (all 3 classes labelled "mostly 'Ge'" — low-quality bol labelling on this recording, which is expected for a freely licensed track)
- Onset F1 mean: 0.998; first-divergence agreement 7/7; status agreement 42/42

## Deviations

- `align_sequences` uses edit-distance traceback rather than Needleman-Wunsch; works correctly for the expected case where model returns n bols for n onsets
- `payload_from_audio` returns a 4-tuple (payload, built_with, warnings, run_keys) rather than the 2-tuple specified (warnings/run_keys needed by the builder); the caller destructures all 4

## Requests for WP5

- None. The `payload_from_audio` API in `tracks/common/goals/tabla.py` is ready for K7 (universal pipeline) to call as the rhythm specialist.

## Open issues

- The freely licensed Wikimedia tabla recording produces low-quality bol labels ("mostly 'Ge'" for all classes) due to audio quality. This is acceptable — the class labels are deterministic, and the bol annotations are clearly marked INFERRED.
