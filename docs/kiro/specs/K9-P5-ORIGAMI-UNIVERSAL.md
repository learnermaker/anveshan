# K9-P5 — Origami as a featured skill built by the universal pipeline (technical-panel WI-2.1, decision D1, closes J-04)

Read `00-COMMON.md`, `K9-00-PRODUCT-UX.md`, then this file. Your folder, branch, status file and inbox protocol are in `K9-ORCHESTRATOR.md` §2 and §4. Also read:
- `docs/plans/universal-pipeline.md` §2, §4, §8 and §12;
- `.claude/skills/case-media/SKILL.md`;
- `.claude/skills/model-gateway/SKILL.md`.

**Goal.** Today the Origami hero case uses a dedicated engine that the panel found brittle (J-04). Decision D1:
- the **featured** Origami skill is a curated pack **composed by the universal pipeline** from the licensed crane video, with committed recorded runs, so it works in recorded and live mode;
- the dedicated engine stays in the repo but is **hidden from the library** and labelled experimental.

This is the strongest proof that "any demonstration becomes a practice task" works on a real video.

---

## 0. Ground rules and budget

- **Live model calls: ≤ 40 in total.** Copy `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan\.env` into your folder root (it is gitignored). Never print it, and never commit it. Count the calls: the gateway records each run under `var/` runs dirs, so count the run directories you create.
- Models: `vision_fast` (gemini-3.5-flash-lite) and `embedding` (gemini-embedding-2) only. Never Gemma for this.
- Media rules:
  - **≤ 2 MB per committed file**;
  - large source media stays fetched by sha256 (case-media skill);
  - attribution "OrigamiCrane.ogv by Tavin, CC BY 3.0, via Wikimedia Commons" (see `tracks/cases/origami/source/source.json`).
- Do not change the frozen contracts. Do not touch `app/`, `service/` or other tasks' files.

## 1. Files you own

- New: `tracks/cases/origami-crane/**` (the curated universal pack, including `samples/`).
- `tracks/cases/index.json`: add `origami-crane`.
- `tracks/track-a/src/track_a/config.py`.
- `tracks/track-a/src/track_a/api.py`, **only** the functions `list_cases`, `CaseHandoff.to_view` (the `hero` field) and `_summary` (the `hero` field). P1 owns `_summary_composed`; do not touch it.
- `tools/build_curated_composed.py` (new).
- `tools/fetch_media.py`: only if the new pack needs a mapping entry.
- **Not yours:** `.github/scripts/check_case_packs.py` belongs to K9-P4. If it rejects the new pack, describe the needed change under "Requests for PC". PC applies it after merging both.
- Tests: `tracks/track-a/tests/test_origami_crane_pack.py` (new), plus minimal updates to existing tests that assert the library list.

## 2. Build the pack

### 2.1 Tool: `tools/build_curated_composed.py`

```text
usage: build_curated_composed.py --source <media path> --case-id origami-crane --title "..." --description "..."
                                 [--data-dir var/k9-compose] [--live]
```

Steps, mirroring `service/anveshan_service/routes/compose.py` exactly, but in-process:
1. `ctx = RunContext.create(<data_dir>, <data_dir>, "live")` (see `adapters.run_context`).
2. `composer.create_draft(data_dir, source, mime, ctx, title_hint=..., description=..., rights_confirmed=True)`.
3. Print the draft's proposal summary: steps, properties and checks. **Stop here if `refused` or the proposal is `None`.**
4. `composer.create_case_from_draft(cases_root, data_dir, draft_id, edits)`. The edits are the proposal as-is, except:
   - **title:** "Fold a paper crane: the first folds" (use the actual folds the proposal covers; keep it honest and short);
   - **skill_summary:** one plain sentence.
5. `track_a.api.build_case(case_dir, ctx)`.
6. Copy `case_dir` to `tracks/cases/<case-id>/`:
   - rewrite `manifest.json` `case_id` and every JSON file that contains the old id string (`<slug>~<hash>`) to the new id;
   - delete `.owners.json` and `.library.json`;
   - the source media file inside the case dir must not be committed if it is > 2 MB. Replace it with a source-registry entry pointing at the existing fetched cache file `src.origami.demo.v1.ogv` (same sha256 as `tracks/cases/origami/source/source.json`), and update `tools/fetch_media.py` so `--from-dir` also fills `tracks/cases/origami-crane/media/cache/`. Follow how the `origami` pack does it.
7. **Rebuild in place.** Run `build_case(tracks/cases/<case-id>, ctx_live)` again. The live cache in the gateway makes identical calls free; the purpose is that run keys are computed against the final case directory.
8. **Promote** every run the final build used into `tracks/cases/<case-id>/runs/golden/`:
   - pattern: `tools/promote_eval_golden_runs.py`, with sources in `<data_dir>/runs/<case-id>/`;
   - check the run key list in the build's result or run metadata.

### 2.2 Source and edits

- **Source:** `tracks/cases/origami/media/cache/src.origami.demo.v1.ogv` (run `fetch_media.py --from-dir …` first if it is missing).
- **Title hint:** "Paper crane".
- **Description:** "Fold a square of paper into a crane, following the demonstration step by step."

**Clean the AI-extracted steps through the real review flow** (this is also demo evidence):
- for each duplicate or contradictory property statement, use `track_a.api.apply_review(case_dir, {"action": "reject_claim", ...})` with reviewer "anveshan-team". This includes the known duplicate "taller than wide" / "taller-than-wide" (WI-2.1);
- leave the package **pending** expert review. Do **not** approve it: no expert has checked it, and the UI must honestly say "Not yet checked by an expert".

### 2.3 Samples (format: `K9-P4-SAMPLES.md` §2)

`tracks/cases/origami-crane/samples/` holds three video samples, each re-encoded with PyAV to 320 px wide, 10 fps, H.264 (`libx264` if available in PyAV's bundled ffmpeg, else `mpeg4`), at most 25 s, ≤ 2 MB:

| sample_id | Label | Content | Licence |
|---|---|---|---|
| `good` | "A careful attempt" | The held-out learner video `tracks/cases/origami/media/cache/src.origami.learner_crane.v1.ogv` (Crane.ogv, CC BY 3.0, Tavin). Credit line required. | CC BY 3.0 |
| `flawed` | "An attempt with steps out of order" | Re-encode `var/eval/origami/swapped_order.mp4` if it exists; it was derived from the demo video. Otherwise build it: cut the demo into 4 equal segments and concatenate them in the order 1, 3, 2, 4. | CC BY 3.0 (derived), credit line required |
| `unrelated` | "Something unrelated" | 8 s, 320×240, 10 fps of slowly moving coloured rectangles drawn with numpy | CC0, synthetic |

Descriptions follow the Kolam style in K9-P4 §3 ("Expect most checks to be met." / "See where the feedback says it first went off track." / "Anveshan should say it does not match instead of scoring it.").

**Record the sample evaluations:**
1. Run each sample once through Track B in **live** mode against the final pack (pattern: `tracks/track-b/tests/test_universal_session_e2e.py`, with a real `RunContext` in live mode). That costs about 3–9 calls per sample.
2. Promote the used runs to `runs/golden/`.
3. Calibrate `expected` from the results.

**Honesty rule:** if the good sample does not pass, do **not** tune thresholds to force it. Record the real result in `expected` and the report, and set the label to "A real learner's attempt" instead of "A careful attempt".

## 3. Library changes (`config.py`, `api.py`)

1. **`config.py`:**
   - add `FEATURED_COMPOSED: Tuple[str, ...] = ("origami-crane",)`;
   - add `EXPERIMENTAL_CASES: Tuple[str, ...] = ("origami",)`.
2. **`list_cases`:**
   - emit hero cases **except** those in `EXPERIMENTAL_CASES`;
   - then each `FEATURED_COMPOSED` pack under `cases_root` (when `manifest.json` exists) as `_summary_composed(...)`, with `hero=True` and `runtime_label` from its sources (INTERNET_REFERENCE);
   - then the existing derived and composed uploads;
   - then the showcase.
   - The experimental `origami` case is **not listed**, but `GET /api/cases/origami` still works (direct URL).
   - Read `_summary_composed`, but do not edit it: P1 owns it. Post-process its returned dict in `list_cases`: set `hero`, `runtime_label` and `composed`.
3. **`CaseHandoff.to_view()`:** `"hero": self.case_id in config.HERO_CASES or self.case_id in config.FEATURED_COMPOSED`.
4. **`origami/manifest.json` title:** "Origami crane (dedicated engine, experimental)".
5. **Order of featured cards:** kolam, origami-crane, tabla.
6. Check `config.modality_for("origami-crane", case_dir)` returns `"universal"`. It does when `case_dir` is passed, because the pack has `knowledge/case_profile.v*.json`. Check every `modality_for` call site in `track_a/api.py` that could pass no `case_dir` for this id, and pass it.

## 4. Tests (`tracks/track-a/tests/test_origami_crane_pack.py`; recorded mode, no live calls)

1. `load_case(tracks/cases/origami-crane)`:
   - modality universal;
   - `review_status` pending;
   - claims non-empty;
   - no duplicate statements (case-insensitive, hyphens normalized to spaces);
   - `to_view()["hero"]` is True.
2. `list_cases(...)`:
   - contains `origami-crane` with `hero=True` and `composed=True`;
   - does **not** contain `origami`;
   - contains `kolam` and `tabla`.
3. **Each sample, recorded mode** (real Track B, the real pack): the evaluation runs **without** `REPLAY_MISMATCH`, and the outcome matches `samples.json` `expected`. This proves the golden runs are complete.
4. A Track B learner session on the pack in recorded mode with the good sample completes end to end (start, baseline, retry with the same file, complete).
5. Update existing tests that assumed `origami` in the library list. Change only the expectation about listing; keep the tests for the dedicated engine itself.

## 5. Acceptance

- The pack builds with ≤ 40 live calls (report the exact number).
- Every committed file is ≤ 2 MB.
- `check_case_packs.py` passes, and the full non-live suite passes.
- Recorded mode works with no network (tests 3 and 4).
- Report `docs/kiro/reports/K9-P5-REPORT.md` with:
  - the step list the AI extracted, after cleaning;
  - each sample's result;
  - live calls used;
  - files and sizes;
  - "Requests for PC" (e.g. P2's Library ordering, if needed).
