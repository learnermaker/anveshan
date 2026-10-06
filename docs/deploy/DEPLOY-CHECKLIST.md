# Anveshan — Cloud Run Deploy Checklist

**Date:** 2026-10-06  
**Audience:** Jim (manual deployment via GCP web console)  
**Reference:** `docs/kiro/cloud-run-console-guide.md` for step-by-step console instructions  
**Deployment branch:** `m1/hero-cases`  
**Note:** Do NOT deploy `main` until the PR is reviewed and merged.

---

## Pre-deploy verification (run locally on the branch)

```powershell
# 1. Tests green (all non-live)
& ".venv\Scripts\python.exe" -m pytest -q tracks/common/tests tracks/track-a/tests tracks/track-b/tests service/tests -m "not live"
# Expected: ~423 passed

# 2. Governance checks
& ".venv\Scripts\python.exe" .github/scripts/check_governance.py
& ".venv\Scripts\python.exe" .github/scripts/check_case_packs.py
& ".venv\Scripts\python.exe" .github/scripts/check_contract_parity.py

# 3. Frontend build
npm --prefix app run build
# Expected: no errors, dist/index.html created
```

---

## Cloud Run service settings

| Setting | Value |
|---|---|
| **Service name** | `anveshan` |
| **Region** | `us-central1` (or nearest to demo audience) |
| **Container image** | built from `Dockerfile` in repo root |
| **Port** | `8080` (set by `PORT` env var in container) |
| **Memory** | **2 GiB** (required: av PyAV + numpy + PIL + Flash-Lite audio buffer) |
| **CPU** | 2 vCPU |
| **Min instances** | 0 (scale to zero between demos) |
| **Max instances** | **1** (prevents concurrent mutation of case packs in /tmp) |
| **Request timeout** | **300 s** (long origami goal builds with 25+ model calls) |
| **Concurrency** | 1 per instance (case-pack writes are not concurrent-safe) |
| **Execution environment** | 2nd gen |

---

## Secret: `gemini-api-key`

1. In Secret Manager, create a secret named **`gemini-api-key`** containing only your Gemini API key (no spaces or newlines).
2. In the Cloud Run service definition, mount this secret as an environment variable:
   - Environment variable name: `GEMINI_API_KEY`
   - Secret: `gemini-api-key`, version: `latest`
3. Grant the Cloud Run service account the `Secret Manager Secret Accessor` role on this secret.

**Never set the API key as a plain environment variable or embed it in the Dockerfile.**

---

## Environment variables (set in Cloud Run service)

Set these as plain (non-secret) environment variables in the Cloud Run console:

| Variable | Value | Notes |
|---|---|---|
| `ANVESHAN_MODE` | `live` | Set to `recorded` first to test without API calls |
| `ANVESHAN_CASES_ROOT` | `/app/tracks/cases` | Baked into image |
| `ANVESHAN_DATA_DIR` | `/tmp/anveshan` | Ephemeral; reset on cold start |
| `ANVESHAN_MAX_UPLOAD_MB` | `30` | Limit learner uploads |
| `ANVESHAN_STATIC_DIR` | `/app/app/dist` | Serves the React SPA |
| `ANVESHAN_CORS_ORIGINS` | `https://<your-cloud-run-url>` | Add localhost for dev testing |
| `ANVESHAN_MODEL_TIMEOUT_MS` | `300000` | 5 min max per model call |
| `ANVESHAN_VISION_FAST_MODEL` | `gemini-3.5-flash-lite` | Perceive + judge |
| `ANVESHAN_EMBEDDING_MODEL` | `gemini-embedding-2` | Similarity + relevance |
| `ANVESHAN_AUDIO_MODEL` | `gemini-3.5-flash-lite` | Tabla bol labels (INFERRED) |
| `ANVESHAN_TEXT_IMAGE_MODEL` | `gemini-3.5-flash-lite` | Wording/propose model |
| `ANVESHAN_VIDEO_FRAMES_MODEL` | `gemini-3.5-flash-lite` | Origami goal build |
| `ANVESHAN_MODEL_TIMEOUT_MS` | `300000` | Already listed above |

---

## Build notes

### fetch_media.py at build time

The `Dockerfile` calls `python tools/fetch_media.py` during the build. This downloads
CC-licensed media (~50 MB total) from Wikimedia. The script verifies SHA-256 of each file.

**If the build fails with HTTP 429 (Wikimedia rate limit):**
1. Retry the build once after 5 minutes.
2. If it fails repeatedly, contact the Hackathon team or host the media on a GCS bucket
   and update `tools/fetch_media.py` to fetch from there instead.
3. Never commit media files to git.

### Python deps in image

The container installs `service/requirements.txt` which pins:
- `numpy==2.5.3` (audio DSP, kolam geometry)
- `pillow==12.3.0` (image processing)
- `av==19.0.1` (PyAV: audio/video decode)
- `google-genai==2.28.0` (Gemini API)
- `fastapi==0.142.2` + `uvicorn==0.54.0` (service)

---

## Post-deploy smoke test

After deploying, replace `<URL>` with your Cloud Run service URL:

```bash
# Health check
curl https://<URL>/api/health

# List cases (should return kolam, tabla, origami + showcase cases)
curl https://<URL>/api/cases

# Kolam case (should have goal present)
curl https://<URL>/api/cases/kolam | python -c "import sys,json; d=json.load(sys.stdin); print('goal:', bool(d.get('goal')))"

# Run the full HTTP smoke test
python tools/e2e_smoke.py --base-url https://<URL> --mode recorded
```

If `e2e_smoke.py` passes in `recorded` mode, switch `ANVESHAN_MODE` to `live` and rerun:

```bash
python tools/e2e_smoke.py --base-url https://<URL> --mode live
```

The live mode will make ~10 Flash-Lite calls (< $0.005 total).

---

## Expected costs (demo day, ~50 sessions)

| Item | Rate | Estimate |
|---|---|---|
| Cloud Run compute (2 GiB, 2 vCPU, ~5 min/session) | ~$0.0002/vCPU-sec | < $5 |
| Flash-Lite vision calls (~5/session) | ~$0.0003/call | < $0.08 |
| Embedding calls (~3/session) | ~$0.00001/call | < $0.002 |
| Flash-Lite audio calls (~1/session, tabla only) | ~$0.0003/call | < $0.02 |
| **Total** | | **< $5.10** |

---

## Rollback

Cloud Run keeps the previous revision. To roll back:
1. Go to Cloud Run → Anveshan → Revisions.
2. Select the previous revision.
3. Click **Manage Traffic** and route 100% to the previous revision.
