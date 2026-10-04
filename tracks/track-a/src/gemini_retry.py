"""
Resilient retry wrapper for Google GenAI SDK calls (Phase 6).

Implements exponential backoff on HTTP 429 (Resource Exhausted) and 5xx errors,
mapping client/server errors to the standardized FailureCategory taxonomy.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, TypeVar

from models import FailureCategory, TrackAFailure

logger = logging.getLogger(__name__)

T = TypeVar("T")


def with_gemini_retry(
    fn: Callable[..., T],
    *args: Any,
    max_retries: int = 3,
    backoff_base: float = 2.0,
    **kwargs: Any,
) -> T:
    """
    Executes a callable with exponential backoff on transient errors.
    Catches google.genai.errors and maps them cleanly to TrackAFailure.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return fn(*args, **kwargs)
        except TrackAFailure:
            raise
        except Exception as exc:
            exc_str = str(exc)
            exc_name = exc.__class__.__name__

            # Check for Rate Limit / Quota Exhaustion (429)
            is_rate_limit = (
                "429" in exc_str
                or "RESOURCE_EXHAUSTED" in exc_str
                or "ResourceExhausted" in exc_name
                or "rate" in exc_str.lower()
            )

            # Check for 5xx Server Error
            is_server_error = (
                "500" in exc_str
                or "503" in exc_str
                or "InternalServerError" in exc_name
                or "ServiceUnavailable" in exc_name
            )

            if (is_rate_limit or is_server_error) and attempt < max_retries:
                wait_sec = (backoff_base ** attempt)
                logger.warning(
                    "Gemini API transient failure (%s) on attempt %d/%d. Retrying in %.1fs...",
                    exc_str,
                    attempt,
                    max_retries,
                    wait_sec,
                )
                time.sleep(wait_sec)
                continue

            if is_rate_limit:
                raise TrackAFailure(
                    FailureCategory.MODEL_TIMEOUT,
                    f"Gemini API rate limit exceeded after {attempt} attempts: {exc_str}",
                    {"attempts": attempt, "error": exc_str},
                ) from exc

            # Non-retryable client error or unhandled failure
            raise TrackAFailure(
                FailureCategory.MODEL_FAILURE,
                f"Gemini API execution error: {exc_str}",
                {"attempts": attempt, "error": exc_str},
            ) from exc

    raise TrackAFailure(
        FailureCategory.MODEL_TIMEOUT,
        f"Max retries ({max_retries}) exceeded for Gemini API call.",
    )
