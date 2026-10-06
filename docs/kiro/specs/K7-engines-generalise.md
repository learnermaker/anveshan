# K7: Generalise the Kolam/Origami engines for new skills, and build the `rubric_vlm` engine

Read `docs/kiro/specs/00-COMMON.md` first, then **`docs/plans/case-composer.md` §3, §5, §7 and §10**. Folder `...\anveshan-wt\k7-engines`, branch `kiro/k7-engines`; created from `m1/hero-cases` **after K1–K4 are merged**. **Needs the API key** (copy `.env`) for the final live check only. Runs in parallel with K6 (composer backend) and K2b (tabla). **Do not edit tabla files** (K2b makes the tabla engine profile-aware) or `track_a/composer.py`, `track_a/config.py`, `track_a/api.py` (K6).

## 0. The rule that matters most
**Hero cases must not change at all.** With `profile=None`, the Kolam and Origami builders and evaluators must produce **byte-identical** output to before. Prove it with a test that builds the hero goal model before and after (in recorded mode, using the committed golden runs) and compares the JSON.

## 1. Files you own
- **Edit:**
  - `tracks/track-a/src/track_a/goals/kolam.py`
  - `tracks/track-a/src/track_a/goals/origami.py` (+ `origami_*.py` helpers)
  - `tracks/track-b/src/track_b/evaluators/origami.py` (+ `origami_trajectory.py` only if needed)
  - `tracks/track-b/src/track_b/evaluators/kolam.py` (only if it uses kolam-specific wording in findings)
  - `tracks/common/goals/kolam.py` (only if needed for dot-less payloads)
- **New prompts:** `tracks/track-a/prompts/origami_states_v2.txt` (generic), `tracks/track-b/prompts/origami_match_v2.txt` (generic), `tracks/track-a/prompts/rubric_vlm_goal_v1.txt`, `tracks/track-b/prompts/rubric_vlm_judge_v1.txt`. Keep every v1 file unchanged; hero cases keep using v1.
- **New modules:** `tracks/common/goals/rubric_vlm.py`, `tracks/track-a/src/track_a/goals/rubric_vlm.py`, `tracks/track-b/src/track_b/evaluators/rubric_vlm.py`. The registry entries for these already exist in `track_a/goals/__init__.py` and `track_b/evaluators/__init__.py`.
- **Tests:** `tracks/track-a/tests/test_engines_profile.py`, `tracks/track-b/tests/test_rubric_vlm_eval.py`, `tracks/track-a/tests/test_rubric_vlm_goal.py`.

## 2. Builder signature (all three engines you touch)
```python
def build(source_path, source, ctx, *, case_id, version, profile: "CaseProfile | None" = None) -> GoalBuildResult
```
Import `CaseProfile` from `tracks.common.profile`. When `profile is None`, the code path is the current one, unchanged.

## 3. Kolam engine with a profile (family `image_target`)
Inputs: `profile.title`, `profile.vocabulary` (`object_noun` default "line drawing", `unit_noun` default "stroke"), `profile.goal_hint`, `profile.criteria`.

1. Geometry is the same (`payload_from_image`). **Dot-less drawings:** if `payload["dots"]` is empty:
   - omit the dot-count and dot-relation claims;
   - omit the `CRIT-KOLAM-DOTS` criterion;
   - make the evaluator handle zero dots (the `kolam.dot_relation_match` metric is not produced, or `value=None` with reason "no dots in target"; since that criterion isn't in the rubric, either is fine; pick one and test it).
   - Verify the scoring core tolerates a metric that has no criterion. It should: observers only reference rubric criteria.
2. **Wording:** replace kolam-specific text in claims, task title and instructions, criterion names and `why_it_matters`:
   - "kolam" → `profile.title`; "pulli"/"pulli dots" → "dots"; "line" stays.
   - Put the wording in a small dict-based template inside `kolam.py`: `_TEXT_HERO` (current strings) and `_TEXT_GENERIC` (with `{title}`, `{object_noun}`, `{unit_noun}` placeholders), chosen by `profile is None`. No regex rewriting of strings.
   - Generic-mode claim statements must still describe only computed facts (counts, symmetry, continuity). The inferred drawing stages say "one suggested way (inferred)".
3. **Criterion ids** in generic mode: `CRIT-IMG-COVERAGE`, `CRIT-IMG-PRECISION`, `CRIT-IMG-DOTS` (if dots), `CRIT-IMG-CURVES`, `CRIT-IMG-CONTINUITY`. Same metrics, same bindings as the hero templates. Hero ids stay `CRIT-KOLAM-*`.
4. **User criteria:** for each `profile.criteria` item with `method == "engine_default"`, try to match it to a generic criterion by keyword (coverage / complete / all lines → COVERAGE; stray / extra / clean → PRECISION; dots → DOTS; continuous / lift → CONTINUITY; loop / curve → CURVES).
   - If it matches, apply the user's `weight` and `required` to that criterion and keep the engine's name.
   - If it doesn't match, add a warning ("criterion '<name>' has no measurable engine metric; consider rubric review") and drop it.
   - Ignore `method == "vlm_status"` items in this engine and add a warning. The composer only creates those for `rubric_vlm`.
5. **Optional Gemma description:** in generic mode, call it with the generic text from `_TEXT_GENERIC` and keep the existing ModelError → warning behaviour.

## 4. Origami engine with a profile (family `video_states`)
1. **Prompts:** create the v2 prompts with placeholders `{skill_title}`, `{state_noun}` (default "state"), `{object_noun}` (default "object") and `{goal_hint}` (default "none"). Remove every origami/paper/crane/fold-specific instruction from v2: describe "visibly distinct {state_noun}s of the {object_noun}". In generic mode, the builder and evaluator load v2 (`load_prompt(..., skill_title=…)`); hero mode keeps v1.
2. **Window:** for composed cases `source.window_sec` is None, so use the full video. If it is longer than 120 s, raise INVALID_INPUT (the composer already limits this).
3. **Frames:** keep the batching and timeout policy chosen in K4 (read the K4 report and code). Do not change it.
4. **Criteria:** same five metric templates with generic ids `CRIT-SEQ-FINAL`, `CRIT-SEQ-ORDER`, `CRIT-SEQ-COMPLETE`, `CRIT-SEQ-CLEAN`, `CRIT-SEQ-KEYSTEP`, and generic names ("reaches the final {state_noun}", …). Apply the user criteria the same way as §3.4, using these keywords: final / end / result → FINAL; order / sequence → ORDER; all / complete / every → COMPLETE; mistake / wrong / off → CLEAN; key / critical → KEYSTEP.
5. **Evaluator:** with a profile, use `origami_match_v2.txt`. Findings text must say "{state_noun}", not "fold". The evaluator gets the profile through the goal model: store `profile_vocabulary` and `skill_title` in the goal payload's `built_with` (or in a new optional payload field `vocabulary`, added to `tracks/common/goals/origami.py` as an optional field with a default, so existing goal files still validate). Track B must not import track_a or composer code.

## 5. New engine `rubric_vlm` (general rubric review)
Use it when nothing deterministic fits. It is honest and lower confidence.

### 5.1 Payload: `tracks/common/goals/rubric_vlm.py`
```python
class RubricVlmCriterion(BaseModel):
    criterion_id: str; name: str; observable_indicator: str
class RubricVlmGoal(BaseModel):
    source_modality: Literal["image", "video", "audio"]
    reference_assets: list[str]          # goal_assets file names: reference image(s) / keyframes (max 3); [] for audio
    reference_description: str           # model description of the reference (INFERRED)
    criteria: list[RubricVlmCriterion]   # from the confirmed profile
    vocabulary: dict[str, str] = {}
    skill_title: str
PAYLOAD_MODEL = RubricVlmGoal
def ui_view(payload) -> dict: {"source_modality", "reference_assets", "criteria", "skill_title"}
```

### 5.2 Builder: `track_a/goals/rubric_vlm.py`
`build(..., profile)` requires a profile; raise INVALID_INPUT without one.
- **Reference assets:**
  - image: save a JPEG copy (max side 768) as `knowledge/goal_assets/rubric_ref_0.jpg`;
  - video: 3 frames at 20%, 60% and 95%, saved as `rubric_ref_0..2.jpg`;
  - audio: none.

  Write the files under `ctx.case_dir / "knowledge" / "goal_assets"`, the same convention the Origami builder uses.
- **One model call** (`rubric_vlm_goal_v1.txt`; model_key `text_image` for image/video with the reference images; `audio` for audio with the WAV, ≤ 30 s). DTO: `{reference_description: str (≤ 600 chars), visible_properties: [str] (≤ 8)}`. On ModelError, raise it; this engine needs the model.
- **Claims:**
  - Probe facts are OBSERVED. Image: an `#xywh=percent:0,0,100,100` locator stating the dimensions. Video/audio: an interval [0, duration] stating the duration.
  - Each model-visible property is INFERRED, confidence 0.5, with the same whole-source locator, `verification_state="inferred"`, `is_observed=False`.
  - **One inferred STEP claim** "Reproduce the reference as described (inferred)", needed because the grounding check requires a goal-conditioned case to have at least one inferred STEP.
- **Criteria:** exactly the profile's criteria (method `vlm_status`; skip others with a warning; if there are none, create one default criterion "Matches the reference overall").
  - Each binding: `metric=f"vlm.{criterion_id}"`, `direction="higher_is_better"`, `bands=[{status:"satisfied", min:1.0}, {status:"partially_satisfied", min:0.5}]`, `otherwise="not_satisfied"`, `process=False`.
  - `why_it_matters` cites the STEP claim id, e.g. "Judged against the reference description (CLM-0n)".
  - Weights and required flags come from the profile.
- **Task:** numbered instructions listing the criteria and citing [CLM-xx]. Constraints say the learner uploads the same kind of media.
- **Warnings** always include `"General rubric review: judgements are model-assisted and lower confidence."`

### 5.3 Evaluator: `track_b/evaluators/rubric_vlm.py`
`evaluate(goal, attempt, ctx)`:
- **Accepted kinds:** the source modality's kind ("image", "video" or "audio"). Otherwise raise INVALID_INPUT.
- **Inputs to the model:**
  - image: the reference image(s) plus the learner image (max side 512);
  - video: reference frames plus 4 learner frames at 20/45/70/95% (max side 384);
  - audio: learner WAV ≤ 30 s, with the reference description as text. The audio model must be enabled, otherwise every metric is `value=None` with reason "audio_model_disabled".

  Respect the K4 latency findings: at most 5 images per call.
- **Prompt** `rubric_vlm_judge_v1.txt`. For each criterion it asks for `{criterion_id, status: "met"|"partly"|"not_met"|"cannot_tell", finding (≤ 200 chars, what is visible/audible), region (optional {x,y,w,h} percent of the learner image), time_sec (optional)}`. The prompt forbids scores and numbers other than positions.
- **Deterministic mapping:** met → 1.0, partly → 0.5, not_met → 0.0, cannot_tell → `None` (uncertain_reason "model could not tell from the evidence"). An unknown criterion id is ignored with a warning; a missing criterion gets None with reason "not reported by model".
- **MetricValue:** `vlm.<criterion_id>` with the finding. Evidence: image → `with_region(attempt.source_id, …)` when a region is given, else the whole-image region; video → `with_frame(attempt.source_id, time_sec)` with `start_sec/end_sec`; audio → an interval.
- **TrajectoryResult:**
  - `events`: one event per not_met criterion, with `severity="material"`, `kind="criterion_not_met"`, `position` = the criterion's index in the goal's criteria list (0-based), `position_kind="stroke"`. Partly-met criteria get `severity="minor"`. cannot_tell criteria get no event.
  - `curve`: `[(0, 0), (1, fraction met)]`, `curve_kind="stroke"`.
  - `process_observable=False`, `run_keys` set, `warnings` include the lower-confidence notice.

## 6. Tests (fake gateway, no network)
- **`test_engines_profile.py`:**
  - (a) hero kolam and origami builds with `profile=None` are byte-identical to the committed v1 artifacts (recorded mode);
  - (b) a generic Kolam build on a synthetic dot-less drawing (circle plus spiral) has no dot claims, no DOTS criterion and generic ids and wording (assert that no claim, task or criterion text contains "kolam" or "pulli");
  - (c) a generic Origami build loads the v2 prompts (spy on `load_prompt` or check the replay key/prompt id) and has no "fold/crane/origami" in claims or criteria;
  - (d) user criteria keyword matching applies weight and required, and unmatched criteria give a warning.
- **`test_rubric_vlm_goal.py`:** a build from an image profile writes the reference asset, has the OBSERVED probe claim plus INFERRED property claims plus an inferred STEP, the bindings and the warning. A missing profile raises INVALID_INPUT. ModelError propagates.
- **`test_rubric_vlm_eval.py`:**
  - the status → value mapping, including cannot_tell → None;
  - an unknown criterion is ignored;
  - a missing criterion → None;
  - audio with the model disabled → all None;
  - the image-count limit per call;
  - an end-to-end Track B session on a synthetic rubric_vlm case pack (write files in tmp, as `tracks/track-b/tests/core_fixtures.py` does) produces a validator-clean bundle with evaluator_type MODEL_ASSISTED.

## 7. Live check (with key; record in report)
Build and evaluate a `rubric_vlm` case from `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\var\kiro\media\kolam\` (any PNG) with 2 hand-written criteria: one learner image = the same PNG (expect met), one = the PNG with half of it painted white using Pillow (expect partly or not_met). Record latency, statuses and findings.

## 8. Acceptance
- Hero byte-identity is proven, and all new tests pass.
- The Definition of Done in 00-COMMON.md is met. Report: `docs/kiro/reports/K7-REPORT.md`, including the live-check table.
