"""Deterministic, offline fake LLM provider.

Returns canned output selected by a ``[tag:NAME]`` marker in the prompt (so tests can
pin exact responses), or — when a JSON Schema is requested — a minimal schema-shaped
stub that validates against it. No network, no API key. Used whenever
``LLM_PROVIDER=fake`` so the whole system is testable offline (testing-standard)."""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from typing import Any

from .base import LLMProvider, Message, validate_json

_TAG_RE = re.compile(r"\[tag:([A-Za-z0-9_-]+)\]")


def _stub_for_schema(schema: dict) -> Any:
    """Build a minimal value satisfying a (subset of) JSON Schema."""
    kind = schema.get("type")
    if kind == "object":
        props = schema.get("properties", {})
        required = schema.get("required", list(props))
        return {name: _stub_for_schema(props.get(name, {})) for name in required}
    if kind == "array":
        return []
    if kind == "string":
        return schema.get("default", "fake")
    if kind in ("number", "integer"):
        return 0
    if kind == "boolean":
        return False
    return None


class FakeLLMProvider(LLMProvider):
    def __init__(
        self,
        responses: dict[str, str | dict] | None = None,
        default: str = "FAKE_COMPLETION",
    ) -> None:
        # Map a prompt tag -> canned response (str for text, dict for structured).
        self.responses = responses or {}
        self.default = default

    def _select_tag(self, messages: Sequence[Message]) -> str | None:
        joined = "\n".join(m["content"] for m in messages)
        match = _TAG_RE.search(joined)
        return match.group(1) if match else None

    def complete(self, messages: Sequence[Message], schema: dict | None = None) -> str | dict:
        tag = self._select_tag(messages)
        canned = self.responses.get(tag) if tag is not None else None

        if schema is not None:
            payload = canned if canned is not None else _stub_for_schema(schema)
            # Validates the canned/stub output against the schema (raises if invalid).
            return validate_json(payload, schema)

        if canned is not None:
            return canned if isinstance(canned, str) else json.dumps(canned)
        return self.default
