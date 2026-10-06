# K7: Universal pipeline, part 2 — Layer 2 SkillModel builder + Layer 3 universal evaluator

Read `docs/kiro/specs/00-COMMON.md` first, then **`docs/plans/universal-pipeline.md` in full** (§5 and §6 are yours), then `docs/kiro/specs/K6-composer-backend.md` §2 (the perception API you consume). Folder `...\anveshan-wt\k7-engines`, branch `kiro/k7-engines`; created from `m1/hero-cases` after K1–K4 are merged. **Needs the API key** for the final live check only.

**Parallelism:** K6 implements `tracks.common.perceivers.perceive()` at the same time as you. Until it is merged, **do not implement perceivers yourself**: test with hand-built `PerceptionRecord` fixtures, and monkeypatch `tracks.common.perceivers.perceive` in tests. Code strictly against the signatures in K6 §2. When Jim tells you K6 is merged, rebase is not allowed: ask Jim to create a fresh branch for a short "K7-integration" follow-up instead.

**Hero cases are not touched.** You do not edit `track_a/goals/kolam.py`, `origami.py`, `tabla.py` or the hero evaluators. You *call* specialist code (§4).

## 0. Shared code (already written; do not change field names)
- `tracks/common/skill_model.py`: `SkillModel` and parts, `STRUCTURE_CHECKS`, `STRUCTURE_ATTEMPT_KINDS`.
- `tracks/common/perception.py`: the PerceptionRecord schema.
- `tracks/common/profile.py` (v2).
- `tracks/common/models.py`: `generate_json`, `embed`, `ImagePart`.
- `tracks/common/goals/kolam.py`: `payload_from_image(path) -> (payload, built_with)`.
- `track_b/evaluators/kolam.py` and `tabla.py`: `evaluate(goal, attempt, ctx)`.
- `track_a/goals/tabla.py`: `build(...)`.
- Registry entries already point at `track_a.goals.universal:build` and `track_b.evaluators.universal:evaluate`; `casedata.GoalModality` includes `"universal"`.

## 1. Files you own
- **New:**
  - `tracks/track-a/src/track_a/universal.py` (Layer 2 proposal)
  - `tracks/track-a/src/track_a/goals/universal.py` (builder: confirmed SkillModel → contracts)
  - `tracks/track-b/src/track_b/evaluators/universal.py` (Layer 3)
  - `tracks/track-b/src/track_b/evaluators/universal_align.py` (alignment helpers)
  - `tracks/common/goals/universal.py` (`PAYLOAD_MODEL = SkillModel`, `ui_view`)
  - prompts: `tracks/common/prompts/structure_skill_v1.txt`, `tracks/common/prompts/judge_final_v1.txt`, `tracks/common/prompts/judge_step_v1.txt`, `tracks/common/prompts/relevance_v1.txt`
  - tests: `tracks/track-a/tests/test_universal_build.py`, `tracks/track-b/tests/test_universal_eval.py`, `tracks/track-b/tests/test_universal_session_e2e.py`
- **Edit:** `tracks/track-a/src/track_a/api.py`, **only** `build_case`: for modality `universal`, load the latest `knowledge/case_profile.v*.json` and call the builder with `profile=…`. Use `inspect.signature` so other builders are unaffected. K6 edits other functions in the same file; keep your edit small and contained.

## 2. Layer 2 proposal: `track_a/universal.py`
```python
def propose_skill_model(record: PerceptionRecord, probe: ProbeFacts, intake: IntakeResult, ctx: RunContext,
                        title_hint: str | None, description: str | None,
                        source_path: Path | None = None) -> tuple[SkillModel, dict, list[str]]
```
Deterministic composition, plus **one optional text-only model call** for wording.

1. **Structures** (from `probe.structures_available`, in this order):
   - image → `["final_state"]`;
   - video → `["procedure"]` if available, else `["final_state"]`; add `"temporal_pattern"` if the rhythm specialist is available on the audio track;
   - audio → `["temporal_pattern"]` if available, else `["utterance"]` if available.

   At most 2 structures.
2. **Specialists:**
   - `line_art` available → `payload, _ = payload_from_image(source_path)`, stored in `specialists["line_art"]` (payload dict);
   - `rhythm` available → prefer `tracks.common.goals.tabla.payload_from_audio(path, window)` if it exists (K2b may add it). Otherwise call `track_a.goals.tabla.build(source_path, <SourceRecord built from probe>, ctx, case_id="tmp", version=1)` and take `.goal_payload`. Store it in `specialists["rhythm"]`. Keep the builder's criterion templates; you need their bindings in §3.
3. **goal_state** (final_state):
   - each `property` observation → `TargetProperty(prop_id="prop-NN", statement=label + (": " + detail if detail), region=segment.region, evidence=[obs_id], certainty="inferred")`, max 8;
   - plus line_art facts as **observed** properties: "N dots", "K continuous lines", "R-fold rotational symmetry" (evidence: the `det:` measurement observation ids if present, otherwise empty with a note).

   For video final_state, use the observations of the **last still segment**.
4. **steps:**
   - procedure → one Step per time segment that has a `state` observation, in time order: `name = state label (≤ 60 chars)`, `state_after = state label`, `action` = that segment's action observation, `start/end` from the segment, `keyframe_asset` from the segment, `segment_id`, `certainty="inferred"` (names come from the model), `source_established=True`. Merge consecutive segments with identical state labels. `critical=True` for the step after the longest active segment.
   - final_state image → steps from the `build step i:` action observations (inferred, `source_established=False`); or, if line_art, one step per line_art stage (inferred).
5. **order:** "strict" for procedure; "none" otherwise.
6. **constraints:** each `avoid: …` quality observation → `Constraint(certainty="inferred", keep=False)`. Off by default; the user can enable them.
7. **temporal / utterance:** temporal = a summary of the rhythm payload (pulse_sec, tempo_bpm, cycle_length). Utterance = `{transcript, language, duration_sec}` from the `speech` observation (inferred) and the measured duration.
8. **Default checks** (all with weight and required as shown; the user edits them later):

| Structure | check_id | kind | metric_id | method | weight | required | process |
|---|---|---|---|---|---|---|---|
| final_state | CHK-FS-SIM | final_similarity | `u.final_similarity` | deterministic | 1 | no | no |
| final_state | CHK-FS-P01..P04 | final_property (one per first ≤ 4 properties) | `u.final_property.<prop_id>` | model_status | 2 | first one yes | no |
| final_state + line_art | CHK-LA-* | line_art | `line_art:<metric>` for each line_art criterion template's metric | specialist | template weight | template required | template process |
| procedure | CHK-PR-COV | step_coverage | `u.step_coverage` | deterministic | 3 | yes | yes |
| procedure | CHK-PR-ORD | step_order | `u.step_order` | deterministic | 2 | yes | yes |
| procedure | CHK-PR-OFF | off_path | `u.off_path` | deterministic | 1 | no | yes |
| procedure | CHK-PR-FIN | final_property (target = last step) | `u.final_state_match` | model_status | 3 | yes | no |
| procedure | CHK-PR-Q01 | step_quality (critical step) | `u.step_quality.<step_id>` | model_status | 2 | no | yes |
| temporal_pattern | CHK-RH-* | rhythm | `rhythm:<metric>` for each rhythm template | specialist | template | template | template |
| utterance | CHK-UT-TXT | utterance_match | `u.utterance_match` | deterministic | 3 | yes | no |
| utterance | CHK-UT-PACE | pace_match | `u.pace_match` | deterministic | 1 | no | no |

   For line_art, get the templates by running the Kolam builder's criterion-template logic. The simplest way is to call `track_a.goals.kolam.build(source_path, source, ctx, case_id="tmp", version=1)` and read `result.criteria`; the Gemma enrichment inside it is optional and degrades to a warning. Store each template's `observer` (binding) in `check.params["binding"]` (`model_dump()`), so the builder can reuse the exact bands. Do the same for rhythm.
9. **Optional wording call** (`vision_fast`, text-only, prompt `structure_skill_v1.txt`). Input: a compact JSON of structures, observation labels (≤ 60), steps and properties, plus the user's title_hint and description. Output DTO: `{skill_title ≤ 60, summary ≤ 300, domain ≤ 60, vocabulary {state_noun, object_noun, unit_noun, action_verb}, check_texts: {check_id: {name ≤ 60, observable_indicator ≤ 160}}}`. Apply only to existing check ids; never add checks. On ModelError, use deterministic texts (`name` = the kind in title case + target name; `observable_indicator` = the target statement) and add a warning.
10. **relevance:** `expected_kinds` = the union of `STRUCTURE_ATTEMPT_KINDS` over structures (drop "trace" unless line_art). `min_similarity` = 0.72 for an image source, 0.70 for video. `reference_segment_ids` = `["seg-000"]` for an image; for video, all keyframe segments.
11. Return `(SkillModel(...), {"structures": ..., "specialists": list(specialists), "wording_model": bool}, warnings)`.

## 3. Builder: `track_a/goals/universal.py`
`build(source_path, source, ctx, *, case_id, version, profile) -> GoalBuildResult`. A confirmed profile is required (else INVALID_INPUT). **No new perception calls.**
- Load the source perception from `ctx.case_dir / "knowledge" / "perception_source.v1.json"` (the K6 composer copies it there).
- **Claims** (KnowledgeClaim), ids `CLM-01…` in this order:
  1. **Observed measurement claims** (deterministic `det:` observations), max 4: image "Image is W×H px; contrast …" with an `#xywh=percent:0,0,100,100` locator and no times; video "The demonstration has N segments over D s" with interval [0, D]; audio "Duration D s; N onsets" with an interval.
  2. `goal_state` properties with `keep=True` → CONDITION claims (certainty from the property; region locator or the whole image; video uses the last segment's interval).
  3. steps → STEP claims (inferred, confidence 0.5; interval or region; `source_established` mentioned in the statement: "Demonstrated step 2: …" vs "Suggested step 2 (inferred): …").
  4. constraints with `keep=True` → FAILURE_MODE claims (inferred).
  5. temporal → CUE claim (observed, from the rhythm payload). Utterance transcript → CUE claim (inferred).

  The grounding rules from Track A apply (`track_a/grounding.py`): OBSERVED needs a locator matching the modality; inferred confidence ≤ 0.5; and a goal-conditioned case needs ≥ 1 inferred STEP. For an image without build steps, add the step "Reproduce the target as shown (suggested, inferred)".
- **Criteria** from **enabled** checks: `criterion_id = f"CRIT-U-{check_id}"`; `name` / `observable_indicator` from the check; weight and required from the check. **Bindings:**
  - specialist checks → `ObserverBinding(**check.params["binding"])`, but with `metric = check.metric_id` (the prefixed id).
  - other kinds:

| kind | direction | bands (satisfied, partial) |
|---|---|---|
| final_similarity | higher | ≥ 0.90, ≥ 0.80 |
| final_property / step_quality | higher | ≥ 1.0, ≥ 0.5 |
| step_coverage | higher | ≥ 0.90, ≥ 0.60 |
| step_order | lower | ≤ 0, ≤ 1 |
| off_path | lower | ≤ 0, ≤ 1 |
| utterance_match | higher | ≥ 0.90, ≥ 0.70 |
| pace_match | lower | ≤ 0.15, ≤ 0.30 |

  `process = check.process`. Every criterion cites the claims of its targets (or the measurement claim for similarity/coverage) in `why_it_matters`, e.g. "Matches the demonstrated sequence (CLM-05, CLM-06)". `drill_hint` comes from a small template per kind.
- **Task:** title "Practice: {skill_title}"; numbered instructions from steps (procedure) or properties (final_state), citing [CLM-xx]; one sentence on what to upload (from `learner_input_kinds`).
- `goal_payload` = `profile.skill_model.model_dump(mode="json")`, with `perception_file` set to "knowledge/perception_source.v1.json".
- **Warnings:** pass through the SkillModel warnings, plus "Composed case: claims named by AI are inferred until reviewed."

## 4. Layer 3: `track_b/evaluators/universal.py`
`evaluate(goal, attempt, ctx) -> TrajectoryResult`. `goal.payload` → `SkillModel.model_validate`. Load the source PerceptionRecord and embeddings from `ctx.case_dir / skill.perception_file` (track_b may import `tracks.common.perceivers`; it must never import track_a).

1. **Kind gate:** `attempt.kind in skill.relevance.expected_kinds`, else `AnveshanFailure(INVALID_INPUT, f"This skill accepts {…} attempts.")`.
2. **Perceive the attempt:** call `perceive(attempt.path, attempt.mime_type, ctx, source_id=attempt.source_id, asset_dir=ctx.data_dir / "attempts" / attempt.sha256[:12], purpose="attempt")`. Skip this for `trace` attempts; trace goes straight to the line_art specialist.
3. **Quality gate** (deterministic, from attempt measurements): image/video blur variance < 15 or brightness < 0.08 → INVALID_INPUT ("too blurry/dark; please re-record"); audio RMS < 0.005 → INVALID_INPUT ("silent").
4. **Relevance gate** (image/video): cosine between the attempt's embedding (image: whole; video: the mean of its keyframe rows) and the source reference (mean of `reference_segment_ids` rows).
   - `< min_similarity` → INVALID_INPUT: "This doesn't look like an attempt at {skill_title} (similarity {s:.2f}). Please upload {kinds}."
   - in `[min, min + ambiguous_band)` → one `vision_fast` call (`relevance_v1.txt`) with a source keyframe and the attempt image, returning `{relevant: bool, reason}`. Not relevant → the same INVALID_INPUT.
   - Audio: relevance via `audio_kind` match (source percussion vs attempt percussion, speech vs speech); a mismatch → INVALID_INPUT.
5. **Per structure:**
   - **final_state:**
     - final image = the attempt image (image), or the keyframe of the last still segment (video).
     - `u.final_similarity` = cosine(final attempt embedding, source whole/last keyframe embedding).
     - **One** `vision_fast` call (`judge_final_v1.txt`): the source image (or last source keyframe) plus the attempt final image (≤ 2 images, max side 512) plus the list of enabled final_property checks with their target statements. DTO `{"results": [{"check_id", "status": "met"|"partly"|"not_met"|"cannot_tell", "finding" ≤ 200, "region": [x,y,w,h] | null}]}`. Map met 1.0 / partly 0.5 / not_met 0.0 / cannot_tell None (reason "model could not tell from the evidence"); a missing check gives None ("not reported by model").
     - Evidence: image → a region locator on `attempt.source_id`; video → a frame locator.
   - **procedure** (video attempts; image attempts get only final checks, and the process checks become UNCERTAIN through `process_observable=False`):
     - attempt frame rows come from `record.specialists["frames"]`, source step keyframe rows from `embedding_index[step.segment_id]`;
     - `universal_align.label_frames(frame_vecs, step_vecs, margin=0.03, floor=0.60)` → for each frame, the step index, or "transition" (best − second < margin), or "off" (best < floor);
     - mode filter (window 3);
     - `universal_align.needleman_wunsch(observed_step_sequence, expected=list(range(n)))` → matched, missing and order violations (reuse the scoring from `track_b/evaluators/origami_trajectory.py`; import its helpers if suitable, or reimplement equivalently);
     - `u.step_coverage` = matched / n; `u.step_order` = violations; `u.off_path` = number of runs of "off" lasting ≥ 2 s;
     - `u.final_state_match`: judge_final with the last source step keyframe vs the attempt's last still keyframe;
     - `u.step_quality.<step>` (critical step only): one `judge_step_v1.txt` call with the source step keyframe vs the attempt frame best matching that step → status → value;
     - events: missing steps (position = the expected time, interpolated), order violations, off-path runs; positions in seconds; frame locators;
     - curve = (time, max matched step index + 1) / n, monotone.
   - **temporal_pattern:**
     - build `GoalModel(case_id=goal.case_id, version=goal.version, modality="tabla_audio", source_ids=goal.source_ids, package_id=goal.package_id, payload=skill.specialists["rhythm"])`;
     - for a video attempt, extract its audio track to a temporary WAV with PyAV first and pass an `AttemptMedia(kind="audio", …)`;
     - call `track_b.evaluators.tabla.evaluate(goal_tabla, attempt_audio, ctx)`;
     - prefix every metric id with `"rhythm:"` and keep its events and curve.
   - **line_art:** same pattern with `modality="kolam_image"`, `payload=skill.specialists["line_art"]`, and `track_b.evaluators.kolam.evaluate`. The attempt is the trace or image as-is. Prefix metrics with `"line_art:"`.
   - **utterance:**
     - normalise both transcripts (lowercase, strip punctuation, split into words);
     - `u.utterance_match` = 1 − levenshtein(words) / max(len(src), 1), clamped to 0..1 (implement levenshtein or reuse `tabla_dsp.levenshtein`);
     - `u.pace_match` = |attempt duration − source duration| / source duration;
     - if either transcript is missing (audio model disabled), value=None with reason "transcript unavailable (audio model disabled)".
6. **Compose the TrajectoryResult:**
   - `metrics` = the union (metric ids exactly equal to the checks' `metric_id`; a metric whose check isn't enabled may be included, since scoring ignores it);
   - `events` sorted by position;
   - `curve` / `curve_kind` from the first structure in the order procedure > temporal_pattern > final_state > utterance (final_state curve: `[(0, 0.0), (1, fraction of final_property checks met)]`, kind "stroke");
   - `process_observable` = False for image attempts, True otherwise;
   - `artifacts` = `{"frame_labels": [...], "relevance": s, "attempt_perception": <record path>}`;
   - `run_keys`, `warnings` (always include "Universal pipeline: AI-perceived checks are lower confidence than specialist measurements").

## 5. Tests (no network; fake gateway clients; fixture PerceptionRecords)
- **`test_universal_build.py`:**
  - `propose_skill_model` for: (a) an image record with property observations → final_state checks; (b) an image that passes line_art on a synthetic line drawing (Pillow) → line_art checks with prefixed metric ids and bindings copied; (c) a video record with 4 still segments and state labels → procedure steps, strict order, default checks; (d) a speech audio record → utterance checks; (e) the wording model failing → deterministic texts plus a warning.
  - `build` on a composed case dir in tmp: grounding passes, inferred steps ≤ 0.5, observed claims carry locators, criterion ids `CRIT-U-*`, specialist bindings preserved, task cites claims, output deterministic.
- **`test_universal_eval.py`:**
  - kind gate;
  - quality gate;
  - the relevance gate below min (→ INVALID_INPUT) and in the ambiguous band (fake yes/no);
  - final_state judge mapping, including cannot_tell → None;
  - procedure alignment with synthetic embeddings: perfect order → coverage 1, violations 0; a swapped pair → 1 violation; a missing step → coverage < 1 with an event at the interpolated time; noise frames → off_path;
  - the image attempt for a procedure → process criteria UNCERTAIN through scoring;
  - the rhythm/line_art specialist delegation with prefixed metric ids (monkeypatch the specialist evaluators);
  - utterance math.
- **`test_universal_session_e2e.py`:** a synthetic composed case (fixture SkillModel plus perception with embeddings written to tmp) → `track_b.api.start_session` → a baseline attempt with a missing step → a retry that is perfect → `complete_session` → the bundle validates (`validate_transmission_bundle`), the gain is positive and `targeted_change` improved. Use fake gateway responses everywhere.

## 6. Live check (with key; after K6 is merged, or with K6's branch checked out read-only for reference)
If K6 is not merged yet, skip this and say so. Otherwise run through the composer API:
- (a) a Kolam PNG from `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\var\kiro\media\kolam\` — build, then attempts: the same image (expect high similarity, properties met), the image half painted white (expect lower or partial), and a random photo (expect the relevance refusal);
- (b) a 30–40 s cut of the origami demo video as source — attempts: a different 30–40 s cut of the same video (expect partial coverage) and the same cut (expect high coverage).

Record statuses, metrics, latency and costs.

## 7. Acceptance
- All tests pass; the hero tests are unchanged and green.
- The Definition of Done in 00-COMMON.md is met. Report: `docs/kiro/reports/K7-REPORT.md` (include the live-check table, or state why it was skipped).
