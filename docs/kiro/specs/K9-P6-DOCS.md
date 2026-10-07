# K9-P6 — README, LICENSE, review status, evidence docs (technical-panel WI-2.4, WI-8.4 licence part, plan bookkeeping)

Read `00-COMMON.md`, `K9-00-PRODUCT-UX.md`, then this file. Your folder, branch, status file and inbox protocol are in `K9-ORCHESTRATOR.md` §2 and §4.

**Goal.** A judge opening the public repo understands in 2 minutes:
- what Anveshan is;
- how to try it;
- where Gen AI is used and where it is deliberately not;
- what is validated versus engineering evidence;
- the limits;
- the licence.

The review and plan documents also show what was fixed.

---

## 0. Ground rules

- **Docs only.** No code, except `LICENSE` and the README.
- **Honesty rules (AGENTS.md):**
  - engineering evidence is never called validation;
  - internet media is never called an expert;
  - synthetic is labelled.
- **Claims need evidence links.** Every number you write must come from a file in the repo; cite it. If you cannot find the evidence, leave the number out.
- Use plain ASCII punctuation where the file had broken characters. Fix every mojibake sequence: `â€”` → —, `â€™` → ', `â€œ` / `â€` → " ", `Â·` → ·, `â†’` → →, `âœ“` → ✓, and any other `Ã`/`â€` sequences. Save as UTF-8 **without** a BOM.

## 1. Files you own

- `README.md`;
- `LICENSE` (new);
- `docs/research/judges-panel-review-2026-10-07.md` (status annotations only);
- `docs/plans/NEXT-STEPS.md`;
- `docs/validation/experiments.md` (new entries E8 and E9 only; PC adds E-K9 later).

## 2. LICENSE (Apache-2.0, Jim's decision)

Download the official text:

```powershell
curl --ssl-no-revoke -o LICENSE https://www.apache.org/licenses/LICENSE-2.0.txt
```

Check that it starts with "Apache License" and contains "Version 2.0, January 2004". If the download fails, write the canonical Apache-2.0 text exactly; do not paraphrase.

Do not add a NOTICE file. Third-party media keep their own licences, as listed in each case pack's `source/source.json`. Say so in the README.

## 3. README.md (rewrite top to bottom; keep it ≤ 220 lines)

Read the current README first. Keep its facts; drop the duplication. Required sections, in this order:
1. **Title and one-line pitch:** "Anveshan turns a real demonstration into a skill someone else can learn, practise and get verified feedback on."
2. **Try it:**
   - live URL placeholder `https://<cloud-run-url>` with the note "(added at deployment)";
   - a 4-step path for a first-time visitor:
     1. open the Kolam drawing;
     2. press Start practising and use **Try a sample attempt**, or draw it yourself;
     3. read the feedback and "Why this feedback?";
     4. do your second try and see what changed.
   - Then one line each for:
     - **Share a skill you know** (composer);
     - **My skills**;
     - **Steward console** (footer "Steward sign-in"; access code required).
3. **Three ways to use Anveshan:** learner, creator and steward, with 2 sentences each (from `docs/product/product-vision.md` §9A).
4. **How it works:**
   - the lifecycle CAPTURE → … → EVOLVE;
   - a 5-line description of the evaluation core: goal model from the source → learner attempt → deterministic checks → first place it went off track → targeted feedback → retry → what changed.
   - Link `docs/plans/evaluation-core.md` and `docs/plans/universal-pipeline.md`.
5. **Where Gen AI is used (and where it is not).** A table with the columns Job | Model | Guard:

| Job | Model | Guard |
|---|---|---|
| Perceiving uploads | vision_fast, audio | Recorded runs, explicit failures |
| Embeddings for alignment | embedding | — |
| Answering questions about a skill | from the cited claims | Insufficient-evidence refusal |
| Wording coaching advice | vision_fast | The guard rejects new numbers or verdict words; template fallback |
| Scoring, pass/fail, permissions, insights | **no model** | Deterministic bands and rules |

   Take the model names from `tracks/common/models.py` or `docs/status/project.yaml`.
6. **Evidence (engineering, not user validation):** links to:
   - `docs/validation/experiments.md` (E-series);
   - the test count (run `<py> -m pytest --collect-only -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live" | Select-Object -Last 1` and cite that number with the date);
   - the judges-panel review.
   - State plainly: "No study with real learners or experts has been run yet."
7. **Limits:**
   - recorded vs live mode;
   - single-instance demo storage is temporary (data is kept about 6 hours, published skills until restart);
   - no accounts;
   - internet sources are not verified experts;
   - known weak spots, taken from `docs/plans/universal-pipeline.md` §12.
8. **Run locally:** the commands from `CLAUDE.md` (venv, `pip install -r requirements-dev.txt`, the service, the app dev server, mock mode, `.env` from `.env.example`). Never show a key.
9. **Deploy:** link `docs/deploy/DEPLOY-CHECKLIST.md`.
10. **Repository map:** 8–10 lines (`app/`, `service/`, `tracks/common`, `tracks/track-a`, `tracks/track-b`, `tracks/cases`, `docs/`, `tools/`).
11. **Licence:** "Code: Apache-2.0 (LICENSE). Case media keep their own licences; see each pack's `source/source.json`."
12. **Team and competition:** Google Cloud AI Builder Cup 2026; keep any team text the current README has.

## 4. Judges-panel review status (`docs/research/judges-panel-review-2026-10-07.md`)

- **Do not rewrite the findings.** For each finding J-01…J-21, add one line directly under its heading:

  ```text
  **Status (2026-10-08):** DONE | PARTIAL | OPEN | NEXT, with a short note and a link
  ```

- Base the status on the repo, not on assumptions. Check `git log --oneline` on `main` (the commits ae579b4, 4ee56af and 5e0f151 and the K9 work) and the plan's WS sections.
- **Known statuses** to use; verify each quickly:

| Finding | Status | Evidence |
|---|---|---|
| J-02, J-05, J-07 | DONE | WS1: rate limits, budget, isolation, locks, housekeeping (`service/anveshan_service/{limits,visitors,housekeeping}.py`) |
| J-03 | DONE | `app/src/api/errors.ts` |
| J-06 | DONE | `.github/workflows/checks.yml` docker job |
| J-09, J-10 | DONE | `tracks/track-b/src/track_b/coach.py`, the show-me animation, drills |
| J-14, J-15, J-16 | DONE when K9 merges (plain language, roles); otherwise PARTIAL | — |
| J-11 | DONE when K9-P4 merges (samples) | — |
| J-04 | DONE when K9-P5 merges | — |
| J-01 | DONE (this README) | — |
| J-21 | DONE (LICENSE) | — |
| J-17 | DONE when K9-B2 and K9-B1 merge (stability numbers, evidence page) | — |
| J-12 | PARTIAL | The cache fixes repeat variance; WS6 robustness moved to NEXT |
| J-08 | OPEN | Needs humans: a pilot and an expert review |

  Use "when K9 merges" wording as "DONE (K9)". PC confirms these after the merge.
- Add a short "Status summary" table at the top of the document.

## 5. Experiments (`docs/validation/experiments.md`)

Read the existing format (`grep -n "^## " docs/validation/experiments.md`). Append these two entries in the same format.

**E8: AI coaching wording (validator-guarded).**
- Model `vision_fast`; prompt `tracks/common/prompts/coach_feedback_v1.txt`; code `tracks/track-b/src/track_b/coach.py`.
- **Guard design:**
  - it rewrites `corrective_advice` only;
  - per item, it rejects verdict words (the regex in `coach.py`) and any number not present in that item;
  - after a rejection it falls back to the template per item;
  - then `feedback.guard_wording` runs.
- **Evidence:** the unit tests in `tracks/track-b/tests/test_coach.py` (count them) and the browser walk-through on 2026-10-07 (Kolam baseline: AI-worded advice shown, the fixed-wording toggle works).
- **Limits:** no human rating of the wording quality yet.

**E9: Bring your own key (BYOK) security behaviour.**
- **Code:** `app/src/api/userKey.ts`, `service/anveshan_service/userkey.py`, `routes/key.py`.
- **Behaviour:**
  - the key is stored in sessionStorage, or localStorage only on opt-in;
  - it is sent only as a header and scoped to one request;
  - it is never stored server-side and is redacted in errors;
  - the check uses a metadata call with no generation quota.
- **Evidence:**
  - the tests in `service/tests/test_public_demo.py` (BYOK tests; count them);
  - the browser test on 2026-10-07: a fake key was rejected ("Google rejected this key") and nothing was stored in session or local storage.
- **Limits:** a key lives in browser storage while it is in use; users should restrict and delete demo keys.

## 6. NEXT-STEPS (`docs/plans/NEXT-STEPS.md`)

- Add a dated section "After K9 (2026-10-08)" listing what remains for Jim:
  - register the team (by Oct 11);
  - deploy to Cloud Run with `ANVESHAN_STEWARD_TOKEN` as a secret;
  - run `tools/smoke_deployed.py` against the URL;
  - pilot with 3–5 colleagues and one expert review (WI-5.1, WI-5.2);
  - make the repo public;
  - record the video;
  - deck;
  - submit by Oct 17.
- Remove or mark done any earlier items that K9 completes. Do not delete history; mark it "DONE (K9)".

## 7. Acceptance

- `README.md` has no BOM and no mojibake: `grep -n "â€\|Ã\|Â" README.md` returns nothing.
- `LICENSE` is the Apache-2.0 text.
- Every J-finding has a status line.
- E8 and E9 are appended.
- NEXT-STEPS is updated.
- `check_governance.py` passes.
- Report `docs/kiro/reports/K9-P6-REPORT.md`.
