# K9-P4 — Sample attempts and sample sources (technical-panel WI-3.1, closes J-11)

Read `00-COMMON.md` (environment and non-negotiables), `K9-00-PRODUCT-UX.md`, then this file. Your folder, branch, status file and inbox protocol are in `K9-ORCHESTRATOR.md` §2 and §4.

**Goal.** A judge or first-time visitor can try every featured skill in 60 seconds **without their own materials**:
- **"Try a sample attempt"** submits a ready-made good, flawed or unrelated attempt as their try and shows real feedback;
- **"Try with an example"** in the composer starts a draft from a committed example source.

The UI for both is built by P2 (practice views) and P3 (composer) against the client methods Phase 0 added:
- `listSamples`;
- `submitSampleAttempt`;
- `listSampleSources`;
- `analyzeSampleSource`.

Their types are `SampleAttempt` and `SampleSource` in `app/src/api/types-product.ts`. **Match those field names exactly.**

---

## 0. Ground rules

- Python only (plus small committed media). No new dependencies. Use `numpy`, `pillow` and `av` (PyAV), which are installed.
- Every committed file must be ≤ 2 MB (repo rule). Total new media ≤ 6 MB.
- Licensing:
  - synthetic files you generate are `CC0-1.0`, made for the demo, with `synthetic: true`;
  - anything derived from case media keeps that media's licence and attribution (`tracks/cases/<case>/source/source.json`);
  - follow `.claude/skills/case-media/SKILL.md`.
- No live model calls are needed for Kolam (trace evaluation is deterministic) or Tabla (deterministic unless `audio` is enabled, which is off by default). P4 has **0 live calls**. Origami samples belong to P5.
- Never change the frozen contracts. Never edit files owned by other tasks.

## 1. Files you own

**New:**
- `service/anveshan_service/samples.py`
- `service/anveshan_service/routes/samples.py`
- `service/tests/test_k9_samples.py`
- `tools/make_samples.py`
- `tracks/cases/kolam/samples/**`
- `tracks/cases/tabla/samples/**`
- `tracks/samples/sources/**` (example sources for the composer)

**Not yours:**
- `service/anveshan_service/main.py`: P1 owns it. PC adds one line to register your router; you test by including the router yourself (§5).
- `limits.py`: P1 adds your rate-limit regexes (`/attempts/sample/` is already covered; P1 adds `/api/compose/sample/`).

## 2. Sample pack format (P5 uses the same format for origami-universal)

`tracks/cases/<case_id>/samples/samples.json`:

```json
{
  "schema_version": 1,
  "samples": [
    {
      "sample_id": "good",
      "label": "A careful attempt",
      "quality": "good",
      "attempt_kind": "trace",
      "file": "good.trace.json",
      "raster": null,
      "description": "Follows the line around every dot without lifting. Expect most checks to be met.",
      "preview": null,
      "synthetic": true,
      "credit": null,
      "licence": "CC0-1.0",
      "expected": {"passed": true}
    }
  ]
}
```

| Field | Rule |
|---|---|
| `sample_id` | `^[a-z0-9-]{1,40}$` |
| `quality` | One of good, flawed, unrelated |
| `attempt_kind` | One of trace, image, audio, video |
| `file` | Relative to the samples dir. Must exist and be ≤ 2 MB. |
| `raster` | Optional PNG for trace attempts, if the Kolam evaluator wants the raster too. Read `make_attempt_media` and the Kolam evaluator: if a raster is required, generate one from the strokes with Pillow. |
| `preview` | Optional relative path to an image, audio or video the UI can show. Exposed as `preview_url` = `/api/cases/{case_id}/samples/{sample_id}/preview`. |
| `expected` | Documents what the sample should produce. Tests assert it: `{"passed": bool}` and/or `{"refused": true}` for unrelated samples, plus an optional `{"first_off_track": "<criterion_id>"}`. |

## 3. Content to generate (`tools/make_samples.py`, deterministic, re-runnable)

The script writes all sample files and the two `samples.json` files. It uses a fixed seed (`numpy.random.default_rng(7)`) so reruns are byte-identical, and prints the sizes.

**Kolam** (`tracks/cases/kolam/samples/`). Attempt kind `trace`, in the trace JSON format of `docs/plans/service-api.md` §4. Coordinates are goal-image pixels.
1. **Read the goal.** The goal curve and dots come from the latest `tracks/cases/kolam/knowledge/goal_model.v*.json`: `ui_view` has `curve.points` (arc-ordered) and `dots`. Open only the keys you need: `grep -n` first, then load with `json`.
2. **good:**
   - one stroke along the goal curve;
   - resample to about 1 point per 3 px;
   - add Gaussian jitter σ = 1.5 px;
   - timestamps at a constant 250 px/s;
   - `duration_ms` is the last timestamp.
3. **flawed:**
   - the same, but break the stroke into two strokes at about 45% of the arc length (pen lifted);
   - skip the arc between 45% and 55%;
   - this should fail continuity and coverage around that region.

   Set `expected` after running the evaluator once (see step 5).
4. **unrelated:** a zig-zag scribble in one corner (about 15% of the image), 1 stroke, 3 s.
5. **Calibrate.** Run each sample through Track B in **recorded** mode using the real case (pattern: `tracks/track-b/tests/test_kolam_session_e2e.py`). Record whether it passed and the first-divergence criterion, and write them into `expected`.
   - If **good** does not pass, reduce the jitter until it does.
   - If **flawed** passes, widen the skipped region.
   - If **unrelated** is not refused or failed, move it further from the dots.
6. **Labels and descriptions** (exact):
   - good: "A careful attempt" / "Follows the line around every dot without lifting. Expect most checks to be met."
   - flawed: "An attempt with a mistake" / "The pen lifts and skips part of the line. See where the feedback says it first went off track."
   - unrelated: "Something unrelated" / "A scribble that is not this kolam. Anveshan should say it does not match instead of scoring it."

**Tabla** (`tracks/cases/tabla/samples/`). Attempt kind `audio`, WAV 16 kHz mono 16-bit, ≤ 12 s.
1. **Read the goal.** The expected onsets and tempo come from the latest `tracks/cases/tabla/knowledge/goal_model.v*.json` (`ui_view` has the beats and tempo; check the actual keys with `grep -n`).
2. **good:** synthesize strokes at the goal onsets. Each onset is a short damped sinusoid: dayan about 400–600 Hz with a 60 ms decay; bayan (where the goal marks it) about 90 Hz with a 120 ms decay. Add a little noise (−40 dB). Use the tempo exactly.
3. **flawed:** the same, but from the midpoint the tempo drifts +12% and one stroke in the second half is missing.
4. **unrelated:** 8 s of a steady 220 Hz hum with soft noise (no onsets pattern).
5. **Reuse:** if `tracks/track-b/tests/test_tabla_eval.py` has synthesis helpers (`synth_handclap`), reuse their approach.
6. **Calibrate** in recorded mode, as for Kolam (pattern: `test_tabla_session_e2e.py`).
7. **Labels:**
   - good: "A steady attempt" / "Plays the pattern at the source's tempo. Expect most checks to be met."
   - flawed: "An attempt that rushes" / "Speeds up halfway and drops a stroke. See where the feedback says it first went off track."
   - unrelated: "Something unrelated" / "A hum, not tabla. Anveshan should say it does not match instead of scoring it."

**Example sources for the composer** (`tracks/samples/sources/`). Write a `sources.json` with entries:

```json
{"sample_id": "...", "label": "...", "description": "...", "file": "...", "mime_type": "...", "credit": "...", "licence": "..."}
```

| sample_id | label | file | credit and licence |
|---|---|---|---|
| `kolam-photo` | "A kolam drawing (photo)" | A **new** PNG rendered from the kolam goal curve: a white background, 6 px dark line, the dots drawn, 512 px | "Rendered for the demo from the Anveshan kolam goal" / `CC0-1.0`. Do not copy the case's source image, so no licence issues. |
| `tabla-rhythm` | "A short tabla rhythm (audio)" | The Tabla **good** sample | `CC0-1.0`, synthetic |
| `crane-fold` | "Folding a paper crane (video)" | Only if P5 is not doing it: skip. P5 owns Origami media; do not add video here. | — |

## 4. Service

### 4.1 `samples.py`

```python
class Sample(BaseModel)         # mirrors one samples.json entry (extra="forbid")
def load_pack(case_dir: Path) -> List[Sample]          # [] when no samples dir; validates sizes and ids
def public_view(case_id: str, s: Sample) -> dict       # SampleAttempt shape: sample_id, label, quality, attempt_kind,
                                                        # description, preview_url, synthetic, credit
def sample_paths(case_dir: Path, s: Sample) -> Tuple[Path, Optional[Path]]   # (file, raster)
def load_sources(repo_root: Path) -> List[dict]       # tracks/samples/sources/sources.json -> SampleSource shape (preview_url = /api/compose/samples/{id}/file)
```

### 4.2 `routes/samples.py` (one `APIRouter`, no prefix)

| Route | Behaviour |
|---|---|
| `GET /api/cases/{case_id}/samples` | `case_dir(settings, case_id)` (404 rules), then `load_pack` for that dir. For a hero-derived case (`kolam~…`) use the base case's pack (`base_case_id`). Returns a list of `public_view`. |
| `GET /api/cases/{case_id}/samples/{sample_id}/preview` | `FileResponse` of `preview`. 404 when absent. Validate `sample_id` with the regex. |
| `POST /api/sessions/{session_id}/attempts/sample/{sample_id}` | **The heart of this task.** Exactly what `routes/sessions.submit_attempt` does, but the uploaded files are the committed sample files (below). |
| `GET /api/compose/samples` | `load_sources` |
| `GET /api/compose/samples/{sample_id}/file` | The source file |
| `POST /api/compose/sample/{sample_id}` | Same as `routes/compose.analyze_upload`, with the committed file and `rights_confirmed=True`. The sample is CC0 or licensed with its credit; the title hint is the sample label. Call `add_owner` on the draft dir like analyze does. |

**Sample attempt route, in detail:**
1. Inside `adapters.session_lock(session_id)`, load the session.
2. Find the case dir via `adapters.session_case_dir` and load its pack. Unknown `sample_id` → 404.
3. Copy the sample file into the uploads store, reusing `paths.store_upload` semantics: write `<data_dir>/uploads/<sha256><ext>` yourself with `hashlib` and build a `StoredUpload`. Do **not** fake an `UploadFile`.
4. Build the media with `adapters.make_attempt_media(kind, primary, extras, session=…, api=…)`, call `api.submit_attempt`, then `api.save_session`.
5. Return `adapters.to_json(result)`.
6. P1 adds insights recording to the normal attempt route. For samples, call `insights.record_attempt(..., source="sample")` only if `anveshan_service.insights` exists (`importlib.util.find_spec`), so you don't depend on P1's branch. PC verifies it after the merge.

**Labelling samples honestly.** The insights field `source: "sample"` lets stewards tell sample tries from real learners. P1's `compute()` currently counts every event; PC adds a filter so samples are excluded from learner counts (see PC §3).

## 5. Tests (`service/tests/test_k9_samples.py`; no live calls)

Build the app with your router included explicitly:

```python
app = create_app(settings)
from anveshan_service.routes import samples as samples_routes
app.include_router(samples_routes.router)
client = TestClient(app)
```

1. `load_pack` on the committed Kolam and Tabla packs:
   - 3 samples each;
   - qualities good, flawed and unrelated;
   - every file exists and is ≤ 2 MB;
   - ids match the regex;
   - descriptions are non-empty.
2. `GET /api/cases/kolam/samples` with a temp `cases_root` copy containing only `manifest.json` and `samples/` returns 3 items with exactly the `SampleAttempt` keys.
3. Sample attempt through the fake Track B (`conftest.py` fakes): start a session, POST the sample → 200; the fake recorded a media path whose sha matches the committed file.
4. An unknown sample gives 404; a bad `sample_id` (`../x`) gives 400 or 404 and never reads outside the samples dir.
5. **Real evaluation, recorded mode** (marked `@pytest.mark.slow` only if > 10 s; otherwise a normal test). Using the real `track_b.api` and the real `tracks/cases/kolam` and `tracks/cases/tabla`, each sample's `expected` holds: good passes, flawed does not, and unrelated is not passed (refused or failed). This is the regression guard for the samples.
6. `GET /api/compose/samples` lists the example sources, and the files exist.

## 6. Acceptance

- `tools/make_samples.py` regenerates byte-identical files.
- The new tests pass.
- The full non-live suite passes.
- `check_case_packs.py` passes. If it rejects the new `samples/` dirs, extend the checker minimally to allow them and validate `samples.json`. That checker file is then yours too: `.github/scripts/check_case_packs.py`. Log it.
- Report `docs/kiro/reports/K9-P4-REPORT.md` with:
  - the sample table (case, id, size, expected result, actual result);
  - "Requests for PC" (the router registration line; the samples filter in insights).
