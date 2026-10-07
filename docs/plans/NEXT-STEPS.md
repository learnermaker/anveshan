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
- **Update (2026-10-07, later):** the whole engineering backlog in §4 is done, except the live smoke test on the deployed URL (it needs the URL) and the deliberately deferred crop. An end-to-end browser walk-through found and fixed real bugs (E7 in `docs/validation/experiments.md`). 449 non-live tests pass.

- **Judges-panel review (2026-10-07):** findings J-01…J-21 in `docs/research/judges-panel-review-2026-10-07.md`; the detailed update plan (WS1–WS8, schedule, decisions D4–D8) is `docs/plans/technical-panel-plan-2026-10-07.md` (PROPOSED). It supersedes the schedule in §1 for steps 2–7 where they differ.

## 1. Critical path (blocking; owner = Jim unless noted)

| # | Step | By | Done when | Risk if skipped |
|---|---|---|---|---|
| 1 | **Register the team (2–4 members) on Hack2skill**; ask the helpdesk for the deadline time zone | **Oct 9** (roster closes Oct 11) | Confirmation email received | Disqualification |
| 2 | **Deploy to Cloud Run** via the console using `docs/deploy/DEPLOY-CHECKLIST.md`: secret `gemini-api-key` in Secret Manager, 2 GiB, 2 vCPU, max-instances 1, concurrency 1, timeout 300 s | Oct 10 | `/healthz` is OK; the HTTP smoke test in the checklist passes on the live URL | No live URL means no valid submission |
| 3 | **Live smoke test of the universal path on the deployed URL** (Claude, with Jim's URL): compose one new image, one short video (≤ 60 s) and one audio skill, plus one attempt each; record latency | Oct 10 | Each compose finishes under the 300 s timeout; numbers recorded in `docs/validation/experiments.md` | Low risk. Measured locally: the 335 s Origami video composes in about 50 s; attempts take 25–62 s; images and audio under 10 s. Cloud Run CPUs may be slower. If needed, raise the timeout to 900 s |
| 4 | **Make the repository public.** Already done by Claude: the history secret scan is clean (no key pattern; only `.env.example` files were ever committed), and the media licences are checked and attributed in `docs/MEDIA-ATTRIBUTION.md`. Jim's part: (a) choose a code licence (there is no LICENSE file; MIT or Apache-2.0 are common), (b) delete the merged remote branches `kiro/*` (Claude was not permitted to), (c) switch the repo to public | Oct 12 | Repo public, with a LICENSE | Required item |
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

## 4. Engineering backlog (status 2026-10-07)

| Item | Status |
|---|---|
| Live smoke test on the deployed URL (all three modalities; record latency) | **TODO**: needs the URL from §1 step 2; Claude runs it |
| Demo-safe progress text (media-aware expected durations) | DONE |
| Matcher self-consistency (two passes, reversed order) | DONE. The swapped-order case is still unstable (cause in E7) |
| Crop to the work region | DEFERRED until real hand-held footage shows a measured need |
| Speech-skill stress test | DONE (E7). It also fixed speech being composed as rhythm |
| Kolam card title and provenance (Ithayakkamalam, not Sikku) | DONE |
| Dead code, merged worktrees | DONE. Remote `kiro/*` branches: Jim |
| Found in the UI walk-through: 404 after Create skill; cached failed drafts; transparent PNG attempts judged blind; duplicate warnings; mid-word names; long event lists; duplicate selector entries | DONE (E7) |

Possible next items (small, only if time allows; not started):
- **Relevance for look-alike unrelated images:** in the ambiguous band, ask the matcher-style yes/no with the expert image beside the attempt. Today such attempts FAIL rather than being REFUSED.
- **Swapped-order sensitivity:** add a "novel state" check that compares each attempt keyframe with *all* expert keyframes side by side, and treats "none of these" as off-path.

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
