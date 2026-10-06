# Kiro Task Sheet: Parallel Support Work (2026-10-06)

You are helping Jim on the **Anveshan** hackathon project (Google Cloud AI Builder Cup 2026; submission deadline **2026-10-18**). Claude Code is the main developer and has **seven coding agents working in parallel** on the code. Your job is the **environment, cloud, verification and research work** that unblocks them. Do it exactly as written.

Repository: `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan`. The current branch is `m1/hero-cases`; do not switch branches.

---

## 0. Hard rules (read before anything else)

1. **Do not modify any existing file** in the repo. You may **create or edit only**:
   - `.env` (gitignored; never commit it);
   - files under `docs/kiro/`;
   - files under `var/kiro/` (gitignored scratch space).
2. **Do not run** `git commit`, `git push`, `git merge`, `git checkout`, `git stash`, `git reset`, `git worktree`, or anything that changes git state. Claude Code is merging agent work into this checkout. Read-only git commands (`git status`, `git log`) are fine.
3. **Never print, log, echo or write the Gemini API key** anywhere except inside `.env` and Google Secret Manager. Do not paste it into reports.
4. Do not touch `.claude/worktrees/`, `app/`, `service/`, `tracks/`, `tools/` (except **running** `tools/check_models.py` and `tools/fetch_media.py`), or `.github/`.
5. Do not deploy anything to Cloud Run. Deployment happens later, once the Dockerfile lands.
6. If a step needs Jim (logins, billing, pasting the key), stop and ask him clearly. Don't guess.
7. Shell: Windows. Use PowerShell or Git Bash. On this machine `curl` needs `--ssl-no-revoke` because the corporate network blocks certificate-revocation checks.
8. Record everything in **`docs/kiro/REPORT.md`** using the template in §7. Jim will tell Claude Code when you're done.

---

## Task 1 — GitHub CLI (priority: HIGH)

Goal: Claude Code can open and merge PRs.

1. `winget install --id GitHub.cli -e` (if it's already installed, run `gh --version` and skip).
2. Ask Jim to run `gh auth login` **himself** (GitHub.com → HTTPS → browser login). The account must have push access to `learnermaker/anveshan`.
3. Verify (read-only):
   - `gh auth status`
   - `gh repo view learnermaker/anveshan --json name,visibility,defaultBranchRef`
   - `gh pr list --repo learnermaker/anveshan --state open`
4. Record the outputs (no tokens) in REPORT §1.

## Task 2 — Gemini key in `.env` and model smoke test (priority: HIGH)

Goal: confirm what the free Gemma 4 model actually supports with Jim's AI Studio key. Several design decisions depend on this.

1. If `.env` does not exist: `Copy-Item .env.example .env`. Do not alter `.env.example`.
2. Ask Jim to paste his AI Studio key into `.env` as `GEMINI_API_KEY=...`. Leave the other values at their defaults. `ANVESHAN_AUDIO_MODEL` stays **empty** unless Jim explicitly wants paid audio.
3. Run, from the repo root:
   ```powershell
   .\.venv\Scripts\python tools\check_models.py
   ```
4. It writes `var/model_check.json`. Copy into REPORT §2, per check (1–7):
   - PASS or FAIL, plus the latency;
   - for check 1: the list of visible model ids that contain `gemma`;
   - for check 2: did JSON mode (`response_mime_type`) work with Gemma? Quote any error message, but **remove anything that looks like a key**;
   - for checks 4 and 5: the parsed outputs (approximate dot count, symmetry order, rotation guesses). This tells us whether Gemma's image understanding is usable.
5. If check 2 fails but check 3 passes, that is fine: the gateway falls back automatically. Note it.
6. If every check fails with an auth or permission error, ask Jim to confirm the key comes from https://aistudio.google.com/apikey and that the Gemini API is enabled for it, then re-run.
7. Also run `.\.venv\Scripts\python tools\fetch_media.py` and record whether every case reports `ok`/`fetched`. The Tabla case may not have a source yet; that is expected.

## Task 3 — Google Cloud project for Cloud Run (priority: HIGH)

Goal: a project that is ready to deploy. **Do not deploy.**

1. Install the gcloud CLI if missing: `winget install --id Google.CloudSDK -e`, then open a new terminal and run `gcloud --version`.
2. Ask Jim to run `gcloud auth login` himself.
3. Ask Jim which project to use. If none exists yet, propose `anveshan-hack-2026` (append a short suffix if the name is taken) and run `gcloud projects create <PROJECT_ID> --name="Anveshan"`.
4. `gcloud config set project <PROJECT_ID>`
5. **Billing:** ask Jim to link a billing account in the console (https://console.cloud.google.com/billing/linkedaccount?project=<PROJECT_ID>). Cloud Run requires it. Then verify with `gcloud billing projects describe <PROJECT_ID>` (`billingEnabled: true`).
6. Enable the APIs:
   ```bash
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com
   ```
7. Region: use **`asia-south1`** (Mumbai) unless Jim says otherwise.
   ```bash
   gcloud config set run/region asia-south1
   gcloud artifacts repositories create anveshan --repository-format=docker --location=asia-south1 --description="Anveshan images"
   ```
8. Store the Gemini key in Secret Manager **without printing it** (PowerShell, from the repo root):
   ```powershell
   $k = (Select-String -Path .env -Pattern '^GEMINI_API_KEY=(.*)$').Matches[0].Groups[1].Value.Trim()
   $tmp = New-TemporaryFile; Set-Content -Path $tmp -Value $k -NoNewline
   gcloud secrets create gemini-api-key --replication-policy=automatic --data-file=$tmp
   Remove-Item $tmp; Remove-Variable k
   ```
   If the secret already exists, use `gcloud secrets versions add gemini-api-key --data-file=$tmp` instead.
9. Let Cloud Run's default service account read the secret:
   ```bash
   gcloud projects describe <PROJECT_ID> --format="value(projectNumber)"
   gcloud secrets add-iam-policy-binding gemini-api-key --member="serviceAccount:<PROJECT_NUMBER>-compute@developer.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
   ```
10. Recommended: ask Jim to create a small **budget alert** (for example ₹1,000 or USD 15) under Billing → Budgets & alerts.
11. Record in REPORT §3: the project ID, project number, region, enabled APIs (`gcloud services list --enabled --format="value(config.name)"`), the Artifact Registry repo, that the secret exists (`gcloud secrets describe gemini-api-key --format="value(name)"`; the name only, never the value), billing status, and whether a budget alert was created.

## Task 4 — Official competition rules snapshot (priority: MEDIUM)

Goal: an exact, dated copy of what judges require. Our plan uses the theme **"Sustainability & Social Impact"**.

1. Open https://aibuildercup.com/ and https://aibuildercup.com/themes.html, plus any rules, FAQ or submission pages linked from them.
2. Create **`docs/kiro/official-rules-2026-10-06.md`** containing:
   - the retrieval date/time and URLs;
   - the **exact** text of the Sustainability & Social Impact theme (quote it), plus one-line summaries of the other themes;
   - submission requirements, verbatim where they are short: deliverables (deck format, video length/hosting, repo/documentation, deployment proof), required Google technologies, Cloud Run/Firebase requirement, English language, team rules;
   - the deadline with its **time zone**, plus the evaluation and finalist dates;
   - judging criteria and weights;
   - anything that **differs** from `docs/hackathon/ai-builder-cup.md` (read that file; do not edit it). List the differences explicitly.
3. If a submission portal exists (Devpost, Google Form or similar), record its URL and the fields it asks for.

## Task 5 — Extra licensed test media (priority: MEDIUM)

Goal: more **upload-test inputs**, so the "upload your own source / attempt" flows can be tested beyond the built-in cases. Research and download only; **do not add anything to `tracks/`**.

Allowed licences: public domain, CC0, CC BY, CC BY-SA. **Not allowed:** NC/ND, "all rights reserved", YouTube downloads, stock sites.

Sources: Wikimedia Commons (via its API or file pages; read the licence on each file page), Internet Archive (only items with an explicit CC/PD licence), Openverse (https://openverse.org; filter commercial use + modification allowed).

Find:
- **Kolam images (5–8):** clean images of finished kolams, preferably high contrast and dot-based (pulli/sikku), top-down, little perspective. Include 2 photos of real floor kolams as harder cases.
- **Origami videos (2–4):** someone folding a crane or another simple model, top-down or front view, ideally under 3 minutes. Exclude AI-generated videos. `OrigamiCrane.ogv` and `Crane.ogv` are already in use, so skip them.
- **Tabla / percussion audio (3–5):** clear tabla playing, preferably a slow steady rhythm cycle (theka). Short clips are fine. Also 1–2 recordings of tabla bols spoken or recited, if any exist with an allowed licence.

For each item:
1. Download it into `var/kiro/media/<category>/` (Wikimedia rate-limits: wait ≥ 15 s between downloads and use a User-Agent like `AnveshanHackathon/0.1 (research prototype)`).
2. Compute its SHA-256: `Get-FileHash <file> -Algorithm SHA256`.
3. Add a row to **`docs/kiro/media-candidates.md`**:

| Category | Title | File page URL | Direct URL | Licence (exact) | Author/attribution | Size (bytes) | Duration/dimensions | SHA-256 | Local path | Why it's useful | Concerns |
|---|---|---|---|---|---|---|---|---|---|---|---|

Mark the single best candidate per category with ⭐.

## Task 6 — Submission drafts (priority: LOW, only after Tasks 1–5)

Create drafts (Claude Code will revise them against the real build):

1. **`docs/kiro/demo-video-script-draft.md`:** a 3-minute public demo video script, organised as timestamped scenes with on-screen action and narration. Base it on `docs/plans/evaluation-core.md`, `docs/plans/track-plan-review-2026-10-06.md` §9, and `docs/hackathon/demo-story.md`. The story is "the same engine across image (Kolam), video (Origami) and audio (Tabla)". The hero moment is the **progress-to-goal curve plus the first divergence plus the targeted improvement on retry**. Be honest: sources are licensed internet references, synthetic attempts are labelled SYNTHETIC, and there are no claims of certification or validated learning.
2. **`docs/kiro/deck-outline-draft.md`:** a 10–12 slide outline. For each slide give the title, 3 bullets, and the visual to use. Map the slides to the judging criteria (40% technical / 25% impact / 25% innovation / 10% UX).
3. **`docs/kiro/judge-qa-draft.md`:** the 12 hardest judge questions with concise, honest answers. Use `docs/hackathon/judge-qa.md` and `docs/product/novelty-boundary.md` as inputs; do not edit them.

---

## 7. Report template: `docs/kiro/REPORT.md`

```markdown
# Kiro Report — <date/time>

## Summary
- Task 1 GitHub CLI: DONE / BLOCKED (reason)
- Task 2 Gemini key + smoke test: DONE / BLOCKED
- Task 3 GCP project: DONE / BLOCKED
- Task 4 Official rules: DONE / BLOCKED
- Task 5 Media candidates: DONE (n kolam, n origami, n tabla) / BLOCKED
- Task 6 Drafts: DONE / SKIPPED

## 1. GitHub CLI
(gh --version, gh auth status summary, repo view output, open PRs)

## 2. Model smoke test
| Check | Status | Latency | Key output / error |
|---|---|---|---|
(rows 1–7)
Visible gemma model ids: ...
JSON mode works with Gemma: yes/no (error text)
fetch_media.py result: ...

## 3. Google Cloud
Project ID / number / region / APIs / Artifact Registry repo / secret name / billing / budget alert

## 4. Official rules
Link to docs/kiro/official-rules-2026-10-06.md + top 5 differences from our docs

## 5. Media candidates
Link to docs/kiro/media-candidates.md + best picks

## 6. Drafts
Links

## Problems / questions for Claude Code
- ...
```

When everything you can do is finished, tell Jim: **"Kiro tasks complete — see docs/kiro/REPORT.md"**.
