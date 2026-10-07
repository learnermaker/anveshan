"""
Hybrid pipeline configuration — loaded from .env / environment variables.

All model names and API keys are read here so nothing is hard-coded in
the individual modules. Import this module instead of os.environ directly.

Usage
-----
    from config import HybridConfig
    cfg = HybridConfig.load()
    print(cfg.hybrid_model)       # e.g. "gemini-3.8-flash"
    print(cfg.google_api_key)     # None if not set
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

_DEFAULT_HYBRID_MODEL = "gemini-3.8-flash"
_DEFAULT_FOLDINGAGENT_MODEL = "gemini-3.8-flash"

# Provider inference: model-name prefix → env key name
_PROVIDER_KEY_MAP = {
    "gemini": "GOOGLE_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "gpt":    "OPENAI_API_KEY",
    "o1":     "OPENAI_API_KEY",
    "o3":     "OPENAI_API_KEY",
    "o4":     "OPENAI_API_KEY",
}


# ---------------------------------------------------------------------------
# HybridConfig
# ---------------------------------------------------------------------------

@dataclass
class HybridConfig:
    """
    Runtime configuration for the hybrid origami pipeline.

    Loaded from (in priority order):
      1. Explicit arguments passed to HybridConfig()
      2. Environment variables (set in shell or exported)
      3. .env file at research/origami_hybrid/.env
    """

    # Model for hybrid pipeline LLM enrichment steps
    hybrid_model: str = _DEFAULT_HYBRID_MODEL

    # Optional fallback model if hybrid_model returns 404
    hybrid_fallback_model: Optional[str] = None

    # Model for FoldingAgent (reference only — must also set in FA config.py)
    foldingagent_model: str = _DEFAULT_FOLDINGAGENT_MODEL

    # API keys (None = not set)
    google_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        env_path: Optional[Path] = None,
        override: bool = False,
    ) -> "HybridConfig":
        """
        Load configuration from .env + environment.

        Parameters
        ----------
        env_path : Path | None
            Path to .env file. Defaults to research/origami_hybrid/.env.
        override : bool
            If True, .env values override existing environment variables.
        """
        _load_dotenv(env_path, override=override)

        hybrid_model = (
            os.environ.get("HYBRID_MODEL", "").strip()
            or _DEFAULT_HYBRID_MODEL
        )
        fallback = os.environ.get("HYBRID_FALLBACK_MODEL", "").strip() or None
        fa_model = (
            os.environ.get("FOLDINGAGENT_MODEL", "").strip()
            or _DEFAULT_FOLDINGAGENT_MODEL
        )

        return cls(
            hybrid_model=hybrid_model,
            hybrid_fallback_model=fallback,
            foldingagent_model=fa_model,
            google_api_key=os.environ.get("GOOGLE_API_KEY") or None,
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY") or None,
            openai_api_key=os.environ.get("OPENAI_API_KEY") or None,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def api_key_for(self, model_id: str) -> Optional[str]:
        """
        Return the appropriate API key for the given model ID.

        Infers the provider from the model name prefix:
          gemini-* → GOOGLE_API_KEY
          claude-* → ANTHROPIC_API_KEY
          gpt-* / o1 / o3 / o4-* → OPENAI_API_KEY
        """
        model_lower = model_id.lower()
        for prefix, key_attr in {
            "gemini": "google_api_key",
            "claude": "anthropic_api_key",
            "gpt":    "openai_api_key",
            "o1":     "openai_api_key",
            "o3":     "openai_api_key",
            "o4":     "openai_api_key",
        }.items():
            if model_lower.startswith(prefix):
                return getattr(self, key_attr)
        # Unknown prefix — try Google as default
        return self.google_api_key

    def require_key_for(self, model_id: str) -> str:
        """
        Return the API key for `model_id`, or raise RuntimeError if absent.
        """
        key = self.api_key_for(model_id)
        if not key:
            provider = _infer_provider(model_id)
            env_var = _PROVIDER_KEY_MAP.get(provider, "GOOGLE_API_KEY")
            raise RuntimeError(
                f"No API key found for model '{model_id}' (provider: {provider}). "
                f"Set {env_var} in research/origami_hybrid/.env or in your shell environment."
            )
        return key

    def summary(self) -> str:
        """Human-readable config summary (no key values)."""
        lines = [
            f"hybrid_model:          {self.hybrid_model}",
            f"hybrid_fallback_model: {self.hybrid_fallback_model or '(none)'}",
            f"foldingagent_model:    {self.foldingagent_model}",
            f"GOOGLE_API_KEY:        {'set' if self.google_api_key else 'NOT SET'}",
            f"ANTHROPIC_API_KEY:     {'set' if self.anthropic_api_key else 'NOT SET'}",
            f"OPENAI_API_KEY:        {'set' if self.openai_api_key else 'NOT SET'}",
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _load_dotenv(env_path: Optional[Path], override: bool) -> None:
    """Load .env if python-dotenv is available; silently skip if not."""
    path = env_path or (Path(__file__).parent / ".env")
    if not path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(path, override=override)
    except ImportError:
        # dotenv not installed — fall back to manual parse
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if k and (override or k not in os.environ):
                os.environ[k] = v


def _infer_provider(model_id: str) -> str:
    m = model_id.lower()
    for prefix in _PROVIDER_KEY_MAP:
        if m.startswith(prefix):
            return prefix
    return "gemini"
