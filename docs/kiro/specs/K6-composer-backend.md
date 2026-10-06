# K6: Case Composer backend (new-skill onboarding: probe → analyse → draft → create)

Read `docs/kiro/specs/00-COMMON.md` first, then **`docs/plans/case-composer.md` in full** (it is the design you implement). Folder `...\anveshan-wt\k6-composer`, branch `kiro/k6-composer`; Jim or Claude Code creates it from `m1/hero-cases` **after K1–K4 are merged**. **Needs the API key** (copy `.env`, which already sets `ANVESHAN_AUDIO_MODEL=gemini-3.5-flash-lite`).

You implement the **backend only**. K7 (engines) and K8 (UI) run in parallel; do not edit their files.

## 0. Existing code you will use (read these first)
- `tracks/common/profile.py`: `CaseProfile`, `ProbeFacts`, `CriterionSuggestion`, `FAMILY_MODALITY`, `FAMILY_LABEL`, `FAMILY_INPUT_KINDS`, `slugify`, `composed_case_id`. **Do not change field names.** If you truly need a field, add an optional one and say so in your report.
- `tracks/common/media.py`: `probe(path) -> MediaInfo` (duration_sec, has_audio, has_video, width, height, fps), `sample_frames(path, fps, start_sec, end_sec, max_side, max_frames)`, `decode_audio(path, sample_rate, start_sec, end_sec)`, `sha256_file`, `image_to_jpeg_bytes`.
- `tracks/common/kolam_geometry.py`: `load_gray(path)`, `binarize(gray) -> (mask, info)` (look inside `info` for the Otsu threshold/separation keys; if none expresses separation, compute it yourself as described in §2.2), `label_components(mask) -> (labels, n)`, `thin(mask)`.
- `tracks/common/onsets.py`: `detect_onsets(x, sr) -> Onsets` (`times_sec`, `strength`, `low_ratio`).
- `tracks/common/tabla_dsp.py`: `percussive_contrast(x, sample_rate) -> float`.
- `tracks/common/models.py`: `ModelGateway.generate_json(model_key, prompt_id, prompt_version, prompt_text, schema, parts, system)`, `ImagePart`, `AudioPart`, `load_prompt(path, **values)`, `AnveshanFailure`, `FailureCategory`, `ModelError`.
- `tracks/common/runtime.py`: `RunContext.create(case_dir, data_dir, mode)`.
- `tracks/common/casedata.py`: `SourceRegistry`, `SourceRecord`, `write_json`, `versioned_path`, `latest_version`, `load_versioned`.
- `tracks/track-a/src/track_a/config.py`: `HERO_CASES`, `modality_for`, `base_case_id`, `UPLOAD_LICENSE`, `UPLOAD_CREATOR`.
- `tracks/track-a/src/track_a/api.py`: `build_case`, `load_case`, `list_cases`, `create_upload_case` (copy its manifest-writing approach; it already produces schema-valid manifests).
- `service/anveshan_service/`: `main.py` (router registration), `routes/cases.py` (multipart upload handling via `store_upload`), `adapters.py` (lazy track imports, `translated()` error mapping), `paths.py` (id regex), `settings.py`.

## 1. Files you own
- **New:** `tracks/track-a/src/track_a/composer.py`, `tracks/track-a/prompts/composer_analyze_v1.txt`, `tracks/track-a/tests/test_composer.py`, `service/anveshan_service/routes/compose.py`, `service/tests/test_service_compose.py`.
- **Edit:**
  - `tracks/track-a/src/track_a/config.py` (only `modality_for` + composer constants);
  - `tracks/track-a/src/track_a/api.py` (only: `build_case` passes `profile=` when the builder accepts it; `list_cases` includes composed cases; `CaseHandoff.to_view()` adds a `profile` key);
  - `service/anveshan_service/main.py` (register the router);
  - `service/anveshan_service/adapters.py` (only if you need a helper);
  - `docs/plans/service-api.md` (add the compose endpoints table from case-composer §8);
  - `tracks/track-b/src/track_b/handoff.py` (only if Track B fails to load a composed case; see step 8).

## 2. `track_a/composer.py`: implement exactly these functions

### 2.1 Types
```python
@dataclass
class Draft:
    draft_id: str                 # sha256[:16]
    dir: Path                     # <data_dir>/drafts/<draft_id>
    source_path: Path             # <dir>/source<ext>
    probe: ProbeFacts
    proposal: CaseProfile         # unconfirmed (confirmed_by_user=False)
    warnings: list[str]
    def to_view(self) -> dict     # {"draft_id","probe","proposal","warnings","family_labels": FAMILY_LABEL}
```

### 2.2 `probe_source(path: Path, mime: str) -> ProbeFacts`
Deterministic, no model.

**Modality from mime prefix:** image/ → image, video/ → video, audio/ → audio; otherwise raise `AnveshanFailure(INVALID_INPUT, "Unsupported file type …")`. Use `media.probe` for duration, size and has_audio (images: open with PIL for width and height).

**Limits** (raise INVALID_INPUT with a learner-readable message): size ≤ 30 MB; video duration ≤ 120 s; audio duration ≤ 60 s and ≥ 3 s; video ≥ 8 s.

**Metrics and allowed families**, rounded to 4 dp, written into `metrics` and `family_reasons`:

- **image**
  - `gray = load_gray(path)`; `mask, info = binarize(gray)`.
  - `ink_fraction = mask.mean()`.
  - `otsu_separation`: let t be the Otsu threshold (from `info` or `otsu_threshold(gray)`). Separation = |mean(gray > t) − mean(gray ≤ t)| / 255.
  - `skeleton_len_ratio = thin(mask).sum() / max(w, h)`.
  - `big_components`: number of components in `label_components(mask)` whose area > 0.5% of ink.
  - Allow `image_target` iff `otsu_separation ≥ 0.25 and 0.01 ≤ ink_fraction ≤ 0.40 and skeleton_len_ratio ≥ 0.5 and big_components ≤ 6`.
  - The reason text lists each check with its value and pass/fail, e.g. `"ink_fraction=0.08 ok; otsu_separation=0.61 ok; skeleton_len_ratio=3.2 ok; big_components=1 ok"`.
  - Always allow `rubric_vlm`.
- **video**
  - `frames = sample_frames(path, fps=1.0, max_side=160, max_frames=120)`.
  - Convert to grayscale arrays. For consecutive pairs, compute the changed-pixel fraction (|diff| > 25).
  - `change_active_ratio` = fraction of pairs with changed fraction > 0.01.
  - Allow `video_states` iff duration ≥ 8 and `change_active_ratio ≥ 0.30`.
  - If `has_audio`, also run the audio checks below on the decoded audio track (first 60 s) and allow `audio_rhythm` if they pass.
  - Always allow `rubric_vlm`.
- **audio**
  - `x = decode_audio(path, 16000, 0, 60)`; `on = detect_onsets(x, 16000)`.
  - `onset_rate = len(on) / duration`; `percussive_contrast = percussive_contrast(x, 16000)`.
  - Allow `audio_rhythm` iff `onset_rate ≥ 1.5 and duration ≥ 6 and percussive_contrast ≥ 1.5`.
  - Allow `rubric_vlm` only if `ModelRegistry().enabled("audio")`; otherwise give the reason "audio model disabled".
- If no family is allowed, raise INVALID_INPUT ("We can't evaluate this file yet: …reasons").

### 2.3 `analyze(probe, source_path, ctx, *, title_hint: str | None, description: str | None) -> tuple[dict, list[str], list[str]]`
Returns `(proposal_dict, run_keys, warnings)`. At most **one** model call:

- **image:** `model_key="text_image"`, parts = `[ImagePart(jpeg of the image downscaled to max 512 px, label="Uploaded source image:")]`.
- **video:** `model_key="video_frames"`, parts = 3 frames at 10%, 50% and 90% of the duration (max_side 384), labelled `"Frame t=<s>s"`.
- **audio:** `model_key="audio"` if enabled, part = `AudioPart(wav of the first 30 s at 16 kHz)` (use `tabla_dsp.wav_bytes`). If the audio model is disabled, make no call and return a deterministic proposal (below) with a warning.

**Prompt** (`composer_analyze_v1.txt`), rendered with `load_prompt` and these placeholders:
- `{modality}`
- `{probe_facts_json}`: compact JSON of `metrics`, duration, size
- `{allowed_families_json}`: list of `{id, label}` from `FAMILY_LABEL` for **allowed families only**
- `{title_hint}`, `{description}` (or "none")

The prompt must say:
1. Return JSON only, matching the schema below.
2. `family` MUST be one of the allowed ids.
3. Do not claim who made the source, its history, cultural meaning or original procedure. Describe only what is visible or audible.
4. `observable_indicator` must name something a camera or microphone can check.
5. If unsure, say so in `concerns`.

**Response DTO** (Pydantic, `extra="ignore"`):
```python
class AnalysisDTO(BaseModel):
    title: str                        # ≤ 60 chars
    skill_summary: str                # ≤ 300 chars
    domain: str                       # ≤ 60 chars
    family: str
    transmission_mode: Literal["forward", "goal-conditioned", "corrective"]
    vocabulary: dict[str, str] = {}   # keys allowed: state_noun, object_noun, unit_noun, action_verb
    criteria: list[dict] = []         # each {name, observable_indicator}; ≤ 6 items
    concerns: list[str] = []
```

**Validation after the call:**
- If `family` is not in allowed → replace it with the deterministic default (below) and add a warning "model proposed <x>, not allowed; using <y>".
- Truncate over-long strings.
- Keep only allowed vocabulary keys.
- Drop criteria whose `observable_indicator` is empty.

**Deterministic default family** (also used when the model fails or is disabled):
image_target > video_states > audio_rhythm > rubric_vlm, choosing the first one that is allowed.

**Default transmission mode:** image_target → goal-conditioned; video_states → forward; audio_rhythm → forward; rubric_vlm → goal-conditioned for an image source, forward otherwise.

On `ModelError`: catch it, use the deterministic proposal (title = title_hint or "Untitled skill", summary = description or "", domain = "unspecified", no criteria), and add the warning `"AI analysis unavailable: <category>"`. Never invent content.

### 2.4 `create_draft(data_dir, file_path, mime, ctx, *, title_hint=None, description=None, rights_confirmed: bool) -> Draft`
1. `rights_confirmed` must be True; otherwise INVALID_INPUT ("Please confirm you have the right to use this file.").
2. Compute sha256; `draft_id = sha[:16]`; copy the file to `<data_dir>/drafts/<draft_id>/source<ext>`, keeping the original extension in lowercase.
3. Run `probe_source`, then `analyze`.
4. Build `proposal = CaseProfile(case_id=composed_case_id(title, sha), …, criteria=[CriterionSuggestion(criterion_id=f"CRIT-{slug.upper()[:12]}-{i:02d}", name, observable_indicator, weight=2.0, required=(i==1), method="engine_default" if family != "rubric_vlm" else "vlm_status")…], probe=probe, model_proposal=<validated dto dict>, model_run_keys=run_keys, confirmed_by_user=False, warnings=…)`.
   - Strip non-alphanumerics from the slug used in criterion ids.
   - `learner_input_kinds` = `FAMILY_INPUT_KINDS[family]` filtered by the source modality (for rubric_vlm, only the source's own modality).
5. Write `draft.json` (`write_json`, the `Draft.to_view()` dict) and return the Draft.
6. Calling it again with the same file returns the existing draft without a new model call: check `draft.json` first.

### 2.5 `load_draft(data_dir, draft_id) -> Draft`
Validate `draft_id` against `^[0-9a-f]{16}$` and that the path stays inside drafts/. Raise MISSING_EVIDENCE if absent.

### 2.6 `create_case_from_draft(cases_root, data_dir, draft_id, edits: dict, ctx_factory) -> Path`
- `edits` contains the user-confirmed fields: `title, skill_summary, domain, family, transmission_mode, learner_input_kinds, vocabulary, goal_hint, criteria` (list of `CriterionSuggestion` dicts).
- Validate by constructing `CaseProfile(**proposal fields updated with edits, confirmed_by_user=True, confirmed_at=<UTC ISO>)`. Pydantic enforces family-in-allowed and kinds-per-family. On a pydantic error, raise INVALID_INPUT with the message.
- `case_id = composed_case_id(edits["title"], probe.sha256)`; `case_dir = <data_dir>/cases/<case_id>`. If it already exists with a confirmed profile, return it (idempotent).
- Write the manifest, copying the structure `create_upload_case` uses, and make it pass `.github/scripts/check_case_packs.py`'s schema validation. Use:
  - `case_id`, `bundle_case_id=case_id`, `title=edits.title`, `domain=edits.domain`, `archetype=<family>`;
  - `workspace_type` by family: image_target→`spatial_canvas`, video_states→`spatial_sequence`, audio_rhythm→`rhythm_envelope`, rubric_vlm→`rubric_review`;
  - `transmission_mode`, `source_mode` (upper-case with `_`);
  - the same values `create_upload_case` uses for `source_posture`, `epistemic_status`, `data_status`, `status`, `runtime_class`;
  - `source_media={type: local_file, path: "source/upload.<sha12><ext>", mime_type, attribution: "user upload — rights asserted by uploader"}`.
- Copy the source to `source/upload.<sha12><ext>`. Write `source/source.json`:
  - one `SourceRecord`: `source_id=f"upload.{sha12}"`;
  - role by family/modality: image → `target_image`; video → `expert_video`; audio → `expert_audio`;
  - `runtime_label="UPLOAD"`, `license=config.UPLOAD_LICENSE`, `creator=config.UPLOAD_CREATOR`, `access_level="approved_learners"`;
  - dimensions or duration from the probe.
- Write `knowledge/case_profile.v1.json`.
- Return `case_dir`. The **caller** then runs `build_case(case_dir, ctx)`.

## 3. `config.modality_for(case_id)` (edit)
Follow the order in case-composer §6. For composed cases (`<slug>~<sha12>` whose base is not a hero case), read the latest `knowledge/case_profile.v*.json` under `<data_dir>/cases/<case_id>/` (the function may need a `case_dir` parameter; add an optional `case_dir: Path | None = None` and update the call sites in `api.py`) and return `FAMILY_MODALITY[family]`. Hero and hero-derived behaviour must not change (the existing tests must pass).

## 4. `api.build_case` (edit)
After resolving the modality, load the profile if one exists. Call the builder with `profile=profile` **only if** `inspect.signature(builder).parameters` contains `profile` (K7 adds it). Otherwise call without it and add the warning `"builder does not yet support profiles; using default wording"`. For `rubric_vlm`, if `track_a.goals.rubric_vlm` is not importable yet, raise `AnveshanFailure(MODEL_FAILURE, "rubric_vlm engine not installed yet")`; it lands with K7.

## 5. `api.list_cases` and `to_view` (edit)
- Composed cases appear with `{case_id, title, modality, hero: False, runtime_label: "UPLOAD", review_status, built, composed: True, family}`.
- `to_view()` includes `"profile": <profile dict or None>`.

## 6. Service routes (`routes/compose.py`)
Follow case-composer §8 exactly:
- `POST /api/compose/analyze`: multipart `file` (stored with the existing `store_upload` helper and its size limit), form fields `title`, `description`, `rights_confirmed` ("true"/"false"). Builds a ctx with `adapters.run_context(settings, settings.data_dir / "drafts", mode)`; a composer-specific RunStore root is fine, since runs are recorded wherever ctx points. Returns `Draft.to_view()`.
- `GET /api/compose/{draft_id}`
- `POST /api/compose/{draft_id}/create`: JSON body = `edits`. Calls `create_case_from_draft`, then `build_case(case_dir, ctx)`, then returns `load_case(case_dir).to_view()`.

All errors go through the existing `adapters.translated()` so they get the standard `{"error": …}` body. Register the router in `main.py` under `/api/compose`.

## 7. Tests (no network; fake gateway clients as in `tracks/common/tests/test_foundation.py`)
- **`tracks/track-a/tests/test_composer.py`:**
  - **probe:**
    - Image: a synthetic line drawing (Pillow: white background, a black circle and a cross, 400×400) allows `image_target` and `rubric_vlm`. A photo-like noise image allows `rubric_vlm` only.
    - Video: a generated mp4 with moving content allows `video_states`; a static one does not (generate it with PyAV as in `test_foundation.py::test_sample_frames_deterministic`).
    - Audio: a click-track WAV (reuse the `click_track` helper idea) allows `audio_rhythm`; silence raises INVALID_INPUT.
    - The size and duration limits are enforced.
  - **analyze:**
    - A fake model returning a valid DTO produces the proposal.
    - A model choosing a disallowed family is replaced, with a warning.
    - A ModelError gives the deterministic proposal plus a warning.
    - The audio model being disabled means no call and a warning.
  - **create_draft:** rights not confirmed raises INVALID_INPUT; the second call is idempotent and makes no extra model call.
  - **create_case_from_draft:**
    - the manifest validates with the case-pack schema checker (import and call its validation function, or run the script against a temp copy);
    - `source.json` and the profile are written;
    - a disallowed family in the edits raises INVALID_INPUT;
    - a second create is idempotent.
  - **modality_for:** hero, hero-derived and composed cases all resolve correctly.
  - **build_case on a composed image_target case** (fake builder via monkeypatch, as the existing Track A tests do) receives `profile`.
- **`service/tests/test_service_compose.py`:** the three endpoints with monkeypatched composer functions, plus error mapping (400 for rights not confirmed, 404 for an unknown draft).

## 8. Live check (manual, recorded in the report)
With the key, run the full flow for:
- (a) a Kolam diagram from `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\var\kiro\media\kolam\kolam_8_mayoo.png`;
- (b) the tabla clip `...\var\kiro\media\tabla\` (the shortest file);
- (c) a 20–40 s cut of any video. Cut it with PyAV into your worktree's `var/`; `tracks/cases/origami/media/cache/` after `tools/fetch_media.py` is a good source.

For each, record the probe metrics, allowed families, the proposal, warnings, latency and whether `build_case` succeeded. If (a)'s build fails because the Kolam builder doesn't take `profile` yet, that's expected until K7. Record it.

If Track B fails to load a composed case in a quick `track_b.api.start_session` test, fix only `track_b/handoff.py` (it must read `goal.modality` and not assume a hero case id). Add a test.

## 9. Acceptance
- All new tests pass, and the Definition of Done in 00-COMMON.md is met.
- `docs/plans/service-api.md` has the compose endpoints.
- The live check is recorded in `docs/kiro/reports/K6-REPORT.md` (no key or secrets).
