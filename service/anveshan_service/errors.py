"""Error mapping: AnveshanFailure -> HTTP (docs/plans/service-api.md §5).

Every error body is ``{"error": {"category", "message", "details"}}``. Unexpected exceptions
become a generic 500 that never echoes exception text (which could carry secrets).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from tracks.common.models import AnveshanFailure, FailureCategory

log = logging.getLogger("anveshan_service")

CATEGORY_STATUS: Dict[str, int] = {
    FailureCategory.INVALID_INPUT.value: 400,
    FailureCategory.MISSING_EVIDENCE.value: 404,
    FailureCategory.REPLAY_MISMATCH.value: 409,
    FailureCategory.HUMAN_REVIEW_REQUIRED.value: 422,
    # Not listed in §5; they are evidence-quality refusals like HUMAN_REVIEW_REQUIRED.
    FailureCategory.AMBIGUOUS_EVIDENCE.value: 422,
    FailureCategory.UNSUPPORTED_CLAIM.value: 422,
    FailureCategory.MODEL_FAILURE.value: 502,
    FailureCategory.MODEL_TIMEOUT.value: 502,
    FailureCategory.CONTRACT_VIOLATION.value: 500,
}

_HTTP_CATEGORY = {400: "INVALID_INPUT", 404: "MISSING_EVIDENCE", 405: "METHOD_NOT_ALLOWED", 413: "INVALID_INPUT"}
_SECRET_ENV = ("GEMINI_API_KEY", "GOOGLE_API_KEY")
_SECRET_WORDS = ("key", "token", "secret", "password", "credential", "authorization")


class ServiceError(Exception):
    """Service-level error with an explicit HTTP status (e.g. 413, 503)."""

    def __init__(self, status: int, category: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status = status
        self.category = category
        self.message = message
        self.details = details or {}


def invalid(message: str, **details: Any) -> ServiceError:
    return ServiceError(400, FailureCategory.INVALID_INPUT.value, message, details)


def not_found(message: str, **details: Any) -> ServiceError:
    return ServiceError(404, FailureCategory.MISSING_EVIDENCE.value, message, details)


def _redact(text: str) -> str:
    from anveshan_service.userkey import current_key

    values = [os.environ.get(name) for name in _SECRET_ENV] + [current_key.get()]
    for value in values:
        if value and len(value) >= 8:
            text = text.replace(value, "[REDACTED]")
    return text


def _clean_details(details: Any) -> Any:
    if isinstance(details, dict):
        return {
            k: ("[REDACTED]" if any(w in str(k).lower() for w in _SECRET_WORDS) and k != "replay_key" else _clean_details(v))
            for k, v in details.items()
        }
    if isinstance(details, (list, tuple)):
        return [_clean_details(v) for v in details]
    if isinstance(details, str):
        return _redact(details)
    return details


def error_response(status: int, category: str, message: str, details: Any = None) -> JSONResponse:
    body = {"error": {"category": category, "message": _redact(str(message)), "details": _clean_details(jsonable_encoder(details or {}))}}
    return JSONResponse(status_code=status, content=body)


def failure_status(category: str) -> int:
    return CATEGORY_STATUS.get(category, 500)


def _category_of(exc: BaseException) -> Optional[str]:
    """Duck-typed failure detection so track-specific subclasses/mirrors (e.g. TrackBFailure) map too."""
    cat = getattr(exc, "category", None)
    if cat is None:
        return None
    value = getattr(cat, "value", cat)
    return value if isinstance(value, str) and value in FailureCategory.__members__ else None


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ServiceError)
    async def _service_error(_: Request, exc: ServiceError) -> JSONResponse:
        return error_response(exc.status, exc.category, exc.message, exc.details)

    @app.exception_handler(AnveshanFailure)
    async def _failure(_: Request, exc: AnveshanFailure) -> JSONResponse:
        return error_response(failure_status(exc.category.value), exc.category.value, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e.get("loc", ())), "msg": e.get("msg", "")} for e in exc.errors()]
        return error_response(400, FailureCategory.INVALID_INPUT.value, "request validation failed", {"errors": errors})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        category = _HTTP_CATEGORY.get(exc.status_code, "HTTP_ERROR")
        return error_response(exc.status_code, category, str(exc.detail))

    @app.exception_handler(FileNotFoundError)
    async def _missing_file(_: Request, exc: FileNotFoundError) -> JSONResponse:
        name = os.path.basename(str(exc.filename)) if exc.filename else ""
        return error_response(404, FailureCategory.MISSING_EVIDENCE.value, f"required file not found {name}".strip())

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Starlette re-raises after this handler (for server logs); the client only gets the generic body.
        category = _category_of(exc)
        if category is not None:
            return error_response(
                failure_status(category), category, getattr(exc, "message", "") or category, getattr(exc, "details", {}) or {}
            )
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "INTERNAL_ERROR", "internal server error", {"type": type(exc).__name__})
