# Cloud Run Deployment Guide — GCP Web Console

**Written:** 2026-10-06  
**Audience:** Jim (no local gcloud CLI install)

> **2026-10-08: no server key.** The service never uses a Gemini key of its own; visitors add theirs in the app. Skip every `gemini-api-key` secret step below. Canonical settings: [DEPLOY-CHECKLIST.md](../deploy/DEPLOY-CHECKLIST.md).  
**Source of truth:** `docs/deploy/cloud-run.md` and the repo `Dockerfile`  
**Prerequisite:** a Google account with billing access to the project

Items marked **[VERIFY]** are console field names or menu paths that may shift between GCP console releases; verify visually when you're on screen.

---

## 1. Create or select a project

1. Go to https://console.cloud.google.com.
2. Click the **project selector** (top-left, next to "Google Cloud").
3. Choose an existing project, or click **New Project**:
   - Project name: `Anveshan`
   - Project ID: `anveshan-hack-2026` (append `-<suffix>` if taken; IDs are globally unique)
   - Organisation: leave as "No organisation" for a personal account
   - Click **Create**.
4. Wait for the project to be created, then select it in the dropdown.

## 2. Link billing

1. From the left sidebar, go to **Billing** (or search for "Billing" in the top search bar).
2. If no billing account is linked, click **Link a billing account** and choose your billing account.
3. To verify: **Billing → Overview** should show the account name with a green status.

### 2a. Set a budget alert (recommended, ~USD 15)

1. In **Billing**, click **Budgets & alerts** in the left sub-menu.
2. Click **Create budget**.
3. Name: `anveshan-demo-budget`
4. Projects: select `anveshan-hack-2026`
5. Budget type: **Specified amount**; Amount: `15` USD (or ₹1,000 if billing in INR)
6. Alert thresholds: leave the defaults (50%, 90%, 100%)
7. Click **Finish**.

## 3. Enable required APIs

1. In the top search bar, type **"APIs & Services"** and click **APIs & Services → Library**.
2. Search for and **enable** each of these four APIs (click the result, then click **Enable**):
   - `Cloud Run Admin API`
   - `Artifact Registry API`
   - `Cloud Build API`
   - `Secret Manager API`
3. Wait for each to show **Enabled** before moving on.

## 4. Create an Artifact Registry repository (one-time)

1. Search for **"Artifact Registry"** in the top bar and open it.
2. Click **Create Repository**.
3. Fill in:
   - Name: `anveshan`
   - Format: **Docker**
   - Mode: **Standard**
   - Location type: **Region**
   - Region: **`asia-south1` (Mumbai)** [VERIFY — ensure this matches the dropdown label]
   - Description: `Anveshan images`
4. Click **Create**.

## 5. Store the Gemini API key in Secret Manager

**Security rule:** never paste the key into an env-var field directly on the Cloud Run service page. Always use Secret Manager, then reference it by name. This keeps the key out of revision configs and audit logs.

1. Search for **"Secret Manager"** and open it.
2. Click **Create Secret**.
3. Fill in:
   - Name: `gemini-api-key`
   - Secret value: paste your AI Studio key (`GEMINI_API_KEY` value from `.env`) directly into the **Secret value** text area. **Do not add trailing whitespace or newlines.**
   - Replication policy: **Automatic**
4. Click **Create Secret**.
5. You should see the secret listed with version `1` (Active).

## 6. Deploying from source

### Option A — Continuous deployment from GitHub (recommended)

This connects Cloud Run to GitHub via Cloud Build. Every push to the configured branch triggers a new build and deploy. It is the most hands-off path for the hackathon.

**Why recommended over Cloud Shell:** it uses the repo's own `Dockerfile` directly, records each deploy as a Build History entry you can audit, and enables one-click rollback to any prior image.

**Steps:**
1. In the top search bar, go to **Cloud Run**.
2. Click **Create Service**.
3. Choose **"Continuously deploy from a repository"** [VERIFY — label may say "Deploy from a repository (with Continuous Deployment)"].
4. Click **Set up with Cloud Build**.
5. Under "Repository provider", choose **GitHub**.
6. Authorise GCP to access your GitHub if prompted (this installs the Cloud Build GitHub App on `learnermaker/anveshan`).
7. Select repository: **`learnermaker/anveshan`**.
8. Branch: **`^main$`** (regex; deploys on every push to `main`). See §6c for the current branch situation.
9. Build type: **Dockerfile**.
10. Dockerfile location: `/Dockerfile` (root of the repo — this is the default).
11. Click **Save** and return to the service configuration page.

### Option B — Cloud Shell `gcloud run deploy --source .` (fallback)

Use this if the GitHub App install is blocked or the continuous-deploy option is unavailable.

1. Click the **Cloud Shell** icon (top-right of the console, looks like `>_`).
2. In the shell, clone or navigate to the repo:
   ```bash
   git clone https://github.com/learnermaker/anveshan.git && cd anveshan
   ```
   Or if you've already cloned: `cd anveshan && git pull`.
3. Run the deploy command (all settings match `docs/deploy/cloud-run.md`):
   ```bash
   gcloud run deploy anveshan \
     --source . \
     --region asia-south1 \
     --allow-unauthenticated \
     --max-instances 1 --min-instances 0 \
     --memory 2Gi --cpu 2 --timeout 300 --concurrency 20 \
     --set-env-vars ANVESHAN_MODE=live,ANVESHAN_TEXT_IMAGE_MODEL=gemini-3.5-flash-lite,ANVESHAN_VIDEO_FRAMES_MODEL=gemini-3.5-flash-lite,ANVESHAN_AUDIO_MODEL=gemini-3.5-flash-lite,ANVESHAN_MAX_UPLOAD_MB=30,ANVESHAN_DATA_DIR=/tmp/anveshan
   ```
4. Cloud Shell has gcloud pre-installed and already authenticated to your GCP account.
5. Build time is approximately 5–15 minutes (npm ci + pip install + ~50 MB media fetch).

**Note:** Cloud Shell sessions time out after ~20 minutes of inactivity. If the build takes longer, the session may disconnect, though the build continues in Cloud Build. Check progress under **Cloud Build → History**.

### 6c. Which branch to deploy

- Default: **`main`** — this is the canonical integrated state per `AGENTS.md`.
- During the hackathon build: agent work lives on `m1/hero-cases` and other feature branches. Until those are merged into `main`, deploying `main` gives you the last stable integrated build, which may lag behind current agent work.
- To deploy the current working branch (`m1/hero-cases`) temporarily: change the regex to `^m1/hero-cases$` in the Cloud Build trigger, or run Option B pointing at that branch.
- **Do not deploy directly from a feature branch for the final submission.** Merge to `main` first.

## 7. Service settings

After the repository is linked (Option A) or directly when configuring the service (Option B via console), set these values in the **Cloud Run → Edit & Deploy New Revision** panel:

### Container, Networking, Security tab

| Setting | Value | Notes |
|---|---|---|
| Region | `asia-south1` | Mumbai; matches `docs/deploy/cloud-run.md` |
| CPU | `2` | Required for PyAV video decode and numpy inference |
| Memory | `2 GiB` | `/tmp` is in-memory; 2 GiB covers media + model response buffers |
| Request timeout | `300` seconds | Live video evaluation can take 30–60 s |
| Maximum instances | `1` | Sessions and uploads live on-disk; multiple instances would split state |
| Minimum instances | `0` (default); `1` during demo window | Min 1 keeps sessions warm during live demo; costs ~USD 1–3/day with 2 CPU/2 GiB |
| Concurrency | `20` | [VERIFY — field label may be "Maximum concurrent requests per instance"] |
| Container port | `8080` | The `Dockerfile` listens on `$PORT` which defaults to 8080 |
| Authentication | **Allow unauthenticated invocations** | Required so judges can access without GCP credentials |

### Environment variables

Click **+ Add variable** for each row (under "Container → Variables & Secrets" or "Environment variables" tab [VERIFY]):

| Name | Value |
|---|---|
| `ANVESHAN_MODE` | `live` |
| `ANVESHAN_TEXT_IMAGE_MODEL` | `gemini-3.5-flash-lite` |
| `ANVESHAN_VIDEO_FRAMES_MODEL` | `gemini-3.5-flash-lite` |
| `ANVESHAN_AUDIO_MODEL` | `gemini-3.5-flash-lite` |
| `ANVESHAN_MAX_UPLOAD_MB` | `30` |
| `ANVESHAN_DATA_DIR` | `/tmp/anveshan` |

### Mount the API key from Secret Manager

1. On the same tab, look for **"Secrets"** or **"Referenced secrets"** [VERIFY].
2. Click **+ Reference a secret**.
3. Secret: select `gemini-api-key`.
4. Reference method: **Environment variable**.
5. Environment variable name: `GEMINI_API_KEY`.
6. Version: **latest**.
7. Click **Done**.

### Grant the service account permission to read the secret (one-time)

Cloud Run uses the Compute Engine default service account unless you assign a custom one. Its email is `<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`.

To find your project number: **Home → Dashboard** → look for "Project number" in the Project info card.

1. Open **Secret Manager → gemini-api-key → Permissions** tab.
2. Click **Grant Access**.
3. In "New principals", paste: `<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`
4. Role: **Secret Manager Secret Accessor** (`roles/secretmanager.secretAccessor`)
5. Click **Save**.

**[VERIFY]** The above assumes the Compute Engine default SA is used. If you configure a custom service account for the Cloud Run service, grant the same role to that SA instead.

## 8. Smoke test

After the service is deployed, Cloud Run shows a **Service URL** (e.g. `https://anveshan-xxxx-el.a.run.app`).

Open these URLs in your browser:

| URL | Expected response |
|---|---|
| `<SERVICE_URL>/api/health` | `{"ok":true,"mode":"live",...}` |
| `<SERVICE_URL>/api/cases` | JSON array of case objects |
| `<SERVICE_URL>/` | The React app (should load the Anveshan UI) |

From Cloud Shell (or any terminal):
```bash
curl -s <SERVICE_URL>/api/health | python3 -m json.tool
curl -s <SERVICE_URL>/api/cases | python3 -m json.tool | head -40
```

If `/api/health` returns `503 SERVICE_UNAVAILABLE`, check the service logs (§9) for a missing module — a track not present in the build will produce this error with a module name.

## 9. View logs and roll back

### Logs

1. Go to **Cloud Run → anveshan service**.
2. Click the **Logs** tab.
3. Filter by severity (Error, Warning) to find startup failures.
4. Alternatively, go to **Logging → Logs Explorer** [VERIFY] and filter by `resource.type="cloud_run_revision"`.

### Roll back to a previous revision

1. In the Cloud Run service page, click the **Revisions** tab.
2. You'll see a list of numbered revisions with their deploy timestamps.
3. Click the three-dot menu on the revision you want to restore and choose **Manage Traffic** [VERIFY — exact label may differ].
4. Set traffic weight to `100%` for the target revision and `0%` for the current one.
5. Click **Save**.

This is instant — no redeploy needed.

## 10. Cost notes

- **Gemma 4 on AI Studio is free** (rate-limited); the container uses it via the `GEMINI_API_KEY` env var. `ANVESHAN_AUDIO_MODEL` is intentionally left empty (paid; disabling it keeps tabla bol criteria as UNCERTAIN but avoids charges).
- **Cloud Run with min-instances 0:** bills only while serving requests. At hackathon demo scale (< 1,000 requests/month), this typically stays well within the free tier (2M requests, 180k vCPU-seconds, 360k GiB-seconds per month).
- **Min-instances 1 during demo/judging window:** 2 vCPU / 2 GiB costs roughly USD 1–3 per day. Turn it on only for the judging window (Oct 19 – Nov 6) and the finale (Dec 4). Turn it off otherwise.
- **Cloud Build:** approximately 120 free build-minutes per day; one Anveshan build takes 5–15 minutes.
- **Artifact Registry:** ~0.5 GB free storage; clean up old image tags after successful deploys.
- **Budget alert** (§2a) will email you if spend approaches USD 15.

## Appendix: `Dockerfile` summary

The build has two stages:
1. **app-build** (`node:22-slim`): runs `npm ci && npm run build` to produce the React app in `/src/app/dist`.
2. **runtime** (`python:3.13-slim`): installs `service/requirements.txt`, copies tracks/tools/service/built-app, then runs `python tools/fetch_media.py` as the `app` user to bake licensed case media (~50 MB) into the image. The container listens on `$PORT` (default 8080) via uvicorn.

Build failures most commonly occur in the media-fetch step if a Wikimedia file hash has changed. If Cloud Build fails there, check `tools/fetch_media.py` for a hash mismatch error.
