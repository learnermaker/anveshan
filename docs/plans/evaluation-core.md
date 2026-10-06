# Evaluation Core — Goal-Trajectory Verification

**Date:** 2026-10-06 · **Status:** DECIDED for the hackathon build (Jim, 2026-10-06). It supersedes the "references" and "observers" details in the track specs wherever the two differ.

## 1. Why evaluation is the core

Anveshan claims that knowledge **moved** from a source to a learner. Everything else (extraction, teaching, lineage) exists to make that claim checkable. A final score cannot carry the claim. The evaluator has to answer four questions, and answer them with evidence:

1. **Did the learner reach the goal?** (outcome)
2. **Were the learner's actions on a path that reaches the goal?** (process)
3. **Where exactly did they first leave that path, and why does that matter according to the source?** (first divergence, grounded)
4. **After the intervention, did that specific deficiency change?** (targeted transmission, not just a higher total)

All four need a model of the **goal** and a model of the learner's **trajectory**. The source's job is to define the goal. The evaluator's job is to compare trajectories against it.

The design generalises the user's Kolam insight: *start from the final state, work backward to the set of action sequences that can produce it, then check whether the learner's actions stay inside that set.*

## 2. The model

```
GoalModel (from Track A, per case)          Attempt trajectory (from Track B, per attempt)
  features F = {f_i, weight, locator}         states S_0 … S_T  (derived from learner actions/media)
  constraints C (violations → off-path)       actions a_1 … a_T  (strokes / frames / beats)
  order O (partial order; may be inferred)
  goal state G = all features achieved
```

For each state `S_t` the evaluator computes:

| Quantity | Meaning |
|---|---|
| `coverage(S_t)` | weighted fraction of goal features achieved so far (**progress toward the goal**) |
| `violations(S_t)` | constraint violations introduced by `a_t` (**off the path**: the goal is no longer reachable from S_t without undoing work) |
| `precision(S_t)` | fraction of the learner's work that belongs to the goal |
| `order_consistency` | agreement between the order features were achieved and O (reported; scored only when O is source-established) |

Derived results:

| Result | Definition |
|---|---|
| **Outcome** | `coverage(S_T)`, `precision(S_T)`, final-state match |
| **First divergence** | the smallest `t` with a material violation. If there is none: the first goal feature never achieved, in O order. If evidence cannot establish it: none (UNCERTAIN). |
| **Progress curve** | `coverage(t)` with divergence markers. This is the signature visual: baseline and retry curves overlaid. |
| **Targeted change** | whether the first-divergence criterion at baseline changed status at retry. Reported separately from total gain. |

These metrics feed the rubric through `practice/observers.vN.json`. Scores come only from the deterministic band → status → score policy. The model never produces a score.

**Contract mapping (no changes to the eight contracts):**

| Concept | Where it lives |
|---|---|
| goal features | `KnowledgeClaim`s with locators |
| constraints and metrics | `RubricCriterion` + observers |
| per-criterion outcome | `CriterionResult` (finding with numbers + an evidence locator for the stroke, onset or frame) |
| curves and trajectories | view model + run artifacts |

The GoalModel itself is case data: `knowledge/goal_model.vN.json`, with its schema in `tracks/cases/schemas/`.

## 3. Kolam: final image only (goal-conditioned)

### 3.1 Backward interpolation (Track A, deterministic + Gemma)

The only input is the finished kolam image.

1. **Normalise:** grayscale, auto-polarity (ink = foreground), Otsu threshold, resize so the longest side is 512 px.
2. **Stroke width** `w`: from the distance transform sampled on the skeleton.
3. **Pulli (dots):** distance-transform maxima wider than about 1.6 × the line half-width, plus isolated small round components. The output is dot centres and radii, so dots that lie on lines are detected too.
4. **Line skeleton:** the ink with dot disks removed, then Zhang–Suen thinning (numpy).
5. **Skeleton graph:** junctions (degree ≥ 3), endpoints, and the pixel chains between them.
6. **Smooth-continuation decomposition:** at every crossing, pair the incident branches by minimum turning angle. Kolam lines cross transversally, so this recovers the **continuous curves** an artist could draw without lifting the hand. The result is K curves (usually closed loops), each an ordered polyline. This is the **inferred drawing path**: claims are `INFERRED`, confidence ≤ 0.5, direction and start point are arbitrary but deterministic (clockwise, starting at the topmost point).
7. **Dot relation:** for each dot, `on_line` (a curve passes through it) or `enclosed` (a curve goes around it). Computed, therefore `OBSERVED`.
8. **Symmetry:** rotational order n ∈ 2…12 and mirror axes, from ink IoU under rotation/reflection about the dot centroid. Computed, therefore `OBSERVED`.
9. **Gemma** (`gemma-4-26b-a4b-it`, image input) adds: a plain description, motif naming **only as uncertain**, a sanity check of K and n against the computed values (disagreement → warning, never an override), and learner-facing instructions for each curve built from the computed geometry. It never asserts the artist, order, meaning or tradition.

**GoalModel payload:** canvas size, dots, curves (polylines in image pixels), `w`, the tolerance band `τ = max(6 px, 1.5·w)`, dot relations, symmetry, and features. Features are the skeleton samples every 4 px, each tagged with its curve and nearest dot.

**Held-out validation:** the author's arrow diagram (`Ithayakkamalam - 1.jpg`) is never given to the system. It is used only to score the inferred decomposition (curve count, route agreement), and the result is recorded as an experiment.

### 3.2 Learner evaluation (Track B)

**Primary input: drawing on the canvas.** The app renders the detected dots at goal coordinates and records timed strokes. At each stroke prefix:

| Metric | Definition |
|---|---|
| `coverage` | goal skeleton samples within τ of learner ink |
| `precision` | learner ink samples within τ of the goal skeleton |
| off-path segments | runs of learner points outside τ longer than 2τ. Each is a violation (in a real kolam, stray powder stays). The locator is `#stroke=k` plus the time. |
| dot-relation errors | for dots in covered regions, the learner's on_line/enclosed relation ≠ the goal's |
| curve completion | each curve's coverage ≥ 0.9 |
| continuity | pen lifts vs K (process efficiency) |
| order | the order curves were completed. Reported, **not scored**, because the image does not establish the original order. |

**Secondary input: photo upload.** Detect ink and dots, register to the goal with a similarity transform (dot centroid, RMS scale, rotation search maximising ink IoU), then compute the final-state metrics. Process criteria (continuity, first divergence in time) are **UNCERTAIN: "process not observable from a final photo"**. This is the same evidence boundary Track A respects for target images.

**Default rubric** (the template Track A generates from the GoalModel; approved by Jim):

| Criterion | Required | Weight | Bands |
|---|---|---|---|
| `CRIT-KOLAM-COVERAGE`: every curve of the target is drawn | ✓ | 3 | ≥ 0.90 sat · ≥ 0.70 partial |
| `CRIT-KOLAM-PRECISION`: no stray lines off the pattern | ✓ | 2 | ≥ 0.92 sat · ≥ 0.80 partial |
| `CRIT-KOLAM-DOTS`: each pulli kept in the same relation to the line | ✓ | 2 | ≥ 0.95 sat · ≥ 0.80 partial |
| `CRIT-KOLAM-CURVES`: each continuous curve completed | | 2 | all sat · K−1 partial |
| `CRIT-KOLAM-CONTINUITY`: drawn as continuous strokes | | 1 | lifts ≤ K+1 sat · ≤ 2K partial |

Bands are calibrated on the synthetic + hand-drawn set (§7) and versioned in the observers file.

## 4. Origami: video (forward; the full-multimodal case)

### 4.1 Goal model from the expert video (Track A)

1. PyAV decodes frames at 1 fps over the skill window (crane up to the bird base; the window is set in the case config) and downsizes them to 384 px.
2. Gemma, over batches of ≤ 12 timestamped frames, identifies the **paper states**. Each state has a short name, the visible properties that define it, and its first/last time.
3. Deterministic merging produces ordered states R_0 … R_k, each with a keyframe (the stablest frame), an interval and properties.
4. Keyframes are stored as small JPEGs in the case pack (CC BY 3.0 attribution). Claims (`STEP`, `OBSERVED` with the keyframe interval) come from the states. Gemma-described "how to do the fold" text stays `INFERRED`.
5. The order O is **source-established** (the expert performed it), so it is scored.

### 4.2 Learner evaluation (Track B)

1. PyAV decodes learner frames at 1 fps (≤ 90). Frames are sent as images, never as a video file; Gemma rejects videos that carry audio.
2. Gemma receives the reference keyframes R_0…R_k plus batches of learner frames. For each learner frame it returns `{state: j | "transition" | "off_path" | "unclear", note}`.
3. Deterministic trajectory:
   - mode-filter the labels (window 3);
   - `progress(t)` = max state reached so far / k;
   - **violations:** `off_path` for ≥ 2 consecutive frames, or a regression of ≥ 2 states for ≥ 2 frames;
   - **skipped states:** a jump of more than 1. If frames around the jump are sparse or unclear, the skip is UNCERTAIN ("not visible"), not "missing";
   - **final match:** the last stable state is k, plus a Gemma pairwise check of the final frame against R_k (using the checklist of the state's properties).
4. First divergence = the first violation, or the first missing state, with the learner timestamp. The expert keyframe of the expected state is the reference evidence.

**Default rubric:**

| Criterion | Required | Weight |
|---|---|---|
| `CRIT-ORI-FINAL`: reaches the target form (bird base) | ✓ | 3 |
| `CRIT-ORI-ORDER`: folds in the demonstrated order | ✓ | 2 |
| `CRIT-ORI-COMPLETE`: every demonstrated state reached | | 2 |
| `CRIT-ORI-CLEAN`: no off-path folds | | 1 |
| `CRIT-ORI-KEYSTEP`: the step the source marks as critical (chosen from claims) is executed as shown | | 2 |

## 5. Tabla: audio only (video optional)

### 5.1 Goal model from the expert audio (Track A)

1. PyAV decodes any audio container to mono 16 kHz float.
2. Onsets via spectral flux (`tracks/common/onsets.py`, numpy). Each onset carries time, strength and a **low-band ratio**: energy below 250 Hz over total, in an 80 ms window.
3. **Bayan (bass) flag:** 2-means clustering of the expert's low-band ratios, so the threshold adapts to the recording. This is a deterministic proxy for open-bass bols (Dha/Dhin/Ge) vs no-bass bols (Ta/Tin/Na). The empty (khaali) section of a theka is exactly where the bayan is withheld, so it is a musically meaningful criterion.
4. Beat period from the IOI histogram. Cycle length from the autocorrelation of the bass pattern; Teentaal = 16 is expected but checked, not assumed.
5. Claims: tempo, cycle length and bass pattern are `OBSERVED` (computed, with intervals). Bol names are `UNVERIFIED` unless the optional audio model is enabled, in which case they are `INFERRED`. The traditional theka text may appear only as an external reference, labelled as such.

### 5.2 Learner evaluation (Track B)

1. Learner audio upload (any container), decoded the same way: onsets plus bass flags.
2. Tempo normalisation: estimate the learner's beat period and rescale.
3. Align learner strokes to goal beats with DTW. The cost combines timing in beat units, bass mismatch and strength. The output is matched, missing and extra strokes.
4. Metrics:
   - tempo error;
   - median and worst timing deviation (ms) after the offset/tempo fit;
   - IOI coefficient of variation (stability);
   - bass-pattern accuracy;
   - missing/extra counts.
5. First divergence = the first beat with |deviation| > tolerance, a bass mismatch, or a missing stroke (with its time).
6. `progress(t)` = cumulative fraction of goal beats matched correctly.
7. **Optional video:** accepted and shown next to the audio timeline. It is not scored in the hackathon build; a hand-position criterion is future work.

**Default rubric:**

| Criterion | Required | Weight | Bands |
|---|---|---|---|
| `CRIT-TABLA-TEMPO`: holds the source tempo | ✓ | 2 | ≤ 5% sat · ≤ 10% partial |
| `CRIT-TABLA-TIMING`: strokes land on the beat grid | ✓ | 3 | median ≤ 50 ms sat · ≤ 100 ms partial |
| `CRIT-TABLA-BAYAN`: bass (bayan) used and withheld where the source does | ✓ | 3 | ≥ 0.9 sat · ≥ 0.7 partial |
| `CRIT-TABLA-COMPLETE`: no missing/extra strokes | | 1 | ≤ 1 sat · ≤ 3 partial |
| `CRIT-TABLA-STEADY`: steady pulse | | 1 | CV ≤ 0.08 sat · ≤ 0.15 partial |
| `CRIT-TABLA-BOLS` (only if the audio model is enabled): bol identity | | 2 | edit-distance accuracy ≥ 0.85 sat · ≥ 0.6 partial |

## 6. Feedback and transmission (shared)

- **Feedback** for the first-divergence criterion first. Each item gives what was observed (numbers + locator), the goal's version (reference region, keyframe or audio segment from the criterion map), why it matters (cites the claim), and the drill.
- **Retry** is always the full task. The drill is unscored.
- **TransmissionRecord** uses the contract gain. The view adds targeted change, progress-curve overlays and observability transitions.

## 7. Test data (no people needed)

| Case | Goal source (committed or fetched) | Learner attempts |
|---|---|---|
| Kolam | `Ithayakkamalam - 2.jpg` (public domain, Mayooranathan) | Synthetic traces from the goal curves: perfect, jittered, one curve missing, a stray stroke, a wrong dot relation, a broken loop. Plus hand-drawn canvas attempts. Plus a photo-upload test (rendered trace raster rotated/scaled). |
| Origami | `OrigamiCrane.ogv` (CC BY 3.0, Tavin), bird-base window | `Crane.ogv` (a separate recording, same licence) as a real second attempt. Synthetic: a segment cut (missing state), segments swapped (order), a truncation (incomplete). |
| Tabla | A CC-licensed tabla theka recording (Wikimedia Commons; selected after analysis) | Synthetic perturbations of the goal audio: timing jitter, dropped strokes, bass removed in the wrong section, tempo drift. Plus any upload. |

Synthetic attempts are labelled `SYNTHETIC` everywhere. Agreement metrics are computed against the known perturbation, which is exact ground truth. That is a stronger evaluation of the evaluator than hand labels.

## 8. Where AI is essential vs deterministic

| Job | Who | Why |
|---|---|---|
| Kolam geometry, curve decomposition, symmetry, coverage/precision | deterministic | exact, explainable, free |
| Kolam description, instructions, plausibility check | Gemma (image) | language and visual sanity, never authority |
| Origami paper-state recognition (expert and learner frames) | **Gemma (image frames)** | the only feasible way to recognise fold states; the core GenAI capability |
| Origami trajectory, order, divergence | deterministic | auditable |
| Tabla onsets, bass, tempo, alignment | deterministic | precise to the millisecond; Gemma has no audio |
| Tabla bol names | optional audio model | paid and off by default; criterion is UNCERTAIN when off |
| Feedback wording, evidence Q&A | Gemma (text) | constrained by a number/ID-preservation guard |
