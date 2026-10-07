# Next steps to submission (written 2026-10-07)

Status: PROPOSED execution plan. It orders the remaining work; it does not add product scope.
Hard dates: **team roster closes 2026-10-11**; **prototype submission 2026-10-18** (time zone unconfirmed; plan for 23:59 IST, UTC+5:30, and finish a day early).

Required submission items (official T&C, `docs/kiro/official-rules-2026-10-06.md`):
1. a working deployed URL (Cloud Run);
2. a demo video, strictly under 3 minutes (public YouTube, Vimeo or Drive);
3. a **public** GitHub repository;
4. a presentation deck covering architecture and the business case.

Judging weights: Technical and Gen AI 40 %, Problem and Impact 25 %, Innovation 25 %, UX 10 %.

## 0. Where we are

- `main` holds everything (the universal pipeline, three hero cases, the composer UI, the service and the deploy files). 435 non-live tests pass, governance, case-pack and contract-parity checks pass, and the app builds.
- Universal-pipeline evidence for new uploads is in `docs/validation/experiments.md` E6 (video, image and audio new-skill stress tests). Known limits are in `docs/plans/universal-pipeline.md` §12.
- Not yet done: the Cloud Run deployment, a public repo, the demo video, the deck and team registration.

## 1. Critical path (blocking; owner = Jim unless noted)

| # | Step | By | Done when | Risk if skipped |
|---|---|---|---|---|
| 1 | **Register the team (2–4 members) on Hack2skill**; ask the helpdesk for the deadline time zone | **Oct 9** (roster closes Oct 11) | Confirmation email received | Disqualification |
| 2 | **Deploy to Cloud Run** via the console using `docs/deploy/DEPLOY-CHECKLIST.md`: secret `gemini-api-key` in Secret Manager, 2 GiB, 2 vCPU, max-instances 1, concurrency 1, timeout 300 s | Oct 10 | `/healthz` is OK; the HTTP smoke test in the checklist passes on the live URL | No live URL means no valid submission |
| 3 | **Live smoke test of the universal path on the deployed URL** (Claude, with Jim's URL): compose one new image, one short video (≤ 60 s) and one audio skill, plus one attempt each; record latency | Oct 10 | Each compose finishes under the 300 s timeout; numbers recorded in `docs/validation/experiments.md` (E7) | A video compose at the 600 s cap may exceed the timeout (about 120 embeddings plus 2–4 vision calls). Mitigation: lower `_VIDEO_MAX_SEC` for the demo or raise the timeout to 900 s |
| 4 | **Make the repository public.** First run a secret scan of the full history (Claude: `git log -p --all` plus the scan pattern `AIza[0-9A-Za-z_-]{20,}`), then confirm that third-party media licences in the case packs allow redistribution | Oct 12 | The scan is clean and the repo is public | Required item |
| 5 | **Lock the demo storyline and decide the Origami presentation** (see §3, D1) | Oct 12 | Decision recorded in `docs/plans/DECISION-LOG.md` | Demo shows a failing engine |
| 6 | **Record the 3-minute demo video** on the live URL; keep a backup recording of each segment | Oct 15 | Public link, under 3:00 | Required item |
| 7 | **Deck** (architecture, Gen AI use, business case, evidence and honest limits) | Oct 16 | PDF or Slides link | Required item |
| 8 | **Submit** on the Hack2skill portal | **Oct 17** (one day of buffer) | Confirmation received | — |

## 2. Recommended demo storyline (≈ 2:50)

The main differentiator is "upload ANY skill and get a grounded, verifiable practice loop". Lead with the universal pipeline (40 % Technical + 25 % Innovation). Use the hero cases as depth, not breadth.

1. **0:00–0:20 Problem.** Expertise transfer is unverifiable. Anveshan grounds every criterion in source evidence and verifies attempts deterministically.
2. **0:20–1:20 Universal compose, live.** Upload a short, new skill video (not one of the hero cases). Show the inferred steps with thumbnails and certainty badges, the expert confirming the profile, and the generated rubric with claim citations.
3. **1:20–2:05 Verify attempts.** Show:
   - a correct attempt PASSES;
   - an attempt that skips a step FAILS on step coverage, with the off-path moment shown on the timeline;
   - an unrelated upload is REFUSED.

   Point out the MEASURED vs AI-JUDGED badges: model outputs are observations and scores are deterministic.
4. **2:05–2:35 Depth.** Show:
   - Kolam: goal-conditioned from one final image, a canvas trace, then verification;
   - Tabla: deterministic tempo and onset feedback.
5. **2:35–2:50 Architecture.** Show the architecture slide (Cloud Run, Gemini 3.5 Flash-Lite, Gemini Embedding 2, Gemma 4 offline) and the honest-limits line.

Pre-record each segment as a backup. Live model variance exists (see the known limits).

## 3. Decisions needed (Jim)

- **D1 — Origami.** The dedicated engine fails its own "perfect" attempt (5 of 7 states; `tracks/track-b/eval/origami/RESULTS.md`). The full OrigamiCrane video through the universal path passes its positive control (11/11).
  - **Recommendation:** present Origami through the universal composer as a composed case, and label the dedicated engine "experimental".
  - **Alternative:** remove Origami from the hero list and use any clean new video for the demo.
- **D2 — Demo video source for the live compose.** Use a short (30–90 s), well-lit, top-down video with clearly distinct stages, where you hold the rights or the licence is open. Claude can pre-test candidates with `tools/stress_universal_video.py`.
- **D3 — Merge discipline.** This push went to `main` directly, at Jim's explicit instruction, without a PR. For the remaining changes, use small branches and PRs again (AGENTS.md lifecycle) or continue direct pushes during the final week. Recommendation: PRs for code, direct pushes allowed for docs only.

## 4. Engineering backlog (ordered; Claude can do these; each is small and independently shippable)

Only after §1 steps 2–3 succeed. Stop when the demo is solid. Do not expand scope.

| P | Item | Why | Acceptance |
|---|---|---|---|
| P0 | Fix anything the live smoke test (step 3) reveals: timeouts, cold-start, upload size | The demo must work without manual recovery | All three modalities compose and evaluate on the live URL |
| P0 | Demo-safe defaults: cap the interactive video compose at a duration that fits the timeout; show progress text during the long compose | UX (10 %) and reliability | No request exceeds the timeout in the smoke test |
| P1 | Self-consistency for the step matcher (2 calls, keep agreeing labels) | Reduces the variance of the swapped-order verdict (known limit) | Synthetic swapped scenario gives a stable verdict over 3 live runs |
| P1 | Crop to the work region before the judges | Helps hand-dominated, low-resolution video (the Origami window limit) | Origami 0–194 s perfect attempt passes in 2 of 3 runs |
| P2 | Speech-skill stress test (utterance structure untested) | Closes a known gap | `tools/stress_universal_other.py --scenario speech` evidence saved |
| P2 | Kolam card title "Sikku" vs the note that lines pass through dots | Content accuracy | Title and description consistent with `tracks/cases/kolam` |
| P3 | Remove the dead code flagged by pyflakes (unused `needleman_wunsch` result in the universal evaluator; unused locals) | Hygiene | pyflakes shows no unused locals in `tracks/*/src` |
| P3 | Remove the merged worktrees `anveshan-wt/*` and the stale remote branches (k1–k4, wp1–wp4) | Repo hygiene before going public | `git worktree list` shows only the main folder |

## 5. Ideal next steps after the hackathon (NEXT bucket; not authorised now)

- **Real expert and learner validation.** One real expert reviews composed claims, real learners do attempts, and Transmission Gain is measured. This is the main gap in `docs/hackathon/submission-checklist.md` § Validation.
- **Persistent storage** (GCS for media; a small DB for sessions) to replace the instance disk and max-instances 1. This is needed for scale (the scalability sub-criterion).
- **Evaluation harness.** A labelled set of new-skill uploads (several domains), run nightly in recorded mode, tracking pass/fail accuracy per modality.
- **Model upgrades behind the registry** (env-configurable), each with E-series evidence before switching.
- **Expert review loop in the UI** (edit steps and checks, re-run the build) using the existing CaseProfile confirmation.

## 6. Risks and mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Deadline time-zone confusion | Medium | Submit Oct 17 |
| Gemini quota/429 during the demo | Medium | Gateway backoff exists; record the demo, don't depend on live calls; keep the AI Studio quota page open |
| Cold start (2 GiB image) in front of judges | Medium | Warm the service with `/healthz` before recording; or min-instances 1 on demo day only (small cost) |
| Live verdict variance | Medium | Demo with tested media (D2); show recorded runs if live differs |
| Repo goes public with unlicensed media | Low | Step 4 licence check; the case-media skill rules (licence + sha256 per file) |
