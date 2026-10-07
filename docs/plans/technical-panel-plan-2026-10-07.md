# Technical-panel update plan — 2026-10-07

Status: **PROPOSED.** This responds to `docs/research/judges-panel-review-2026-10-07.md` (finding IDs J-01…J-21). Each work item (WI) lists:
- the findings it closes;
- the files it touches;
- the approach;
- the tests;
- the acceptance criteria;
- the effort;
- the owner.

**Scope rule (AGENTS.md "no free scope").** Workstreams 1–3 harden and fix what already exists. Workstreams 4–5 add product behaviour, so Jim must decide them first (decisions D4–D8 in §5). Nothing here changes the eight frozen contracts or makes scoring depend on a model.

**Delivery rule (decision D3, recommended).** One work item = one branch = one PR into `main` (Jim merges in GitHub Desktop or on the web). Docs-only changes may be pushed directly. Every PR runs the `anveshan-verify` checks.

---

## 1. Panel and principles

The technical panel (architect, Gen AI engineer, SRE, frontend/UX engineer, QA) agreed on five principles:

1. **Protect the demo first.** A judge must never meet a drained quota, someone else's upload, a raw stack-style error, or a failing hero case.
2. **Make it tryable in 60 seconds** with no materials: sample attempts with recorded results.
3. **Put Gen AI where the learner feels it**, without letting it touch scores: wording and teaching only, with validators and fallbacks.
4. **Evidence beats claims.** A small real pilot and one real reviewer are worth more than another engine feature.
5. **Freeze code on Oct 15.** After that, only demo-blocking fixes.

---

## 2. Workstreams

### WS1 — Deployment safety (P0). Closes J-02, J-03, J-05, J-06, J-07.

**Status: DONE** (WI-1.1–1.6 on `main` before K9; WI-1.5 smoke gate added by K9-P7).

**WI-1.1 Cost and abuse guard.** Owner: Claude. Effort: M (½ day).

Files:
- `service/anveshan_service/settings.py`
- `deps.py`
- `main.py`
- new `service/anveshan_service/limits.py`
- `tracks/common/models.py` (budget hook only)

Approach:
- **Mode override.** New setting `allow_mode_override` (env `ANVESHAN_ALLOW_MODE_OVERRIDE`, default `false` when `K_SERVICE` is set (Cloud Run), else `true`). `get_mode` ignores `?mode=` when it is false. The UI runtime panel hides the mode switch when `/api/health` reports `mode_override: false`.
- **Per-IP rate limit.** A token bucket in memory (single instance, so no store is needed), keyed by the `X-Forwarded-For` first hop.
  - Defaults: `POST /api/compose/analyze` 6 per hour, attempts 30 per hour, "Ask the source" 30 per hour.
  - Over the limit, return 429 `RATE_LIMITED` with a human message and `retry_after_s`.
- **Daily live-call budget.** A process-wide counter in `ModelGateway`: `ANVESHAN_DAILY_CALL_BUDGET`, default 2000 calls per UTC day. When it is exhausted, live calls raise `ModelError(SERVICE_UNAVAILABLE, "Today's live AI budget for this demo is used up; recorded samples still work.")`. Recorded and cached calls do not count.
- **Jim, outside the code:** set a quota or budget alert on the Gemini API key's project (AI Studio / Cloud Billing budget, about US$20).

Tests:
- `service/tests/test_limits.py`:
  - bucket refill and 429 shape;
  - override ignored when disabled;
  - budget exhaustion raises the right category.
- A gateway unit test with a fake client confirms that recorded and cached calls do not decrement the budget.

Acceptance:
- 7 analyses from one IP in an hour → the 7th returns 429 with a readable message.
- `?mode=live` on a server with the override disabled → still recorded.
- All existing tests pass.

**WI-1.2 Per-visitor isolation and read-only hero packs.** Owner: Claude. Effort: M (½–1 day).

Files:
- `service/anveshan_service/main.py` (cookie middleware)
- `routes/compose.py`
- `routes/cases.py`
- `tracks/track-a/src/track_a/api.py` (`list_cases` filter param)
- `tracks/track-a/src/track_a/composer.py` (owner tag in the draft and case metadata; not a contract field: stored in `var/.../owner.json`)
- `app/src/App.tsx` / discovery view

Approach:
- **Visitor id.** An anonymous `anv_vid` cookie (random 128-bit, HttpOnly, SameSite=Lax, Secure on HTTPS).
- **Owned skills.** Composed cases and drafts record their owner id. `GET /api/cases` returns curated cases plus composed cases owned by the caller. A composed case opened by URL from another visitor returns 404.
- **Review.** `POST …/review` on curated (`tracks/cases/*`) packs returns 403 `REVIEW_DISABLED` unless `ANVESHAN_REVIEW_TOKEN` is set and sent as a header (for the real expert in WI-5.2). Review on your own composed case stays allowed. In the UI the review panel on curated cases shows "Expert review is by invitation in this demo".
- **Optional curated composed case.** Jim can choose one composed case to show to everyone: Origami via the universal path (see WI-2.1). It lives under `tracks/cases/` and is committed, so it is curated, not owned.

Tests:
- Service tests with two clients (different cookies): A's composed case is invisible to B (list and GET).
- Review on a curated case without the token → 403; with the token → 200.
- Composer tests: the owner file is written.

Acceptance: in two browser profiles, neither sees the other's uploads, and the hero cases cannot be approved anonymously.

**WI-1.3 Storage hygiene (in-memory `/tmp`).** Owner: Claude. Effort: S (2 h).

Files:
- new `service/anveshan_service/housekeeping.py`
- `main.py` (startup hook, plus a run every N requests)

Approach:
- Delete uploads, drafts and composed data older than `ANVESHAN_DATA_TTL_H` (default 6 h). Never touch committed `tracks/cases`.
- Cap total `data_dir` size (default 600 MB) by deleting the oldest first.
- Delete raw attempt uploads after evaluation, unless the result view needs them. The UI already keeps the local object URL for display; confirm with `make_attempt_media`.

Tests: tmp-dir fixtures with backdated mtimes; the size-cap eviction order.

Acceptance: after 20 synthetic composes, `data_dir` stays under the cap, and the newest drafts survive.

**WI-1.4 Human error messages.** Owner: Claude. Effort: S (2 h).

Files:
- `app/src/api/*` (error normaliser)
- the shared error component
- `service/anveshan_service/errors.py` (message map only)

Approach:
- Map the categories to plain text, keeping the code in a collapsible "details" line:
  - `REPLAY_MISMATCH` → "This needs live AI, and this deployment is running recorded demos. Try a sample attempt.";
  - `RATE_LIMITED`;
  - `SERVICE_UNAVAILABLE` (budget);
  - 5xx.
- Never show the replay key in the main message.

Tests: a unit test of the TypeScript mapper; the `npm run build` type check.

Acceptance: the Origami "Ask the source" in recorded mode shows the friendly sentence.

**WI-1.5 Prove the image builds before deploy day.** Owner: Claude (CI) and Jim (Cloud Build). Effort: S–M.

Files:
- `.github/workflows/checks.yml` (new `docker-build` job: `docker build .` on push to main and on PRs touching `Dockerfile`, `service/`, `tools/fetch_media.py`; CI Python moves to 3.13)
- `tools/fetch_media.py` (explicit `User-Agent`, 3 retries with backoff, clear failure message)
- `docs/deploy/DEPLOY-CHECKLIST.md` (deploy from `main`; remove the "do NOT deploy main" note; add the WI-1.1 and WI-1.2 env vars; test count 449+)

Acceptance:
- The GitHub Actions `docker-build` job is green.
- The checklist matches the code (env var names are checked by grep).

**WI-1.6 Capacity: safe concurrency on one instance.** Owner: Claude. Effort: M (½ day).

Files:
- new `tracks/common/locks.py`, a per-path `threading.Lock` registry (single process, single uvicorn worker);
- used in `composer.create_draft` and `create_case_from_draft`, `track_a.api.build_case` and `apply_review`, and the session writes in `track_b/session.py`.

Approach:
- Lock per case or draft directory, so independent visitors run in parallel.
- Confirm that `ModelGateway` is thread-safe: one `genai.Client` per gateway, and the gateway is created per request in `RunContext.create`, so it is.
- Then deploy with **concurrency 8**, max-instances 1 (keep 1: composed cases live on the instance's disk).

Tests: a threaded test (2 composes plus 2 attempts on fakes) with no interleaved writes, plus an idempotency test on the same draft from two threads.

Acceptance: a load test of 4 parallel attempts in recorded mode finishes without errors; the p95 latency is recorded.

Ops (Jim, D6): min-instances 1 only during the judging window, about Oct 18–25, which costs a few dollars and avoids cold starts.

---

### WS2 — Demo integrity and copy (P0/P1). Closes J-01, J-04, J-13, J-14, J-15.

**Status: DONE** (WI-2.1 K9-P5; WI-2.2/2.3 K9-P2/P3; WI-2.4 K9-P6).

**WI-2.1 Origami decision D1.** Owner: Claude after Jim decides. Effort: M.

Approach (recommended option):
- Build a committed curated case `tracks/cases/origami-universal/` from the full OrigamiCrane video through the universal composer, in live mode once. Commit its recorded runs so it works in recorded mode and costs nothing.
- Its positive control already passes 11/11 (NEXT-STEPS D1).
- Title it accurately: "Origami crane: square to kite base".
- Hide the dedicated `origami` engine from the landing page; keep it reachable with `?case=origami` and label it "EXPERIMENTAL".
- Fix the claim text duplication ("taller than wide; taller-than-wide"): de-duplicate attribute lists in `track_a/goals/origami.py`.
- Rule for confidence below 0.5: if `verification_state=observed` and `confidence < 0.5`, the UI shows "OBSERVED (low confidence)". This is display only; no contract change.

Tests:
- `check_case_packs.py` passes for the new pack.
- A Track B recorded test: perfect attempt PASS, missing-step attempt FAIL.

Acceptance: the landing page shows Kolam, Origami (universal) and Tabla, all of which pass their own positive control in recorded mode.

**WI-2.2 Product-chrome cleanup.** Owner: Claude. Effort: S (½ day).

- Remove the "STITCH" button, the "SEAM: 8 CONTRACTS" block and the "MODE" chip from the production header. Keep them behind `?debug=1`.
- Copy changes:
  - "Contract gain (TransmissionRecord)" → "Score change";
  - "Skill gain excluding observability" → "Change on criteria seen in both attempts".
- Show a neutral colour for a zero gain, amber for negative, green for positive.
- Fix "LEARNER LEARNER": render "Learner: <name>", default "Guest".
- Remove the stale "Gemma reads sampled frames" text: read the model names from `/api/health`.
- Banner text: "Not yet reviewed by an expert. Results are engineering evidence, not certification." Remove the inaccurate "may refuse attempts".
- Use a case-specific "Ask the source" placeholder from case data (`lesson.example_question`), with a generic fallback.
- In the lineage, for INTERNET REFERENCE sources, label the `expert_id` value "Source author (internet reference — not a verified expert)". This is display only; the contract field is unchanged.

Tests: build, plus a grep test in CI that the production bundle has no "Stitch" text.

Acceptance: J-14 and J-15 items are verified in the browser.

**WI-2.3 Synthetic showcase.** Owner: Claude. Effort: S.

- Recommended: move the four synthetic cards into a collapsed "Design archetypes (synthetic, not evaluated)" section at the bottom, with one plain sentence each.
- Alternative: remove them from the landing page (D7).

Acceptance: above the fold, the landing page shows only the hero cases and the composer.

**WI-2.4 README rewrite.** Owner: Claude. Effort: M (½ day).

Structure:
1. A one-sentence pitch and the live URL.
2. **Try it in 90 seconds** (sample attempts from WI-3.1).
3. What it does, as a 6-step loop diagram.
4. **How Gen AI is used**: a table of model, job, where determinism takes over, and how it is evaluated.
5. Architecture: Cloud Run, Gemini 3.5 Flash-Lite, Gemini Embedding 2, recorded/replay.
6. Evidence summary (E6, E7, E8 pilot) and honest limits.
7. Run locally and test.
8. Licences (code and media).

Move the vision and governance prose to `docs/product/`, linked. Save as UTF-8 without a BOM, with no mojibake. Remove "Product name: TBD" and the stack-hypothesis section.

Acceptance:
- `grep -c "â" README.md` returns 0.
- Every command in the README runs.
- A judge reaches the URL and the "try it" path within the first screen.

---

### WS3 — Judge-tryable flows (P1). Closes J-11, J-12.

**Status: DONE** (WI-3.1 K9-P4/P2/P3/P5; WI-3.2 on `main` before K9).

**WI-3.1 Sample attempts with recorded results.** Owner: Claude. Effort: M–L (1 day).

Files:
- `tracks/cases/<case>/samples/` (each ≤ 2 MB, generated by us, so licence-clean and SYNTHETIC-labelled)
- `manifest.json` `samples` list (case-pack metadata, not one of the 8 contracts)
- service `GET /api/cases/{id}/samples` and `POST …/attempts/sample/{sample_id}`
- UI "Try a sample attempt" buttons on each practice page and in the composer ("Try the composer with a sample video")

Samples:
- **Kolam:** a good trace and a missing-stage trace (stroke JSON), plus one photo.
- **Origami (universal):** a perfect clip and a skipped-step clip (from `tools/stress_universal_video.py` output, re-encoded under 2 MB).
- **Tabla:** an on-tempo and a rushed recording (synthesised with `tabla_dsp`).
- **Composer:** the synthetic "draw a house" video and one image.

Recorded runs for every sample are committed, so samples work in recorded mode at zero cost. Every result is labelled "SYNTHETIC SAMPLE".

Tests:
- Recorded tests that each sample's verdict matches its label (good → PASS, flawed → FAIL).
- `check_case_packs.py` extended for `samples` (sha256, size ≤ 2 MB, licence field).

Acceptance: a judge with no files can run a pass and a fail on every hero case in under 60 s each.

**WI-3.2 Live read-through cache.** Owner: Claude. Effort: S–M.

Files:
- `tracks/common/models.py` (`generate_json`, `embed`)
- `RunStore`

Approach:
- In live mode, look up `replay_key` in the session's run store first. On a hit, return it with `runtime_class="RECORDED_LIVE"` and the note `cache_hit`.
- On a miss, call the model and save the result (saving already happens).
- Controlled by `ANVESHAN_LIVE_CACHE=true` (default on). The key already covers the model, prompt version, system text and input digests, so any change misses.

Effect: identical uploads get identical verdicts and cost nothing, which fixes the "retry gives a different answer" failure for judges. The variance on *new* inputs remains, and is documented.

Tests: a fake client counts calls (2 identical calls → 1 client call); a prompt-version bump → a miss.

Acceptance: re-uploading the same attempt returns a byte-identical evaluation, with a "cached" badge in the run metadata.

---

### WS4 — Gen AI where the learner feels it (P1; needs D4 and D5). Closes J-09, J-10.

**Status: DONE** (WI-4.1 on `main` before K9 + E8/E9 by K9-P6; WI-4.2/4.3 on `main` before K9).

**WI-4.1 Grounded coach wording (AI-worded, never scored).** Owner: Claude. Effort: M (1 day).

Files:
- new prompt `tracks/common/prompts/coach_feedback_v1.txt`
- `tracks/track-b/src/track_b/feedback.py`
- new `track_b/coach.py`
- UI feedback card

Approach:
- After the deterministic evaluation, send one Flash-Lite call with:
  - each failing criterion's name;
  - the measured finding text;
  - the cited claim statements;
  - the first divergence.
- Output schema: `[{criterion_id, coaching (≤ 40 words), cites: [claim_id]}]`.
- **Validator:** reject any item that:
  - introduces a number not present in its inputs;
  - cites a claim not in its inputs;
  - mentions a pass/fail verdict.

  Rejected items fall back to the template text.
- Show it as the "Try" line with a badge "AI-WORDED · grounded in CLM-05". The template remains visible under "details".
- Also fix the template: remove the tautological DIFFERED line. Show "Target: ≥ 90 % within 6 px · You: 42.8 %" from the band thresholds. Format times with `fmtPosition`.
- Recorded fixtures for tests; live calls count against the WI-1.1 budget.

Tests:
- Validator unit tests (invented number → rejected; foreign claim id → rejected).
- Recorded end to end: the coaching shows and the scores are unchanged byte for byte.

Evaluation (evidence rule): run on 20 recorded attempts across the cases and record the validator rejection rate and two human ratings (clarity, faithfulness) as E9.

**WI-4.2 Real micro-drills.** Owner: Claude. Effort: S–M.

- **Kolam:** the drill canvas shows only the first-divergence stage's target segment as a faint guide ("trace this stage 3 times"), using `kolam_geometry` stage polylines. Unscored, as today.
- **Universal video:** show the expert keyframe and timestamp of the missed step, plus that step's checks.
- **Tabla:** a click-track at the target tempo with the 4-beat bol pattern.

Acceptance: the drill card always has an actionable body, never only a title.

**WI-4.3 "Show me" teaching step (TRANSMIT).** Owner: Claude. Effort: M (1 day).

- **Kolam:** stage-by-stage animated stroke playback on the dot grid from the goal's stage polylines. Each step card says "Stage 3 of 8 · show me" instead of coordinates. The coordinates move into a details line.
- **Universal video:** step cards with the expert keyframe thumbnail and a "play from 01:42" link into the source video.
- Practice instructions render as a numbered list, with claim IDs as small chips that show the claim on hover.

Acceptance: a first-time user can follow Kolam stage 1 without reading any coordinates (checked in the pilot, WI-5.1).

---

### WS5 — Evidence and impact (P1; humans). Closes J-08, J-17.

**Status: PARTIAL** (WI-5.1 pilot HUMAN — Jim to run; WI-5.2 expert review HUMAN — Jim to arrange; WI-5.3 evidence page DONE K9-B1; WI-5.4 stability numbers DONE K9-B2).

**WI-5.1 Mini pilot (E8).** Owner: Jim runs it, Claude prepares. Effort: about 2 h of people time.

- Participants: 3–5 adult colleagues (21 or over) who are not on the team. Written consent: a one-paragraph form in `docs/validation/pilot-consent.md`.
- Protocol: Kolam canvas baseline → read the feedback and drill → retry.
- Export each `TransmissionRecord` JSON with no names, using participant codes P1–P5.
- Three questions: "Did the feedback tell you what to change?", "Was it clear?", "Would you use this to learn?" (1–5 scale).
- Claude writes `tools/pilot_summary.py`. It reads the exported records and produces gain per participant, criteria improved and a first-divergence change table, saved in `docs/validation/experiments.md` E8.
- Honest framing: "pilot, n = 5, not a validated study".

Acceptance: E8 is recorded, with the raw records committed under `docs/validation/pilot/` (no personal data).

**WI-5.2 One real expert review.** Owner: Jim. Effort: about 1 h.

- A person who actually draws kolam (or folds origami) reviews the claims, using the invitation token from WI-1.2.
- At least one package is APPROVED or REVISED by a named, consenting reviewer.
- The review record is committed.

**WI-5.3 In-app "Evidence" page.** Owner: Claude. Effort: S–M.

- A `/evidence` view renders a committed `docs/validation/evidence.json`, generated by `tools/build_evidence.py` from the E6–E9 summaries:
  - per-modality pass/fail matrices;
  - stability across 3 runs;
  - pilot gains;
  - the limits list.
- Linked from the header and the README.

**WI-5.4 Stability numbers.** Owner: Claude. Effort: S (mostly runtime).

- Run each WI-3.1 sample 3 times in live mode, with the cache off.
- Publish the verdict agreement % per modality in E7b. This turns "variance exists" into a number.

---

### WS6 — Universal-path robustness (P2, optional). Closes part of J-12.

**Status: NEXT** (deferred to post-submission per decision 2026-10-07).

- **WI-6.1 Ambiguous-band relevance.** For similarity between 0.70 and 0.80, add a side-by-side yes/no check of the expert image and the attempt (`relevance_v2.txt`). Target: the look-alike unrelated image is REFUSED; recorded test plus 3 live runs.
- **WI-6.2 Novel-state check for swapped order.** Compare each attempt keyframe with *all* expert keyframes in one call. If the answer is "none of these", mark it off-path. Target: swapped order FAILs 3/3 with no new false FAIL on perfect runs (E-series).

Do these only if WS1–WS5 are done by Oct 13.

### WS7 — Accessibility (P2). Closes J-16.

**Status: DONE** (WI-7.1 K9-B1 + K9-P2/P3 in their own files).

**WI-7.1** Owner: Claude. Effort: S–M.
- Minimum 12 px for body and table text, and 11 px for labels: replace `text-[8px]`, `text-[9px]` and `text-[10px]` with tokens.
- Raise the `on-surface-variant` contrast to at least 4.5:1 on the dark surface.
- Visible focus rings; `aria-label` on icon buttons.
- Keep upload (photo) as the documented non-canvas alternative for Kolam.

Check: the axe-core browser console scan on 5 key views has no serious or critical issues.

### WS8 — Public-repo hygiene (P2). Closes J-18, J-19, J-20, J-21.

**Status: PARTIAL** (WI-8.1 screenshots HUMAN/NEXT — Jim's decision D8; WI-8.2 showcase kept collapsed; WI-8.3 NEXT — deferred; WI-8.4 LICENSE DONE K9-P6; make-public HUMAN — Jim after merge).

- **WI-8.1** `git rm -r screenshots/runs` (keep `screenshots/latest` and the README). It stays in history and needs D8.
- **WI-8.2** If WI-2.3 removes the showcase, delete the legacy synthetic UI (`StitchModal`, `DualDeckPlayer`, `workspaces/*`, `data/cases/registry.ts` synthetic entries). Otherwise leave it.
- **WI-8.3** Split `track_b/evaluators/universal.py` into `relevance.py`, `matcher.py`, `judges.py` and `assemble.py`, with no behaviour change. **Deferred until after submission**: too risky in the final week for no judge-visible gain.
- **WI-8.4** LICENSE (Jim, D-licence), then make the repo public.

### WS9 — Three product roles, end-user-centric surfaces (P0, DECIDED by Jim 2026-10-07). Closes the rest of J-14, J-15 and J-16 (wording).

**Status: DONE** (K9-P1/P2/P3/P7 + PC gate; `k9/integration` pending merge to `main`).

**Problem.** The learner's path showed evaluation tooling:
- "Expert review · Approve, revise or reject claims";
- claim IDs, confidence numbers and run-class badges;
- lineage hashes and the provenance DAG.

The product read as an evaluation harness, and the BRD's knowledge owners and curators (§4.3–4.4) had no surface.

**Decision.**
- Three roles, as defined in `docs/product/product-vision.md` §9A, `docs/product/user-journeys.md` Journeys 7–8 and `docs/status/DECISIONS.md` (2026-10-07):
  - **Learner:** plain language, no audit tooling.
  - **Creator:** check what the AI understood, publish with credit, licence and consent, see insights.
  - **Steward:** review queue, library and moderation, consent and licence ledger, insights, usage.
- `?debug=1` stays a team-only diagnostic view.
- No accounts:
  - creators are identified by the visitor cookie;
  - stewards by an access code (`ANVESHAN_STEWARD_TOKEN`).
- Runtime state is temporary on the demo server; durable decisions are exported and committed (`tools/apply_expert_review.py`).

**Delivery.** One Kiro session with parallel agents. Spec: `docs/kiro/specs/K9-ORCHESTRATOR.md`, plus:
- K9-00 (product, UX and copy rules);
- K9-P0 (shared foundation code);
- K9-P1 (backend);
- K9-P2 (learner surface);
- K9-P3 (creator and steward surfaces);
- K9-PC (integration and verification).

**Scope trade.** WS6 (universal-path robustness) moves to NEXT.

**NEXT (post-submission).** Accounts, persistent storage, a full admin console, and multi-steward collections.

## 3. Schedule (deadline Oct 18; submit Oct 17)

| Date | Claude | Jim |
|---|---|---|
| **Oct 8** | WI-1.1 cost guard; WI-1.4 errors; WI-1.5 CI docker build and checklist | Register team; decide D1, D4–D8 |
| **Oct 9** | WI-1.2 isolation and read-only hero packs; WI-1.3 housekeeping; WI-1.6 locks | Gemini budget alert |
| **Oct 10** | WI-2.1 Origami (universal) case; WI-2.2 chrome cleanup; WI-2.3 showcase | **Deploy** to Cloud Run (live, override off, concurrency 8); share URL |
| **Oct 11** | Live smoke test on the URL (NEXT-STEPS step 3) and fixes; WI-3.2 cache; WI-3.1 samples (start) | Roster closes |
| **Oct 12** | WI-3.1 samples (finish); WI-4.1 coach wording | Choose LICENSE; recruit pilot participants and an expert |
| **Oct 13** | WI-4.3 show-me; WI-4.2 drills; WI-5.4 stability | Run pilot (WI-5.1) and expert review (WI-5.2) |
| **Oct 14** | WI-5.1 summary (E8); WI-5.3 evidence page; WI-2.4 README; WI-7.1 a11y | Make repo public (after WI-8.1) |
| **Oct 15** | **Code freeze.** Redeploy; full browser regression on the URL; record E-numbers | Record demo video on the live URL |
| **Oct 16** | Demo-blocking fixes only | Deck |
| **Oct 17** | — | **Submit** |

**Critical path:** WI-1.1 → WI-1.2 → deploy (Oct 10) → smoke test → samples → pilot. If the deploy slips, every later item still lands locally, but the pilot should run on the deployed URL.

## 4. Verification gates (every PR)

1. `anveshan-verify`: non-live pytest (449+), governance, case packs, contract parity, compileall, app build.
2. New behaviour has recorded-mode tests. Live behaviour has an E-series entry (model, prompt version, runs, result).
3. Browser check of the touched view (built-in browser; screenshot in the PR).
4. Before the freeze, run the deployed-URL regression script `tools/smoke_deployed.py` (new, in the WS1 PR). It covers health, cases, a sample attempt per case, compose on a sample, 429 behaviour and isolation (two cookie jars).

## 5. Decisions for Jim

| ID | Decision | Recommendation |
|---|---|---|
| D1 | Origami presentation | Universal composed case as the hero; the dedicated engine is hidden and labelled experimental (WI-2.1) |
| D4 | Allow AI-worded coaching (validator-guarded, never scored) | **Yes**: it is the largest Gen AI and UX gain for the effort |
| D5 | Build "show me" teaching and real drills | **Yes** for Kolam and universal video; Tabla drill only if time allows |
| D6 | min-instances 1 during judging (about Oct 18–25) | Yes (a few dollars; no cold start in front of judges) |
| D7 | Synthetic showcase | Collapse it to the bottom of the landing page (not delete) |
| D8 | Remove `screenshots/runs` (42 MB) from the tree | Yes (it stays in git history) |
| D3 | Merge discipline | PRs for code, direct pushes for docs |
| — | Licence | Apache-2.0 (patent grant) or MIT |

## 6. Expected effect on the panel score

| Criterion | Now | After WS1–WS5 | Main drivers |
|---|---:|---:|---|
| Technical & Gen AI (40 %) | 7.0 | 8.0 | Safe deployment, cache and stability numbers, validator-guarded coaching, evidence page |
| Problem & Impact (25 %) | 5.5 | 7.5 | Pilot E8, one real expert review, honest framing |
| Innovation (25 %) | 7.5 | 8.0 | "Show me" teaching closes the TRANSMIT step; universal Origami shows the pipeline on a real video |
| UX (10 %) | 5.5 | 8.0 | Sample attempts, plain copy, readable type, no dev artefacts |
| **Weighted** | **6.6** | **≈ 7.9** | |

These are the panel's estimates, not measurements.

## 7. Explicitly out of scope before submission

- Persistent storage (GCS or a database), multiple instances, auth accounts and a full admin console (WS9 NEXT). The NEXT bucket stays as in `NEXT-STEPS.md` §5.
- New modalities, new hero cases beyond Origami-universal, and model upgrades.
- Changes to the eight contracts; any model-authored score.
