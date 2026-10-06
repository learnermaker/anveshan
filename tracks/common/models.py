"""Shared model gateway: registry, JSON generation, and run recording/replay.

Every Gemma/Gemini call in Anveshan goes through ``ModelGateway.generate_json``.
Rules (see .claude/skills/model-gateway):
- model ids come from env via ``ModelRegistry``; no hard-coded ids or silent fallback lists;
- temperature 0, JSON output validated by a Pydantic DTO;
- every live call is recorded; ``recorded`` mode replays by key or raises REPLAY_MISMATCH;
- failures are explicit ``ModelError``s, never fabricated content.
This is a shared utility, not a contract.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Type, TypeVar, Union

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)
Mode = Literal["live", "recorded"]


class FailureCategory(str, Enum):
    """Shared failure taxonomy (tracks/common/CASE-DATA-CONVENTIONS.md §6)."""

    INVALID_INPUT = "INVALID_INPUT"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    AMBIGUOUS_EVIDENCE = "AMBIGUOUS_EVIDENCE"
    UNSUPPORTED_CLAIM = "UNSUPPORTED_CLAIM"
    CONTRACT_VIOLATION = "CONTRACT_VIOLATION"
    MODEL_FAILURE = "MODEL_FAILURE"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    REPLAY_MISMATCH = "REPLAY_MISMATCH"
    HUMAN_REVIEW_REQUIRED = "HUMAN_REVIEW_REQUIRED"


class AnveshanFailure(Exception):
    def __init__(self, category: FailureCategory, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(f"[{category.value}] {message}")
        self.category = category
        self.message = message
        self.details = details or {}


class ModelError(AnveshanFailure):
    pass


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_REGISTRY_ENV = {
    "text_image": ("ANVESHAN_TEXT_IMAGE_MODEL", "gemma-4-26b-a4b-it"),
    "video_frames": ("ANVESHAN_VIDEO_FRAMES_MODEL", "gemma-4-26b-a4b-it"),
    "audio": ("ANVESHAN_AUDIO_MODEL", ""),  # disabled unless configured (paid)
}


def load_dotenv(path: Path | str = ".env") -> None:
    """Minimal .env loader (does not override existing env vars)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.split(" #", 1)[0].strip().strip("'\"")
        os.environ.setdefault(k.strip(), v)


class ModelRegistry:
    def __init__(self, overrides: Optional[Dict[str, str]] = None) -> None:
        self._overrides = overrides or {}

    def model_id(self, key: str) -> Optional[str]:
        if key in self._overrides:
            return self._overrides[key] or None
        if key not in _REGISTRY_ENV:
            raise KeyError(f"unknown model key {key!r}")
        env, default = _REGISTRY_ENV[key]
        value = os.environ.get(env, default)
        return value or None

    def enabled(self, key: str) -> bool:
        return self.model_id(key) is not None


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ImagePart:
    data: bytes
    mime_type: str = "image/jpeg"
    label: Optional[str] = None  # optional caption placed before the image in the prompt


@dataclass(frozen=True)
class AudioPart:
    data: bytes
    mime_type: str = "audio/wav"


Part = Union[str, ImagePart, AudioPart]


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parts_digest(parts: Sequence[Part]) -> List[str]:
    out: List[str] = []
    for p in parts:
        if isinstance(p, str):
            out.append("text:" + _sha(p.encode("utf-8")))
        else:
            out.append(f"{type(p).__name__}:" + _sha(p.data))
    return out


# ---------------------------------------------------------------------------
# Run records
# ---------------------------------------------------------------------------


@dataclass
class RunMetadata:
    run_id: str
    provider: str
    model_key: str
    model_id: str
    prompt_id: str
    prompt_version: str
    prompt_sha256: str
    input_digests: List[str]
    runtime_class: Literal["LIVE", "RECORDED_LIVE"]
    started_at: str
    latency_ms: int
    replay_key: str
    expected_behavior: str = ""
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.__dict__)


def replay_key(model_key: str, prompt_id: str, prompt_version: str, system: str, parts: Sequence[Part]) -> str:
    payload = json.dumps(
        {"model_key": model_key, "prompt": f"{prompt_id}@{prompt_version}", "system": _sha(system.encode()), "parts": parts_digest(parts)},
        sort_keys=True,
    )
    return _sha(payload.encode())[:32]


class RunStore:
    """File-based store of recorded model runs: <root>/<replay_key>/{run_metadata,raw_response}.json"""

    def __init__(self, roots: Sequence[Path | str]) -> None:
        # First root is where new live runs are written; all roots are searched on replay.
        self.roots = [Path(r) for r in roots]

    def find(self, key: str) -> Optional[Dict[str, Any]]:
        for root in self.roots:
            d = root / key
            if (d / "raw_response.json").exists():
                return {
                    "metadata": json.loads((d / "run_metadata.json").read_text(encoding="utf-8")),
                    "raw": json.loads((d / "raw_response.json").read_text(encoding="utf-8")),
                }
        return None

    def save(self, meta: RunMetadata, raw: Dict[str, Any]) -> Path:
        d = self.roots[0] / meta.replay_key
        d.mkdir(parents=True, exist_ok=True)
        (d / "run_metadata.json").write_text(json.dumps(meta.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
        (d / "raw_response.json").write_text(json.dumps(raw, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        return d


# ---------------------------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------------------------

_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL)


def extract_json(text: str) -> Any:
    """Extract the first JSON object/array from model text (handles ```json fences)."""
    if not text or not text.strip():
        raise ValueError("empty model text")
    m = _FENCE.search(text)
    candidate = m.group(1) if m else text
    candidate = candidate.strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    starts = [i for i in (candidate.find("{"), candidate.find("[")) if i >= 0]
    if not starts:
        raise ValueError("no JSON object in model text")
    start = min(starts)
    dec = json.JSONDecoder()
    obj, _ = dec.raw_decode(candidate[start:])
    return obj


# ---------------------------------------------------------------------------
# Gateway
# ---------------------------------------------------------------------------


@dataclass
class GenerationResult:
    data: BaseModel
    raw_text: str
    metadata: RunMetadata


class ModelGateway:
    def __init__(
        self,
        mode: Mode,
        store: RunStore,
        registry: Optional[ModelRegistry] = None,
        api_key: Optional[str] = None,
        timeout_ms: int = 120_000,
        client: Any = None,
    ) -> None:
        if mode not in ("live", "recorded"):
            raise ValueError(mode)
        self.mode = mode
        self.store = store
        self.registry = registry or ModelRegistry()
        self._api_key = api_key
        self._timeout_ms = timeout_ms
        self._client = client

    def _get_client(self) -> Any:
        if self._client is None:
            key = self._api_key or os.environ.get("GEMINI_API_KEY")
            if not key:
                raise ModelError(FailureCategory.MODEL_FAILURE, "GEMINI_API_KEY is not set (live mode)")
            from google import genai
            from google.genai import types

            self._client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=self._timeout_ms))
        return self._client

    def generate_json(
        self,
        *,
        model_key: str,
        prompt_id: str,
        prompt_version: str,
        prompt_text: str,
        schema: Type[T],
        parts: Sequence[Part] = (),
        system: str = "",
        expected_behavior: str = "",
    ) -> GenerationResult:
        """Generate and validate JSON. ``prompt_text`` is appended after ``parts``."""
        all_parts: List[Part] = [*parts, prompt_text]
        key = replay_key(model_key, prompt_id, prompt_version, system, all_parts)
        if self.mode == "recorded":
            hit = self.store.find(key)
            if hit is None:
                raise ModelError(
                    FailureCategory.REPLAY_MISMATCH,
                    f"no recorded run for {prompt_id}@{prompt_version} (key {key})",
                    {"replay_key": key},
                )
            raw_text = hit["raw"]["text"]
            meta_d = dict(hit["metadata"])
            meta_d["runtime_class"] = "RECORDED_LIVE"
            meta = RunMetadata(**meta_d)
            return GenerationResult(self._validate(raw_text, schema, prompt_id), raw_text, meta)

        model_id = self.registry.model_id(model_key)
        if not model_id:
            raise ModelError(FailureCategory.MODEL_FAILURE, f"model key {model_key!r} is disabled (no model id configured)")
        client = self._get_client()
        from google.genai import types

        contents: List[Any] = []
        for p in all_parts:
            if isinstance(p, str):
                contents.append(p)
            elif isinstance(p, ImagePart):
                if p.label:
                    contents.append(p.label)
                contents.append(types.Part.from_bytes(data=p.data, mime_type=p.mime_type))
            elif isinstance(p, AudioPart):
                contents.append(types.Part.from_bytes(data=p.data, mime_type=p.mime_type))
        notes: List[str] = []
        started = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()
        response = None
        last_exc: Optional[Exception] = None
        for attempt, json_mode in enumerate((True, False)):
            cfg: Dict[str, Any] = {"temperature": 0.0}
            if system:
                cfg["system_instruction"] = system
            if json_mode:
                cfg["response_mime_type"] = "application/json"
            try:
                response = client.models.generate_content(
                    model=model_id, contents=contents, config=types.GenerateContentConfig(**cfg)
                )
                if json_mode is False:
                    notes.append("json_mode_unsupported_retried_without")
                break
            except Exception as exc:  # provider error: retry once without JSON mode, then fail explicitly
                last_exc = exc
                msg = str(exc).lower()
                if attempt == 0 and ("mime" in msg or "json" in msg or "response_mime_type" in msg or "invalid_argument" in msg):
                    continue
                break
        latency = int((time.perf_counter() - t0) * 1000)
        if response is None:
            cat = FailureCategory.MODEL_TIMEOUT if last_exc and "timeout" in str(last_exc).lower() else FailureCategory.MODEL_FAILURE
            raise ModelError(cat, f"{model_id} call failed: {last_exc}", {"model_id": model_id})
        raw_text = getattr(response, "text", None) or ""
        meta = RunMetadata(
            run_id=f"run.{prompt_id}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.{uuid.uuid4().hex[:6]}",
            provider="google-genai",
            model_key=model_key,
            model_id=model_id,
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            prompt_sha256=_sha(prompt_text.encode("utf-8")),
            input_digests=parts_digest(all_parts),
            runtime_class="LIVE",
            started_at=started,
            latency_ms=latency,
            replay_key=key,
            expected_behavior=expected_behavior,
            notes=notes,
        )
        self.store.save(meta, {"text": raw_text})
        return GenerationResult(self._validate(raw_text, schema, prompt_id), raw_text, meta)

    @staticmethod
    def _validate(raw_text: str, schema: Type[T], prompt_id: str) -> T:
        try:
            return schema.model_validate(extract_json(raw_text))
        except (ValueError, ValidationError) as exc:
            raise ModelError(
                FailureCategory.MODEL_FAILURE,
                f"{prompt_id}: model output failed {schema.__name__} validation: {exc}",
                {"raw_text": raw_text[:2000]},
            ) from exc


def load_prompt(path: Path | str, **values: str) -> tuple[str, str]:
    """Load a versioned prompt file and substitute {placeholders}. Returns (text, version)."""
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    for k, v in values.items():
        text = text.replace("{" + k + "}", v)
    m = re.search(r"_v(\d+)\.txt$", p.name)
    return text, (f"v{m.group(1)}" if m else "v0")
