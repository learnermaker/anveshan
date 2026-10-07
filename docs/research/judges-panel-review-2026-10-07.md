# Judges-panel review — 2026-10-07

> **REVIEW ARTIFACT (evidence, not scope).** A simulated judging panel reviewed the running app and the codebase against the official AI Builder Cup criteria. It covers the product, not the submission pack (demo video, deck), which is out of scope here. Findings do not authorise work by themselves; the update plan is `docs/plans/technical-panel-plan-2026-10-07.md` (PROPOSED).

## Status summary (2026-10-08, K9 merged into `k9/integration`, pending merge to `main`)

| ID | Sev | Status | Notes |
|---|---|---|---|
| J-01 | P0 | DONE | README rewritten (K9-P6) |
| J-02 | P0 | DONE | Rate limits, daily budget, visitor isolation added |
| J-03 | P0 | DONE | Friendly error messages in `app/src/api/errors.ts` |
| J-04 | P0 | DONE (K9) | Origami rebuilt via universal pipeline (K9-P5) |
| J-05 | P0 | DONE | Case ownership and visitor isolation added |
| J-06 | P0 | DONE | Docker image build added to CI (`checks.yml`) |
| J-07 | P0 | DONE | Housekeeping, TTL and capacity limits added |
| J-08 | P1 | OPEN | Needs a real pilot and expert review; humans required |
| J-09 | P1 | DONE | AI coaching wording added (E8, `tracks/track-b/src/track_b/coach.py`) |
| J-10 | P1 | DONE | Show-me animation and drill cards added |
| J-11 | P1 | DONE (K9) | Sample attempts added (K9-P4) |
| J-12 | P1 | PARTIAL | Live cache added (E7); WS6 robustness deferred to NEXT |
| J-13 | P1 | DONE (K9) | Showcase collapsed; plain language cleanup (K9-P2/P3) |
| J-14 | P1 | DONE (K9) | Developer chrome cleaned up (K9-P2/P3) |
| J-15 | P1 | DONE (K9) | Copy corrections (K9-P2/P3) |
| J-16 | P1 | DONE (K9) | Accessibility sweep (K9-B1) |
| J-17 | P2 | DONE (K9) | Evidence page and stability numbers (K9-B1/K9-B2) |
| J-18 | P2 | OPEN | Screenshots kept (D8, Jim's decision); legacy showcase kept |
| J-19 | P2 | NEXT | Deferred until after submission (WI-8.3) |
| J-20 | P2 | PARTIAL | Docker CI added; smoke test by K9-P7; Python version mismatch open |
| J-21 | P2 | DONE | Apache-2.0 LICENSE added (K9-P6) |

---

## Method

- **Commit reviewed:** `main` at `3abb3e4`.
- **Setup:** local service (`ANVESHAN_MODE=recorded`, the default) and the Vite app, driven in the built-in browser.
- **App paths exercised:**
  - landing → Kolam source → practice → canvas baseline → retry → transmission record;
  - Origami source page;
  - "Ask the source" in recorded mode, then with `?mode=live`.
- **Earlier, same day:** the composer and universal flows were exercised end to end in live mode (E7 in `docs/validation/experiments.md`) and are not repeated here.
- **Code read:**
  - the service (`settings`, `deps`, `main`, `routes/compose`, `adapters`);
  - the model gateway, Dockerfile, deploy checklist, CI workflow, README and handoff gating;
  - size and quality signals across `tracks/` and `app/`.
- **Baseline checks:** 449 non-live tests pass, plus governance, case packs, contract parity and the app build (E7).
- **Panel:** five seats, each mapped to a criterion:
  - Gen AI / ML engineer — Technical, 40 %;
  - platform / SRE — Technical, scalability;
  - domain and learning-science reviewer — Problem & Impact, 25 %;
  - product and innovation judge — Innovation, 25 %;
  - UX and accessibility judge — UX, 10 %.

## Panel scores (as of 3abb3e4, if deployed as-is in live mode)

| Criterion | Weight | Score /10 | Weighted | One-line rationale |
|---|---:|---:|---:|---|
| Technical merit & Gen AI | 40 % | 7.0 | 2.80 | A real multimodal pipeline with deterministic scoring and replayable tests. Weak on deployed-service safety (cost, shared state) and live verdict variance |
| Problem alignment & impact | 25 % | 5.5 | 1.38 | The problem is clear, but no real expert or learner has used it; every package is "REVIEW: PENDING" |
| Innovation & creativity | 25 % | 7.5 | 1.88 | "Upload any skill → grounded rubric → verified attempt → transmission record" is distinctive. Diluted by the synthetic showcase and a weak teaching step |
| UX & solution design | 10 % | 5.5 | 0.55 | Coherent loop, but jargon, wall-of-text instructions, 8-10 px type, and judges cannot try most cases without their own media |
| **Total** | | | **6.6 / 10** | Target after the plan: ~8.0 (see the plan, §6) |

## What the panel praised (keep and show)

1. **Deterministic, auditable scoring.**
   - Every criterion cites source claims (for example "cites CLM-05").
   - Scores come from fixed bands, and the UI says so ("No model authors a score; UNCERTAIN scores zero and is reported").
   - MEASURED and AI-JUDGED badges separate observation from verdict.
   - This is the strongest answer to "is the AI hallucinating?".
2. **One universal pipeline for three modalities.** Perception → SkillModel → evaluation works for images, video and audio, with refusals for unrelated uploads (E6, E7). It is not a one-off demo per case.
3. **First divergence plus the transmission record.**
   - The baseline → retry comparison shows criterion transitions and a provenance hash.
   - The honest disclaimer ("it is not a certification of skill") is visible.
4. **Grounded Q&A.** In live mode, "Ask the source" on Origami answered with cited claims (CLM-04, CLM-09) and timestamped evidence (102.0-104.0 s), with inferred material marked as inferred.
5. **Honest labelling everywhere.** INTERNET REFERENCE, INFERRED vs OBSERVED, SYNTHETIC REPLAY, "package not expert-approved".
6. **Engineering discipline.**
   - The model gateway has a registry, recording, replay keys and backoff.
   - Recorded mode makes 449 tests deterministic.
   - The frozen contracts are checked against the UI types by CI.
   - Strict TypeScript.

## Findings

Severity:
- **P0** = blocks a safe or credible deployed demo;
- **P1** = moves the score materially;
- **P2** = polish or hygiene.

Criterion tags:
- **T** = Technical;
- **I** = Problem & Impact;
- **N** = Innovation;
- **U** = UX.

### P0 — deployment safety and credibility

| ID | Tag | Finding | Evidence | Status (2026-10-08) |
|---|---|---|---|---|
| J-01 | T U | **The README is the judges' first page, and it is stale and garbled.** · 17 mojibake sequences. · "Product name: TBD". · Status says branch `m1/hero-cases`, 2026-10-06, "~423 passed", "Not yet deployed". · Stack hypothesis lists "Gemini 3.5 Transcribe" and "ADK", which are not used. · "What works" says Origami is a working hero case. | `README.md` (BOM plus double-encoded UTF-8 arrows) | **DONE** — README rewritten (K9-P6) |
| J-02 | T | **No cost or abuse guard on a public URL.** · Any visitor can run compose and attempts in live mode without limit. · `?mode=live` overrides the server default even when it is `recorded`. · No per-IP rate limit, no daily call budget. · A crawler or one curious user can exhaust the Gemini quota during judging, and then the app fails for the judges. | `service/anveshan_service/deps.py` `get_mode`; no limiter in `main.py`; `ModelGateway.generate_json` has no budget | **DONE** — Rate limits, daily budget and visitor isolation added (`service/anveshan_service/limits.py`, `visitors.py`, `housekeeping.py`) |
| J-03 | U T | **Recorded mode shows raw internals.** "Ask the source" on Origami showed `REPLAY_MISMATCH · HTTP 409 no recorded run for evidence_query@v1 (key d8ac59c1...)`. The Dockerfile defaults to `ANVESHAN_MODE=recorded`, and the composer cannot work in recorded mode for new uploads. | Browser, `?view=source&case=origami`; `Dockerfile` ENV | **DONE** — Friendly error messages in `app/src/api/errors.ts` |
| J-04 | I T | **Origami is presented as a "Live hero case" but is not demo-safe.** · The dedicated engine fails its own perfect attempt (decision D1 is still open). · Title says "Petal Folding", but the goal ends at "kite form", before the petal fold. · CLM-05 repeats "taller than wide; taller-than-wide". · Claims labelled OBSERVED carry conf 0.33. · The video panel is black until played. | Landing cards; Origami source page; `tracks/track-b/eval/origami/RESULTS.md` | **DONE (K9)** — Origami rebuilt via universal pipeline (K9-P5) |
| J-05 | T U | **One shared state for every visitor.** · "Your composed skills" lists every visitor's uploads, which anyone can open and play: a privacy problem for people's own videos. · Expert Review lets anyone approve or revise the hero packages under any reviewer name, so a stranger can flip a hero case to "APPROVED". | `track_a.api.list_cases` returns all composed cases; review UI on hero source pages | **DONE** — Case ownership and visitor isolation added (`service/anveshan_service/visitors.py`) |
| J-06 | T | **The deploy path has never been exercised.** · The Dockerfile has never been built (no Docker locally, no CI image build). · The image build downloads ~50 MB from Wikimedia (`tools/fetch_media.py`), so a rate limit or network failure fails Cloud Build. · `DEPLOY-CHECKLIST.md` still says "Deployment branch m1/hero-cases... Do NOT deploy main". · CI runs Python 3.12; the container runs 3.13. | `Dockerfile`, `.github/workflows/checks.yml`, `docs/deploy/DEPLOY-CHECKLIST.md` | **DONE** — Docker image build added to CI (`.github/workflows/checks.yml`) |
| J-07 | T | **Capacity during judging.** · Concurrency 1 and max-instances 1, with synchronous 25-60 s compose and attempt requests: a second judge either waits behind someone else's compose or gets a 429. · `/tmp` on Cloud Run is in-memory and counts against the 2 GiB limit. · Uploads (up to 30 MB each), drafts and keyframes are never cleaned up, so memory grows over the judging window. | `DEPLOY-CHECKLIST.md` settings; no TTL or cleanup in `service/` or `composer.py` | **DONE** — Housekeeping, TTL and capacity limits added (`service/anveshan_service/housekeeping.py`, `limits.py`) |

### P1 — score-moving

| ID | Tag | Finding | Evidence | Status (2026-10-08) |
|---|---|---|---|---|
| J-08 | I | **No human evidence yet.** · All seven cases are internet or synthetic. · Every package is "REVIEW: PENDING". · No real learner has done baseline → retry. · The judging strategy itself names "baseline → intervention → retry → measured change → expert review" as the strongest impact proof. | `docs/hackathon/judging-strategy.md`; landing badges | **OPEN** — Needs a real pilot and expert review; humans required |
| J-09 | N U | **Feedback reads like a template, and Gen AI is absent where the learner feels it.** · The DIFFERED line is tautological: "Expected: fraction of learner ink samples within 6.0 px of the goal line. Does not meet the expected indicator: fraction of learner ink samples within 6.0 px of the goal line." · The micro-drill card shows only a title ("Practise: No stray lines off the pattern"). · Summary shows a raw time ("at time 0.001"). | Kolam attempt result; `track_b/feedback.py`, `drill.py` have no model calls | **DONE** — AI coaching wording added (E8, `tracks/track-b/src/track_b/coach.py`) |
| J-10 | I U | **The TRANSMIT (teaching) step is thin.** · Kolam stages are taught as coordinates ("draw from (49% across, 7% down) to (18% across, 82% down)"). · Practice instructions are one 12-item paragraph that sends the learner to claim IDs ("follow [CLM-06]"). · There is no "show me" playback, though the geometry already exists. | Kolam source and practice pages | **DONE** — Show-me animation and drill cards added (`tracks/track-b/src/track_b/coach.py`, K9-P2) |
| J-11 | U | **Judges cannot try most cases.** · Only the Kolam canvas works without the judge's own materials. · Origami needs a folding video, Tabla a tabla recording, and the composer the judge's own media. · There are no sample attempt files and no "try a good / flawed attempt" buttons. | Practice views; no sample affordance in `app/src` | **DONE (K9)** — Sample attempts added for hero cases (K9-P4) |
| J-12 | T | **Live verdict variance, and no read-through cache.** · The swapped-order video went PASS, FAIL, PASS over 3 runs. · A look-alike unrelated image FAILs instead of being REFUSED. · Live mode never reuses an identical earlier call, so the same file can get a different verdict when a judge retries it, and every repeat costs money. | E7; `ModelGateway.generate_json` (live never consults `RunStore`) | **PARTIAL** — Live cache added (E7); swapped-order instability is a known limit; WS6 robustness moved to NEXT |
| J-13 | N U | **The synthetic showcase dilutes the story.** Four of the seven cards on the landing page are synthetic replays, written in dense jargon ("ratchet stop speeder torque-limiting"). Judges may read them as padding. | Landing page "Other archetypes" | **DONE (K9)** — Showcase collapsed; plain language cleanup (K9-P2/P3) |
| J-14 | U | **Developer artefacts and jargon in the product chrome:** · header "SEAM: 8 CONTRACTS · SCORES DETERMINISTIC"; · a "STITCH" button ("View Google Stitch design reference"); · "MODE: SERVER DEFAULT"; · "CONTRACT GAIN (TRANSMISSIONRECORD)"; · a "LEARNER LEARNER" badge; · stale copy "Gemma reads sampled frames" (Cloud Run uses Flash-Lite). | Header, transmission view, `HeroPracticeView.tsx:32` | **DONE (K9)** — Developer chrome cleaned up (K9-P2/P3) |
| J-15 | U I | **Inaccurate or misleading copy:** · the practice banner says the service "may refuse attempts until an expert approves it", but it refuses only when every package version is rejected (`track_b/handoff.py`); · the Origami question box placeholder is Kolam-specific ("Which dots stay enclosed?"); · "+0.0" gain is shown in success green; · the lineage shows `expert_id: Mayooranathan (Tamil Wikipedia)`, which puts the photographer of an internet image in the expert slot, against the honesty rule that internet media is never an authentic expert. | Practice banner; `HeroSourceView.tsx`; transmission view | **DONE (K9)** — Copy corrections applied (K9-P2/P3) |
| J-16 | U | **Accessibility:** · 260 uses of 8-10 px text; · heavy uppercase monospace; · low-contrast secondary text on near-black; · Kolam input is canvas-only, with no alternative; · about 50 `aria-label`/`alt` attributes across the app. | `grep text-[8-10px] app/src` | **DONE (K9)** — Accessibility sweep completed (K9-B1) |
| J-17 | T | **The evidence is not visible in the app.** The E1-E7 validation lives in docs only. A judge using the app never sees pass/fail accuracy or stability numbers. | `docs/validation/experiments.md` | **DONE (K9)** — "How we check" evidence page and stability numbers added (K9-B1/K9-B2) |

### P2 — hygiene (public repo)

| ID | Tag | Finding | Evidence | Status (2026-10-08) |
|---|---|---|---|---|
| J-18 | T | **Public-repo noise:** · `screenshots/`: 42 MB, 165 files, mostly 2026-10-04 runs of the earlier prototype; · legacy synthetic-showcase UI: `StitchModal`, `DualDeckPlayer`, `workspaces/*`, and a 2,070-line `app/src/data/cases/registry.ts`. | `git ls-files` | **OPEN** — Screenshots kept (D8, Jim's decision); legacy showcase kept |
| J-19 | T | **Large modules and broad exception handling:** · `track_b/evaluators/universal.py` is 1,520 lines; · 55 `except Exception` in non-test code. | `wc -l`, grep | **NEXT** — Deferred until after submission (WI-8.3) |
| J-20 | T | **CI gaps:** no Docker image build, no browser smoke test, and a Python version mismatch (J-06). | `checks.yml` | **PARTIAL** — Docker image build added (J-06); smoke test added by K9-P7; Python version mismatch open |
| J-21 | T | **No LICENSE** (already Jim's action). | repo root | **DONE** — Apache-2.0 LICENSE added (K9-P6) |

## Panel verdict

The engineering core is genuinely strong and honest. The risk is not the AI; it is what a judge meets first:
- a garbled README;
- a URL that anyone can drain;
- shared state;
- one hero case that fails;
- results they cannot try without their own media.

The largest *score* upside is in three areas:
- **human evidence**: a tiny real pilot and one real reviewer;
- **Gen AI where the learner feels it**: grounded coaching wording and a "show me" teaching step;
- **judge-tryable sample attempts**.
