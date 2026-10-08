# Anveshan: one container for Cloud Run = FastAPI service + built React app + case packs.
# Build:  docker build -t anveshan .        Run: docker run -p 8080:8080 -e GEMINI_API_KEY=... anveshan
# See docs/deploy/cloud-run.md.

# ---------------------------------------------------------------------------
# Stage 1: build the React app (served same-origin, so VITE_API_BASE is empty)
# ---------------------------------------------------------------------------
FROM node:22-slim AS app-build
WORKDIR /src/app
ARG VITE_API_BASE=""
ENV VITE_API_BASE=${VITE_API_BASE}
COPY app/package.json app/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY app/ ./
# Canonical files the app imports from ../tracks (single-copy rule; see app/vite.config.ts).
COPY tracks/common/tests/fixtures/transmission_case_001/ /src/tracks/common/tests/fixtures/transmission_case_001/
COPY tracks/cases/kolam/source/ithayakkamalam_target.jpg /src/tracks/cases/kolam/source/ithayakkamalam_target.jpg
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Python runtime
# Python 3.13 matches the interpreter the pinned service/requirements.txt is tested with.
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app:/app/tracks/track-a/src:/app/tracks/track-b/src:/app/service \
    ANVESHAN_MODE=live \
    ANVESHAN_DAILY_CALL_BUDGET=2000 \
    ANVESHAN_CASES_ROOT=/app/tracks/cases \
    ANVESHAN_DATA_DIR=/tmp/anveshan \
    ANVESHAN_STATIC_DIR=/app/app/dist \
    ANVESHAN_MAX_UPLOAD_MB=30 \
    PORT=8080

WORKDIR /app

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin app

COPY service/requirements.txt /app/service/requirements.txt
RUN pip install -r /app/service/requirements.txt

# Case packs are writable by the app user: Track A build/review writes the next versions in place
# (ephemeral on Cloud Run; committed golden runs and versions ship in the image).
COPY --chown=app:app tracks/ /app/tracks/
COPY --chown=app:app tools/ /app/tools/
COPY --chown=app:app service/ /app/service/
COPY --chown=app:app --from=app-build /src/app/dist /app/app/dist

# Bake licensed case media (CC / public domain, ~50 MB) into the image. fetch_media verifies every
# sha256 and exits non-zero on a mismatch or download failure, which fails the build.
USER app
RUN python tools/fetch_media.py

EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn anveshan_service.main:app --host 0.0.0.0 --port ${PORT:-8080} --proxy-headers --forwarded-allow-ips='*'"]
