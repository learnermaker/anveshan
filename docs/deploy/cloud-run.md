# Deploying Anveshan to Google Cloud Run

**Status:** IMPLEMENTED (container + service); deployment is run by a human with project access.

One container serves the FastAPI API (`/api/*`, see `docs/plans/service-api.md` §5) and the built React app (`/`).
The image bakes in the case packs and the licensed case media (`tools/fetch_media.py`, sha256-verified at build time).

## 0. Prerequisites

- `gcloud` CLI authenticated (`gcloud auth login`) with a billing-enabled project.
- **No server API key.** Every live Gemini call uses the visitor's own key, entered in the app and sent per request
  in the `X-Gemini-Api-Key` header (never stored). The service deletes `GEMINI_API_KEY`/`GOOGLE_API_KEY` from its
  environment at startup, so a server key is ignored even if one is set. Samples replay committed runs and need no key.

```bash
export PROJECT_ID=<your-project>
export REGION=asia-south1          # or us-central1
export SERVICE=anveshan
export REPO=anveshan
gcloud config set project $PROJECT_ID
gcloud config set run/region $REGION
```

## 1. Enable APIs and create the image repository (once)

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com

gcloud artifacts repositories create $REPO --repository-format=docker \
  --location=$REGION --description="Anveshan images"
```

## 2. API key: none on the server

Do not create a `gemini-api-key` secret or set `GEMINI_API_KEY` on the service. Visitors add their own key in the
app (key button in the header); it lives only in their browser and in one request at a time
(`service/anveshan_service/userkey.py`). If an old deployment still mounts the secret, remove it:
`gcloud run services update $SERVICE --remove-secrets GEMINI_API_KEY`.

## 3. Build and deploy

### Option A: one command from source (Cloud Build builds the `Dockerfile`)

```bash
gcloud run deploy $SERVICE --source . \
  --allow-unauthenticated \
  --max-instances 1 --min-instances 0 \
  --memory 2Gi --cpu 2 --timeout 300 --concurrency 20 \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --set-env-vars ANVESHAN_MODE=live,ANVESHAN_TEXT_IMAGE_MODEL=gemini-3.5-flash-lite,ANVESHAN_VIDEO_FRAMES_MODEL=gemini-3.5-flash-lite,ANVESHAN_AUDIO_MODEL=gemini-3.5-flash-lite,ANVESHAN_MAX_UPLOAD_MB=30,ANVESHAN_DATA_DIR=/tmp/anveshan
```

### Option B: explicit build, then deploy the image

```bash
IMAGE=$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$SERVICE:$(git rev-parse --short HEAD)
gcloud builds submit --tag $IMAGE --timeout=1800s .
gcloud run deploy $SERVICE --image $IMAGE \
  --allow-unauthenticated --max-instances 1 --memory 2Gi --cpu 2 --timeout 300 --concurrency 20 \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --set-env-vars ANVESHAN_MODE=live,ANVESHAN_TEXT_IMAGE_MODEL=gemini-3.5-flash-lite,ANVESHAN_VIDEO_FRAMES_MODEL=gemini-3.5-flash-lite,ANVESHAN_AUDIO_MODEL=gemini-3.5-flash-lite,ANVESHAN_MAX_UPLOAD_MB=30
```

Local equivalent (needs Docker): `docker build -t anveshan . && docker run --rm -p 8080:8080 anveshan`.

### Settings (env vars; defaults in `.env.example` and the `Dockerfile`)

| Variable | Container default | Notes |
|---|---|---|
| `ANVESHAN_MODE` | `live` | Live mode replays committed recordings first (samples cost nothing) and calls Gemini only for new uploads, with the visitor's own key. Canonical settings: [DEPLOY-CHECKLIST.md](DEPLOY-CHECKLIST.md). |
| `ANVESHAN_TEXT_IMAGE_MODEL`, `ANVESHAN_VIDEO_FRAMES_MODEL` | `gemini-3.5-flash-lite` on Cloud Run | The code default (Gemma 4 26B, ~43 s/image) is for offline builds only. |
| `ANVESHAN_AUDIO_MODEL` | `gemini-3.5-flash-lite` on Cloud Run | Empty disables it and keeps tabla bol criteria UNCERTAIN. |
| `ANVESHAN_CASES_ROOT` | `/app/tracks/cases` | Baked case packs. |
| `ANVESHAN_DATA_DIR` | `/tmp/anveshan` | Uploads, sessions, derived upload cases, ad-hoc live runs. |
| `ANVESHAN_MAX_UPLOAD_MB` | `30` | Per-file limit (413 above it). Keep below Cloud Run's 32 MiB request cap. |
| `ANVESHAN_CORS_ORIGINS` | empty | Not needed in the container (app is same-origin). |
| `ANVESHAN_STATIC_DIR` | `/app/app/dist` | Built React app. |

### Why these flags

- `--max-instances 1`: sessions, uploads and derived cases live on the instance's local disk. More instances would split a
  learner's session across machines. This is a deliberate prototype limit; no database is added for the demo.
- `/tmp` on Cloud Run is in-memory and counts against `--memory`; 2 GiB leaves room for video decoding (PyAV) plus uploads.
  State is lost when the instance is recycled. Use `--min-instances 1` during judging/demo windows to keep sessions warm.
- `--timeout 300`: live video evaluation (frame sampling + Gemma calls) can take tens of seconds.
- **Request size:** Cloud Run rejects HTTP/1 request bodies above 32 MiB before they reach the container. Origami attempt
  videos must therefore be ≤ 30 MB (the app should downscale; a 60 s 480p clip is well under this).
- Track A build/review writes new case versions inside the container (case packs are owned by the `app` user). Those writes
  are ephemeral; durable case versions are committed to the repo.

## 4. Smoke test

```bash
URL=$(gcloud run services describe $SERVICE --format='value(status.url)')
curl -s $URL/api/health
# {"ok":true,"mode":"live", ...}
curl -s $URL/api/cases | head -c 400; echo
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' $URL/api/media/kolam/src.kolam.target.v1      # 200 image/jpeg
curl -s -o /dev/null -w '%{http_code}\n' $URL/api/media/kolam/src.kolam.direction_diagram.v1           # 404 (held out)
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' -H 'Range: bytes=0-1023' $URL/api/media/origami/src.origami.demo.v1  # 206 video/ogg
curl -s -X POST $URL/api/sessions -H 'content-type: application/json' -d '{"case_id":"kolam","learner_name":"smoke"}'
curl -s -o /dev/null -w '%{http_code} %{content_type}\n' $URL/                                          # 200 text/html
gcloud run services logs read $SERVICE --limit 50
```

A route that needs a track not present in the build returns `503 SERVICE_UNAVAILABLE` with the module name.

## 5. Cost notes

- Cloud Run with `--min-instances 0` bills only while serving requests; a demo-scale deployment stays inside the free tier
  (2M requests, 180k vCPU-s, 360k GiB-s per month). `--min-instances 1` with 2 vCPU / 2 GiB costs on the order of a few USD
  per day; turn it on only for judging windows.
- Cloud Build: about 120 free build-minutes per day; one image build is ~5–10 min (npm ci, pip, ~50 MB media download).
- Artifact Registry: ~0.5 GB free storage; delete old image tags (`gcloud artifacts docker images list`).
- Live mode calls gemini-3.5-flash-lite (about $0.0003 per call) only for new uploads, on the visitor's own key; samples replay committed recordings for free.
- Set a budget alert: `gcloud billing budgets create --billing-account=<ID> --display-name=anveshan --budget-amount=20USD`.

## 6. Rollback

```bash
gcloud run revisions list --service $SERVICE
gcloud run services update-traffic $SERVICE --to-revisions <REVISION>=100
```
