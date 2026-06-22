"""LLM provider interface + shared retry/validation helpers.

All LLM access goes through :class:`LLMProvider`; callers never import a vendor SDK
(ARCHITECTURE.md cross-cutting contracts). Structured output is validated against a
JSON Schema so callers can trust the shape (INTEGRATIONS.md §3). Transient failures
(429 / timeout / cold-start) are retried with exponential backoff.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any, TypedDict

from jsonschema import validate as jsonschema_validate
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class Message(TypedDict):
    """A chat message. ``role`` is one of ``system`` / ``user`` / ``assistant``."""

    role: str
    content: str


class LLMError(Exception):
    """Base class for LLM provider errors."""


class TransientLLMError(LLMError):
    """A retryable failure: HTTP 429, timeout, or free-tier cold start."""


def transient_retry(
    attempts: int = 4, base_delay: float = 0.5, max_delay: float = 8.0
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator: retry on :class:`TransientLLMError` with exponential backoff.

    ``reraise=True`` so the original error surfaces after the final attempt.
    """
    return retry(
        retry=retry_if_exception_type(TransientLLMError),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=base_delay, max=max_delay),
        reraise=True,
    )


def validate_json(payload: str | dict, schema: dict) -> dict:
    """Parse (if needed) and validate ``payload`` against ``schema``; return the dict."""
    obj = json.loads(payload) if isinstance(payload, str) else payload
    jsonschema_validate(instance=obj, schema=schema)
    return obj


class LLMProvider(ABC):
    """Generate a completion from chat messages.

    With ``schema=None`` returns the model's text. With a JSON Schema, returns a dict
    validated against it (raises on invalid output).
    """

    @abstractmethod
    def complete(self, messages: Sequence[Message], schema: dict | None = None) -> str | dict: ...
