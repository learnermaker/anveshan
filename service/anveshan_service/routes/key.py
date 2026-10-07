"""POST /api/key/check — verify a visitor's own Gemini key with one free metadata call.

The key arrives in ``X-Gemini-Api-Key`` (never in the URL or body), is used for this request only
and is never stored or echoed. The check reads the configured model's metadata, which costs no
generation tokens.
"""

from __future__ import annotations

from fastapi import APIRouter

from tracks.common.models import ModelRegistry

from anveshan_service.errors import ServiceError, invalid
from anveshan_service.userkey import current_key

router = APIRouter()


@router.post("/api/key/check")
def check_key() -> dict:
    key = current_key.get()
    if not key:
        raise invalid("No API key was sent, or it does not look like a Google API key.")
    model = ModelRegistry().model_id("vision_fast") or "gemini-3.5-flash-lite"
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=20000))
        info = client.models.get(model=model)
    except Exception as exc:  # never echo provider text: it can contain request details
        msg = str(exc).lower()
        if "api key" in msg or "api_key" in msg or "permission" in msg or "401" in msg or "403" in msg or "invalid" in msg:
            raise ServiceError(400, "INVALID_INPUT", "Google rejected this key. Check that it is a Gemini API key from AI Studio and that it is enabled.") from None
        if "429" in msg or "quota" in msg or "resource_exhausted" in msg:
            raise ServiceError(429, "RATE_LIMITED", "This key is valid but its quota is used up right now. Try again later.") from None
        raise ServiceError(502, "MODEL_FAILURE", "Could not reach Google to check the key. Please try again.") from None
    return {"ok": True, "model": getattr(info, "name", model)}
