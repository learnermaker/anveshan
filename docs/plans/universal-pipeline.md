# Universal Pipeline — Perception → Knowledge Structure → Evaluation

**Date:** 2026-10-06 · **Status:** DECIDED architecture for any upload (Jim: "a common perception layer, a knowledge structure layer and an evaluation/review layer — that is the purpose of our solution"). This supersedes the engine-family routing in `case-composer.md` §3–§7. The composer becomes the UI and API front end of this pipeline.

## 1. Why the previous design was not enough

The composer routed each upload to one of three hand-built engines (line art, video states, rhythm), with a VLM fallback. That generalises only to things that look like the three demo cases. A cooking video, a yoga pose, a spoken phrase, a knot, a calligraphy stroke, a photo of a plated dish, or something unteachable would either be forced into the wrong engine or fall through to an unstructured "model judges it".

The product's purpose is a **common** path: perceive anything → structure it as a skill → verify a learner against that structure. Specialist engines should add precision **inside** that path, not replace it.

## 2. The three layers (plus gates)

```
            ┌────────────── INTAKE GATES ───────────────┐
 upload ──► │ format/limits · safety · teachability      │──► refuse with reasons (no case)
            └────────────────────────────────────────────┘
                        │
                        ▼
 LAYER 1  PERCEPTION      any media ─► PerceptionRecord
          generic perceivers (always) + specialist perceivers (when applicable)
                        │
                        ▼
 LAYER 2  KNOWLEDGE STRUCTURE   PerceptionRecord(s) + user intent ─► SkillModel
          goal state · steps · constraints · temporal pattern · utterance · checks
          ─► KnowledgePackage claims + Rubric + Observers + CriterionMap (8 contracts unchanged)
                        │
                        ▼
 LAYER 3  EVALUATION / REVIEW   attempt media ─► attempt gates ─► PerceptionRecord(attempt)
          ─► alignment to SkillModel ─► checks ─► metrics ─► deterministic bands ─► first divergence ─► feedback
```

The same perceivers run on the **source** (Layer 2 input) and on the **attempt** (Layer 3 input). That symmetry is what makes the comparison meaningful for any skill.

## 3. Layer 1: Perception

### 3.1 PerceptionRecord (`tracks/common/perception.py`)
```
PerceptionRecord
  media: {source_id, modality: image|video|audio, sha256, duration_sec?, width?, height?, has_audio?}
  segments: [Segment]          time intervals (video/audio) or regions (image), or "whole"
  observations: [Observation]  everything perceived, each anchored to a segment
  embeddings: {segment_id: vector_ref}   unit vectors stored in a sidecar .npy (keyed by sha), not inline
  specialists: {name: payload}           e.g. line_art (KolamGoal-like geometry), rhythm (onsets/pulse/timbre)
  runs: [replay keys]                    every model call used
Segment      {segment_id, kind: time|region|whole, start_sec?, end_sec?, region? [x,y,w,h %], keyframe_sec?, keyframe_asset?, stability?}
Observation  {obs_id, segment_id, kind: state|action|object|property|event|speech|measurement|quality,
              label (short canonical phrase), detail?, value?, unit?,
              certainty: observed|inferred|unverified, producer: "det:<name>" | "model:<model_key>"}
```
**Certainty rule:** deterministic measurements are `observed`. Model descriptions of visible content are `inferred` (the model may be wrong) until a human reviewer approves them. This is the same discipline the 8 contracts already enforce.

### 3.2 Generic perceivers (always run, by modality)

| Modality | Perceiver | Output | Cost / latency |
|---|---|---|---|
| image | `det:image_basic` | size, contrast, ink fraction, components, blur score, brightness | free, < 0.5 s |
| image | `model:embedding` | whole-image embedding (+ 2×2 tile embeddings) | ~$0.0005, ~1 s |
| image | `model:vision_fast` | objects, visible properties (with regions), what kind of artefact, teachability | ~$0.0003, ~2.5 s |
| video | `det:video_segment` | 1 fps frame diffs → activity/still segments, stable keyframes (≤ 12) | free, ~2–5 s |
| video | `model:embedding` | keyframe embeddings (+ per-second frame embeddings for alignment, ≤ 120) | ~$0.01, ~5 s |
| video | `model:vision_fast` | per keyframe: state / action / objects (batches of ≤ 4 images) | ~$0.001, ~9 s per batch |
| video | audio perceivers on the audio track if present | as below | |
| audio | `det:audio_signal` | onsets, energy envelope, pulse, percussive contrast, speech-likeness (spectral flatness + 4 Hz modulation) | free, < 1 s |
| audio | `model:audio` | audio type (speech / music / percussion / environment), transcript if speech, sound events with approximate times, instrument and bols if tabla | ~$0.0003, ~3 s |

### 3.3 Specialist perceivers (run when the predicate holds; add precision)

| Specialist | Predicate (deterministic) | Adds |
|---|---|---|
| `line_art` (Kolam geometry) | image binarises cleanly (separation ≥ 0.25, ink 1–40%, skeleton length ratio ≥ 0.5, ≤ 6 big components) | dots, continuous curves, crossings, symmetry, stages (backward interpolation), coverage/precision machinery |
| `rhythm` (Tabla DSP) | onset rate ≥ 1.5/s over ≥ 6 s and percussive contrast ≥ 1.5 | pulse, cycle, bass pattern, timbre classes, DTW alignment |
| `procedure_states` (Origami engine) | video has ≥ 2 stable distinct segments (embedding distance between keyframes ≥ 0.08) | ordered states with keyframes and properties |

Specialists are registered in a table (`tracks/common/perceivers.py: SPECIALISTS`). New specialists (pose, OCR/handwriting, colour palette) can be added later without touching the layers.

### 3.4 Models (registry keys)

| Key | Default | Use |
|---|---|---|
| `vision_fast` | `gemini-3.5-flash-lite` | all interactive image/frame perception and checklist judgements (2.5 s per image; 4 images in 8.9 s) |
| `audio` | `gemini-3.5-flash-lite` | audio perception |
| `embedding` | `gemini-embedding-2` | image/frame embeddings (5 images in 1.3 s) |
| `text_image` | `gemma-4-26b-a4b-it` | free; offline or batch descriptions where latency doesn't matter (43 s per image) |

Measured on 2026-10-06 with Jim's key. All are configurable through env; the gateway records every call (embeddings included) for replay.

## 4. Intake gates (before any case exists)

1. **Format/limits** (deterministic): image ≤ 30 MB; video 8–120 s; audio 3–60 s; supported containers via PyAV.
2. **Safety screen** (from the `vision_fast` / `audio` perception call, plus deterministic rules). Refuse, with a clear message, when the source depicts:
   - weapons or explosives manufacture;
   - self-harm;
   - medical or invasive procedures;
   - sexual content;
   - illegal activity;
   - dangerous chemical or electrical work.

   Flag (allow, with a privacy notice) when identifiable faces are present. The policy list lives in `tracks/common/policy.py` and is versioned.
3. **Teachability:** the perception call returns `teachable: yes|no|unclear` + `skill_kind` + `reason`. `no` (e.g. a landscape, a meme, a screenshot of text, a blank image) → refuse: "We couldn't find a learnable, observable skill in this file: <reason>. Try a video of someone doing it, or a clear photo of a finished piece." `unclear` → continue, but require the user's description (title + "what should a learner achieve") before analysis can finish.

## 5. Layer 2: Knowledge structure

### 5.1 SkillModel (`tracks/common/skill_model.py`) = GoalModel payload for modality `universal`
```
SkillModel
  skill_title, summary, source_modality
  structures: subset of [final_state, procedure, temporal_pattern, utterance]   (≥ 1)
  goal_state:   [TargetProperty {prop_id, statement, region?, evidence: [obs_id], certainty, check: final_property|final_similarity|specialist}]
  steps:        [Step {step_id, index, name, state_after, action?, start_sec?, end_sec?, keyframe_asset?, evidence:[obs_id],
                       certainty, source_established: bool, critical: bool}]
  order:        strict | partial | none        (strict/partial only if source_established)
  constraints:  [Constraint {constraint_id, statement, evidence:[obs_id], certainty, check: off_path|model_constraint|specialist}]
  temporal:     {pulse_sec, cycle, pattern...} | null     (from rhythm specialist)
  utterance:    {transcript, language?, duration_sec} | null
  specialists:  {line_art?: KolamGoal payload, rhythm?: TablaGoal payload, procedure_states?: OrigamiGoal payload}
  relevance:    {source_embedding_ref, min_similarity (default 0.72), expected_kind}
  checks:       [Check {check_id, kind, targets:[ids], metric_id, method: deterministic|model_status|specialist:<name>, params}]
```

### 5.2 How each structure is built (deterministic composition over perception)
- **final_state** (any image, or a video's last stable keyframe): goal properties = model-perceived visible properties (inferred, with regions) + deterministic measurements (observed) + specialist facts (e.g. line_art dot count, symmetry). A final image always gets **backward interpolation** as inferred steps:
  - line_art present → its stages;
  - otherwise → one `vision_fast` call proposing a plausible build order with a region for each stage (inferred, confidence ≤ 0.5; `order: none`, so it's reported but never scored).
- **procedure** (video): steps = stable segments (deterministic segmentation), named by `vision_fast` keyframe descriptions; `source_established=true`, `order: strict`. If `procedure_states` applies, use its states instead and keep the deterministic segments as evidence. Critical steps = the longest transitions (Origami rule), or user-marked.
- **temporal_pattern** (rhythmic audio or audio track): from the rhythm specialist.
- **utterance** (speech audio): transcript from the audio perceiver (inferred), duration and pace measured (observed).
- **constraints:** from specialists (off-path ink, tempo steadiness) and from model-perceived "visible mistakes to avoid" (inferred). Model constraints become checks only if the user keeps them in the composer.

### 5.3 Check catalogue (the common evaluation vocabulary)

| Check kind | Method | Metric (value) | Applies when |
|---|---|---|---|
| `final_similarity` | deterministic over embeddings | cosine(attempt final, goal) | any final_state; reported/minor weight (coarse) |
| `final_property` | model_status (`vision_fast` checklist) | met 1 / partly 0.5 / not 0 / cannot_tell None | each goal property kept by the user |
| `step_coverage` | deterministic over embedding-aligned frames | fraction of source steps matched | procedure × video attempt |
| `step_order` | deterministic (Needleman–Wunsch) | number of order violations | procedure with order strict |
| `off_path` | deterministic | number of attempt segments far from every step (cos < τ) for ≥ 2 s | procedure |
| `step_quality` | model_status (attempt segment keyframe vs source keyframe) | status | critical steps only (≤ 2 calls) |
| `line_art_*` | specialist `line_art` | coverage / precision / dots / curves / continuity | line_art present |
| `rhythm_*` | specialist `rhythm` | tempo / timing / bass / strokes / complete / steady | rhythm present |
| `utterance_match` | deterministic over transcripts | 1 − normalised edit distance | utterance |
| `pace_match` | deterministic | relative duration or speech-rate error | utterance / procedure |

**The rubric = the checks the user keeps.** Scores come only from bands on these metrics (score_policy_v1). The model only reports perceptions and statuses.

### 5.4 Mapping to the 8 frozen contracts (unchanged)
- SkillModel elements → `KnowledgeClaim`s (STEP / CONDITION / CUE / FAILURE_MODE), with locators to segments (time) or regions (`#xywh`).
- Checks → `RubricCriterion` + `ObserverBinding` + `CriterionMap` entries (`why_it_matters` cites the element's claim).
- The SkillModel is stored as `knowledge/goal_model.vN.json` with `modality: "universal"` and `payload = SkillModel`. Perception records are stored as `knowledge/perception_source.vN.json` (+ `.npy` embeddings).

## 6. Layer 3: Evaluation / review

1. **Attempt gates:**
   - kind compatibility, via the applicability matrix (§6.1);
   - quality (deterministic: blur, darkness, silence, clipping, too short);
   - **relevance**: embedding cosine between attempt and source. Below `relevance.min_similarity` → raise `INVALID_INPUT` "This doesn't look like an attempt at <skill> (similarity 0.61). Please upload <expected_kind> of <skill>." The attempt is **not recorded**.

   Between min and min+0.08 → one `vision_fast` yes/no relevance check.
2. **Perceive the attempt** with the same generic perceivers, plus the specialists present in the SkillModel.
3. **Align:**
   - procedure → each attempt frame's embedding gets the nearest source step keyframe (cosine, with a margin of 0.03 over the second best, else "transition"/"unclear"), then mode filter, then Needleman–Wunsch against the step order;
   - final_state → the attempt's final frame (last stable keyframe for video, the image itself for photos);
   - temporal → rhythm DTW;
   - line art → registration (image) or the trace path.
4. **Run checks → metrics** (MetricValue with findings and locators).
5. **Deterministic scoring**, first divergence (earliest aligned violation), feedback with source evidence (keyframe / region / segment via criterion map), drill. All of this is already implemented in the Track B core.

### 6.1 Applicability matrix (source structure × attempt kind)

| Source structure | image attempt | video attempt | audio attempt | canvas trace |
|---|---|---|---|---|
| final_state | final checks; process UNCERTAIN | final checks on the last stable frame + inferred-step progression (reported) | n/a | line_art checks (if line_art) |
| procedure | final checks only; process UNCERTAIN | all checks | n/a | n/a |
| temporal_pattern | n/a | rhythm checks on the audio track | rhythm checks | n/a |
| utterance | n/a | utterance checks on the audio track | utterance checks | n/a |

`n/a` → INVALID_INPUT at upload, with the accepted kinds listed.

## 7. Hero cases in this architecture

| Case | Structures | Specialists |
|---|---|---|
| Kolam | final_state | line_art |
| Origami | procedure | procedure_states |
| Tabla | temporal_pattern | rhythm |

For the hackathon the hero cases keep their proven builders/evaluators (`kolam_image`, `origami_video`, `tabla_audio` modalities). The universal engine **calls the same specialist code**, so architecturally they are the same pipeline. Migrating the hero cases to `modality: universal` is post-hackathon work.

## 8. What happens with "something entirely different"

| Upload | Outcome |
|---|---|
| Cooking / knot / assembly video | procedure: segmented steps, embedding alignment, step order and coverage, final checklist |
| Photo of a finished craft (pottery, plated dish) | final_state: property checklist + similarity; inferred build order shown, not scored |
| Yoga pose photo | final_state: posture properties via checklist (lower confidence, labelled); a pose specialist is future work |
| A spoken phrase or recitation | utterance: transcript match + pace |
| Clapping or drumming | temporal_pattern: rhythm specialist |
| Landscape photo, meme, blank, text screenshot | refused at the teachability gate, with a reason |
| Dangerous or sensitive skill | refused at the safety gate |
| Learner uploads something unrelated | refused at the relevance gate, not scored, not recorded |
| PDF / text | not supported yet (refused at the format gate); future: text-structured knowledge |

## 9. Cost and latency budget (per composed case)
- **Build:** ≤ 40 embeddings, ≤ 4 `vision_fast` calls, ≤ 1 audio call. Under 2 US cents and under 45 s.
- **Attempt:** ≤ 120 embeddings, ≤ 3 `vision_fast` calls, ≤ 1 audio call. Under 2 cents and under 30 s.

## 10. Implementation plan (Kiro wave 2; replaces the earlier K6/K7 scope)

| Spec | Scope |
|---|---|
| K6 | Intake gates + Layer 1 generic perceivers + composer API/drafts |
| K7 | Layer 2 SkillModel builder + Layer 3 universal evaluator + specialist adapters (`modality: universal`) |
| K8 | Composer UI (proposal shows perception facts vs inferred structure; checks editor) |
| K2b | Tabla timbre (rhythm specialist upgrade) |

Shared schemas (`perception.py`, `skill_model.py`, `profile.py` v2) and the gateway's `embed()` are written by Claude Code before wave 2 starts, so K6 and K7 build on the same definitions.

## 11. Calibration log

Calibration decisions made during WP5 integration live checks (2026-10-06). All values are
written justifications against observed live data on the actual hero media and synthetic test files.

### 11.1 Quality gate thresholds (Layer 3 `_quality_gate` in `universal.py`)

**Original WP2 values:** `blur_score < 15`, `brightness < 0.08`

**Problem found during WP5 step 3 live checks:** The measurements in `perceive_image` normalise pixel values to `[0, 1]` before computing the Laplacian variance. All tested images — including high-quality photos of size 960×720 — returned `blur_score` values between 0.0 and 0.1. The original threshold of 15 was calibrated against the raw `[0, 255]` range and would reject every real-world image.

**Images measured (WP5 step 3):**

| File | brightness | blur_score |
|---|---|---|
| kolam_8_mayoo.png (dark background) | 0.061 | 0.1 |
| colorful_kolam.jpg | 0.433 | 0.1 |
| india_kolam_06_savage.jpg | 0.490 | 0.0 |
| india_kolam_09_savage.jpg | 0.554 | 0.1 |
| synthetic gradient 128×128 | ~0.60 | 0.0000 |
| synthetic rangoli 256×256 | ~0.06 | 0.001 |

**Decisions and rationale:**

- `blur_score` threshold: **15 → 0.002**  
  Rationale: All real images (even very sharp photos) produce blur_score ≤ 0.1 at [0,1] scale. The threshold 0.002 still rejects completely uniform blank images (gradient: 0.0) while accepting all valid photograph and drawing submissions. The synthetic gradient was correctly refused at 0.0000 < 0.002.

- `brightness` threshold: **0.08 → 0.02**  
  Rationale: The kolam_8_mayoo.png hero source has a black background with white lines, giving brightness = 0.061. At 0.08 threshold this was incorrectly refused. The threshold 0.02 still rejects near-blank white images (brightness close to 1.0 but with nothing in them — caught by blur_score) and truly black images, but allows dark-background artwork that is a valid teaching medium.

### 11.2 Relevance gate (`min_similarity`) live observations

**Default WP2 values:** `min_similarity = 0.72` for image, `0.70` for other modalities.

**Live check results (WP5 step 3, kolam compose):**

| Attempt | Embedding cosine similarity | Gate outcome |
|---|---|---|
| Same source image | 1.00 | PASS |
| Half-erased (right half whitened) | 0.96 | PASS |
| Synthetic gradient (uniform gradient) | caught by blur_score gate first | REFUSED (quality gate) |

**Decision:** Retain `min_similarity = 0.72` for images.  
Rationale: The half-erased image (0.96) was correctly passed as a valid attempt. No ambiguous-band case (0.72–0.90) was observed in these checks. The gradient was refused by the quality gate before the relevance gate was evaluated, which is the intended behaviour (quality gate runs first).

### 11.3 Audio structure detection for synthetic waveforms

**Observation:** A synthetic 8-second hand-clap WAV (1200 Hz damped sine bursts at 120 BPM) did not receive a proposal from `propose_skill_model`. The audio perceiver did not detect either `temporal_pattern` (rhythm) or `utterance` (speech) structures.

**Decision:** No threshold change made.  
Rationale: The synthetic waveform does not exhibit realistic percussive contrast (natural percussion has broadband energy and a sharp transient), so the rhythm specialist probe correctly returning no structures is expected behaviour. Synthetic waveforms are not valid learning media; the intake gate should reject them. The `tabla_chanderi_1.webm` real recording (a video with tabla audio) was correctly classified as `procedure + temporal_pattern` and evaluations passed.

### 11.4 Model latency observations (WP5 live checks)

| Check | Model call | Elapsed |
|---|---|---|
| Kolam compose (perceive + propose) | vision_fast + embedding | ~6 s |
| Kolam evaluate: same image | vision_fast + embedding | ~6 s |
| Kolam evaluate: half-erased | vision_fast + embedding | ~5 s |
| Rangoli compose + evaluate | vision_fast + embedding | ~5 s |
| Tabla_chanderi compose (video) | vision_fast + embedding + audio | ~20 s |

All within the latency budget (case build < 45 s, attempt < 30 s per §9). The tabla chanderi video evaluation at 19.8 s is close to the 30 s budget; this was due to the procedure structure doing embedding-based step alignment over a long video.


## 12. Video procedures for ANY upload: robustness revision (2026-10-07, IMPLEMENTED)

**Why:** the WP5 live checks covered images and audio only, and reported "PASS" whenever no exception was raised. A video stress harness (`tools/stress_universal_video.py`) that composes a case exactly like the UI and reads real session verdicts showed the video path was broken for new uploads:
- the perceiver only looked at the first 120 s;
- pixel-motion segmentation merged steps whenever hands kept moving;
- the judges never received an image for video attempts, so they always returned "cannot tell";
- the wording prompt path was wrong, so wording was silently disabled;
- expert reference keyframes were looked up in the wrong folder.

### 12.1 Design (domain-agnostic; nothing knows origami, drawing or cooking)

| Stage | Technique | Where |
|---|---|---|
| Sampling | adaptive fps over the whole video (≤ 120 frames); uploads up to 600 s, cost flat | `perceivers/video.py` |
| State segmentation | one Gemini Embedding 2 vector per frame, fused with a 24×14 layout thumbnail; optimal K-segment DP (deliberately over-segmenting, K ≤ 16); high-motion frames down-weighted | `tracks/common/segmentation.py::segment_k` |
| Stage naming | ONE vision_fast call sees all keyframes in order and groups them into stages (non-decreasing, repaired deterministically); brief all-in-progress stages dropped | `perceive_frames_v2`, `_monotone_stages`, `_drop_brief_in_progress` |
| Steps | settled stages → `SkillModel.steps`; low-calm segments are transitions, not steps | `track_a/universal.py::_build_steps` |
| Relevance gate | median frame-level best match vs the source's own non-adjacent self-consistency, minus 0.15 | `_relevance_gate` |
| Step identity | (a) per-frame cosine to step span centroids, z-scored per frame (scene-level similarity cancels); (b) ONE `match_steps_v1` call labels learner keyframes against expert step keyframes, fused as an observation | `_procedure_checks`, `_reference_step_matches` |
| Coverage / progress | Drop-DTW-style monotone alignment (steps may be skipped, never revisited; frames may be dropped as "off") | `segmentation.monotone_align` |
| Order | present steps minus the longest increasing subsequence of step times, with a 2-sample tolerance | `order_violations` |
| Off-path | calm runs (≥ 2 s) far below the attempt's own typical match level are states the expert never showed | `_procedure_checks` |
| Judges | several frames each: final evidence = matcher-labelled final-step keyframes (else the end-window frames most like the final step); step evidence = frames around the moment aligned to the step; both compared with the expert keyframe re-decoded at 512 px | `judge_*_v2` |

Concepts reused from elsewhere:
- optimal change-point segmentation (dynamic programming over all change points);
- Drop-DTW (Dvornik et al., NeurIPS 2021): monotone alignment with a drop cost, used for procedure-step localisation;
- LIS / Kendall-style rank distance for order;
- visual-RAG-style "show the reference next to the candidate" for fine-grained identity.

Model outputs remain observations. Every score comes from deterministic metrics, bands and policy.

### 12.2 Evidence (live, 2026-10-07; summaries in `tracks/track-b/eval/universal_video/`)

| Scenario | Attempts → verdict |
|---|---|
| Synthetic "draw a house" (5 steps, never seen before) | re-performance PASS; missing door FAIL (coverage, final); stopped early FAIL; unrelated video REFUSED (0.64); swapped walls/roof is **unstable** (FAIL with an off-path state in some runs, PASS in others) |
| Full `OrigamiCrane.ogv` as a new upload (no origami code) | 8–9 steps through to the finished crane; `Crane.ogv` positive control PASS 11/11; first 40 % FAIL; unrelated REFUSED |
| Hard clip: 0–194 s window at 400×226, hands always on the paper (the dedicated-engine eval setup) | unrelated REFUSED; missing, swapped and truncated attempts flagged; **the perfect re-encode does not pass reliably**. Stage names vary between runs, and the clip has no clean final moment |

### 12.3 Known limits (honest)
- Global embeddings separate scenes, not fine-grained object states. When hands dominate a low-resolution frame, step identity depends on the vision model, whose answers vary between live runs even at temperature 0. Recorded replay makes demos reproducible; live answers can differ.
- Composed steps are proposals. The composer's review step, where the expert confirms or edits steps, is the product safeguard. Steps stay INFERRED until then.
- Next options, not yet authorised: self-consistency (2–3 matcher calls with agreement weighting); crop to the work region before embedding.
