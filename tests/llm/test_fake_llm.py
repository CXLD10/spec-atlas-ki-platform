"""Contract tests for the fake LLM provider (offline, deterministic)."""

from __future__ import annotations

import pytest
from jsonschema.exceptions import ValidationError

from spec_atlas.config import Settings
from spec_atlas.llm import FakeLLMProvider, Message, get_llm_provider

SPEC_SCHEMA = {
    "type": "object",
    "properties": {
        "purpose": {"type": "string"},
        "invariants": {"type": "array"},
    },
    "required": ["purpose", "invariants"],
}


def _msgs(content: str) -> list[Message]:
    return [{"role": "user", "content": content}]


def test_default_text_completion() -> None:
    p = FakeLLMProvider(default="hello")
    assert p.complete(_msgs("anything")) == "hello"


def test_canned_output_by_prompt_tag() -> None:
    p = FakeLLMProvider(responses={"greet": "hi there"})
    assert p.complete(_msgs("please [tag:greet] now")) == "hi there"
    # Unknown tag falls back to default.
    assert p.complete(_msgs("[tag:unknown]")) == "FAKE_COMPLETION"


def test_schema_returns_validated_dict_stub() -> None:
    p = FakeLLMProvider()
    out = p.complete(_msgs("generate a spec"), schema=SPEC_SCHEMA)
    assert isinstance(out, dict)
    assert set(out) >= {"purpose", "invariants"}
    assert isinstance(out["invariants"], list)


def test_schema_uses_canned_dict_when_tagged() -> None:
    canned = {"purpose": "issue tokens", "invariants": ["signed"]}
    p = FakeLLMProvider(responses={"spec": canned})
    out = p.complete(_msgs("[tag:spec]"), schema=SPEC_SCHEMA)
    assert out == canned


def test_invalid_canned_output_raises_against_schema() -> None:
    # Canned dict missing a required field must fail schema validation.
    p = FakeLLMProvider(responses={"spec": {"purpose": "x"}})
    with pytest.raises(ValidationError):
        p.complete(_msgs("[tag:spec]"), schema=SPEC_SCHEMA)


def test_factory_returns_fake_offline() -> None:
    provider = get_llm_provider(Settings(_env_file=None))  # defaults to fake
    assert isinstance(provider, FakeLLMProvider)
