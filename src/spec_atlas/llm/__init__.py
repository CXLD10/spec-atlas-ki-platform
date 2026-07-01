"""LLM providers — interface, offline fake, and the Gemini real default.

Use :func:`get_llm_provider` to obtain the provider selected by configuration
(``LLM_PROVIDER``); callers depend only on :class:`LLMProvider`.
"""

from __future__ import annotations

from spec_atlas.config import Settings, get_settings

from .base import (
    LLMError,
    LLMProvider,
    Message,
    TransientLLMError,
    transient_retry,
    validate_json,
)
from .fake import FakeLLMProvider

__all__ = [
    "LLMProvider",
    "FakeLLMProvider",
    "Message",
    "LLMError",
    "TransientLLMError",
    "transient_retry",
    "validate_json",
    "get_llm_provider",
]


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    """Return the configured LLM provider.

    ``fake`` is fully offline. ``ollama`` and ``groq`` are real providers.
    ``gemini`` is also supported.
    """
    s = settings or get_settings()
    if s.llm_provider == "fake":
        return FakeLLMProvider()
    elif s.llm_provider == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider(base_url=s.ollama_base_url, model=s.ollama_model)
    elif s.llm_provider == "groq":
        from .ollama_provider import GroqProvider

        return GroqProvider(model=s.groq_model)
    elif s.llm_provider == "gemini":
        from .gemini_provider import GeminiLLMProvider

        return GeminiLLMProvider(api_key=s.gemini_api_key or "", model=s.llm_model)
    else:
        raise ValueError(f"Unknown LLM provider: {s.llm_provider}")
