# K6: Universal pipeline, part 1 — Intake gates + Layer 1 Perception + Composer API

Read `docs/kiro/specs/00-COMMON.md` first, then **`docs/plans/universal-pipeline.md` in full** (the architecture you implement). Folder `...\anveshan-wt\k6-composer`, branch `kiro/k6-composer`; created from `m1/hero-cases` after K1–K4 are merged. **Needs the API key** (copy `.env`).

You build **Layer 1 (perception) + intake gates + the composer draft API**. K7 builds Layer 2 (SkillModel builder) and Layer 3 (universal evaluator) in parallel, **on top of your `perceive()`**. K8 builds the UI. Keep the function signatures in §2 exactly as written; K7 codes against them.

## 0. Shared code already written (use it; do not change field names)
- `tracks/common/perception.py`: `PerceptionRecord`, `Segment`, `Observation`, `MediaInfoRecord` (validators: model-produced observations cannot be "observed").
- `tracks/common/skill_model.py`: `SkillModel`, `TargetProperty`, `Step`, `Constraint`, `Check`, `Relevance`, `STRUCTURE_CHECKS`, `STRUCTURE_ATTEMPT_KINDS`.
- `tracks/common/profile.py` (v2): `CaseProfile`, `ProbeFacts`, `IntakeResult`, `STRUCTURE_LABEL`, `SPECIALIST_LABEL`, `slugify`, `composed_case_id`, `COMPOSED_MODALITY="universal"`.
- `tracks/common/policy.py`: `REFUSE_CATEGORIES`, `FLAG_CATEGORIES`, `safety_decision(categories)`, `REFUSE_TEACHABILITY_MESSAGE`.
- `tracks/common/models.py`:
  - `ModelGateway.generate_json(...)`;
  - **`ModelGateway.embed(items, purpose, model_key="embedding", dims=768)` → `EmbeddingResult(vectors (n,768) unit float32, metadata)`**, recorded and replayable;
  - registry keys `vision_fast` (gemini-3.5-flash-lite), `audio` (gemini-3.5-flash-lite via env), `embedding` (gemini-embedding-2), `text_image` (gemma).
- `tracks/common/media.py` (probe, sample_frames, decode_audio, sha256_file, image_to_jpeg_bytes), `tracks/common/onsets.py` (detect_onsets), `tracks/common/tabla_dsp.py` (percussive_contrast, wav_bytes, estimate_pulse), `tracks/common/kolam_geometry.py` (load_gray, binarize, otsu_threshold, label_components, thin).
- **Measured latencies (2026-10-06):**
  - vision_fast: 1 image 2.5 s, 4 images 8.9 s;
  - embedding: 5 images 1.3 s;
  - audio: a 12 s clip in 2.7 s.

  **Use at most 4 images per vision_fast call.**

## 1. Files you own
- **New:**
  - `tracks/common/perceivers/__init__.py`, `tracks/common/perceivers/image.py`, `video.py`, `audio.py`, `screen.py`, `specialist_probe.py`
  - `tracks/common/prompts/perceive_image_v1.txt`, `perceive_frames_v1.txt`, `perceive_audio_v1.txt`
  - `tracks/track-a/src/track_a/composer.py`
  - `service/anveshan_service/routes/compose.py`
  - tests: `tracks/common/tests/test_perceivers.py`, `tracks/track-a/tests/test_composer.py`, `service/tests/test_service_compose.py`
- **Edit:**
  - `tracks/track-a/src/track_a/config.py` (only `modality_for`; see §5)
  - `tracks/track-a/src/track_a/api.py` (only `list_cases` + `to_view` additions; see §5)
  - `service/anveshan_service/main.py` (router registration)
  - `docs/plans/service-api.md` (compose endpoints)
  - `.env.example` (document `ANVESHAN_VISION_FAST_MODEL`, `ANVESHAN_EMBEDDING_MODEL`)

## 2. Layer 1 API (`tracks/common/perceivers/__init__.py`): exact signatures
```python
def perceive(path: Path, mime: str, ctx: RunContext, *, source_id: str, asset_dir: Path,
             purpose: Literal["source", "attempt"], skill_hint: str | None = None,
             want_specialists: bool = True) -> PerceptionRecord
def load_embeddings(record: PerceptionRecord, record_dir: Path) -> np.ndarray   # rows aligned to record.embedding_index
def save_record(record: PerceptionRecord, path: Path) -> None                   # writes JSON (+ the .npy must already sit next to it)
def load_record(path: Path) -> PerceptionRecord
```
- `perceive` dispatches on the mime prefix to `perceive_image` / `perceive_video` / `perceive_audio` in the modality modules (same keyword arguments).
- `asset_dir` is where keyframe JPEGs and the embeddings `.npy` are written. Use file names `kf_<segment_id>.jpg` and `emb_<record sha[:12]>.npy`, and set `record.embeddings_file` to the .npy file name (relative to `asset_dir`).
- `purpose="source"` also runs the intake screen (safety + teachability) and stores the result in `record.gates["intake"]`. `purpose="attempt"` skips the screen.
- Every model call goes through `ctx.gateway`; collect `metadata.replay_key` values into `record.runs`.
- **Deterministic ids:** segments `seg-000…` in time order (image: `seg-000` = whole, then `seg-001…` for regions). Observations `obs-000…` in creation order.

### 2.1 `perceive_image`
1. **Deterministic** (`det:image_basic`): width, height, mean brightness (0–1), RMS contrast, blur score (variance of a 3×3 Laplacian on gray, implemented with numpy), ink fraction and Otsu separation (via `binarize`/`otsu_threshold`). Add each as an `Observation(kind="measurement", certainty="observed", producer="det:image_basic", label=<name>, value=…)` on `seg-000` (kind "whole").
2. **Embedding:** one call, `gateway.embed(items=[ImagePart(jpeg max 768 px)] + 4 tile crops (2×2 grid, each max 384 px), purpose=f"{purpose}_image")`.
   - Segments: `seg-000` whole, `seg-001…seg-004` regions `[0,0,50,50]`, `[50,0,50,50]`, `[0,50,50,50]`, `[50,50,50,50]`.
   - Save a float16 `.npy` with 5 rows; `embedding_index = {seg-000:0, seg-001:1, …}`.
3. **Perception call** (`vision_fast`, prompt `perceive_image_v1.txt`, the whole image ≤ 768 px). Response DTO:
   ```python
   class ImagePerceptionDTO(BaseModel):
       artefact_kind: str                     # e.g. "line drawing", "plated dish", "person in a pose"
       objects: list[str] = []                # ≤ 10
       properties: list[{"label": str, "detail": str, "region": [x,y,w,h] | None}] = []   # ≤ 12, visible facts only
       visible_mistakes_to_avoid: list[str] = []   # ≤ 5, things a learner could get wrong that are checkable in a photo
       plausible_build_order: list[{"step": str, "region": [x,y,w,h] | None}] = []  # ≤ 8 (backward interpolation; INFERRED)
       safety_categories: list[str] = ["none"]   # from the allowed list given in the prompt
       teachable: "yes" | "no" | "unclear"; teachable_reason: str; skill_kind: str
   ```
   Map to observations:
   - `objects` → kind "object";
   - `properties` → kind "property" (on the matching region segment if a region is given; otherwise on whole). Add a **new region segment** for each property region (`seg-005…`), clamped to [0,100];
   - `visible_mistakes_to_avoid` → kind "quality" with label prefix "avoid: ";
   - `plausible_build_order` → kind "action" with label prefix "build step i: ".

   All of these use `certainty="inferred"`, `producer="model:vision_fast"`. Store `artefact_kind` / `skill_kind` / `teachable*` / `safety_categories` in `record.gates["intake"]` (source only), via `screen.py` (§2.4).

   The prompt must list the allowed `safety_categories` (the keys of `REFUSE_CATEGORIES` + `FLAG_CATEGORIES` + "none") and say: describe only what is visible; no identity, history or meaning claims; regions are percentages.

### 2.2 `perceive_video`
1. **Deterministic segmentation** (`det:video_segment`): `sample_frames(path, fps=1.0, max_side=256, max_frames=120)`.
   - Gray frames; `diff[i]` = mean |frame[i] − frame[i−1]| / 255.
   - Smooth with a 3-tap moving average. A frame is **still** if `diff < 0.02`, else **active**.
   - Segments = maximal runs of equal still/active label. Merge runs shorter than 2 s into the previous segment.
   - Cap at 12 segments by merging the shortest neighbouring pair repeatedly.
   - Each segment's keyframe = the frame with the minimum diff inside it; its stability = 1 − mean diff (clamped 0..1). Save keyframes (max side 384) as `kf_seg-NNN.jpg` in `asset_dir`.
   - Measurement observations on whole-video segment `seg-000`: duration, segment count, active fraction. Each time segment is `seg-001…` (the time segments; also create `seg-000` kind "whole").
2. **Embeddings:** keyframes (one per segment) **and** per-second frames (all sampled frames, max side 256) in one `embed` call (`purpose=f"{purpose}_frames"`).
   - `embedding_index`: `seg-NNN` → its keyframe row.
   - Frame rows: `frame-<index>` keys are **not** segments, so store the frame times and row indices in `record.specialists["frames"] = {"times": [...], "rows": [...]}`. The `.npy` holds keyframe rows first, then frame rows.
3. **Perception calls** (`vision_fast`, prompt `perceive_frames_v1.txt`): send keyframes in batches of ≤ 4, each as `ImagePart(label=f"Segment {segment_id} keyframe at t={keyframe_sec:.1f}s")`. DTO per batch:
   `{"segments":[{"segment_id":str, "state":str, "action":str|None, "objects":[str], "notes":str|None}], "safety_categories":[...], "teachable":..., "teachable_reason":..., "skill_kind":...}`.
   - Map to `state` / `action` / `object` observations (inferred) on that segment. Ignore unknown segment ids, with a warning.
   - Only the **first** batch needs the safety/teachability fields; merge categories across batches (union).
   - **If the video has an audio track:** also run `perceive_audio` on the audio track (decode with PyAV to WAV in memory), store that record in `record.specialists["audio_track"]` (as a dict), and merge its intake categories.

### 2.3 `perceive_audio`
1. **Deterministic** (`det:audio_signal`): decode to 16 kHz mono (`decode_audio`; ≤ 60 s). Compute and record as measurement observations on `seg-000`:
   - duration, RMS, clipping fraction;
   - onsets (count, rate);
   - `percussive_contrast`;
   - **speech-likeness:** spectral flatness mean (numpy) and 4 Hz modulation energy ratio (envelope FFT power at 3–6 Hz over 0.5–20 Hz);
   - pulse (via `tabla_dsp.estimate_pulse` when onsets ≥ 8; else None).

   Time segments: split at silences ≥ 0.4 s (energy < 10% of the median); at most 20 segments.
2. **No embeddings for audio** (audio embedding is expensive). Leave `embeddings_file=None`.
3. **Perception call** (`audio` model key; skip with a warning if disabled; prompt `perceive_audio_v1.txt`; WAV ≤ 30 s). DTO:
   `{"audio_kind": "speech"|"music"|"percussion"|"environment"|"mixed", "transcript": str|None, "language": str|None, "events":[{"label":str,"approx_sec":float|None}], "instrument": str|None, "safety_categories":[...], "teachable":..., "teachable_reason":..., "skill_kind":...}`.
   - Transcript → a `speech` observation (inferred).
   - Events → `event` observations attached to the time segment containing `approx_sec` (else whole).
   - Instrument → an `object` observation.

### 2.4 Intake screen (`screen.py`)
`intake_from_perception(record) -> IntakeResult`. It combines the model's `safety_categories` (via `policy.safety_decision`), `teachable`, `teachable_reason` and `skill_kind`, plus deterministic overrides:
- an image with contrast < 0.03 or ink_fraction < 0.002 → teachable "no" ("blank or near-blank image");
- audio with RMS < 0.005 → teachable "no" ("silence");
- video with active fraction < 0.05 **and** segment count ≤ 1 → teachable "unclear" ("nothing visibly changes").

If the model call failed or was disabled → teachable "unclear" with reason "AI screen unavailable", and safety from deterministic only (`["none"]`), plus a warning.

### 2.5 Specialist availability (`specialist_probe.py`)
`available_specialists(record, path) -> dict[name, (bool, reason)]`, using the thresholds in universal-pipeline §3.3:
- **line_art:** image; separation ≥ 0.25, ink 1–40%, skeleton length ratio ≥ 0.5, ≤ 6 big components.
- **rhythm:** audio, or a video's audio track; onset rate ≥ 1.5/s over ≥ 6 s, and percussive contrast ≥ 1.5.
- **procedure_states:** video; ≥ 2 still segments whose keyframe embedding cosine distance ≥ 0.08 (1 − cos).

Also `available_structures(record, specialists) -> dict[structure, (bool, reason)]`:

| Structure | Available when |
|---|---|
| final_state | image, or video (uses the last still segment) |
| procedure | video with ≥ 2 segments |
| temporal_pattern | rhythm available |
| utterance | audio (or video audio track) whose `audio_kind` is "speech", or flatness/modulation heuristics indicate speech: flatness < 0.35 and modulation ratio > 0.2 |

## 3. Composer (`track_a/composer.py`)

### 3.1 Draft
```python
@dataclass
class Draft:
    draft_id: str; dir: Path; source_path: Path
    perception: PerceptionRecord; probe: ProbeFacts; intake: IntakeResult
    proposal: CaseProfile | None        # None when refused
    refused: bool; refusal_message: str | None
    warnings: list[str]
    def to_view(self) -> dict  # {"draft_id","probe","intake","proposal","refused","refusal_message","warnings",
                               #  "structure_labels": STRUCTURE_LABEL, "specialist_labels": SPECIALIST_LABEL,
                               #  "perception": {"segments": [...], "observations": [...]} (no embeddings)}
```

### 3.2 `create_draft(data_dir, file_path, mime, ctx, *, title_hint=None, description=None, rights_confirmed: bool) -> Draft`
1. Check `rights_confirmed`; enforce limits (≤ 30 MB; video 8–120 s; audio 3–60 s; images ≥ 64 px on the short side). Failures raise INVALID_INPUT with friendly messages.
2. `draft_id = sha256[:16]`; dir `<data_dir>/drafts/<draft_id>/`. Copy the source to `source<ext>`. **Idempotent:** if `draft.json` exists, load and return it.
3. `record = perceive(source, mime, ctx, source_id=f"upload.{sha[:12]}", asset_dir=<draft dir>/assets, purpose="source", skill_hint=title_hint or description)`, then `save_record(record, <dir>/perception_source.json)`.
4. `intake = intake_from_perception(record)`.
   - Safety "refuse" → `refused=True`, message "We can't use this file: " + reasons.
   - Teachable "no" → `refused=True`, message `REFUSE_TEACHABILITY_MESSAGE.format(reason=…)`.
   - Teachable "unclear" without `title_hint` **and** `description` → not refused, but `proposal=None` and the warning "Tell us what skill this is (title and what a learner should achieve) to continue". The UI then calls `refine_draft` (below).
5. Otherwise build `probe = ProbeFacts(... structures_available=[available], specialists_available=[available], reasons=…)` and call **K7's** `track_a.universal.propose_skill_model(record, probe, intake, ctx, title_hint, description) -> (SkillModel, dict proposal_meta, list[str] warnings)`.
   - **Until K7 merges, that module may not exist.** In that case use `_fallback_skill_model(record, probe, intake, title_hint)`, which you implement minimally and deterministically: structures = [first available structure in the order final_state > procedure > temporal_pattern > utterance]; one `final_property` check per inferred property (max 4); `relevance.expected_kinds` from `STRUCTURE_ATTEMPT_KINDS`. Mark `proposal_meta={"fallback": True}` and add a warning.
6. `proposal = CaseProfile(case_id=composed_case_id(title, sha), title=<model skill title or hint or "Untitled skill">, skill_summary, domain, transmission_mode=<"goal-conditioned" if structures == ["final_state"] else "forward">, learner_input_kinds=<intersection of STRUCTURE_ATTEMPT_KINDS over structures, filtered by the specialists rule>, probe, intake, skill_model, perception_file="perception_source.json", confirmed_by_user=False, …)`.
7. Write `draft.json` (the `to_view()` dict plus internal fields needed to reload) and return.

`refine_draft(data_dir, draft_id, ctx, *, title, description) -> Draft`: re-runs step 5 only; perception is reused (no new perception calls).

### 3.3 `create_case_from_draft(cases_root, data_dir, draft_id, edits: dict) -> Path`
`edits` = `{title, skill_summary, domain, transmission_mode, learner_input_kinds, goal_hint, skill_model}`, where `skill_model` is the full edited SkillModel dict from the UI: it may toggle `keep` on properties/constraints, `enabled`/`weight`/`required` on checks, `critical` on steps, and rename steps or properties.
- Validate by constructing `CaseProfile(..., confirmed_by_user=True, confirmed_at=<UTC ISO>)`. A ValidationError raises INVALID_INPUT with the message.
- `case_id = composed_case_id(title, sha)`; `case_dir = <data_dir>/cases/<case_id>`. If it already exists and is confirmed, return it.
- Write:
  - `manifest.json`: copy the approach in `track_a.api.create_upload_case` so it is schema-valid. Use `archetype="universal:" + "+".join(structures)`; `workspace_type` = "spatial_canvas" if final_state is the only structure, "rhythm_envelope" if temporal_pattern, otherwise "spatial_sequence"; plus `transmission_mode`, `source_mode`, the same enum values as `create_upload_case`, and `source_media` local_file.
  - `source/upload.<sha12><ext>` and `source/source.json` (one SourceRecord, `runtime_label="UPLOAD"`, licence and creator from config, access `approved_learners`, role target_image / expert_video / expert_audio by modality).
  - `knowledge/perception_source.v1.json` plus its `.npy` and keyframe assets copied to `knowledge/goal_assets/` (update `embeddings_file` and `keyframe_asset` names accordingly).
  - `knowledge/case_profile.v1.json`.
- The caller (the service) then calls `track_a.api.build_case(case_dir, ctx)`. K7 makes `build_case` work for `universal`: it maps the confirmed SkillModel to contracts without new perception calls.

## 4. Service routes (`routes/compose.py`, prefix `/api/compose`)

| Method | Path | Body | Behaviour |
|---|---|---|---|
| POST | `/analyze` | multipart `file`, form `title`, `description`, `rights_confirmed` | `create_draft` → `Draft.to_view()` (refused drafts return **200** with `refused: true` and the message; they are not errors) |
| GET | `/{draft_id}` | — | `load_draft` |
| POST | `/{draft_id}/refine` | JSON `{title, description}` | `refine_draft` |
| POST | `/{draft_id}/create` | JSON edits | `create_case_from_draft` → `build_case` → `load_case(...).to_view()` |

- Use the existing `store_upload`, `adapters.translated()` and `adapters.run_context(settings, <draft dir>, mode)`.
- Validate `draft_id` with `^[0-9a-f]{16}$`.
- Add the table to `docs/plans/service-api.md`.

## 5. Track A wiring (small edits)
- `config.modality_for(case_id, case_dir=None)`:
  1. hero cases;
  2. hero-derived cases (`kolam~…` etc.);
  3. a composed case with `knowledge/case_profile.v*.json` → `"universal"`;
  4. else None.

  Add the optional `case_dir` parameter and pass it from `api.py` where available. All existing tests must still pass.
- `api.list_cases`: include composed cases from `<data_dir>/cases/*~*` that have a profile: `{case_id, title, modality: "universal", hero: False, runtime_label: "UPLOAD", composed: True, structures, review_status, built}`.
- `CaseHandoff.to_view()` adds `"profile": <profile dict or None>`.

## 6. Tests (fake gateway; no network)
- **`test_perceivers.py`:**
  - image: a synthetic line drawing gives the expected measurement observations; a fake embed gives 5 rows; a fake vision DTO gives inferred observations with region segments clamped.
  - video: a generated mp4 with 3 visually distinct still phases separated by motion gives ≥ 3 segments, with keyframes written and frame rows stored (generate with PyAV as in `tests/test_foundation.py::test_sample_frames_deterministic`, using solid colours plus a moving square).
  - audio: a click-track WAV gives onset and pulse observations; a speech-like synthetic signal (a noise burst amplitude-modulated at 4 Hz) passes the utterance heuristic; silence makes the intake teachable "no".
  - specialist / structure availability thresholds;
  - model failure → intake "unclear" plus a warning (never fabricated);
  - determinism: same file plus recorded runs → identical record JSON;
  - **at most 4 images per vision_fast call**, asserted on the fake client.
- **`test_composer.py`:** create_draft for an image (proposal present), refused cases (fake safety "weapons"; blank image), the unclear-without-hint path, refine_draft (no new perception calls), the fallback skill model when `track_a.universal` is missing, create_case_from_draft (manifest validates against the case-pack schema checker; files written; idempotent; invalid edits raise INVALID_INPUT), and `modality_for` for composed cases.
- **`test_service_compose.py`:** endpoints with monkeypatched composer functions; refused draft returns 200 with `refused: true`; unknown draft returns 404; invalid id returns 400.

## 7. Live check (with key; record in the report)
Run `create_draft` on:
1. `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\var\kiro\media\kolam\kolam_8_mayoo.png`
2. the shortest file in `...\var\kiro\media\tabla\`
3. a 30 s cut of `tracks/cases/origami/media/cache/*.ogv` (cut with PyAV into your `var/`)
4. a landscape-like image: generate one with Pillow (sky gradient plus a green band), **or** a random-noise image. Expect a refusal or "unclear".
5. a 5 s silent WAV (expect a refusal).

For each, record: segments, observation counts by kind, intake result, specialists and structures available, number of model calls, total latency and estimated cost (tokens × price; use the usage metadata if you store it, otherwise estimate).

## 8. Acceptance
- All tests pass; the live-check table is in `docs/kiro/reports/K6-REPORT.md`.
- The Definition of Done in 00-COMMON.md is met.
- No change to hero-case behaviour (the existing tests stay green).
