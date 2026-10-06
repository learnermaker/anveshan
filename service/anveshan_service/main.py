"""FastAPI app factory. Run: ``uvicorn anveshan_service.main:app --app-dir service``."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from anveshan_service.errors import ServiceError, error_response, install_error_handlers
from anveshan_service.paths import within
from anveshan_service.routes import cases, compose, health, media, sessions
from anveshan_service.settings import Settings

MAX_UPLOAD_FILES = 3  # attempts: file + raster + video


class BodyLimitMiddleware:
    """Reject oversized requests up front from Content-Length (413) before multipart parsing.
    Per-file limits are enforced again while streaming each upload to disk."""

    def __init__(self, app, limit_bytes: int) -> None:
        self.app = app
        self.limit = limit_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            for name, value in scope.get("headers", []):
                if name == b"content-length":
                    try:
                        too_big = int(value) > self.limit
                    except ValueError:
                        too_big = False
                    if too_big:
                        resp = error_response(413, "INVALID_INPUT", "request body too large", {"limit_bytes": self.limit})
                        await resp(scope, receive, send)
                        return
                    break
        await self.app(scope, receive, send)


def _mount_static(app: FastAPI, static_dir: Path) -> None:
    index = static_dir / "index.html"

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str, request: Request) -> Response:
        if full_path == "api" or full_path.startswith("api/"):
            raise ServiceError(404, "MISSING_EVIDENCE", f"unknown API route /{full_path}")
        if full_path:
            candidate = static_dir / full_path
            if within(candidate, static_dir) and candidate.is_file():
                return FileResponse(candidate)
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(title="Anveshan", version="0.1.0", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.settings = settings
    install_error_handlers(app)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST"], allow_headers=["*"]
        )
    app.add_middleware(BodyLimitMiddleware, limit_bytes=settings.max_upload_bytes * MAX_UPLOAD_FILES + (1 << 20))
    for module in (health, cases, sessions, media, compose):
        app.include_router(module.router)
    if settings.static_dir is not None and (settings.static_dir / "index.html").is_file():
        _mount_static(app, settings.static_dir)
    return app


app = create_app()
