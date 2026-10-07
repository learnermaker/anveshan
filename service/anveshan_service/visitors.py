"""Anonymous per-visitor isolation for a public demo (no accounts).

Every browser gets a random ``anv_vid`` cookie. Drafts and upload/composed cases record the visitors
that created them in ``.owners.json``; other visitors get a 404 for those ids and do not see them in
the case list. Curated cases under ``cases_root`` are shared and never owned. A directory without an
owners file (created before isolation existed) stays visible to everyone.
"""

from __future__ import annotations

import contextvars
import json
import re
import secrets
from http.cookies import SimpleCookie
from pathlib import Path
from typing import List, Optional

COOKIE = "anv_vid"
OWNERS_FILE = ".owners.json"
_VID_RE = re.compile(r"^[0-9a-f]{32}$")

current_visitor: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("anveshan_visitor", default=None)


def _owners(directory: Path) -> Optional[List[str]]:
    p = Path(directory) / OWNERS_FILE
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return [str(v) for v in data.get("owners", [])]
    except (OSError, ValueError, AttributeError):
        return []


def add_owner(directory: Path, visitor: Optional[str] = None) -> None:
    """Record the current visitor as an owner of ``directory`` (content-addressed ids can be shared)."""
    visitor = visitor or current_visitor.get()
    directory = Path(directory)
    if not visitor or not directory.is_dir():
        return
    owners = _owners(directory) or []
    if visitor not in owners:
        owners.append(visitor)
        (directory / OWNERS_FILE).write_text(json.dumps({"owners": owners}), encoding="utf-8")


def visible(directory: Path, visitor: Optional[str] = None) -> bool:
    """True when the visitor may see ``directory``: no owners file (legacy/shared) or listed as owner."""
    owners = _owners(directory)
    if owners is None:
        return True
    visitor = visitor if visitor is not None else current_visitor.get()
    return bool(visitor) and visitor in owners


class VisitorMiddleware:
    """Pure ASGI middleware: read or mint the visitor cookie and expose it through ``current_visitor``."""

    def __init__(self, app, secure: bool = False) -> None:
        self.app = app
        self.secure = secure

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        vid = None
        for name, value in scope.get("headers", []):
            if name == b"cookie":
                jar = SimpleCookie()
                try:
                    jar.load(value.decode("latin-1"))
                except Exception:  # malformed cookie header: treat as absent
                    jar = SimpleCookie()
                morsel = jar.get(COOKIE)
                if morsel is not None and _VID_RE.fullmatch(morsel.value):
                    vid = morsel.value
                break
        minted = vid is None
        if minted:
            vid = secrets.token_hex(16)
        token = current_visitor.set(vid)

        async def send_with_cookie(message):
            if minted and message["type"] == "http.response.start":
                attrs = f"{COOKIE}={vid}; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax"
                if self.secure:
                    attrs += "; Secure"
                message.setdefault("headers", [])
                message["headers"] = list(message["headers"]) + [(b"set-cookie", attrs.encode("latin-1"))]
            await send(message)

        try:
            await self.app(scope, receive, send_with_cookie)
        finally:
            current_visitor.reset(token)
