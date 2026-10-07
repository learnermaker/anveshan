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
import threading
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
    "audio": ("ANVESHAN_AUDIO_MODEL", ""),  # disabled unless configured (paid, ~$0.0003/clip)
    "vision_fast": ("ANVESHAN_VISION_FAST_MODEL", "gemini-3.5-flash-lite"),  # interactive perception (~2.5 s/image)
    "embedding": ("ANVESHAN_EMBEDDING_MODEL", "gemini-embedding-2"),         # image/frame/text embeddings
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
class EmbeddingResult:
    vectors: Any            # numpy float32 array (n, dims), unit rows
    metadata: "RunMetadata"


@dataclass
class GenerationResult:
    data: BaseModel
    raw_text: str
    metadata: RunMetadata


_RETRYABLE_SIGNALS = ("504", "deadline_exceeded", "unavailable", "service unavailable")


def _is_retryable_exc(exc: Exception) -> bool:
    """Return True if the exception signals a transient server error worth one retry."""
    msg = str(exc).lower()
    return any(s in msg for s in _RETRYABLE_SIGNALS)


_RATE_LIMIT_SIGNALS = ("429", "resource_exhausted", "rate limit", "quota")
RATE_LIMIT_BACKOFF_S = (5.0, 15.0, 30.0)   # waits before retries 1..3 on HTTP 429 (per-minute quotas)


def _is_rate_limited(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(s in msg for s in _RATE_LIMIT_SIGNALS)


def _sleep(seconds: float) -> None:   # indirection so tests can patch the wait
    time.sleep(seconds)


class DailyBudget:
    """Process-wide cap on live provider calls per UTC day (``ANVESHAN_DAILY_CALL_BUDGET``; 0/unset = off).

    Protects a public demo from draining the API quota. Recorded and cached calls never count."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._day = ""
        self.used = 0

    @staticmethod
    def limit() -> int:
        try:
            return max(0, int(os.environ.get("ANVESHAN_DAILY_CALL_BUDGET", "0") or 0))
        except ValueError:
            return 0

    def take(self) -> None:
        limit = self.limit()
        if not limit:
            return
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            if today != self._day:
                self._day, self.used = today, 0
            if self.used >= limit:
                raise ModelError(
                    FailureCategory.MODEL_FAILURE,
                    "Today's live AI budget for this demo is used up. Recorded examples and samples still work; "
                    "please try again tomorrow (UTC).",
                    {"reason": "daily_budget", "limit": limit},
                )
            self.used += 1

    def today_used(self) -> int:
        """Return the number of live calls made today (UTC), 0 if no calls yet today."""
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self._lock:
            return self.used if self._day == today else 0


DAILY_BUDGET = DailyBudget()


class UsageCounters:
    """Process-wide counts for the steward usage view (never affects behaviour)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.cache_hits = 0
        self.own_key_calls = 0
        self.live_calls = 0

    def inc(self, name: str) -> None:
        with self._lock:
            setattr(self, name, getattr(self, name) + 1)


USAGE = UsageCounters()


def live_cache_enabled() -> bool:
    """Live mode reuses an identical earlier call (same model, prompt version, system text and inputs)
    from the run store. Identical uploads then get identical results at no cost. Variance studies set
    ``ANVESHAN_LIVE_CACHE=0``."""
    return os.environ.get("ANVESHAN_LIVE_CACHE", "1").strip().lower() not in ("0", "false", "no", "off")


class ModelGateway:
    def __init__(
        self,
        mode: Mode,
        store: RunStore,
        registry: Optional[ModelRegistry] = None,
        api_key: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        client: Any = None,
    ) -> None:
        """``timeout_ms`` defaults to ``ANVESHAN_MODEL_TIMEOUT_MS`` env var (default 300 000 ms)."""
        if mode not in ("live", "recorded"):
            raise ValueError(mode)
        self.mode = mode
        self.store = store
        self.registry = registry or ModelRegistry()
        self._api_key = api_key
        # A caller-supplied key (bring-your-own-key) is the caller's quota: no shared daily budget.
        self.own_key = api_key is not None
        if timeout_ms is None:
            timeout_ms = int(os.environ.get("ANVESHAN_MODEL_TIMEOUT_MS", "300000"))
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

        if live_cache_enabled():
            hit = self.store.find(key)
            if hit is not None:
                raw_text = hit["raw"].get("text", "")
                try:
                    parsed = self._validate(raw_text, schema, prompt_id)
                except ModelError:
                    parsed = None  # a cached response that no longer validates: call the model again
                if parsed is not None:
                    meta_d = dict(hit["metadata"])
                    meta_d["runtime_class"] = "RECORDED_LIVE"
                    meta_d["notes"] = list(meta_d.get("notes") or []) + ["live_cache_hit"]
                    USAGE.inc("cache_hits")
                    return GenerationResult(parsed, raw_text, RunMetadata(**meta_d))

        model_id = self.registry.model_id(model_key)
        if not model_id:
            raise ModelError(FailureCategory.MODEL_FAILURE, f"model key {model_key!r} is disabled (no model id configured)")
        client = self._get_client()
        if not self.own_key:
            DAILY_BUDGET.take()
            USAGE.inc("live_calls")
        else:
            USAGE.inc("own_key_calls")
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
        rate_waits = 0
        for api_attempt in range(2 + len(RATE_LIMIT_BACKOFF_S)):  # 1 retry on 5xx; up to 3 backoff retries on 429
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
                except Exception as exc:  # provider error: retry without JSON mode, then fail explicitly
                    last_exc = exc
                    msg = str(exc).lower()
                    if attempt == 0 and ("mime" in msg or "json" in msg or "response_mime_type" in msg or "invalid_argument" in msg):
                        continue
                    break
            if response is not None:
                break
            # Check whether the failure is retryable (504 / DEADLINE_EXCEEDED / UNAVAILABLE).
            if last_exc is not None and _is_rate_limited(last_exc) and rate_waits < len(RATE_LIMIT_BACKOFF_S):
                wait = RATE_LIMIT_BACKOFF_S[rate_waits]
                rate_waits += 1
                notes.append(f"rate_limited_backoff_{wait:g}s")
                _sleep(wait)
                continue
            if api_attempt == 0 and last_exc is not None and _is_retryable_exc(last_exc):
                notes.append(f"retried_once_after_{type(last_exc).__name__}")
                continue
            break  # not retryable or retries exhausted
        latency = int((time.perf_counter() - t0) * 1000)
        if response is None:
            exc_msg = str(last_exc).lower() if last_exc else ""
            cat = FailureCategory.MODEL_TIMEOUT if "timeout" in exc_msg or "deadline_exceeded" in exc_msg else FailureCategory.MODEL_FAILURE
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

    def embed(
        self,
        *,
        items: Sequence[Part],
        purpose: str,
        model_key: str = "embedding",
        dims: int = 768,
        batch_size: int = 16,
    ) -> "EmbeddingResult":
        """Embed each item (text / ImagePart / AudioPart) separately into unit vectors (n, dims).

        Recorded like generate_json: vectors are stored as float16 ``vectors.npy`` next to the run
        metadata; ``recorded`` mode replays them or raises REPLAY_MISMATCH. ``purpose`` is a short
        stable label (e.g. "perception_frames") that becomes part of the replay key.
        """
        import numpy as np

        if not items:
            raise ModelError(FailureCategory.INVALID_INPUT, "embed() needs at least one item")
        key = replay_key(model_key, f"embed:{purpose}", f"d{dims}", "", items)
        if self.mode == "recorded" or live_cache_enabled():
            hit = self.store.find(key)
            arr_path = None
            for root in self.store.roots:
                if (root / key / "vectors.npy").exists():
                    arr_path = root / key / "vectors.npy"
                    break
            if self.mode == "live" and (hit is None or arr_path is None):
                pass  # live cache miss: embed below
            elif hit is None or arr_path is None:
                raise ModelError(FailureCategory.REPLAY_MISMATCH, f"no recorded embeddings for {purpose} (key {key})", {"replay_key": key})
            else:
                meta_d = dict(hit["metadata"])
                meta_d["runtime_class"] = "RECORDED_LIVE"
                if self.mode == "live":
                    meta_d["notes"] = list(meta_d.get("notes") or []) + ["live_cache_hit"]
                    USAGE.inc("cache_hits")
                vecs = np.load(arr_path).astype(np.float32)
                return EmbeddingResult(vectors=vecs, metadata=RunMetadata(**meta_d))

        model_id = self.registry.model_id(model_key)
        if not model_id:
            raise ModelError(FailureCategory.MODEL_FAILURE, f"model key {model_key!r} is disabled (no model id configured)")
        client = self._get_client()
        from google.genai import types

        def to_content(p: Part) -> Any:
            if isinstance(p, str):
                return types.Content(parts=[types.Part(text=p)])
            return types.Content(parts=[types.Part.from_bytes(data=p.data, mime_type=p.mime_type)])

        started = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()
        rows: List[List[float]] = []
        try:
            for i in range(0, len(items), batch_size):
                chunk = items[i : i + batch_size]
                if not self.own_key:
                    DAILY_BUDGET.take()
                    USAGE.inc("live_calls")
                else:
                    USAGE.inc("own_key_calls")
                for wait in (*RATE_LIMIT_BACKOFF_S, None):
                    try:
                        resp = client.models.embed_content(
                            model=model_id,
                            contents=[to_content(p) for p in chunk],
                            config=types.EmbedContentConfig(output_dimensionality=dims),
                        )
                        break
                    except Exception as exc:  # 429: back off and retry; anything else fails below
                        if wait is None or not _is_rate_limited(exc):
                            raise
                        _sleep(wait)
                if len(resp.embeddings) != len(chunk):
                    raise ModelError(FailureCategory.MODEL_FAILURE, f"{model_id}: got {len(resp.embeddings)} embeddings for {len(chunk)} items")
                rows.extend(e.values for e in resp.embeddings)
        except ModelError:
            raise
        except Exception as exc:
            cat = FailureCategory.MODEL_TIMEOUT if "timeout" in str(exc).lower() or "deadline" in str(exc).lower() else FailureCategory.MODEL_FAILURE
            raise ModelError(cat, f"{model_id} embedding failed: {exc}", {"model_id": model_id}) from exc
        vecs = np.asarray(rows, dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        vecs = vecs / np.where(norms == 0, 1.0, norms)
        meta = RunMetadata(
            run_id=f"run.embed.{purpose}.{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.{uuid.uuid4().hex[:6]}",
            provider="google-genai",
            model_key=model_key,
            model_id=model_id,
            prompt_id=f"embed:{purpose}",
            prompt_version=f"d{dims}",
            prompt_sha256="",
            input_digests=parts_digest(items),
            runtime_class="LIVE",
            started_at=started,
            latency_ms=int((time.perf_counter() - t0) * 1000),
            replay_key=key,
        )
        d = self.store.save(meta, {"text": "", "embedding_count": int(vecs.shape[0]), "dims": int(vecs.shape[1])})
        np.save(d / "vectors.npy", vecs.astype(np.float16))
        return EmbeddingResult(vectors=vecs, metadata=meta)

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
