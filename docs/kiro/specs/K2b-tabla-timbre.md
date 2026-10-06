# K2b: Tabla stroke identity (expert-referenced timbre classes) + Flash-Lite bol labels + profile awareness

Read `docs/kiro/specs/00-COMMON.md` first. Folder `...\anveshan-wt\k2b-tabla`, branch `kiro/k2b-tabla`; created from `m1/hero-cases` **after K2 is merged**. **Needs the API key** (copy `.env`; it sets `ANVESHAN_AUDIO_MODEL=gemini-3.5-flash-lite`).

## Why
Tabla is currently scored on timing, tempo, steadiness and a binary bass/no-bass flag. That misses **which stroke** was played (Na, Tin and Ta ring differently; Ge and Ka are open versus muted bass).

We will learn 4–6 **timbre classes from the expert's own strokes**, with no labels and no fabrication, and score whether each learner stroke falls in the same class as the aligned expert stroke. Bol names from Gemini Flash-Lite are added only as **INFERRED display labels**; they never affect scores.

Measured on the goal window: Flash-Lite took 2.7 s and 445 tokens (≈ $0.0003) and returned 16 bols. Its 5.2 strokes/s agreed with our deterministic 5.28.

## Files you own
- `tracks/common/tabla_dsp.py`, `tracks/common/goals/tabla.py`
- `tracks/track-a/src/track_a/goals/tabla.py`, `tracks/track-b/src/track_b/evaluators/tabla.py`
- `tracks/common/prompts/tabla_bols_v1.txt` (moved there by K2) plus a new `tabla_bols_v2.txt`
- `tracks/cases/tabla/**`, `tracks/track-b/eval/tabla/**`
- the Tabla tests
- the Tabla section of `docs/plans/evaluation-core.md` (§5)

## Steps

### 1. Stroke features (`tabla_dsp.py`, numpy only)
Implement `stroke_features(x, sr, onset_times, window_sec=0.08) -> np.ndarray` of shape (n, 16):
- **13 MFCCs:** frame = window starting at the onset, Hann window, n_fft = 1024 (zero-pad the window), power spectrum; a mel filterbank of 40 triangular filters from 50 Hz to 7600 Hz (implement `mel_filterbank(sr, n_fft, n_mels, fmin, fmax)` with the HTK mel formula `2595*log10(1+f/700)`); log(power + 1e-10); DCT-II (orthonormal, implement with numpy). Keep coefficients 1..13 and drop coefficient 0, which is loudness.
- **Spectral centroid** (Hz, divided by 1000).
- **Low-band ratio** (< 250 Hz, same as onsets.py).
- **Decay ratio:** RMS of 40–80 ms divided by RMS of 0–40 ms after the onset. Ringing strokes (Na/Tin) decay slowly; muted ones (Ka/Ti) fast.

Test it on synthetic strokes: a ringing 300 Hz decaying sine vs a short noise burst must differ clearly in decay ratio and centroid.

### 2. Classes from the expert (`tabla_dsp.timbre_classes`)
`fit_timbre_classes(features, k_range=(3, 6), seed=0) -> TimbreModel` with fields `mean`, `std` (z-score from expert features), `centroids` (k×16), `k`, `silhouette`, `radius_p95` (95th percentile of each expert stroke's distance to its own centroid).
- **k-means:** deterministic farthest-point initialisation (start from the stroke closest to the global mean), at most 100 iterations, Euclidean distance on z-scored features.
- **Choose k** in 3..6 by maximum silhouette (implement silhouette in numpy; n ≈ 53, so O(n²) is fine). If the best silhouette is < 0.15, use **k = 2** (bass vs no-bass, matching the existing flag) and add a warning "timbre classes weakly separated".
- Implement `assign(model, features) -> (labels, distances)`. A stroke whose distance is greater than 1.5 × `radius_p95` gets label −1 ("unlike any expert stroke").

### 3. Goal model (`goals/tabla.py` payload and the Track A builder)
- Add optional payload fields with defaults, so the old v1 goal still validates:
  - `timbre: {k, mean, std, centroids, radius_p95, silhouette} | None`
  - per-onset `timbre_class: int | None`
  - `class_display: [{class: int, label: str, source: "deterministic"|"inferred"}]`
- Builder: compute features and classes from the goal window. Class display names are deterministic by default: "Class A".."Class F", ordered by descending low-band ratio, so A is the most bass-heavy.
- **Bol labels (Flash-Lite, optional):** if the audio model is enabled, call it with a v2 prompt (`tracks/common/prompts/tabla_bols_v2.txt`) asking for the **sequence of bols in order**, one per stroke, standard names, plus confidence; DTO `{bols: [str], confidence: "low"|"medium"|"high"}`.
  - Align the bol sequence to the expert onsets with `tabla_dsp.levenshtein`-style alignment (implement `align_sequences(a, b)` returning index pairs).
  - For each class take the majority bol, and set `class_display.label = f"Class A (mostly '{bol}', inferred)"` with `source="inferred"`.
  - Add a claim: "Stroke classes correspond mostly to bols … (inferred by audio model)", INFERRED, confidence 0.5, with the window interval.
  - ModelError → a warning, keeping deterministic labels.
- **New OBSERVED claim:** "The source uses k distinct stroke timbres (silhouette s)", with the window interval and confidence 1.0.
- **New criterion `CRIT-TABLA-STROKES`**, not required, weight 2: metric `tabla.stroke_class_accuracy`, higher is better, bands sat ≥ 0.80, partial ≥ 0.60. `why_it_matters` cites the new claim. Keep every other criterion unchanged.
- Rebuild the tabla case to **v2 artifacts**: keep v1 and add v2. With the audio model enabled this makes one Flash-Lite call, which is recorded. Promote that golden run into `tracks/cases/tabla/runs/golden/`.

### 4. Evaluator (`evaluators/tabla.py`)
- Compute learner stroke features and assign them with the goal's timbre model, using the goal mean/std.
- Over aligned pairs (the existing DTW alignment): `stroke_class_accuracy` = fraction where learner class == expert class. Learner −1 counts as wrong. If there are fewer than 8 aligned strokes, value=None with reason "too few aligned strokes".
- **Events:** first stroke-class mismatch → `DivergenceEvent(metric="tabla.stroke_class_accuracy", kind="stroke_mismatch", …)`, with the onset locator and a detail like "expected Class B (mostly 'Na', inferred), played Class D".
- **Artifacts:** add `expert_class` and `learner_class` per alignment row, plus `class_display`, for the UI.
- If the goal has no `timbre` (an old v1 goal), omit the metric. The criterion isn't in the v1 rubric, so nothing breaks.

### 5. Synthetic eval
Add a `stroke_substitution` variant to `make_synthetic.py`: replace 6 strokes with copies of expert strokes from a **different** class (splice 80 ms segments with a 5 ms crossfade). Ground truth: the substituted indices and the expected STROKES status (partial or not). Re-run `run_eval.py` on all variants. Every other criterion must keep its previous status; report any change. Update `RESULTS.md`.

### 6. Rhythm specialist reuse (for the universal pipeline; see `docs/plans/universal-pipeline.md` §3.3)
The universal engine (K7) reuses the Tabla engine as the **rhythm specialist** for any percussive audio. Make this clean:
- Add `payload_from_audio(path: Path, window: tuple[float, float] | None, ctx: RunContext | None = None) -> tuple[dict, dict]` to `tracks/common/goals/tabla.py`. It returns `(payload, built_with)` using the same deterministic code as the builder (timbre classes included). Bol labelling via the audio model happens **only** when `ctx` is given and the audio model is enabled. Refactor `track_a/goals/tabla.py:build` to call it, so there is one implementation. Hero output must stay byte-identical (test this against the committed v2 artifacts).
- `track_b/evaluators/tabla.py:evaluate` must work on a GoalModel whose payload came from `payload_from_audio` on an arbitrary percussive clip: no assumptions about tabla-specific labels, and the timbre fields are optional. Add a test with a synthetic hand-clap track (noise bursts) as the goal and a jittered copy as the attempt.
- Neutral wording in metric findings: use "bass (low-frequency) strokes" and "stroke class"; never say "bayan" or "bol" unless `class_display` labels came from the audio model.

## Tests
- features and MFCC sanity;
- k-means determinism (same input → same labels) and the k = 2 fallback on weakly separated data;
- `assign` returns −1 for an outlier;
- the evaluator metric on a perfect copy is ≥ 0.95, and on the substitution variant matches the ground truth;
- bol alignment / majority labelling with a fake gateway;
- the ModelError fallback;
- hero byte-identity after the `payload_from_audio` refactor;
- the evaluator on a generic hand-clap goal works, with neutral wording.

## Acceptance
- v2 tabla artifacts plus the golden Flash-Lite run are committed and reproduce in recorded mode.
- The eval shows the new variant detected and no regressions.
- The Definition of Done in 00-COMMON.md is met. Report: `docs/kiro/reports/K2b-REPORT.md`, with the classes found (k, silhouette, class display labels) and the cost of the Flash-Lite call.
