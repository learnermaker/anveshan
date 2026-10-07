# Anveshan — Session Handoff (context for the next Claude Code / coding-agent session)

**Written:** 2026-10-06 (updated 2026-10-07) by the Claude Code session (Opus 5.5) that did planning, foundation, integration and orchestration.
**Read this first in any new session**, then `CLAUDE.md` → `AGENTS.md` → the docs it points to. The repo is the durable record; this file summarises everything that was only in chat.

## 1. Who and what
- **Jim** (git "Jim", GitHub `learnermaker`, Windows PC, GitHub Desktop; no `gh`, no gcloud, no Docker locally) owns integration and decisions. Coding is done by Claude Code (main developer) plus **Kiro** sessions (Sonnet 4.6, a weaker model, so **specs for Kiro must be exhaustive and step-by-step**).
- **Hackathon:** Google Cloud AI Builder Cup 2026, theme **Sustainability & Social Impact** (living heritage + skill transmission).
  - **Submission deadline 2026-10-18**; the time zone isn't published, so ask Hack2skill.
  - Team of **2–4 members registered by 2026-10-11**; working professionals aged 21+.
  - **Fresh-code rule:** only code written after 2026-09-07. The first repo commit is 2026-10-02, so we comply. Never import older code.
  - Portal: https://hack2skill.com/event/aibuildercup2026/registration.
  - Deliverables: deck, working prototype on Cloud Run, a public 3-minute video (YouTube/Vimeo/Drive). Rules snapshot: `docs/kiro/official-rules-2026-10-06.md`.
- **Jim's preferences:**
  - act autonomously and fast;
  - minimise cost (negligible paid calls are OK);
  - use parallel agents;
  - no human recordings needed (use licensed internet media and uploads);
  - don't create the submission pack yet;
  - commit and push work to GitHub.

## 2. Product in one paragraph
Anveshan helps transmit a bounded skill from a source to a learner with evidence:

**source → perception → structured knowledge (claims with locators, observed vs inferred) → rubric/checks → learner attempt → deterministic scoring → first divergence → grounded feedback → retry → transmission gain + lineage**

The **evaluation core** is *Goal-Trajectory Verification* (`docs/plans/evaluation-core.md`): progress toward the goal, first divergence, why it matters, and targeted change after retry. **Model output never sets scores.** Scores come from deterministic bands (`practice/observers.vN.json`, score_policy_v1). The 8 shared contracts in `tracks/common/schemas/` are **frozen**.

## 3. Architecture map (where things live)

| Layer / area | Location |
|---|---|
| Contracts (frozen) + validator | `tracks/common/schemas/`, `tracks/common/validator.py` |
| Shared foundation | `tracks/common/{media,onsets,locators,models,casedata,runtime}.py` |
| Universal pipeline schemas | `tracks/common/{perception,skill_model,profile,policy}.py` |
| Model gateway | `tracks/common/models.py`: `generate_json`, **`embed()`** (Gemini Embedding 2, float16 .npy recording), registry, `RunStore` record/replay |
| Specialists | Kolam geometry `tracks/common/kolam_geometry.py` + `goals/kolam.py`; Tabla DSP `tracks/common/tabla_dsp.py` + `goals/tabla.py`; Origami `track_a/goals/origami*.py` + `track_b/evaluators/origami*.py` |
| Track A (knowledge) | `tracks/track-a/src/track_a/` (`api.py` build/load/list/upload/query/review, `authoring.py`, `grounding.py`, `goals/*`) |
| Track B (evaluation) | `tracks/track-b/src/track_b/` (`api.py` sessions, `scoring`, `evaluate`, `divergence`, `feedback`, `compare`, `transmission`, `intake`, `evaluators/*`); never imports `track_a` |
| Service | `service/anveshan_service/` (FastAPI; serves `app/dist`); `Dockerfile`; `docs/deploy/cloud-run.md`; console guide `docs/kiro/cloud-run-console-guide.md` |
| App | `app/` (React/Vite/Tailwind; `src/api/{client,types,mock}`; hero views; mock mode `npm --prefix app run dev:mock`) |
| Case packs | `tracks/cases/<id>/` (manifest, `source/source.json`, versioned `knowledge/*.vN.json`, `practice/*.vN.json`, `runs/golden/`) |
| Tools | `tools/fetch_media.py` (licensed media by sha256), `tools/check_models.py` (model smoke test) |

**Interfaces:** `docs/plans/service-api.md`.
**Universal pipeline** (for any new upload): `docs/plans/universal-pipeline.md`. Intake gates (format / safety / teachability) → Layer 1 perception (generic + specialist perceivers + embeddings) → Layer 2 SkillModel (final_state / procedure / temporal_pattern / utterance + check catalogue) → Layer 3 evaluation (attempt gates including relevance, embedding alignment, checks, bands).

## 4. Hero cases (live) and data

| Case | Source (licensed) | Key facts |
|---|---|---|
| Kolam (final image only) | `Ithayakkamalam - 2.jpg`, public domain (Mayooranathan). The author's direction diagram is **held out** (validation only) | 41 dots, **K=1** continuous line, 32 crossings, 8-fold symmetry. Held-out route overlap 99.3/99.8%. Lines pass *through* dots (don't assume sikku). |
| Origami (video) | `OrigamiCrane.ogv` CC BY 3.0 (Tavin); window 0–194 s (crane → bird base) | `Crane.ogv` is the **same performance re-encoded**: a positive control only. No licence-clean independent learner video exists. |
| Tabla (audio) | Wikimedia "A man playing tabla in village pranpur near Chanderi.webm" CC BY-SA 4.0, window 20–32 s | pulse 0.1893 s (shown as 158.5 BPM), 12-pulse bass cycle, IOI CV 0.113 (STEADY bands widened). Jim's listening verdict: YES. |

Showcase cases (micrometer, bicycle-repair, handloom-weaving, square-knot) are **SYNTHETIC replay only**.

## 5. Models (measured 2026-10-06 with Jim's AI Studio key; key lives in local `.env`, never committed)

| Registry key | Model | Measured |
|---|---|---|
| `vision_fast` | gemini-3.5-flash-lite | 1 image 2.5 s; 4 images 8.9 s; ≈ $0.0003 per image |
| `audio` | gemini-3.5-flash-lite | 12 s clip in 2.7 s, 445 tokens ≈ $0.0003; heard tabla, 5.2 strokes/s (our DSP: 5.28) |
| `embedding` | gemini-embedding-2 | 5 images in 1.3 s; cosine: rotated copy 0.98, half-erased 0.85, other kolam 0.82, noise 0.63 (good for relevance and coarse matching, not fine correctness) |
| `text_image` / `video_frames` | gemma-4-26b-a4b-it (free) | **43 s per image; a 4-image call timed out (504)**; no audio. Offline only. |

The models are cross-checks, not authority (e.g. flash-lite said 7-fold symmetry; the geometry says 8).

## 6. Branches, folders and status (updated 2026-10-07)
- **`main` is current (2026-10-07):** `m1/hero-cases` was fast-forwarded into `main` at Jim's explicit instruction (no PR). Branch from `main` for new work. **Remaining work, in order: `docs/plans/NEXT-STEPS.md`.**
- **Everything from Kiro is merged:** K1–K4 and WP1–WP5 (see `docs/plans/DECISION-LOG.md` and `docs/kiro/reports/*`). The `anveshan-wt/*` folders are git worktrees of this repo; remove them with `git worktree remove` once they are no longer needed.
- **2026-10-07 (Claude Code), universal-pipeline robustness for ANY upload** (Jim's priority over tuning single hero videos):
  - video segmentation, alignment, relevance and judges redesigned;
  - image completeness check added;
  - audio skills that aren't tabla now compose;
  - 429 backoff in the gateway.

  Design, evidence and limits: `docs/plans/universal-pipeline.md` §12 and `docs/validation/experiments.md` E6. Stress tools: `tools/stress_universal_video.py --scenario synth|origami|origami_window`, `tools/stress_universal_other.py --scenario image|audio` (`--mode recorded` replays from `var/stress/*/data/runs`; `--mode live` costs a few cents).
- **Tests:** 434+ non-live passing; governance, case-pack and parity checks pass; the app builds.
- **Known limits:**
  - fine-grained states in low-resolution, hand-dominated video (the Origami bird-base clip);
  - the swapped-order synthetic verdict varies between live runs (vision-model variance);
  - speech skills are untested.
- **Dedicated Origami engine:** its own RESULTS show it fails its "perfect" attempt (5 of 7 states; see `tracks/track-b/eval/origami/RESULTS.md`). The full `OrigamiCrane.ogv` through the universal path does better (positive control passes 11/11). This is Jim's decision: either present Origami through the universal path, or keep the dedicated engine and label it honestly.
- **UI wiring of universal views** (source media, step thumbnails, line_art canvas, MEASURED vs AI-JUDGED badges) is merged.

## 7. How to resume in a new session
1. `git checkout main && git pull`. Read `docs/plans/DECISION-LOG.md` and `docs/kiro/reports/*-REPORT.md` to see what Kiro finished.
2. Run the verification: the `anveshan-verify` skill, or
   ```bash
   .venv/Scripts/python -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"
   ```
   then the 3 `.github/scripts/check_*.py` scripts, then `npm --prefix app run build`.
3. If Kiro branches exist unmerged: merge in the order K1 → K4 → WP4 → WP1 → WP2 → WP3, resolving by master spec §3 ownership, verifying after each.
4. Then finish master spec §5 (WP5) and whatever the DECISION-LOG marks TODO / PENDING-KEY.
5. After that: deploy (Jim, console; `docs/deploy/DEPLOY-CHECKLIST.md`), then the submission pack (deck, 3-minute video) **only when Jim asks**.

## 8. Gotchas learned the hard way
- **Windows network:** `curl` needs `--ssl-no-revoke`. Wikimedia rate-limits (HTTP 429); use a descriptive User-Agent and ≥ 15–60 s gaps. Jim's IP got blocked for some files.
- **Gemma rejects video files that have an audio track.** Always send sampled frames (PyAV), never video files.
- **Agents/Kiro sometimes commit files they don't own** (K3 committed Kolam/Tabla artifacts; K1 wrote review notes into the main folder). Always check `git diff --name-status` before merging, and resolve by ownership.
- **Test fixtures:** `tracks/track-a/tests/conftest.py` copies real cases **without** `*.v*.json` artifacts, so tests start unbuilt.
- **Kolam rubric** bands degenerate for K=1 (handled: CURVES has no partial band; CONTINUITY uses excess pen lifts).
- **Onsets:** `onsets.py` has an absolute flux floor (rejects pure tones and near-silence). Timestamps are at the frame centre.
- **`requirements.txt` at the root was a UTF-16 pip freeze;** it has been deleted. Use `requirements-dev.txt`, `service/requirements.txt` and the per-track requirements.
- **Graphify** hooks (`.claude/settings.json`) refresh the local code graph; they're a no-op if graphify isn't installed. `graphify-out/` is gitignored.
- **Cloud Run** caps request bodies at 32 MiB, so uploads are limited to 30 MB. Sessions live on instance disk; use `max-instances 1`.
- **Honesty rules:** never call internet media an "authentic expert"; synthetic attempts are labelled SYNTHETIC; validation docs must say "engineering/capability evidence", not learner validation.

## 9. Key documents index
- Plan and decisions: `docs/plans/track-plan-review-2026-10-06.md` (§9 decisions), `docs/status/{NOW.md,project.yaml,DECISIONS.md}`
- Design: `docs/plans/evaluation-core.md`, `docs/plans/universal-pipeline.md`, `docs/plans/case-composer.md` (partly superseded), `docs/plans/service-api.md`
- Execution: `docs/plans/wave2-master-spec.md`, `docs/kiro/specs/*` (00-COMMON, K1–K8, K2b, KIRO-WAVE2, KIRO-ORCHESTRATOR), `docs/plans/cloud-runbook.md`
- Evidence: `tracks/track-b/eval/*/RESULTS.md`, `tracks/track-a/eval/KOLAM_PATH_VALIDATION.md`, `docs/kiro/reports/*`
- Research: `docs/kiro/media-candidates.md`, `docs/kiro/official-rules-2026-10-06.md`, `docs/kiro/cloud-run-console-guide.md`
