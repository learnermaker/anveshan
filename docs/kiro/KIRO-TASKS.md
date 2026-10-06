# Kiro Task Sheet: Parallel Support Work (v2, 2026-10-06)

You are helping Jim on the **Anveshan** hackathon project (Google Cloud AI Builder Cup 2026; submission deadline **2026-10-18**). Claude Code is the main developer and is running several coding agents on the code in this same folder. Your job is **research and documentation support** that unblocks them. Do it exactly as written.

Repository folder: `C:\Users\JIMSEELAN\Desktop\Projects\hackathons\anveshan` (shared with Claude Code; Windows).

**Changes since v1:** these are dropped — GitHub CLI (Jim uses GitHub Desktop), the model smoke test (Claude Code already ran it), gcloud CLI install, and submission drafts. If you already started any of them, stop and do not continue.

---

## 0. Hard rules

1. **Do not modify any existing file** in the repo. You may **create or edit only**:
   - files under `docs/kiro/` (except this task sheet);
   - files under `var/kiro/` (gitignored scratch space).
2. **Do not run any git command that changes state** (no commit, push, merge, checkout, stash, reset, worktree). Claude Code is merging code in this folder. Read-only commands such as `git status` and `git log` are fine.
3. **Do not read or print `.env`.** It holds an API key.
4. Do not touch `.claude/`, `app/`, `service/`, `tracks/`, `tools/`, `.github/`.
5. Do not deploy anything and do not create cloud resources.
6. If a step needs Jim, ask him clearly. Don't guess.
7. On this machine `curl` needs `--ssl-no-revoke` because the corporate network blocks certificate-revocation checks.
8. Record everything in **`docs/kiro/REPORT.md`** (template in §5). When finished, tell Jim: **"Kiro tasks complete — see docs/kiro/REPORT.md"**.

---

## Task 1: Licensed test media (priority: HIGHEST)

Goal: find inputs for testing the three live cases. Research and download only; do **not** add anything to `tracks/`.

Allowed licences: public domain, CC0, CC BY, CC BY-SA. **Not allowed:** NC/ND, "all rights reserved", YouTube downloads, stock sites, AI-generated media.

Where to look: Wikimedia Commons (read the licence on each file page), Internet Archive (only items with an explicit CC/PD licence), and Openverse (https://openverse.org; filter for commercial use and modification allowed).

### 1a. Origami: an independent learner video (MOST IMPORTANT)
The current "learner" video `Crane.ogv` turned out to be the same performance as the expert video `OrigamiCrane.ogv`, just re-encoded. We need **1–3 genuinely different recordings** of someone folding a **traditional paper crane** (at least up to the bird base): a different person or session, ideally under 5 minutes, with hands and paper visible. Imperfect folding is a bonus, because we want real mistakes. Videos of other simple models (paper cup, fortune teller, boat) are a fallback; list them separately.

### 1b. Tabla: a steady rhythm cycle (theka)
Find **2–4 clips** of clear tabla playing, preferably a **slow, steady theka** (Teentaal, Keherwa or Dadra) with audible bayan (bass) strokes. Short clips (10–60 s) are fine. The current source, Wikimedia `Tabla drums demo.oga`, is fast and varied, so a steadier clip would improve the case. If you find two recordings of the **same theka** by different players, that pair is especially valuable: one becomes the goal, the other a learner attempt.

### 1c. Kolam: extra finished images (5–8)
Find clean images of **finished kolams**, preferably high contrast and dot-based (pulli or sikku), top-down with little perspective. Include 2 photos of real floor kolams as harder cases. The author "Mayooranathan" on Wikimedia has public-domain diagram-style kolams; that set is already partly used (Ithayakkamalam), so list others from them too.

For each item:
1. Download it into `var/kiro/media/<origami|tabla|kolam>/`. Wikimedia rate-limits: wait ≥ 15 s between downloads and use the User-Agent `AnveshanHackathon/0.1 (research prototype)`.
2. Compute its SHA-256 in PowerShell: `Get-FileHash <file> -Algorithm SHA256`.
3. Add a row to **`docs/kiro/media-candidates.md`**:

| Category | Title | File page URL | Direct URL | Licence (exact) | Author/attribution | Size (bytes) | Duration/dimensions | SHA-256 | Local path | Why it's useful | Concerns |
|---|---|---|---|---|---|---|---|---|---|---|---|

Mark the single best candidate per category with ⭐. Note any file that might be the same performance as another (same uploader, same length).

## Task 2: Cloud Run deployment guide for the GCP **web console** (priority: HIGH)

Jim cannot install gcloud and will deploy through the browser console. Read `docs/deploy/cloud-run.md` (written for gcloud; do not edit it) and the `Dockerfile` (read only). Write **`docs/kiro/cloud-run-console-guide.md`**: a click-by-click guide that uses only https://console.cloud.google.com (and Cloud Shell in the browser if unavoidable; say so explicitly where it is). Cover:

1. Create or select a project; link billing; set a budget alert of about USD 15.
2. Enable APIs: Cloud Run Admin, Artifact Registry, Cloud Build, Secret Manager.
3. Secret Manager: create the secret `gemini-api-key`, pasting the value manually in the console.
4. Deploying from source. Compare these options and recommend one, explaining why:
   - (a) Cloud Run → "Deploy container" → "Continuously deploy from a repository" (connects GitHub `learnermaker/anveshan` through Cloud Build, using the repo's `Dockerfile`);
   - (b) Cloud Shell `gcloud run deploy --source .`.
5. Service settings, taken from `docs/deploy/cloud-run.md`:
   - region `asia-south1`;
   - `--max-instances 1`, memory 2 GiB, 2 CPU, request timeout 300 s, port 8080;
   - allow unauthenticated access (for judges);
   - environment variables (the table in that doc);
   - secret `gemini-api-key` mounted as env var `GEMINI_API_KEY`;
   - granting the service account Secret Accessor.
6. Which branch to deploy. Default `main`, but note that work currently lives on `m1/hero-cases` until it is merged.
7. Smoke test from a browser: `/api/health`, `/api/cases`, then the app at `/`.
8. Where to read logs (Cloud Run → Logs) and how to roll back (Revisions tab).
9. Cost notes: Gemma is free on AI Studio; Cloud Run min instances 0.
Include the exact console menu paths and field names. Mark anything you are unsure of with **[VERIFY]**.

## Task 3: Official competition rules snapshot (priority: MEDIUM)

1. Open https://aibuildercup.com/ and https://aibuildercup.com/themes.html, plus any rules, FAQ or submission pages they link to.
2. Write **`docs/kiro/official-rules-2026-10-06.md`** with:
   - the retrieval date/time and URLs;
   - the **exact** text of the "Sustainability & Social Impact" theme, plus one-line summaries of the others;
   - submission requirements, verbatim where short: deliverables (deck format, video length and hosting, repo/docs, deployment proof), required Google technologies, Cloud Run/Firebase requirement, language, team rules;
   - the deadline with its **time zone**, plus the evaluation and finalist dates;
   - judging criteria and weights;
   - an explicit list of anything that **differs** from `docs/hackathon/ai-builder-cup.md` (read that file; do not edit it);
   - the submission portal URL and the fields it asks for, if there is one.

---

## 5. Report template: `docs/kiro/REPORT.md`

```markdown
# Kiro Report — <date/time>

## Summary
- Task 1 Media: DONE (n origami, n tabla, n kolam) / BLOCKED (reason)
- Task 2 Console guide: DONE / BLOCKED
- Task 3 Official rules: DONE / BLOCKED

## 1. Media candidates
Link to docs/kiro/media-candidates.md. Best picks: origami ⭐…, tabla ⭐…, kolam ⭐…

## 2. Console deployment guide
Link + recommended deploy option + open [VERIFY] items

## 3. Official rules
Link + top differences from our docs

## Problems / questions for Claude Code
- ...
```
